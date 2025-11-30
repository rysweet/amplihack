"""Test configuration and fixtures for REST API Client tests.

This module provides shared fixtures, mock servers, and test utilities
following the testing pyramid principle.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest.mock import Mock

import pytest

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


@dataclass
class MockResponse:
    """Mock HTTP response for testing."""

    status_code: int
    headers: dict[str, str]
    content: bytes
    json_data: dict[str, Any] | None = None

    def json(self):
        if self.json_data is not None:
            return self.json_data
        return json.loads(self.content.decode())

    @property
    def text(self):
        return self.content.decode()


class MockHTTPHandler(BaseHTTPRequestHandler):
    """Mock HTTP handler for integration tests."""

    def do_GET(self):
        """Handle GET requests."""
        self._handle_request("GET")

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        self._handle_request("POST", body)

    def do_PUT(self):
        """Handle PUT requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        self._handle_request("PUT", body)

    def do_DELETE(self):
        """Handle DELETE requests."""
        self._handle_request("DELETE")

    def do_PATCH(self):
        """Handle PATCH requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        self._handle_request("PATCH", body)

    def _handle_request(self, method: str, body: bytes = b""):
        """Common request handling logic."""
        # Store request for inspection
        self.server.last_request = {
            "method": method,
            "path": self.path,
            "headers": dict(self.headers),
            "body": body,
        }

        # Check for special test scenarios
        if "/retry" in self.path:
            self._handle_retry_scenario()
        elif "/rate_limit" in self.path:
            self._handle_rate_limit_scenario()
        elif "/timeout" in self.path:
            time.sleep(5)  # Force timeout
        elif "/error/500" in self.path:
            self.send_error(500, "Internal Server Error")
        else:
            # Default success response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "method": method,
                "path": self.path,
                "body": body.decode() if body else None,
            }
            self.wfile.write(json.dumps(response).encode())

    def _handle_retry_scenario(self):
        """Handle retry test scenarios."""
        if not hasattr(self.server, "retry_count"):
            self.server.retry_count = 0

        self.server.retry_count += 1

        if self.server.retry_count < 3:
            # Fail first 2 attempts
            self.send_error(503, "Service Unavailable")
        else:
            # Succeed on 3rd attempt
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"retries": self.server.retry_count}).encode())

    def _handle_rate_limit_scenario(self):
        """Handle rate limit test scenarios."""
        self.send_response(429)
        self.send_header("Retry-After", "2")
        self.send_header("X-RateLimit-Remaining", "0")
        self.send_header("X-RateLimit-Reset", str(int(time.time()) + 2))
        self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""


@pytest.fixture
def mock_server():
    """Create a mock HTTP server for integration tests."""
    server = HTTPServer(("localhost", 0), MockHTTPHandler)
    server.timeout = 0.1

    # Start server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Get actual port
    port = server.server_port
    base_url = f"http://localhost:{port}"

    yield base_url, server

    # Cleanup
    server.shutdown()


@pytest.fixture
def mock_response_factory():
    """Factory for creating mock responses."""

    def create_response(
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> MockResponse:
        if json_data is not None and content is None:
            content = json.dumps(json_data).encode()
        elif content is None:
            content = b"{}"

        return MockResponse(
            status_code=status_code,
            headers=headers or {"Content-Type": "application/json"},
            content=content,
            json_data=json_data,
        )

    return create_response


@pytest.fixture
def rate_limit_headers():
    """Common rate limit headers for testing."""
    return {
        "X-RateLimit-Limit": "100",
        "X-RateLimit-Remaining": "99",
        "X-RateLimit-Reset": str(int(time.time()) + 3600),
        "Retry-After": "60",
    }


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = Mock(spec=logging.Logger)
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def request_counter():
    """Thread-safe request counter for concurrency tests."""

    class RequestCounter:
        def __init__(self):
            self.count = 0
            self.lock = threading.Lock()
            self.requests = []

        def increment(self, request_info=None):
            with self.lock:
                self.count += 1
                if request_info:
                    self.requests.append(request_info)

        def get_count(self):
            with self.lock:
                return self.count

    return RequestCounter()


@pytest.fixture
def mock_time():
    """Mock time module for testing rate limiting and retries."""

    class MockTime:
        def __init__(self):
            self.current_time = time.time()
            self.sleep_calls = []

        def time(self):
            return self.current_time

        def sleep(self, seconds):
            self.sleep_calls.append(seconds)
            self.current_time += seconds

        def advance(self, seconds):
            self.current_time += seconds

    return MockTime()


# Test data fixtures
@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "id": 123,
        "name": "Test Item",
        "tags": ["test", "sample"],
        "metadata": {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-02T00:00:00Z"},
    }


@pytest.fixture
def sample_headers():
    """Sample headers for testing."""
    return {
        "Authorization": "Bearer test_token",
        "User-Agent": "TestClient/1.0",
        "X-Request-ID": "test-123",
    }


@pytest.fixture
def ssl_context():
    """Mock SSL context for testing."""
    import ssl

    context = Mock(spec=ssl.SSLContext)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context
