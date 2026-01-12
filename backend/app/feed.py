import csv
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from .auth import get_current_user

# Local AI recommender
from aii.serving.recommender import recommend_for_user


router = APIRouter(
    prefix="/feed",
    tags=["Feed"]
)


# ---------------------------
# Helpers
# ---------------------------

def safe_year(release_date: Optional[str]) -> Optional[int]:
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None


def stable_user_int(user_id_str: str, modulo: int = 10000) -> int:
    """
    UUID / email gibi string user_id -> stabil numeric id
    Aynı kullanıcı her zaman aynı sayıyı alır.
    """
    h = hashlib.sha256(user_id_str.encode("utf-8")).hexdigest()
    n = int(h[:8], 16)
    return (n % modulo) + 1


def ensure_movies_table_seeded(db: Session) -> None:
    """
    movies tablosu yoksa oluşturur
    boşsa CSV'den seed eder
    """

    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
        return
    except OperationalError:
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

    count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    if int(count) > 0:
        return

    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        return

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "movie_id": int(r["movie_id"]),
                    "title": r["title"],
                    "poster_url": None,
                    "overview": None,
                    "release_date": None,
                }
            )

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


# ---------------------------
# Endpoints
# ---------------------------

@router.get("/")
def feed_root(user=Depends(get_current_user)):
    return {
        "ok": True,
        "user": user.email,
        "items": []
    }


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id_str = str(user.id)
    numeric_user_id = stable_user_int(user_id_str)

    ensure_movies_table_seeded(db)

    # ----------------------------
    # AI FIRST (SUNUMDA GÖSTERİLEN KISIM)
    # ----------------------------
    try:
        ai_items = recommend_for_user(
            user_id=numeric_user_id,
            limit=limit,
            offset=offset,
        )

        if ai_items:
            ids = [int(it["movie_id"]) for it in ai_items]

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
                mid = int(it["movie_id"])
                row = movie_map.get(mid)
                if not row:
                    continue

                items.append(
                    {
                        "movie_id": row["movie_id"],
                        "title": row["title"],
                        "year": safe_year(row["release_date"]),
                        "poster_url": row["poster_url"],
                        "overview": row["overview"],
                        "release_date": row["release_date"],
                        "reason_chips": [it.get("reason", "ai")],
                    }
                )

            return {
                "user_id": user_id_str,
                "ai_user_id": numeric_user_id,   # 👈 hocaya göster
                "items": items,
                "next_offset": offset + limit,
                "source": "ai",
            }

    except Exception as e:
        # AI fail → DB fallback
        pass

    # ----------------------------
    # DB FALLBACK
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
                "year": safe_year(row["release_date"]),
                "poster_url": row["poster_url"],
                "overview": row["overview"],
                "release_date": row["release_date"],
                "reason_chips": ["DB fallback (AI skipped/failed)"],
            }
        )

    return {
        "user_id": user_id_str,
        "ai_user_id": numeric_user_id,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback",
    }
