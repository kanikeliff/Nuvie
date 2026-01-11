from sqlalchemy import Column, Integer, DateTime, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class WatchEvent(Base):
    __tablename__ = "watch_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    movie_id = Column(Integer, ForeignKey("movies.movie_id"))
    event_type = Column(String(50))  # 'watched', 'liked', 'disliked', etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration = Column(Integer)  # watch duration in seconds, optional