"""
Comprehensive test suite for REST API Client following TDD approach.

Testing Pyramid:
- 60% Unit tests (test individual methods and components)
- 30% Integration tests (test with mock server)
- 10% E2E tests (test with real API if available)

These tests are written BEFORE implementation and will FAIL initially.
"""

import concurrent.futures
import json
import socket
import threading
import time
import unittest
import unittest.mock as mock
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from unittest.mock import MagicMock, call, patch

# Import our API client components (these don't exist yet - TDD!)
try:
    from api_client import APIClient, APIError, ClientConfig, HTTPError
    from api_client.rate_limiter import RateLimiter
    from api_client.response import Response
except ImportError:
    # Expected to fail initially in TDD
    APIClient = None
    ClientConfig = None
    APIError = None
    HTTPError = None
    Response = None
    RateLimiter = None


# ============================================================================
# UNIT TESTS - 60% of test coverage
# ============================================================================


class TestClientConfig(unittest.TestCase):
    """Unit tests for ClientConfig validation and defaults."""

    @unittest.skipIf(ClientConfig is None, "ClientConfig not implemented yet")
    def test_config_requires_base_url(self):
        """Test that ClientConfig requires base_url."""
        with self.assertRaises(TypeError):
            ClientConfig()

    @unittest.skipIf(ClientConfig is None, "ClientConfig not implemented yet")
    def test_config_with_minimal_params(self):
        """Test ClientConfig with only base_url."""
        config = ClientConfig(base_url="https://api.example.com")
        self.assertEqual(config.base_url, "https://api.example.com")
        self.assertEqual(config.timeout, 30.0)  # Default timeout
        self.assertEqual(config.max_retries, 3)  # Default retries
        self.assertIsNone(config.api_key)

    @unittest.skipIf(ClientConfig is None, "ClientConfig not implemented yet")
    def test_config_with_all_params(self):
        """Test ClientConfig with all parameters."""
        config = ClientConfig(
            base_url="https://api.example.com",
            timeout=60.0,
            max_retries=5,
            api_key="secret-key-123",  # pragma: allowlist secret
        )
        self.assertEqual(config.base_url, "https://api.example.com")
        self.assertEqual(config.timeout, 60.0)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.api_key, "secret-key-123")

    @unittest.skipIf(ClientConfig is None, "ClientConfig not implemented yet")
    def test_config_base_url_normalization(self):
        """Test that base_url trailing slash is handled."""
        config1 = ClientConfig(base_url="https://api.example.com/")
        config2 = ClientConfig(base_url="https://api.example.com")
        # Both should work correctly
        self.assertTrue(config1.base_url.startswith("https://api.example.com"))
        self.assertTrue(config2.base_url.startswith("https://api.example.com"))


class TestAPIClientInitialization(unittest.TestCase):
    """Unit tests for APIClient initialization."""

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_client_requires_config(self):
        """Test that APIClient requires ClientConfig."""
        with self.assertRaises(TypeError):
            APIClient()

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_client_initialization(self):
        """Test APIClient initialization with config."""
        config = ClientConfig(base_url="https://api.example.com")
        client = APIClient(config)
        self.assertIsNotNone(client)
        self.assertEqual(client.config, config)


