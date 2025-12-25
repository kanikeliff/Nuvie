import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# I create a Base class for SQLAlchemy models
# so all models can inherit from it
Base = declarative_base()

logger = logging.getLogger(__name__)

# I read DATABASE_URL from environment variables
# For local development, fall back to a SQLite file when not provided
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL is not set, falling back to sqlite:///./dev.db for local development")
    DATABASE_URL = "sqlite:///./dev.db"

# I create the SQLAlchemy engine using the database URL
# Use sqlite-specific connect args when needed and keep pool_pre_ping
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# I create a database session factory
# I disable autocommit and autoflush for safer transaction control
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# I provide a database session for each request
# and I make sure it is always closed after use
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
