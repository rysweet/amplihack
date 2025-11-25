"""
Unit tests for refresh token flow and token blacklisting.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import uuid
from typing import Dict, Any

# Import the modules to be tested
from src.amplihack.auth.services import (
    TokenService,
    TokenBlacklistService,
)
from src.amplihack.auth.models import (
    User,
    RefreshToken,
    RefreshTokenRequest,
)
from src.amplihack.auth.exceptions import (
    TokenInvalidError,
    TokenExpiredError,
    TokenBlacklistedError,
)


class TestRefreshTokenFlow:
    """Test refresh token flow functionality."""

    @pytest.fixture
    def mock_token_service(self):
        """Create a mock token service."""
        service = Mock(spec=TokenService)
        service.generate_access_token.return_value = "new_access_token_123"
        service.generate_refresh_token.return_value = "new_refresh_token_123"
        service.validate_refresh_token.return_value = Mock(
            user_id="user_123",
            jti="refresh_jti_123",
        )
        return service

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        return User(
            id="user_123",
            email="user@example.com",
            username="johndoe",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            is_active=True,
        )

    @pytest.fixture
    def token_service(self):
        """Create a TokenService instance with test config."""
        from src.amplihack.auth.config import JWTConfig
        config = JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            issuer="amplihack-auth",
            audience="amplihack-api",
        )
        return TokenService(config=config)

    def test_refresh_token_success(self, mock_token_service, mock_user):
        """Test successful token refresh."""
        request = RefreshTokenRequest(
            refresh_token="valid_refresh_token_123",
        )

        # Generate tokens
        access_token = mock_token_service.generate_access_token(mock_user)
        refresh_token = mock_token_service.generate_refresh_token(mock_user)

        assert access_token is not None
        assert refresh_token is not None
        assert access_token == "new_access_token_123"
        assert refresh_token == "new_refresh_token_123"

    def test_refresh_token_rotation(self, mock_token_service, mock_user):
        """Test refresh token rotation (new token on each refresh)."""
        request = RefreshTokenRequest(
            refresh_token="valid_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=False,
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token
        mock_refresh_repository.get_user.return_value = Mock(id="user_123")

        # Perform multiple refreshes
        for i in range(3):
            token_pair = refresh_service.refresh_tokens(request)
            assert token_pair.refresh_token is not None

            # Each refresh should revoke the previous token
            assert mock_refresh_repository.revoke_token.call_count == i + 1

    def test_refresh_token_revoked(self, refresh_service, mock_refresh_repository):
        """Test refresh fails with revoked token."""
        request = RefreshTokenRequest(
            refresh_token="revoked_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=True,  # Token is revoked
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token

        with pytest.raises(RefreshTokenRevokedError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "refresh token has been revoked" in str(exc_info.value).lower()

    def test_refresh_token_expired(self, refresh_service, mock_refresh_repository):
        """Test refresh fails with expired token."""
        request = RefreshTokenRequest(
            refresh_token="expired_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            is_revoked=False,
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token

        with pytest.raises(TokenExpiredError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "refresh token has expired" in str(exc_info.value).lower()

    def test_refresh_token_not_found(self, refresh_service, mock_refresh_repository):
        """Test refresh fails when token not found in database."""
        request = RefreshTokenRequest(
            refresh_token="nonexistent_refresh_token_123",
        )

        mock_refresh_repository.find_by_jti.return_value = None

        with pytest.raises(RefreshTokenNotFoundError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "refresh token not found" in str(exc_info.value).lower()

    def test_refresh_token_user_inactive(self, refresh_service, mock_refresh_repository):
        """Test refresh fails when user account is inactive."""
        request = RefreshTokenRequest(
            refresh_token="valid_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=False,
        )

        inactive_user = User(
            id="user_123",
            email="user@example.com",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",
            is_active=False,  # User is inactive
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token
        mock_refresh_repository.get_user.return_value = inactive_user

        with pytest.raises(InvalidTokenError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "user account is not active" in str(exc_info.value).lower()

    def test_refresh_token_reuse_detection(self, refresh_service, mock_refresh_repository):
        """Test detection of refresh token reuse (security feature)."""
        request = RefreshTokenRequest(
            refresh_token="reused_refresh_token_123",
        )

        # Token was already used (revoked)
        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=True,
            revoked_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token

        with pytest.raises(TokenRotationViolationError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "token rotation violation" in str(exc_info.value).lower()

        # Verify all user's refresh tokens were revoked (security measure)
        mock_refresh_repository.revoke_all_user_tokens.assert_called_once_with("user_123")

    def test_refresh_token_family_tracking(self, refresh_service, mock_refresh_repository):
        """Test refresh token family tracking for security."""
        request = RefreshTokenRequest(
            refresh_token="valid_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            family_id="family_123",  # Token family for tracking
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=False,
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token
        mock_refresh_repository.get_user.return_value = Mock(id="user_123")

        token_pair = refresh_service.refresh_tokens(request)

        # Verify new token maintains family ID
        save_call = mock_refresh_repository.save_refresh_token.call_args[0][0]
        assert save_call.family_id == "family_123"

    def test_refresh_token_max_uses(self, refresh_service, mock_refresh_repository):
        """Test refresh token has maximum use limit."""
        request = RefreshTokenRequest(
            refresh_token="valid_refresh_token_123",
        )

        stored_token = RefreshToken(
            id="token_id_123",
            user_id="user_123",
            token_jti="refresh_jti_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=False,
            use_count=99,  # Near maximum
            max_uses=100,
        )

        mock_refresh_repository.find_by_jti.return_value = stored_token
        mock_refresh_repository.get_user.return_value = Mock(id="user_123")

        # First refresh should succeed (use 100)
        token_pair = refresh_service.refresh_tokens(request)
        assert token_pair is not None

        # Update stored token to reflect maximum uses reached
        stored_token.use_count = 100

        # Next refresh should fail
        with pytest.raises(InvalidTokenError) as exc_info:
            refresh_service.refresh_tokens(request)

        assert "maximum uses exceeded" in str(exc_info.value).lower()


class TestTokenBlacklist:
    """Test token blacklisting functionality."""

    @pytest.fixture
    def mock_blacklist_repository(self):
        """Create a mock blacklist repository."""
        return Mock(spec=TokenBlacklistRepository)

    @pytest.fixture
    def blacklist_service(self, mock_blacklist_repository):
        """Create a TokenBlacklistService instance."""
        return TokenBlacklistService(
            repository=mock_blacklist_repository,
        )

    def test_blacklist_token(self, blacklist_service, mock_blacklist_repository):
        """Test adding token to blacklist."""
        token_jti = "token_jti_123"
        user_id = "user_123"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        blacklist_service.blacklist_token(token_jti, user_id, expires_at)

        mock_blacklist_repository.add_to_blacklist.assert_called_once_with(
            jti=token_jti,
            user_id=user_id,
            expires_at=expires_at,
        )

    def test_is_blacklisted_true(self, blacklist_service, mock_blacklist_repository):
        """Test checking if token is blacklisted (true case)."""
        token_jti = "blacklisted_token_123"
        mock_blacklist_repository.is_blacklisted.return_value = True

        result = blacklist_service.is_blacklisted(token_jti)

        assert result is True
        mock_blacklist_repository.is_blacklisted.assert_called_once_with(token_jti)

    def test_is_blacklisted_false(self, blacklist_service, mock_blacklist_repository):
        """Test checking if token is blacklisted (false case)."""
        token_jti = "valid_token_123"
        mock_blacklist_repository.is_blacklisted.return_value = False

        result = blacklist_service.is_blacklisted(token_jti)

        assert result is False

    def test_blacklist_all_user_tokens(self, blacklist_service, mock_blacklist_repository):
        """Test blacklisting all tokens for a user."""
        user_id = "user_123"

        blacklist_service.blacklist_all_user_tokens(user_id)

        mock_blacklist_repository.blacklist_all_user_tokens.assert_called_once_with(user_id)

    def test_clean_expired_blacklist(self, blacklist_service, mock_blacklist_repository):
        """Test cleaning expired tokens from blacklist."""
        mock_blacklist_repository.remove_expired.return_value = 42

        removed_count = blacklist_service.clean_expired()

        assert removed_count == 42
        mock_blacklist_repository.remove_expired.assert_called_once()

    def test_logout_blacklists_tokens(self, blacklist_service, mock_blacklist_repository):
        """Test logout blacklists both access and refresh tokens."""
        request = LogoutRequest(
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            access_token_jti="access_jti_123",
            refresh_token_jti="refresh_jti_123",
            user_id="user_123",
        )

        blacklist_service.logout(request)

        # Verify both tokens were blacklisted
        assert mock_blacklist_repository.add_to_blacklist.call_count == 2

        # Check the calls
        calls = mock_blacklist_repository.add_to_blacklist.call_args_list
        jtis = [call[1]["jti"] for call in calls]
        assert "access_jti_123" in jtis
        assert "refresh_jti_123" in jtis

    def test_logout_everywhere(self, blacklist_service, mock_blacklist_repository):
        """Test logout from all devices blacklists all user tokens."""
        user_id = "user_123"

        blacklist_service.logout_everywhere(user_id)

        # Should blacklist all user tokens and revoke all refresh tokens
        mock_blacklist_repository.blacklist_all_user_tokens.assert_called_once_with(user_id)

    def test_validate_token_checks_blacklist(self, blacklist_service):
        """Test token validation checks blacklist."""
        with patch('src.amplihack.auth.services.TokenService') as mock_token_service:
            mock_token_service.validate_token.return_value = Mock(jti="token_jti_123")

            # Token is blacklisted
            blacklist_service.repository.is_blacklisted.return_value = True

            with pytest.raises(TokenBlacklistedError) as exc_info:
                blacklist_service.validate_token_with_blacklist("token_123")

            assert "token has been blacklisted" in str(exc_info.value).lower()

    def test_blacklist_with_reason(self, blacklist_service, mock_blacklist_repository):
        """Test blacklisting token with reason."""
        token_jti = "token_jti_123"
        user_id = "user_123"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reason = "User requested logout"

        blacklist_service.blacklist_token(token_jti, user_id, expires_at, reason)

        mock_blacklist_repository.add_to_blacklist.assert_called_once()
        call_args = mock_blacklist_repository.add_to_blacklist.call_args[1]
        assert call_args["reason"] == reason

    def test_blacklist_statistics(self, blacklist_service, mock_blacklist_repository):
        """Test getting blacklist statistics."""
        mock_blacklist_repository.get_statistics.return_value = {
            "total_blacklisted": 1234,
            "expired": 456,
            "active": 778,
            "by_reason": {
                "logout": 500,
                "security": 100,
                "admin_action": 50,
                "other": 128,
            },
        }

        stats = blacklist_service.get_statistics()

        assert stats["total_blacklisted"] == 1234
        assert stats["active"] == 778
        assert stats["by_reason"]["logout"] == 500