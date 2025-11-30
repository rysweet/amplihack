"""
Thread safety tests for API Client.

These tests verify that the API Client can be safely used from multiple threads
concurrently without data corruption or race conditions.
"""

import concurrent.futures
import json
import queue
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Import our API client (will fail initially in TDD)
try:
    from api_client import APIClient, ClientConfig
except ImportError:
    APIClient = None
    ClientConfig = None


class TestThreadSafety(unittest.TestCase):
    """Comprehensive thread safety tests."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(
                base_url="https://api.example.com", disable_ssrf_protection=True
            )
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_concurrent_get_requests(self, mock_urlopen):
        """Test multiple threads making GET requests concurrently."""
        num_threads = 20
        requests_per_thread = 5

        def create_response(thread_id, request_id):
            inner_response = MagicMock()
            inner_response.status = 200
            inner_response.read.return_value = json.dumps(
                {"thread_id": thread_id, "request_id": request_id}
            ).encode()
            inner_response.headers = MagicMock()
            inner_response.headers.items.return_value = []

            # Create context manager
            ctx_manager = MagicMock()
            ctx_manager.__enter__.return_value = inner_response
            ctx_manager.__exit__.return_value = None
            return ctx_manager

        # Prepare responses for all requests
        responses = []
        for t in range(num_threads):
            for r in range(requests_per_thread):
                responses.append(create_response(t, r))

        mock_urlopen.side_effect = responses

        results = queue.Queue()
        errors = queue.Queue()

        def worker(thread_id):
            """Worker function for each thread."""
            try:
                thread_results = []
                for request_id in range(requests_per_thread):
                    response = self.client.get(f"/test/{thread_id}/{request_id}")
                    data = response.json()
                    thread_results.append(data)
                results.put((thread_id, thread_results))
            except Exception as e:
                errors.put((thread_id, str(e)))

        # Start all threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=10)

        # Check results
        error_list = []
        while not errors.empty():
            error_list.append(errors.get())
        if error_list:
            print(f"Thread errors: {error_list}")
        self.assertEqual(len(error_list), 0, "No errors should occur")
        self.assertEqual(results.qsize(), num_threads, "All threads should complete")

        # Verify all requests were made
        total_calls = num_threads * requests_per_thread
        self.assertEqual(mock_urlopen.call_count, total_calls)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_mixed_http_methods_concurrent(self, mock_urlopen):
        """Test different HTTP methods used concurrently."""

        def create_response(method, id):
            inner_response = MagicMock()
            inner_response.status = 200 if method != "DELETE" else 204
            inner_response.read.return_value = (
                json.dumps({"method": method, "id": id}).encode() if method != "DELETE" else b""
            )
            inner_response.headers = MagicMock()
            inner_response.headers.items.return_value = []

            # Create context manager
            ctx_manager = MagicMock()
            ctx_manager.__enter__.return_value = inner_response
            ctx_manager.__exit__.return_value = None
            return ctx_manager

        # Prepare mixed responses
        responses = []
        for i in range(40):  # 10 of each method
            if i < 10:
                responses.append(create_response("GET", i))
            elif i < 20:
                responses.append(create_response("POST", i))
            elif i < 30:
                responses.append(create_response("PUT", i))
            else:
                responses.append(create_response("DELETE", i))

        mock_urlopen.side_effect = responses

        results = []
        lock = threading.Lock()

        def make_requests(method, start_id):
            """Make requests with specified method."""
            for i in range(10):
                try:
                    if method == "GET":
                        response = self.client.get(f"/resource/{start_id + i}")
                    elif method == "POST":
                        response = self.client.post("/resource", json={"id": start_id + i})
                    elif method == "PUT":
                        response = self.client.put(
                            f"/resource/{start_id + i}", json={"updated": True}
                        )
                    elif method == "DELETE":
                        response = self.client.delete(f"/resource/{start_id + i}")

                    with lock:
                        results.append((method, response.status_code))
                except Exception as e:
                    with lock:
                        results.append((method, f"Error: {e}"))

        # Start threads for each method
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(make_requests, "GET", 0),
                executor.submit(make_requests, "POST", 10),
                executor.submit(make_requests, "PUT", 20),
                executor.submit(make_requests, "DELETE", 30),
            ]
            concurrent.futures.wait(futures, timeout=10)

        # Verify results
        self.assertEqual(len(results), 40)

        # Check that each method was called correctly
        get_results = [r for r in results if r[0] == "GET"]
        post_results = [r for r in results if r[0] == "POST"]
        put_results = [r for r in results if r[0] == "PUT"]
        delete_results = [r for r in results if r[0] == "DELETE"]

        self.assertEqual(len(get_results), 10)
        self.assertEqual(len(post_results), 10)
        self.assertEqual(len(put_results), 10)
        self.assertEqual(len(delete_results), 10)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    def test_rate_limiter_thread_safety(self):
        """Test that rate limiter works correctly with multiple threads."""
        config = ClientConfig(base_url="https://api.example.com", disable_ssrf_protection=True)
        client = APIClient(config)

        # Track request times
        request_times = []
        lock = threading.Lock()

        @patch("urllib.request.urlopen")
        def make_request(mock_urlopen):
            """Make a single request and record time."""
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b"{}"
            mock_response.headers = {}
            mock_urlopen.return_value.__enter__.return_value = mock_response

            client.get("/test")

            with lock:
                request_times.append(time.time())

        # Make 20 requests from 10 threads
        num_threads = 10
        requests_per_thread = 2

        def worker():
            for _ in range(requests_per_thread):
                make_request()

        threads = []
        start_time = time.time()

        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        total_time = time.time() - start_time

        # With 10 req/s rate limit, 20 requests should take ~2 seconds
        self.assertGreaterEqual(total_time, 1.8)
        self.assertLess(total_time, 3.0)

        # Verify requests are properly spaced
        request_times.sort()
        for i in range(1, len(request_times)):
            interval = request_times[i] - request_times[i - 1]
            # Each interval should be at least 90ms (allowing some margin)
            self.assertGreaterEqual(interval, 0.09)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_shared_client_state_isolation(self, mock_urlopen):
        """Test that shared client maintains proper state isolation."""

        def create_response(header_value):
            response = MagicMock()
            response.status = 200
            response.read.return_value = json.dumps({"received_header": header_value}).encode()
            response.headers = MagicMock()
            response.headers.items.return_value = []

            # Create context manager
            ctx_manager = MagicMock()
            ctx_manager.__enter__.return_value = response
            ctx_manager.__exit__.return_value = None
            return ctx_manager

        # Each thread will use different headers
        num_threads = 10
        responses = [create_response(f"thread-{i}") for i in range(num_threads)]
        mock_urlopen.side_effect = responses

        results = {}
        errors = []

        def worker(thread_id):
            """Each thread uses unique headers."""
            try:
                headers = {"X-Thread-ID": f"thread-{thread_id}"}
                response = self.client.get("/test", headers=headers)
                results[thread_id] = response.json()
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        # Verify no errors and all threads completed
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), num_threads)

        # Verify each thread's headers were properly isolated
        for i in range(num_threads):
            self.assertIn(i, results)
            self.assertEqual(results[i]["received_header"], f"thread-{i}")

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_error_handling_thread_safety(self, mock_urlopen):
        """Test that error handling is thread-safe."""

        # Mix of success and failure responses
        def create_response(i):
            if i % 3 == 0:
                # Return error for every 3rd request
                from io import BytesIO
                from urllib.error import HTTPError

                raise HTTPError(
                    f"https://api.example.com/test/{i}",
                    500,
                    "Server Error",
                    {},
                    BytesIO(b'{"error": "Server error"}'),
                )
            response = MagicMock()
            response.status = 200
            response.read.return_value = json.dumps({"id": i}).encode()
            response.headers = {}
            return response.__enter__.return_value

        num_requests = 30
        responses = []
        for i in range(num_requests):
            if i % 3 == 0:
                responses.append(create_response(i))
            else:
                responses.append(create_response(i))

        mock_urlopen.side_effect = responses

        success_count = threading.local()
        error_count = threading.local()

        def init_counts():
            success_count.value = 0
            error_count.value = 0

        def worker(start, end):
            """Worker that handles both success and errors."""
            init_counts()

            for i in range(start, end):
                try:
                    response = self.client.get(f"/test/{i}")
                    if response.status_code == 200:
                        success_count.value += 1
                except Exception:
                    error_count.value += 1

            return success_count.value, error_count.value

        # Run workers in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                start = i * 6
                end = start + 6
                futures.append(executor.submit(worker, start, end))

            results = [f.result(timeout=10) for f in futures]

        # Count total successes and errors
        total_success = sum(r[0] for r in results)
        total_errors = sum(r[1] for r in results)

        # Every 3rd request should fail
        expected_errors = num_requests // 3
        expected_success = num_requests - expected_errors

        self.assertEqual(total_success, expected_success)
        self.assertEqual(total_errors, expected_errors)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_connection_pool_safety(self, mock_urlopen):
        """Test that connection handling is thread-safe."""
        # Test that the client properly handles connection pooling
        # when multiple threads are making requests

        def test_connections():
            connections_in_use = threading.local()
            max_concurrent = [0]
            lock = threading.Lock()

            def track_connection():
                with lock:
                    current = getattr(connections_in_use, "count", 0)
                    connections_in_use.count = current + 1
                    max_concurrent[0] = max(max_concurrent[0], connections_in_use.count)

            def release_connection():
                with lock:
                    connections_in_use.count -= 1

            def create_response():
                track_connection()
                time.sleep(0.01)  # Simulate network delay
                inner_response = MagicMock()
                inner_response.status = 200
                inner_response.read.return_value = b"{}"
                inner_response.headers = MagicMock()
                inner_response.headers.items.return_value = []
                release_connection()

                # Create context manager
                ctx_manager = MagicMock()
                ctx_manager.__enter__.return_value = inner_response
                ctx_manager.__exit__.return_value = None
                return ctx_manager

            mock_urlopen.side_effect = [create_response() for _ in range(50)]

            # Make many concurrent requests
            def make_requests():
                for _ in range(10):
                    self.client.get("/test")

            threads = []
            for _ in range(5):
                t = threading.Thread(target=make_requests)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=10)

            # Verify connections were properly managed
            self.assertGreater(max_concurrent[0], 1, "Should use multiple connections")
            self.assertEqual(
                getattr(connections_in_use, "count", 0), 0, "All connections should be released"
            )

        test_connections()


class TestRaceConditions(unittest.TestCase):
    """Tests for specific race condition scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        if ClientConfig and APIClient:
            self.config = ClientConfig(
                base_url="https://api.example.com", disable_ssrf_protection=True
            )
            self.client = APIClient(self.config)

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_rapid_fire_requests(self, mock_urlopen):
        """Test rapid-fire requests from multiple threads."""

        # Create responses with unique IDs
        responses = []
        for i in range(100):
            inner_response = MagicMock()
            inner_response.status = 200
            inner_response.read.return_value = json.dumps({"id": i}).encode()
            inner_response.headers = MagicMock()
            inner_response.headers.items.return_value = []

            # Create context manager
            ctx_manager = MagicMock()
            ctx_manager.__enter__.return_value = inner_response
            ctx_manager.__exit__.return_value = None
            responses.append(ctx_manager)

        mock_urlopen.side_effect = responses

        received_ids = []
        lock = threading.Lock()

        def rapid_requests():
            """Make requests as fast as possible."""
            for _ in range(10):
                response = self.client.get("/rapid")
                data = response.json()
                with lock:
                    received_ids.append(data["id"])

        # Start 10 threads making rapid requests
        threads = []
        for _ in range(10):
            t = threading.Thread(target=rapid_requests)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Verify all requests completed and got unique IDs
        self.assertEqual(len(received_ids), 100)
        self.assertEqual(len(set(received_ids)), 100)  # All unique

    @unittest.skipIf(APIClient is None, "APIClient not implemented yet")
    @patch("urllib.request.urlopen")
    def test_interleaved_retry_scenarios(self, mock_urlopen):
        """Test that retries from different threads don't interfere."""

        # Create a mix of failing and succeeding responses
        from io import BytesIO
        from urllib.error import HTTPError

        def create_responses_for_thread(thread_id):
            """Create response sequence for a thread (2 failures, then success)."""
            responses = []

            # Two 500 errors
            for i in range(2):
                error = HTTPError(
                    f"https://api.example.com/thread/{thread_id}",
                    500,
                    "Server Error",
                    {},
                    BytesIO(json.dumps({"thread": thread_id, "attempt": i}).encode()),
                )
                responses.append(error)

            # Then success
            success = MagicMock()
            success.status = 200
            success.read.return_value = json.dumps({"thread": thread_id, "success": True}).encode()
            success.headers = {}
            responses.append(success.__enter__.return_value)

            return responses

        # Prepare responses for 5 threads
        all_responses = []
        for thread_id in range(5):
            all_responses.extend(create_responses_for_thread(thread_id))

        mock_urlopen.side_effect = all_responses

        results = {}
        errors = {}

        @patch("time.sleep")  # Mock sleep to speed up test
        def worker(thread_id, mock_sleep):
            """Worker that experiences retries."""
            try:
                response = self.client.get(f"/thread/{thread_id}")
                results[thread_id] = response.json()
            except Exception as e:
                errors[thread_id] = str(e)

        # Start all threads simultaneously
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        # All threads should eventually succeed
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

        # Verify each thread got its correct response
        for thread_id in range(5):
            self.assertEqual(results[thread_id]["thread"], thread_id)
            self.assertTrue(results[thread_id]["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
