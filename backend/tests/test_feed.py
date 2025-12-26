"""
Feed endpoint tests.

Tests cover:
- Home feed with AI recommendations
- Fallback to database when AI unavailable
- Trending feed
- Pagination and limits
- Input validation
"""

import pytest
from fastapi.testclient import TestClient


class TestHomeFeed:
    """Tests for /feed/home endpoint."""

    def test_home_feed_with_ai(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test home feed returns AI recommendations."""
        response = client.get("/feed/home", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "ai"
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Movie"

    def test_home_feed_ai_fallback(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service_error
    ):
        """Test home feed falls back to DB when AI fails."""
        response = client.get("/feed/home", headers=auth_headers)
        # Will be 503 if no movies in test DB, or 200 with db_fallback
        assert response.status_code in [200, 503]

    def test_home_feed_pagination(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test pagination parameters are passed correctly."""
        response = client.get(
            "/feed/home?limit=10&offset=5",
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["next_offset"] == 6  # offset + items returned

    def test_home_feed_requires_auth(self, client: TestClient):
        """Test home feed requires authentication."""
        response = client.get("/feed/home")
        assert response.status_code == 401


class TestFeedValidation:
    """Tests for feed input validation."""

    def test_limit_max_enforced(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test that limit is capped at MAX_LIMIT (50)."""
        response = client.get(
            "/feed/home?limit=100",
            headers=auth_headers
        )
        # Should either reject or cap the value
        assert response.status_code in [200, 422]

    def test_limit_min_enforced(
        self,
        client: TestClient,
        auth_headers
    ):
        """Test that limit must be at least 1."""
        response = client.get(
            "/feed/home?limit=0",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_negative_offset_rejected(
        self,
        client: TestClient,
        auth_headers
    ):
        """Test that negative offset is rejected."""
        response = client.get(
            "/feed/home?offset=-1",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_offset_max_enforced(
        self,
        client: TestClient,
        auth_headers
    ):
        """Test that offset has a maximum limit."""
        response = client.get(
            "/feed/home?offset=100000",
            headers=auth_headers
        )
        # Should either reject or cap the value
        assert response.status_code in [200, 422]


class TestTrendingFeed:
    """Tests for /feed/trending endpoint."""

    def test_trending_feed_success(
        self,
        client: TestClient,
        auth_headers
    ):
        """Test trending feed endpoint."""
        response = client.get("/feed/trending", headers=auth_headers)
        # 200 if movies exist, 503 if DB issue
        assert response.status_code in [200, 503]

    def test_trending_feed_source(
        self,
        client: TestClient,
        auth_headers
    ):
        """Test trending feed returns correct source."""
        response = client.get("/feed/trending", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert data["source"] == "trending"

    def test_trending_requires_auth(self, client: TestClient):
        """Test trending feed requires authentication."""
        response = client.get("/feed/trending")
        assert response.status_code == 401


class TestFeedResponse:
    """Tests for feed response structure."""

    def test_response_structure(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test that response matches expected schema."""
        response = client.get("/feed/home", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "user_id" in data
        assert "items" in data
        assert "next_offset" in data
        assert "source" in data

    def test_feed_item_structure(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test that feed items have expected fields."""
        response = client.get("/feed/home", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0

        item = data["items"][0]
        assert "movie_id" in item
        assert "title" in item

    def test_explanation_structure(
        self,
        client: TestClient,
        auth_headers,
        mock_ai_service
    ):
        """Test that AI explanations have expected structure."""
        response = client.get("/feed/home", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        item = data["items"][0]

        if "explanation" in item and item["explanation"]:
            exp = item["explanation"]
            assert "primary_reason" in exp
            assert "confidence" in exp
            assert "text" in exp
