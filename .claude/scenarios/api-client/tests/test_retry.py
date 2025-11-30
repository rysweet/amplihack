"""Retry logic tests for RESTClient - Testing exponential backoff retry mechanism.

Tests verify that the client properly retries failed requests with exponential backoff.
Formula: delay = 2^attempt seconds (1s, 2s, 4s, 8s, etc.)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import RESTClient


class TestRetryLogic(unittest.TestCase):
    """Test exponential backoff retry functionality."""

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_connection_error(self, mock_sleep, mock_urlopen):
        """Test that connection errors trigger retries."""
        # Fail twice, then succeed
        mock_urlopen.side_effect = [
            URLError("Connection refused"),
            URLError("Connection refused"),
            MagicMock(
                status=200,
                headers={},
                read=MagicMock(return_value=b'{"success": true}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        response = client.get("/test")

        # Should have made 3 attempts
        self.assertEqual(mock_urlopen.call_count, 3)

        # Should have slept with exponential backoff: 2^1=2, 2^2=4
        expected_sleep_calls = [call(2), call(4)]
        mock_sleep.assert_has_calls(expected_sleep_calls)

        self.assertEqual(response.status_code, 200)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_timeout(self, mock_sleep, mock_urlopen):
        """Test that timeout errors trigger retries."""
        # Timeout once, then succeed
        mock_urlopen.side_effect = [
            TimeoutError("Connection timed out"),
            MagicMock(
                status=200,
                headers={},
                read=MagicMock(return_value=b'{"data": "test"}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(base_url="https://api.example.com", max_retries=3, timeout=5)

        response = client.get("/resource")

        # Should have made 2 attempts
        self.assertEqual(mock_urlopen.call_count, 2)

        # Should have slept once with delay of 2^1=2 seconds
        mock_sleep.assert_called_once_with(2)

        self.assertEqual(response.status_code, 200)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_5xx_errors(self, mock_sleep, mock_urlopen):
        """Test that 5xx server errors trigger retries."""
        # Return 503, 502, then 200
        mock_urlopen.side_effect = [
            HTTPError(
                url="https://api.example.com/test",
                code=503,
                msg="Service Unavailable",
                hdrs={},
                fp=None,
            ),
            HTTPError(
                url="https://api.example.com/test", code=502, msg="Bad Gateway", hdrs={}, fp=None
            ),
            MagicMock(
                status=200,
                headers={},
                read=MagicMock(return_value=b'{"status": "ok"}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        response = client.get("/test")

        # Should have made 3 attempts
        self.assertEqual(mock_urlopen.call_count, 3)

        # Should have exponential backoff delays
        expected_sleep_calls = [call(2), call(4)]
        mock_sleep.assert_has_calls(expected_sleep_calls)

        self.assertEqual(response.status_code, 200)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_no_retry_on_4xx_errors(self, mock_sleep, mock_urlopen):
        """Test that 4xx client errors do NOT trigger retries."""
        mock_urlopen.side_effect = HTTPError(
            url="https://api.example.com/test", code=404, msg="Not Found", hdrs={}, fp=None
        )

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        with self.assertRaises(HTTPError) as cm:
            client.get("/test")

        # Should have made only 1 attempt (no retry)
        self.assertEqual(mock_urlopen.call_count, 1)

        # Should not have slept
        mock_sleep.assert_not_called()

        # Verify it's a 404 error
        self.assertEqual(cm.exception.code, 404)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, mock_urlopen):
        """Test that retries stop after max_retries is reached."""
        # Always fail
        mock_urlopen.side_effect = URLError("Connection refused")

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        with self.assertRaises(URLError):
            client.get("/test")

        # Should have made exactly 4 attempts (initial + 3 retries)
        self.assertEqual(mock_urlopen.call_count, 4)

        # Should have slept 3 times with exponential backoff
        expected_sleep_calls = [call(2), call(4), call(8)]
        mock_sleep.assert_has_calls(expected_sleep_calls)

    @patch("urllib.request.urlopen")
    def test_no_retry_when_disabled(self, mock_urlopen):
        """Test that setting max_retries=0 disables retries."""
        mock_urlopen.side_effect = URLError("Connection refused")

        client = RESTClient(base_url="https://api.example.com", max_retries=0)

        with self.assertRaises(URLError):
            client.get("/test")

        # Should have made only 1 attempt
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_exponential_backoff_calculation(self, mock_sleep, mock_urlopen):
        """Test that exponential backoff follows the 2^attempt formula."""
        # Always fail to test all retry delays
        mock_urlopen.side_effect = URLError("Connection refused")

        client = RESTClient(base_url="https://api.example.com", max_retries=5)

        with self.assertRaises(URLError):
            client.get("/test")

        # Should have made 6 attempts (initial + 5 retries)
        self.assertEqual(mock_urlopen.call_count, 6)

        # Verify exponential backoff: 2^1, 2^2, 2^3, 2^4, 2^5
        expected_delays = [2, 4, 8, 16, 32]
        expected_sleep_calls = [call(delay) for delay in expected_delays]
        mock_sleep.assert_has_calls(expected_sleep_calls)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_with_different_http_methods(self, mock_sleep, mock_urlopen):
        """Test that retry logic works for all HTTP methods."""
        # Test POST with retry
        mock_urlopen.side_effect = [
            URLError("Connection refused"),
            MagicMock(
                status=201,
                headers={},
                read=MagicMock(return_value=b'{"id": 123}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        response = client.post("/users", json={"name": "test"})

        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(2)
        self.assertEqual(response.status_code, 201)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_specific_status_codes(self, mock_sleep, mock_urlopen):
        """Test retry on specific HTTP status codes (500, 502, 503, 504)."""
        test_cases = [
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
            (504, "Gateway Timeout"),
        ]

        for status_code, msg in test_cases:
            with self.subTest(status_code=status_code):
                mock_urlopen.reset_mock()
                mock_sleep.reset_mock()

                mock_urlopen.side_effect = [
                    HTTPError(
                        url="https://api.example.com/test",
                        code=status_code,
                        msg=msg,
                        hdrs={},
                        fp=None,
                    ),
                    MagicMock(
                        status=200,
                        headers={},
                        read=MagicMock(return_value=b'{"ok": true}'),
                        __enter__=lambda self: self,
                        __exit__=lambda self, *args: None,
                    ),
                ]

                client = RESTClient(base_url="https://api.example.com", max_retries=3)

                response = client.get("/test")

                self.assertEqual(mock_urlopen.call_count, 2)
                mock_sleep.assert_called_once_with(2)
                self.assertEqual(response.status_code, 200)


class TestRetryWithRateLimiting(unittest.TestCase):
    """Test interaction between retry and rate limiting."""

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_respects_rate_limiting(self, mock_sleep, mock_urlopen):
        """Test that retries still respect rate limiting."""
        # First request fails, retry succeeds
        mock_urlopen.side_effect = [
            URLError("Connection refused"),
            MagicMock(
                status=200,
                headers={},
                read=MagicMock(return_value=b'{"ok": true}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(
            base_url="https://api.example.com",
            max_retries=3,
            requests_per_second=2.0,  # Rate limiting enabled
        )

        response = client.get("/test")

        # Should have both retry delay and potential rate limit delays
        self.assertTrue(mock_sleep.called)
        self.assertEqual(response.status_code, 200)

    @patch("urllib.request.urlopen")
    def test_retry_count_per_request(self, mock_urlopen):
        """Test that retry count is per-request, not global."""
        # First request succeeds
        mock_response_1 = MagicMock(
            status=200,
            headers={},
            read=MagicMock(return_value=b'{"request": 1}'),
            __enter__=lambda self: self,
            __exit__=lambda self, *args: None,
        )

        # Second request fails once then succeeds
        mock_response_2_success = MagicMock(
            status=200,
            headers={},
            read=MagicMock(return_value=b'{"request": 2}'),
            __enter__=lambda self: self,
            __exit__=lambda self, *args: None,
        )

        mock_urlopen.side_effect = [
            mock_response_1,  # First request succeeds immediately
            URLError("Connection refused"),  # Second request fails
            mock_response_2_success,  # Second request retry succeeds
        ]

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        # First request
        response1 = client.get("/test1")
        self.assertEqual(response1.status_code, 200)

        # Second request (should retry independently)
        response2 = client.get("/test2")
        self.assertEqual(response2.status_code, 200)

        # Total of 3 calls (1 for first request, 2 for second request)
        self.assertEqual(mock_urlopen.call_count, 3)


class TestRetryEdgeCases(unittest.TestCase):
    """Test edge cases in retry logic."""

    def test_max_retries_validation(self):
        """Test that max_retries must be non-negative."""
        # Negative max_retries should raise error
        with self.assertRaises(ValueError):
            RESTClient(base_url="https://api.example.com", max_retries=-1)

    def test_very_high_max_retries(self):
        """Test handling of very high max_retries value."""
        # Should accept high values but be reasonable
        client = RESTClient(base_url="https://api.example.com", max_retries=100)
        self.assertEqual(client.max_retries, 100)

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_on_empty_response(self, mock_sleep, mock_urlopen):
        """Test retry behavior on empty/malformed responses."""
        # First response is malformed, second is good
        mock_bad_response = MagicMock(
            status=200,
            headers={},
            read=MagicMock(return_value=b""),  # Empty response
            __enter__=lambda self: self,
            __exit__=lambda self, *args: None,
        )

        mock_good_response = MagicMock(
            status=200,
            headers={},
            read=MagicMock(return_value=b'{"data": "valid"}'),
            __enter__=lambda self: self,
            __exit__=lambda self, *args: None,
        )

        # Note: Depending on implementation, empty response might not trigger retry
        # This test documents expected behavior
        mock_urlopen.side_effect = [mock_bad_response]

        client = RESTClient(base_url="https://api.example.com", max_retries=3)

        response = client.get("/test")

        # Empty response should still be returned (not an error to retry)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b"")
        self.assertEqual(mock_urlopen.call_count, 1)  # No retry

    @patch("urllib.request.urlopen")
    @patch("time.sleep")
    def test_retry_with_custom_retry_codes(self, mock_sleep, mock_urlopen):
        """Test if client supports custom retry status codes (optional feature)."""
        # This tests an optional feature - custom retry codes
        # If not implemented, this test documents the limitation

        mock_urlopen.side_effect = [
            HTTPError(
                url="https://api.example.com/test",
                code=429,  # Too Many Requests
                msg="Too Many Requests",
                hdrs={},
                fp=None,
            ),
            MagicMock(
                status=200,
                headers={},
                read=MagicMock(return_value=b'{"ok": true}'),
                __enter__=lambda self: self,
                __exit__=lambda self, *args: None,
            ),
        ]

        client = RESTClient(
            base_url="https://api.example.com",
            max_retries=3,
            # This might be an optional parameter
            # retry_codes=[429, 500, 502, 503, 504]
        )

        # Depending on implementation, 429 might or might not trigger retry
        try:
            response = client.get("/test")
            # If it retries on 429, this should work
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mock_urlopen.call_count, 2)
        except HTTPError as e:
            # If it doesn't retry on 429, it should fail immediately
            self.assertEqual(e.code, 429)
            self.assertEqual(mock_urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