class TestAPIClientMethods(unittest.TestCase):
    """Unit tests for APIClient HTTP methods."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url="https://api.example.com")
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_get_request(self, mock_urlopen):
        """Test GET request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.get("/users/123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "success"})

        # Verify request was made correctly
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "https://api.example.com/users/123")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_post_request_with_json(self, mock_urlopen):
        """Test POST request with JSON data."""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.read.return_value = b'{"id": 101}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {"title": "Test", "body": "Content"}
        response = self.client.post("/posts", json=data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"id": 101})

        # Verify request
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, json.dumps(data).encode())
        self.assertIn("Content-Type", request.headers)
        self.assertEqual(request.headers["Content-Type"], "application/json")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_put_request(self, mock_urlopen):
        """Test PUT request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"updated": true}'
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        data = {"title": "Updated"}
        response = self.client.put("/posts/1", json=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"updated": True})

        # Verify method
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.get_method(), "PUT")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_delete_request(self, mock_urlopen):
        """Test DELETE request."""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.read.return_value = b""
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.delete("/posts/1")

        self.assertEqual(response.status_code, 204)

        # Verify method
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.get_method(), "DELETE")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_request_with_query_params(self, mock_urlopen):
        """Test request with query parameters."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"[]"
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        self.client.get("/posts", params={"userId": 1, "limit": 5})

        # Verify URL includes query params
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertIn("userId=1", request.full_url)
        self.assertIn("limit=5", request.full_url)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_request_with_custom_headers(self, mock_urlopen):
        """Test request with custom headers."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        headers = {"X-Custom-Header": "value", "Accept": "application/json"}
        self.client.get("/data", headers=headers)

        # Verify headers
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.headers["X-Custom-Header"], "value")
        self.assertEqual(request.headers["Accept"], "application/json")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_api_key_authentication(self, mock_urlopen):
        """Test that API key is added as Bearer token."""
        config = ClientConfig(
            base_url="https://api.example.com",
            api_key="test-api-key",  # pragma: allowlist secret
        )
        client = APIClient(config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client.get("/protected")

        # Verify Authorization header
        args, kwargs = mock_urlopen.call_args
        request = args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer test-api-key")


class TestExceptionHandling(unittest.TestCase):
    """Unit tests for exception handling."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url="https://api.example.com")
            self.client = APIClient(self.config)

    @unittest.skipIf(HTTPError is None, "HTTPError not implemented yet")
    def test_http_error_creation(self):
        """Test HTTPError exception creation."""
        error = HTTPError(404, "Not Found", {"detail": "Resource not found"})
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.message, "Not Found")
        self.assertEqual(error.response_data, {"detail": "Resource not found"})
        self.assertIn("404", str(error))
        self.assertIn("Not Found", str(error))

    @unittest.skipIf(APIError is None, "APIError not implemented yet")
    def test_api_error_creation(self):
        """Test APIError exception creation."""
        error = APIError("Connection failed")
        self.assertEqual(str(error), "Connection failed")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_http_error_raised_on_4xx(self, mock_urlopen):
        """Test that HTTPError is raised on 4xx responses."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.example.com/users/999",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "User not found"}'),
        )

        with self.assertRaises(HTTPError) as context:
            self.client.get("/users/999")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, "Not Found")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_api_error_on_connection_failure(self, mock_urlopen):
        """Test that APIError is raised on connection failures."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        with self.assertRaises(APIError) as context:
            self.client.get("/test")

        self.assertIn("Failed to connect", str(context.exception))

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_timeout_error(self, mock_urlopen):
        """Test timeout error handling."""
        mock_urlopen.side_effect = TimeoutError("Request timed out")

        with self.assertRaises(APIError) as context:
            self.client.get("/slow-endpoint")

        self.assertIn("timeout", str(context.exception).lower())


class TestRetryLogic(unittest.TestCase):
    """Unit tests for retry logic on 5xx errors."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url="https://api.example.com", max_retries=3)
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_retry_on_500_error(self, mock_sleep, mock_urlopen):
        """Test that 500 errors trigger retries."""
        # First two calls fail with 500, third succeeds
        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b'{"result": "success"}'
        success_response.headers.items.return_value = []
        # Make it work as a context manager (urlopen returns a context manager)
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [
            urllib.error.HTTPError(
                "https://api.example.com/test",
                500,
                "Internal Server Error",
                {},
                BytesIO(b'{"error": "Server error"}'),
            ),
            urllib.error.HTTPError(
                "https://api.example.com/test",
                500,
                "Internal Server Error",
                {},
                BytesIO(b'{"error": "Server error"}'),
            ),
            success_response,
        ]

        response = self.client.get("/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"result": "success"})

        # Verify retries happened
        self.assertEqual(mock_urlopen.call_count, 3)
        # Verify exponential backoff
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_has_calls([call(0.5), call(1.0)])  # 0.5s, 1s backoff

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_502_error(self, mock_sleep, mock_urlopen):
        """Test that 502 Bad Gateway triggers retries."""
        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b'{"ok": true}'
        success_response.headers.items.return_value = []
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [
            urllib.error.HTTPError(
                "https://api.example.com/test", 502, "Bad Gateway", {}, BytesIO(b"")
            ),
            success_response,
        ]

        response = self.client.get("/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_urlopen.call_count, 2)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_503_error(self, mock_sleep, mock_urlopen):
        """Test that 503 Service Unavailable triggers retries."""
        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b'{"ok": true}'
        success_response.headers.items.return_value = []
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [
            urllib.error.HTTPError(
                "https://api.example.com/test", 503, "Service Unavailable", {}, BytesIO(b"")
            ),
            success_response,
        ]

        response = self.client.get("/test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_urlopen.call_count, 2)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_no_retry_on_4xx_errors(self, mock_urlopen):
        """Test that 4xx errors do NOT trigger retries."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.example.com/test", 404, "Not Found", {}, BytesIO(b'{"error": "Not found"}')
        )

        with self.assertRaises(HTTPError):
            self.client.get("/test")

        # Should only call once, no retries
        self.assertEqual(mock_urlopen.call_count, 1)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_max_retries_exhausted(self, mock_sleep, mock_urlopen):
        """Test that retries stop after max_retries."""
        # All calls fail with 500
        mock_urlopen.side_effect = [
            urllib.error.HTTPError(
                "https://api.example.com/test", 500, "Internal Server Error", {}, BytesIO(b"")
            )
        ] * 4  # More than max_retries

        with self.assertRaises(HTTPError) as context:
            self.client.get("/test")

        self.assertEqual(context.exception.status_code, 500)
        # Should try 1 + max_retries times
        self.assertEqual(mock_urlopen.call_count, 4)  # 1 initial + 3 retries


