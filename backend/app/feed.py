import csv
from pathlib import Path
from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy import bindparam

from backend.session import get_db
from backend.models.user import User
from backend.app.auth import get_current_user

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
    Ensure movies table exists and seed minimal data if empty.
    NOTE: this should not crash the request if CSV not found.
    """
    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
    except (OperationalError, ProgrammingError):
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

    count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    if int(count) > 0:
        return

    # repo-root/aii/data/processed/movies.csv  (adjust if your path differs)
    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        return

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append(
                    {
                        "movie_id": int(r["movie_id"]),
                        "title": r.get("title") or "",
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


@router.get("")
def feed_root(current_user: User = Depends(get_current_user)):
    # super simple protected endpoint to prove auth works
    return {"ok": True, "user": current_user.email, "items": []}


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_movies_table_seeded(db)

    user_id_str = str(current_user.id)

    # ----------------------------
    # Try AI first (OPTIONAL)
    # ----------------------------
    ai_items = []
    try:
        # IMPORTANT: make AI import optional so Render never dies
        from aii.serving.recommender import recommend_for_user  # type: ignore

        # your AI expects int user_id -> only if digits
        if user_id_str.isdigit():
            ai_items = recommend_for_user(user_id=int(user_id_str), limit=limit, offset=offset) or []
    except Exception:
        ai_items = []

    if ai_items:
        ids = []
        for it in ai_items:
            try:
                ids.append(int(it["movie_id"]))
            except Exception:
                continue

        if ids:
            stmt = (
                text(
                    """
                    SELECT movie_id, title, poster_url, overview, release_date
                    FROM movies
                    WHERE movie_id IN :ids
                    """
                )
                .bindparams(bindparam("ids", expanding=True))
            )

            rows = db.execute(stmt, {"ids": ids}).mappings().all()
            movie_map = {r["movie_id"]: r for r in rows}

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
                "user_id": user_id_str,
                "items": items,
                "next_offset": offset + limit,
                "source": "ai",
            }

    # ----------------------------
    # DB fallback feed
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
                "reason_chips": ["DB fallback"],
            }
        )

    return {
        "user_id": user_id_str,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback",
    }
