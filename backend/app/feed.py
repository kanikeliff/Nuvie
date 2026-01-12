# backend/app/feed.py
import csv
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from .auth import get_current_user

# Local AI recommender
from aii.serving.recommender import recommend_for_user


router = APIRouter(prefix="/feed", tags=["Feed"])


def safe_year(release_date: Optional[str]) -> Optional[int]:
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None


def user_to_int(user_id: str) -> int:
    """
    Stable int for any user_id (uuid/email/etc) so AI model can be called.
    Returns 32-bit positive int.
    """
    h = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def ensure_movies_table_seeded(db: Session) -> None:
    """
    Ensure `movies` table exists; seed minimal rows from aii/data/processed/movies.csv if empty.
    This avoids 500 errors on fresh DBs.
    """
    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
        return
    except OperationalError:
        # previous statement may have aborted transaction; rollback first
        try:
            db.rollback()
        except Exception:
            pass

        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    movie_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    poster_url TEXT,
                    overview TEXT,
                    release_date TEXT
                )
                """
            )
        )
        db.commit()

    # Seed only if empty
    count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    if int(count) > 0:
        return

    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        logging.warning("movies.csv not found at %s; leaving movies table empty", csv_path)
        return

    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # keep it minimal; poster/overview can be null
            try:
                rows.append(
                    {
                        "movie_id": int(r["movie_id"]),
                        "title": r.get("title") or "Unknown",
                        "poster_url": r.get("poster_url"),
                        "overview": r.get("overview"),
                        "release_date": r.get("release_date"),
                    }
                )
            except Exception:
                continue

    if rows:
        db.execute(
            text(
                """
                INSERT INTO movies (movie_id, title, poster_url, overview, release_date)
                VALUES (:movie_id, :title, :poster_url, :overview, :release_date)
                """
            ),
            rows,
        )
        db.commit()


def fetch_movies_by_ids(db: Session, ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not ids:
        return {}
    rows = db.execute(
        text(
            """
            SELECT movie_id, title, poster_url, overview, release_date
            FROM movies
            WHERE movie_id = ANY(:ids)
            """
        ),
        {"ids": ids},
    ).mappings().all()
    return {int(r["movie_id"]): dict(r) for r in rows}


@router.get("")
def feed_root(user=Depends(get_current_user)):
    return {"ok": True, "user": user.email, "items": []}


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = str(user.id)
    uid_int = user_to_int(user_id)

    # Make sure movies table exists
    ensure_movies_table_seeded(db)

    # ----------------------------
    # Try AI first (always)
    # ----------------------------
    try:
        ai_items = recommend_for_user(user_id=uid_int, limit=limit, offset=offset) or []
        # expected shape: [{"movie_id": 123, "reason": "..."}...]
        ids = []
        for it in ai_items:
            try:
                ids.append(int(it["movie_id"]))
            except Exception:
                continue

        movie_map = fetch_movies_by_ids(db, ids)

        items = []
        for it in ai_items:
            try:
                mid = int(it["movie_id"])
            except Exception:
                continue
            row = movie_map.get(mid)
            if not row:
                continue
            items.append(
                {
                    "movie_id": mid,
                    "title": row.get("title"),
                    "year": safe_year(row.get("release_date")),
                    "poster_url": row.get("poster_url"),
                    "overview": row.get("overview"),
                    "release_date": row.get("release_date"),
                    "reason_chips": [it.get("reason", "ai")],
                }
            )

        # If AI returned usable items -> success
        if items:
            return {
                "user_id": user_id,
                "items": items,
                "next_offset": offset + limit,
                "source": "ai",
            }

    except Exception as e:
        logging.exception("AI recommend_for_user failed: %r", e)
        # if AI crashed mid-transaction, ensure DB is usable
        try:
            db.rollback()
        except Exception:
            pass

    # ----------------------------
    # Fallback: DB feed
    # ----------------------------
    try:
        rows = db.execute(
            text(
                """
                SELECT movie_id, title, poster_url, overview, release_date
                FROM movies
                ORDER BY movie_id
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": limit, "offset": offset},
        ).mappings().all()
    except SQLAlchemyError:
        # In case transaction got aborted earlier
        db.rollback()
        rows = db.execute(
            text(
                """
                SELECT movie_id, title, poster_url, overview, release_date
                FROM movies
                ORDER BY movie_id
                LIMIT :limit OFFSET :offset
                """
            ),
            {"limit": limit, "offset": offset},
        ).mappings().all()

    items = []
    for row in rows:
        items.append(
            {
                "movie_id": int(row["movie_id"]),
                "title": row["title"],
                "year": safe_year(row.get("release_date")),
                "poster_url": row.get("poster_url"),
                "overview": row.get("overview"),
                "release_date": row.get("release_date"),
                "reason_chips": ["DB fallback"],
            }
        )

    return {
        "user_id": user_id,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback",
    }


# ✅ Production-friendly aliases for iOS (backward compatible)
@router.get("/recommendations")
def recommendations_alias(
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return home_feed(limit=limit, offset=offset, user=user, db=db)


@router.get("/activities")
def activities_alias(user=Depends(get_current_user)):
    # If iOS expects this, return a stable response (can be expanded later)
    return {"ok": True, "user": user.email, "activities": []}
