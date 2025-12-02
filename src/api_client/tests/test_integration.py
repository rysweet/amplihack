"""End-to-end tests with mock server.

Tests complete workflows against a mock HTTP server.
This is part of the 10% E2E test coverage.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


class MockAPIHandler(BaseHTTPRequestHandler):
    """Mock HTTP request handler for testing."""

    # Class-level configuration for test scenarios
    response_queue = []
    request_log = []
    delay_seconds = 0

    def log_message(self, format, *args):
        """Suppress default logging."""

    def _send_response(self, status_code, body=None, headers=None):
        """Helper to send HTTP response."""
        self.send_response(status_code)

        if headers:
            for key, value in headers.items():
                self.send_header(key, value)

        if body is not None:
            content = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if MockAPIHandler.delay_seconds > 0:
            time.sleep(MockAPIHandler.delay_seconds)

        MockAPIHandler.request_log.append(
            {"method": "GET", "path": self.path, "headers": dict(self.headers)}
        )

        self._route_request("GET")

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else ""

        MockAPIHandler.request_log.append(
            {"method": "POST", "path": self.path, "headers": dict(self.headers), "body": body}
        )

        self._route_request("POST", body)

    def do_PUT(self):
        """Handle PUT requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else ""

        MockAPIHandler.request_log.append(
            {"method": "PUT", "path": self.path, "headers": dict(self.headers), "body": body}
        )

        self._route_request("PUT", body)

    def do_PATCH(self):
        """Handle PATCH requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else ""

        MockAPIHandler.request_log.append(
            {"method": "PATCH", "path": self.path, "headers": dict(self.headers), "body": body}
        )

        self._route_request("PATCH", body)

    def do_DELETE(self):
        """Handle DELETE requests."""
        MockAPIHandler.request_log.append(
            {"method": "DELETE", "path": self.path, "headers": dict(self.headers)}
        )

        self._route_request("DELETE")

    def _route_request(self, method, body=None):
        """Route request to appropriate handler."""
        # Check for queued responses (for retry testing)
        if MockAPIHandler.response_queue:
            response = MockAPIHandler.response_queue.pop(0)
            self._send_response(
                response.get("status", 200), response.get("body"), response.get("headers")
            )
            return

        # Default routing
        if self.path == "/users":
            if method == "GET":
                self._send_response(200, {"users": [{"id": 1, "name": "Alice"}]})
            elif method == "POST":
                self._send_response(201, {"id": 2, "name": "Bob"})
        elif self.path.startswith("/users/"):
            user_id = self.path.split("/")[-1]
            if method == "GET":
                self._send_response(200, {"id": int(user_id), "name": "User"})
            elif method == "PUT":
                self._send_response(200, {"id": int(user_id), "updated": True})
            elif method == "PATCH":
                self._send_response(200, {"id": int(user_id), "patched": True})
            elif method == "DELETE":
                self._send_response(204)
        elif self.path == "/error/500":
            self._send_response(500, {"error": "Internal Server Error"})
        elif self.path == "/error/429":
            self._send_response(429, {"error": "Rate Limited"}, {"Retry-After": "1"})
        elif self.path == "/error/404":
            self._send_response(404, {"error": "Not Found"})
        elif self.path == "/slow":
            time.sleep(2)
            self._send_response(200, {"slow": True})
        else:
            self._send_response(404, {"error": "Not Found"})


@pytest.fixture
def mock_server():
    """Fixture to start/stop mock HTTP server."""
    # Find an available port
    server = HTTPServer(("127.0.0.1", 0), MockAPIHandler)
    port = server.server_address[1]

    # Reset handler state
    MockAPIHandler.response_queue = []
    MockAPIHandler.request_log = []
    MockAPIHandler.delay_seconds = 0

    # Start server in background thread
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    yield {"url": f"http://127.0.0.1:{port}", "server": server, "handler": MockAPIHandler}

    server.shutdown()


class TestBasicHTTPOperations:
    """E2E tests for basic HTTP operations."""

    def test_get_request(self, mock_server):
        """Should successfully make GET request."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data

    def test_post_request(self, mock_server):
        """Should successfully make POST request with JSON."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.post("/users", json={"name": "Charlie"})

        assert response.status_code == 201
        data = response.json()
        assert "id" in data

    def test_put_request(self, mock_server):
        """Should successfully make PUT request."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.put("/users/1", json={"name": "Updated"})

        assert response.status_code == 200
        data = response.json()
        assert data["updated"] is True

    def test_patch_request(self, mock_server):
        """Should successfully make PATCH request."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.patch("/users/1", json={"name": "Patched"})

        assert response.status_code == 200
        data = response.json()
        assert data["patched"] is True

    def test_delete_request(self, mock_server):
        """Should successfully make DELETE request."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.delete("/users/1")

        assert response.status_code == 204


