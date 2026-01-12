import csv
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from .auth import get_current_user

router = APIRouter(prefix="/feed", tags=["Feed"])

def safe_year(release_date):
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None

def ensure_movies_table_seeded(db: Session) -> None:
    # 1) Table exists?
    try:
        db.execute(text("SELECT 1 FROM movies LIMIT 1"))
    except OperationalError:
        # IMPORTANT: rollback aborted transaction
        db.rollback()

        db.execute(text("""
            CREATE TABLE IF NOT EXISTS movies (
                movie_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                poster_url TEXT,
                overview TEXT,
                release_date TEXT
            )
        """))
        db.commit()

    # 2) Seed only if empty
    try:
        count = db.execute(text("SELECT COUNT(*) FROM movies")).scalar() or 0
    except Exception:
        db.rollback()
        return

    if int(count) > 0:
        return

    csv_path = Path(__file__).resolve().parents[2] / "aii" / "data" / "processed" / "movies.csv"
    if not csv_path.exists():
        return

    try:
        rows = []
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append({
                    "movie_id": int(r["movie_id"]),
                    "title": r["title"],
                    "poster_url": r.get("poster_url"),
                    "overview": r.get("overview"),
                    "release_date": r.get("release_date"),
                })

        if rows:
            db.execute(text("""
                INSERT INTO movies (movie_id, title, poster_url, overview, release_date)
                VALUES (:movie_id, :title, :poster_url, :overview, :release_date)
            """), rows)
            db.commit()

    except Exception:
        db.rollback()
        return

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

    rows = db.execute(text("""
        SELECT movie_id, title, poster_url, overview, release_date
        FROM movies
        ORDER BY movie_id
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).mappings().all()

    items = []
    for row in rows:
        items.append({
            "movie_id": row["movie_id"],
            "title": row["title"],
            "year": safe_year(row.get("release_date")),
            "poster_url": row.get("poster_url"),
            "overview": row.get("overview"),
            "release_date": row.get("release_date"),
            "reason_chips": ["DB fallback (AI not wired yet)"]
        })

    return {
        "user_id": user_id,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback"
    }
