"""Unit tests fer API Client main class.

Tests the APIClient class, HTTP methods, retry integration,
rate limiting, logging, and context manager protocol.

Testing pyramid: Unit tests (60%)
"""

from unittest.mock import Mock, patch

import pytest

# Imports will fail initially - this be TDD!
from amplihack.api_client.client import APIClient
from amplihack.api_client.exceptions import (
    APIError,
    InternalServerError,
)
from amplihack.api_client.retry import RetryConfig, RetryStrategy


class TestAPIClientInitialization:
    """Test APIClient initialization and configuration."""

    def test_api_client_default_initialization(self) -> None:
        """Verify APIClient initializes with default values."""
        # Act
        client = APIClient(base_url="https://api.example.com")

        # Assert
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30.0
        assert client.retry_config is not None

    def test_api_client_with_custom_timeout(self) -> None:
        """Verify APIClient accepts custom timeout."""
        # Arrange
        timeout = 60.0

        # Act
        client = APIClient(base_url="https://api.example.com", timeout=timeout)

        # Assert
        assert client.timeout == timeout

    def test_api_client_with_custom_retry_config(self) -> None:
        """Verify APIClient accepts custom retry configuration."""
        # Arrange
        retry_config = RetryConfig(max_attempts=5, initial_delay=2.0)

        # Act
        client = APIClient(base_url="https://api.example.com", retry_config=retry_config)

        # Assert
        assert client.retry_config.max_attempts == 5
        assert client.retry_config.initial_delay == 2.0

    def test_api_client_with_default_headers(self) -> None:
        """Verify APIClient accepts default headers."""
        # Arrange
        headers = {"Authorization": "Bearer token", "User-Agent": "TestClient/1.0"}

        # Act
        client = APIClient(base_url="https://api.example.com", headers=headers)

        # Assert
        assert client.headers == headers


class TestAPIClientHTTPMethods:
    """Test APIClient HTTP method implementations."""

    @patch("requests.request")
    def test_get_request(self, mock_request: Mock) -> None:
        """Verify GET request is executed correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/users")

        # Assert
        mock_request.assert_called_once()
        assert response.status_code == 200

    @patch("requests.request")
    def test_post_request_with_json_body(self, mock_request: Mock) -> None:
        """Verify POST request with JSON body is executed correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 123}'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        body = {"name": "Test User", "email": "test@example.com"}

        # Act
        response = client.post("/users", json=body)

        # Assert
        mock_request.assert_called_once()
        assert response.status_code == 201

    @patch("requests.request")
    def test_put_request_with_body(self, mock_request: Mock) -> None:
        """Verify PUT request with body is executed correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"id": 123, "updated": true}'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        body = {"name": "Updated User"}

        # Act
        response = client.put("/users/123", json=body)

        # Assert
        mock_request.assert_called_once()
        assert response.status_code == 200

    @patch("requests.request")
    def test_delete_request(self, mock_request: Mock) -> None:
        """Verify DELETE request is executed correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.delete("/users/123")

        # Assert
        mock_request.assert_called_once()
        assert response.status_code == 204

    @patch("requests.request")
    def test_patch_request_with_body(self, mock_request: Mock) -> None:
        """Verify PATCH request with body is executed correctly."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"id": 123, "patched": true}'
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        body = {"email": "newemail@example.com"}

        # Act
        response = client.patch("/users/123", json=body)

        # Assert
        mock_request.assert_called_once()
        assert response.status_code == 200


class TestAPIClientRetryLogic:
    """Test APIClient retry logic integration."""

    @patch("requests.request")
    @patch("time.sleep")
    def test_retry_on_500_error(self, mock_sleep: Mock, mock_request: Mock) -> None:
        """Verify client retries on 500 error."""
        # Arrange
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.text = "Server error"
        mock_response_500.headers = {}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = "Success"
        mock_response_200.headers = {}

        # First 2 attempts fail, 3rd succeeds
        mock_request.side_effect = [
            mock_response_500,
            mock_response_500,
            mock_response_200,
        ]

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/users")

        # Assert
        assert mock_request.call_count == 3
        assert response.status_code == 200

    @patch("requests.request")
    @patch("time.sleep")
    def test_retry_exhaustion_raises_error(self, mock_sleep: Mock, mock_request: Mock) -> None:
        """Verify client raises error after retry exhaustion."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(max_attempts=3),
        )

        # Act & Assert
        with pytest.raises(InternalServerError):
            client.get("/users")

        assert mock_request.call_count == 3

    @patch("requests.request")
    @patch("time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep: Mock, mock_request: Mock) -> None:
        """Verify client uses exponential backoff delays."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(
                max_attempts=3, strategy=RetryStrategy.EXPONENTIAL, jitter=False
            ),
        )

        # Act
        with pytest.raises(InternalServerError):
            client.get("/users")

        # Assert - verify sleep was called with exponential delays
        assert mock_sleep.call_count == 2  # 2 retries = 2 sleeps
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == pytest.approx(2.0, rel=0.1)  # 1 * 2^1
        assert sleep_calls[1] == pytest.approx(4.0, rel=0.1)  # 1 * 2^2


class TestAPIClientRateLimiting:
    """Test APIClient rate limiting detection and handling."""

    @patch("requests.request")
    @patch("time.sleep")
    def test_rate_limit_with_retry_after_header(self, mock_sleep: Mock, mock_request: Mock) -> None:
        """Verify client respects Retry-After header."""
        # Arrange
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.text = "Rate limited"
        mock_response_429.headers = {"Retry-After": "5"}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = "Success"
        mock_response_200.headers = {}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(base_url="https://api.example.com")

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        mock_sleep.assert_called_once_with(5)

    @patch("requests.request")
    @patch("time.sleep")
    def test_rate_limit_without_retry_after_uses_backoff(
        self, mock_sleep: Mock, mock_request: Mock
    ) -> None:
        """Verify client uses backoff when Retry-After not present."""
        # Arrange
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.text = "Rate limited"
        mock_response_429.headers = {}

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = "Success"
        mock_response_200.headers = {}

        mock_request.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=RetryConfig(jitter=False),
        )

        # Act
        response = client.get("/users")

        # Assert
        assert response.status_code == 200
        # Should use exponential backoff (2^1 = 2.0)
        mock_sleep.assert_called_once()


class TestAPIClientExceptionHandling:
    """Test APIClient exception raising behavior."""

    @patch("requests.request")
    def test_raises_exception_on_4xx_error(self, mock_request: Mock) -> None:
        """Verify client raises exception fer 4xx errors."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError):
            client.get("/users/999")

    @patch("requests.request")
    def test_raises_exception_on_network_error(self, mock_request: Mock) -> None:
        """Verify client raises NetworkError on connection failure."""
        # Arrange
        mock_request.side_effect = ConnectionError("Connection refused")

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError):
            client.get("/users")


