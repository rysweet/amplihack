"""Tests for API client models and dataclasses - TDD approach.

Focus on Request/Response models, configuration, and serialization.
"""

import json
from datetime import datetime, timedelta

import pytest

from amplihack.api_client.models import (
    APIConfig,
    ErrorDetail,
    RateLimitInfo,
    Request,
    RequestID,
    Response,
    RetryConfig,
)


class TestAPIConfig:
    """Unit tests for APIConfig model."""

    def test_minimal_config(self):
        """Test creating config with only required fields."""
        config = APIConfig(base_url="https://api.example.com")
        assert config.base_url == "https://api.example.com"
        assert config.timeout == 30  # Default
        assert config.max_retries == 3  # Default
        assert config.headers == {}  # Default empty dict
        assert config.user_agent.startswith("amplihack/")

    def test_full_config(self):
        """Test creating config with all fields."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            retry_delay=2.0,
            retry_multiplier=3.0,
            max_retry_delay=120,
            headers={"X-API-Key": "secret"},
            user_agent="CustomApp/1.0",
            verify_ssl=False,
            proxy="http://proxy.example.com:8080",
            follow_redirects=False,
            log_level="DEBUG",
        )
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.retry_multiplier == 3.0
        assert config.max_retry_delay == 120
        assert config.headers["X-API-Key"] == "secret"
        assert config.user_agent == "CustomApp/1.0"
        assert config.verify_ssl is False
        assert config.proxy == "http://proxy.example.com:8080"
        assert config.follow_redirects is False
        assert config.log_level == "DEBUG"

    def test_config_validation(self):
        """Test config field validation."""
        # Invalid URL
        with pytest.raises(ValueError) as exc_info:
            APIConfig(base_url="not-a-url")
        assert "Invalid URL" in str(exc_info.value)

        # Negative timeout
        with pytest.raises(ValueError) as exc_info:
            APIConfig(base_url="https://api.example.com", timeout=-1)
        assert "Timeout must be positive" in str(exc_info.value)

        # Negative max_retries
        with pytest.raises(ValueError) as exc_info:
            APIConfig(base_url="https://api.example.com", max_retries=-1)
        assert "Max retries must be non-negative" in str(exc_info.value)

        # Invalid log level
        with pytest.raises(ValueError) as exc_info:
            APIConfig(base_url="https://api.example.com", log_level="INVALID")
        assert "Invalid log level" in str(exc_info.value)

    def test_config_copy_with_updates(self):
        """Test creating a copy of config with updates."""
        original = APIConfig(
            base_url="https://api.example.com",
            headers={"X-API-Key": "original"},
        )

        # Create copy with updates
        updated = original.copy_with(
            timeout=90,
            headers={"X-API-Key": "updated", "X-New": "value"},
        )

        # Original unchanged
        assert original.timeout == 30
        assert original.headers["X-API-Key"] == "original"
        assert "X-New" not in original.headers

        # Updated has new values
        assert updated.base_url == "https://api.example.com"  # Inherited
        assert updated.timeout == 90
        assert updated.headers["X-API-Key"] == "updated"
        assert updated.headers["X-New"] == "value"

    def test_config_merge_headers(self):
        """Test merging headers properly."""
        config = APIConfig(
            base_url="https://api.example.com",
            headers={"X-API-Key": "secret", "Accept": "application/json"},
        )

        merged = config.merge_headers({"X-Request-ID": "123", "Accept": "text/plain"})

        # Original unchanged
        assert config.headers["Accept"] == "application/json"

        # Merged has both, with override
        assert merged["X-API-Key"] == "secret"
        assert merged["X-Request-ID"] == "123"
        assert merged["Accept"] == "text/plain"  # Overridden


class TestRetryConfig:
    """Unit tests for RetryConfig model."""

    def test_retry_config_defaults(self):
        """Test RetryConfig with default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.retry_multiplier == 2.0
        assert config.max_retry_delay == 60.0
        assert config.retry_on_status == {429, 500, 502, 503, 504}

    def test_retry_config_custom(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_retries=5,
            retry_delay=0.5,
            retry_multiplier=3.0,
            max_retry_delay=30.0,
            retry_on_status={500, 503},
        )
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.retry_multiplier == 3.0
        assert config.max_retry_delay == 30.0
        assert config.retry_on_status == {500, 503}

    def test_calculate_delay(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(
            retry_delay=1.0,
            retry_multiplier=2.0,
            max_retry_delay=10.0,
        )

        # First retry: 1.0
        assert config.calculate_delay(0) == 1.0

        # Second retry: 2.0
        assert config.calculate_delay(1) == 2.0

        # Third retry: 4.0
        assert config.calculate_delay(2) == 4.0

        # Fourth retry: 8.0
        assert config.calculate_delay(3) == 8.0

        # Fifth retry: capped at 10.0
        assert config.calculate_delay(4) == 10.0

    def test_should_retry(self):
        """Test determining if a status code should be retried."""
        config = RetryConfig(retry_on_status={429, 503})

        assert config.should_retry(429) is True
        assert config.should_retry(503) is True
        assert config.should_retry(500) is False
        assert config.should_retry(404) is False
        assert config.should_retry(200) is False


class TestRequest:
    """Unit tests for Request model."""

    def test_request_minimal(self):
        """Test Request with minimal fields."""
        request = Request(
            method="GET",
            url="https://api.example.com/test",
        )
        assert request.method == "GET"
        assert request.url == "https://api.example.com/test"
        assert request.headers == {}
        assert request.params == {}
        assert request.json_data is None
        assert request.data is None
        assert request.timeout is None

    def test_request_full(self):
        """Test Request with all fields."""
        request = Request(
            method="POST",
            url="https://api.example.com/users",
            headers={"Content-Type": "application/json"},
            params={"debug": "true"},
            json_data={"name": "Test User"},
            data=b"raw bytes",
            timeout=30,
            request_id="req-123",
        )
        assert request.method == "POST"
        assert request.headers["Content-Type"] == "application/json"
        assert request.params["debug"] == "true"
        assert request.json_data["name"] == "Test User"
        assert request.data == b"raw bytes"
        assert request.timeout == 30
        assert request.request_id == "req-123"

    def test_request_to_dict(self):
        """Test converting Request to dictionary."""
        request = Request(
            method="GET",
            url="https://api.example.com/test",
            headers={"X-API-Key": "secret"},
            params={"page": 1},
        )

        data = request.to_dict()
        assert data["method"] == "GET"
        assert data["url"] == "https://api.example.com/test"
        assert data["headers"]["X-API-Key"] == "secret"
        assert data["params"]["page"] == 1

    def test_request_from_dict(self):
        """Test creating Request from dictionary."""
        data = {
            "method": "POST",
            "url": "https://api.example.com/users",
            "headers": {"Content-Type": "application/json"},
            "json_data": {"name": "Test"},
        }

        request = Request.from_dict(data)
        assert request.method == "POST"
        assert request.url == "https://api.example.com/users"
        assert request.headers["Content-Type"] == "application/json"
        assert request.json_data["name"] == "Test"


class TestResponse:
    """Unit tests for Response model."""

    def test_response_minimal(self):
        """Test Response with minimal fields."""
        request = Request(method="GET", url="https://api.example.com/test")
        response = Response(
            status_code=200,
            headers={},
            data=None,
            request=request,
        )
        assert response.status_code == 200
        assert response.headers == {}
        assert response.data is None
        assert response.request.method == "GET"
        assert response.elapsed is None
        assert response.raw_content is None

    def test_response_full(self):
        """Test Response with all fields."""
        request = Request(method="GET", url="https://api.example.com/test")
        response = Response(
            status_code=201,
            headers={"Content-Type": "application/json"},
            data={"id": 123, "created": True},
            request=request,
            elapsed=timedelta(seconds=0.5),
            raw_content=b'{"id": 123, "created": true}',
        )
        assert response.status_code == 201
        assert response.headers["Content-Type"] == "application/json"
        assert response.data["id"] == 123
        assert response.elapsed.total_seconds() == 0.5
        assert response.raw_content == b'{"id": 123, "created": true}'

    def test_response_properties(self):
        """Test Response computed properties."""
        request = Request(method="GET", url="https://api.example.com/test")

        # Success responses
        for code in [200, 201, 204]:
            response = Response(status_code=code, headers={}, data=None, request=request)
            assert response.is_success is True
            assert response.is_error is False
            assert response.is_client_error is False
            assert response.is_server_error is False

        # Client errors
        for code in [400, 404, 429]:
            response = Response(status_code=code, headers={}, data=None, request=request)
            assert response.is_success is False
            assert response.is_error is True
            assert response.is_client_error is True
            assert response.is_server_error is False

        # Server errors
        for code in [500, 502, 503]:
            response = Response(status_code=code, headers={}, data=None, request=request)
            assert response.is_success is False
            assert response.is_error is True
            assert response.is_client_error is False
            assert response.is_server_error is True

    def test_response_json(self):
        """Test Response JSON parsing."""
        request = Request(method="GET", url="https://api.example.com/test")

        # Valid JSON
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            data=None,
            request=request,
            raw_content=b'{"key": "value"}',
        )
        assert response.json() == {"key": "value"}

        # Invalid JSON
        response = Response(
            status_code=200,
            headers={},
            data=None,
            request=request,
            raw_content=b"not json",
        )
        with pytest.raises(json.JSONDecodeError):
            response.json()

        # No content
        response = Response(
            status_code=204,
            headers={},
            data=None,
            request=request,
            raw_content=None,
        )
        assert response.json() is None

    def test_response_text(self):
        """Test Response text decoding."""
        request = Request(method="GET", url="https://api.example.com/test")

        # UTF-8 text
        response = Response(
            status_code=200,
            headers={},
            data=None,
            request=request,
            raw_content="Hello, 世界".encode(),
        )
        assert response.text() == "Hello, 世界"

        # Different encoding
        response = Response(
            status_code=200,
            headers={},
            data=None,
            request=request,
            raw_content="Hello".encode("latin-1"),
        )
        assert response.text(encoding="latin-1") == "Hello"

        # No content
        response = Response(
            status_code=204,
            headers={},
            data=None,
            request=request,
            raw_content=None,
        )
        assert response.text() == ""


