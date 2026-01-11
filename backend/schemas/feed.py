from pydantic import BaseModel
from typing import List, Optional

class RecommendationItem(BaseModel):
    movie_id: int
    title: Optional[str] = None
    score: float
    rating_count: Optional[int] = None

class FeedResponse(BaseModel):
    source: str  # "ai" or "db_fallback"
    recommendations: List[RecommendationItem]