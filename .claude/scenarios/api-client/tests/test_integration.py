"""
Integration tests with mock server.

Tests complete request/response cycles with a mock HTTP server,
validating end-to-end behavior.

Coverage areas:
- Complete request/response cycles
- Mock server interactions
- Real HTTP flow (mocked)
- Multiple request sequences
- Error scenarios end-to-end
- Authentication flows
- Rate limiting in practice
- Retry logic in practice
"""

import json
from unittest.mock import Mock, patch

import pytest


class TestBasicIntegration:
    """Basic integration tests with mock server."""

    def test_full_get_request_cycle(self, mock_server) -> None:
        """Test complete GET request/response cycle."""
        from amplihack.api_client import RestClient

        mock_server.add_route(
            "GET", "/users/123", response_data={"id": 123, "name": "Alice"}, status=200
        )

        client = RestClient(base_url=mock_server.url)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.ok = True
            mock_response.text = json.dumps({"id": 123, "name": "Alice"})
            mock_response.json.return_value = {"id": 123, "name": "Alice"}
            mock_response.headers = {"Content-Type": "application/json"}
            mock_get.return_value = mock_response

            response = client.get("/users/123")

            assert response.status_code == 200
            assert response.json()["name"] == "Alice"

    def test_full_post_request_cycle(self, mock_server) -> None:
        """Test complete POST request/response cycle."""
        from amplihack.api_client import RestClient

        mock_server.add_route(
            "POST", "/users", response_data={"id": 124, "name": "Bob"}, status=201
        )

        client = RestClient(base_url=mock_server.url)

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.ok = True
            mock_response.json.return_value = {"id": 124, "name": "Bob"}
            mock_post.return_value = mock_response

            body = {"name": "Bob", "email": "bob@example.com"}
            response = client.post("/users", json=body)

            assert response.status_code == 201
            assert response.json()["id"] == 124

    def test_multiple_sequential_requests(self, mock_server) -> None:
        """Test multiple requests in sequence."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url)

        # Setup mock responses
        responses = [
            Mock(status_code=200, ok=True, json=lambda: {"id": 1}),
            Mock(status_code=200, ok=True, json=lambda: {"id": 2}),
            Mock(status_code=200, ok=True, json=lambda: {"id": 3}),
        ]

        with patch("requests.get", side_effect=responses):
            result1 = client.get("/items/1")
            result2 = client.get("/items/2")
            result3 = client.get("/items/3")

            assert result1.json()["id"] == 1
            assert result2.json()["id"] == 2
            assert result3.json()["id"] == 3


class TestRetryIntegration:
    """Integration tests for retry logic."""

    def test_retry_with_eventual_success(self, mock_server) -> None:
        """Test retry logic with eventual success."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, max_retries=3, retry_backoff_factor=0.1)

        # First two fail, third succeeds
        responses = [
            Mock(status_code=500, ok=False),
            Mock(status_code=500, ok=False),
            Mock(status_code=200, ok=True, json=lambda: {"success": True}),
        ]

        with patch("requests.get", side_effect=responses):
            response = client.get("/flaky")

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_retry_exhaustion(self, mock_server) -> None:
        """Test retry exhaustion after max attempts."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RetryExhaustedError

        client = RestClient(base_url=mock_server.url, max_retries=2, retry_backoff_factor=0.1)

        # Always fail
        with patch("requests.get", return_value=Mock(status_code=500, ok=False)):
            with pytest.raises(RetryExhaustedError):
                client.get("/always-fails")

    def test_retry_on_connection_error(self, mock_server) -> None:
        """Test retry on connection errors."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, max_retries=2, retry_backoff_factor=0.1)

        # First two fail with connection error, third succeeds
        def side_effect(*args, **kwargs):
            if side_effect.call_count < 3:
                side_effect.call_count += 1
                raise ConnectionError("Connection refused")
            return Mock(status_code=200, ok=True)

        side_effect.call_count = 0

        with patch("requests.get", side_effect=side_effect):
            response = client.get("/endpoint")
            assert response.status_code == 200


