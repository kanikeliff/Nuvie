from pydantic import BaseModel
from typing import Optional

class MovieBase(BaseModel):
    movie_id: int
    title: str
    genres: Optional[str]

class MovieCreate(MovieBase):
    pass

class Movie(MovieBase):
    class Config:
        from_attributes = True