from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class RecommendationFeed(Base):
    __tablename__ = "recommendation_feed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    movie_ids = Column(Text)  # JSON string of recommended movie IDs
    algorithm = Column(String(50))  # 'ibcf', 'content', 'hybrid', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # when this recommendation expires