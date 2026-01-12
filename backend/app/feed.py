import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from .auth import get_current_user

# Local AI recommender (Phase 3)
from aii.serving.recommender import recommend_for_user


router = APIRouter(prefix="/feed", tags=["Feed"])


def safe_year(release_date: Optional[str]) -> Optional[int]:
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None


def ensure_movies_table_seeded(db: Session) -> None:
    """
    Ensure the `movies` table exists.
    If it's empty, try to seed from aii/data/processed/movies.csv.
    Important: rollback after a failed query to avoid 'transaction is aborted' errors.
    """

    # 1) Check if table exists by querying it
    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
        table_exists = True
    except (OperationalError, ProgrammingError):
        table_exists = False
        # IMPORTANT: any DB error inside a transaction can abort it
        db.rollback()

    # 2) Create table if missing
    if not table_exists:
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

    # 3) If table already has rows, we are done
    try:
        count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    except (OperationalError, ProgrammingError):
        db.rollback()
        count = 0

    if int(count) > 0:
        return

    # 4) Try seed from CSV (optional)
    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        # No seed file available; leave empty without crashing
        return

    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # minimal columns for demo
            try:
                rows.append(
                    {
                        "movie_id": int(r["movie_id"]),
                        "title": r.get("title") or "Unknown",
                        "poster_url": r.get("poster_url"),   # if csv has it
                        "overview": r.get("overview"),       # if csv has it
                        "release_date": r.get("release_date") or r.get("release"),
                    }
                )
            except Exception:
                # skip bad row
                continue

    if not rows:
        return

    # Insert rows
    try:
        db.execute(
            text(
                """
                INSERT INTO movies (movie_id, title, poster_url, overview, release_date)
                VALUES (:movie_id, :title, :poster_url, :overview, :release_date)
                ON CONFLICT (movie_id) DO NOTHING
                """
            ),
            rows,
        )
        db.commit()
    except (OperationalError, ProgrammingError):
        db.rollback()


@router.get("/")
def feed_root(user=Depends(get_current_user)):
    # simple protected endpoint sanity check
    return {"ok": True, "user": user.email, "items": []}


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns feed items.
    - Ensures movies table exists (and optionally seeded)
    - Tries AI first (only if user_id is numeric; otherwise fallback)
    - Falls back to DB list
    """

    # Make sure DB has movies table
    ensure_movies_table_seeded(db)

    user_id = str(getattr(user, "id", ""))

    # ----------------------------
    # Phase 3: AI first (only if numeric user_id)
    # ----------------------------
    if user_id.isdigit():
        try:
            ai_items = recommend_for_user(user_id=int(user_id), limit=limit, offset=offset)

            if ai_items:
                ids = [int(it["movie_id"]) for it in ai_items if str(it.get("movie_id", "")).isdigit()]
                if ids:
                    # PostgreSQL "IN :ids" needs tuple + parentheses
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

                    movie_map = {r["movie_id"]: r for r in rows}

                    items = []
                    for it in ai_items:
                        mid = it.get("movie_id")
                        if not str(mid).isdigit():
                            continue
                        mid = int(mid)
                        row = movie_map.get(mid)
                        if not row:
                            continue

                        items.append(
                            {
                                "movie_id": row["movie_id"],
                                "title": row["title"],
                                "year": safe_year(row.get("release_date")),
                                "poster_url": row.get("poster_url"),
                                "overview": row.get("overview"),
                                "release_date": row.get("release_date"),
                                "reason_chips": [it.get("reason", "ai")],
                            }
                        )

                    return {
                        "user_id": user_id,
                        "items": items,
                        "next_offset": offset + limit,
                        "source": "ai",
                    }
        except Exception:
            # AI fails -> fallback to DB
            pass

    # ----------------------------
    # Phase 2 fallback: DB feed
    # ----------------------------
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
                "movie_id": row["movie_id"],
                "title": row["title"],
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
    }
