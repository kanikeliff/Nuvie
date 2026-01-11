from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# I create a Base class for SQLAlchemy models
# so all models can inherit from it
Base = declarative_base()

# I read DATABASE_URL from environment variables
# because I never want database credentials inside the codebase
DATABASE_URL = os.getenv("DATABASE_URL")

# I fail fast if DATABASE_URL is missing
# because it is better to crash early than debug silent DB errors
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# I create the SQLAlchemy engine using the database URL
# pool_pre_ping=True helps me avoid broken or stale connections
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
