import os
import time
import requests
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.session import get_db
from backend.models.movie import Movie

router = APIRouter(prefix="/admin", tags=["admin"])

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

def tmdb_search(title: str, year: Optional[int] = None) -> Optional[int]:
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not set")

    params = {"api_key": TMDB_API_KEY, "query": title}
    if year:
        params["year"] = year

    r = requests.get(TMDB_SEARCH_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    return results[0].get("id")

def tmdb_details(tmdb_id: int) -> dict:
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not set")

    r = requests.get(f"{TMDB_MOVIE_URL}/{tmdb_id}", params={"api_key": TMDB_API_KEY}, timeout=20)
    r.raise_for_status()
    return r.json()

@router.post("/backfill/movies")
def backfill_movies(
    limit: int = Query(200, ge=1, le=2000),
    sleep_ms: int = Query(150, ge=0, le=2000),
    db: Session = Depends(get_db),
):
    """
    Backfill poster_url, overview, release_date for movies missing poster_url.
    Safe to run multiple times.
    """
    if not TMDB_API_KEY:
        raise HTTPException(status_code=500, detail="TMDB_API_KEY is not set")

    q = (
        db.query(Movie)
        .filter((Movie.poster_url.is_(None)) | (Movie.poster_url == ""))
        .order_by(Movie.movie_id.asc())
        .limit(limit)
    )
    movies = q.all()

    updated = 0
    skipped = 0
    failed = 0

    for m in movies:
        try:
            # title (1995) gibi geldiyse parantezi kırp
            title = (m.title or "").strip()
            year = m.year

            tmdb_id = tmdb_search(title=title, year=year)
            if not tmdb_id:
                skipped += 1
                continue

            d = tmdb_details(tmdb_id)

            poster_path = d.get("poster_path")
            overview = d.get("overview")
            release_date = d.get("release_date")  # "YYYY-MM-DD"

            if poster_path:
                m.poster_url = f"{TMDB_IMG_BASE}{poster_path}"

            if overview and (not m.overview):
                m.overview = overview

            # release_date Date column ise string’i DB’ye cast etsin diye raw SQL ile güvenli yazıyoruz
            if release_date and (m.release_date is None):
                db.execute(
                    text("UPDATE movies SET release_date = :rd WHERE movie_id = :mid"),
                    {"rd": release_date, "mid": m.movie_id},
                )

            db.add(m)
            db.commit()
            updated += 1

            if sleep_ms:
                time.sleep(sleep_ms / 1000.0)

        except Exception as e:
            db.rollback()
            failed += 1

    return {
        "limit": limit,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "note": "Run again to fill more. Safe to re-run.",
    }
