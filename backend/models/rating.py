from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Rating(Base):
    __tablename__ = "ratings"

    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.movie_id"), primary_key=True)
    rating = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)