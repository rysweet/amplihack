"""Unit tests for API client data models.

Tests the HTTPMethod enum, RetryConfig, APIRequest, and APIResponse dataclasses.
Validates immutability, defaults, and property behavior.

Testing coverage:
- HTTPMethod: All values, string conversion
- RetryConfig: Default values, custom values, frozen behavior
- APIRequest: Field defaults, request_id generation, frozen behavior
- APIResponse: Properties (is_success, is_rate_limited), frozen behavior
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from amplihack.api_client.models import (
    APIRequest,
    APIResponse,
    HTTPMethod,
    RetryConfig,
)


class TestHTTPMethod:
    """Tests for HTTPMethod enum."""

    def test_all_methods_exist(self):
        """All standard HTTP methods should be defined."""
        expected = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        actual = {m.value for m in HTTPMethod}
        assert actual == expected

    def test_method_values_are_uppercase(self):
        """HTTP method values should be uppercase strings."""
        for method in HTTPMethod:
            assert method.value == method.value.upper()
            assert isinstance(method.value, str)

    def test_method_from_string(self):
        """Should be able to get method from string value."""
        assert HTTPMethod("GET") == HTTPMethod.GET
        assert HTTPMethod("POST") == HTTPMethod.POST

    def test_invalid_method_raises(self):
        """Invalid method string should raise ValueError."""
        with pytest.raises(ValueError):
            HTTPMethod("INVALID")


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self):
        """Default values should be sensible."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.multiplier == 2.0
        assert config.max_delay == 60.0
        assert config.jitter == 0.1
        assert 429 in config.retry_on_status
        assert 500 in config.retry_on_status

    def test_custom_values(self):
        """Custom values should override defaults."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            multiplier=3.0,
            max_delay=120.0,
            jitter=0.2,
            retry_on_status=(503, 504),
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.multiplier == 3.0
        assert config.max_delay == 120.0
        assert config.jitter == 0.2
        assert config.retry_on_status == (503, 504)

    def test_frozen_immutability(self):
        """RetryConfig should be immutable (frozen dataclass)."""
        config = RetryConfig()
        with pytest.raises(FrozenInstanceError):
            config.max_attempts = 10  # type: ignore

    def test_zero_attempts_allowed(self):
        """Zero max_attempts should be allowed (no retries)."""
        config = RetryConfig(max_attempts=0)
        assert config.max_attempts == 0

    def test_zero_jitter_allowed(self):
        """Zero jitter should disable randomness."""
        config = RetryConfig(jitter=0.0)
        assert config.jitter == 0.0


class TestAPIRequest:
    """Tests for APIRequest dataclass."""

    def test_minimal_request(self):
        """Minimal request with only required fields."""
        request = APIRequest(method=HTTPMethod.GET, url="https://api.example.com")
        assert request.method == HTTPMethod.GET
        assert request.url == "https://api.example.com"
        assert request.headers == {}
        assert request.body is None
        assert request.params is None
        assert request.timeout == 30.0
        assert len(request.request_id) == 8  # UUID truncated to 8 chars

    def test_full_request(self):
        """Request with all fields populated."""
        request = APIRequest(
            method=HTTPMethod.POST,
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            body={"name": "Test User"},
            params={"include": "profile"},
            timeout=60.0,
            request_id="custom-id",
        )
        assert request.method == HTTPMethod.POST
        assert request.headers == {"Authorization": "Bearer token"}
        assert request.body == {"name": "Test User"}
        assert request.params == {"include": "profile"}
        assert request.timeout == 60.0
        assert request.request_id == "custom-id"

    def test_request_id_uniqueness(self):
        """Each request should get a unique ID."""
        requests = [
            APIRequest(method=HTTPMethod.GET, url="https://api.example.com") for _ in range(100)
        ]
        ids = {r.request_id for r in requests}
        assert len(ids) == 100  # All unique

    def test_frozen_immutability(self):
        """APIRequest should be immutable."""
        request = APIRequest(method=HTTPMethod.GET, url="https://api.example.com")
        with pytest.raises(FrozenInstanceError):
            request.url = "https://other.com"  # type: ignore

    def test_empty_url_allowed(self):
        """Empty URL should be allowed (validation is caller's responsibility)."""
        request = APIRequest(method=HTTPMethod.GET, url="")
        assert request.url == ""


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_success_response(self):
        """Successful response with 2xx status code."""
        response = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"data": "test"},
            elapsed_ms=50.0,
            request_id="test-123",
        )
        assert response.status_code == 200
        assert response.is_success
        assert not response.is_rate_limited
        assert response.retry_count == 0

    def test_error_response(self):
        """Error response with 4xx/5xx status code."""
        response = APIResponse(
            status_code=500,
            headers={},
            body="Internal Server Error",
            elapsed_ms=100.0,
            request_id="test-123",
        )
        assert not response.is_success
        assert not response.is_rate_limited

    def test_rate_limited_response(self):
        """429 rate limited response."""
        response = APIResponse(
            status_code=429,
            headers={"Retry-After": "60"},
            body={"error": "rate_limited"},
            elapsed_ms=10.0,
            request_id="test-123",
        )
        assert not response.is_success
        assert response.is_rate_limited

    def test_is_success_boundary_values(self):
        """Test is_success at boundary status codes."""
        # 199 should be False
        response_199 = APIResponse(
            status_code=199, headers={}, body="", elapsed_ms=0, request_id="test"
        )
        assert not response_199.is_success

        # 200 should be True
        response_200 = APIResponse(
            status_code=200, headers={}, body="", elapsed_ms=0, request_id="test"
        )
        assert response_200.is_success

        # 299 should be True
        response_299 = APIResponse(
            status_code=299, headers={}, body="", elapsed_ms=0, request_id="test"
        )
        assert response_299.is_success

        # 300 should be False
        response_300 = APIResponse(
            status_code=300, headers={}, body="", elapsed_ms=0, request_id="test"
        )
        assert not response_300.is_success

    def test_retry_count_tracking(self):
        """Response should track retry count."""
        response = APIResponse(
            status_code=200,
            headers={},
            body="",
            elapsed_ms=0,
            request_id="test",
            retry_count=3,
        )
        assert response.retry_count == 3

    def test_string_body_allowed(self):
        """Body can be string or dict."""
        response_str = APIResponse(
            status_code=200,
            headers={},
            body="plain text response",
            elapsed_ms=0,
            request_id="test",
        )
        assert response_str.body == "plain text response"

        response_dict = APIResponse(
            status_code=200,
            headers={},
            body={"key": "value"},
            elapsed_ms=0,
            request_id="test",
        )
        assert response_dict.body == {"key": "value"}

    def test_frozen_immutability(self):
        """APIResponse should be immutable."""
        response = APIResponse(
            status_code=200, headers={}, body="", elapsed_ms=0, request_id="test"
        )
        with pytest.raises(FrozenInstanceError):
            response.status_code = 500  # type: ignore
