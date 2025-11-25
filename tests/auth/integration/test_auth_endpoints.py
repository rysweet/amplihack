"""
Integration tests for authentication API endpoints.
These tests follow TDD approach and should fail initially.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import json
import time
from typing import Dict, Any

# Import the application (doesn't exist yet - TDD approach)
from src.amplihack.auth.app import create_app
from src.amplihack.auth.database import get_db, Base
from src.amplihack.auth.models import User
from src.amplihack.auth.config import get_settings


class TestAuthEndpoints:
    """Integration tests for authentication endpoints."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app(testing=True)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_user_data(self):
        """Test user registration data."""
        return {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestP@ssw0rd123!",
            "first_name": "Test",
            "last_name": "User",
        }

    @pytest.fixture
    def registered_user(self, client, test_user_data):
        """Register a test user and return credentials."""
        response = client.post("/api/auth/register", json=test_user_data)
        return {
            **test_user_data,
            "user_id": response.json().get("user_id"),
        }

    def test_register_endpoint_success(self, client, test_user_data):
        """Test successful user registration via API."""
        response = client.post("/api/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "password" not in data  # Password should not be returned
        assert "password_hash" not in data

    def test_register_endpoint_duplicate_email(self, client, test_user_data):
        """Test registration fails with duplicate email."""
        # First registration
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 201

        # Attempt duplicate registration
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 409  # Conflict
        assert "already registered" in response.json()["detail"].lower()

    def test_register_endpoint_invalid_email(self, client):
        """Test registration fails with invalid email format."""
        data = {
            "email": "notanemail",
            "username": "testuser",
            "password": "TestP@ssw0rd123!",
        }

        response = client.post("/api/auth/register", json=data)
        assert response.status_code == 422  # Unprocessable Entity
        assert "invalid email" in response.json()["detail"].lower()

    def test_register_endpoint_weak_password(self, client):
        """Test registration fails with weak password."""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",
        }

        response = client.post("/api/auth/register", json=data)
        assert response.status_code == 422
        assert "password" in response.json()["detail"].lower()

    def test_login_endpoint_success(self, client, registered_user):
        """Test successful login via API."""
        login_data = {
            "email": registered_user["email"],
            "password": registered_user["password"],
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "Bearer"
        assert "expires_in" in data

    def test_login_endpoint_with_username(self, client, registered_user):
        """Test login with username instead of email."""
        login_data = {
            "username": registered_user["username"],
            "password": registered_user["password"],
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_endpoint_invalid_credentials(self, client, registered_user):
        """Test login fails with invalid credentials."""
        login_data = {
            "email": registered_user["email"],
            "password": "WrongPassword123!",
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401  # Unauthorized
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_endpoint_nonexistent_user(self, client):
        """Test login fails for non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestP@ssw0rd123!",
        }

        response = client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_refresh_endpoint_success(self, client, registered_user):
        """Test successful token refresh via API."""
        # First login to get tokens
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        tokens = login_response.json()

        # Refresh tokens
        refresh_data = {
            "refresh_token": tokens["refresh_token"],
        }

        response = client.post("/api/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != tokens["access_token"]  # New access token
        assert data["refresh_token"] != tokens["refresh_token"]  # New refresh token

    def test_refresh_endpoint_invalid_token(self, client):
        """Test refresh fails with invalid token."""
        refresh_data = {
            "refresh_token": "invalid_refresh_token_123",
        }

        response = client.post("/api/auth/refresh", json=refresh_data)

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_endpoint_reused_token(self, client, registered_user):
        """Test refresh fails when reusing old refresh token."""
        # Login to get tokens
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        tokens = login_response.json()

        # First refresh (succeeds)
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response1 = client.post("/api/auth/refresh", json=refresh_data)
        assert response1.status_code == 200

        # Try to reuse the same refresh token (should fail)
        response2 = client.post("/api/auth/refresh", json=refresh_data)
        assert response2.status_code == 401
        assert "token rotation violation" in response2.json()["detail"].lower()

    def test_logout_endpoint_success(self, client, registered_user):
        """Test successful logout via API."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        tokens = login_response.json()

        # Logout with access token
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post("/api/auth/logout", headers=headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Verify token is no longer valid
        protected_response = client.get("/api/auth/me", headers=headers)
        assert protected_response.status_code == 401

    def test_logout_endpoint_without_token(self, client):
        """Test logout fails without authentication token."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_protected_endpoint_with_valid_token(self, client, registered_user):
        """Test accessing protected endpoint with valid token."""
        # Login to get token
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        token = login_response.json()["access_token"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == registered_user["email"]
        assert data["username"] == registered_user["username"]

    def test_protected_endpoint_without_token(self, client):
        """Test protected endpoint requires authentication."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test protected endpoint rejects invalid token."""
        headers = {"Authorization": "Bearer invalid_token_123"}
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_protected_endpoint_with_expired_token(self, client):
        """Test protected endpoint rejects expired token."""
        # Create an expired token
        with patch('src.amplihack.auth.services.TokenService.generate_access_token') as mock_generate:
            # Generate token that expires immediately
            mock_generate.return_value = "expired_token_123"

            headers = {"Authorization": "Bearer expired_token_123"}
            response = client.get("/api/auth/me", headers=headers)

            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()

    def test_change_password_endpoint(self, client, registered_user):
        """Test password change via API."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        token = login_response.json()["access_token"]

        # Change password
        headers = {"Authorization": f"Bearer {token}"}
        change_data = {
            "current_password": registered_user["password"],
            "new_password": "NewP@ssw0rd456!",
        }

        response = client.post("/api/auth/change-password", json=change_data, headers=headers)
        assert response.status_code == 200

        # Verify old password no longer works
        old_login = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert old_login.status_code == 401

        # Verify new password works
        new_login = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "NewP@ssw0rd456!",
        })
        assert new_login.status_code == 200

    def test_forgot_password_endpoint(self, client, registered_user):
        """Test password reset request via API."""
        reset_data = {
            "email": registered_user["email"],
        }

        response = client.post("/api/auth/forgot-password", json=reset_data)

        assert response.status_code == 200
        assert "reset link sent" in response.json()["message"].lower()

    def test_reset_password_endpoint(self, client, registered_user):
        """Test password reset with token via API."""
        # Request reset token
        reset_request = client.post("/api/auth/forgot-password", json={
            "email": registered_user["email"],
        })

        # In real app, token would be sent via email
        # For testing, we'll mock getting the token
        with patch('src.amplihack.auth.services.PasswordResetService.get_reset_token') as mock_token:
            mock_token.return_value = "reset_token_123"

            # Reset password with token
            reset_data = {
                "token": "reset_token_123",
                "new_password": "ResetP@ssw0rd789!",
            }

            response = client.post("/api/auth/reset-password", json=reset_data)
            assert response.status_code == 200

            # Verify new password works
            login_response = client.post("/api/auth/login", json={
                "email": registered_user["email"],
                "password": "ResetP@ssw0rd789!",
            })
            assert login_response.status_code == 200

    def test_verify_email_endpoint(self, client, test_user_data):
        """Test email verification via API."""
        # Register user
        register_response = client.post("/api/auth/register", json=test_user_data)
        assert register_response.status_code == 201

        # In real app, verification token would be sent via email
        with patch('src.amplihack.auth.services.EmailVerificationService.get_verification_token') as mock_token:
            mock_token.return_value = "verify_token_123"

            # Verify email with token
            response = client.get(f"/api/auth/verify-email?token=verify_token_123")
            assert response.status_code == 200
            assert "email verified" in response.json()["message"].lower()

    def test_resend_verification_email(self, client, registered_user):
        """Test resending verification email via API."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/auth/resend-verification", headers=headers)

        assert response.status_code == 200
        assert "verification email sent" in response.json()["message"].lower()

    def test_user_profile_update(self, client, registered_user):
        """Test user profile update via API."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        token = login_response.json()["access_token"]

        # Update profile
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "+1234567890",
        }

        response = client.patch("/api/auth/profile", json=update_data, headers=headers)
        assert response.status_code == 200

        # Verify changes
        profile_response = client.get("/api/auth/me", headers=headers)
        profile = profile_response.json()
        assert profile["first_name"] == "Updated"
        assert profile["last_name"] == "Name"
        assert profile["phone"] == "+1234567890"

    def test_delete_account_endpoint(self, client, registered_user):
        """Test account deletion via API."""
        # Login first
        login_response = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        token = login_response.json()["access_token"]

        # Delete account
        headers = {"Authorization": f"Bearer {token}"}
        delete_data = {
            "password": registered_user["password"],  # Confirm with password
            "confirm": True,
        }

        response = client.delete("/api/auth/account", json=delete_data, headers=headers)
        assert response.status_code == 200
        assert "account deleted" in response.json()["message"].lower()

        # Verify account no longer exists
        login_attempt = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert login_attempt.status_code == 401