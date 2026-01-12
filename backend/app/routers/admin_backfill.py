# backend/app/routers/admin_backfill.py

import os
import time
import logging
from typing import Optional, Dict, Any, List

import requests
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

log = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_READ_TOKEN = os.getenv("TMDB_READ_ACCESS_TOKEN")  # optional (v4)
INTERNAL_TOKEN = os.getenv("INTERNAL_ADMIN_TOKEN") or os.getenv("INTERNAL_AI_TOKEN")


def _require_internal_token(x_internal_token: Optional[str] = Header(default=None)) -> None:
    """
    Simple internal auth. Call with header:
      X-Internal-Token: <INTERNAL_ADMIN_TOKEN>
    """
    if not INTERNAL_TOKEN:
        # If you forgot to set it, fail closed (safer).
        raise HTTPException(status_code=500, detail="INTERNAL token is not configured on server")

    if not x_internal_token or x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _tmdb_headers() -> Dict[str, str]:
    """
    TMDB supports:
      - v3 API key via query param api_key=...
      - v4 read token via Authorization: Bearer <token>
    We'll use v3 api_key by default, but keep v4 token optional.
    """
    headers: Dict[str, str] = {"Accept": "application/json"}
    if TMDB_READ_TOKEN:
        headers["Authorization"] = f"Bearer {TMDB_READ_TOKEN}"
    return headers


def _tmdb_get_movie(movie_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch movie details by TMDB movie id.
    Returns None if not found or key missing.
    """
    if not TMDB_API_KEY and not TMDB_READ_TOKEN:
        raise HTTPException(status_code=500, detail="TMDB API key/token not configured (TMDB_API_KEY missing)")

    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"language": "en-US"}
    # If you have TMDB_API_KEY, use v3 style
    if TMDB_API_KEY:
        params["api_key"] = TMDB_API_KEY

    r = requests.get(url, params=params, headers=_tmdb_headers(), timeout=20)
    if r.status_code == 404:
        return None
    if r.status_code >= 400:
        # Don't leak secrets; keep it short
        raise HTTPException(status_code=502, detail=f"TMDB error {r.status_code}")

    return r.json()


def _build_poster_url(poster_path: Optional[str], size: str = "w500") -> Optional[str]:
    if not poster_path:
        return None
    # Standard TMDB image base
    return f"https://image.tmdb.org/t/p/{size}{poster_path}"


@router.get("/backfill/status")
def backfill_status(
    db: Session = Depends(get_db),
    _: None = Depends(_require_internal_token),
):
    """
    Quick stats: how many movies missing poster/overview/release_date.
    """
    q = text("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN poster_url IS NULL OR poster_url = '' THEN 1 ELSE 0 END) AS poster_missing,
            SUM(CASE WHEN overview IS NULL OR overview = '' THEN 1 ELSE 0 END) AS overview_missing,
            SUM(CASE WHEN release_date IS NULL THEN 1 ELSE 0 END) AS release_missing
        FROM movies
    """)
    row = db.execute(q).mappings().first()
    return dict(row) if row else {"total": 0, "poster_missing": 0, "overview_missing": 0, "release_missing": 0}


@router.post("/backfill/tmdb")
def backfill_movies_from_tmdb(
    limit: int = Query(50, ge=1, le=300),
    offset: int = Query(0, ge=0),
    sleep_ms: int = Query(150, ge=0, le=2000),
    only_missing: bool = Query(True),
    db: Session = Depends(get_db),
    _: None = Depends(_require_internal_token),
):
    """
    Backfill DB from TMDB.

    - limit/offset: batch window
    - sleep_ms: polite delay between TMDB calls
    - only_missing=True: only update rows missing poster/overview/release_date/year
      set False to force refresh for selected window
    """
    if not TMDB_API_KEY and not TMDB_READ_TOKEN:
        raise HTTPException(status_code=500, detail="TMDB_API_KEY or TMDB_READ_ACCESS_TOKEN is required")

    # Select a batch of movies
    if only_missing:
        sel = text("""
            SELECT movie_id, title, poster_url, overview, release_date, year
            FROM movies
            WHERE
                (poster_url IS NULL OR poster_url = '')
                OR (overview IS NULL OR overview = '')
                OR (release_date IS NULL)
                OR (year IS NULL)
            ORDER BY movie_id
            LIMIT :limit OFFSET :offset
        """)
    else:
        sel = text("""
            SELECT movie_id, title, poster_url, overview, release_date, year
            FROM movies
            ORDER BY movie_id
            LIMIT :limit OFFSET :offset
        """)

    rows = db.execute(sel, {"limit": limit, "offset": offset}).mappings().all()
    if not rows:
        return {"updated": 0, "skipped": 0, "errors": 0, "details": [], "message": "No rows in this window"}

    updated = 0
    skipped = 0
    errors = 0
    details: List[Dict[str, Any]] = []

    for row in rows:
        movie_id = int(row["movie_id"])

        try:
            data = _tmdb_get_movie(movie_id)
            if not data:
                skipped += 1
                details.append({"movie_id": movie_id, "status": "skipped", "reason": "tmdb_not_found"})
                continue

            poster_url = _build_poster_url(data.get("poster_path"), size="w500")
            overview = data.get("overview") or None
            release_date = data.get("release_date") or None

            # year: from release_date
            year = None
            if release_date and len(release_date) >= 4:
                try:
                    year = int(release_date[:4])
                except Exception:
                    year = None

            # If only_missing, don't overwrite existing non-empty values
            new_poster = poster_url if (not only_missing or not row["poster_url"]) else row["poster_url"]
            new_overview = overview if (not only_missing or not row["overview"]) else row["overview"]
            new_release = release_date if (not only_missing or not row["release_date"]) else row["release_date"]
            new_year = year if (not only_missing or not row["year"]) else row["year"]

            upd = text("""
                UPDATE movies
                SET poster_url = :poster_url,
                    overview = :overview,
                    release_date = :release_date,
                    year = :year
                WHERE movie_id = :movie_id
            """)

            db.execute(upd, {
                "poster_url": new_poster,
                "overview": new_overview,
                "release_date": new_release,
                "year": new_year,
                "movie_id": movie_id,
            })
            db.commit()

            updated += 1
            details.append({"movie_id": movie_id, "status": "updated", "poster": bool(new_poster), "overview": bool(new_overview)})

        except HTTPException:
            # pass through controlled errors
            errors += 1
            db.rollback()
            details.append({"movie_id": movie_id, "status": "error", "reason": "tmdb_http_error"})
        except Exception as e:
            errors += 1
            db.rollback()
            details.append({"movie_id": movie_id, "status": "error", "reason": str(e)[:120]})
            log.exception("Backfill error for movie_id=%s", movie_id)

        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)

    return {
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "only_missing": only_missing,
        "sleep_ms": sleep_ms,
        "details": details[:20],  # keep response small
    }