class TestAPIClientLogging:
    """Test APIClient logging behavior."""

    @patch("requests.request")
    @patch("amplihack.api_client.client.logger")
    def test_logs_request_without_sensitive_headers(
        self, mock_logger: Mock, mock_request: Mock
    ) -> None:
        """Verify client logs requests with sensitive headers redacted."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer secret-token"},
        )

        # Act
        client.get("/users")

        # Assert - verify logging happened
        assert mock_logger.info.called or mock_logger.debug.called

        # Verify sensitive headers not in log output
        log_calls = [str(call) for call in mock_logger.method_calls]
        assert "secret-token" not in " ".join(log_calls)
        assert "[REDACTED]" in " ".join(log_calls) or "Authorization" not in " ".join(log_calls)


class TestAPIClientContextManager:
    """Test APIClient context manager protocol."""

    def test_context_manager_enter(self) -> None:
        """Verify APIClient works as context manager (enter)."""
        # Act
        with APIClient(base_url="https://api.example.com") as client:
            # Assert
            assert client is not None
            assert isinstance(client, APIClient)

    @patch("requests.request")
    def test_context_manager_exit(self, mock_request: Mock) -> None:
        """Verify APIClient cleanup on context exit."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        # Act
        with APIClient(base_url="https://api.example.com") as client:
            client.get("/users")

        # Assert - context manager exited without error
        assert True

    @patch("requests.request")
    def test_context_manager_exception_handling(self, mock_request: Mock) -> None:
        """Verify APIClient handles exceptions in context manager."""
        # Arrange
        mock_request.side_effect = Exception("Unexpected error")

        # Act & Assert - exception should propagate
        with pytest.raises(Exception, match="Unexpected error"):
            with APIClient(base_url="https://api.example.com") as client:
                client.get("/users")


class TestAPIClientTimeoutConfiguration:
    """Test APIClient timeout configuration."""

    @patch("requests.request")
    def test_timeout_passed_to_request(self, mock_request: Mock) -> None:
        """Verify client passes timeout to underlying request."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        timeout = 60.0
        client = APIClient(base_url="https://api.example.com", timeout=timeout)

        # Act
        client.get("/users")

        # Assert - verify timeout was passed
        call_kwargs = mock_request.call_args[1]
        assert "timeout" in call_kwargs
        assert call_kwargs["timeout"] == timeout
