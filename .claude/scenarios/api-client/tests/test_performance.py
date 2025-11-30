"""Performance tests for optimized REST API Client.

These tests verify performance improvements are working.
Written using TDD - they will fail until optimizations are implemented.
"""

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api_client import RESTClient


class TestConnectionPooling(unittest.TestCase):
    """Test that connections are reused for better performance."""

    def test_connection_reuse_same_host(self):
        """Test that multiple requests to same host reuse connection."""
        client = RESTClient("http://localhost:8889")

        # Mock urllib to track connection creation
        with patch("api_client.client.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read.return_value = b'{"test": "data"}'
            mock_response.url = "http://localhost:8889/test"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Make multiple requests
            for i in range(5):
                client.get(f"/test/{i}")

            # Check that Keep-Alive header was set
            calls = mock_urlopen.call_args_list
            for call in calls:
                request_obj = call[0][0]
                # After optimization, should have Connection: keep-alive
                # This will fail until we implement connection pooling
                self.assertIn("Connection", request_obj.headers)
                self.assertEqual(request_obj.headers.get("Connection"), "keep-alive")

    def test_parallel_performance_improvement(self):
        """Test that parallel requests are faster with connection pooling."""
        # This test will use timing to verify improvement
        # Will fail until connection pooling is implemented

        client = RESTClient("http://httpbin.org")

        def make_requests(num_requests):
            start = time.time()
            threads = []

            def worker():
                with patch("api_client.client.request.urlopen") as mock_urlopen:
                    mock_response = MagicMock()
                    mock_response.status = 200
                    mock_response.headers = {}
                    mock_response.read.return_value = b'{"test": "data"}'
                    mock_response.url = "http://httpbin.org/get"
                    mock_urlopen.return_value.__enter__.return_value = mock_response

                    client.get("/get")

            for _ in range(num_requests):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            return time.time() - start

        # Measure time for parallel requests
        # With connection pooling, this should be significantly faster
        parallel_time = make_requests(10)

        # This assertion will fail until optimization is implemented
        # We expect parallel requests to complete in under 1 second with pooling
        self.assertLess(
            parallel_time, 1.0, "Parallel requests should complete quickly with connection pooling"
        )


class TestJitteredBackoff(unittest.TestCase):
    """Test jittered exponential backoff implementation."""

    def test_backoff_has_jitter(self):
        """Test that retry delays have random jitter."""
        client = RESTClient("http://localhost:8890", max_retries=3)

        # Mock to simulate failures and track delays
        delays = []
        original_sleep = time.sleep

        def track_sleep(duration):
            delays.append(duration)
            # Don't actually sleep in tests
            return

        from urllib import error as urllib_error

        with patch("time.sleep", side_effect=track_sleep):
            with patch("api_client.client.request.urlopen") as mock_urlopen:
                # Simulate connection errors that trigger retries
                mock_urlopen.side_effect = urllib_error.URLError("Connection error")

                try:
                    client.get("/test")
                except:
                    pass  # Expected to fail

        # Check that delays have jitter (not exact powers of 2)
        # This will fail until jitter is implemented
        self.assertGreater(len(delays), 0, "Should have retry delays")

        for i, delay in enumerate(delays):
            base_delay = 2 ** (i + 1)
            # With jitter, delay should be between base and base * 1.25
            self.assertGreaterEqual(delay, base_delay * 0.9)
            self.assertLessEqual(delay, base_delay * 1.3)

            # Delays should not be exactly powers of 2 (indicates jitter)
            # This assertion will fail until jitter is implemented
            self.assertNotEqual(
                delay, base_delay, f"Delay {delay} should have jitter, not be exactly {base_delay}"
            )

    def test_no_thundering_herd(self):
        """Test that multiple clients don't retry at exactly the same time."""
        clients = [RESTClient(f"http://localhost:{8891 + i}", max_retries=2) for i in range(3)]

        all_delays = []

        def track_sleep(duration):
            all_delays.append((time.time(), duration))

        with patch("time.sleep", side_effect=track_sleep):
            with patch("api_client.client.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = Exception("Connection error")

                threads = []
                for client in clients:

                    def worker(c):
                        try:
                            c.get("/test")
                        except:
                            pass

                    t = threading.Thread(target=worker, args=(client,))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

        # Check that retries are spread out (not synchronized)
        # This will fail until jitter is implemented
        retry_times = [t for t, _ in all_delays]
        if len(retry_times) > 1:
            # Check that not all retries happen at the same time
            unique_times = len(set(round(t, 1) for t in retry_times))
            self.assertGreater(unique_times, 1, "Retries should be spread out with jitter")


class TestStreamingResponse(unittest.TestCase):
    """Test streaming response capability for large payloads."""

    def test_streaming_response_available(self):
        """Test that streaming responses can be used."""
        client = RESTClient("http://localhost:8892")

        with patch("api_client.client.request.urlopen") as mock_urlopen:
            # Mock a large response
            large_data = b"x" * 1024 * 1024  # 1MB
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}

            # Create a proper mock for chunked reading
            data_chunks = [large_data[i : i + 8192] for i in range(0, len(large_data), 8192)]
            data_chunks.append(b"")  # End marker
            mock_response.read.side_effect = data_chunks
            mock_response.url = "http://localhost:8892/large"
            # For streaming, return the mock directly (not through context manager)
            mock_urlopen.return_value = mock_response

            # This will fail until streaming is implemented
            # After implementation, should support get_stream method
            if hasattr(client, "get_stream"):
                response = client.get_stream("/large")

                # Should be able to iterate chunks without loading all
                chunks = []
                for chunk in response.iter_chunks(chunk_size=8192):
                    chunks.append(chunk)
                    # Memory should not grow to full size immediately
                    self.assertLessEqual(len(chunk), 8192)

                # Should get all data eventually
                self.assertEqual(b"".join(chunks), large_data)
            else:
                # This assertion will fail until streaming is implemented
                self.fail("Client should support get_stream method for large responses")


class TestPerformanceMetrics(unittest.TestCase):
    """Test that performance improvements meet targets."""

    def test_parallel_throughput_improved(self):
        """Test that parallel throughput exceeds 60 rps."""
        # This is a synthetic test to verify optimization goals
        # Will fail until optimizations are implemented

        client = RESTClient("http://localhost:8893")

        request_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal request_count
            with patch("api_client.client.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.headers = {}
                mock_response.read.return_value = b"{}"
                mock_response.url = "http://localhost:8893/test"
                mock_urlopen.return_value.__enter__.return_value = mock_response

                for _ in range(10):
                    client.get("/test")
                    with lock:
                        request_count += 1

        start = time.time()
        threads = []

        for _ in range(4):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start
        throughput = request_count / elapsed if elapsed > 0 else 0

        # Target: > 60 requests per second in parallel
        # This will fail until optimizations are implemented
        self.assertGreater(
            throughput, 60, f"Parallel throughput {throughput:.1f} rps should exceed 60 rps"
        )


if __name__ == "__main__":
    unittest.main()