class TestRateLimitInfo:
    """Unit tests for RateLimitInfo model."""

    def test_rate_limit_info(self):
        """Test RateLimitInfo creation and properties."""
        info = RateLimitInfo(
            limit=1000,
            remaining=450,
            reset_time=datetime(2024, 1, 1, 12, 0, 0),
            retry_after=60,
        )
        assert info.limit == 1000
        assert info.remaining == 450
        assert info.reset_time == datetime(2024, 1, 1, 12, 0, 0)
        assert info.retry_after == 60

    def test_rate_limit_from_headers(self):
        """Test parsing RateLimitInfo from response headers."""
        headers = {
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "450",
            "X-RateLimit-Reset": "1704110400",  # 2024-01-01 12:00:00 UTC
            "Retry-After": "60",
        }

        info = RateLimitInfo.from_headers(headers)
        assert info.limit == 1000
        assert info.remaining == 450
        assert info.reset_time == datetime(2024, 1, 1, 12, 0, 0)
        assert info.retry_after == 60

    def test_rate_limit_partial_headers(self):
        """Test parsing with partial rate limit headers."""
        # Only Retry-After
        headers = {"Retry-After": "30"}
        info = RateLimitInfo.from_headers(headers)
        assert info.retry_after == 30
        assert info.limit is None

        # Only rate limit headers
        headers = {
            "X-RateLimit-Limit": "500",
            "X-RateLimit-Remaining": "100",
        }
        info = RateLimitInfo.from_headers(headers)
        assert info.limit == 500
        assert info.remaining == 100
        assert info.retry_after is None

    def test_is_rate_limited(self):
        """Test checking if rate limited."""
        # Has retry_after
        info = RateLimitInfo(retry_after=60)
        assert info.is_rate_limited() is True

        # Zero remaining
        info = RateLimitInfo(limit=1000, remaining=0)
        assert info.is_rate_limited() is True

        # Not limited
        info = RateLimitInfo(limit=1000, remaining=500)
        assert info.is_rate_limited() is False


