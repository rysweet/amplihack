"""Unit tests for rate limiting - testing token bucket algorithm.

Tests rate limiting mechanism in isolation.
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from rest_api_client.exceptions import RateLimitError
from rest_api_client.rate_limiter import RateLimiter, TokenBucket


@pytest.mark.unit
class TestTokenBucket:
    """Test token bucket algorithm."""

    def test_initial_tokens(self):
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10

    def test_consume_tokens(self):
        """Test consuming tokens from bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume 5 tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5

        # Consume 3 more
        assert bucket.consume(3) is True
        assert bucket.tokens == 2

    def test_insufficient_tokens(self):
        """Test when insufficient tokens available."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Try to consume more than available
        assert bucket.consume(15) is False
        assert bucket.tokens == 10  # Unchanged

        # Consume all tokens
        assert bucket.consume(10) is True
        assert bucket.tokens == 0

        # Try to consume when empty
        assert bucket.consume(1) is False
        assert bucket.tokens == 0

    @patch("time.time")
    def test_token_refill(self, mock_time):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens per second

        # Initial state at time 0
        mock_time.return_value = 0
        bucket._last_refill = 0
        bucket.tokens = 5

        # After 1 second, should have 7 tokens (5 + 2)
        mock_time.return_value = 1
        bucket._refill()
        assert bucket.tokens == 7

        # After 2 more seconds, should be at capacity (7 + 4 = 11, capped at 10)
        mock_time.return_value = 3
        bucket._refill()
        assert bucket.tokens == 10

    @patch("time.time")
    def test_fractional_refill(self, mock_time):
        """Test fractional token refill."""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)  # 5 tokens per second

        # Initial state
        mock_time.return_value = 0
        bucket._last_refill = 0
        bucket.tokens = 3

        # After 0.5 seconds, should have 5.5 tokens
        mock_time.return_value = 0.5
        bucket._refill()
        assert bucket.tokens == 5.5

        # After 0.3 more seconds, should have 7 tokens
        mock_time.return_value = 0.8
        bucket._refill()
        assert bucket.tokens == 7

    def test_wait_for_tokens(self):
        """Test waiting for tokens to become available."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens per second

        # Consume all tokens
        bucket.tokens = 0

        # Wait for 1 token (should take 0.1 seconds)
        start = time.time()
        result = bucket.wait_for_tokens(1, timeout=1.0)
        elapsed = time.time() - start

        assert result is True
        assert 0.05 <= elapsed <= 0.2  # Allow some margin

    def test_wait_timeout(self):
        """Test timeout when waiting for tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)  # 1 token per second

        # Consume all tokens
        bucket.tokens = 0

        # Try to wait for 5 tokens with 1 second timeout (would need 5 seconds)
        start = time.time()
        result = bucket.wait_for_tokens(5, timeout=0.1)
        elapsed = time.time() - start

        assert result is False
        assert elapsed < 0.2

    def test_thread_safety(self):
        """Test thread-safe token consumption."""
        bucket = TokenBucket(capacity=100, refill_rate=0)  # No refill during test

        consumed = []

        def consumer(n):
            if bucket.consume(n):
                consumed.append(n)

        # Create multiple threads trying to consume tokens
        threads = []
        for i in range(20):
            t = threading.Thread(target=consumer, args=(5,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Exactly 20 threads should succeed (100 tokens / 5 per thread)
        assert sum(consumed) == 100
        assert bucket.tokens == 0


@pytest.mark.unit
class TestRateLimiter:
    """Test the rate limiter."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        limiter = RateLimiter()
        assert limiter.requests_per_second == 10
        assert limiter.burst_capacity == 20

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        limiter = RateLimiter(requests_per_second=5, burst_capacity=15)
        assert limiter.requests_per_second == 5
        assert limiter.burst_capacity == 15

    def test_allow_request(self):
        """Test allowing requests within rate limit."""
        limiter = RateLimiter(requests_per_second=10, burst_capacity=10)

        # Should allow first 10 requests
        for _ in range(10):
            assert limiter.check_rate_limit() is True

        # 11th request should be blocked
        assert limiter.check_rate_limit() is False

    def test_wait_for_capacity(self):
        """Test waiting for capacity to become available."""
        limiter = RateLimiter(requests_per_second=10, burst_capacity=5)

        # Consume all tokens
        for _ in range(5):
            limiter.check_rate_limit()

        # Should wait and then allow
        start = time.time()
        limiter.wait_if_needed(timeout=1.0)
        elapsed = time.time() - start

        # Should have waited about 0.1 seconds (1 token at 10/sec)
        assert 0.05 <= elapsed <= 0.2

    def test_handle_429_response(self):
        """Test handling 429 rate limit response."""
        limiter = RateLimiter()

        # Mock response with Retry-After header
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}

        with patch("time.sleep") as mock_sleep:
            limiter.handle_429_response(mock_response)
            mock_sleep.assert_called_once_with(5)

    def test_handle_429_without_retry_after(self):
        """Test handling 429 without Retry-After header."""
        limiter = RateLimiter()

        # Mock response without Retry-After header
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {}

        with patch("time.sleep") as mock_sleep:
            limiter.handle_429_response(mock_response)
            # Should use default backoff
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 1 <= sleep_time <= 60  # Default range

    def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting based on responses."""
        limiter = RateLimiter(adaptive=True, requests_per_second=10)

        # Simulate successful requests
        for _ in range(5):
            limiter.record_response(200)

        # Rate should increase slightly
        assert limiter.requests_per_second > 10

        # Simulate rate limit errors
        for _ in range(3):
            limiter.record_response(429)

        # Rate should decrease
        assert limiter.requests_per_second < 10

    def test_rate_limit_headers_parsing(self):
        """Test parsing rate limit headers from response."""
        limiter = RateLimiter()

        mock_response = Mock()
        mock_response.headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "50",
            "X-RateLimit-Reset": str(int(time.time()) + 3600),
        }

        info = limiter.parse_rate_limit_headers(mock_response)

        assert info["limit"] == 100
        assert info["remaining"] == 50
        assert info["reset"] > time.time()

    def test_concurrent_request_limiting(self):
        """Test concurrent request limiting."""
        limiter = RateLimiter(requests_per_second=10, burst_capacity=5)

        success_count = []

        def make_request():
            if limiter.check_rate_limit():
                success_count.append(1)

        # Create multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Only 5 should succeed (burst capacity)
        assert len(success_count) == 5

    def test_reset_rate_limiter(self):
        """Test resetting rate limiter state."""
        limiter = RateLimiter(requests_per_second=10, burst_capacity=5)

        # Consume all tokens
        for _ in range(5):
            limiter.check_rate_limit()

        assert limiter.check_rate_limit() is False

        # Reset limiter
        limiter.reset()

        # Should have full capacity again
        assert limiter.check_rate_limit() is True

    def test_custom_rate_limit_exceeded_handler(self):
        """Test custom handler for rate limit exceeded."""
        called = []

        def custom_handler():
            called.append(True)
            raise RateLimitError("Custom rate limit error")

        limiter = RateLimiter(
            requests_per_second=1, burst_capacity=1, on_rate_limit_exceeded=custom_handler
        )

        # First request OK
        limiter.check_rate_limit()

        # Second request should trigger handler
        with pytest.raises(RateLimitError):
            limiter.enforce_rate_limit()

        assert len(called) == 1

    @patch("time.time")
    def test_time_based_rate_limiting(self, mock_time):
        """Test time-based rate limiting."""
        limiter = RateLimiter(requests_per_second=2, burst_capacity=2)

        # Start at time 0
        mock_time.return_value = 0

        # Use both tokens
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is False

        # After 0.5 seconds, should have 1 token
        mock_time.return_value = 0.5
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is False

        # After 1 second total, should have 1 more token
        mock_time.return_value = 1.0
        assert limiter.check_rate_limit() is True


@pytest.mark.unit
class TestRateLimitStrategies:
    """Test different rate limiting strategies."""

    def test_fixed_window_strategy(self):
        """Test fixed window rate limiting strategy."""
        limiter = RateLimiter(strategy="fixed_window", requests_per_second=10, window_size=1.0)

        # Should allow 10 requests in the window
        for _ in range(10):
            assert limiter.check_rate_limit() is True

        # 11th should fail
        assert limiter.check_rate_limit() is False

    def test_sliding_window_strategy(self):
        """Test sliding window rate limiting strategy."""
        limiter = RateLimiter(strategy="sliding_window", requests_per_second=10, window_size=1.0)

        # Make 5 requests
        for _ in range(5):
            limiter.check_rate_limit()

        time.sleep(0.5)

        # Should allow 5 more (sliding window)
        for _ in range(5):
            assert limiter.check_rate_limit() is True

    def test_leaky_bucket_strategy(self):
        """Test leaky bucket rate limiting strategy."""
        limiter = RateLimiter(strategy="leaky_bucket", requests_per_second=10, bucket_size=5)

        # Fill the bucket
        for _ in range(5):
            limiter.check_rate_limit()

        # Should leak over time
        time.sleep(0.2)  # 2 requests should leak

        # Should allow 2 more
        assert limiter.check_rate_limit() is True
        assert limiter.check_rate_limit() is True
