"""Integration tests for RESTClient - Testing with mock server (30% of test coverage).

These tests verify the client works correctly with a real HTTP server,
testing multiple components working together.
"""

import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import RESTClient

from tests.mock_server import FlakeyMockServer, MockHTTPServer, RateLimitingMockServer


class TestClientServerIntegration(unittest.TestCase):
    """Test REST client with mock HTTP server."""

    @classmethod
    def setUpClass(cls):
        """Start mock server for all tests."""
        cls.server = MockHTTPServer(port=0)  # Random port
        cls.port = cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        """Stop mock server after all tests."""
        cls.server.stop()

    def setUp(self):
        """Reset server state before each test."""
        self.server.reset()

    def test_get_request_integration(self):
        """Test GET request with real server."""
        client = RESTClient(base_url=self.base_url)

        response = client.get("/users")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("users", data)

        # Verify server received the request
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["method"], "GET")
        self.assertEqual(requests[0]["path"], "/users")

    def test_post_with_json_body(self):
        """Test POST request with JSON body."""
        client = RESTClient(base_url=self.base_url)

        user_data = {"name": "John Doe", "email": "john@example.com"}
        response = client.post("/users", json=user_data)

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["id"], 123)

        # Verify server received correct data
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["method"], "POST")
        self.assertEqual(requests[0]["body"], user_data)

    def test_custom_headers_integration(self):
        """Test that custom headers are sent correctly."""
        client = RESTClient(base_url=self.base_url, headers={"Authorization": "Bearer token123"})

        client.get("/protected")

        requests = self.server.get_requests()
        self.assertEqual(len(requests), 1)
        self.assertIn("Authorization", requests[0]["headers"])
        self.assertEqual(requests[0]["headers"]["Authorization"], "Bearer token123")

    def test_query_parameters_integration(self):
        """Test query parameters are sent correctly."""
        client = RESTClient(base_url=self.base_url)

        params = {"page": "2", "limit": "10", "sort": "name"}
        client.get("/items", params=params)

        requests = self.server.get_requests()
        self.assertEqual(len(requests), 1)

        # Query params should be parsed correctly
        query_params = requests[0]["query_params"]
        self.assertEqual(query_params["page"], ["2"])
        self.assertEqual(query_params["limit"], ["10"])
        self.assertEqual(query_params["sort"], ["name"])

    def test_multiple_requests_sequence(self):
        """Test sequence of multiple requests."""
        client = RESTClient(base_url=self.base_url)

        # Create, update, get, delete sequence
        create_response = client.post("/items", json={"name": "item1"})
        self.assertEqual(create_response.status_code, 201)

        update_response = client.put("/items/1", json={"name": "updated"})
        self.assertEqual(update_response.status_code, 200)

        get_response = client.get("/items/1")
        self.assertEqual(get_response.status_code, 200)

        delete_response = client.delete("/items/1")
        self.assertEqual(delete_response.status_code, 204)

        # Verify all requests were received in order
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[0]["method"], "POST")
        self.assertEqual(requests[1]["method"], "PUT")
        self.assertEqual(requests[2]["method"], "GET")
        self.assertEqual(requests[3]["method"], "DELETE")

    def test_error_status_codes(self):
        """Test handling of error status codes from server."""
        client = RESTClient(base_url=self.base_url, max_retries=0)

        # Test 404 response
        response = client.get("/status/404")
        self.assertEqual(response.status_code, 404)

        # Test 500 response (no retry since max_retries=0)
        response = client.get("/status/500")
        self.assertEqual(response.status_code, 500)

    def test_concurrent_requests(self):
        """Test multiple concurrent requests."""
        client = RESTClient(base_url=self.base_url)

        results = []
        lock = threading.Lock()

        def make_request(path):
            response = client.get(path)
            with lock:
                results.append((path, response.status_code))

        # Start multiple threads
        threads = []
        paths = ["/test1", "/test2", "/test3", "/test4", "/test5"]

        for path in paths:
            thread = threading.Thread(target=make_request, args=(path,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all requests completed
        self.assertEqual(len(results), 5)
        for path, status in results:
            self.assertEqual(status, 200)

        # Verify server received all requests
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 5)

    def test_timeout_handling(self):
        """Test timeout with slow server response."""
        client = RESTClient(
            base_url=self.base_url,
            timeout=1,  # 1 second timeout
            max_retries=0,
        )

        # This endpoint sleeps for 2 seconds
        with self.assertRaises(Exception):  # Should timeout
            client.get("/slow")


class TestRateLimitingIntegration(unittest.TestCase):
    """Test rate limiting with mock server."""

    @classmethod
    def setUpClass(cls):
        """Start rate limiting mock server."""
        cls.server = RateLimitingMockServer(port=0, rate_limit=3)
        cls.port = cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        """Stop mock server."""
        cls.server.stop()

    def setUp(self):
        """Reset server state."""
        self.server.reset()

    def test_rate_limiting_prevents_429(self):
        """Test that client rate limiting prevents 429 errors."""
        # Client with rate limit slightly below server limit
        client = RESTClient(
            base_url=self.base_url,
            requests_per_second=2.5,  # Below server's 3 req/sec
            max_retries=0,
        )

        # Make 6 requests - should all succeed with rate limiting
        responses = []
        for i in range(6):
            response = client.get(f"/test{i}")
            responses.append(response.status_code)

        # All should be 200 (no 429 errors)
        for status in responses:
            self.assertEqual(status, 200)

    def test_no_rate_limiting_triggers_429(self):
        """Test that without rate limiting, server returns 429."""
        # Client without rate limiting
        client = RESTClient(
            base_url=self.base_url,
            requests_per_second=None,  # No rate limiting
            max_retries=0,
        )

        # Make rapid requests
        responses = []
        for i in range(5):
            try:
                response = client.get(f"/test{i}")
                responses.append(response.status_code)
            except Exception:
                responses.append(429)

        # Should have some 429 responses
        self.assertIn(429, responses)


class TestRetryIntegration(unittest.TestCase):
    """Test retry logic with flakey server."""

    @classmethod
    def setUpClass(cls):
        """Start flakey mock server."""
        # Pattern: fail, fail, success
        cls.server = FlakeyMockServer(port=0, failure_pattern=[True, True, False])
        cls.port = cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        """Stop mock server."""
        cls.server.stop()

    def test_retry_on_connection_failure(self):
        """Test that client retries on connection failures."""
        client = RESTClient(base_url=self.base_url, max_retries=3)

        # First two attempts will fail, third will succeed
        response = client.get("/test")

        # Should eventually succeed
        self.assertEqual(response.status_code, 200)

    def test_insufficient_retries_fails(self):
        """Test that insufficient retries leads to failure."""
        client = RESTClient(
            base_url=self.base_url,
            max_retries=1,  # Only 1 retry (needs 2 to succeed)
        )

        # Will fail after 2 attempts (initial + 1 retry)
        with self.assertRaises(Exception):
            client.get("/test")


class TestEndToEndWorkflows(unittest.TestCase):
    """End-to-end test scenarios (10% of test coverage)."""

    @classmethod
    def setUpClass(cls):
        """Start mock server."""
        cls.server = MockHTTPServer(port=0)
        cls.port = cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        """Stop mock server."""
        cls.server.stop()

    def setUp(self):
        """Reset server state."""
        self.server.reset()

    def test_crud_workflow(self):
        """Test complete CRUD workflow."""
        client = RESTClient(
            base_url=self.base_url,
            headers={"API-Key": "test-key"},
            requests_per_second=10,
            max_retries=2,
        )

        # Create resource
        create_data = {"name": "Test Resource", "type": "example"}
        create_response = client.post("/resources", json=create_data)
        self.assertEqual(create_response.status_code, 201)
        resource_id = create_response.json().get("id", 1)

        # Read resource
        get_response = client.get(f"/resources/{resource_id}")
        self.assertEqual(get_response.status_code, 200)

        # Update resource
        update_data = {"name": "Updated Resource"}
        update_response = client.put(f"/resources/{resource_id}", json=update_data)
        self.assertEqual(update_response.status_code, 200)

        # Partial update
        patch_data = {"description": "Added description"}
        patch_response = client.patch(f"/resources/{resource_id}", json=patch_data)
        self.assertEqual(patch_response.status_code, 200)

        # Delete resource
        delete_response = client.delete(f"/resources/{resource_id}")
        self.assertEqual(delete_response.status_code, 204)

        # Verify all requests were made
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 5)

    def test_pagination_workflow(self):
        """Test paginated data retrieval workflow."""
        client = RESTClient(base_url=self.base_url)

        # Queue responses for pagination
        self.server.queue_response(
            {
                "status": 200,
                "body": {"items": [{"id": i} for i in range(10)], "next_page": 2, "total": 25},
            }
        )
        self.server.queue_response(
            {
                "status": 200,
                "body": {"items": [{"id": i} for i in range(10, 20)], "next_page": 3, "total": 25},
            }
        )
        self.server.queue_response(
            {
                "status": 200,
                "body": {
                    "items": [{"id": i} for i in range(20, 25)],
                    "next_page": None,
                    "total": 25,
                },
            }
        )

        # Retrieve all pages
        all_items = []
        page = 1

        while page:
            response = client.get("/items", params={"page": str(page)})
            self.assertEqual(response.status_code, 200)

            data = response.json()
            all_items.extend(data["items"])
            page = data.get("next_page")

        # Verify we got all items
        self.assertEqual(len(all_items), 25)

    def test_authentication_workflow(self):
        """Test authentication and token refresh workflow."""
        client = RESTClient(base_url=self.base_url)

        # Login to get token
        self.server.queue_response(
            {"status": 200, "body": {"token": "auth-token-123", "expires_in": 3600}}
        )

        login_response = client.post("/auth/login", json={"username": "test", "password": "pass"})
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["token"]

        # Use token for authenticated request
        client.headers = {"Authorization": f"Bearer {token}"}

        self.server.queue_response(
            {"status": 200, "body": {"user": {"id": 1, "name": "Test User"}}}
        )

        profile_response = client.get("/user/profile")
        self.assertEqual(profile_response.status_code, 200)

        # Verify token was sent
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[1]["headers"]["Authorization"], f"Bearer {token}")

    def test_batch_processing_workflow(self):
        """Test batch processing with rate limiting and retry."""
        client = RESTClient(
            base_url=self.base_url,
            requests_per_second=5,  # Rate limited
            max_retries=2,
        )

        # Process batch of items
        batch_items = [{"id": i, "data": f"item_{i}"} for i in range(10)]

        results = []
        for item in batch_items:
            # Queue success response for each item
            self.server.queue_response(
                {"status": 200, "body": {"processed": True, "id": item["id"]}}
            )

            response = client.post("/process", json=item)
            if response.status_code == 200:
                results.append(response.json())

        # Verify all items processed
        self.assertEqual(len(results), 10)
        for i, result in enumerate(results):
            self.assertTrue(result["processed"])
            self.assertEqual(result["id"], i)

        # Verify rate limiting was applied (requests should be spaced)
        requests = self.server.get_requests()
        self.assertEqual(len(requests), 10)

        # Check timing between requests
        timestamps = [req["timestamp"] for req in requests]
        for i in range(1, len(timestamps)):
            time_diff = timestamps[i] - timestamps[i - 1]
            # With 5 req/sec, minimum spacing should be ~0.2 seconds
            self.assertGreaterEqual(time_diff, 0.15)  # Allow some margin


if __name__ == "__main__":
    unittest.main()
