"""Simple mock HTTP server for integration testing.

Provides a lightweight HTTP server for testing the REST client without
external dependencies. Uses only standard library components.
"""

import http.server
import json
import socketserver
import threading
import time
import urllib.parse
from typing import Any


class MockHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler for testing."""

    # Class-level storage for request tracking
    requests_received: list[dict[str, Any]] = []
    response_queue: list[dict[str, Any]] = []
    default_response = {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"message": "Default response"},
    }

    def log_message(self, format, *args):
        """Suppress default logging to keep test output clean."""

    def _send_response(self, response_config: dict[str, Any]):
        """Send a configured response."""
        status = response_config.get("status", 200)
        headers = response_config.get("headers", {})
        body = response_config.get("body", {})

        self.send_response(status)

        for header, value in headers.items():
            self.send_header(header, value)
        self.end_headers()

        if body:
            if isinstance(body, dict):
                body_str = json.dumps(body)
            else:
                body_str = str(body)
            self.wfile.write(body_str.encode())

    def _record_request(self):
        """Record details of the incoming request."""
        # Parse URL and query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Read request body if present
        content_length = int(self.headers.get("Content-Length", 0))
        body = None
        if content_length > 0:
            body_bytes = self.rfile.read(content_length)
            try:
                body = json.loads(body_bytes.decode())
            except json.JSONDecodeError:
                body = body_bytes.decode()

        request_data = {
            "method": self.command,
            "path": parsed_url.path,
            "query_params": query_params,
            "headers": dict(self.headers),
            "body": body,
            "timestamp": time.time(),
        }

        MockHTTPRequestHandler.requests_received.append(request_data)

    def do_GET(self):
        """Handle GET requests."""
        self._record_request()

        # Special endpoints for testing
        if self.path.startswith("/status/"):
            # Return specific status codes for testing
            status_code = int(self.path.split("/")[-1])
            self._send_response({"status": status_code, "body": {"status": status_code}})
        elif self.path == "/slow":
            # Simulate slow response
            time.sleep(2)
            self._send_response({"status": 200, "body": {"message": "Slow response"}})
        elif self.path.startswith("/users"):
            # Mock users endpoint
            self._send_response(
                {"status": 200, "body": {"users": [{"id": 1, "name": "Test User"}]}}
            )
        else:
            # Use queued response or default
            if MockHTTPRequestHandler.response_queue:
                response = MockHTTPRequestHandler.response_queue.pop(0)
            else:
                response = MockHTTPRequestHandler.default_response
            self._send_response(response)

    def do_POST(self):
        """Handle POST requests."""
        self._record_request()

        if self.path == "/users":
            # Mock user creation
            self._send_response({"status": 201, "body": {"id": 123, "message": "User created"}})
        elif self.path == "/error":
            # Trigger an error for testing
            self._send_response({"status": 500, "body": {"error": "Internal server error"}})
        else:
            if MockHTTPRequestHandler.response_queue:
                response = MockHTTPRequestHandler.response_queue.pop(0)
            else:
                response = {"status": 201, "body": {"created": True}}
            self._send_response(response)

    def do_PUT(self):
        """Handle PUT requests."""
        self._record_request()

        if MockHTTPRequestHandler.response_queue:
            response = MockHTTPRequestHandler.response_queue.pop(0)
        else:
            response = {"status": 200, "body": {"updated": True}}
        self._send_response(response)

    def do_DELETE(self):
        """Handle DELETE requests."""
        self._record_request()

        if MockHTTPRequestHandler.response_queue:
            response = MockHTTPRequestHandler.response_queue.pop(0)
        else:
            response = {"status": 204, "body": ""}
        self._send_response(response)

    def do_PATCH(self):
        """Handle PATCH requests."""
        self._record_request()

        if MockHTTPRequestHandler.response_queue:
            response = MockHTTPRequestHandler.response_queue.pop(0)
        else:
            response = {"status": 200, "body": {"patched": True}}
        self._send_response(response)


class MockHTTPServer:
    """Mock HTTP server for integration testing."""

    def __init__(self, port: int = 0):
        """Initialize mock server on specified or random port."""
        self.port = port
        self.server = None
        self.thread = None
        self.handler_class = MockHTTPRequestHandler

    def start(self):
        """Start the mock server in a background thread."""
        # Create server with SO_REUSEADDR to avoid "Address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("127.0.0.1", self.port), self.handler_class)

        # Get actual port if random port was requested
        self.port = self.server.server_address[1]

        # Start server in background thread
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        # Give server time to start
        time.sleep(0.1)

        return self.port

    def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)

    def reset(self):
        """Reset request tracking and response queue."""
        MockHTTPRequestHandler.requests_received.clear()
        MockHTTPRequestHandler.response_queue.clear()

    def get_requests(self) -> list[dict[str, Any]]:
        """Get all requests received by the server."""
        return MockHTTPRequestHandler.requests_received.copy()

    def queue_response(self, response: dict[str, Any]):
        """Queue a response to be returned on the next request."""
        MockHTTPRequestHandler.response_queue.append(response)

    def set_default_response(self, response: dict[str, Any]):
        """Set the default response when queue is empty."""
        MockHTTPRequestHandler.default_response = response

    @property
    def url(self) -> str:
        """Get the base URL of the mock server."""
        return f"http://127.0.0.1:{self.port}"


class RateLimitingMockServer(MockHTTPServer):
    """Mock server that simulates rate limiting responses."""

    class RateLimitingHandler(MockHTTPRequestHandler):
        """Handler that returns 429 Too Many Requests after threshold."""

        request_times: list[float] = []
        rate_limit = 2  # requests per second

        def do_GET(self):
            """Handle GET with rate limiting simulation."""
            current_time = time.time()

            # Clean old request times (older than 1 second)
            self.request_times = [t for t in self.request_times if current_time - t < 1.0]

            # Check if rate limit exceeded
            if len(self.request_times) >= self.rate_limit:
                self._send_response(
                    {
                        "status": 429,
                        "headers": {"Retry-After": "1"},
                        "body": {"error": "Too many requests"},
                    }
                )
            else:
                self.request_times.append(current_time)
                super().do_GET()

    def __init__(self, port: int = 0, rate_limit: int = 2):
        """Initialize rate limiting mock server."""
        super().__init__(port)
        self.handler_class = self.RateLimitingHandler
        self.handler_class.rate_limit = rate_limit


class FlakeyMockServer(MockHTTPServer):
    """Mock server that simulates intermittent failures."""

    class FlakeyHandler(MockHTTPRequestHandler):
        """Handler that fails intermittently."""

        request_count = 0
        failure_pattern = [True, True, False]  # Fail, Fail, Success

        def do_GET(self):
            """Handle GET with intermittent failures."""
            should_fail = self.failure_pattern[self.request_count % len(self.failure_pattern)]
            self.request_count += 1

            if should_fail:
                # Simulate connection drop (close without response)
                self.close_connection = True
                return
            super().do_GET()

    def __init__(self, port: int = 0, failure_pattern: list[bool] = None):
        """Initialize flakey mock server."""
        super().__init__(port)
        self.handler_class = self.FlakeyHandler
        if failure_pattern:
            self.handler_class.failure_pattern = failure_pattern


def create_mock_server(server_type: str = "basic", **kwargs) -> MockHTTPServer:
    """Factory function to create different types of mock servers.

    Args:
        server_type: Type of server ("basic", "rate_limiting", "flakey")
        **kwargs: Additional arguments for specific server types

    Returns:
        Configured mock server instance
    """
    if server_type == "rate_limiting":
        return RateLimitingMockServer(**kwargs)
    if server_type == "flakey":
        return FlakeyMockServer(**kwargs)
    return MockHTTPServer(**kwargs)


# Example usage for testing
if __name__ == "__main__":
    # Create and start a basic mock server
    server = MockHTTPServer(port=8888)
    port = server.start()
    print(f"Mock server running on http://127.0.0.1:{port}")

    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped")
