"""
Contract validation tests for JWT authentication API.
Ensures implementation matches OpenAPI specification exactly.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any
from pydantic import ValidationError

from ..models.requests import RegisterRequest, LoginRequest, RevokeRequest
from ..models.responses import (
    UserResponse, LoginResponse, RefreshResponse,
    VerifyResponse, ErrorResponse, MessageResponse
)
from ..validators.email import EmailValidator
from ..validators.password import PasswordValidator
from ..validators.token import TokenValidator
from ..constants.error_codes import ErrorCode


class TestOpenAPIContract:
    """Validate models against OpenAPI specification."""

    @pytest.fixture
    def openapi_spec(self) -> Dict[str, Any]:
        """Load OpenAPI specification."""
        spec_path = Path(__file__).parent.parent.parent / "openapi.yaml"
        with open(spec_path, 'r') as file:
            return yaml.safe_load(file)

    def test_register_request_schema(self):
        """Test RegisterRequest matches OpenAPI schema."""
        # Valid request
        valid_data = {
            "email": "user@example.com",
            "password": "SecureP@ss123",
            "username": "john_doe"
        }
        request = RegisterRequest(**valid_data)
        assert request.email == "user@example.com"
        assert request.username == "john_doe"

        # Invalid email
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="invalid-email",
                password="SecureP@ss123",
                username="john_doe"
            )

        # Weak password
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="weak",
                username="john_doe"
            )

        # Invalid username
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com",
                password="SecureP@ss123",
                username="john@doe!"  # Special chars not allowed
            )

    def test_login_request_schema(self):
        """Test LoginRequest matches OpenAPI schema."""
        valid_data = {
            "email": "user@example.com",
            "password": "SecureP@ss123"
        }
        request = LoginRequest(**valid_data)
        assert request.email == "user@example.com"

        # Missing field
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

    def test_revoke_request_schema(self):
        """Test RevokeRequest matches OpenAPI schema."""
        # With reason
        request = RevokeRequest(
            token_id="550e8400-e29b-41d4-a716-446655440000",
            reason="Security breach"
        )
        assert request.reason == "Security breach"

        # Without reason (optional)
        request = RevokeRequest(
            token_id="550e8400-e29b-41d4-a716-446655440000"
        )
        assert request.reason is None

        # Invalid UUID
        with pytest.raises(ValidationError):
            RevokeRequest(token_id="not-a-uuid")

    def test_error_response_structure(self):
        """Test ErrorResponse matches OpenAPI schema."""
        # All error codes should produce valid responses
        for code in ErrorCode:
            error = ErrorResponse(
                error={
                    "code": code.value,
                    "message": "Test message",
                    "details": {"field": "test"},
                    "request_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            )
            assert error.error.code == code.value

    def test_rate_limit_headers(self, openapi_spec):
        """Test rate limit headers match specification."""
        headers = openapi_spec["components"]["headers"]

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

        # Verify header schemas
        limit_header = headers["X-RateLimit-Limit"]["schema"]
        assert limit_header["type"] == "integer"
        assert limit_header["example"] == 5


class TestValidators:
    """Test validation utilities."""

    def test_email_validator(self):
        """Test email validation rules."""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.user+tag@example.co.uk",
            "123@test.org"
        ]
        for email in valid_emails:
            valid, error = EmailValidator.validate(email)
            assert valid, f"Email {email} should be valid"

        # Invalid emails
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user..name@example.com",  # Consecutive dots
            "a" * 256 + "@test.com"  # Too long
        ]
        for email in invalid_emails:
            valid, error = EmailValidator.validate(email)
            assert not valid, f"Email {email} should be invalid"

    def test_password_validator(self):
        """Test password strength requirements."""
        # Valid passwords
        valid_passwords = [
            "SecureP@ss123",
            "MyP@ssw0rd!",
            "Test123$Password"
        ]
        for password in valid_passwords:
            valid, error = PasswordValidator.validate(password)
            assert valid, f"Password should be valid: {error}"

        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nocapitals123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No digits
            "NoSpecial123",  # No special chars
            "a" * 129  # Too long
        ]
        for password in invalid_passwords:
            valid, error = PasswordValidator.validate(password)
            assert not valid, f"Password should be invalid"

    def test_token_validator(self):
        """Test JWT token format validation."""
        # Valid JWT format
        valid_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        valid, error = TokenValidator.validate_format(valid_token)
        assert valid

        # Valid with Bearer prefix
        valid, error = TokenValidator.validate_format(f"Bearer {valid_token}")
        assert valid

        # Invalid formats
        invalid_tokens = [
            "not.a.token",
            "only.two",
            "invalid-characters!@#",
            ""
        ]
        for token in invalid_tokens:
            valid, error = TokenValidator.validate_format(token)
            assert not valid

    def test_token_extraction(self):
        """Test Bearer token extraction."""
        token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        auth_header = f"Bearer {token}"

        extracted = TokenValidator.extract_bearer_token(auth_header)
        assert extracted == token

        # Invalid formats
        assert TokenValidator.extract_bearer_token("Basic token") is None
        assert TokenValidator.extract_bearer_token("Bearer") is None
        assert TokenValidator.extract_bearer_token("") is None


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test bcrypt hashing and verification."""
        password = "SecureP@ss123"

        # Hash password
        hashed = PasswordValidator.hash(password)
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hash length

        # Verify correct password
        assert PasswordValidator.verify(password, hashed)

        # Verify incorrect password
        assert not PasswordValidator.verify("WrongPassword", hashed)

        # Each hash should be unique (due to salt)
        hashed2 = PasswordValidator.hash(password)
        assert hashed != hashed2
        assert PasswordValidator.verify(password, hashed2)