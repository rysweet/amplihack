"""Rate limiting tests for RESTClient - Testing time-based rate limiting.

Tests verify that the client properly enforces request rate limits.
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import RESTClient


class TestRateLimiting(unittest.TestCase):
    """Test rate limiting functionality."""

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_basic_rate_limiting(self, mock_sleep, mock_urlopen):
        """Test that rate limiting delays requests appropriately."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Create client with 2 requests per second limit
        client = RESTClient(base_url="https://api.example.com", requests_per_second=2.0)

        # Make 3 rapid requests
        client.get("/test1")
        client.get("/test2")
        client.get("/test3")

        # First two should go through without delay
        # Third should be delayed by ~0.5 seconds
        self.assertTrue(mock_sleep.called)

    @patch("urllib.request.urlopen")
    def test_requests_per_second_timing(self, mock_urlopen):
        """Test that actual request timing matches rate limit."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Client with 5 requests per second (0.2 seconds between requests)
        client = RESTClient(base_url="https://api.example.com", requests_per_second=5.0)

        start_time = time.time()

        # Make 5 requests - should take approximately 0.8 seconds
        for i in range(5):
            client.get(f"/test{i}")

        elapsed = time.time() - start_time

        # Should take at least 0.8 seconds (4 intervals of 0.2 seconds)
        # But less than 1.2 seconds (accounting for execution time)
        self.assertGreaterEqual(elapsed, 0.8)
        self.assertLess(elapsed, 1.2)

    @patch("urllib.request.urlopen")
    def test_no_rate_limit_when_disabled(self, mock_urlopen):
        """Test that setting requests_per_second=None disables rate limiting."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = RESTClient(base_url="https://api.example.com", requests_per_second=None)

        start_time = time.time()

        # Make 10 rapid requests - should complete very quickly
        for i in range(10):
            client.get(f"/test{i}")

        elapsed = time.time() - start_time

        # Should complete in less than 0.5 seconds (no rate limiting)
        self.assertLess(elapsed, 0.5)

    @patch("urllib.request.urlopen")
    def test_rate_limit_with_different_methods(self, mock_urlopen):
        """Test that rate limiting applies to all HTTP methods."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = RESTClient(
            base_url="https://api.example.com",
            requests_per_second=3.0,  # 3 req/sec = ~0.33 seconds between requests
        )

        start_time = time.time()

        # Mix of different HTTP methods
        client.get("/resource")
        client.post("/resource", json={"data": "test"})
        client.put("/resource/1", json={"update": "data"})
        client.delete("/resource/1")
        client.patch("/resource/1", json={"patch": "data"})

        elapsed = time.time() - start_time

        # 5 requests with 3 req/sec should take at least 1.33 seconds
        self.assertGreaterEqual(elapsed, 1.3)

    @patch("urllib.request.urlopen")
    def test_rate_limit_thread_safety(self, mock_urlopen):
        """Test that rate limiting works correctly with concurrent threads."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = RESTClient(
            base_url="https://api.example.com",
            requests_per_second=2.0,  # 2 req/sec
        )

        request_times = []
        lock = threading.Lock()

        def make_request(thread_id):
            """Make a request and record the time."""
            response = client.get(f"/test{thread_id}")
            with lock:
                request_times.append(time.time())

        # Start 4 threads simultaneously
        threads = []
        start_time = time.time()

        for i in range(4):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # With 2 req/sec, 4 requests should take at least 1.5 seconds
        elapsed = time.time() - start_time
        self.assertGreaterEqual(elapsed, 1.5)

        # Verify request spacing
        request_times.sort()
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i - 1]
            # Each request should be at least 0.45 seconds apart (allowing some margin)
            self.assertGreaterEqual(time_diff, 0.45)

    @patch("urllib.request.urlopen")
    def test_rate_limit_reset_after_pause(self, mock_urlopen):
        """Test that rate limiting resets properly after a pause."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = RESTClient(
            base_url="https://api.example.com",
            requests_per_second=10.0,  # 10 req/sec = 0.1 sec between requests
        )

        # Make 2 quick requests
        client.get("/test1")
        client.get("/test2")

        # Pause for more than the rate limit interval
        time.sleep(0.5)

        # Next request should go through immediately (no delay)
        start_time = time.time()
        client.get("/test3")
        elapsed = time.time() - start_time

        # Should complete quickly (no rate limit delay after pause)
        self.assertLess(elapsed, 0.05)

    @patch("urllib.request.urlopen")
    def test_fractional_requests_per_second(self, mock_urlopen):
        """Test rate limiting with fractional requests per second (e.g., 0.5 req/sec)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # 0.5 requests per second = 2 seconds between requests
        client = RESTClient(base_url="https://api.example.com", requests_per_second=0.5)

        start_time = time.time()

        # Make 3 requests
        client.get("/test1")
        client.get("/test2")
        client.get("/test3")

        elapsed = time.time() - start_time

        # Should take at least 4 seconds (2 intervals of 2 seconds each)
        self.assertGreaterEqual(elapsed, 4.0)

    def test_rate_limit_calculation(self):
        """Test the internal calculation of rate limit delays."""
        client = RESTClient(base_url="https://api.example.com", requests_per_second=4.0)

        # Test that the delay calculation is correct
        # 4 requests per second = 0.25 seconds between requests
        expected_delay = 0.25

        # This assumes the client has a method to calculate delay
        # or we can infer it from the behavior
        self.assertAlmostEqual(1.0 / client.requests_per_second, expected_delay)


class TestRateLimitingEdgeCases(unittest.TestCase):
    """Test edge cases in rate limiting."""

    def test_very_high_rate_limit(self):
        """Test with very high rate limit (effectively no limiting)."""
        client = RESTClient(
            base_url="https://api.example.com",
            requests_per_second=1000.0,  # 1000 req/sec
        )

        # Should work without issues
        self.assertEqual(client.requests_per_second, 1000.0)

    def test_very_low_rate_limit(self):
        """Test with very low rate limit."""
        client = RESTClient(
            base_url="https://api.example.com",
            requests_per_second=0.1,  # 1 request per 10 seconds
        )

        self.assertEqual(client.requests_per_second, 0.1)

    def test_zero_rate_limit_raises_error(self):
        """Test that zero rate limit raises an appropriate error."""
        with self.assertRaises(ValueError):
            RESTClient(base_url="https://api.example.com", requests_per_second=0.0)

    def test_negative_rate_limit_raises_error(self):
        """Test that negative rate limit raises an appropriate error."""
        with self.assertRaises(ValueError):
            RESTClient(base_url="https://api.example.com", requests_per_second=-1.0)


if __name__ == "__main__":
    unittest.main()
