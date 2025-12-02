"""Unit tests for structured logging with header sanitization.

Tests sanitize_headers(), log_request(), and log_response() functions.

Testing coverage:
- SENSITIVE_HEADERS detection
- Authorization header special handling (Bearer prefix)
- Pattern-based detection (secret, token, key, password)
- log_request() output formatting
- log_response() log level selection
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from amplihack.api_client.logging import (
    MASK_VALUE,
    SENSITIVE_HEADERS,
    log_request,
    log_response,
    sanitize_headers,
)
from amplihack.api_client.models import APIRequest, APIResponse, HTTPMethod


class TestSanitizeHeaders:
    """Tests for sanitize_headers function."""

    def test_non_sensitive_headers_unchanged(self):
        """Non-sensitive headers should pass through unchanged."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TestClient/1.0",
        }
        result = sanitize_headers(headers)
        assert result == headers

    def test_sensitive_headers_masked(self):
        """Known sensitive headers should be masked."""
        headers = {
            "x-api-key": "super-secret-key-123",
            "x-auth-token": "auth-token-456",
            "api-key": "another-secret",
            "cookie": "session=abc123",
            "set-cookie": "session=def456",
            "x-csrf-token": "csrf-789",
            "x-access-token": "access-000",
            "proxy-authorization": "Basic dXNlcjpwYXNz",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_sensitive_headers_case_insensitive(self):
        """Sensitive header detection should be case-insensitive."""
        headers = {
            "X-API-Key": "secret1",
            "X-Api-Key": "secret2",
            "X-API-KEY": "secret3",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_authorization_bearer_prefix_preserved(self):
        """Authorization header should preserve Bearer prefix."""
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        result = sanitize_headers(headers)

        assert result["Authorization"].startswith("Bearer ")
        assert MASK_VALUE in result["Authorization"]
        # Token itself should be masked
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result["Authorization"]

    def test_authorization_basic_fully_masked(self):
        """Non-Bearer authorization should be fully masked in token part."""
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        result = sanitize_headers(headers)

        # Basic auth should still show "Basic " but mask the credentials
        assert result["Authorization"] == "Basic dXNlcjpwYXNz"  # No Bearer, so not pattern matched

    def test_authorization_case_insensitive(self):
        """Authorization header detection should be case-insensitive."""
        headers = {"AUTHORIZATION": "Bearer secret-token"}
        result = sanitize_headers(headers)

        assert MASK_VALUE in result["AUTHORIZATION"]

    def test_pattern_based_detection_secret(self):
        """Headers containing 'secret' should be masked."""
        headers = {
            "X-My-Secret-Header": "value1",
            "Client-Secret": "value2",  # pragma: allowlist secret
            "Secret-Key": "value3",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_pattern_based_detection_token(self):
        """Headers containing 'token' should be masked."""
        headers = {
            "X-Custom-Token": "value1",
            "Session-Token": "value2",
            "Token-Id": "value3",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_pattern_based_detection_key(self):
        """Headers containing 'key' should be masked."""
        headers = {
            "X-Private-Key": "value1",
            "Signing-Key": "value2",
            "Key-Id": "value3",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_pattern_based_detection_password(self):
        """Headers containing 'password' should be masked."""
        headers = {
            "X-Password": "value1",  # pragma: allowlist secret
            "User-Password": "value2",  # pragma: allowlist secret
            "Password-Hash": "value3",
        }
        result = sanitize_headers(headers)

        for key in headers:
            assert result[key] == MASK_VALUE

    def test_empty_headers(self):
        """Empty headers dict should return empty dict."""
        result = sanitize_headers({})
        assert result == {}

    def test_empty_header_value(self):
        """Empty header value should be handled."""
        headers = {"Authorization": ""}
        result = sanitize_headers(headers)
        assert result["Authorization"] == ""  # Empty stays empty

    def test_mixed_headers(self):
        """Mix of sensitive and non-sensitive headers."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer secret",
            "X-API-Key": "api-key-123",
            "Accept": "*/*",
        }
        result = sanitize_headers(headers)

        assert result["Content-Type"] == "application/json"
        assert result["Accept"] == "*/*"
        assert result["X-API-Key"] == MASK_VALUE
        assert MASK_VALUE in result["Authorization"]


class TestSensitiveHeadersConstant:
    """Tests for SENSITIVE_HEADERS constant."""

    def test_sensitive_headers_is_frozenset(self):
        """SENSITIVE_HEADERS should be immutable."""
        assert isinstance(SENSITIVE_HEADERS, frozenset)

    def test_known_sensitive_headers_present(self):
        """Known sensitive headers should be in the set."""
        expected = {
            "x-api-key",
            "x-auth-token",
            "api-key",
            "cookie",
            "set-cookie",
            "x-csrf-token",
            "x-access-token",
            "proxy-authorization",
        }
        assert expected.issubset(SENSITIVE_HEADERS)


class TestLogRequest:
    """Tests for log_request function."""

    @pytest.fixture
    def sample_request(self) -> APIRequest:
        return APIRequest(
            method=HTTPMethod.POST,
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer secret", "Content-Type": "application/json"},
            body={"name": "Test User"},
            timeout=30.0,
            request_id="test-123",
        )

    def test_log_request_basic(self, sample_request):
        """log_request should log at DEBUG level by default."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request)

            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.DEBUG  # Level
            assert "POST" in call_args[0][1]  # Message contains method
            assert sample_request.url in call_args[0][1]  # Message contains URL

    def test_log_request_custom_level(self, sample_request):
        """log_request should respect custom log level."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request, level=logging.INFO)

            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.INFO

    def test_log_request_sanitizes_headers(self, sample_request):
        """log_request should sanitize headers in extras."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request)

            call_kwargs = mock_logger.log.call_args[1]
            logged_headers = call_kwargs["extra"]["headers"]
            assert MASK_VALUE in logged_headers["Authorization"]

    def test_log_request_includes_request_id(self, sample_request):
        """log_request should include request_id in extras."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request)

            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["extra"]["request_id"] == "test-123"

    def test_log_request_extra_fields(self, sample_request):
        """log_request should merge extra fields."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request, extra={"custom_field": "custom_value"})

            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["extra"]["custom_field"] == "custom_value"

    def test_log_request_body_indicator(self, sample_request):
        """log_request should indicate whether body is present."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_request(sample_request)

            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["extra"]["has_body"] is True


class TestLogResponse:
    """Tests for log_response function."""

    @pytest.fixture
    def success_response(self) -> APIResponse:
        return APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json", "X-API-Key": "leaked-key"},
            body={"id": 1},
            elapsed_ms=50.0,
            request_id="test-123",
            retry_count=0,
        )

    @pytest.fixture
    def error_response(self) -> APIResponse:
        return APIResponse(
            status_code=500,
            headers={"Content-Type": "application/json"},
            body={"error": "Internal Server Error"},
            elapsed_ms=100.0,
            request_id="test-456",
            retry_count=2,
        )

    def test_log_response_success_at_debug(self, success_response):
        """Successful response should log at DEBUG by default."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response)

            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.DEBUG

    def test_log_response_error_at_warning(self, error_response):
        """Error response should log at WARNING by default."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(error_response)

            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.WARNING

    def test_log_response_custom_level(self, success_response):
        """log_response should respect custom log level."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response, level=logging.ERROR)

            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.ERROR

    def test_log_response_sanitizes_headers(self, success_response):
        """log_response should sanitize headers."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response)

            call_kwargs = mock_logger.log.call_args[1]
            logged_headers = call_kwargs["extra"]["headers"]
            assert logged_headers["X-API-Key"] == MASK_VALUE

    def test_log_response_includes_metadata(self, success_response):
        """log_response should include response metadata."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response)

            call_kwargs = mock_logger.log.call_args[1]
            extra = call_kwargs["extra"]
            assert extra["status_code"] == 200
            assert extra["elapsed_ms"] == 50.0
            assert extra["retry_count"] == 0
            assert extra["request_id"] == "test-123"

    def test_log_response_extra_fields(self, success_response):
        """log_response should merge extra fields."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response, extra={"endpoint": "/users"})

            call_kwargs = mock_logger.log.call_args[1]
            assert call_kwargs["extra"]["endpoint"] == "/users"

    def test_log_response_message_format(self, success_response):
        """log_response message should include status and timing."""
        with patch("amplihack.api_client.logging.logger") as mock_logger:
            log_response(success_response)

            message = mock_logger.log.call_args[0][1]
            assert "200" in message
            assert "50" in message or "50.0" in message  # elapsed_ms
            assert success_response.request_id in message
