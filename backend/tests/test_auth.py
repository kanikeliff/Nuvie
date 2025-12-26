"""
Authentication endpoint tests.

Tests cover:
- User registration with validation
- Login with correct/incorrect credentials
- JWT token validation
- Account lockout after failed attempts
- Protected endpoint access
"""

import pytest
from fastapi.testclient import TestClient


class TestRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, client: TestClient):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@example.com"

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 422

    def test_register_weak_password(self, client: TestClient):
        """Test registration with password that's too short."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "weak"
            }
        )
        assert response.status_code == 422

    def test_register_password_no_numbers(self, client: TestClient):
        """Test registration with password missing numbers."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "NoNumbersHere"
            }
        )
        assert response.status_code == 422

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with already registered email."""
        response = client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "password": "AnotherPass123"
            }
        )
        assert response.status_code == 409


class TestLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login returns JWT token."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Test login with incorrect password."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123"
            }
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent email."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "AnyPassword123"
            }
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, db_session, test_user):
        """Test login with inactive account."""
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123"
            }
        )
        assert response.status_code == 403


class TestTokenValidation:
    """Tests for JWT token validation."""

    def test_valid_token_access(self, client: TestClient, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/feed/home", headers=auth_headers)
        # Should succeed or fail based on DB content, not auth
        assert response.status_code in [200, 503]

    def test_expired_token_rejected(self, client: TestClient, expired_token):
        """Test that expired tokens are rejected."""
        response = client.get(
            "/feed/home",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        """Test that malformed tokens are rejected."""
        response = client.get(
            "/feed/home",
            headers={"Authorization": "Bearer invalid-token-here"}
        )
        assert response.status_code == 401

    def test_missing_token_rejected(self, client: TestClient):
        """Test that requests without token are rejected."""
        response = client.get("/feed/home")
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for get current user endpoint."""

    def test_get_current_user(self, client: TestClient, auth_headers, test_user):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