class TestRetryIntegration:
    """E2E tests for retry behavior."""

    def test_retry_on_server_error(self, mock_server):
        """Should retry and succeed after initial 500 error."""
        from api_client import APIClient, RetryPolicy

        # Queue responses: first 500, then 200
        MockAPIHandler.response_queue = [
            {"status": 500, "body": {"error": "Server Error"}},
            {"status": 200, "body": {"success": True}},
        ]

        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        client = APIClient(base_url=mock_server["url"], retry_policy=policy)

        response = client.get("/flaky-endpoint")

        assert response.status_code == 200
        assert len(MockAPIHandler.request_log) == 2

    def test_retry_with_backoff(self, mock_server):
        """Should use exponential backoff between retries."""
        from api_client import APIClient, RetryPolicy

        # Queue multiple failures then success
        MockAPIHandler.response_queue = [
            {"status": 503, "body": {"error": "Service Unavailable"}},
            {"status": 503, "body": {"error": "Service Unavailable"}},
            {"status": 200, "body": {"success": True}},
        ]

        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        client = APIClient(base_url=mock_server["url"], retry_policy=policy)

        start = time.monotonic()
        response = client.get("/flaky-endpoint")
        elapsed = time.monotonic() - start

        assert response.status_code == 200
        # Should have waited some time due to backoff
        assert elapsed >= 0.1  # At least one backoff period


class TestRateLimitIntegration:
    """E2E tests for rate limit handling."""

    def test_respects_retry_after(self, mock_server):
        """Should respect Retry-After header."""
        from api_client import APIClient, RetryPolicy

        MockAPIHandler.response_queue = [
            {"status": 429, "body": {"error": "Rate Limited"}, "headers": {"Retry-After": "1"}},
            {"status": 200, "body": {"success": True}},
        ]

        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        client = APIClient(base_url=mock_server["url"], retry_policy=policy)

        start = time.monotonic()
        response = client.get("/rate-limited")
        elapsed = time.monotonic() - start

        assert response.status_code == 200
        # Should have waited at least 1 second (Retry-After value)
        assert elapsed >= 0.9


class TestErrorHandling:
    """E2E tests for error handling."""

    def test_raises_http_error_on_4xx(self, mock_server):
        """Should raise HTTPError for 4xx responses."""
        from api_client import APIClient, HTTPError

        client = APIClient(base_url=mock_server["url"])

        with pytest.raises(HTTPError) as exc_info:
            client.get("/error/404")

        assert exc_info.value.status_code == 404

    def test_raises_http_error_after_retries_exhausted(self, mock_server):
        """Should raise HTTPError when all retries fail."""
        from api_client import APIClient, HTTPError, RetryPolicy

        # Always return 500
        MockAPIHandler.response_queue = [
            {"status": 500, "body": {"error": "Error"}},
            {"status": 500, "body": {"error": "Error"}},
            {"status": 500, "body": {"error": "Error"}},
            {"status": 500, "body": {"error": "Error"}},
        ]

        policy = RetryPolicy(max_retries=2, base_delay=0.05)
        client = APIClient(base_url=mock_server["url"], retry_policy=policy)

        with pytest.raises(HTTPError) as exc_info:
            client.get("/always-fails")

        assert exc_info.value.status_code == 500


class TestTimeoutEnforcement:
    """E2E tests for timeout behavior."""

    def test_timeout_enforced(self, mock_server):
        """Should enforce request timeout."""
        from api_client import APIClient, NetworkError

        # Set server to delay responses
        MockAPIHandler.delay_seconds = 5

        client = APIClient(
            base_url=mock_server["url"],
            timeout=0.5,  # 500ms timeout
        )

        with pytest.raises(NetworkError):
            client.get("/slow")

        # Reset delay
        MockAPIHandler.delay_seconds = 0


