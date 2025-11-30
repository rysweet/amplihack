"""Unit tests for RESTClient - TDD approach (60% of test coverage).

Testing pyramid:
- Unit tests (this file): Testing individual methods with heavy mocking
- Integration tests: Testing multiple components together
- E2E tests: Complete workflows
"""

import json
import os

# Import the not-yet-existing module (TDD - will fail initially)
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import APIConnectionError, APITimeoutError, HTTPError, Response, RESTClient


class TestRESTClientInitialization(unittest.TestCase):
    """Test RESTClient initialization and configuration."""

    def test_init_with_base_url(self):
        """Test client initialization with base URL."""
        client = RESTClient(base_url="https://api.example.com")
        self.assertEqual(client.base_url, "https://api.example.com")

    def test_init_with_rate_limit(self):
        """Test client initialization with rate limiting."""
        client = RESTClient(base_url="https://api.example.com", requests_per_second=2.0)
        self.assertEqual(client.requests_per_second, 2.0)

    def test_init_with_retry_config(self):
        """Test client initialization with retry configuration."""
        client = RESTClient(base_url="https://api.example.com", max_retries=5)
        self.assertEqual(client.max_retries, 5)

    def test_init_with_headers(self):
        """Test client initialization with default headers."""
        headers = {"Authorization": "Bearer token123"}
        client = RESTClient(base_url="https://api.example.com", headers=headers)
        self.assertEqual(client.headers, headers)

    def test_init_with_timeout(self):
        """Test client initialization with timeout."""
        client = RESTClient(base_url="https://api.example.com", timeout=60)
        self.assertEqual(client.timeout, 60)


class TestResponseDataclass(unittest.TestCase):
    """Test Response dataclass functionality."""

    def test_response_creation(self):
        """Test creating a Response object."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=b'{"message": "success"}',
            url="https://api.example.com/data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_response_json_method(self):
        """Test parsing JSON from response body."""
        response = Response(
            status_code=200,
            headers={},
            body=b'{"key": "value", "number": 42}',
            url="https://api.example.com",
        )
        data = response.json()
        self.assertEqual(data["key"], "value")
        self.assertEqual(data["number"], 42)

    def test_response_text_property(self):
        """Test getting response body as text."""
        response = Response(
            status_code=200, headers={}, body=b"Hello, World!", url="https://api.example.com"
        )
        self.assertEqual(response.text, "Hello, World!")

    def test_response_json_with_invalid_json(self):
        """Test that json() raises error for invalid JSON."""
        response = Response(
            status_code=200, headers={}, body=b"Not valid JSON", url="https://api.example.com"
        )
        with self.assertRaises(json.JSONDecodeError):
            response.json()


class TestHTTPMethods(unittest.TestCase):
    """Test HTTP method implementations."""

    @patch("urllib.request.urlopen")
    def test_get_request(self, mock_urlopen):
        """Test GET request method."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.url = "https://api.example.com/users"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        response = client.get("/users")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "success")

        # Verify request was called correctly
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_method(), "GET")
        self.assertEqual(request_obj.full_url, "https://api.example.com/users")

    @patch("urllib.request.urlopen")
    def test_post_request_with_json_data(self, mock_urlopen):
        """Test POST request with JSON data."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.read.return_value = b'{"id": 123}'
        mock_response.url = "https://api.example.com/users"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        post_data = {"name": "John Doe", "email": "john@example.com"}
        response = client.post("/users", json=post_data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 123)

        # Verify request was called correctly
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_method(), "POST")
        self.assertIn(b"John Doe", request_obj.data)

    @patch("urllib.request.urlopen")
    def test_put_request(self, mock_urlopen):
        """Test PUT request method."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'{"updated": true}'
        mock_response.url = "https://api.example.com/users/123"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        response = client.put("/users/123", json={"name": "Jane Doe"})

        self.assertEqual(response.status_code, 200)
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_method(), "PUT")

    @patch("urllib.request.urlopen")
    def test_delete_request(self, mock_urlopen):
        """Test DELETE request method."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.headers = {}
        mock_response.read.return_value = b""
        mock_response.url = "https://api.example.com/users/123"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        response = client.delete("/users/123")

        self.assertEqual(response.status_code, 204)
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_method(), "DELETE")

    @patch("urllib.request.urlopen")
    def test_patch_request(self, mock_urlopen):
        """Test PATCH request method."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b'{"patched": true}'
        mock_response.url = "https://api.example.com/users/123"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        response = client.patch("/users/123", json={"email": "new@example.com"})

        self.assertEqual(response.status_code, 200)
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.get_method(), "PATCH")


