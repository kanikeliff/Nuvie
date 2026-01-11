import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# I read DATABASE_URL from env so secrets never live in the codebase
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import all models to ensure they are registered with Base
from .models.user import Base as UserBase
from .models.movie import Base as MovieBase
from .models.rating import Base as RatingBase
from .models.watch_event import Base as WatchEventBase
from .models.recommendation_feed import Base as RecommendationFeedBase

# Create all tables
def create_tables():
    UserBase.metadata.create_all(bind=engine)
    MovieBase.metadata.create_all(bind=engine)
    RatingBase.metadata.create_all(bind=engine)
    WatchEventBase.metadata.create_all(bind=engine)
    RecommendationFeedBase.metadata.create_all(bind=engine)

def get_db():
    # I create one DB session per request and close it safely
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
