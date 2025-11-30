"""Unit tests for rate limiting functionality.

Testing focus: Token bucket algorithm, 429 response handling,
rate limit headers parsing, and thread-safe rate limiting.
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest

# These imports will fail initially (TDD approach)
from rest_api_client.rate_limiter import (
    AdaptiveRateLimiter,
    RateLimiter,
    RateLimitExceeded,
    RateLimitHeaders,
    TokenBucket,
)


class TestTokenBucket:
    """Test token bucket algorithm implementation."""

    def test_token_bucket_initialization(self):
        """Test token bucket initializes with correct capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)

        assert bucket.capacity == 10
        assert bucket.tokens == 10
        assert bucket.refill_rate == 2.0

    def test_consume_tokens_success(self):
        """Test consuming tokens when available."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)

        # Consume 5 tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5

        # Consume 3 more tokens
        assert bucket.consume(3) is True
        assert bucket.tokens == 2

    def test_consume_tokens_failure(self):
        """Test consuming tokens when insufficient."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)

        # Try to consume more than available
        assert bucket.consume(11) is False
        assert bucket.tokens == 10  # Unchanged

        # Consume all tokens
        assert bucket.consume(10) is True
        assert bucket.tokens == 0

        # Try to consume when empty
        assert bucket.consume(1) is False

    def test_token_refill(self, mock_time):
        """Test token refilling over time."""
        bucket = TokenBucket(
            capacity=10,
            refill_rate=2.0,  # 2 tokens per second
            clock=mock_time.time,
        )

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Advance time by 2 seconds (should add 4 tokens)
        mock_time.advance(2)
        bucket.refill()
        assert bucket.tokens == 4

        # Advance time by 5 more seconds (should cap at capacity)
        mock_time.advance(5)
        bucket.refill()
        assert bucket.tokens == 10  # Capped at capacity

    def test_token_bucket_thread_safety(self):
        """Test token bucket is thread-safe."""
        bucket = TokenBucket(capacity=100, refill_rate=10)
        consumed = []
        errors = []

        def consume_tokens():
            for _ in range(10):
                try:
                    if bucket.consume(1):
                        consumed.append(1)
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=consume_tokens) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(consumed) <= 100  # Should not exceed capacity

    def test_wait_for_tokens(self, mock_time):
        """Test waiting for tokens to become available."""
        bucket = TokenBucket(
            capacity=10,
            refill_rate=5.0,  # 5 tokens per second
            clock=mock_time.time,
        )

        # Consume all tokens
        bucket.consume(10)

        # Calculate wait time for 3 tokens
        wait_time = bucket.time_until_tokens_available(3)
        assert wait_time == pytest.approx(0.6, rel=0.01)  # 3 tokens / 5 per second

    def test_burst_capacity(self):
        """Test burst capacity allows temporary spike."""
        bucket = TokenBucket(
            capacity=10,
            refill_rate=1.0,
            burst_capacity=15,  # Allow burst up to 15
        )

        # Should allow burst consumption
        assert bucket.consume(12) is True
        assert bucket.tokens == -2  # Negative tokens (debt)

        # Further consumption should fail until refill
        assert bucket.consume(1) is False


