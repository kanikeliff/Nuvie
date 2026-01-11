from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
import os
from ..session import get_db
from ..models.movie import Movie
from ..models.rating import Rating
from ..schemas.feed import FeedResponse, RecommendationItem

router = APIRouter()

AI_BASE_URL = os.getenv("AI_BASE_URL", "http://localhost:8001")

@router.get("/home", response_model=FeedResponse)
def get_home_feed(user_id: int = 1, db: Session = Depends(get_db)):
    """
    Get personalized home feed for user.
    First try AI service, fallback to database recommendations.
    """
    try:
        # Try AI service first
        ai_response = requests.post(
            f"{AI_BASE_URL}/ai/recommend",
            json={
                "request_id": f"feed-{user_id}",
                "user_id": user_id,
                "limit": 20,
                "offset": 0,
                "exclude_movie_ids": [],
                "context": {
                    "use_social": True,
                    "seed_movie_ids": [],
                    "locale": "en-US"
                }
            },
            headers={"X-Internal-Token": os.getenv("AI_INTERNAL_TOKEN", "dev-internal-token")},
            timeout=5
        )

        if ai_response.status_code == 200:
            ai_data = ai_response.json()
            recommendations = ai_data.get("recommendations", [])
            return FeedResponse(
                source="ai",
                recommendations=[RecommendationItem(**rec) for rec in recommendations]
            )

    except Exception as e:
        print(f"AI service failed: {e}")

    # DB fallback: Get popular movies based on ratings
    try:
        popular_movies = db.query(
            Movie.movie_id,
            Movie.title,
            db.func.avg(Rating.rating).label('avg_rating'),
            db.func.count(Rating.rating).label('rating_count')
        ).join(Rating).group_by(Movie.movie_id, Movie.title)\
         .having(db.func.count(Rating.rating) >= 10)\
         .order_by(db.func.avg(Rating.rating).desc())\
         .limit(20).all()

        recommendations = [
            {
                "movie_id": movie.movie_id,
                "title": movie.title,
                "score": float(movie.avg_rating),
                "rating_count": movie.rating_count
            }
            for movie in popular_movies
        ]

        return FeedResponse(
            source="db_fallback",
            recommendations=recommendations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

