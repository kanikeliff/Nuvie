from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RatingBase(BaseModel):
    user_id: int
    movie_id: int
    rating: float
    timestamp: Optional[datetime]

class RatingCreate(RatingBase):
    pass

class Rating(RatingBase):
    class Config:
        from_attributes = True