class TestRateLimiter:
    """Test the main rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(calls_per_second=10, burst_size=20)

        assert limiter.calls_per_second == 10
        assert limiter.burst_size == 20
        assert limiter.token_bucket is not None

    def test_acquire_permit_success(self):
        """Test acquiring permit when rate limit allows."""
        limiter = RateLimiter(calls_per_second=10)

        # Should succeed immediately
        assert limiter.acquire_permit() is True

    def test_acquire_permit_with_wait(self, mock_time):
        """Test acquiring permit with waiting."""
        limiter = RateLimiter(calls_per_second=1, burst_size=1, clock=mock_time.time)

        # First call succeeds
        assert limiter.acquire_permit() is True

        # Second call should wait
        with patch("time.sleep") as mock_sleep:
            # Configure time to advance during sleep
            def sleep_side_effect(seconds):
                mock_time.advance(seconds)

            mock_sleep.side_effect = sleep_side_effect

            assert limiter.acquire_permit(wait=True, timeout=2) is True
            mock_sleep.assert_called()

    def test_acquire_permit_timeout(self, mock_time):
        """Test acquire permit timeout."""
        limiter = RateLimiter(calls_per_second=1, burst_size=1, clock=mock_time.time)

        # Consume the only token
        limiter.acquire_permit()

        # Try to acquire with short timeout
        assert limiter.acquire_permit(wait=True, timeout=0.1) is False

    def test_rate_limit_headers_parsing(self):
        """Test parsing rate limit headers from response."""
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "42",
            "X-RateLimit-Reset": str(int(time.time()) + 3600),
            "Retry-After": "60",
        }

        parsed = RateLimitHeaders.from_response_headers(headers)

        assert parsed.limit == 100
        assert parsed.remaining == 42
        assert parsed.reset_time > time.time()
        assert parsed.retry_after == 60

    def test_adjust_from_headers(self):
        """Test adjusting rate limiter from response headers."""
        limiter = RateLimiter(calls_per_second=10)

        headers = {
            "X-RateLimit-Limit": "60",  # 60 per hour = 1 per minute
            "X-RateLimit-Remaining": "5",
            "X-RateLimit-Reset": str(int(time.time()) + 300),
        }

        limiter.update_from_headers(headers)

        # Should adjust internal rate
        assert limiter.calls_per_second <= 1.0

    def test_handle_429_response(self, mock_time):
        """Test handling 429 Too Many Requests response."""
        limiter = RateLimiter(calls_per_second=10, clock=mock_time.time)

        # Simulate 429 response
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "5"}

        with patch("time.sleep") as mock_sleep:

            def sleep_side_effect(seconds):
                mock_time.advance(seconds)

            mock_sleep.side_effect = sleep_side_effect

            limiter.handle_429_response(response)

            # Should wait for Retry-After duration
            mock_sleep.assert_called_with(5)

            # Rate should be reduced
            assert limiter.calls_per_second < 10

    def test_concurrent_rate_limiting(self):
        """Test rate limiting with concurrent requests."""
        limiter = RateLimiter(calls_per_second=10, burst_size=5)

        successful_requests = []
        blocked_requests = []

        def make_request(request_id):
            if limiter.acquire_permit(wait=False):
                successful_requests.append(request_id)
            else:
                blocked_requests.append(request_id)

        # Launch many concurrent requests
        threads = []
        for i in range(20):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should allow burst_size requests immediately
        assert len(successful_requests) <= 5
        assert len(blocked_requests) >= 15


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiting that learns from responses."""

    def test_adaptive_rate_adjustment(self):
        """Test adaptive rate limiter adjusts based on success/failure."""
        limiter = AdaptiveRateLimiter(initial_rate=10, min_rate=1, max_rate=100)

        # Successful requests should increase rate
        for _ in range(10):
            limiter.record_success()

        assert limiter.current_rate > 10

        # Failures (429s) should decrease rate
        for _ in range(5):
            limiter.record_rate_limit()

        assert limiter.current_rate < limiter.max_rate

    def test_adaptive_rate_bounds(self):
        """Test adaptive rate stays within bounds."""
        limiter = AdaptiveRateLimiter(initial_rate=10, min_rate=5, max_rate=20)

        # Many successes should hit max rate
        for _ in range(100):
            limiter.record_success()

        assert limiter.current_rate <= 20

        # Many failures should hit min rate
        for _ in range(100):
            limiter.record_rate_limit()

        assert limiter.current_rate >= 5

    def test_exponential_backoff_on_429(self):
        """Test exponential backoff when receiving 429s."""
        limiter = AdaptiveRateLimiter(initial_rate=10)

        initial_rate = limiter.current_rate

        # First 429
        limiter.record_rate_limit()
        rate_after_first = limiter.current_rate
        assert rate_after_first < initial_rate

        # Second 429 (consecutive)
        limiter.record_rate_limit()
        rate_after_second = limiter.current_rate
        assert rate_after_second < rate_after_first

        # The reduction should be more aggressive for consecutive 429s
        first_reduction = initial_rate - rate_after_first
        second_reduction = rate_after_first - rate_after_second
        assert second_reduction > first_reduction

    def test_rate_recovery(self, mock_time):
        """Test rate recovery after successful requests."""
        limiter = AdaptiveRateLimiter(initial_rate=10, recovery_factor=1.1, clock=mock_time.time)

        # Reduce rate due to 429
        limiter.record_rate_limit()
        reduced_rate = limiter.current_rate

        # After some time and successful requests, rate should recover
        mock_time.advance(60)
        for _ in range(10):
            limiter.record_success()
            mock_time.advance(1)

        assert limiter.current_rate > reduced_rate


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with client."""

    def test_rate_limit_with_retry(self):
        """Test rate limiting integrated with retry logic."""
        limiter = RateLimiter(calls_per_second=2)

        request_times = []

        def mock_request():
            if limiter.acquire_permit(wait=True):
                request_times.append(time.time())
                return Mock(status_code=200)
            raise RateLimitExceeded()

        # Make several requests
        for _ in range(4):
            mock_request()

        # Check spacing between requests
        for i in range(1, len(request_times)):
            time_diff = request_times[i] - request_times[i - 1]
            assert time_diff >= 0.4  # ~0.5 seconds apart (2 per second)

    def test_per_endpoint_rate_limiting(self):
        """Test different rate limits for different endpoints."""

        class EndpointRateLimiter:
            def __init__(self):
                self.limiters = {}

            def get_limiter(self, endpoint):
                if endpoint not in self.limiters:
                    # Different limits for different endpoints
                    if "/search" in endpoint:
                        self.limiters[endpoint] = RateLimiter(calls_per_second=1)
                    elif "/bulk" in endpoint:
                        self.limiters[endpoint] = RateLimiter(calls_per_second=0.1)
                    else:
                        self.limiters[endpoint] = RateLimiter(calls_per_second=10)
                return self.limiters[endpoint]

        endpoint_limiter = EndpointRateLimiter()

        # Different endpoints should have different limits
        search_limiter = endpoint_limiter.get_limiter("/search")
        bulk_limiter = endpoint_limiter.get_limiter("/bulk")
        default_limiter = endpoint_limiter.get_limiter("/users")

        assert search_limiter.calls_per_second == 1
        assert bulk_limiter.calls_per_second == 0.1
        assert default_limiter.calls_per_second == 10

    def test_rate_limit_statistics(self):
        """Test collecting rate limit statistics."""
        limiter = RateLimiter(calls_per_second=5, burst_size=2)

        # Track statistics
        limiter.enable_statistics()

        # Make some requests
        for i in range(10):
            limiter.acquire_permit(wait=False)
            time.sleep(0.1)

        stats = limiter.get_statistics()
        assert "total_requests" in stats
        assert "allowed_requests" in stats
        assert "blocked_requests" in stats
        assert "current_rate" in stats
        assert stats["total_requests"] == 10

    def test_rate_limit_with_api_key_isolation(self):
        """Test rate limiting isolated per API key."""

        class ApiKeyRateLimiter:
            def __init__(self):
                self.limiters = {}

            def get_limiter(self, api_key):
                if api_key not in self.limiters:
                    self.limiters[api_key] = RateLimiter(calls_per_second=5)
                return self.limiters[api_key]

        key_limiter = ApiKeyRateLimiter()

        # Different API keys have separate limits
        limiter1 = key_limiter.get_limiter("key1")
        limiter2 = key_limiter.get_limiter("key2")

        # Exhaust limiter1
        for _ in range(5):
            limiter1.acquire_permit()

        # limiter2 should still have tokens
        assert limiter2.acquire_permit() is True

    def test_distributed_rate_limiting(self):
        """Test distributed rate limiting across multiple instances."""

        # This would use Redis or similar in production
        class DistributedRateLimiter:
            def __init__(self, redis_client=None):
                self.redis = redis_client or Mock()
                self.local_cache = {}

            def acquire_permit(self, key, limit=10):
                # Check Redis for current count
                current = self.redis.incr(f"rate_limit:{key}")

                if current <= limit:
                    return True

                # Exceeded limit
                self.redis.decr(f"rate_limit:{key}")
                return False

        redis_mock = Mock()
        redis_mock.incr.return_value = 1

        limiter = DistributedRateLimiter(redis_mock)
        assert limiter.acquire_permit("test_key") is True

        # Simulate limit exceeded
        redis_mock.incr.return_value = 11
        assert limiter.acquire_permit("test_key") is False
