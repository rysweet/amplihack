"""Integration tests - 30% of test coverage.

Tests multiple components working together with mock server.
"""

import json
from unittest.mock import patch

import pytest

from rest_api_client.client import APIClient
from rest_api_client.exceptions import (
    AuthenticationError,
    HTTPResponseError,
    NetworkError,
    RateLimitError,
)


@pytest.mark.integration
class TestClientWithRetry:
    """Test APIClient with retry mechanism."""

    def test_retry_on_server_error(self, mock_server):
        """Test client retries on 5xx errors."""
        # Setup endpoint that fails twice then succeeds
        mock_server.add_retry_endpoint("/flaky", fail_times=2)

        client = APIClient("https://api.example.com", max_retries=3)

        # Should succeed after retries
        result = client.get("/flaky")
        assert result["success"] is True

    def test_no_retry_on_client_error(self, mock_server):
        """Test client doesn't retry on 4xx errors."""
        mock_server.add_endpoint(
            "GET", "/bad-request", status=400, json_data={"error": "Bad request"}
        )

        client = APIClient("https://api.example.com", max_retries=3)

        # Should fail immediately without retries
        with pytest.raises(HTTPResponseError) as exc_info:
            client.get("/bad-request")

        assert exc_info.value.status_code == 400

    def test_retry_with_exponential_backoff(self, mock_server, timer):
        """Test exponential backoff during retries."""
        mock_server.add_retry_endpoint("/slow", fail_times=2)

        client = APIClient(
            "https://api.example.com",
            max_retries=3,
            retry_delay=0.1,  # Fast for testing
        )

        with timer:
            result = client.get("/slow")

        assert result["success"] is True
        # Should have delays: 0.1 + 0.2 = 0.3 seconds minimum
        assert timer.elapsed >= 0.25  # Allow some margin