class TestRateLimiting(unittest.TestCase):
    """Unit tests for rate limiting."""

    @unittest.skipIf(RateLimiter is None, "RateLimiter not implemented yet")
    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(requests_per_second=10)
        self.assertEqual(limiter.requests_per_second, 10)
        self.assertEqual(limiter.min_interval, 0.1)  # 1/10

    @unittest.skipIf(RateLimiter is None, "RateLimiter not implemented yet")
    def test_rate_limiter_acquire(self):
        """Test that rate limiter delays requests appropriately."""
        limiter = RateLimiter(requests_per_second=10)

        start = time.time()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.time() - start

        # Should take at least 0.2 seconds for 3 requests at 10/sec
        self.assertGreaterEqual(elapsed, 0.2)
        self.assertLess(elapsed, 0.4)  # But not too long

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_client_rate_limiting(self, mock_urlopen):
        """Test that APIClient applies rate limiting."""
        config = ClientConfig(base_url="https://api.example.com")
        client = APIClient(config)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"{}"
        mock_response.headers = {}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        start = time.time()
        for i in range(5):
            client.get(f"/test/{i}")
        elapsed = time.time() - start

        # Default 10 req/s means 5 requests should take ~0.4 seconds
        self.assertGreaterEqual(elapsed, 0.35)  # Allow some margin


class TestResponse(unittest.TestCase):
    """Unit tests for Response object."""

    @unittest.skipIf(Response is None, "Response not implemented yet")
    def test_response_creation(self):
        """Test Response object creation."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"key": "value"}',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers, {"Content-Type": "application/json"})
        self.assertEqual(response.content, b'{"key": "value"}')

    @unittest.skipIf(Response is None, "Response not implemented yet")
    def test_response_text(self):
        """Test Response.text() method."""
        response = Response(status_code=200, headers={}, content=b"Hello, World!")
        self.assertEqual(response.text(), "Hello, World!")

    @unittest.skipIf(Response is None, "Response not implemented yet")
    def test_response_json(self):
        """Test Response.json() method."""
        response = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            content=b'{"name": "test", "value": 42}',
        )
        data = response.json()
        self.assertEqual(data, {"name": "test", "value": 42})

    @unittest.skipIf(Response is None, "Response not implemented yet")
    def test_response_json_invalid(self):
        """Test Response.json() with invalid JSON."""
        response = Response(status_code=200, headers={}, content=b"Not JSON")
        with self.assertRaises(json.JSONDecodeError):
            response.json()


class TestThreadSafety(unittest.TestCase):
    """Unit tests for thread safety."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url="https://api.example.com")
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_concurrent_requests(self, mock_urlopen):
        """Test that APIClient handles concurrent requests safely."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}

        def create_response(i):
            response = MagicMock()
            response.status = 200
            response.read.return_value = json.dumps({"id": i}).encode()
            response.headers.items.return_value = []
            response.__enter__ = MagicMock(return_value=response)
            response.__exit__ = MagicMock(return_value=None)
            return response

        # Each call gets a unique response
        responses = [create_response(i) for i in range(10)]
        mock_urlopen.side_effect = responses

        results = []

        def make_request(i):
            response = self.client.get(f"/item/{i}")
            return response.json()

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        self.assertEqual(len(results), 10)
        # Each should have unique ID
        ids = [r["id"] for r in results]
        self.assertEqual(len(set(ids)), 10)


class Test429Handling(unittest.TestCase):
    """Unit tests for 429 rate limit handling."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url="https://api.example.com")
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_handle_429_with_retry_after(self, mock_sleep, mock_urlopen):
        """Test handling 429 with Retry-After header."""
        # First call returns 429 with Retry-After, second succeeds
        error_response = urllib.error.HTTPError(
            "https://api.example.com/test",
            429,
            "Too Many Requests",
            {"Retry-After": "2"},
            BytesIO(b'{"error": "Rate limited"}'),
        )

        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b'{"result": "success"}'
        success_response.headers.items.return_value = []
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [error_response, success_response]

        response = self.client.get("/test")

        self.assertEqual(response.status_code, 200)
        # Should respect Retry-After header
        mock_sleep.assert_called_with(2)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_handle_429_without_retry_after(self, mock_sleep, mock_urlopen):
        """Test handling 429 without Retry-After header."""
        error_response = urllib.error.HTTPError(
            "https://api.example.com/test", 429, "Too Many Requests", {}, BytesIO(b"")
        )

        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b'{"result": "success"}'
        success_response.headers.items.return_value = []
        success_response.__enter__ = MagicMock(return_value=success_response)
        success_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen.side_effect = [error_response, success_response]

        response = self.client.get("/test")

        self.assertEqual(response.status_code, 200)
        # Should use default backoff
        mock_sleep.assert_called_once()
        # Default backoff should be reasonable (1-5 seconds)
        sleep_time = mock_sleep.call_args[0][0]
        self.assertGreaterEqual(sleep_time, 1)
        self.assertLessEqual(sleep_time, 5)


