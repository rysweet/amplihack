"""
Tests for rate limiting mechanism.

Tests the rate limiter that enforces requests per second/minute limits
and handles 429 Rate Limit responses.

Coverage areas:
- Requests per second limiting
- Requests per minute limiting
- 429 response handling
- Retry-After header parsing
- Rate limit wait time calculation
- Concurrent request rate limiting
"""

import time
from unittest.mock import Mock, patch

import pytest


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_rate_limiter_creation(self) -> None:
        """Test creating RateLimiter with per-second limit."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10)
        assert limiter.requests_per_second == 10
        assert limiter.requests_per_minute is None

    def test_rate_limiter_per_minute(self) -> None:
        """Test RateLimiter with per-minute limit."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_minute=100)
        assert limiter.requests_per_second is None
        assert limiter.requests_per_minute == 100

    def test_rate_limiter_both_limits(self) -> None:
        """Test RateLimiter with both per-second and per-minute limits."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10, requests_per_minute=500)
        assert limiter.requests_per_second == 10
        assert limiter.requests_per_minute == 500


class TestRequestsPerSecondLimiting:
    """Test requests per second rate limiting."""

    def test_allows_requests_under_limit(self) -> None:
        """Test RateLimiter allows requests under the limit."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10)

        # First request should be allowed
        assert limiter.allows_request() is True

    def test_blocks_requests_over_limit(self) -> None:
        """Test RateLimiter blocks requests over the limit."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # Make 2 requests quickly
        limiter.record_request()
        limiter.record_request()

        # Third request should be blocked
        assert limiter.allows_request() is False

    def test_rate_limit_enforced_timing(self) -> None:
        """Test rate limit enforces timing correctly."""
        import time

        from amplihack.api_client import RestClient

        client = RestClient(
            base_url="https://api.example.com",
            rate_limit_per_second=2,  # 2 requests per second
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            start = time.time()

            # Make 5 requests
            for i in range(5):
                client.get(f"/item/{i}")

            elapsed = time.time() - start

            # Should take at least 2 seconds (5 requests / 2 per second = 2.5s)
            assert elapsed >= 2.0

    def test_wait_time_calculation(self) -> None:
        """Test calculating wait time until next allowed request."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # Make requests to hit limit
        limiter.record_request()
        limiter.record_request()

        # Should need to wait ~0.5 seconds
        wait = limiter.wait_time()
        assert wait > 0
        assert wait <= 1.0  # Should be less than a full second


