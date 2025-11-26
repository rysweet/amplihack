"""Integration tests for APIClient.

Tests complete request/response cycles with mock HTTP server.
These tests will FAIL until the client is fully implemented.

Testing Pyramid: Integration tests (30%)
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from email.utils import formatdate

import pytest
import responses


class TestBasicRequestResponseCycle:
    """Test complete request/response workflows."""

    @responses.activate
    def test_successful_get_request_complete_cycle(self):
        """Test complete GET request from client to response parsing."""
        from amplihack.api import APIClient

        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": [{"id": 1, "name": "Blackbeard"}]},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response.status_code == 200
        assert response.json() == {"users": [{"id": 1, "name": "Blackbeard"}]}

    @responses.activate
    def test_successful_post_request_with_json_data(self):
        """Test POST request with JSON body and response."""
        from amplihack.api import APIClient

        responses.add(
            responses.POST,
            "https://api.example.com/users",
            json={"id": 2, "name": "Anne Bonny", "created": True},
            status=201,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.post("/users", json_data={"name": "Anne Bonny"})

        assert response.status_code == 201
        assert response.json()["created"] is True
        assert response.json()["id"] == 2

    @responses.activate
    def test_put_request_update_cycle(self):
        """Test PUT request for updating resource."""
        from amplihack.api import APIClient

        responses.add(
            responses.PUT,
            "https://api.example.com/users/123",
            json={"id": 123, "name": "Captain Hook", "updated": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.put("/users/123", json_data={"name": "Captain Hook"})

        assert response.status_code == 200
        assert response.json()["updated"] is True

    @responses.activate
    def test_delete_request_cycle(self):
        """Test DELETE request."""
        from amplihack.api import APIClient

        responses.add(responses.DELETE, "https://api.example.com/users/123", status=204)

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/123")

        assert response.status_code == 204


class TestRetryWithActualDelays:
    """Test retry logic with actual sleep delays."""

    @responses.activate
    def test_retry_with_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff."""
        from amplihack.api import APIClient

        # First two requests fail, third succeeds
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            status=500,  # Fail
        )
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            status=500,  # Fail
        )
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"data": "success"},
            status=200,  # Success
        )

        client = APIClient(base_url="https://api.example.com")

        start_time = time.time()
        response = client.get("/data")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should have slept for 1s + 2s = 3s total
        assert elapsed >= 3.0
        assert elapsed < 4.0  # Allow some overhead

    @responses.activate
    def test_retry_eventually_fails_after_max_attempts(self):
        """Test that client gives up after max_retries."""
        from amplihack.api import APIClient, APIError

        # All requests fail
        for _ in range(4):  # Initial + 3 retries
            responses.add(responses.GET, "https://api.example.com/data", status=500)

        client = APIClient(base_url="https://api.example.com", max_retries=3)

        with pytest.raises(APIError):
            client.get("/data")

        # Should have made 4 requests total
        assert len(responses.calls) == 4

    @responses.activate
    def test_server_error_recovery(self):
        """Test recovery from transient server error."""
        from amplihack.api import APIClient

        # Server error then success
        responses.add(responses.GET, "https://api.example.com/users", status=503)
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": []},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response.status_code == 200
        assert len(responses.calls) == 2


class TestRateLimitIntegration:
    """Test rate limiting with actual delay handling."""

    @responses.activate
    def test_rate_limit_with_retry_after_header(self):
        """Test rate limit handling with Retry-After header."""
        from amplihack.api import APIClient

        # First request: rate limited with Retry-After
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            status=429,
            headers={"Retry-After": "2"},  # Wait 2 seconds
        )
        # Second request: success
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"data": "value"},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        start_time = time.time()
        response = client.get("/data")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should have waited at least 2 seconds
        assert elapsed >= 2.0
        assert len(responses.calls) == 2

    @responses.activate
    def test_rate_limit_with_http_date_retry_after(self):
        """Test rate limit with HTTP date in Retry-After."""
        from amplihack.api import APIClient

        # HTTP date 3 seconds in the future
        future_time = time.time() + 3
        http_date = formatdate(future_time, usegmt=True)

        responses.add(
            responses.GET,
            "https://api.example.com/data",
            status=429,
            headers={"Retry-After": http_date},
        )
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"success": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        start_time = time.time()
        response = client.get("/data")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should have waited approximately 3 seconds
        assert elapsed >= 1.8  # Allow some timing variance
        assert elapsed < 4.0

    @responses.activate
    def test_rate_limit_exhausts_retries(self):
        """Test that persistent rate limiting raises RateLimitError."""
        from amplihack.api import APIClient, RateLimitError

        # All requests return 429
        for _ in range(4):
            responses.add(
                responses.GET,
                "https://api.example.com/data",
                status=429,
                headers={"Retry-After": "1"},
            )

        client = APIClient(base_url="https://api.example.com", max_retries=3)

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/data")

        assert exc_info.value.retry_after == 1
        assert len(responses.calls) == 4  # Initial + 3 retries


