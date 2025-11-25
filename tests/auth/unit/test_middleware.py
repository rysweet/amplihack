"""
Unit tests for authentication middleware and route protection.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
from typing import Optional, List

# Import the modules to be tested
from src.amplihack.auth.middleware import (
    AuthMiddleware,
    require_auth,
    require_role,
    require_permission,
)
from src.amplihack.auth.models import User, TokenPayload
from src.amplihack.auth.exceptions import (
    InvalidCredentialsError,
    InsufficientPermissionsError,
    TokenExpiredError,
)


class TestJWTAuthMiddleware:
    """Test JWT authentication middleware."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application."""
        app = FastAPI()

        # Add middleware
        app.add_middleware(
            AuthMiddleware,
            secret_key="test_secret",
            algorithm="HS256",
            exclude_paths=["/api/auth/login", "/api/auth/register"],
        )

        @app.get("/protected")
        async def protected_route():
            return {"message": "Protected content"}

        @app.get("/api/auth/login")
        async def login():
            return {"message": "Login endpoint"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_middleware_allows_excluded_paths(self, client):
        """Test middleware allows access to excluded paths without token."""
        response = client.get("/api/auth/login")
        assert response.status_code == 200
        assert response.json()["message"] == "Login endpoint"

    def test_middleware_blocks_protected_routes(self, client):
        """Test middleware blocks protected routes without token."""
        response = client.get("/protected")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_middleware_allows_with_valid_token(self, client):
        """Test middleware allows access with valid token."""
        with patch('src.amplihack.auth.middleware.TokenService') as mock_service:
            mock_service.return_value.validate_token.return_value = TokenPayload(
                user_id="user_123",
                email="user@example.com",
            )

            headers = {"Authorization": "Bearer valid_token_123"}
            response = client.get("/protected", headers=headers)

            assert response.status_code == 200
            assert response.json()["message"] == "Protected content"

    def test_middleware_rejects_invalid_token(self, client):
        """Test middleware rejects invalid token."""
        with patch('src.amplihack.auth.middleware.TokenService') as mock_service:
            mock_service.return_value.validate_token.side_effect = Exception("Invalid token")

            headers = {"Authorization": "Bearer invalid_token_123"}
            response = client.get("/protected", headers=headers)

            assert response.status_code == 401

    def test_middleware_rejects_expired_token(self, client):
        """Test middleware rejects expired token."""
        with patch('src.amplihack.auth.middleware.TokenService') as mock_service:
            mock_service.return_value.validate_token.side_effect = TokenExpiredError("Token expired")

            headers = {"Authorization": "Bearer expired_token_123"}
            response = client.get("/protected", headers=headers)

            assert response.status_code == 401
            assert "token expired" in response.json()["detail"].lower()

    def test_middleware_handles_malformed_header(self, client):
        """Test middleware handles malformed authorization header."""
        test_cases = [
            {"Authorization": "InvalidFormat"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer token1 token2"},
            {"Authorization": "Basic dXNlcjpwYXNz"},  # Wrong scheme
        ]

        for headers in test_cases:
            response = client.get("/protected", headers=headers)
            assert response.status_code == 401

    def test_middleware_case_insensitive_bearer(self, client):
        """Test middleware handles case variations in Bearer scheme."""
        with patch('src.amplihack.auth.middleware.TokenService') as mock_service:
            mock_service.return_value.validate_token.return_value = TokenPayload(
                user_id="user_123",
            )

            test_cases = ["Bearer", "bearer", "BEARER", "BeArEr"]

            for scheme in test_cases:
                headers = {"Authorization": f"{scheme} token_123"}
                response = client.get("/protected", headers=headers)
                assert response.status_code == 200


class TestAuthDependencies:
    """Test authentication dependencies for route protection."""

    @pytest.fixture
    def mock_token_service(self):
        """Create mock token service."""
        service = Mock()
        service.validate_token.return_value = TokenPayload(
            user_id="user_123",
            email="user@example.com",
            roles=["user"],
            permissions=["read:profile"],
        )
        return service

    @pytest.fixture
    def mock_user_service(self):
        """Create mock user service."""
        service = Mock()
        service.get_user_by_id.return_value = User(
            id="user_123",
            email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            is_active=True,
            roles=["user"],
        )
        return service

    def test_get_current_user_valid_token(self, mock_token_service, mock_user_service):
        """Test getting current user with valid token."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_123")

        with patch('src.amplihack.auth.dependencies.token_service', mock_token_service):
            with patch('src.amplihack.auth.dependencies.user_service', mock_user_service):
                user = get_current_user(credentials)

                assert user is not None
                assert user.id == "user_123"
                assert user.email == "user@example.com"

    def test_get_current_user_invalid_token(self, mock_token_service):
        """Test getting current user with invalid token."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        mock_token_service.validate_token.side_effect = Exception("Invalid token")

        with patch('src.amplihack.auth.dependencies.token_service', mock_token_service):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials)

            assert exc_info.value.status_code == 401

    def test_get_current_active_user_inactive(self, mock_token_service, mock_user_service):
        """Test active user check rejects inactive users."""
        mock_user_service.get_user_by_id.return_value = User(
            id="user_123",
            email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            is_active=False,  # Inactive user
        )

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token_123")

        with patch('src.amplihack.auth.dependencies.token_service', mock_token_service):
            with patch('src.amplihack.auth.dependencies.user_service', mock_user_service):
                with pytest.raises(HTTPException) as exc_info:
                    get_current_active_user(credentials)

                assert exc_info.value.status_code == 403
                assert "inactive" in exc_info.value.detail.lower()


class TestRoleBasedAccessControl:
    """Test role-based access control decorators."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application with RBAC."""
        app = FastAPI()

        @app.get("/admin-only")
        @RequireRoles(["admin"])
        async def admin_route(current_user: User = Depends(get_current_user)):
            return {"message": "Admin content"}

        @app.get("/multi-role")
        @RequireRoles(["admin", "moderator"], require_all=False)
        async def multi_role_route(current_user: User = Depends(get_current_user)):
            return {"message": "Admin or Moderator content"}

        @app.get("/all-roles")
        @RequireRoles(["user", "verified"], require_all=True)
        async def all_roles_route(current_user: User = Depends(get_current_user)):
            return {"message": "User and Verified content"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_require_roles_single_role_success(self, client):
        """Test role requirement with matching role."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                roles=["admin"],
            )

            response = client.get("/admin-only")
            assert response.status_code == 200

    def test_require_roles_single_role_failure(self, client):
        """Test role requirement without matching role."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                roles=["user"],  # Not admin
            )

            response = client.get("/admin-only")
            assert response.status_code == 403
            assert "insufficient permissions" in response.json()["detail"].lower()

    def test_require_roles_any_role_success(self, client):
        """Test role requirement with any matching role."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                roles=["moderator"],  # Has one of the required roles
            )

            response = client.get("/multi-role")
            assert response.status_code == 200

    def test_require_roles_all_roles_success(self, client):
        """Test role requirement with all matching roles."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                roles=["user", "verified"],  # Has all required roles
            )

            response = client.get("/all-roles")
            assert response.status_code == 200

    def test_require_roles_all_roles_partial_failure(self, client):
        """Test role requirement fails with partial role match."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                roles=["user"],  # Missing "verified"
            )

            response = client.get("/all-roles")
            assert response.status_code == 403


class TestPermissionBasedAccessControl:
    """Test permission-based access control."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI application with permission checks."""
        app = FastAPI()

        @app.get("/read-users")
        @RequirePermissions(["users:read"])
        async def read_users(current_user: User = Depends(get_current_user)):
            return {"message": "User list"}

        @app.get("/modify-users")
        @RequirePermissions(["users:read", "users:write"], require_all=True)
        async def modify_users(current_user: User = Depends(get_current_user)):
            return {"message": "User modification"}

        @app.delete("/delete-users")
        @RequirePermissions(["users:delete", "admin:all"], require_all=False)
        async def delete_users(current_user: User = Depends(get_current_user)):
            return {"message": "User deletion"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_require_permissions_success(self, client):
        """Test permission requirement with matching permission."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                permissions=["users:read"],
            )

            response = client.get("/read-users")
            assert response.status_code == 200

    def test_require_permissions_wildcard(self, client):
        """Test permission with wildcard matching."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                permissions=["users:*"],  # Wildcard permission
            )

            response = client.get("/read-users")
            assert response.status_code == 200

            response = client.get("/modify-users")
            assert response.status_code == 200

    def test_require_permissions_admin_override(self, client):
        """Test admin:all permission overrides specific requirements."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                permissions=["admin:all"],
            )

            # Admin should have access to everything
            response = client.get("/read-users")
            assert response.status_code == 200

            response = client.get("/modify-users")
            assert response.status_code == 200

            response = client.delete("/delete-users")
            assert response.status_code == 200


class TestOptionalAuth:
    """Test optional authentication middleware."""

    @pytest.fixture
    def app(self):
        """Create test app with optional auth routes."""
        app = FastAPI()

        @app.get("/public")
        @OptionalAuth()
        async def public_route(current_user: Optional[User] = None):
            if current_user:
                return {"message": f"Hello {current_user.email}"}
            return {"message": "Hello anonymous"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_optional_auth_without_token(self, client):
        """Test optional auth allows access without token."""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "Hello anonymous"

    def test_optional_auth_with_valid_token(self, client):
        """Test optional auth with valid token provides user."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.return_value = User(
                id="user_123",
                email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            )

            headers = {"Authorization": "Bearer valid_token"}
            response = client.get("/public", headers=headers)

            assert response.status_code == 200
            assert response.json()["message"] == "Hello user@example.com"

    def test_optional_auth_with_invalid_token(self, client):
        """Test optional auth treats invalid token as anonymous."""
        with patch('src.amplihack.auth.dependencies.get_current_user') as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401)

            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/public", headers=headers)

            # Should treat as anonymous instead of failing
            assert response.status_code == 200
            assert response.json()["message"] == "Hello anonymous"