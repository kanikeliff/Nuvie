# backend/app/feed.py
import csv
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.session import get_db
from backend.models.user import User
from backend.app.security import decode_token

# AI recommender (senin projedeki import)
from aii.serving.recommender import recommend_for_user


router = APIRouter(prefix="/feed", tags=["Feed"])

bearer_optional = HTTPBearer(auto_error=False)


def user_to_int(user_id: str) -> int:
    # stable 32-bit int from UUID/email etc.
    h = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def safe_year(release_date):
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None


def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_optional),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    If Authorization header exists and token is valid -> return User
    else -> None (public access)
    """
    if not creds:
        return None
    token = creds.credentials
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


def ensure_movies_table_seeded(db: Session) -> None:
    """
    Create movies table if missing + seed from aii/data/processed/movies.csv if empty.
    IMPORTANT: If any query fails, rollback so transaction doesn't stay 'aborted'.
    """
    try:
        # ensure table exists
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

        # if already seeded, skip
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
                        "poster_url": r.get("poster_url"),
                        "overview": r.get("overview"),
                        "release_date": r.get("release_date"),
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

    except SQLAlchemyError:
        db.rollback()
        raise


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


def db_fallback_feed(db: Session, limit: int, offset: int) -> List[Dict[str, Any]]:
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
    return items


def ai_feed_for_user(db: Session, user_key: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    uid_int = user_to_int(user_key)

    ai_items = recommend_for_user(user_id=uid_int, limit=limit, offset=offset)
    # expect: [{"movie_id": 123, "reason": "..."}]

    ids = [int(it["movie_id"]) for it in ai_items if "movie_id" in it]
    movie_map = fetch_movies_by_ids(db, ids)

    items: List[Dict[str, Any]] = []
    for it in ai_items:
        mid = int(it["movie_id"])
        row = movie_map.get(mid)
        if not row:
            continue
        items.append(
            {
                "movie_id": mid,
                "title": row["title"],
                "year": safe_year(row.get("release_date")),
                "poster_url": row.get("poster_url"),
                "overview": row.get("overview"),
                "release_date": row.get("release_date"),
                "reason_chips": [it.get("reason", "AI recommendation")],
            }
        )
    return items


@router.get("")
def feed_root(user: Optional[User] = Depends(get_optional_user)):
    # iOS tarafında bazen /feed çağrılıyor gibi; “ok” dönelim
    return {"ok": True, "user": (user.email if user else None), "items": []}


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    ensure_movies_table_seeded(db)

    # user varsa personalize, yoksa public kullanıcı gibi üret
    user_key = user.id if user else "public-user"

    # 1) AI dene
    try:
        items = ai_feed_for_user(db, user_key=user_key, limit=limit, offset=offset)
        if items:
            return {
                "user_id": str(user_key),
                "items": items,
                "next_offset": offset + limit,
                "source": "ai",
            }
    except Exception as e:
        logging.exception("AI feed failed, falling back to DB")
        # devam -> DB fallback

    # 2) DB fallback
    items = db_fallback_feed(db, limit=limit, offset=offset)
    return {
        "user_id": str(user_key),
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback",
    }


# ✅ iOS’un beklediği path: /feed/recommendations
@router.get("/recommendations")
def recommendations(
    limit: int = 20,
    offset: int = 0,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    # aynı response formatını döndür (iOS bozulmasın)
    return home_feed(limit=limit, offset=offset, user=user, db=db)


# ✅ iOS’un beklediği path: /feed/activities
@router.get("/activities")
def activities(user: Optional[User] = Depends(get_optional_user)):
    # şimdilik basit ama “final ürün” gibi: boş liste döndür
    return {"user": (user.email if user else None), "items": []}