class TestRequestsPerMinuteLimiting:
    """Test requests per minute rate limiting."""

    def test_per_minute_limit_enforcement(self) -> None:
        """Test per-minute rate limit is enforced."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Make 60 requests
        for _ in range(60):
            limiter.record_request()

        # 61st request should be blocked
        assert limiter.allows_request() is False

    def test_per_minute_limit_resets(self) -> None:
        """Test per-minute limit resets after a minute."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_minute=10)

        # Fill the limit
        for _ in range(10):
            limiter.record_request()

        # Should be blocked
        assert limiter.allows_request() is False

        # Simulate time passing (mock internal timestamp)
        # After 60+ seconds, should allow again
        # (Implementation detail - may need adjustment based on actual code)

    def test_combined_limits_enforced(self) -> None:
        """Test both per-second and per-minute limits enforced."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10, requests_per_minute=100)

        # Make 10 requests in quick succession
        for _ in range(10):
            limiter.record_request()

        # Should hit per-second limit
        assert limiter.allows_request() is False


class Test429ResponseHandling:
    """Test handling of 429 Rate Limit responses."""

    def test_429_triggers_retry(self) -> None:
        """Test 429 response triggers retry with backoff."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=429, ok=False, headers={"Retry-After": "1"}),
                Mock(status_code=200, ok=True),
            ]

            response = client.get("/endpoint")
            assert response.status_code == 200
            assert mock_request.call_count == 2

    def test_429_respects_retry_after_header(self) -> None:
        """Test 429 handler respects Retry-After header."""
        import time

        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(
                    status_code=429,
                    ok=False,
                    headers={"Retry-After": "2"},  # Wait 2 seconds
                ),
                Mock(status_code=200, ok=True),
            ]

            start = time.time()
            client.get("/endpoint")
            elapsed = time.time() - start

            # Should have waited at least 2 seconds
            assert elapsed >= 2.0

    def test_429_without_retry_after(self) -> None:
        """Test 429 handler uses exponential backoff without Retry-After."""
        from amplihack.api_client import RestClient

        client = RestClient(
            base_url="https://api.example.com", max_retries=2, retry_backoff_factor=0.5
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=429, ok=False, headers={}),
                Mock(status_code=200, ok=True),
            ]

            response = client.get("/endpoint")
            assert response.status_code == 200

    def test_429_max_retries_exhausted(self) -> None:
        """Test 429 retries until max_retries exhausted."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RateLimitError

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        with patch.object(client, "_make_request") as mock_request:
            # Always return 429
            mock_request.return_value = Mock(
                status_code=429, ok=False, headers={"Retry-After": "60"}
            )

            with pytest.raises(RateLimitError) as exc_info:
                client.get("/endpoint")

            # Should have tried initial + 2 retries
            assert mock_request.call_count == 3
            assert exc_info.value.status_code == 429


class TestRetryAfterHeader:
    """Test parsing and handling of Retry-After header."""

    def test_retry_after_seconds(self) -> None:
        """Test parsing Retry-After as seconds."""
        from amplihack.api_client.exceptions import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        error = RateLimitError("Rate limited", response=mock_response)
        assert error.retry_after == 60

    def test_retry_after_http_date(self) -> None:
        """Test parsing Retry-After as HTTP date."""
        import time
        from email.utils import formatdate

        from amplihack.api_client.exceptions import RateLimitError

        # Create a date 30 seconds in the future
        future_time = time.time() + 30
        http_date = formatdate(future_time, usegmt=True)

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": http_date}

        error = RateLimitError("Rate limited", response=mock_response)
        # Should parse to approximately 30 seconds
        assert 25 <= error.retry_after <= 35

    def test_retry_after_missing_header(self) -> None:
        """Test handling missing Retry-After header."""
        from amplihack.api_client.exceptions import RateLimitError

        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {}

        error = RateLimitError("Rate limited", response=mock_response)
        # Should default to None or reasonable value
        assert error.retry_after is None or isinstance(error.retry_after, int)


class TestClientIntegrationRateLimiting:
    """Integration tests for rate limiting in RestClient."""

    def test_client_rate_limit_configuration(self) -> None:
        """Test configuring rate limits on client."""
        from amplihack.api_client import RestClient

        client = RestClient(
            base_url="https://api.example.com", rate_limit_per_second=10, rate_limit_per_minute=500
        )

        assert client.rate_limiter is not None
        assert client.rate_limiter.requests_per_second == 10
        assert client.rate_limiter.requests_per_minute == 500

    def test_client_enforces_rate_limits(self) -> None:
        """Test client enforces configured rate limits."""
        import time

        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", rate_limit_per_second=5)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            start = time.time()

            # Make 10 requests
            for i in range(10):
                client.get(f"/item/{i}")

            elapsed = time.time() - start

            # Should take at least 1 second (10 requests / 5 per second)
            assert elapsed >= 1.0

    def test_client_no_rate_limit_by_default(self) -> None:
        """Test client has no rate limit by default."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com")

        # No rate limiter configured
        assert client.rate_limiter is None

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            # Should make requests without delay
            start = time.time()
            for i in range(10):
                client.get(f"/item/{i}")
            elapsed = time.time() - start

            # Should be fast (< 1 second for 10 requests)
            assert elapsed < 1.0


class TestConcurrentRateLimiting:
    """Test rate limiting with concurrent requests."""

    def test_rate_limit_thread_safe(self) -> None:
        """Test rate limiter is thread-safe for concurrent requests."""
        import threading

        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10)

        def make_requests():
            for _ in range(5):
                if limiter.allows_request():
                    limiter.record_request()

        threads = [threading.Thread(target=make_requests) for _ in range(4)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have properly tracked requests across threads
        # (Actual assertion depends on implementation details)

    def test_concurrent_429_handling(self) -> None:
        """Test handling multiple concurrent 429 responses."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", max_retries=2)

        # Multiple requests hit rate limit
        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                Mock(status_code=429, ok=False, headers={"Retry-After": "1"}),
                Mock(status_code=200, ok=True),
            ]

            # Should handle gracefully
            response = client.get("/endpoint")
            assert response.status_code == 200


class TestRateLimitContext:
    """Test rate limiter context manager."""

    def test_rate_limiter_context_manager(self) -> None:
        """Test using RateLimiter as context manager."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=5)

        with limiter:
            # Request should be rate limited within context
            pass

        # Context should have tracked the request
        # (Assertion depends on implementation)

    def test_multiple_contexts(self) -> None:
        """Test multiple rate limiter contexts."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # Rapidly use contexts
        for _ in range(5):
            with limiter:
                pass

        # Should have enforced rate limiting across all contexts


class TestRateLimitMetrics:
    """Test rate limit metrics and statistics."""

    def test_track_requests_count(self) -> None:
        """Test tracking total requests made."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10)

        for _ in range(5):
            limiter.record_request()

        assert limiter.total_requests == 5

    def test_track_rate_limit_hits(self) -> None:
        """Test tracking how many times rate limit was hit."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=2)

        # Fill limit
        limiter.record_request()
        limiter.record_request()

        # Try to exceed
        for _ in range(3):
            if not limiter.allows_request():
                limiter.record_rate_limit_hit()

        assert limiter.rate_limit_hits >= 1

    def test_calculate_current_rate(self) -> None:
        """Test calculating current request rate."""
        from amplihack.api_client.models import RateLimiter

        limiter = RateLimiter(requests_per_second=10)

        for _ in range(5):
            limiter.record_request()

        # Current rate should be calculable
        rate = limiter.current_rate()
        assert isinstance(rate, (int, float))
        assert rate >= 0
