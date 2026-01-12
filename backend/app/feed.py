import csv
import hashlib
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from .auth import get_current_user

# AI recommender (local module)
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
    Stable int from UUID/email etc.
    We convert to 32-bit int using sha256 -> first 8 hex chars.
    """
    h = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def ensure_movies_table_seeded(db: Session) -> None:
    """
    Ensure `movies` table exists and has at least basic rows.
    Creates table if missing and seeds from aii/data/processed/movies.csv if available.
    """
    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
        db.commit()
    except OperationalError:
        db.rollback()
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

    # If already has rows, done
    count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    if int(count) > 0:
        return

    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        # No seed file available; leave empty but don't crash requests
        return

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # movie_id + title is enough for demo
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
    """
    Returns a dict: movie_id -> row mappings
    """
    if not ids:
        return {}

    # Use tuple for IN
    rows = db.execute(
        text(
            """
            SELECT movie_id, title, poster_url, overview, release_date
            FROM movies
            WHERE movie_id IN :ids
            """
        ),
        {"ids": tuple(ids)},
    ).mappings().all()

    return {int(r["movie_id"]): dict(r) for r in rows}


@router.get("/")
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
    ensure_movies_table_seeded(db)

    # ---------- AI PATH ----------
    # Convert UUID/email user_id to stable int -> call AI model for recommendations
    uid_int = user_to_int(user_id)

    try:
        ai_items = recommend_for_user(user_id=uid_int, limit=limit, offset=offset)

        # ai_items expected like: [{"movie_id": 123, "reason": "..."}...]
        if ai_items:
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

            # If AI returned movie_ids but DB lacked details, still fall back
            if items:
                return {
                    "user_id": user_id,
                    "items": items,
                    "next_offset": offset + limit,
                    "source": "ai",
                    "ai_user_int": uid_int,  # demo için debug (istersen kaldır)
                }

    except Exception as e:
        logging.exception("AI recommend_for_user failed, falling back to DB. Error=%s", repr(e))
        # IMPORTANT: rollback if any DB transaction got upset
        try:
            db.rollback()
        except Exception:
            pass

    # ---------- DB FALLBACK ----------
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
                "title": row.get("title"),
                "year": safe_year(row.get("release_date")),
                "poster_url": row.get("poster_url"),
                "overview": row.get("overview"),
                "release_date": row.get("release_date"),
                "reason_chips": ["DB fallback (AI skipped/failed)"],
            }
        )

    return {
        "user_id": user_id,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback",
        "ai_user_int": uid_int,  # demo için debug (istersen kaldır)
    }


# iOS'ın çağırdığı path'ler varsa, map edelim (Not Found olmasın)
@router.get("/recommendations")
def recommendations(
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return home_feed(limit=limit, offset=offset, user=user, db=db)


@router.get("/activities")
def activities(user=Depends(get_current_user)):
    return {"user": user.email, "items": []}
