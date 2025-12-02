"""Unit tests for APIClient (with mocking).

Testing pyramid: 60% unit tests (these tests)
"""

from unittest.mock import Mock, patch

import pytest
import requests

from api_client import APIClient, RateLimiter, Request
from api_client.exceptions import (
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
)


class TestAPIClientInit:
    """Tests for APIClient initialization."""

    def test_create_with_minimal_params(self):
        """Test creating client with minimal parameters."""
        client = APIClient(base_url="https://api.example.com")
        assert client._base_url == "https://api.example.com"
        assert client._rate_limiter is None
        assert client._retry_handler is not None
        assert client._default_headers == {}

    def test_create_with_all_params(self):
        """Test creating client with all parameters."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        headers = {"Authorization": "Bearer token"}

        client = APIClient(
            base_url="https://api.example.com",
            rate_limiter=limiter,
            default_headers=headers,
        )

        assert client._base_url == "https://api.example.com"
        assert client._rate_limiter is limiter
        assert client._default_headers == headers

    def test_validate_empty_base_url(self):
        """Test that empty base_url raises ValueError."""
        with pytest.raises(ValueError, match="base_url cannot be empty"):
            APIClient(base_url="")

    def test_strip_trailing_slash(self):
        """Test that trailing slash is stripped from base_url."""
        client = APIClient(base_url="https://api.example.com/")
        assert client._base_url == "https://api.example.com"

    def test_file_protocol_rejected(self):
        """Test that file:// protocol is rejected (SSRF protection)."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            APIClient(base_url="file:///etc/passwd")

    def test_ftp_protocol_rejected(self):
        """Test that ftp:// protocol is rejected (SSRF protection)."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            APIClient(base_url="ftp://example.com")


class TestAPIClientSend:
    """Tests for APIClient.send method."""

    @patch("api_client.client.requests.Session")
    def test_successful_get_request(self, mock_session_class):
        """Test successful GET request."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"id": 123}'
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient(base_url="https://api.example.com")
        request = Request(method="GET", endpoint="/users")
        response = client.send(request)

        # Verify
        assert response.status_code == 200
        assert response.data == {"id": 123}
        assert response.raw_text == '{"id": 123}'

        # Verify HTTP request was made correctly
        mock_session.request.assert_called_once()
        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["url"] == "https://api.example.com/users"

    @patch("api_client.client.requests.Session")
    def test_successful_post_request(self, mock_session_class):
        """Test successful POST request with data."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.text = '{"created": true}'
        mock_response.json.return_value = {"created": True}
        mock_response.headers = {}
        mock_response.elapsed.total_seconds.return_value = 0.3
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient(base_url="https://api.example.com")
        request = Request(
            method="POST",
            endpoint="/users",
            data={"name": "Alice"},
        )
        response = client.send(request)

        # Verify
        assert response.status_code == 201
        assert response.data == {"created": True}

        # Verify POST data was sent as JSON
        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["json"] == {"name": "Alice"}

    @patch("api_client.client.requests.Session")
    def test_request_with_custom_headers(self, mock_session_class):
        """Test request with custom headers."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "{}"
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response

        # Make request with both default and request headers
        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"X-Default": "default"},
        )
        request = Request(
            method="GET",
            endpoint="/users",
            headers={"X-Custom": "custom"},
        )
        client.send(request)

        # Verify headers were merged
        call_kwargs = mock_session.request.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["X-Default"] == "default"
        assert headers["X-Custom"] == "custom"

    @patch("api_client.client.requests.Session")
    def test_timeout_error(self, mock_session_class):
        """Test request timeout."""
        # Setup mock to raise timeout
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.Timeout()

        # Make request with NO retries (to test immediate error handling)
        from api_client import RetryHandler

        client = APIClient(
            base_url="https://api.example.com", retry_handler=RetryHandler(max_retries=0)
        )
        request = Request(method="GET", endpoint="/users")

        # Timeout wrapped in RetryExhaustedError when retries are exhausted
        with pytest.raises(RetryExhaustedError) as exc_info:
            client.send(request)

        # Verify the underlying error was a timeout
        assert isinstance(exc_info.value.last_error, RequestError)
        assert "timeout" in str(exc_info.value.last_error).lower()

    @patch("api_client.client.requests.Session")
    def test_connection_error(self, mock_session_class):
        """Test connection error."""
        # Setup mock to raise connection error
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.ConnectionError()

        # Make request with NO retries (to test immediate error handling)
        from api_client import RetryHandler

        client = APIClient(
            base_url="https://api.example.com", retry_handler=RetryHandler(max_retries=0)
        )
        request = Request(method="GET", endpoint="/users")

        # Connection error wrapped in RetryExhaustedError when retries are exhausted
        with pytest.raises(RetryExhaustedError) as exc_info:
            client.send(request)

        # Verify the underlying error was a connection error
        assert isinstance(exc_info.value.last_error, RequestError)
        assert "connection" in str(exc_info.value.last_error).lower()

    @patch("api_client.client.requests.Session")
    def test_4xx_response_error(self, mock_session_class):
        """Test 4xx client error response."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json.side_effect = ValueError()  # Not JSON
        mock_response.headers = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response

        # Make request with NO retries (to test immediate error handling)
        from api_client import RetryHandler

        client = APIClient(
            base_url="https://api.example.com", retry_handler=RetryHandler(max_retries=0)
        )
        request = Request(method="GET", endpoint="/users")

        # 4xx error wrapped in RetryExhaustedError when retries are exhausted
        with pytest.raises(RetryExhaustedError) as exc_info:
            client.send(request)

        # Verify the underlying error was a 404 response error
        assert isinstance(exc_info.value.last_error, ResponseError)
        assert exc_info.value.last_error.status_code == 404
        assert "404" in str(exc_info.value.last_error)

    @patch("api_client.client.requests.Session")
    def test_rate_limit_error(self, mock_session_class):
        """Test 429 rate limit response."""
        # Setup mock
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient(base_url="https://api.example.com")
        request = Request(method="GET", endpoint="/users")

        with pytest.raises(RateLimitError) as exc_info:
            client.send(request)

        # Check retry_after was parsed
        assert exc_info.value.context.get("retry_after") == 60.0

    @patch("api_client.client.requests.Session")
    def test_malformed_json_response(self, mock_session_class):
        """Test handling of malformed JSON response."""
        # Setup mock with malformed JSON
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "{invalid json content"  # Malformed JSON
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.headers = {}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient(base_url="https://api.example.com")
        request = Request(method="GET", endpoint="/users")
        response = client.send(request)

        # Should handle gracefully: data=None, raw_text has the content
        assert response.status_code == 200
        assert response.data is None
        assert response.raw_text == "{invalid json content"

    @patch("api_client.client.requests.Session")
    def test_generic_request_exception(self, mock_session_class):
        """Test handling of generic RequestException."""
        # Setup mock to raise generic RequestException
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = requests.exceptions.RequestException("Generic error")

        # Make request with NO retries (to test immediate error handling)
        from api_client import RetryHandler

        client = APIClient(
            base_url="https://api.example.com", retry_handler=RetryHandler(max_retries=0)
        )
        request = Request(method="GET", endpoint="/users")

        # Generic error wrapped in RetryExhaustedError when retries are exhausted
        with pytest.raises(RetryExhaustedError) as exc_info:
            client.send(request)

        # Verify the underlying error was a RequestError with the generic message
        assert isinstance(exc_info.value.last_error, RequestError)
        assert "Generic error" in str(exc_info.value.last_error)


class TestAPIClientContextManager:
    """Tests for APIClient context manager."""

    def test_context_manager_closes_session(self):
        """Test that context manager closes session."""
        with patch("api_client.client.requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            with APIClient(base_url="https://api.example.com") as _:
                pass

            # Session should be closed
            mock_session.close.assert_called_once()

    def test_manual_close(self):
        """Test manual close method."""
        with patch("api_client.client.requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            client = APIClient(base_url="https://api.example.com")
            client.close()

            # Session should be closed
            mock_session.close.assert_called_once()
