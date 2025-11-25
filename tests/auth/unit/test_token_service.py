"""
Unit tests for JWT token generation, validation, and expiry.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
import time
from typing import Dict, Any

# Import the modules to be tested
from src.amplihack.auth.services import TokenService, TokenBlacklistService
from src.amplihack.auth.models import (
    User,
    TokenPayload,
    RefreshToken,
)
from src.amplihack.auth.exceptions import (
    TokenInvalidError,
    TokenExpiredError,
    TokenBlacklistedError,
)
from src.amplihack.auth.config import JWTConfig


class TestTokenGeneration:
    """Test JWT token generation."""

    @pytest.fixture
    def jwt_config(self):
        """Create JWT configuration."""
        return JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            access_token_expire_minutes=60,  # 1 hour
            refresh_token_expire_days=30,
            issuer="amplihack-auth",
            audience="amplihack-api",
        )

    @pytest.fixture
    def token_service(self, jwt_config):
        """Create a TokenService instance."""
        return TokenService(config=jwt_config)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id="user_123",
            email="user@example.com",
            username="johndoe",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            is_active=True,
            roles=["user"],
            permissions=["read:profile", "update:profile"],
        )

    def test_generate_access_token(self, token_service, sample_user):
        """Test access token generation."""
        token = token_service.generate_access_token(sample_user)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

        # Decode and verify payload
        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        assert payload["sub"] == "user_123"
        assert payload["email"] == "user@example.com"
        assert payload["username"] == "johndoe"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload  # JWT ID

    def test_generate_refresh_token(self, token_service, sample_user):
        """Test refresh token generation."""
        token = token_service.generate_refresh_token(sample_user)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

        # Decode and verify payload
        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        assert payload["sub"] == "user_123"
        assert payload["type"] == "refresh"
        assert "exp" in payload

        # Refresh token should have longer expiry
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (exp_time - now).days >= 29  # Close to 30 days

    def test_generate_token_with_custom_claims(self, token_service, sample_user):
        """Test token generation with custom claims."""
        custom_claims = {
            "organization_id": "org_456",
            "subscription": "premium",
        }

        token = token_service.generate_access_token(sample_user, custom_claims)

        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        assert payload["organization_id"] == "org_456"
        assert payload["subscription"] == "premium"

    def test_generate_token_with_roles_and_permissions(self, token_service, sample_user):
        """Test token includes user roles and permissions."""
        token = token_service.generate_access_token(sample_user)

        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        assert payload["roles"] == ["user"]
        assert payload["permissions"] == ["read:profile", "update:profile"]

    def test_generate_token_unique_jti(self, token_service, sample_user):
        """Test each token has unique JWT ID (jti)."""
        token1 = token_service.generate_access_token(sample_user)
        token2 = token_service.generate_access_token(sample_user)

        payload1 = jwt.decode(
            token1,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        payload2 = jwt.decode(
            token2,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            audience="amplihack-api",
            issuer="amplihack-auth",
        )

        assert payload1["jti"] != payload2["jti"]

    def test_generate_token_pair(self, token_service, sample_user):
        """Test generation of access and refresh token pair."""
        token_pair = token_service.generate_token_pair(sample_user)

        assert token_pair is not None
        assert token_pair.get("access_token") is not None
        assert token_pair.get("refresh_token") is not None
        assert token_pair.get("expires_in") == 3600  # 1 hour in seconds
        assert token_pair.get("token_type") == "Bearer"

    def test_generate_token_invalid_user(self, token_service):
        """Test token generation fails with invalid user."""
        with pytest.raises((ValueError, AttributeError)):
            token_service.generate_access_token(None)

        with pytest.raises((ValueError, AttributeError)):
            token_service.generate_access_token(User(id=None, email="test@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz"))


class TestTokenValidation:
    """Test JWT token validation."""

    @pytest.fixture
    def jwt_config(self):
        """Create JWT configuration."""
        return JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            issuer="amplihack-auth",
            audience="amplihack-api",
        )

    @pytest.fixture
    def token_service(self, jwt_config):
        """Create a TokenService instance."""
        return TokenService(config=jwt_config)

    @pytest.fixture
    def valid_token(self, token_service):
        """Create a valid access token."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        return token_service.generate_access_token(user)

    def test_validate_valid_token(self, token_service, valid_token):
        """Test validation of valid token."""
        payload = token_service.validate_token(valid_token)

        assert payload is not None
        assert payload.user_id == "user_123"
        assert payload.email == "user@example.com"
        assert payload.token_type == "access"

    def test_validate_token_invalid_signature(self, token_service):
        """Test validation fails with invalid signature."""
        # Create token with different secret
        token = jwt.encode(
            {"sub": "user_123", "exp": time.time() + 3600},
            "wrong_secret_key",
            algorithm="HS256",
        )

        with pytest.raises(TokenInvalidError) as exc_info:
            token_service.validate_token(token)

        assert "signature" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    def test_validate_token_expired(self, token_service):
        """Test validation fails with expired token."""
        # Create expired token
        expired_payload = {
            "sub": "user_123",
            "exp": time.time() - 3600,  # Expired 1 hour ago
            "iat": time.time() - 7200,
            "type": "access",
        }

        expired_token = jwt.encode(
            expired_payload,
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(TokenExpiredError) as exc_info:
            token_service.validate_token(expired_token)

        assert "token has expired" in str(exc_info.value).lower()

    def test_validate_token_invalid_issuer(self, token_service):
        """Test validation fails with invalid issuer."""
        token = jwt.encode(
            {
                "sub": "user_123",
                "exp": time.time() + 3600,
                "iss": "wrong_issuer",
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.validate_token(token)

        assert "invalid issuer" in str(exc_info.value).lower()

    def test_validate_token_invalid_audience(self, token_service):
        """Test validation fails with invalid audience."""
        token = jwt.encode(
            {
                "sub": "user_123",
                "exp": time.time() + 3600,
                "iss": "amplihack-auth",
                "aud": "wrong_audience",
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(InvalidTokenError) as exc_info:
            token_service.validate_token(token)

        assert "invalid audience" in str(exc_info.value).lower()

    def test_validate_token_malformed(self, token_service):
        """Test validation fails with malformed token."""
        malformed_tokens = [
            "not.a.token",
            "invalid_jwt_format",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Missing payload and signature
            "",
        ]

        for token in malformed_tokens:
            with pytest.raises((TokenInvalidError, ValueError)):
                token_service.validate_token(token)

        # Test None separately
        with pytest.raises((TokenInvalidError, ValueError, TypeError)):
            token_service.validate_token(None)

    def test_validate_token_wrong_algorithm(self, token_service):
        """Test validation fails with wrong algorithm."""
        # Create token with different algorithm
        token = jwt.encode(
            {"sub": "user_123", "exp": time.time() + 3600},
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS512",  # Different from expected HS256
        )

        with pytest.raises(InvalidTokenError):
            token_service.validate_token(token)

    def test_validate_refresh_token(self, token_service):
        """Test validation of refresh token."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        refresh_token = token_service.generate_refresh_token(user)

        payload = token_service.validate_refresh_token(refresh_token)

        assert payload is not None
        assert payload.user_id == "user_123"
        assert payload.token_type == "refresh"

    def test_validate_wrong_token_type(self, token_service):
        """Test access token validation fails for refresh token."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        refresh_token = token_service.generate_refresh_token(user)

        with pytest.raises(TokenInvalidError) as exc_info:
            # Try to validate refresh token as access token
            token_service.validate_token(refresh_token, expected_type="access")

        assert "token type" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


class TestTokenExpiry:
    """Test token expiry handling."""

    @pytest.fixture
    def jwt_config(self):
        """Create JWT configuration with short expiry for testing."""
        return JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            access_token_expire_minutes=1,  # 1 minute for testing
            refresh_token_expire_days=1,
            issuer="amplihack-auth",
            audience="amplihack-api",
        )

    @pytest.fixture
    def token_service(self, jwt_config):
        """Create a TokenService instance."""
        return TokenService(config=jwt_config)

    def test_token_expiry_time_access(self, token_service):
        """Test access token has correct expiry time."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        token = token_service.generate_access_token(user)

        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            options={"verify_exp": False},  # Don't verify expiry for inspection
        )

        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Should expire 1 minute after issued
        assert (exp_time - iat_time).seconds == 60

    def test_token_expiry_time_refresh(self, token_service):
        """Test refresh token has correct expiry time."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        token = token_service.generate_refresh_token(user)

        payload = jwt.decode(
            token,
            "test_secret_key_for_testing_only_123456789",
            algorithms=["HS256"],
            options={"verify_exp": False},
        )

        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Should expire 1 day after issued
        assert (exp_time - iat_time).days == 1

    def test_is_token_expired(self, token_service):
        """Test checking if token is expired."""
        # Create token that expires immediately
        expired_payload = {
            "sub": "user_123",
            "exp": time.time() - 1,  # Already expired
            "iat": time.time() - 61,
        }

        expired_token = jwt.encode(
            expired_payload,
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        assert token_service.is_token_expired(expired_token) is True

        # Create valid token
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        valid_token = token_service.generate_access_token(user)

        assert token_service.is_token_expired(valid_token) is False

    def test_get_token_expiry_time(self, token_service):
        """Test getting token expiry timestamp."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        token = token_service.generate_access_token(user)

        expiry_time = token_service.get_token_expiry(token)

        assert expiry_time is not None
        assert isinstance(expiry_time, datetime)
        assert expiry_time > datetime.now(timezone.utc)

    def test_time_until_expiry(self, token_service):
        """Test calculating time until token expires."""
        user = User(id="user_123", email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz")
        token = token_service.generate_access_token(user)

        seconds_until_expiry = token_service.time_until_expiry(token)

        assert seconds_until_expiry > 0
        assert seconds_until_expiry <= 60  # 1 minute max

    def test_token_expiry_leeway(self, token_service):
        """Test token validation with expiry leeway."""
        # Create token that just expired
        expired_payload = {
            "sub": "user_123",
            "exp": time.time() - 5,  # Expired 5 seconds ago
            "iat": time.time() - 65,
            "type": "access",
        }

        expired_token = jwt.encode(
            expired_payload,
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        # Should fail without leeway
        with pytest.raises(TokenExpiredError):
            token_service.validate_token(expired_token)

        # Should pass with 10-second leeway
        payload = token_service.validate_token(expired_token, leeway_seconds=10)
        assert payload.user_id == "user_123"