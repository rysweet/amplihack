"""TDD tests for Simple API Client.

These tests define the expected behavior of api_client.py.
They should FAIL initially - the implementation will make them pass.

Testing pyramid: ~70% unit tests (mocked), ~20% integration, ~10% edge cases.

Run with: python -m pytest .claude/scenarios/api-client/tests/ -v
"""

import json

# Import the module under test - will fail until implementation exists
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError as URLLibHTTPError
from urllib.error import URLError

# Add parent directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

import builtins

from api_client import APIClient, APIError, HTTPError, RequestTimeoutError


class TestExceptionHierarchy(unittest.TestCase):
    """Test that exception classes exist and have correct inheritance."""

    def test_api_error_is_base_exception(self):
        """APIError should be a subclass of Exception."""
        self.assertTrue(issubclass(APIError, Exception))

    def test_timeout_error_inherits_from_api_error(self):
        """RequestTimeoutError should inherit from APIError."""
        self.assertTrue(issubclass(RequestTimeoutError, APIError))

    def test_http_error_inherits_from_api_error(self):
        """HTTPError should inherit from APIError."""
        self.assertTrue(issubclass(HTTPError, APIError))

    def test_http_error_has_status_code_attribute(self):
        """HTTPError should have status_code attribute."""
        error = HTTPError(404, "Not Found")
        self.assertEqual(error.status_code, 404)

    def test_http_error_has_message_attribute(self):
        """HTTPError should have message attribute."""
        error = HTTPError(500, "Internal Server Error")
        self.assertEqual(error.message, "Internal Server Error")

    def test_http_error_string_representation(self):
        """HTTPError str() should include status code and message."""
        error = HTTPError(403, "Forbidden")
        error_str = str(error)
        self.assertIn("403", error_str)
        self.assertIn("Forbidden", error_str)

    def test_catching_api_error_catches_http_error(self):
        """APIError catch block should catch HTTPError."""
        with self.assertRaises(APIError):
            raise HTTPError(404, "Not Found")

    def test_catching_api_error_catches_timeout_error(self):
        """APIError catch block should catch RequestTimeoutError."""
        with self.assertRaises(APIError):
            raise RequestTimeoutError("Request timed out")


class TestAPIClientInitialization(unittest.TestCase):
    """Test APIClient initialization and configuration."""

    def test_init_with_base_url(self):
        """APIClient should accept base_url parameter."""
        client = APIClient("https://api.example.com")
        self.assertEqual(client.base_url, "https://api.example.com")

    def test_init_with_trailing_slash_removed(self):
        """Base URL trailing slash should be normalized."""
        client = APIClient("https://api.example.com/")
        self.assertEqual(client.base_url, "https://api.example.com")

    def test_init_with_default_timeout(self):
        """Default timeout should be 30 seconds."""
        client = APIClient("https://api.example.com")
        self.assertEqual(client.timeout, 30)

    def test_init_with_custom_timeout(self):
        """Custom timeout should be stored correctly."""
        client = APIClient("https://api.example.com", timeout=60)
        self.assertEqual(client.timeout, 60)

    def test_init_requires_base_url(self):
        """APIClient should require base_url parameter."""
        with self.assertRaises(TypeError):
            APIClient()  # Missing required argument