class TestRateLimitIntegration:
    """Integration tests for rate limiting."""

    def test_rate_limit_enforcement(self, mock_server) -> None:
        """Test rate limiting is enforced across requests."""
        import time

        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, rate_limit_per_second=2)

        with patch("requests.get", return_value=Mock(status_code=200, ok=True)):
            start = time.time()

            # Make 5 requests
            for i in range(5):
                client.get(f"/item/{i}")

            elapsed = time.time() - start

            # Should take at least 2 seconds
            assert elapsed >= 2.0

    def test_429_retry_with_retry_after(self, mock_server) -> None:
        """Test 429 response with Retry-After header."""
        import time

        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, max_retries=2)

        # First response is 429, second is success
        responses = [
            Mock(status_code=429, ok=False, headers={"Retry-After": "1"}),
            Mock(status_code=200, ok=True, json=lambda: {"success": True}),
        ]

        with patch("requests.get", side_effect=responses):
            start = time.time()
            response = client.get("/limited")
            elapsed = time.time() - start

            assert response.status_code == 200
            assert elapsed >= 1.0  # Should have waited at least 1 second


class TestAuthenticationIntegration:
    """Integration tests for authentication."""

    def test_bearer_auth_flow(self, mock_server) -> None:
        """Test Bearer token authentication flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import BearerAuth

        auth = BearerAuth(token="test_token_123")
        client = RestClient(base_url=mock_server.url, auth=auth)

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, ok=True, json=lambda: {"user": "alice"})

            response = client.get("/protected")

            # Verify Authorization header was sent
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test_token_123"
            assert response.status_code == 200

    def test_api_key_auth_flow(self, mock_server) -> None:
        """Test API key authentication flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import APIKeyAuth

        auth = APIKeyAuth(key="test_key", location="header", name="X-API-Key")
        client = RestClient(base_url=mock_server.url, auth=auth)

        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            # Verify API key was sent
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["headers"]["X-API-Key"] == "test_key"

    def test_401_authentication_error(self, mock_server) -> None:
        """Test 401 authentication error handling."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import AuthenticationError

        client = RestClient(base_url=mock_server.url)

        with patch("requests.get", return_value=Mock(status_code=401, ok=False)):
            with pytest.raises(AuthenticationError):
                client.get("/protected")


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_404_not_found_flow(self, mock_server) -> None:
        """Test 404 Not Found error flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import NotFoundError

        client = RestClient(base_url=mock_server.url)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.ok = False
            mock_response.text = "Not found"
            mock_get.return_value = mock_response

            with pytest.raises(NotFoundError) as exc_info:
                client.get("/missing")

            assert exc_info.value.status_code == 404

    def test_500_server_error_flow(self, mock_server) -> None:
        """Test 500 Internal Server Error flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import ServerError

        client = RestClient(base_url=mock_server.url, max_retries=0)

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.ok = False
            mock_response.text = "Internal server error"
            mock_get.return_value = mock_response

            with pytest.raises(ServerError) as exc_info:
                client.get("/error")

            assert exc_info.value.status_code == 500

    def test_connection_error_flow(self, mock_server) -> None:
        """Test connection error flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RequestError

        client = RestClient(base_url=mock_server.url, max_retries=0)

        with patch("requests.get", side_effect=ConnectionError("Connection refused")):
            with pytest.raises(RequestError):
                client.get("/endpoint")

    def test_timeout_error_flow(self, mock_server) -> None:
        """Test timeout error flow."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import TimeoutError as APITimeoutError

        client = RestClient(base_url=mock_server.url, timeout=1, max_retries=0)

        with patch("requests.get", side_effect=TimeoutError("Request timed out")):
            with pytest.raises(APITimeoutError):
                client.get("/slow")


class TestComplexWorkflows:
    """Integration tests for complex workflows."""

    def test_crud_workflow(self, mock_server) -> None:
        """Test complete CRUD workflow."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url)

        # Create
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=201, ok=True, json=lambda: {"id": 123, "name": "Alice"}
            )

            create_response = client.post(
                "/users", json={"name": "Alice", "email": "alice@example.com"}
            )
            assert create_response.status_code == 201
            user_id = create_response.json()["id"]

        # Read
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200, ok=True, json=lambda: {"id": 123, "name": "Alice"}
            )

            read_response = client.get(f"/users/{user_id}")
            assert read_response.status_code == 200

        # Update
        with patch("requests.put") as mock_put:
            mock_put.return_value = Mock(
                status_code=200, ok=True, json=lambda: {"id": 123, "name": "Alice Smith"}
            )

            update_response = client.put(f"/users/{user_id}", json={"name": "Alice Smith"})
            assert update_response.status_code == 200

        # Delete
        with patch("requests.delete") as mock_delete:
            mock_delete.return_value = Mock(status_code=204, ok=True)

            delete_response = client.delete(f"/users/{user_id}")
            assert delete_response.status_code == 204

    def test_pagination_workflow(self, mock_server) -> None:
        """Test pagination workflow."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url)

        # Page 1
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                ok=True,
                json=lambda: {"data": [{"id": 1}, {"id": 2}], "page": 1, "has_more": True},
            )

            page1 = client.get("/users", params={"page": 1, "per_page": 2})
            assert len(page1.json()["data"]) == 2

        # Page 2
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                ok=True,
                json=lambda: {"data": [{"id": 3}, {"id": 4}], "page": 2, "has_more": False},
            )

            page2 = client.get("/users", params={"page": 2, "per_page": 2})
            assert len(page2.json()["data"]) == 2
            assert page2.json()["has_more"] is False

    def test_batch_operations(self, mock_server) -> None:
        """Test batch operations workflow."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url)

        users_to_create = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
            {"name": "Charlie", "email": "charlie@example.com"},
        ]

        results = []

        for idx, user_data in enumerate(users_to_create):
            with patch("requests.post") as mock_post:
                mock_post.return_value = Mock(
                    status_code=201,
                    ok=True,
                    json=lambda idx=idx: {"id": idx + 1, "name": users_to_create[idx]["name"]},
                )

                response = client.post("/users", json=user_data)
                results.append(response.json())

        assert len(results) == 3
        assert results[0]["name"] == "Alice"
        assert results[1]["name"] == "Bob"
        assert results[2]["name"] == "Charlie"


