"""
Unit tests for user login functionality.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Import the modules to be tested
from src.amplihack.auth.models import User, LoginRequest, LoginResponse
from src.amplihack.auth.services import AuthenticationService, TokenService
from src.amplihack.auth.exceptions import (
    InvalidCredentialsError,
    AccountLockedError,
    AccountNotActiveError,
    TooManyFailedAttemptsError,
)
from src.amplihack.auth.repository import UserRepository
from src.amplihack.auth.services import RateLimiter


class TestLoginValidation:
    """Test login request validation."""

    @pytest.fixture
    def auth_service(self):
        """Create an AuthenticationService instance with mocks."""
        return AuthenticationService(
            user_repository=Mock(spec=UserRepository),
            token_service=Mock(spec=TokenService),
            rate_limiter=Mock(spec=RateLimiter),
        )

    def test_validate_login_request_valid(self, auth_service):
        """Test validation of valid login request."""
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        assert auth_service.validate_login_request(request) is True

    def test_validate_login_request_with_username(self, auth_service):
        """Test login with username instead of email."""
        request = LoginRequest(
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        assert auth_service.validate_login_request(request) is True

    def test_validate_login_request_missing_identifier(self, auth_service):
        """Test login fails without email or username."""
        request = LoginRequest(
            password="MyP@ssw0rd123!",
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.validate_login_request(request)

        assert "email or username required" in str(exc_info.value).lower()

    def test_validate_login_request_missing_password(self, auth_service):
        """Test login fails without password."""
        request = LoginRequest(
            email="user@example.com",
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.validate_login_request(request)

        assert "password required" in str(exc_info.value).lower()

    def test_validate_login_request_both_email_and_username(self, auth_service):
        """Test login with both email and username uses email."""
        request = LoginRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        assert auth_service.validate_login_request(request) is True
        assert auth_service.get_login_identifier(request) == "user@example.com"


class TestAuthenticationService:
    """Test authentication service login logic."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_token_service(self):
        """Create a mock token service."""
        service = Mock(spec=TokenService)
        service.generate_access_token.return_value = "access_token_123"
        service.generate_refresh_token.return_value = "refresh_token_123"
        return service

    @pytest.fixture
    def mock_rate_limiter(self):
        """Create a mock rate limiter."""
        limiter = Mock(spec=RateLimiter)
        limiter.check_rate_limit.return_value = True
        return limiter

    @pytest.fixture
    def auth_service(self, mock_repository, mock_token_service, mock_rate_limiter):
        """Create an AuthenticationService with mocks."""
        return AuthenticationService(
            user_repository=mock_repository,
            token_service=mock_token_service,
            rate_limiter=mock_rate_limiter,
        )

    @pytest.fixture
    def valid_user(self):
        """Create a valid user fixture."""
        return User(
            id="user_123",
            email="user@example.com",
            username="johndoe",
            password_hash="$2b$12$KIXxPfR1234567890abcdefghijklmnopqrstuvwxyz",  # bcrypt hash
            is_active=True,
            is_locked=False,
            failed_login_attempts=0,
            last_login_at=None,
            created_at=datetime.now(timezone.utc),
        )

    def test_login_success_with_email(self, auth_service, mock_repository, valid_user):
        """Test successful login with email."""
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response is not None
            assert response.access_token == "access_token_123"
            assert response.refresh_token == "refresh_token_123"
            assert response.user_id == "user_123"
            assert response.expires_in == 3600  # Default 1 hour

            # Verify user login timestamp was updated
            mock_repository.update_last_login.assert_called_once_with("user_123")

    def test_login_success_with_username(self, auth_service, mock_repository, valid_user):
        """Test successful login with username."""
        request = LoginRequest(
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_username.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response is not None
            assert response.access_token == "access_token_123"
            assert response.refresh_token == "refresh_token_123"

    def test_login_invalid_email(self, auth_service, mock_repository):
        """Test login with non-existent email."""
        request = LoginRequest(
            email="nonexistent@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = None

        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.login(request)

        assert "invalid credentials" in str(exc_info.value).lower()

    def test_login_invalid_password(self, auth_service, mock_repository, valid_user):
        """Test login with incorrect password."""
        request = LoginRequest(
            email="user@example.com",
            password="WrongPassword123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = False

            with pytest.raises(InvalidCredentialsError) as exc_info:
                auth_service.login(request)

            assert "invalid credentials" in str(exc_info.value).lower()

            # Verify failed attempt was recorded
            mock_repository.increment_failed_attempts.assert_called_once_with("user_123")

    def test_login_account_locked(self, auth_service, mock_repository, valid_user):
        """Test login fails when account is locked."""
        valid_user.is_locked = True
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with pytest.raises(AccountLockedError) as exc_info:
            auth_service.login(request)

        assert "account is locked" in str(exc_info.value).lower()

    def test_login_account_inactive(self, auth_service, mock_repository, valid_user):
        """Test login fails when account is inactive."""
        valid_user.is_active = False
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with pytest.raises(AccountNotActiveError) as exc_info:
            auth_service.login(request)

        assert "account is not active" in str(exc_info.value).lower()

    def test_login_too_many_failed_attempts(self, auth_service, mock_repository, valid_user):
        """Test account locks after too many failed attempts."""
        valid_user.failed_login_attempts = 4  # One below threshold
        request = LoginRequest(
            email="user@example.com",
            password="WrongPassword123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = False

            with pytest.raises(TooManyFailedAttemptsError) as exc_info:
                auth_service.login(request)

            assert "too many failed attempts" in str(exc_info.value).lower()

            # Verify account was locked
            mock_repository.lock_account.assert_called_once_with("user_123")

    def test_login_resets_failed_attempts_on_success(self, auth_service, mock_repository, valid_user):
        """Test successful login resets failed attempt counter."""
        valid_user.failed_login_attempts = 3
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response is not None
            mock_repository.reset_failed_attempts.assert_called_once_with("user_123")

    def test_login_rate_limited(self, auth_service, mock_rate_limiter):
        """Test login is rate limited."""
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_rate_limiter.check_rate_limit.return_value = False

        with pytest.raises((InvalidCredentialsError, Exception)) as exc_info:
            auth_service.login(request)

        assert "rate limit" in str(exc_info.value).lower() or "exceeded" in str(exc_info.value).lower()

    def test_login_creates_audit_log(self, auth_service, mock_repository, valid_user):
        """Test successful login creates audit log."""
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            with patch('src.amplihack.auth.services.AuditLogger') as mock_audit:
                response = auth_service.login(request)

                mock_audit.log_successful_login.assert_called_once_with(
                    user_id="user_123",
                    ip_address=request.ip_address,
                    user_agent=request.user_agent,
                )

    def test_login_failed_audit_log(self, auth_service, mock_repository, valid_user):
        """Test failed login creates audit log."""
        request = LoginRequest(
            email="user@example.com",
            password="WrongPassword123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = False

            with patch('src.amplihack.auth.services.AuditLogger') as mock_audit:
                with pytest.raises(InvalidCredentialsError):
                    auth_service.login(request)

                mock_audit.log_failed_login.assert_called_once_with(
                    email="user@example.com",
                    reason="invalid_password",
                    ip_address=request.ip_address,
                    user_agent=request.user_agent,
                )

    def test_login_with_remember_me(self, auth_service, mock_repository, mock_token_service, valid_user):
        """Test login with remember me extends token expiry."""
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
            remember_me=True,
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response.expires_in == 604800  # 7 days for remember me

    def test_login_case_insensitive_email(self, auth_service, mock_repository, valid_user):
        """Test login is case-insensitive for email."""
        request = LoginRequest(
            email="USER@EXAMPLE.COM",  # Uppercase
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response is not None
            # Verify email was normalized to lowercase
            mock_repository.find_by_email.assert_called_with("user@example.com")

    def test_login_with_2fa_enabled(self, auth_service, mock_repository, valid_user):
        """Test login returns 2FA challenge when enabled."""
        valid_user.two_factor_enabled = True
        request = LoginRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = valid_user

        with patch('src.amplihack.auth.services.PasswordService') as mock_pwd:
            mock_pwd.return_value.verify_password.return_value = True

            response = auth_service.login(request)

            assert response.requires_2fa is True
            assert response.challenge_token is not None
            assert response.access_token is None  # No access token until 2FA complete