class TestErrorHandlingIntegration:
    """Test error handling in complete request cycles."""

    @responses.activate
    def test_authentication_error_flow(self):
        """Test authentication error handling."""
        from amplihack.api import APIClient, AuthenticationError

        responses.add(
            responses.GET,
            "https://api.example.com/protected",
            json={"error": "Invalid token"},
            status=401,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/protected")

        assert exc_info.value.status_code == 401
        assert exc_info.value.response is not None

    @responses.activate
    def test_client_error_no_retry(self):
        """Test that 4xx errors don't trigger retry."""
        from amplihack.api import APIClient, APIError

        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"error": "Bad request"},
            status=400,
        )

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(APIError):
            client.get("/data")

        # Should only make one request (no retry)
        assert len(responses.calls) == 1

    @responses.activate
    def test_timeout_error_integration(self):
        """Test timeout handling in integration scenario."""
        import requests

        from amplihack.api import APIClient, TimeoutError

        def timeout_callback(request):
            raise requests.exceptions.ConnectTimeout("Connection timeout")

        responses.add_callback(
            responses.GET,
            "https://api.example.com/slow",
            callback=timeout_callback,
        )

        client = APIClient(base_url="https://api.example.com", timeout=(1, 5))

        with pytest.raises(TimeoutError) as exc_info:
            client.get("/slow")

        assert exc_info.value.timeout_type == "connect"


class TestConcurrentRequests:
    """Test thread safety with concurrent requests."""

    @responses.activate
    def test_multiple_concurrent_get_requests(self):
        """Test concurrent GET requests from multiple threads."""
        from amplihack.api import APIClient

        # Add multiple responses
        for i in range(10):
            responses.add(
                responses.GET,
                f"https://api.example.com/users/{i}",
                json={"id": i, "name": f"User{i}"},
                status=200,
            )

        client = APIClient(base_url="https://api.example.com")

        def fetch_user(user_id):
            response = client.get(f"/users/{user_id}")
            return response.json()

        # Execute 10 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_user, i) for i in range(10)]
            results = [f.result() for f in futures]

        assert len(results) == 10
        assert all(r["id"] in range(10) for r in results)

    @responses.activate
    def test_concurrent_requests_with_different_methods(self):
        """Test mixed HTTP methods concurrently."""
        from amplihack.api import APIClient

        responses.add(responses.GET, "https://api.example.com/users", status=200)
        responses.add(responses.POST, "https://api.example.com/users", status=201)
        responses.add(responses.PUT, "https://api.example.com/users/1", status=200)
        responses.add(responses.DELETE, "https://api.example.com/users/1", status=204)

        client = APIClient(base_url="https://api.example.com")

        def task1():
            return client.get("/users")

        def task2():
            return client.post("/users", json_data={"name": "Test"})

        def task3():
            return client.put("/users/1", json_data={"name": "Updated"})

        def task4():
            return client.delete("/users/1")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(task1),
                executor.submit(task2),
                executor.submit(task3),
                executor.submit(task4),
            ]
            results = [f.result() for f in futures]

        assert len(results) == 4

    @responses.activate
    def test_session_isolation_per_thread(self):
        """Test that each thread gets isolated session."""
        from amplihack.api import APIClient

        for _ in range(20):
            responses.add(
                responses.GET,
                "https://api.example.com/data",
                json={"data": "value"},
                status=200,
            )

        client = APIClient(base_url="https://api.example.com")
        results = []

        def worker():
            # Each thread should get its own session
            for _ in range(5):
                response = client.get("/data")
                results.append(response.status_code)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All requests should succeed
        assert len(results) == 20
        assert all(status == 200 for status in results)


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    @responses.activate
    def test_pagination_workflow(self):
        """Test fetching multiple pages of data."""
        from amplihack.api import APIClient

        # Page 1
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": [1, 2, 3], "next_page": 2},
            status=200,
        )
        # Page 2
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": [4, 5, 6], "next_page": 3},
            status=200,
        )
        # Page 3
        responses.add(
            responses.GET,
            "https://api.example.com/users",
            json={"users": [7, 8, 9], "next_page": None},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        all_users = []
        page = 1
        while True:
            response = client.get("/users", params={"page": page})
            data = response.json()
            all_users.extend(data["users"])

            if data["next_page"] is None:
                break
            page = data["next_page"]

        assert len(all_users) == 9
        assert all_users == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    @responses.activate
    def test_create_read_update_delete_workflow(self):
        """Test complete CRUD workflow."""
        from amplihack.api import APIClient

        # Create
        responses.add(
            responses.POST,
            "https://api.example.com/resources",
            json={"id": 42, "name": "treasure", "created": True},
            status=201,
        )

        # Read
        responses.add(
            responses.GET,
            "https://api.example.com/resources/42",
            json={"id": 42, "name": "treasure", "value": 1000},
            status=200,
        )

        # Update
        responses.add(
            responses.PUT,
            "https://api.example.com/resources/42",
            json={"id": 42, "name": "treasure", "value": 2000, "updated": True},
            status=200,
        )

        # Delete
        responses.add(responses.DELETE, "https://api.example.com/resources/42", status=204)

        client = APIClient(base_url="https://api.example.com")

        # Execute CRUD workflow
        create_response = client.post("/resources", json_data={"name": "treasure", "value": 1000})
        assert create_response.status_code == 201
        resource_id = create_response.json()["id"]

        read_response = client.get(f"/resources/{resource_id}")
        assert read_response.status_code == 200

        update_response = client.put(f"/resources/{resource_id}", json_data={"value": 2000})
        assert update_response.status_code == 200

        delete_response = client.delete(f"/resources/{resource_id}")
        assert delete_response.status_code == 204

    @responses.activate
    def test_retry_with_eventual_success_after_failures(self):
        """Test resilience to transient failures."""
        from amplihack.api import APIClient

        # Simulate intermittent failures
        responses.add(responses.GET, "https://api.example.com/data", status=503)
        responses.add(responses.GET, "https://api.example.com/data", status=502)
        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"recovered": True},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")

        start_time = time.time()
        response = client.get("/data")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert response.json()["recovered"] is True
        # Should have retried with backoff: 1s + 2s = 3s
        assert elapsed >= 3.0


