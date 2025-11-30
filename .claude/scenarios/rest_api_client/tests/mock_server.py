"""Mock server for testing REST API client."""

import random
import threading
import time

from flask import Flask, jsonify, request


class MockAPIServer:
    """Mock API server for testing."""

    def __init__(self, port=5000):
        self.app = Flask(__name__)
        self.port = port
        self.rate_limit_counter = {}
        self.server_thread = None
        self.setup_routes()

    def setup_routes(self):
        """Setup mock API routes."""

        @self.app.route("/health")
        def health():
            return jsonify({"status": "ok", "timestamp": time.time()})

        @self.app.route("/users", methods=["GET"])
        def get_users():
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 10, type=int)

            users = [
                {"id": i, "name": f"User {i}"}
                for i in range((page - 1) * limit + 1, page * limit + 1)
            ]

            return jsonify({"data": users, "page": page, "limit": limit, "total": 100})

        @self.app.route("/users/<int:user_id>", methods=["GET"])
        def get_user(user_id):
            if user_id == 999:
                return jsonify({"error": "User not found"}), 404

            return jsonify(
                {
                    "id": user_id,
                    "name": f"User {user_id}",
                    "email": f"user{user_id}@example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            )

        @self.app.route("/users", methods=["POST"])
        def create_user():
            data = request.get_json()

            # Validate required fields
            if not data.get("name") or not data.get("email"):
                return jsonify(
                    {
                        "error": "Validation failed",
                        "fields": {
                            "name": "Required" if not data.get("name") else None,
                            "email": "Required" if not data.get("email") else None,
                        },
                    }
                ), 422

            # Validate email format
            if "@" not in data.get("email", ""):
                return jsonify(
                    {"error": "Validation failed", "fields": {"email": "Invalid format"}}
                ), 422

            return jsonify({"id": random.randint(100, 999), **data}), 201

        @self.app.route("/users/<int:user_id>", methods=["PUT"])
        def update_user(user_id):
            data = request.get_json()
            return jsonify({"id": user_id, **data})

        @self.app.route("/users/<int:user_id>", methods=["DELETE"])
        def delete_user(user_id):
            return "", 204

        @self.app.route("/protected", methods=["GET"])
        def protected():
            auth_header = request.headers.get("Authorization")

            if not auth_header:
                return jsonify({"error": "No authorization"}), 401

            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Invalid auth format"}), 401

            token = auth_header.replace("Bearer ", "")
            if token == "invalid-token":
                return jsonify({"error": "Invalid token"}), 401

            return jsonify({"data": "protected resource"})

        @self.app.route("/rate-limited", methods=["GET"])
        def rate_limited():
            client_id = request.remote_addr

            # Simple rate limiting
            if client_id not in self.rate_limit_counter:
                self.rate_limit_counter[client_id] = []

            now = time.time()
            # Clean old entries
            self.rate_limit_counter[client_id] = [
                t for t in self.rate_limit_counter[client_id] if now - t < 60
            ]

            if len(self.rate_limit_counter[client_id]) >= 5:
                return jsonify({"error": "Rate limit exceeded"}), 429, {"Retry-After": "60"}

            self.rate_limit_counter[client_id].append(now)
            return jsonify({"data": "success"})

        @self.app.route("/flaky", methods=["GET"])
        def flaky():
            """Endpoint that fails randomly."""
            if random.random() < 0.5:
                return jsonify({"error": "Server error"}), 500
            return jsonify({"data": "success"})

        @self.app.route("/slow", methods=["GET"])
        def slow():
            """Endpoint that responds slowly."""
            delay = request.args.get("delay", 2, type=float)
            time.sleep(delay)
            return jsonify({"data": "slow response"})

        @self.app.route("/echo", methods=["POST"])
        def echo():
            """Echo back the request."""
            return jsonify(
                {
                    "headers": dict(request.headers),
                    "json": request.get_json(),
                    "args": dict(request.args),
                    "method": request.method,
                }
            )

        @self.app.route("/status/<int:code>", methods=["GET"])
        def status(code):
            """Return specific status code."""
            return jsonify({"status": code}), code

    def start(self):
        """Start the mock server."""
        self.server_thread = threading.Thread(
            target=lambda: self.app.run(
                host="127.0.0.1", port=self.port, debug=False, use_reloader=False
            )
        )
        self.server_thread.daemon = True
        self.server_thread.start()

        # Wait for server to start
        time.sleep(0.5)

    def stop(self):
        """Stop the mock server."""
        # Flask doesn't have a clean shutdown in testing
        # In production, you'd use a proper server

    @property
    def url(self):
        """Get server URL."""
        return f"http://127.0.0.1:{self.port}"


# Pytest fixtures for using mock server
import pytest


@pytest.fixture(scope="session")
def mock_server():
    """Create and start mock server for testing."""
    server = MockAPIServer(port=5001)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def server_url(mock_server):
    """Get mock server URL."""
    return mock_server.url


# Example test using real mock server
def test_with_real_server(server_url):
    """Example test using the mock server."""
    import requests

    # Test health endpoint
    response = requests.get(f"{server_url}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Test user creation
    response = requests.post(
        f"{server_url}/users", json={"name": "Test User", "email": "test@example.com"}
    )
    assert response.status_code == 201
    assert "id" in response.json()

    # Test rate limiting
    for _ in range(6):
        response = requests.get(f"{server_url}/rate-limited")
        if response.status_code == 429:
            assert response.headers.get("Retry-After") == "60"
            break
