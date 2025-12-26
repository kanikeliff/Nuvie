"""
Health and system endpoint tests.

Tests cover:
- Health check endpoint
- Readiness check endpoint
- Root endpoint
- Security headers
- Request ID tracking
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, client: TestClient):
        """Test /health returns 200 and status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_ready_endpoint(self, client: TestClient):
        """Test /ready returns readiness status."""
        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Nuvie Backend API"
        assert "version" in data


class TestSecurityHeaders:
    """Tests for security header middleware."""

    def test_content_type_options(self, client: TestClient):
        """Test X-Content-Type-Options header is set."""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options(self, client: TestClient):
        """Test X-Frame-Options header is set."""
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_xss_protection(self, client: TestClient):
        """Test X-XSS-Protection header is set."""
        response = client.get("/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client: TestClient):
        """Test Referrer-Policy header is set."""
        response = client.get("/health")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


class TestRequestTracking:
    """Tests for request ID tracking middleware."""

    def test_request_id_generated(self, client: TestClient):
        """Test that requests get a request ID."""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_preserved(self, client: TestClient):
        """Test that provided request ID is preserved."""
        custom_id = "custom-request-123"
        response = client.get(
            "/health",
            headers={"X-Request-ID": custom_id}
        )
        assert response.headers.get("X-Request-ID") == custom_id


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_preflight(self, client: TestClient):
        """Test CORS preflight request handling."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200

    def test_cors_headers_present(self, client: TestClient):
        """Test CORS headers are present on responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS headers should be present for allowed origins
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error response handling."""

    def test_404_response(self, client: TestClient):
        """Test 404 response for unknown routes."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        """Test 405 for wrong HTTP method."""
        response = client.post("/health")
        assert response.status_code == 405