class TestConcurrency:
    """Integration tests for concurrent requests."""

    def test_concurrent_requests(self, mock_server) -> None:
        """Test multiple concurrent requests."""
        import threading

        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url)

        results = []
        lock = threading.Lock()

        def make_request(item_id: int) -> None:
            with patch("requests.get") as mock_get:
                mock_get.return_value = Mock(status_code=200, ok=True, json=lambda: {"id": item_id})

                response = client.get(f"/items/{item_id}")
                with lock:
                    results.append(response.json())

        threads = [threading.Thread(target=make_request, args=(i,)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 5

    def test_concurrent_rate_limiting(self, mock_server) -> None:
        """Test rate limiting with concurrent requests."""
        import threading
        import time

        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, rate_limit_per_second=2)

        start = time.time()

        def make_request() -> None:
            with patch("requests.get", return_value=Mock(status_code=200, ok=True)):
                client.get("/endpoint")

        threads = [threading.Thread(target=make_request) for _ in range(6)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.time() - start

        # 6 requests at 2/second should take at least 2 seconds
        assert elapsed >= 2.0


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_complete_api_integration(self, mock_server) -> None:
        """Test complete API integration scenario."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import BearerAuth

        # Setup authenticated client with rate limiting and retries
        auth = BearerAuth(token="test_token")
        client = RestClient(
            base_url=mock_server.url, auth=auth, max_retries=3, rate_limit_per_second=5, timeout=30
        )

        # Authenticate (simulated)
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200, ok=True, json=lambda: {"token": "test_token"}
            )

            auth_response = client.post(
                "/auth/login",
                json={"username": "user", "password": "pass"},  # pragma: allowlist secret
            )
            assert auth_response.status_code == 200

        # Make authenticated request
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200, ok=True, json=lambda: {"user": "alice", "role": "admin"}
            )

            profile_response = client.get("/profile")
            assert profile_response.status_code == 200
            assert profile_response.json()["role"] == "admin"

        # Handle transient failure with retry
        responses = [
            Mock(status_code=503, ok=False),
            Mock(status_code=200, ok=True, json=lambda: {"data": "success"}),
        ]

        with patch("requests.get", side_effect=responses):
            data_response = client.get("/data")
            assert data_response.status_code == 200

    def test_realistic_error_recovery(self, mock_server) -> None:
        """Test realistic error recovery scenario."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=mock_server.url, max_retries=3, retry_backoff_factor=0.1)

        # Sequence: connection error, 500 error, 503 error, success
        def side_effect(*args, **kwargs):
            call_count = side_effect.count
            side_effect.count += 1

            if call_count == 0:
                raise ConnectionError("Connection refused")
            if call_count == 1:
                return Mock(status_code=500, ok=False)
            if call_count == 2:
                return Mock(status_code=503, ok=False)
            return Mock(status_code=200, ok=True, json=lambda: {"recovered": True})

        side_effect.count = 0

        with patch("requests.get", side_effect=side_effect):
            response = client.get("/resilient")
            assert response.status_code == 200
            assert response.json()["recovered"] is True
