"""
AI Router for FastAPI - Single service deployment
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from aii.serving.recommender import recommend_for_user, ai_status

router = APIRouter(prefix="/ai", tags=["AI"])


class RecommendIn(BaseModel):
    user_id: int
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


@router.get("/health")
def health():
    """Health check endpoint for AI service."""
    return {"ok": True, **ai_status()}


@router.post("/recommend")
def recommend(body: RecommendIn):
    """
    Get AI recommendations for a user.
    Returns list of movie_id + AI scores.
    """
    items = recommend_for_user(
        user_id=body.user_id,
        limit=body.limit,
        offset=body.offset,
    )
    return {"user_id": body.user_id, "items": items}

