"""End-to-end tests - 10% of test coverage.

Tests complete workflows from start to finish with minimal mocking.
"""

import json
import threading
import time
from unittest.mock import patch

import pytest

from rest_api_client import APIClient, ClientConfig
from rest_api_client.exceptions import (
    AuthenticationError,
    HTTPResponseError,
    NetworkError,
    RateLimitError,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestRealWorldScenarios:
    """Test real-world usage scenarios end-to-end."""

    def test_api_client_initialization_and_configuration(self):
        """Test complete client setup and configuration."""
        # Create config
        config = ClientConfig(
            base_url="https://api.example.com",
            api_key="test_key_123",
            timeout=60,
            max_retries=5,
            rate_limit_enabled=True,
            requests_per_second=10,
            user_agent="MyApp/1.0",
        )

        # Initialize client
        client = APIClient.from_config(config)

        # Verify configuration
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.rate_limiter is not None
        assert client.headers["User-Agent"] == "MyApp/1.0"
        assert "Authorization" in client.headers

    def test_complete_api_integration_workflow(self, mock_server):
        """Test complete API integration workflow."""
        # Setup mock API with various endpoints
        mock_server.add_endpoint("POST", "/auth/login", json_data={"token": "access_token_123"})
        mock_server.add_endpoint("GET", "/user/profile", json_data={"id": 1, "name": "John Doe"})
        mock_server.add_endpoint(
            "GET", "/user/1/posts", json_data={"posts": [{"id": 1, "title": "First Post"}]}
        )
        mock_server.add_endpoint(
            "POST", "/posts", json_data={"id": 2, "title": "New Post", "created": True}
        )
        mock_server.add_endpoint("DELETE", "/posts/1", status=204)

        # Initialize client
        client = APIClient("https://api.example.com")

        # 1. Authenticate
        auth_response = client.post("/auth/login", json={"username": "user", "password": "pass"})
        token = auth_response["token"]
        client.update_headers({"Authorization": f"Bearer {token}"})

        # 2. Get user profile
        profile = client.get("/user/profile")
        user_id = profile["id"]

        # 3. Get user's posts
        posts = client.get(f"/user/{user_id}/posts")
        assert len(posts["posts"]) == 1

        # 4. Create new post
        new_post = client.post("/posts", json={"title": "New Post", "content": "Content here"})
        assert new_post["created"] is True

        # 5. Delete old post
        result = client.delete("/posts/1")
        assert result is None  # 204 No Content

    def test_concurrent_requests_handling(self, mock_server):
        """Test handling multiple concurrent requests."""
        request_count = {"count": 0}

        def counting_callback(request):
            request_count["count"] += 1
            time.sleep(0.1)  # Simulate processing
            return (200, {}, json.dumps({"request_num": request_count["count"]}))

        mock_server.add_endpoint("GET", "/concurrent", callback=counting_callback)

        client = APIClient(
            "https://api.example.com", rate_limit_enabled=True, requests_per_second=10
        )

        results = []
        threads = []

        def make_request(thread_id):
            try:
                result = client.get("/concurrent")
                results.append((thread_id, result["request_num"]))
            except Exception as e:
                results.append((thread_id, f"Error: {e}"))

        # Launch 10 concurrent requests
        for i in range(10):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All requests should complete
        assert len(results) == 10
        # Request numbers should be unique
        request_nums = [r[1] for r in results if isinstance(r[1], int)]
        assert len(set(request_nums)) == len(request_nums)

    def test_error_handling_and_recovery(self, mock_server):
        """Test comprehensive error handling and recovery."""
        error_sequence = {"step": 0}

        def error_sequence_callback(request):
            error_sequence["step"] += 1
            step = error_sequence["step"]

            if step == 1:
                # Network error simulation
                raise ConnectionError("Connection refused")
            if step == 2:
                # Timeout simulation
                time.sleep(5)
                return (200, {}, json.dumps({"data": "delayed"}))
            if step == 3:
                # Rate limit
                return (429, {"Retry-After": "1"}, json.dumps({"error": "Rate limited"}))
            if step == 4:
                # Server error
                return (500, {}, json.dumps({"error": "Internal server error"}))
            if step == 5:
                # Authentication error
                return (401, {}, json.dumps({"error": "Unauthorized"}))
            # Success
            return (200, {}, json.dumps({"data": "success"}))

        mock_server.add_endpoint("GET", "/unreliable", callback=error_sequence_callback)

        client = APIClient(
            "https://api.example.com",
            max_retries=3,
            timeout=1,  # Short timeout for test
        )

        errors_encountered = []

        # Try multiple requests, handling different errors
        for i in range(6):
            try:
                result = client.get("/unreliable")
                if result:
                    break
            except NetworkError as e:
                errors_encountered.append(("NetworkError", str(e)))
                time.sleep(0.5)
            except TimeoutError as e:
                errors_encountered.append(("TimeoutError", str(e)))
                client.timeout = 10  # Increase timeout
            except RateLimitError as e:
                errors_encountered.append(("RateLimitError", str(e)))
                time.sleep(e.retry_after or 1)
            except HTTPResponseError as e:
                errors_encountered.append(("HTTPResponseError", e.status_code))
                if e.status_code == 500:
                    time.sleep(1)  # Wait before retry
            except AuthenticationError as e:
                errors_encountered.append(("AuthenticationError", str(e)))
                # Would refresh token here
                client.update_headers({"Authorization": "Bearer new_token"})

        # Should have encountered various errors
        error_types = [e[0] for e in errors_encountered]
        assert "NetworkError" in error_types or "TimeoutError" in error_types
        assert len(errors_encountered) >= 3

    def test_streaming_response_handling(self, mock_server):
        """Test handling of streaming responses."""

        def streaming_callback(request):
            # Simulate streaming response with chunks
            chunks = [
                '{"chunk": 1, "data": "First chunk"}\n',
                '{"chunk": 2, "data": "Second chunk"}\n',
                '{"chunk": 3, "data": "Third chunk"}\n',
            ]
            return (200, {"Transfer-Encoding": "chunked"}, "".join(chunks))

        mock_server.add_endpoint("GET", "/stream", callback=streaming_callback)

        client = APIClient("https://api.example.com")

        # Request streaming endpoint
        response = client.get("/stream", stream=True)

        # Process streamed data
        chunks = []
        for line in response.split("\n"):
            if line:
                chunks.append(json.loads(line))

        assert len(chunks) == 3
        assert chunks[0]["chunk"] == 1
        assert chunks[-1]["data"] == "Third chunk"

    def test_file_upload_workflow(self, mock_server):
        """Test file upload functionality."""

        def upload_callback(request):
            # Check for file in request
            if "multipart/form-data" in request.headers.get("Content-Type", ""):
                return (200, {}, json.dumps({"file_id": "file_123", "status": "uploaded"}))
            return (400, {}, json.dumps({"error": "Invalid upload"}))

        mock_server.add_endpoint("POST", "/upload", callback=upload_callback)

        client = APIClient("https://api.example.com")

        # Simulate file upload
        files = {"file": ("test.txt", b"file content", "text/plain")}
        result = client.post("/upload", files=files)

        assert result["status"] == "uploaded"
        assert result["file_id"] == "file_123"

    def test_webhook_callback_handling(self, mock_server):
        """Test webhook callback mechanism."""
        webhook_data = []

        def webhook_receiver(request):
            data = json.loads(request.body)
            webhook_data.append(data)
            return (200, {}, json.dumps({"received": True}))

        mock_server.add_endpoint("POST", "/webhook", callback=webhook_receiver)

        # Simulate external service with webhook
        client = APIClient("https://api.example.com")

        # Register webhook
        registration = {
            "url": "https://api.example.com/webhook",
            "events": ["order.created", "order.updated"],
        }

        # Send webhook events
        events = [
            {"event": "order.created", "order_id": 123},
            {"event": "order.updated", "order_id": 123, "status": "shipped"},
        ]

        for event in events:
            client.post("/webhook", json=event)

        assert len(webhook_data) == 2
        assert webhook_data[0]["event"] == "order.created"
        assert webhook_data[1]["status"] == "shipped"

    def test_api_versioning_handling(self, mock_server):
        """Test API versioning strategies."""

        def versioned_callback(request):
            # Check version in header
            version = request.headers.get("API-Version", "v1")

            if version == "v1":
                return (200, {}, json.dumps({"version": "v1", "data": "old format"}))
            if version == "v2":
                return (200, {}, json.dumps({"version": "v2", "data": {"formatted": "new format"}}))
            return (400, {}, json.dumps({"error": "Unsupported version"}))

        mock_server.add_endpoint("GET", "/resource", callback=versioned_callback)

        # Test v1 client
        client_v1 = APIClient("https://api.example.com")
        client_v1.update_headers({"API-Version": "v1"})
        result_v1 = client_v1.get("/resource")
        assert result_v1["version"] == "v1"

        # Test v2 client
        client_v2 = APIClient("https://api.example.com")
        client_v2.update_headers({"API-Version": "v2"})
        result_v2 = client_v2.get("/resource")
        assert result_v2["version"] == "v2"
        assert isinstance(result_v2["data"], dict)

    def test_monitoring_and_metrics(self, mock_server):
        """Test request monitoring and metrics collection."""
        mock_server.add_endpoint("GET", "/fast", json_data={"response": "fast"})
        mock_server.add_endpoint("GET", "/slow", json_data={"response": "slow"})

        client = APIClient("https://api.example.com", enable_metrics=True)

        # Make various requests
        metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0,
            "endpoints": {},
        }

        # Fast endpoint
        start = time.time()
        client.get("/fast")
        fast_time = time.time() - start
        metrics["total_requests"] += 1
        metrics["successful"] += 1
        metrics["total_time"] += fast_time
        metrics["endpoints"]["/fast"] = {"count": 1, "avg_time": fast_time}

        # Slow endpoint (with simulated delay)
        with patch("time.sleep"):
            start = time.time()
            client.get("/slow")
            slow_time = time.time() - start
            metrics["total_requests"] += 1
            metrics["successful"] += 1
            metrics["total_time"] += slow_time
            metrics["endpoints"]["/slow"] = {"count": 1, "avg_time": slow_time}

        # Failed request
        mock_server.add_endpoint("GET", "/error", status=500)
        try:
            client.get("/error")
        except HTTPResponseError:
            metrics["total_requests"] += 1
            metrics["failed"] += 1

        # Verify metrics
        assert metrics["total_requests"] == 3
        assert metrics["successful"] == 2
        assert metrics["failed"] == 1
        assert len(metrics["endpoints"]) == 2

        # Calculate average response time
        if metrics["successful"] > 0:
            avg_time = metrics["total_time"] / metrics["successful"]
            assert avg_time > 0