class TestHeaderMerging:
    """Test header merging between client and request level."""

    @responses.activate
    def test_client_headers_included_in_request(self):
        """Test that client-level headers are sent with request."""
        from amplihack.api import APIClient

        def request_callback(request):
            # Verify headers present
            assert "Authorization" in request.headers
            assert request.headers["Authorization"] == "Bearer token123"
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/data",
            callback=request_callback,
        )

        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer token123"},
        )
        response = client.get("/data")

        assert response.status_code == 200

    @responses.activate
    def test_request_headers_override_client_headers(self):
        """Test that request-level headers override client headers."""
        from amplihack.api import APIClient

        def request_callback(request):
            # Should have request-level header, not client-level
            assert request.headers["X-Custom"] == "request-value"
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/data",
            callback=request_callback,
        )

        client = APIClient(base_url="https://api.example.com", headers={"X-Custom": "client-value"})
        response = client.get("/data", headers={"X-Custom": "request-value"})

        assert response.status_code == 200

    @responses.activate
    def test_headers_merged_not_replaced(self):
        """Test that request headers are merged with client headers."""
        from amplihack.api import APIClient

        def request_callback(request):
            # Both headers should be present
            assert request.headers["Authorization"] == "Bearer token"
            assert request.headers["X-Custom"] == "value"
            return (200, {}, '{"success": true}')

        responses.add_callback(
            responses.GET,
            "https://api.example.com/data",
            callback=request_callback,
        )

        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer token"},
        )
        response = client.get("/data", headers={"X-Custom": "value"})

        assert response.status_code == 200


class TestResourceCleanup:
    """Test resource cleanup in integration scenarios."""

    @responses.activate
    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up."""
        from amplihack.api import APIClient

        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"data": "value"},
            status=200,
        )

        with APIClient(base_url="https://api.example.com") as client:
            response = client.get("/data")
            assert response.status_code == 200

        # Client should be cleaned up after context exit

    @responses.activate
    def test_manual_close_cleanup(self):
        """Test manual cleanup with close()."""
        from amplihack.api import APIClient

        responses.add(
            responses.GET,
            "https://api.example.com/data",
            json={"data": "value"},
            status=200,
        )

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")
        assert response.status_code == 200

        client.close()
        # Should have cleaned up resources