class TestThreadSafety:
    """E2E tests for thread-safe operations."""

    def test_concurrent_requests(self, mock_server):
        """Should handle concurrent requests safely."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"], thread_safe=True)

        results = []
        errors = []

        def make_request(i):
            try:
                response = client.get(f"/users/{i}")
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Concurrent requests failed: {errors}"
        assert len(results) == 20
        assert all(status == 200 for status in results)

    def test_rate_limiter_thread_safety(self, mock_server):
        """Should rate limit correctly across threads."""
        from api_client import APIClient, RateLimiter

        # Very restrictive rate limit
        limiter = RateLimiter(requests_per_second=5.0, burst_size=2)
        client = APIClient(base_url=mock_server["url"], rate_limiter=limiter, thread_safe=True)

        request_times = []
        lock = threading.Lock()

        def make_request(i):
            start = time.monotonic()
            client.get(f"/users/{i}")
            with lock:
                request_times.append(time.monotonic() - start)

        start_time = time.monotonic()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            for f in futures:
                f.result()
        total_time = time.monotonic() - start_time

        # 10 requests at 5/s with burst of 2 should take at least 1.6s
        # (2 immediate, then 8 at 5/s = 1.6s)
        assert total_time >= 1.0  # Allow some tolerance


class TestContextManager:
    """E2E tests for context manager usage."""

    def test_context_manager_cleanup(self, mock_server):
        """Should properly clean up resources."""
        from api_client import APIClient

        with APIClient(base_url=mock_server["url"]) as client:
            response = client.get("/users")
            assert response.status_code == 200

        # After exiting context, client should still work but session closed
        # This tests that cleanup happened without error


class TestHeadersAndAuth:
    """E2E tests for headers and authentication."""

    def test_default_headers_sent(self, mock_server):
        """Should send default headers with all requests."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"], headers={"X-Custom-Header": "TestValue"})
        client.get("/users")

        # Check request log
        last_request = MockAPIHandler.request_log[-1]
        assert last_request["headers"].get("X-Custom-Header") == "TestValue"

    def test_authorization_header_sent(self, mock_server):
        """Should send Authorization header."""
        from api_client import APIClient

        client = APIClient(
            base_url=mock_server["url"], headers={"Authorization": "Bearer test-token"}
        )
        client.get("/users")

        last_request = MockAPIHandler.request_log[-1]
        assert "Bearer test-token" in last_request["headers"].get("Authorization", "")


class TestJSONHandling:
    """E2E tests for JSON request/response handling."""

    def test_json_request_body(self, mock_server):
        """Should properly serialize JSON request body."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        client.post("/users", json={"name": "TestUser", "age": 25})

        last_request = MockAPIHandler.request_log[-1]
        body = json.loads(last_request["body"])
        assert body["name"] == "TestUser"
        assert body["age"] == 25

    def test_json_response_parsing(self, mock_server):
        """Should properly parse JSON response."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])
        response = client.get("/users")

        data = response.json()
        assert isinstance(data, dict)
        assert "users" in data


class TestCompleteWorkflow:
    """E2E tests for complete API workflows."""

    def test_crud_workflow(self, mock_server):
        """Should handle complete CRUD workflow."""
        from api_client import APIClient

        client = APIClient(base_url=mock_server["url"])

        # Create
        create_response = client.post("/users", json={"name": "NewUser"})
        assert create_response.status_code == 201

        # Read
        read_response = client.get("/users/1")
        assert read_response.status_code == 200

        # Update
        update_response = client.put("/users/1", json={"name": "UpdatedUser"})
        assert update_response.status_code == 200

        # Patch
        patch_response = client.patch("/users/1", json={"name": "PatchedUser"})
        assert patch_response.status_code == 200

        # Delete
        delete_response = client.delete("/users/1")
        assert delete_response.status_code == 204

    def test_error_recovery_workflow(self, mock_server):
        """Should recover from errors and continue."""
        from api_client import APIClient, RetryPolicy

        MockAPIHandler.response_queue = [
            {"status": 503, "body": {"error": "Temporarily down"}},
            {"status": 200, "body": {"recovered": True}},
        ]

        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        client = APIClient(base_url=mock_server["url"], retry_policy=policy)

        # First request recovers after retry
        response = client.get("/flaky")
        assert response.status_code == 200

        # Second request should work immediately
        response = client.get("/users")
        assert response.status_code == 200
