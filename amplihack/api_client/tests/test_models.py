"""Unit tests fer API Client data models.

Tests the APIRequest and APIResponse dataclasses, validation,
helper methods, and JSON parsing.

Testing pyramid: Unit tests (60%)
"""

from datetime import UTC, datetime

import pytest
from amplihack.api_client.exceptions import APIError

# Imports will fail initially - this be TDD!
from amplihack.api_client.models import APIRequest, APIResponse


class TestAPIRequest:
    """Test APIRequest dataclass."""

    def test_api_request_creation_minimal(self) -> None:
        """Verify APIRequest can be created with minimal fields."""
        # Arrange
        method = "GET"
        url = "https://api.example.com/users"

        # Act
        request = APIRequest(method=method, url=url)

        # Assert
        assert request.method == method
        assert request.url == url
        assert request.headers is None
        assert request.body is None
        assert request.timeout is None

    def test_api_request_creation_full(self) -> None:
        """Verify APIRequest stores all fields correctly."""
        # Arrange
        method = "POST"
        url = "https://api.example.com/users"
        headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        body = {"name": "Test User", "email": "test@example.com"}
        timeout = 30.0

        # Act
        request = APIRequest(method=method, url=url, headers=headers, body=body, timeout=timeout)

        # Assert
        assert request.method == method
        assert request.url == url
        assert request.headers == headers
        assert request.body == body
        assert request.timeout == timeout

    def test_api_request_method_uppercase(self) -> None:
        """Verify APIRequest method is stored in uppercase."""
        # Arrange
        method = "post"
        url = "https://api.example.com"

        # Act
        request = APIRequest(method=method, url=url)

        # Assert
        assert request.method == "POST"

    def test_api_request_invalid_method(self) -> None:
        """Verify APIRequest raises error fer invalid HTTP method."""
        # Arrange
        method = "INVALID"
        url = "https://api.example.com"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid HTTP method"):
            APIRequest(method=method, url=url)

    def test_api_request_empty_url(self) -> None:
        """Verify APIRequest raises error fer empty URL."""
        # Arrange
        method = "GET"
        url = ""

        # Act & Assert
        with pytest.raises(ValueError, match="URL cannot be empty"):
            APIRequest(method=method, url=url)


class TestAPIResponse:
    """Test APIResponse dataclass."""

    def test_api_response_creation_minimal(self) -> None:
        """Verify APIResponse can be created with minimal fields."""
        # Arrange
        status_code = 200
        body = "Success"
        url = "https://api.example.com/users"

        # Act
        response = APIResponse(status_code=status_code, body=body, url=url)

        # Assert
        assert response.status_code == status_code
        assert response.body == body
        assert response.url == url
        assert response.headers is None
        assert response.request is None

    def test_api_response_creation_full(self) -> None:
        """Verify APIResponse stores all fields correctly."""
        # Arrange
        status_code = 201
        body = {"id": 123, "name": "Test User"}
        url = "https://api.example.com/users"
        headers = {"Content-Type": "application/json", "X-Request-Id": "abc-123"}
        request = APIRequest(method="POST", url=url)

        # Act
        response = APIResponse(
            status_code=status_code,
            body=body,
            url=url,
            headers=headers,
            request=request,
        )

        # Assert
        assert response.status_code == status_code
        assert response.body == body
        assert response.url == url
        assert response.headers == headers
        assert response.request == request


class TestAPIResponseStatusMethods:
    """Test APIResponse status checking methods."""

    def test_is_success_with_2xx_status(self) -> None:
        """Verify is_success() returns True fer 2xx status codes."""
        # Arrange
        test_cases = [200, 201, 204, 299]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_success() is True, f"Failed fer status {status_code}"

    def test_is_success_with_non_2xx_status(self) -> None:
        """Verify is_success() returns False fer non-2xx status codes."""
        # Arrange
        test_cases = [199, 300, 400, 500]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_success() is False, f"Failed fer status {status_code}"

    def test_is_client_error_with_4xx_status(self) -> None:
        """Verify is_client_error() returns True fer 4xx status codes."""
        # Arrange
        test_cases = [400, 401, 403, 404, 429, 499]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_client_error() is True, f"Failed fer status {status_code}"

    def test_is_client_error_with_non_4xx_status(self) -> None:
        """Verify is_client_error() returns False fer non-4xx status codes."""
        # Arrange
        test_cases = [200, 399, 500]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_client_error() is False, f"Failed fer status {status_code}"

    def test_is_server_error_with_5xx_status(self) -> None:
        """Verify is_server_error() returns True fer 5xx status codes."""
        # Arrange
        test_cases = [500, 502, 503, 504, 599]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_server_error() is True, f"Failed fer status {status_code}"

    def test_is_server_error_with_non_5xx_status(self) -> None:
        """Verify is_server_error() returns False fer non-5xx status codes."""
        # Arrange
        test_cases = [200, 400, 499]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_server_error() is False, f"Failed fer status {status_code}"

    def test_is_rate_limited_with_429_status(self) -> None:
        """Verify is_rate_limited() returns True fer 429 status."""
        # Arrange
        response = APIResponse(status_code=429, body="Rate limited", url="https://api.example.com")

        # Act & Assert
        assert response.is_rate_limited() is True

    def test_is_rate_limited_with_non_429_status(self) -> None:
        """Verify is_rate_limited() returns False fer non-429 status."""
        # Arrange
        test_cases = [200, 400, 500]

        for status_code in test_cases:
            # Act
            response = APIResponse(status_code=status_code, body="", url="https://api.example.com")

            # Assert
            assert response.is_rate_limited() is False, f"Failed fer status {status_code}"


