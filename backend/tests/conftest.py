"""
Pytest configuration and fixtures for Nuvie backend tests.

Provides:
- Test database setup with SQLite in-memory
- Test client for API integration tests
- Authentication fixtures for protected endpoints
- Mock fixtures for external services
"""

import os
import pytest
from typing import Generator, Dict, Any
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["ENVIRONMENT"] = "testing"

from backend.session import Base, get_db
from backend.app.main import app
from backend.models.user import User


# -----------------------
# Database Fixtures
# -----------------------

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using SQLite in-memory."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -----------------------
# User Fixtures
# -----------------------

@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user in the database."""
    from passlib.hash import bcrypt

    user = User(
        id="test-user-123",
        email="test@example.com",
        password_hash=bcrypt.hash("TestPassword123"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Generate a valid JWT token for the test user."""
    from jose import jwt

    payload = {
        "sub": test_user.id,
        "email": test_user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


@pytest.fixture
def auth_headers(test_user_token: str) -> Dict[str, str]:
    """Return authorization headers with valid token."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def expired_token(test_user: User) -> str:
    """Generate an expired JWT token for testing."""
    from jose import jwt

    payload = {
        "sub": test_user.id,
        "email": test_user.email,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


# -----------------------
# Mock Fixtures
# -----------------------

@pytest.fixture
def mock_ai_service():
    """Mock the AI recommendation service."""
    with patch("backend.app.ai_client.get_ai_recommendations") as mock:
        mock.return_value = [
            {
                "movie_id": 1,
                "title": "Test Movie",
                "year": 2023,
                "poster_url": "https://example.com/poster.jpg",
                "score": 0.95,
                "rank": 1,
                "explanation": {
                    "primary_reason": "genre_match",
                    "confidence": 0.9,
                    "text": "Based on your love of sci-fi",
                    "factors": []
                },
                "reason_chips": ["Sci-Fi", "Highly Rated"]
            }
        ]
        yield mock


@pytest.fixture
def mock_ai_service_error():
    """Mock AI service to raise an error."""
    from backend.app.ai_client import AIServiceError

    with patch("backend.app.ai_client.get_ai_recommendations") as mock:
        mock.side_effect = AIServiceError("Service unavailable", status_code=503)
        yield mock


# -----------------------
# Sample Data Fixtures
# -----------------------

@pytest.fixture
def sample_movie_data() -> Dict[str, Any]:
    """Sample movie data for testing."""
    return {
        "movie_id": 550,
        "title": "Fight Club",
        "year": 1999,
        "poster_url": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "overview": "A ticking-Loss time bomb of a movie.",
        "release_date": "1999-10-15",
        "genres": ["Drama", "Thriller"],
        "rating": 8.4,
    }


@pytest.fixture
def sample_recommendations() -> list:
    """Sample recommendation list for testing."""
    return [
        {
            "movie_id": 1,
            "title": "The Matrix",
            "year": 1999,
            "score": 0.95,
            "reason_chips": ["Sci-Fi Classic"]
        },
        {
            "movie_id": 2,
            "title": "Inception",
            "year": 2010,
            "score": 0.92,
            "reason_chips": ["Mind-Bending"]
        },
    ]
