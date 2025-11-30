"""Unit tests for APIClient - 60% of test coverage.

Tests the APIClient class in isolation with heavy mocking.
These tests should run in milliseconds without any external dependencies.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from requests.exceptions import ConnectionError, HTTPError, Timeout

from rest_api_client.client import APIClient
from rest_api_client.exceptions import (
    AuthenticationError,
    HTTPResponseError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


@pytest.mark.unit
class TestAPIClientInitialization:
    """Test APIClient initialization and configuration."""

    def test_init_with_minimal_config(self):
        """Test initialization with just base_url."""
        client = APIClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30  # Default
        assert client.max_retries == 3  # Default
        assert client.headers["User-Agent"] == "rest-api-client/1.0.0"

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = APIClient("https://api.example.com", api_key="test_key_123")
        assert client.headers["Authorization"] == "Bearer test_key_123"

    def test_init_with_custom_headers(self):
        """Test initialization with custom headers."""
        custom_headers = {"X-Custom-Header": "custom_value", "Accept": "application/json"}
        client = APIClient("https://api.example.com", headers=custom_headers)
        assert client.headers["X-Custom-Header"] == "custom_value"
        assert client.headers["Accept"] == "application/json"
        assert client.headers["User-Agent"] == "rest-api-client/1.0.0"  # Default preserved

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = APIClient("https://api.example.com", timeout=60)
        assert client.timeout == 60

    def test_init_with_custom_retry_config(self):
        """Test initialization with custom retry configuration."""
        client = APIClient("https://api.example.com", max_retries=5, retry_delay=2)
        assert client.max_retries == 5
        assert client.retry_delay == 2

    def test_init_validates_base_url(self):
        """Test that invalid base URLs are rejected."""
        with pytest.raises(ValidationError, match="Invalid base URL"):
            APIClient("")

        with pytest.raises(ValidationError, match="Invalid base URL"):
            APIClient("not-a-url")

        with pytest.raises(ValidationError, match="Invalid base URL"):
            APIClient("ftp://wrong-protocol.com")


@pytest.mark.unit
class TestHTTPMethods:
    """Test HTTP method implementations."""

    @patch("requests.Session")
    def test_get_request_success(self, mock_session_class):
        """Test successful GET request."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.get("/test")

        # Assertions
        assert result["result"] == "success"
        mock_session.request.assert_called_once_with(
            "GET",
            "https://api.example.com/test",
            headers=client.headers,
            timeout=30,
            params=None,
            json=None,
        )

    @patch("requests.Session")
    def test_post_request_with_json_body(self, mock_session_class):
        """Test POST request with JSON body."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        body = {"name": "Test Item", "value": 42}
        result = client.post("/items", json=body)

        # Assertions
        assert result["id"] == 123
        mock_session.request.assert_called_once_with(
            "POST",
            "https://api.example.com/items",
            headers=client.headers,
            timeout=30,
            params=None,
            json=body,
        )

    @patch("requests.Session")
    def test_put_request_success(self, mock_session_class):
        """Test PUT request."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"updated": True}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        body = {"name": "Updated Item"}
        result = client.put("/items/123", json=body)

        # Assertions
        assert result["updated"] is True
        mock_session.request.assert_called_once()

    @patch("requests.Session")
    def test_delete_request_success(self, mock_session_class):
        """Test DELETE request."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.delete("/items/123")

        # Assertions
        assert result is None  # 204 returns None
        mock_session.request.assert_called_once_with(
            "DELETE",
            "https://api.example.com/items/123",
            headers=client.headers,
            timeout=30,
            params=None,
            json=None,
        )

    @patch("requests.Session")
    def test_patch_request_success(self, mock_session_class):
        """Test PATCH request."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"patched": True}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        body = {"status": "active"}
        result = client.patch("/items/123", json=body)

        # Assertions
        assert result["patched"] is True


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    @patch("requests.Session")
    def test_400_bad_request(self, mock_session_class):
        """Test handling of 400 Bad Request."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad Request"}
        mock_response.text = "Bad Request"
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = HTTPError("400 Client Error")
        mock_session.request.return_value = mock_response

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(HTTPResponseError) as exc_info:
            client.get("/bad-request")

        assert exc_info.value.status_code == 400
        assert "Bad Request" in str(exc_info.value)

    @patch("requests.Session")
    def test_401_unauthorized(self, mock_session_class):
        """Test handling of 401 Unauthorized."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_response.text = "Unauthorized"
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = HTTPError("401 Client Error")
        mock_session.request.return_value = mock_response

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/protected")

        assert exc_info.value.status_code == 401

    @patch("requests.Session")
    def test_429_rate_limit(self, mock_session_class):
        """Test handling of 429 Too Many Requests."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {"Retry-After": "60"}
        mock_response.raise_for_status.side_effect = HTTPError("429 Client Error")
        mock_session.request.return_value = mock_response

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(RateLimitError) as exc_info:
            client.get("/rate-limited")

        assert exc_info.value.retry_after == 60

    @patch("requests.Session")
    def test_500_internal_server_error(self, mock_session_class):
        """Test handling of 500 Internal Server Error."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = HTTPError("500 Server Error")
        mock_session.request.return_value = mock_response

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(HTTPResponseError) as exc_info:
            client.get("/server-error")

        assert exc_info.value.status_code == 500

    @patch("requests.Session")
    def test_connection_error(self, mock_session_class):
        """Test handling of connection errors."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = ConnectionError("Connection refused")

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(NetworkError) as exc_info:
            client.get("/test")

        assert "Connection refused" in str(exc_info.value)

    @patch("requests.Session")
    def test_timeout_error(self, mock_session_class):
        """Test handling of timeout errors."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = Timeout("Request timed out")

        # Make request and expect error
        client = APIClient("https://api.example.com")
        with pytest.raises(TimeoutError) as exc_info:
            client.get("/slow-endpoint")

        assert "Request timed out" in str(exc_info.value)