class TestAPIResponseJSONParsing:
    """Test APIResponse JSON parsing methods."""

    def test_json_with_valid_json_string(self) -> None:
        """Verify json() parses valid JSON string body."""
        # Arrange
        body = '{"name": "Test User", "id": 123}'
        response = APIResponse(status_code=200, body=body, url="https://api.example.com")

        # Act
        data = response.json()

        # Assert
        assert data == {"name": "Test User", "id": 123}

    def test_json_with_dict_body(self) -> None:
        """Verify json() returns dict body unchanged."""
        # Arrange
        body = {"name": "Test User", "id": 123}
        response = APIResponse(status_code=200, body=body, url="https://api.example.com")

        # Act
        data = response.json()

        # Assert
        assert data == body

    def test_json_with_invalid_json_raises_error(self) -> None:
        """Verify json() raises error fer invalid JSON."""
        # Arrange
        body = "not valid json {"
        response = APIResponse(status_code=200, body=body, url="https://api.example.com")

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid JSON"):
            response.json()

    def test_json_with_empty_body(self) -> None:
        """Verify json() handles empty body gracefully."""
        # Arrange
        body = ""
        response = APIResponse(status_code=204, body=body, url="https://api.example.com")

        # Act
        data = response.json()

        # Assert
        assert data is None


class TestAPIResponseErrorHandling:
    """Test APIResponse error handling methods."""

    def test_raise_for_status_with_success(self) -> None:
        """Verify raise_for_status() does not raise fer 2xx status."""
        # Arrange
        response = APIResponse(status_code=200, body="Success", url="https://api.example.com")

        # Act & Assert - should not raise
        response.raise_for_status()

    def test_raise_for_status_with_client_error(self) -> None:
        """Verify raise_for_status() raises fer 4xx status."""
        # Arrange
        response = APIResponse(status_code=404, body="Not found", url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError):
            response.raise_for_status()

    def test_raise_for_status_with_server_error(self) -> None:
        """Verify raise_for_status() raises fer 5xx status."""
        # Arrange
        response = APIResponse(status_code=500, body="Server error", url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError):
            response.raise_for_status()


class TestAPIResponseRetryAfter:
    """Test APIResponse Retry-After header extraction."""

    def test_get_retry_after_with_seconds(self) -> None:
        """Verify get_retry_after() parses seconds value."""
        # Arrange
        headers = {"Retry-After": "120"}
        response = APIResponse(
            status_code=429,
            body="Rate limited",
            url="https://api.example.com",
            headers=headers,
        )

        # Act
        retry_after = response.get_retry_after()

        # Assert
        assert retry_after == 120

    def test_get_retry_after_with_http_date(self) -> None:
        """Verify get_retry_after() parses HTTP date format."""
        # Arrange
        # HTTP date: Wed, 21 Oct 2025 07:28:00 GMT (120 seconds from now)
        future_time = datetime.now(UTC).timestamp() + 120
        http_date = datetime.fromtimestamp(future_time, UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
        headers = {"Retry-After": http_date}
        response = APIResponse(
            status_code=429,
            body="Rate limited",
            url="https://api.example.com",
            headers=headers,
        )

        # Act
        retry_after = response.get_retry_after()

        # Assert
        assert retry_after is not None
        assert 115 <= retry_after <= 125  # Allow 5 second margin

    def test_get_retry_after_without_header(self) -> None:
        """Verify get_retry_after() returns None without header."""
        # Arrange
        response = APIResponse(status_code=429, body="Rate limited", url="https://api.example.com")

        # Act
        retry_after = response.get_retry_after()

        # Assert
        assert retry_after is None

    def test_get_retry_after_with_invalid_value(self) -> None:
        """Verify get_retry_after() returns None fer invalid value."""
        # Arrange
        headers = {"Retry-After": "invalid"}
        response = APIResponse(
            status_code=429,
            body="Rate limited",
            url="https://api.example.com",
            headers=headers,
        )

        # Act
        retry_after = response.get_retry_after()

        # Assert
        assert retry_after is None


class TestAPIResponseLogging:
    """Test APIResponse logging methods."""

    def test_to_dict_basic_fields(self) -> None:
        """Verify to_dict() includes basic response fields."""
        # Arrange
        response = APIResponse(status_code=200, body="Success", url="https://api.example.com")

        # Act
        log_dict = response.to_dict()

        # Assert
        assert log_dict["status_code"] == 200
        assert log_dict["url"] == "https://api.example.com"
        assert "body" in log_dict

    def test_to_dict_sanitizes_sensitive_headers(self) -> None:
        """Verify to_dict() redacts sensitive headers."""
        # Arrange
        headers = {
            "Authorization": "Bearer secret-token",
            "X-API-Key": "super-secret-key",
            "Content-Type": "application/json",
        }
        response = APIResponse(
            status_code=200,
            body="Success",
            url="https://api.example.com",
            headers=headers,
        )

        # Act
        log_dict = response.to_dict()

        # Assert
        assert log_dict["headers"]["Authorization"] == "[REDACTED]"
        assert log_dict["headers"]["X-API-Key"] == "[REDACTED]"
        assert log_dict["headers"]["Content-Type"] == "application/json"

    def test_to_dict_truncates_large_body(self) -> None:
        """Verify to_dict() truncates large response bodies."""
        # Arrange
        large_body = "x" * 10000
        response = APIResponse(status_code=200, body=large_body, url="https://api.example.com")

        # Act
        log_dict = response.to_dict()

        # Assert
        assert len(log_dict["body"]) < 10000
        assert "..." in log_dict["body"] or "[truncated]" in str(log_dict)