class TestRequestID:
    """Unit tests for RequestID model."""

    def test_request_id_generation(self):
        """Test automatic request ID generation."""
        req_id = RequestID()
        assert req_id.value is not None
        assert len(req_id.value) == 36  # UUID4 format
        assert req_id.timestamp is not None

    def test_request_id_custom(self):
        """Test custom request ID."""
        req_id = RequestID(value="custom-123")
        assert req_id.value == "custom-123"

    def test_request_id_str(self):
        """Test string representation."""
        req_id = RequestID(value="test-id")
        assert str(req_id) == "test-id"

    def test_request_id_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = [RequestID() for _ in range(100)]
        values = [req_id.value for req_id in ids]
        assert len(set(values)) == 100  # All unique


class TestErrorDetail:
    """Unit tests for ErrorDetail model."""

    def test_error_detail_basic(self):
        """Test ErrorDetail with basic fields."""
        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid email format",
            field="email",
        )
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid email format"
        assert error.field == "email"
        assert error.details is None

    def test_error_detail_with_details(self):
        """Test ErrorDetail with additional details."""
        error = ErrorDetail(
            code="RATE_LIMIT",
            message="Too many requests",
            details={
                "limit": 1000,
                "window": "1h",
                "retry_after": 3600,
            },
        )
        assert error.code == "RATE_LIMIT"
        assert error.details["limit"] == 1000
        assert error.details["retry_after"] == 3600

    def test_error_detail_from_response(self):
        """Test parsing ErrorDetail from API response."""
        response_data = {
            "error": {
                "code": "NOT_FOUND",
                "message": "User not found",
                "details": {"user_id": 123},
            }
        }

        error = ErrorDetail.from_response(response_data)
        assert error.code == "NOT_FOUND"
        assert error.message == "User not found"
        assert error.details["user_id"] == 123

    def test_error_detail_list_from_response(self):
        """Test parsing multiple errors from response."""
        response_data = {
            "errors": [
                {"code": "INVALID_FIELD", "message": "Invalid email", "field": "email"},
                {"code": "REQUIRED", "message": "Name is required", "field": "name"},
            ]
        }

        errors = ErrorDetail.list_from_response(response_data)
        assert len(errors) == 2
        assert errors[0].code == "INVALID_FIELD"
        assert errors[0].field == "email"
        assert errors[1].code == "REQUIRED"
        assert errors[1].field == "name"

    def test_error_detail_to_dict(self):
        """Test converting ErrorDetail to dictionary."""
        error = ErrorDetail(
            code="TEST_ERROR",
            message="Test message",
            field="test_field",
            details={"key": "value"},
        )

        data = error.to_dict()
        assert data["code"] == "TEST_ERROR"
        assert data["message"] == "Test message"
        assert data["field"] == "test_field"
        assert data["details"]["key"] == "value"
