"""
Shared fixtures and helpers for authentication tests.
These provide reusable test utilities following TDD approach.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import jwt
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
import redis

# Import modules for fixtures (these don't exist yet - TDD approach)
from src.amplihack.auth.models import User, TokenPayload
from src.amplihack.auth.services import TokenService, UserService
from src.amplihack.auth.config import JWTConfig, AuthConfig
from src.amplihack.auth.database import get_test_database
from src.amplihack.auth.app import create_app


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def jwt_config():
    """Create JWT configuration for testing."""
    return JWTConfig(
        secret_key="test_secret_key_for_testing_only_123456789",
        algorithm="HS256",
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        issuer="amplihack-auth-test",
        audience="amplihack-api-test",
    )


@pytest.fixture
def auth_config():
    """Create authentication configuration for testing."""
    return AuthConfig(
        enable_registration=True,
        enable_social_login=False,
        require_email_verification=False,
        password_min_length=8,
        password_require_uppercase=True,
        password_require_lowercase=True,
        password_require_digit=True,
        password_require_special=True,
        max_login_attempts=5,
        lockout_duration_minutes=30,
    )


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user():
    """Create a test user object."""
    return User(
        id="test_user_123",
        email="test@example.com",
        username="testuser",
        password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
        is_locked=False,
        roles=["user"],
        permissions=["read:profile", "update:profile"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def admin_user():
    """Create an admin user object."""
    return User(
        id="admin_user_123",
        email="admin@example.com",
        username="admin",
        password_hash="$2b$12$AdminHash1234567890abcdefghijklmnopqrstuvwxyz",
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_verified=True,
        is_locked=False,
        roles=["admin", "user"],
        permissions=["admin:all"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def inactive_user():
    """Create an inactive user object."""
    return User(
        id="inactive_user_123",
        email="inactive@example.com",
        username="inactive",
        password_hash="$2b$12$InactiveHash1234567890abcdefghijklmnop",
        is_active=False,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def user_factory():
    """Factory for creating test users with custom attributes."""
    def _create_user(**kwargs):
        defaults = {
            "id": f"user_{datetime.now().timestamp()}",
            "email": f"user_{datetime.now().timestamp()}@example.com",
            "username": f"user_{datetime.now().timestamp()}",
            "password_hash": "$2b$12$DefaultHash1234567890abcdefghijklmnop",
            "is_active": True,
            "is_verified": True,
            "is_locked": False,
            "roles": ["user"],
            "permissions": [],
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return User(**defaults)
    return _create_user


# ============================================================================
# Token Fixtures
# ============================================================================

@pytest.fixture
def valid_access_token(jwt_config, test_user):
    """Create a valid access token."""
    payload = {
        "sub": test_user.id,
        "email": test_user.email,
        "username": test_user.username,
        "roles": test_user.roles,
        "permissions": test_user.permissions,
        "type": "access",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": "access_jti_123",
        "iss": jwt_config.issuer,
        "aud": jwt_config.audience,
    }
    return jwt.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)


@pytest.fixture
def valid_refresh_token(jwt_config, test_user):
    """Create a valid refresh token."""
    payload = {
        "sub": test_user.id,
        "type": "refresh",
        "exp": (datetime.now(timezone.utc) + timedelta(days=30)).timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
        "jti": "refresh_jti_123",
        "iss": jwt_config.issuer,
        "aud": jwt_config.audience,
    }
    return jwt.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)


@pytest.fixture
def expired_access_token(jwt_config, test_user):
    """Create an expired access token."""
    payload = {
        "sub": test_user.id,
        "email": test_user.email,
        "type": "access",
        "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
        "iat": (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp(),
        "jti": "expired_jti_123",
        "iss": jwt_config.issuer,
        "aud": jwt_config.audience,
    }
    return jwt.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)


@pytest.fixture
def token_factory(jwt_config):
    """Factory for creating test tokens with custom claims."""
    def _create_token(**kwargs):
        defaults = {
            "sub": "user_123",
            "type": "access",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp(),
            "jti": f"jti_{datetime.now().timestamp()}",
            "iss": jwt_config.issuer,
            "aud": jwt_config.audience,
        }
        defaults.update(kwargs)
        return jwt.encode(defaults, jwt_config.secret_key, algorithm=jwt_config.algorithm)
    return _create_token


# ============================================================================
# Service Mocks
# ============================================================================

@pytest.fixture
def mock_token_service():
    """Create a mock token service."""
    service = Mock(spec=TokenService)
    service.generate_access_token.return_value = "mock_access_token"
    service.generate_refresh_token.return_value = "mock_refresh_token"
    service.validate_token.return_value = TokenPayload(
        user_id="user_123",
        email="user@example.com",
        roles=["user"],
    )
    return service


@pytest.fixture
def mock_user_service():
    """Create a mock user service."""
    service = Mock(spec=UserService)
    service.get_user_by_id.return_value = Mock(spec=User)
    service.get_user_by_email.return_value = Mock(spec=User)
    service.create_user.return_value = Mock(spec=User)
    return service


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def test_db():
    """Create a test database session."""
    async with get_test_database() as db:
        yield db


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    mock.expire.return_value = True
    mock.ttl.return_value = -1
    return mock


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    return create_app(testing=True)


@pytest.fixture
def test_client(test_app):
    """Create a test client for the application."""
    return TestClient(test_app)


@pytest.fixture
def authenticated_client(test_client, valid_access_token):
    """Create a test client with authentication headers."""
    test_client.headers = {"Authorization": f"Bearer {valid_access_token}"}
    return test_client


# ============================================================================
# Request/Response Helpers
# ============================================================================

@pytest.fixture
def registration_request():
    """Create a valid registration request."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "NewP@ssw0rd123!",
        "first_name": "New",
        "last_name": "User",
    }