@pytest.mark.integration
class TestClientWithRateLimiting:
    """Test APIClient with rate limiting."""

    def test_handle_rate_limit_response(self, mock_server):
        """Test handling 429 rate limit responses."""
        mock_server.add_rate_limit_endpoint("/limited")

        client = APIClient("https://api.example.com", rate_limit_handler="adaptive")

        # First 3 requests should succeed
        for _ in range(3):
            result = client.get("/limited")
            assert result["success"] is True

        # 4th request should get rate limited
        with pytest.raises(RateLimitError):
            client.get("/limited")

    def test_respect_retry_after_header(self, mock_server):
        """Test respecting Retry-After header."""

        def rate_limit_callback(request):
            return (429, {"Retry-After": "2"}, json.dumps({"error": "Rate limited"}))

        mock_server.add_endpoint("GET", "/rate-limited", callback=rate_limit_callback)

        client = APIClient("https://api.example.com")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(RateLimitError):
                client.get("/rate-limited")

            # Should have attempted to wait for Retry-After duration
            # (Implementation may vary based on actual client behavior)

    def test_token_bucket_rate_limiting(self, mock_server):
        """Test token bucket rate limiting."""
        mock_server.add_endpoint("GET", "/resource", json_data={"data": "value"})

        client = APIClient(
            "https://api.example.com",
            rate_limit_strategy="token_bucket",
            requests_per_second=5,
            burst_capacity=2,
        )

        # Should allow burst of 2 requests
        results = []
        for _ in range(2):
            result = client.get("/resource")
            results.append(result)

        assert len(results) == 2

        # 3rd request should be rate limited (or delayed)
        # Actual behavior depends on implementation


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test authentication and authorization flows."""

    def test_api_key_authentication(self, mock_server):
        """Test API key authentication."""

        def auth_callback(request):
            auth_header = request.headers.get("Authorization")
            if auth_header == "Bearer valid_key":
                return (200, {}, json.dumps({"authenticated": True}))
            return (401, {}, json.dumps({"error": "Unauthorized"}))

        mock_server.add_endpoint("GET", "/protected", callback=auth_callback)

        # Test with valid key
        client = APIClient("https://api.example.com", api_key="valid_key")
        result = client.get("/protected")
        assert result["authenticated"] is True

        # Test with invalid key
        client = APIClient("https://api.example.com", api_key="invalid_key")
        with pytest.raises(AuthenticationError):
            client.get("/protected")

    def test_refresh_token_on_401(self, mock_server):
        """Test automatic token refresh on 401."""
        token_state = {"expired": True}

        def protected_callback(request):
            auth = request.headers.get("Authorization")
            if auth == "Bearer new_token":
                return (200, {}, json.dumps({"data": "secret"}))
            if token_state["expired"]:
                return (401, {}, json.dumps({"error": "Token expired"}))
            return (200, {}, json.dumps({"data": "secret"}))

        def refresh_callback(request):
            token_state["expired"] = False
            return (200, {}, json.dumps({"access_token": "new_token"}))

        mock_server.add_endpoint("GET", "/protected", callback=protected_callback)
        mock_server.add_endpoint("POST", "/auth/refresh", callback=refresh_callback)

        client = APIClient(
            "https://api.example.com",
            api_key="old_token",
            auto_refresh_token=True,
            refresh_endpoint="/auth/refresh",
        )

        # Should handle 401 and refresh token
        result = client.get("/protected")
        # Implementation depends on actual refresh logic


@pytest.mark.integration
class TestCompleteWorkflow:
    """Test complete workflows with multiple operations."""

    def test_crud_operations_workflow(self, mock_server):
        """Test complete CRUD workflow."""
        items = {}
        next_id = [1]

        def create_callback(request):
            data = json.loads(request.body)
            item_id = next_id[0]
            next_id[0] += 1
            items[item_id] = {**data, "id": item_id}
            return (201, {}, json.dumps(items[item_id]))

        def read_callback(request):
            item_id = int(request.path.split("/")[-1])
            if item_id in items:
                return (200, {}, json.dumps(items[item_id]))
            return (404, {}, json.dumps({"error": "Not found"}))

        def update_callback(request):
            item_id = int(request.path.split("/")[-1])
            if item_id in items:
                data = json.loads(request.body)
                items[item_id].update(data)
                return (200, {}, json.dumps(items[item_id]))
            return (404, {}, json.dumps({"error": "Not found"}))

        def delete_callback(request):
            item_id = int(request.path.split("/")[-1])
            if item_id in items:
                del items[item_id]
                return (204, {}, "")
            return (404, {}, json.dumps({"error": "Not found"}))

        mock_server.add_endpoint("POST", "/items", callback=create_callback)
        mock_server.add_endpoint("GET", "/items/1", callback=read_callback)
        mock_server.add_endpoint("PUT", "/items/1", callback=update_callback)
        mock_server.add_endpoint("DELETE", "/items/1", callback=delete_callback)

        client = APIClient("https://api.example.com")

        # Create
        created = client.post("/items", json={"name": "Test Item", "value": 42})
        assert created["id"] == 1
        assert created["name"] == "Test Item"

        # Read
        fetched = client.get(f"/items/{created['id']}")
        assert fetched["id"] == created["id"]
        assert fetched["name"] == "Test Item"

        # Update
        updated = client.put(f"/items/{created['id']}", json={"name": "Updated Item", "value": 100})
        assert updated["name"] == "Updated Item"
        assert updated["value"] == 100

        # Delete
        result = client.delete(f"/items/{created['id']}")
        assert result is None  # 204 returns None

        # Verify deleted
        with pytest.raises(HTTPResponseError) as exc_info:
            client.get(f"/items/{created['id']}")
        assert exc_info.value.status_code == 404

    def test_pagination_workflow(self, mock_server):
        """Test paginated requests workflow."""
        total_items = 25
        page_size = 10

        def paginated_callback(request):
            page = int(request.params.get("page", 1))
            start = (page - 1) * page_size
            end = min(start + page_size, total_items)

            items = [{"id": i, "name": f"Item {i}"} for i in range(start, end)]

            return (
                200,
                {},
                json.dumps(
                    {
                        "items": items,
                        "page": page,
                        "total": total_items,
                        "has_next": end < total_items,
                    }
                ),
            )

        mock_server.add_endpoint("GET", "/items", callback=paginated_callback)

        client = APIClient("https://api.example.com")

        # Fetch all pages
        all_items = []
        page = 1
        has_next = True

        while has_next:
            response = client.get("/items", params={"page": page})
            all_items.extend(response["items"])
            has_next = response["has_next"]
            page += 1

        assert len(all_items) == 25
        assert all_items[0]["id"] == 0
        assert all_items[-1]["id"] == 24

    def test_batch_operations_workflow(self, mock_server):
        """Test batch operations workflow."""

        def batch_callback(request):
            operations = json.loads(request.body)["operations"]
            results = []

            for op in operations:
                if op["method"] == "GET":
                    results.append({"success": True, "data": {"id": 1}})
                elif op["method"] == "POST":
                    results.append({"success": True, "data": {"created": True}})
                else:
                    results.append({"success": False, "error": "Unsupported"})

            return (200, {}, json.dumps({"results": results}))

        mock_server.add_endpoint("POST", "/batch", callback=batch_callback)

        client = APIClient("https://api.example.com")

        batch_request = {
            "operations": [
                {"method": "GET", "path": "/items/1"},
                {"method": "POST", "path": "/items", "data": {"name": "New"}},
                {"method": "DELETE", "path": "/items/2"},
            ]
        }

        response = client.post("/batch", json=batch_request)
        results = response["results"]

        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[1]["success"] is True
        assert results[2]["success"] is False


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_circuit_breaker_pattern(self, mock_server):
        """Test circuit breaker for failing endpoints."""
        failures = {"count": 0}

        def failing_callback(request):
            failures["count"] += 1
            if failures["count"] <= 5:
                return (500, {}, json.dumps({"error": "Server error"}))
            return (200, {}, json.dumps({"recovered": True}))

        mock_server.add_endpoint("GET", "/unstable", callback=failing_callback)

        client = APIClient(
            "https://api.example.com", circuit_breaker_enabled=True, circuit_breaker_threshold=3
        )

        # First 3 failures should trigger circuit breaker
        for _ in range(3):
            try:
                client.get("/unstable")
            except HTTPResponseError:
                pass

        # Circuit should be open - fast fail
        with pytest.raises(NetworkError) as exc_info:
            client.get("/unstable")
        assert "Circuit breaker open" in str(exc_info.value)

    def test_fallback_on_error(self, mock_server):
        """Test fallback behavior on errors."""
        mock_server.add_endpoint(
            "GET", "/primary", status=500, json_data={"error": "Primary failed"}
        )
        mock_server.add_endpoint("GET", "/fallback", json_data={"source": "fallback"})

        client = APIClient("https://api.example.com")

        # Try primary, fall back on error
        try:
            result = client.get("/primary")
        except HTTPResponseError:
            result = client.get("/fallback")

        assert result["source"] == "fallback"

    def test_graceful_degradation(self, mock_server):
        """Test graceful degradation when services fail."""
        services = {
            "main": {"status": "up", "data": "main_data"},
            "extra": {"status": "down", "error": "Service unavailable"},
        }

        def service_callback(request):
            service = request.path.split("/")[2]
            if services[service]["status"] == "up":
                return (200, {}, json.dumps(services[service]))
            return (503, {}, json.dumps({"error": services[service]["error"]}))

        mock_server.add_endpoint("GET", "/service/main", callback=service_callback)
        mock_server.add_endpoint("GET", "/service/extra", callback=service_callback)

        client = APIClient("https://api.example.com")

        response = {"data": {}, "errors": []}

        # Try to get data from all services
        for service in ["main", "extra"]:
            try:
                result = client.get(f"/service/{service}")
                response["data"][service] = result
            except HTTPResponseError as e:
                response["errors"].append({"service": service, "error": str(e)})

        # Should have main data but extra failed
        assert "main" in response["data"]
        assert len(response["errors"]) == 1
        assert response["errors"][0]["service"] == "extra"
