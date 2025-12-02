"""Pytest configuration and fixtures for API client tests.

Provides common fixtures and test utilities.
"""

import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

# Global callback storage (thread-safe)
_callback_registry: dict[int, Callable] = {}
_callback_lock = threading.Lock()


class MockHTTPHandler(BaseHTTPRequestHandler):
    """Mock HTTP request handler for testing."""

    # Class-level response configuration
    response_status: int = 200
    response_body: str = '{"status": "ok"}'
    response_headers: dict[str, str] = {}

    def do_GET(self) -> None:
        """Handle GET request."""
        self._handle_request()

    def do_POST(self) -> None:
        """Handle POST request."""
        self._handle_request()

    def do_PUT(self) -> None:
        """Handle PUT request."""
        self._handle_request()

    def do_DELETE(self) -> None:
        """Handle DELETE request."""
        self._handle_request()

    def _handle_request(self) -> None:
        """Handle HTTP request with configured response."""
        # Call callback if set (using global registry)
        server_address = self.server.server_address
        if isinstance(server_address, tuple):
            server_port = server_address[1]
        else:
            return  # Shouldn't happen, but mypy needs this
        with _callback_lock:
            callback = _callback_registry.get(server_port)

        callback_handled = False
        if callback:
            # Call callback and check if it handled the response
            callback_handled = callback(self)

        # Only send response if callback didn't handle it
        if not callback_handled:
            # Send response
            self.send_response(self.response_status)

            # Send headers
            for key, value in self.response_headers.items():
                self.send_header(key, value)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Send body
            self.wfile.write(self.response_body.encode())

    def log_message(self, format: str, *args) -> None:
        """Suppress server logging."""


class MockHTTPServer:
    """Mock HTTP server for integration testing."""

    def __init__(self, port: int = 0) -> None:
        """Initialize mock server.

        Args:
            port: Port to bind (0 = random available port)
        """
        self.server = HTTPServer(("127.0.0.1", port), MockHTTPHandler)
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.thread: threading.Thread | None = None
        self._request_count = 0
        self._count_lock = threading.Lock()

    @property
    def request_count(self) -> int:
        """Get current request count (thread-safe)."""
        with self._count_lock:
            return self._request_count

    def _increment_count(self) -> None:
        """Increment request count (thread-safe)."""
        with self._count_lock:
            self._request_count += 1

    def set_response(
        self,
        status: int = 200,
        body: str = '{"status": "ok"}',
        headers: dict[str, str] | None = None,
    ) -> None:
        """Configure server response.

        Args:
            status: HTTP status code
            body: Response body
            headers: Response headers
        """
        MockHTTPHandler.response_status = status
        MockHTTPHandler.response_body = body
        MockHTTPHandler.response_headers = headers or {}

    def set_callback(self, callback: Callable | None = None) -> None:
        """Set request callback.

        Args:
            callback: Callable to invoke on each request (takes handler as argument)
                     If callback is provided, it must handle the full HTTP response
                     (send_response, send_header, end_headers, wfile.write).
                     If callback is None, only request counting is enabled.
        """
        # Store reference for closure
        server_instance = self

        def wrapper(handler):
            """Wrapper that counts requests and calls user callback."""
            server_instance._increment_count()
            if callback is not None:
                callback(handler)
                # Return True to signal that callback handled the response
                return True
            # Return False to let default handler send response
            return False

        # Register in global registry
        with _callback_lock:
            _callback_registry[self.port] = wrapper

    def start(self) -> None:
        """Start server in background thread."""
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop server."""
        self.server.shutdown()
        if self.thread:
            self.thread.join(timeout=5.0)

        # Clean up callback registry
        with _callback_lock:
            _callback_registry.pop(self.port, None)

    def __enter__(self) -> "MockHTTPServer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


@pytest.fixture
def mock_server():
    """Provide mock HTTP server for testing."""
    server = MockHTTPServer()
    # Set a simple counting callback by default
    server.set_callback(None)
    server.start()
    yield server
    server.stop()
