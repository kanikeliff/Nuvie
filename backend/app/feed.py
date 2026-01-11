"""
Feed API - Home feed with AI recommendations + DB fallback
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db
from backend.app.auth import get_current_user

# Direct AI import (same service - no HTTP calls)
from aii.serving.recommender import recommend_for_user

router = APIRouter(
    prefix="/feed",
    tags=["Feed"]
)


def safe_year(release_date):
    """Extract year safely so API never crashes on missing dates."""
    if not release_date:
        return None
    try:
        return int(str(release_date)[:4])
    except Exception:
        return None


@router.get("/home")
def home_feed(
    limit: int = 20,
    offset: int = 0,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Home feed endpoint.
    1. Try AI recommendations first
    2. If AI fails/empty, fallback to DB popular movies
    """
    # JWT user IDs are usually strings, but IBCF expects int
    # Assuming auth system uses integer user IDs
    try:
        user_id = int(user["id"])
    except (KeyError, TypeError, ValueError):
        # If user_id is UUID/string, this will fail
        # In that case, we need a mapping table
        user_id = None

    # ----------------------------
    # AI First
    # ----------------------------
    try:
        if user_id is not None:
            ai_items = recommend_for_user(
                user_id=user_id,
                limit=limit,
                offset=offset,
            )

            if ai_items:
                # AI gives movie_id -> join with DB for full details
                movie_ids = [it["movie_id"] for it in ai_items]

                rows = db.execute(
                    text("""
                        SELECT movie_id, title, poster_url, overview, release_date
                        FROM movies
                        WHERE movie_id = ANY(:ids)
                    """),
                    {"ids": movie_ids}
                ).mappings().all()

                # Build lookup map
                by_id = {r["movie_id"]: r for r in rows}

                items = []
                for it in ai_items:
                    mid = it["movie_id"]
                    m = by_id.get(mid)
                    if not m:
                        continue
                    items.append({
                        "movie_id": mid,
                        "title": m["title"],
                        "year": safe_year(m.get("release_date")),
                        "poster_url": m["poster_url"],
                        "overview": m["overview"],
                        "release_date": m["release_date"],
                        "ai_score": it.get("ai_score", 50),
                        "social_score": it.get("social_score", 0),
                        "reason_chips": [it.get("reason", "AI recommendation")],
                    })

                return {
                    "user_id": user_id,
                    "items": items,
                    "next_offset": offset + limit,
                    "source": "ai"
                }

        # AI failed or no user_id -> fall through to DB fallback

    except Exception as e:
        # Log error but continue to fallback
        print(f"[feed] AI failed: {repr(e)}")

    # ----------------------------
    # DB Fallback: Popular movies
    # ----------------------------
    rows = db.execute(
        text("""
            SELECT movie_id, title, poster_url, overview, release_date
            FROM movies
            ORDER BY movie_id
            LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset}
    ).mappings().all()

    items = []
    for row in rows:
        items.append({
            "movie_id": row["movie_id"],
            "title": row["title"],
            "year": safe_year(row.get("release_date")),
            "poster_url": row["poster_url"],
            "overview": row["overview"],
            "release_date": row["release_date"],
            "reason_chips": ["DB fallback"],
        })

    return {
        "user_id": user_id,
        "items": items,
        "next_offset": offset + limit,
        "source": "db_fallback"
    }