class TestURLHandling(unittest.TestCase):
    """Test URL construction and handling."""

    @patch("urllib.request.urlopen")
    def test_url_joining(self, mock_urlopen):
        """Test that URLs are properly joined with base URL."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_response.url = "https://api.example.com/v1/users"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        # Test with trailing slash in base URL
        client = RESTClient(base_url="https://api.example.com/v1/")
        response = client.get("/users")
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.full_url, "https://api.example.com/v1/users")

        # Test without trailing slash
        client = RESTClient(base_url="https://api.example.com/v1")
        response = client.get("/users")
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.full_url, "https://api.example.com/v1/users")

    @patch("urllib.request.urlopen")
    def test_query_parameters(self, mock_urlopen):
        """Test query parameter handling."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"[]"
        mock_response.url = "https://api.example.com/users?page=2&limit=10"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com")
        response = client.get("/users", params={"page": 2, "limit": 10})

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertIn("page=2", request_obj.full_url)
        self.assertIn("limit=10", request_obj.full_url)


class TestHeaderHandling(unittest.TestCase):
    """Test header handling and merging."""

    @patch("urllib.request.urlopen")
    def test_default_headers(self, mock_urlopen):
        """Test that default headers are included in requests."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_response.url = "https://api.example.com/data"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        default_headers = {"Authorization": "Bearer token123", "X-API-Key": "secret"}
        client = RESTClient(base_url="https://api.example.com", headers=default_headers)
        response = client.get("/data")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.headers["Authorization"], "Bearer token123")
        self.assertEqual(
            request_obj.headers["X-api-key"], "secret"
        )  # urllib lowercases some headers

    @patch("urllib.request.urlopen")
    def test_request_specific_headers(self, mock_urlopen):
        """Test that request-specific headers override defaults."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_response.url = "https://api.example.com/data"
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = None
        mock_urlopen.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com", headers={"X-Default": "value"})
        response = client.get("/data", headers={"X-Custom": "custom-value"})

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        self.assertEqual(request_obj.headers["X-custom"], "custom-value")
        self.assertEqual(request_obj.headers["X-default"], "value")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and exceptions."""

    @patch("api_client.client.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """Test handling of HTTP errors (4xx, 5xx)."""
        from urllib.error import HTTPError as URLHTTPError

        # Create a mock HTTPError
        mock_error = URLHTTPError(
            "https://api.example.com/users",
            404,
            "Not Found",
            {"Content-Type": "application/json"},
            None,
        )
        mock_urlopen.side_effect = mock_error

        client = RESTClient(base_url="https://api.example.com", max_retries=0)

        # Client raises custom HTTPError for better error handling
        with self.assertRaises(HTTPError) as cm:
            client.get("/users")

        self.assertEqual(cm.exception.status_code, 404)

    @patch("api_client.client.request.urlopen")
    def test_timeout_error(self, mock_urlopen):
        """Test handling of timeout errors."""
        mock_urlopen.side_effect = TimeoutError("Connection timed out")

        client = RESTClient(base_url="https://api.example.com", timeout=5, max_retries=0)

        # Client raises custom APITimeoutError for better error handling
        with self.assertRaises(APITimeoutError):
            client.get("/users")

    @patch("api_client.client.request.urlopen")
    def test_connection_error(self, mock_urlopen):
        """Test handling of connection errors."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        client = RESTClient(base_url="https://api.example.com", max_retries=0)

        # Client raises custom APIConnectionError for better error handling
        with self.assertRaises(APIConnectionError):
            client.get("/users")


if __name__ == "__main__":
    unittest.main()
