"""
Unit tests for user registration functionality.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import re
from typing import Dict, Any

# Import the modules to be tested
from src.amplihack.auth.models import User, RegisterRequest
from src.amplihack.auth.services import AuthenticationService, PasswordService
from src.amplihack.auth.exceptions import (
    UserAlreadyExistsError,
    UserError,
)
from src.amplihack.auth.repository import UserRepository


class TestUserRegistrationValidation:
    """Test user registration input validation."""

    def test_registration_request_structure(self):
        """Test that registration request has required fields."""
        request = RegisterRequest(
            email="user@example.com",
            password="MyP@ssw0rd123!",
            username="johndoe",
        )

        assert request.email == "user@example.com"
        assert request.password == "MyP@ssw0rd123!"
        assert request.username == "johndoe"

    def test_valid_registration_request(self):
        """Test validation of complete registration request."""
        request = RegisterRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        assert request is not None
        assert request.email == "user@example.com"
        assert request.username == "johndoe"

    def test_registration_request_missing_email(self):
        """Test that missing email is caught."""
        with pytest.raises((ValueError, TypeError)):
            request = RegisterRequest(
                email=None,
                username="johndoe",
                password="MyP@ssw0rd123!",
            )

    def test_registration_request_missing_username(self):
        """Test that missing username is caught."""
        with pytest.raises((ValueError, TypeError)):
            request = RegisterRequest(
                email="user@example.com",
                username=None,
                password="MyP@ssw0rd123!",
            )

    def test_registration_request_missing_password(self):
        """Test that missing password is caught."""
        with pytest.raises((ValueError, TypeError)):
            request = RegisterRequest(
                email="user@example.com",
                username="johndoe",
                password=None,
            )


class TestPasswordService:
    """Test password hashing and verification."""

    @pytest.fixture
    def password_service(self):
        """Create a PasswordService instance."""
        return PasswordService()

    def test_hash_password_creates_hash(self, password_service):
        """Test that password hashing creates a hash string."""
        password = "MyP@ssw0rd123!"
        hashed = password_service.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # Should be a long hash

    def test_hash_password_creates_different_hashes(self, password_service):
        """Test that same password creates different hashes (salt)."""
        password = "MyP@ssw0rd123!"
        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self, password_service):
        """Test password verification with correct password."""
        password = "MyP@ssw0rd123!"
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, password_service):
        """Test password verification with incorrect password."""
        password = "MyP@ssw0rd123!"
        wrong_password = "WrongP@ssw0rd123!"
        hashed = password_service.hash_password(password)

        assert password_service.verify_password(wrong_password, hashed) is False

    def test_hash_password_empty(self, password_service):
        """Test that empty password raises error."""
        with pytest.raises(ValueError):
            password_service.hash_password("")

    def test_hash_password_none(self, password_service):
        """Test that None password raises error."""
        with pytest.raises(ValueError):
            password_service.hash_password(None)


class TestUserService:
    """Test user service registration logic."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_password_service(self):
        """Create a mock password service."""
        service = Mock(spec=PasswordService)
        service.hash_password.return_value = "hashed_password_123"
        return service

    @pytest.fixture
    def mock_validator(self):
        """Create a mock validator."""
        validator = Mock(spec=UserValidator)
        validator.validate_registration.return_value = True
        return validator

    @pytest.fixture
    def user_service(self, mock_repository, mock_password_service, mock_validator):
        """Create a UserService instance with mocks."""
        return UserService(
            repository=mock_repository,
            password_service=mock_password_service,
            validator=mock_validator,
        )

    def test_register_user_success(self, user_service, mock_repository):
        """Test successful user registration."""
        request = UserRegistrationRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
            first_name="John",
            last_name="Doe",
        )

        mock_repository.find_by_email.return_value = None
        mock_repository.find_by_username.return_value = None
        mock_repository.save.return_value = User(
            id="user_123",
            email=request.email,
            username=request.username,
            password_hash="hashed_password_123",
            first_name=request.first_name,
            last_name=request.last_name,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

        user = user_service.register_user(request)

        assert user is not None
        assert user.email == request.email
        assert user.username == request.username
        assert user.password_hash == "hashed_password_123"
        assert user.is_active is True
        mock_repository.save.assert_called_once()

    def test_register_user_duplicate_email(self, user_service, mock_repository):
        """Test registration fails with duplicate email."""
        request = UserRegistrationRequest(
            email="existing@example.com",
            username="newuser",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = User(
            id="existing_user",
            email="existing@example.com",
            username="existinguser",
            password_hash="hash",
        )

        with pytest.raises(UserAlreadyExistsError) as exc_info:
            user_service.register_user(request)

        assert "email already registered" in str(exc_info.value).lower()

    def test_register_user_duplicate_username(self, user_service, mock_repository):
        """Test registration fails with duplicate username."""
        request = UserRegistrationRequest(
            email="new@example.com",
            username="existinguser",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = None
        mock_repository.find_by_username.return_value = User(
            id="existing_user",
            email="other@example.com",
            username="existinguser",
            password_hash="hash",
        )

        with pytest.raises(UserAlreadyExistsError) as exc_info:
            user_service.register_user(request)

        assert "username already taken" in str(exc_info.value).lower()

    def test_register_user_validation_fails(self, user_service, mock_validator):
        """Test registration fails when validation fails."""
        request = UserRegistrationRequest(
            email="invalid",
            username="u",
            password="weak",
        )

        mock_validator.validate_registration.side_effect = InvalidEmailError("Invalid email")

        with pytest.raises(InvalidEmailError):
            user_service.register_user(request)

    def test_register_user_repository_error(self, user_service, mock_repository):
        """Test registration handles repository errors."""
        request = UserRegistrationRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = None
        mock_repository.find_by_username.return_value = None
        mock_repository.save.side_effect = Exception("Database error")

        with pytest.raises(RegistrationFailedError) as exc_info:
            user_service.register_user(request)

        assert "registration failed" in str(exc_info.value).lower()

    def test_register_user_creates_audit_log(self, user_service, mock_repository):
        """Test that user registration creates an audit log entry."""
        request = UserRegistrationRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = None
        mock_repository.find_by_username.return_value = None
        mock_repository.save.return_value = User(
            id="user_123",
            email=request.email,
            username=request.username,
            password_hash="hashed",
        )

        with patch('src.amplihack.auth.services.AuditLogger') as mock_audit:
            user = user_service.register_user(request)
            mock_audit.log_user_registration.assert_called_once_with(user.id)

    def test_register_user_sends_welcome_email(self, user_service, mock_repository):
        """Test that successful registration sends welcome email."""
        request = UserRegistrationRequest(
            email="user@example.com",
            username="johndoe",
            password="MyP@ssw0rd123!",
        )

        mock_repository.find_by_email.return_value = None
        mock_repository.find_by_username.return_value = None
        mock_repository.save.return_value = User(
            id="user_123",
            email=request.email,
            username=request.username,
            password_hash="hashed",
        )

        with patch('src.amplihack.auth.services.EmailService') as mock_email:
            user = user_service.register_user(request)
            mock_email.send_welcome_email.assert_called_once_with(
                email=user.email,
                username=user.username,
            )

    @pytest.mark.parametrize("reserved_username", [
        "admin",
        "root",
        "administrator",
        "system",
        "api",
        "auth",
        "login",
        "register",
        "test",
    ])
    def test_register_user_reserved_usernames(self, user_service, reserved_username):
        """Test that reserved usernames are rejected."""
        request = UserRegistrationRequest(
            email="user@example.com",
            username=reserved_username,
            password="MyP@ssw0rd123!",
        )

        with pytest.raises(InvalidUsernameError) as exc_info:
            user_service.register_user(request)

        assert "reserved username" in str(exc_info.value).lower()