@pytest.mark.unit
class TestQueryParameters:
    """Test query parameter handling."""

    @patch("requests.Session")
    def test_get_with_query_params(self, mock_session_class):
        """Test GET request with query parameters."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        params = {"page": 1, "limit": 10, "sort": "name"}
        client.get("/items", params=params)

        # Assertions
        mock_session.request.assert_called_once_with(
            "GET",
            "https://api.example.com/items",
            headers=client.headers,
            timeout=30,
            params=params,
            json=None,
        )

    @patch("requests.Session")
    def test_empty_query_params(self, mock_session_class):
        """Test that empty query params are handled correctly."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        client.get("/items", params={})

        # Assertions
        mock_session.request.assert_called_once_with(
            "GET",
            "https://api.example.com/items",
            headers=client.headers,
            timeout=30,
            params={},
            json=None,
        )


@pytest.mark.unit
class TestHeaderManagement:
    """Test header management functionality."""

    def test_update_headers(self):
        """Test updating headers after initialization."""
        client = APIClient("https://api.example.com")

        # Add new header
        client.update_headers({"X-Custom": "value"})
        assert client.headers["X-Custom"] == "value"

        # Update existing header
        client.update_headers({"User-Agent": "custom-agent/2.0"})
        assert client.headers["User-Agent"] == "custom-agent/2.0"

    def test_remove_header(self):
        """Test removing headers."""
        client = APIClient("https://api.example.com", headers={"X-Custom": "value"})

        client.remove_header("X-Custom")
        assert "X-Custom" not in client.headers

    def test_clear_headers(self):
        """Test clearing all headers except defaults."""
        client = APIClient(
            "https://api.example.com", api_key="test_key", headers={"X-Custom": "value"}
        )

        client.clear_headers()
        # Default headers should remain
        assert client.headers["User-Agent"] == "rest-api-client/1.0.0"
        # Custom headers should be removed
        assert "X-Custom" not in client.headers
        assert "Authorization" not in client.headers


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("requests.Session")
    def test_empty_response_body(self, mock_session_class):
        """Test handling of empty response body."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError("No JSON content")
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.delete("/items/123")

        # Should return None for 204
        assert result is None

    @patch("requests.Session")
    def test_non_json_response(self, mock_session_class):
        """Test handling of non-JSON response."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Plain text response"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.get("/text-endpoint")

        # Should return text for non-JSON
        assert result == "Plain text response"

    @patch("requests.Session")
    def test_null_values_in_json(self, mock_session_class):
        """Test handling of null values in JSON response."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": None, "items": []}
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.get("/nulls")

        # Assertions
        assert result["value"] is None
        assert result["items"] == []

    def test_url_path_normalization(self):
        """Test URL path normalization."""
        client = APIClient("https://api.example.com/")

        # Should handle trailing slashes correctly
        assert client._build_url("/test") == "https://api.example.com/test"
        assert client._build_url("test") == "https://api.example.com/test"
        assert client._build_url("//test") == "https://api.example.com/test"

    @patch("requests.Session")
    def test_large_response_body(self, mock_session_class):
        """Test handling of large response bodies."""
        # Setup mock
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        # Create large response (1MB of data)
        large_data = {"items": ["x" * 1000 for _ in range(1000)]}
        mock_response.json.return_value = large_data
        mock_response.headers = {}
        mock_session.request.return_value = mock_response

        # Make request
        client = APIClient("https://api.example.com")
        result = client.get("/large-data")

        # Should handle large responses
        assert len(result["items"]) == 1000