@pytest.fixture
def login_request():
    """Create a valid login request."""
    return {
        "email": "test@example.com",
        "password": "TestP@ssw0rd123!",
    }


@pytest.fixture
def auth_headers(valid_access_token):
    """Create authorization headers with a valid token."""
    return {"Authorization": f"Bearer {valid_access_token}"}


# ============================================================================
# Async Helpers
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Time/Date Helpers
# ============================================================================

@pytest.fixture
def freeze_time():
    """Fixture to freeze time for testing."""
    from unittest.mock import patch
    import time as time_module

    def _freeze(timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()

        patcher = patch('time.time', return_value=timestamp)
        patcher.start()
        return patcher

    return _freeze


# ============================================================================
# Validation Helpers
# ============================================================================

def assert_valid_jwt(token: str, secret: str, algorithm: str = "HS256") -> Dict[str, Any]:
    """Assert that a token is a valid JWT and return its payload."""
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        assert payload is not None
        return payload
    except jwt.InvalidTokenError as e:
        pytest.fail(f"Invalid JWT token: {e}")


def assert_token_contains_claims(token: str, secret: str, expected_claims: Dict[str, Any]):
    """Assert that a token contains expected claims."""
    payload = assert_valid_jwt(token, secret)
    for key, value in expected_claims.items():
        assert key in payload, f"Token missing claim: {key}"
        assert payload[key] == value, f"Token claim {key} mismatch: {payload[key]} != {value}"


def assert_api_error(response, status_code: int, error_message: Optional[str] = None):
    """Assert API error response format."""
    assert response.status_code == status_code
    data = response.json()
    assert "detail" in data or "error" in data

    if error_message:
        error_text = data.get("detail", data.get("error", "")).lower()
        assert error_message.lower() in error_text


# ============================================================================
# Performance Testing Helpers
# ============================================================================

@pytest.fixture
def measure_time():
    """Fixture to measure execution time."""
    import time

    class TimeMeasure:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.end_time = time.perf_counter()

        @property
        def duration(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000  # Return in milliseconds
            return 0

    return TimeMeasure


# ============================================================================
# Data Generators
# ============================================================================

def generate_users(count: int) -> List[User]:
    """Generate multiple test users."""
    users = []
    for i in range(count):
        users.append(User(
            id=f"user_{i}",
            email=f"user{i}@example.com",
            username=f"user{i}",
            password_hash=f"hash_{i}",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        ))
    return users


def generate_tokens(users: List[User], config: JWTConfig) -> List[str]:
    """Generate tokens for multiple users."""
    tokens = []
    for user in users:
        payload = {
            "sub": user.id,
            "email": user.email,
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = jwt.encode(payload, config.secret_key, algorithm=config.algorithm)
        tokens.append(token)
    return tokens