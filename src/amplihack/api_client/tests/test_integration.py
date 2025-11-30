"""Integration tests for complete API client workflows - TDD approach.

Tests complete scenarios combining all components.
"""

import asyncio
import json
import time

import pytest
from aioresponses import aioresponses

from amplihack.api_client import (
    APIClient,
    APIConfig,
    RateLimitConfig,
)
from amplihack.api_client.exceptions import (
    RateLimitError,
    ServerError,
    ValidationError,
)


class TestCompleteWorkflows:
    """End-to-end integration tests for complete API workflows."""

    @pytest.mark.asyncio
    async def test_authenticated_api_workflow(self):
        """Test complete authenticated API workflow."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=30,
            max_retries=3,
        )

        with aioresponses() as m:
            # Step 1: Authentication
            m.post(
                "https://api.example.com/auth/login",
                payload={"token": "bearer-token-123", "expires_in": 3600},
                status=200,
            )

            # Step 2: Get user profile (authenticated)
            def check_auth_header(url, **kwargs):
                headers = kwargs.get("headers", {})
                if headers.get("Authorization") != "Bearer bearer-token-123":
                    return aioresponses.CallbackResult(status=401)
                return aioresponses.CallbackResult(
                    status=200,
                    payload={"id": 1, "name": "Test User", "email": "test@example.com"},
                )

            m.get(
                "https://api.example.com/users/me",
                callback=check_auth_header,
            )

            # Step 3: Update profile
            m.patch(
                "https://api.example.com/users/me",
                payload={"id": 1, "name": "Updated User", "email": "test@example.com"},
                status=200,
            )

            # Step 4: Logout
            m.post(
                "https://api.example.com/auth/logout",
                status=204,
            )

            async with APIClient(config) as client:
                # Authenticate
                auth_response = await client.post(
                    "/auth/login",
                    json={"username": "test", "password": "secret"},  # pragma: allowlist secret
                )
                assert auth_response.status_code == 200
                token = auth_response.data["token"]

                # Update client headers with token
                client.config.headers["Authorization"] = f"Bearer {token}"

                # Get profile
                profile_response = await client.get("/users/me")
                assert profile_response.status_code == 200
                assert profile_response.data["name"] == "Test User"

                # Update profile
                update_response = await client.patch(
                    "/users/me",
                    json={"name": "Updated User"},
                )
                assert update_response.status_code == 200
                assert update_response.data["name"] == "Updated User"

                # Logout
                logout_response = await client.post("/auth/logout")
                assert logout_response.status_code == 204

    @pytest.mark.asyncio
    async def test_pagination_with_rate_limiting(self):
        """Test paginated requests with rate limit handling."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=3,
            retry_delay=0.01,
        )

        rate_limit_hit = False

        def page_callback(url, **kwargs):
            nonlocal rate_limit_hit
            params = kwargs.get("params", {})
            page = int(params.get("page", 1))

            # Simulate rate limit on page 3
            if page == 3 and not rate_limit_hit:
                rate_limit_hit = True
                return aioresponses.CallbackResult(
                    status=429,
                    headers={"Retry-After": "0.1"},
                )

            # Return page data
            items_per_page = 10
            start = (page - 1) * items_per_page
            end = start + items_per_page

            if page <= 5:  # 5 pages total
                return aioresponses.CallbackResult(
                    status=200,
                    payload={
                        "page": page,
                        "total_pages": 5,
                        "items": [{"id": i} for i in range(start, end)],
                    },
                )
            return aioresponses.CallbackResult(
                status=404,
                payload={"error": "Page not found"},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/items",
                callback=page_callback,
                repeat=True,
            )

            async with APIClient(config) as client:
                all_items = []
                page = 1

                while page <= 5:
                    try:
                        response = await client.get(
                            "/items",
                            params={"page": page},
                        )
                        all_items.extend(response.data["items"])
                        page += 1
                    except RateLimitError:
                        # Should be handled by retry logic
                        await asyncio.sleep(0.1)

                assert len(all_items) == 50  # 5 pages * 10 items
                assert all_items[0]["id"] == 0
                assert all_items[-1]["id"] == 49

    @pytest.mark.asyncio
    async def test_bulk_operations_with_error_recovery(self):
        """Test bulk operations with partial failures and recovery."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=2,
            retry_delay=0.01,
        )

        # Track which items have been processed
        processed_items = set()
        failed_items = []

        def create_callback(url, **kwargs):
            data = kwargs.get("json", {})
            item_id = data.get("id")

            # Simulate failures for specific items
            if item_id in [3, 7]:  # These items always fail
                return aioresponses.CallbackResult(
                    status=400,
                    payload={"error": f"Invalid data for item {item_id}"},
                )

            # Simulate transient failure for item 5
            if item_id == 5 and item_id not in processed_items:
                return aioresponses.CallbackResult(status=503)

            processed_items.add(item_id)
            return aioresponses.CallbackResult(
                status=201,
                payload={"id": item_id, "status": "created"},
            )

        with aioresponses() as m:
            m.post(
                "https://api.example.com/items",
                callback=create_callback,
                repeat=True,
            )

            async with APIClient(config) as client:
                items_to_create = [{"id": i, "name": f"Item {i}"} for i in range(10)]
                results = {"success": [], "failed": []}

                for item in items_to_create:
                    try:
                        response = await client.post("/items", json=item)
                        results["success"].append(response.data)
                    except ValidationError as e:
                        results["failed"].append(
                            {
                                "item": item,
                                "error": str(e),
                            }
                        )
                    except Exception as e:
                        # Unexpected errors
                        results["failed"].append(
                            {
                                "item": item,
                                "error": f"Unexpected: {e}",
                            }
                        )

                # Verify results
                assert len(results["success"]) == 8  # 10 - 2 permanent failures
                assert len(results["failed"]) == 2  # Items 3 and 7
                failed_ids = [f["item"]["id"] for f in results["failed"]]
                assert 3 in failed_ids
                assert 7 in failed_ids
                assert 5 in processed_items  # Item 5 succeeded after retry

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_rate_limiting(self):
        """Test concurrent requests respecting rate limits."""
        config = APIConfig(
            base_url="https://api.example.com",
            rate_limit=RateLimitConfig(
                strategy="token_bucket",
                capacity=5,
                refill_rate=5.0,  # 5 requests per second
            ),
        )

        request_times = []

        def track_request(url, **kwargs):
            request_times.append(time.time())
            return aioresponses.CallbackResult(
                status=200,
                payload={"id": len(request_times)},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/resource",
                callback=track_request,
                repeat=True,
            )

            async with APIClient(config) as client:
                # Try to make 10 concurrent requests
                tasks = [client.get("/resource") for _ in range(10)]
                responses = await asyncio.gather(*tasks)

                assert len(responses) == 10
                assert all(r.status_code == 200 for r in responses)

                # Verify rate limiting spread requests over time
                duration = request_times[-1] - request_times[0]
                assert duration >= 1.0  # Should take at least 1 second for 10 requests at 5/sec

    @pytest.mark.asyncio
    async def test_streaming_response_handling(self):
        """Test handling streaming responses."""
        config = APIConfig(base_url="https://api.example.com")

        chunks = [
            b'{"event": "start", "id": 1}\n',
            b'{"event": "progress", "percentage": 50}\n',
            b'{"event": "complete", "result": "success"}\n',
        ]

        async def stream_callback(url, **kwargs):
            async def generate():
                for chunk in chunks:
                    yield chunk
                    await asyncio.sleep(0.01)

            return aioresponses.CallbackResult(
                status=200,
                body=generate(),
                headers={"Content-Type": "application/x-ndjson"},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/stream",
                callback=stream_callback,
            )

            async with APIClient(config) as client:
                events = []
                async for chunk in client.stream("/stream"):
                    if chunk:
                        event = json.loads(chunk.decode())
                        events.append(event)

                assert len(events) == 3
                assert events[0]["event"] == "start"
                assert events[1]["percentage"] == 50
                assert events[2]["result"] == "success"

    @pytest.mark.asyncio
    async def test_timeout_and_retry_interaction(self):
        """Test timeout behavior with retry logic."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=0.1,  # 100ms timeout
            max_retries=3,
            retry_delay=0.01,
        )

        call_count = 0

        async def slow_callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # First two attempts are slow
                await asyncio.sleep(0.2)  # Exceeds timeout
            # Third attempt is fast
            return aioresponses.CallbackResult(
                status=200,
                payload={"success": True},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/slow",
                callback=slow_callback,
                repeat=True,
            )

            async with APIClient(config) as client:
                response = await client.get("/slow")
                assert response.status_code == 200
                assert call_count == 3  # Two timeouts, then success

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker pattern for failing services."""
        config = APIConfig(
            base_url="https://api.example.com",
            circuit_breaker_enabled=True,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=0.5,
        )

        fail_count = 0

        def failing_service(url, **kwargs):
            nonlocal fail_count
            fail_count += 1
            if fail_count <= 5:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(
                status=200,
                payload={"status": "recovered"},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/unreliable",
                callback=failing_service,
                repeat=True,
            )

            async with APIClient(config) as client:
                # First 3 requests fail and open circuit
                for i in range(3):
                    with pytest.raises(ServerError):
                        await client.get("/unreliable")

                # Circuit is now open, requests fail fast
                with pytest.raises(Exception) as exc_info:
                    await client.get("/unreliable")
                assert "Circuit breaker open" in str(exc_info.value)

                # Wait for circuit to reset
                await asyncio.sleep(0.6)

                # Circuit should be half-open, trying again
                response = await client.get("/unreliable")
                assert response.status_code == 200
                assert response.data["status"] == "recovered"

    @pytest.mark.asyncio
    async def test_request_id_tracking(self):
        """Test request ID tracking through retries."""
        config = APIConfig(
            base_url="https://api.example.com",
            max_retries=2,
            retry_delay=0.01,
        )

        request_ids_seen = []

        def track_request_id(url, **kwargs):
            headers = kwargs.get("headers", {})
            request_id = headers.get("X-Request-ID")
            request_ids_seen.append(request_id)

            if len(request_ids_seen) < 2:
                return aioresponses.CallbackResult(status=503)
            return aioresponses.CallbackResult(
                status=200,
                payload={"request_id": request_id},
            )

        with aioresponses() as m:
            m.get(
                "https://api.example.com/tracked",
                callback=track_request_id,
                repeat=True,
            )

            async with APIClient(config) as client:
                response = await client.get(
                    "/tracked",
                    headers={"X-Request-ID": "test-123"},
                )

                assert response.status_code == 200
                # Same request ID used through all retries
                assert all(rid == "test-123" for rid in request_ids_seen)
                assert len(request_ids_seen) == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_connection_pooling(self):
        """Test connection pooling and reuse."""
        config = APIConfig(
            base_url="https://api.example.com",
            connection_limit=2,
            connection_ttl=60,
        )

        connection_ids = []

        def track_connection(url, **kwargs):
            # Simulate connection tracking
            conn_id = id(kwargs.get("session"))  # Fake connection ID
            connection_ids.append(conn_id)
            return aioresponses.CallbackResult(
                status=200,
                payload={"connection": len(connection_ids)},
            )

        with aioresponses() as m:
            for i in range(5):
                m.get(
                    f"https://api.example.com/test{i}",
                    callback=track_connection,
                )

            async with APIClient(config) as client:
                # Make multiple requests that should reuse connections
                responses = []
                for i in range(5):
                    response = await client.get(f"/test{i}")
                    responses.append(response)

                assert len(responses) == 5
                assert all(r.status_code == 200 for r in responses)
                # Connections should be reused (pool size 2, 5 requests)
                # Note: This is simulated behavior