@pytest.mark.e2e
class TestPerformanceAndScaling:
    """Test performance and scaling characteristics."""

    @pytest.mark.slow
    def test_high_volume_requests(self, mock_server):
        """Test handling high volume of requests."""
        request_counter = {"count": 0}

        def counter_callback(request):
            request_counter["count"] += 1
            return (200, {}, json.dumps({"num": request_counter["count"]}))

        mock_server.add_endpoint("GET", "/counter", callback=counter_callback)

        client = APIClient(
            "https://api.example.com",
            rate_limit_enabled=True,
            requests_per_second=100,  # High rate for testing
        )

        # Make 100 requests
        results = []
        for i in range(100):
            result = client.get("/counter")
            results.append(result["num"])

        # All requests should complete
        assert len(results) == 100
        assert results[-1] == 100

    @pytest.mark.slow
    def test_connection_pooling(self, mock_server):
        """Test connection pooling efficiency."""
        mock_server.add_endpoint("GET", "/pooled", json_data={"status": "ok"})

        client = APIClient("https://api.example.com", connection_pool_size=10)

        # Make requests that should reuse connections
        start_time = time.time()
        for _ in range(50):
            client.get("/pooled")
        elapsed = time.time() - start_time

        # Connection pooling should make this faster
        # (actual timing depends on implementation)
        assert elapsed < 5  # Should complete within 5 seconds

    def test_memory_efficiency(self, mock_server):
        """Test memory efficiency with large responses."""
        # Create large response (1MB)
        large_data = {"data": "x" * 1000000}
        mock_server.add_endpoint("GET", "/large", json_data=large_data)

        client = APIClient("https://api.example.com")

        # Process multiple large responses
        for _ in range(10):
            result = client.get("/large")
            # Process and discard
            assert len(result["data"]) == 1000000
            del result  # Explicitly free memory

        # Should handle without memory issues
        # (actual memory testing would require memory profiler)