# ============================================================================
# INTEGRATION TESTS - 30% of test coverage
# ============================================================================


class MockHTTPHandler(BaseHTTPRequestHandler):
    """Mock HTTP server for integration tests."""

    def log_message(self, format, *args):
        """Suppress server logs during tests."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/users/1":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"id": 1, "name": "Test User"}')
        elif self.path == "/error/404":
            self.send_error(404, "Not Found")
        elif self.path == "/error/500":
            self.send_error(500, "Internal Server Error")
        elif self.path == "/rate-limit":
            self.send_response(429)
            self.send_header("Retry-After", "1")
            self.end_headers()
            self.wfile.write(b'{"error": "Rate limited"}')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"path": "' + self.path.encode() + b'"}')

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"received": json.loads(body) if body else None}
        self.wfile.write(json.dumps(response).encode())

    def do_PUT(self):
        """Handle PUT requests."""
        self.do_POST()  # Similar handling

    def do_DELETE(self):
        """Handle DELETE requests."""
        self.send_response(204)
        self.end_headers()


class TestIntegrationWithMockServer(unittest.TestCase):
    """Integration tests with a mock HTTP server."""

    @classmethod
    def setUpClass(cls):
        """Start mock server."""
        cls.server = HTTPServer(("localhost", 0), MockHTTPHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://localhost:{cls.port}"

        # Start server in background thread
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Stop mock server."""
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)

    def setUp(self):
        """Set up test client."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(base_url=self.base_url)
            self.client = APIClient(self.config)
            # Patch SSRF validation for localhost testing
            self.patcher = mock.patch.object(self.client, "_validate_url")
            self.patcher.start()

    def tearDown(self):
        """Clean up after test."""
        if hasattr(self, "patcher"):
            self.patcher.stop()

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_integration_get_request(self):
        """Integration test for GET request."""
        response = self.client.get("/users/1")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["name"], "Test User")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_integration_post_request(self):
        """Integration test for POST request."""
        payload = {"title": "Test Post", "content": "Test content"}
        response = self.client.post("/posts", json=payload)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["received"], payload)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_integration_404_error(self):
        """Integration test for 404 error handling."""
        with self.assertRaises(HTTPError) as context:
            self.client.get("/error/404")

        self.assertEqual(context.exception.status_code, 404)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_integration_500_retry(self):
        """Integration test for 500 error retry."""
        # This will fail all retries since our mock always returns 500
        with self.assertRaises(HTTPError) as context:
            self.client.get("/error/500")

        self.assertEqual(context.exception.status_code, 500)


# ============================================================================
# END-TO-END TESTS - 10% of test coverage
# ============================================================================


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests with real API (optional)."""

    def setUp(self):
        """Set up for E2E tests."""
        if ClientConfig and APIClient:
            # Use a real test API
            self.config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @unittest.skipUnless(
        socket.gethostbyname_ex("jsonplaceholder.typicode.com")[2], "Requires internet connection"
    )
    def test_e2e_real_api_get(self):
        """E2E test with real API - GET request."""
        response = self.client.get("/users/1")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("name", data)
        self.assertIn("email", data)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @unittest.skipUnless(
        socket.gethostbyname_ex("jsonplaceholder.typicode.com")[2], "Requires internet connection"
    )
    def test_e2e_real_api_post(self):
        """E2E test with real API - POST request."""
        payload = {"title": "Test Post", "body": "This is a test post", "userId": 1}
        response = self.client.post("/posts", json=payload)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)  # Should return created ID
        self.assertEqual(data["title"], payload["title"])


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