class TestURLConstruction(unittest.TestCase):
    """Test URL construction from base_url and endpoint."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    def test_endpoint_with_leading_slash(self):
        """Endpoint with leading slash should construct correct URL."""
        url = self.client._build_url("/users")
        self.assertEqual(url, "https://api.example.com/users")

    def test_endpoint_without_leading_slash(self):
        """Endpoint without leading slash should still work."""
        url = self.client._build_url("users")
        self.assertEqual(url, "https://api.example.com/users")

    def test_nested_endpoint(self):
        """Nested endpoint paths should work correctly."""
        url = self.client._build_url("/users/1/posts")
        self.assertEqual(url, "https://api.example.com/users/1/posts")

    def test_base_url_with_path(self):
        """Base URL with path should work with endpoint."""
        client = APIClient("https://api.example.com/v1")
        url = client._build_url("/users")
        self.assertEqual(url, "https://api.example.com/v1/users")


class TestGetRequests(unittest.TestCase):
    """Test GET request functionality."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    @patch("api_client.urllib.request.urlopen")
    def test_get_returns_parsed_json_dict(self, mock_urlopen):
        """GET should return parsed JSON as dict."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": 1, "name": "Test"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.get("/users/1")

        self.assertEqual(result, {"id": 1, "name": "Test"})

    @patch("api_client.urllib.request.urlopen")
    def test_get_returns_parsed_json_list(self, mock_urlopen):
        """GET should return parsed JSON as list."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'[{"id": 1}, {"id": 2}]'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.get("/users")

        self.assertEqual(result, [{"id": 1}, {"id": 2}])

    @patch("api_client.urllib.request.urlopen")
    def test_get_constructs_correct_url(self, mock_urlopen):
        """GET should call urlopen with correct URL."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.get("/users/123")

        # Check the URL passed to urlopen
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.full_url, "https://api.example.com/users/123")

    @patch("api_client.urllib.request.urlopen")
    def test_get_uses_correct_timeout(self, mock_urlopen):
        """GET should pass timeout to urlopen."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = APIClient("https://api.example.com", timeout=45)
        client.get("/test")

        call_args = mock_urlopen.call_args
        self.assertEqual(call_args[1].get("timeout"), 45)

    @patch("api_client.urllib.request.urlopen")
    def test_get_sets_accept_json_header(self, mock_urlopen):
        """GET should set Accept: application/json header."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.get("/test")

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.get_header("Accept"), "application/json")


class TestPostRequests(unittest.TestCase):
    """Test POST request functionality."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    @patch("api_client.urllib.request.urlopen")
    def test_post_returns_parsed_json(self, mock_urlopen):
        """POST should return parsed JSON response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": 101, "title": "Test"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.post("/posts", {"title": "Test"})

        self.assertEqual(result, {"id": 101, "title": "Test"})

    @patch("api_client.urllib.request.urlopen")
    def test_post_sends_json_encoded_data(self, mock_urlopen):
        """POST should encode data as JSON in request body."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.post("/posts", {"title": "Hello", "body": "World"})

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        sent_data = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent_data, {"title": "Hello", "body": "World"})

    @patch("api_client.urllib.request.urlopen")
    def test_post_sets_content_type_json(self, mock_urlopen):
        """POST should set Content-Type: application/json header."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.post("/posts", {"data": "test"})

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.get_header("Content-type"), "application/json")

    @patch("api_client.urllib.request.urlopen")
    def test_post_constructs_correct_url(self, mock_urlopen):
        """POST should call urlopen with correct URL."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.post("/users", {"name": "Test"})

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.full_url, "https://api.example.com/users")

    @patch("api_client.urllib.request.urlopen")
    def test_post_uses_post_method(self, mock_urlopen):
        """POST should use HTTP POST method."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        self.client.post("/posts", {"title": "Test"})

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.method, "POST")


class TestHTTPErrorHandling(unittest.TestCase):
    """Test handling of HTTP error responses (4xx, 5xx)."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    @patch("api_client.urllib.request.urlopen")
    def test_404_raises_http_error(self, mock_urlopen):
        """404 response should raise HTTPError with status_code=404."""
        mock_urlopen.side_effect = URLLibHTTPError(
            url="https://api.example.com/nonexistent",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(HTTPError) as context:
            self.client.get("/nonexistent")

        self.assertEqual(context.exception.status_code, 404)

    @patch("api_client.urllib.request.urlopen")
    def test_500_raises_http_error(self, mock_urlopen):
        """500 response should raise HTTPError with status_code=500."""
        mock_urlopen.side_effect = URLLibHTTPError(
            url="https://api.example.com/error",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(HTTPError) as context:
            self.client.get("/error")

        self.assertEqual(context.exception.status_code, 500)

    @patch("api_client.urllib.request.urlopen")
    def test_401_raises_http_error(self, mock_urlopen):
        """401 response should raise HTTPError with status_code=401."""
        mock_urlopen.side_effect = URLLibHTTPError(
            url="https://api.example.com/protected",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(HTTPError) as context:
            self.client.get("/protected")

        self.assertEqual(context.exception.status_code, 401)

    @patch("api_client.urllib.request.urlopen")
    def test_http_error_contains_message(self, mock_urlopen):
        """HTTPError should contain the error message."""
        mock_urlopen.side_effect = URLLibHTTPError(
            url="https://api.example.com/forbidden",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(HTTPError) as context:
            self.client.get("/forbidden")

        self.assertIn("Forbidden", context.exception.message)

    @patch("api_client.urllib.request.urlopen")
    def test_post_http_error(self, mock_urlopen):
        """POST should also raise HTTPError on 4xx/5xx."""
        mock_urlopen.side_effect = URLLibHTTPError(
            url="https://api.example.com/posts",
            code=422,
            msg="Unprocessable Entity",
            hdrs={},
            fp=None,
        )

        with self.assertRaises(HTTPError) as context:
            self.client.post("/posts", {"invalid": "data"})

        self.assertEqual(context.exception.status_code, 422)


class TestTimeoutErrorHandling(unittest.TestCase):
    """Test handling of timeout errors."""

    def setUp(self):
        self.client = APIClient("https://api.example.com", timeout=5)

    @patch("api_client.urllib.request.urlopen")
    def test_timeout_raises_timeout_error_on_get(self, mock_urlopen):
        """GET timeout should raise RequestTimeoutError."""
        mock_urlopen.side_effect = builtins.TimeoutError("timed out")

        with self.assertRaises(RequestTimeoutError):
            self.client.get("/slow-endpoint")

    @patch("api_client.urllib.request.urlopen")
    def test_timeout_raises_timeout_error_on_post(self, mock_urlopen):
        """POST timeout should raise RequestTimeoutError."""
        mock_urlopen.side_effect = builtins.TimeoutError("timed out")

        with self.assertRaises(RequestTimeoutError):
            self.client.post("/slow-endpoint", {"data": "test"})

    @patch("api_client.urllib.request.urlopen")
    def test_url_error_timeout_raises_timeout_error(self, mock_urlopen):
        """URLError with timeout reason should raise RequestTimeoutError."""
        mock_urlopen.side_effect = URLError(builtins.TimeoutError("timed out"))

        with self.assertRaises(RequestTimeoutError):
            self.client.get("/timeout")


class TestConnectionErrorHandling(unittest.TestCase):
    """Test handling of connection errors."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    @patch("api_client.urllib.request.urlopen")
    def test_connection_refused_raises_api_error(self, mock_urlopen):
        """Connection refused should raise APIError."""
        mock_urlopen.side_effect = URLError("Connection refused")

        with self.assertRaises(APIError):
            self.client.get("/test")

    @patch("api_client.urllib.request.urlopen")
    def test_dns_failure_raises_api_error(self, mock_urlopen):
        """DNS resolution failure should raise APIError."""
        mock_urlopen.side_effect = URLError("Name or service not known")

        with self.assertRaises(APIError):
            self.client.get("/test")


class TestJSONParsing(unittest.TestCase):
    """Test JSON response parsing."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    @patch("api_client.urllib.request.urlopen")
    def test_invalid_json_raises_api_error(self, mock_urlopen):
        """Invalid JSON response should raise APIError."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        with self.assertRaises(APIError):
            self.client.get("/invalid-json")

    @patch("api_client.urllib.request.urlopen")
    def test_empty_response_handled(self, mock_urlopen):
        """Empty response should be handled appropriately."""
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Empty response should raise APIError or return None/empty dict
        # The exact behavior depends on design choice - testing for APIError
        with self.assertRaises(APIError):
            self.client.get("/empty")

    @patch("api_client.urllib.request.urlopen")
    def test_unicode_response_parsed(self, mock_urlopen):
        """Unicode characters in JSON should be parsed correctly."""
        mock_response = MagicMock()
        mock_response.read.return_value = '{"name": "Cafe\u0301"}'.encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.get("/unicode")

        self.assertEqual(result["name"], "Cafe\u0301")

    @patch("api_client.urllib.request.urlopen")
    def test_nested_json_parsed(self, mock_urlopen):
        """Nested JSON structures should be parsed correctly."""
        nested_data = {"user": {"profile": {"name": "Test", "tags": ["a", "b"]}}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(nested_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.get("/nested")

        self.assertEqual(result, nested_data)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        self.client = APIClient("https://api.example.com")

    def test_empty_base_url_raises_error(self):
        """Empty base_url should raise ValueError."""
        with self.assertRaises(ValueError):
            APIClient("")

    def test_none_base_url_raises_error(self):
        """None base_url should raise TypeError or ValueError."""
        with self.assertRaises((TypeError, ValueError)):
            APIClient(None)

    def test_invalid_scheme_raises_error(self):
        """Invalid URL scheme should raise ValueError."""
        with self.assertRaises(ValueError):
            APIClient("ftp://api.example.com")

    def test_file_scheme_raises_error(self):
        """file:// scheme should raise ValueError for security."""
        with self.assertRaises(ValueError):
            APIClient("file:///etc/passwd")

    def test_negative_timeout_raises_error(self):
        """Negative timeout should raise ValueError."""
        with self.assertRaises(ValueError):
            APIClient("https://api.example.com", timeout=-1)

    def test_zero_timeout_raises_error(self):
        """Zero timeout should raise ValueError."""
        with self.assertRaises(ValueError):
            APIClient("https://api.example.com", timeout=0)

    @patch("api_client.urllib.request.urlopen")
    def test_post_with_empty_dict(self, mock_urlopen):
        """POST with empty dict should work."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"{}"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = self.client.post("/posts", {})

        self.assertEqual(result, {})


class TestModuleExports(unittest.TestCase):
    """Test that module exports the correct public API via __all__."""

    def test_module_exports_api_client(self):
        """Module should export APIClient class."""
        import api_client

        self.assertIn("APIClient", api_client.__all__)

    def test_module_exports_api_error(self):
        """Module should export APIError class."""
        import api_client

        self.assertIn("APIError", api_client.__all__)

    def test_module_exports_timeout_error(self):
        """Module should export RequestTimeoutError class."""
        import api_client

        self.assertIn("RequestTimeoutError", api_client.__all__)

    def test_module_exports_http_error(self):
        """Module should export HTTPError class."""
        import api_client

        self.assertIn("HTTPError", api_client.__all__)

    def test_module_all_has_exactly_four_exports(self):
        """Module __all__ should have exactly 4 exports."""
        import api_client

        self.assertEqual(len(api_client.__all__), 4)


if __name__ == "__main__":
    unittest.main()
