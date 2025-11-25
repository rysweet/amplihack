"""Tests for JWT authentication system."""

import os
import tempfile
from datetime import timedelta
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

from fastapi.testclient import TestClient

# Set test JWT secret
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"  # pragma: allowlist secret

from amplihack.auth import (
    UserCreate,
    jwt_handler,
)
from examples.jwt_api_example import app


@pytest.fixture if pytest else lambda f: f
def test_user_store():
    """Create a temporary user store for testing."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_file = f.name

    # Create new user store with temp file
    from amplihack.auth.user_store import UserStore

    store = UserStore(storage_path=temp_file)

    yield store

    # Cleanup
    Path(temp_file).unlink(missing_ok=True)


@pytest.fixture if pytest else lambda f: f
def test_client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture if pytest else lambda f: f
def test_user_data():
    """Test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",  # pragma: allowlist secret
        "full_name": "Test User",
    }


@pytest.fixture if pytest else lambda f: f
def admin_user_data():
    """Admin user data."""
    return {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "AdminPass123!",  # pragma: allowlist secret
        "full_name": "Admin User",
    }


class TestJWTHandler:
    """Test JWT handler functionality."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"user_id": "123", "username": "testuser"}
        token = jwt_handler.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Verify token
        payload = jwt_handler.verify_access_token(token)
        assert payload["user_id"] == "123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"user_id": "123", "username": "testuser"}
        token = jwt_handler.create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)

        # Verify token
        payload = jwt_handler.verify_refresh_token(token)
        assert payload["user_id"] == "123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "refresh"

    def test_expired_token(self):
        """Test expired token validation."""
        data = {"user_id": "123"}
        # Create token that expires immediately
        token = jwt_handler.create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(Exception) as exc_info:
            jwt_handler.verify_access_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_invalid_token_type(self):
        """Test token type validation."""
        data = {"user_id": "123"}
        access_token = jwt_handler.create_access_token(data)

        # Try to verify access token as refresh token
        with pytest.raises(Exception) as exc_info:
            jwt_handler.verify_refresh_token(access_token)
        assert "Invalid token type" in str(exc_info.value)


class TestUserStore:
    """Test user store functionality."""

    def test_create_user(self, test_user_store, test_user_data):
        """Test user creation."""
        user_create = UserCreate(**test_user_data)
        user = test_user_store.create_user(user_create)

        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
        assert user.full_name == test_user_data["full_name"]
        assert user.id is not None
        assert user.hashed_password != test_user_data["password"]

    def test_duplicate_username(self, test_user_store, test_user_data):
        """Test duplicate username prevention."""
        user_create = UserCreate(**test_user_data)
        test_user_store.create_user(user_create)

        # Try to create user with same username
        with pytest.raises(ValueError) as exc_info:
            test_user_store.create_user(user_create)
        assert "Username already exists" in str(exc_info.value)

    def test_duplicate_email(self, test_user_store, test_user_data):
        """Test duplicate email prevention."""
        user_create = UserCreate(**test_user_data)
        test_user_store.create_user(user_create)

        # Try to create user with same email but different username
        test_user_data["username"] = "different"
        user_create2 = UserCreate(**test_user_data)
        with pytest.raises(ValueError) as exc_info:
            test_user_store.create_user(user_create2)
        assert "Email already exists" in str(exc_info.value)

    def test_authenticate_user(self, test_user_store, test_user_data):
        """Test user authentication."""
        user_create = UserCreate(**test_user_data)
        created_user = test_user_store.create_user(user_create)

        # Test successful authentication
        user = test_user_store.authenticate_user(
            test_user_data["username"], test_user_data["password"]
        )
        assert user is not None
        assert user.id == created_user.id

        # Test authentication with email
        user = test_user_store.authenticate_user(
            test_user_data["email"], test_user_data["password"]
        )
        assert user is not None

        # Test wrong password
        user = test_user_store.authenticate_user(test_user_data["username"], "wrongpassword")
        assert user is None

        # Test non-existent user
        user = test_user_store.authenticate_user("nonexistent", test_user_data["password"])
        assert user is None


class TestAuthEndpoints:
    """Test authentication API endpoints."""

    def test_register(self, test_client, test_user_data):
        """Test user registration endpoint."""
        response = test_client.post("/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data

    def test_login(self, test_client, test_user_data):
        """Test user login endpoint."""
        # Register user first
        test_client.post("/auth/register", json=test_user_data)

        # Test login
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        }
        response = test_client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, test_client, test_user_data):
        """Test login with wrong password."""
        # Register user first
        test_client.post("/auth/register", json=test_user_data)

        # Test login with wrong password
        login_data = {"username": test_user_data["username"], "password": "wrongpassword"}
        response = test_client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_get_current_user(self, test_client, test_user_data):
        """Test getting current user info."""
        # Register and login
        test_client.post("/auth/register", json=test_user_data)
        login_response = test_client.post(
            "/auth/login",
            json={"username": test_user_data["username"], "password": test_user_data["password"]},
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = test_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    def test_refresh_token(self, test_client, test_user_data):
        """Test token refresh endpoint."""
        # Register and login
        test_client.post("/auth/register", json=test_user_data)
        login_response = test_client.post(
            "/auth/login",
            json={"username": test_user_data["username"], "password": test_user_data["password"]},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = test_client.post("/auth/refresh", params={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


class TestProtectedEndpoints:
    """Test protected API endpoints."""

    def test_protected_route_without_auth(self, test_client):
        """Test accessing protected route without authentication."""
        response = test_client.get("/protected")
        assert response.status_code == 403

    def test_protected_route_with_auth(self, test_client, test_user_data):
        """Test accessing protected route with authentication."""
        # Register and login
        test_client.post("/auth/register", json=test_user_data)
        login_response = test_client.post(
            "/auth/login",
            json={"username": test_user_data["username"], "password": test_user_data["password"]},
        )
        token = login_response.json()["access_token"]

        # Access protected route
        response = test_client.get("/protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()
        assert test_user_data["username"] in data["message"]
        assert "secret_data" in data

    def test_admin_route_without_admin(self, test_client, test_user_data):
        """Test accessing admin route without admin privileges."""
        # Register and login as regular user
        test_client.post("/auth/register", json=test_user_data)
        login_response = test_client.post(
            "/auth/login",
            json={"username": test_user_data["username"], "password": test_user_data["password"]},
        )
        token = login_response.json()["access_token"]

        # Try to access admin route
        response = test_client.get("/admin", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]

    def test_public_route_with_optional_auth(self, test_client, test_user_data):
        """Test public route with optional authentication."""
        # Test without authentication
        response = test_client.get("/public/data")
        assert response.status_code == 200
        data = response.json()
        assert "personalized_message" not in data

        # Register and login
        test_client.post("/auth/register", json=test_user_data)
        login_response = test_client.post(
            "/auth/login",
            json={"username": test_user_data["username"], "password": test_user_data["password"]},
        )
        token = login_response.json()["access_token"]

        # Test with authentication
        response = test_client.get("/public/data", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert "personalized_message" in data
        assert test_user_data["username"] in data["personalized_message"]


class TestPasswordValidation:
    """Test password validation rules."""

    def test_weak_password(self, test_client):
        """Test registration with weak password."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "weak",  # Too short  # pragma: allowlist secret
            "full_name": "Test User",
        }
        response = test_client.post("/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error

    def test_password_no_digit(self, test_client):
        """Test password without digit."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "NoDigitHere!",  # No digit  # pragma: allowlist secret
            "full_name": "Test User",
        }
        response = test_client.post("/auth/register", json=user_data)
        assert response.status_code == 422

    def test_password_no_uppercase(self, test_client):
        """Test password without uppercase."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "nouppercase123!",  # No uppercase  # pragma: allowlist secret
            "full_name": "Test User",
        }
        response = test_client.post("/auth/register", json=user_data)
        assert response.status_code == 422
