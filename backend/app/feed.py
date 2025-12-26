"""
Feed API endpoints for Nuvie Backend.

IMPROVEMENTS:
- Added input validation with Query parameters
- Added response models with Pydantic
- Added proper error handling with specific exceptions
- Added logging for debugging
- Added max limits to prevent abuse
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from backend.session import get_db

from .ai_client import AIServiceError, get_ai_recommendations
from .auth import get_current_user

logger = logging.getLogger(__name__)

# -----------------------
# Configuration
# -----------------------
MAX_LIMIT = 50
MAX_OFFSET = 10000
DEFAULT_LIMIT = 20


# -----------------------
# Response Models
# -----------------------
class ExplanationFactor(BaseModel):
    """Individual explanation factor."""

    type: str
    weight: float
    payload: dict = Field(default_factory=dict)


class Explanation(BaseModel):
    """AI explanation for a recommendation."""

    primary_reason: str
    confidence: float = Field(ge=0, le=1)
    text: str
    factors: List[ExplanationFactor] = Field(default_factory=list)


class FeedItem(BaseModel):
    """Individual movie item in the feed."""

    movie_id: int
    title: Optional[str] = None
    year: Optional[int] = None
    poster_url: Optional[str] = None
    overview: Optional[str] = None
    release_date: Optional[str] = None
    score: Optional[float] = None
    rank: Optional[int] = None
    explanation: Optional[Explanation] = None
    reason_chips: List[str] = Field(default_factory=list)


class FeedResponse(BaseModel):
    """Response model for feed endpoints."""

    user_id: str
    items: List[FeedItem]
    next_offset: int
    total_count: Optional[int] = None
    source: str


# -----------------------
# Router
# -----------------------
router = APIRouter(
    prefix="/feed",
    tags=["Feed"],
)


# -----------------------
# Helper Functions
# -----------------------
def safe_year(release_date: Any) -> Optional[int]:
    """Extract year from release date safely."""
    if not release_date:
        return None
    try:
        year_str = str(release_date)[:4]
        year = int(year_str)
        # Sanity check - movies between 1888 (first film) and 2100
        if 1888 <= year <= 2100:
            return year
        return None
    except (ValueError, TypeError):
        return None


def transform_ai_item(item: dict) -> FeedItem:
    """Transform AI service response item to FeedItem model."""
    explanation = None
    if "explanation" in item:
        exp = item["explanation"]
        explanation = Explanation(
            primary_reason=exp.get("primary_reason", "unknown"),
            confidence=exp.get("confidence", 0.5),
            text=exp.get("text", ""),
            factors=[
                ExplanationFactor(type=f.get("type", ""), weight=f.get("weight", 0), payload=f.get("payload", {}))
                for f in exp.get("factors", [])
            ],
        )

    return FeedItem(
        movie_id=item.get("movie_id", 0),
        title=item.get("title"),
        year=item.get("year"),
        poster_url=item.get("poster_url"),
        overview=item.get("overview"),
        release_date=item.get("release_date"),
        score=item.get("score"),
        rank=item.get("rank"),
        explanation=explanation,
        reason_chips=item.get("reason_chips", []),
    )


# -----------------------
# Endpoints
# -----------------------
@router.get("/home", response_model=FeedResponse)
def home_feed(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Number of items to return (1-50)"),
    offset: int = Query(default=0, ge=0, le=MAX_OFFSET, description="Pagination offset"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedResponse:
    """
    Get personalized movie recommendations for the authenticated user.

    Returns AI-powered recommendations with automatic fallback to database
    if the AI service is unavailable.
    """
    user_id = user["id"]

    # Clamp values for extra safety
    limit = min(max(limit, 1), MAX_LIMIT)
    offset = min(max(offset, 0), MAX_OFFSET)

    # -----------------------
    # Try AI Service First
    # -----------------------
    try:
        logger.info(f"Fetching AI recommendations: user_id={user_id}, limit={limit}, offset={offset}")

        ai_items = get_ai_recommendations(user_id=user_id, limit=limit, offset=offset)

        items = [transform_ai_item(item) for item in ai_items]

        return FeedResponse(user_id=user_id, items=items, next_offset=offset + len(items), source="ai")

    except AIServiceError as e:
        logger.warning(f"AI service error, falling back to DB: {e.message}")

    except Exception as e:
        logger.exception(f"Unexpected error from AI service: {e}")

    # -----------------------
    # Fallback to Database
    # -----------------------
    try:
        logger.info(f"Using DB fallback: user_id={user_id}, limit={limit}, offset={offset}")

        rows = (
            db.execute(
                text(
                    """
                SELECT movie_id, title, poster_url, overview, release_date
                FROM movies
                ORDER BY movie_id
                LIMIT :limit OFFSET :offset
            """
                ),
                {"limit": limit, "offset": offset},
            )
            .mappings()
            .all()
        )

        items = []
        for row in rows:
            items.append(
                FeedItem(
                    movie_id=row["movie_id"],
                    title=row.get("title"),
                    year=safe_year(row.get("release_date")),
                    poster_url=row.get("poster_url"),
                    overview=row.get("overview"),
                    release_date=str(row.get("release_date")) if row.get("release_date") else None,
                    reason_chips=["Popular movies"],
                )
            )

        return FeedResponse(user_id=user_id, items=items, next_offset=offset + len(items), source="db_fallback")

    except SQLAlchemyError as e:
        logger.exception(f"Database error in home_feed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database temporarily unavailable")


@router.get("/trending", response_model=FeedResponse)
def trending_feed(
    limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0, le=MAX_OFFSET),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedResponse:
    """
    Get trending movies based on recent activity.
    """
    user_id = user["id"]

    try:
        rows = (
            db.execute(
                text(
                    """
                SELECT movie_id, title, poster_url, overview, release_date
                FROM movies
                ORDER BY movie_id DESC
                LIMIT :limit OFFSET :offset
            """
                ),
                {"limit": limit, "offset": offset},
            )
            .mappings()
            .all()
        )

        items = []
        for row in rows:
            items.append(
                FeedItem(
                    movie_id=row["movie_id"],
                    title=row.get("title"),
                    year=safe_year(row.get("release_date")),
                    poster_url=row.get("poster_url"),
                    overview=row.get("overview"),
                    release_date=str(row.get("release_date")) if row.get("release_date") else None,
                    reason_chips=["Trending now"],
                )
            )

        return FeedResponse(user_id=user_id, items=items, next_offset=offset + len(items), source="trending")

    except SQLAlchemyError as e:
        logger.exception(f"Database error in trending_feed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database temporarily unavailable")
