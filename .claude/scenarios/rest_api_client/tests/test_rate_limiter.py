"""Unit tests for rate limiting."""

import threading
import time

import pytest

# These imports will fail initially (TDD)
from rest_api_client.rate_limiter import (
    AdaptiveRateLimiter,
    RateLimiter,
    SlidingWindow,
    TokenBucket,
)


class TestTokenBucket:
    """Test token bucket rate limiter."""

    def test_token_bucket_creation(self):
        """Test creating token bucket."""
        bucket = TokenBucket(
            capacity=10,
            refill_rate=2.0,  # 2 tokens per second
        )
        assert bucket.capacity == 10
        assert bucket.refill_rate == 2.0
        assert bucket.tokens == 10  # Starts full

    def test_token_bucket_consume(self, mock_time):
        """Test consuming tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5

        assert bucket.consume(3) is True
        assert bucket.tokens == 2

        # Not enough tokens
        assert bucket.consume(5) is False
        assert bucket.tokens == 2  # Unchanged

    def test_token_bucket_refill(self, mock_time):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)

        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Advance time by 2 seconds (should add 4 tokens)
        mock_time(2.0)
        bucket.refill()
        assert bucket.tokens == 4

        # Advance time by 5 seconds (should be capped at capacity)
        mock_time(5.0)
        bucket.refill()
        assert bucket.tokens == 10  # Capped at capacity

    def test_token_bucket_wait_for_tokens(self, mock_time):
        """Test waiting for tokens to become available."""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)
        bucket.consume(10)  # Empty the bucket

        # Should wait for 1 second to get 5 tokens
        wait_time = bucket.wait_time_for_tokens(5)
        assert wait_time == pytest.approx(1.0, rel=0.1)

        # Should wait for 2 seconds to get 10 tokens
        wait_time = bucket.wait_time_for_tokens(10)
        assert wait_time == pytest.approx(2.0, rel=0.1)

    def test_token_bucket_thread_safety(self):
        """Test token bucket thread safety."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        results = []

        def consume_tokens():
            for _ in range(10):
                if bucket.consume(1):
                    results.append(1)
                time.sleep(0.001)

        threads = [threading.Thread(target=consume_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have consumed exactly 100 tokens (or close to it)
        assert 90 <= len(results) <= 100


class TestSlidingWindow:
    """Test sliding window rate limiter."""

    def test_sliding_window_creation(self):
        """Test creating sliding window."""
        window = SlidingWindow(
            max_requests=100,
            window_size=60,  # 60 seconds
        )
        assert window.max_requests == 100
        assert window.window_size == 60

    def test_sliding_window_allow_request(self, mock_time):
        """Test allowing requests within window."""
        window = SlidingWindow(max_requests=3, window_size=10)

        # First 3 requests should be allowed
        assert window.allow_request() is True
        assert window.allow_request() is True
        assert window.allow_request() is True

        # 4th request should be denied
        assert window.allow_request() is False

        # Advance time past window
        mock_time(11)

        # Should allow new requests
        assert window.allow_request() is True

    def test_sliding_window_cleanup(self, mock_time):
        """Test cleanup of old requests."""
        window = SlidingWindow(max_requests=5, window_size=10)

        # Add requests at different times
        for i in range(3):
            window.allow_request()
            mock_time(2)  # Advance 2 seconds

        # Now at t=6, we have 3 requests
        assert len(window.requests) == 3

        # Advance to t=12 (first request should expire)
        mock_time(6)
        window.cleanup()
        assert len(window.requests) == 2

    def test_sliding_window_reset(self):
        """Test resetting sliding window."""
        window = SlidingWindow(max_requests=5, window_size=10)

        window.allow_request()
        window.allow_request()
        assert len(window.requests) == 2

        window.reset()
        assert len(window.requests) == 0


class TestAdaptiveRateLimiter:
    """Test adaptive rate limiter."""

    def test_adaptive_rate_limiter_creation(self):
        """Test creating adaptive rate limiter."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0, min_rate=1.0, max_rate=100.0)
        assert limiter.current_rate == 10.0
        assert limiter.min_rate == 1.0
        assert limiter.max_rate == 100.0

    def test_adaptive_increase_rate(self):
        """Test increasing rate on success."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0, max_rate=100.0, increase_factor=1.5)

        # Successful requests should increase rate
        for _ in range(10):
            limiter.record_success()

        assert limiter.current_rate > 10.0
        assert limiter.current_rate <= 100.0

    def test_adaptive_decrease_rate(self):
        """Test decreasing rate on rate limit errors."""
        limiter = AdaptiveRateLimiter(initial_rate=50.0, min_rate=5.0, decrease_factor=0.5)

        # Rate limit error should decrease rate
        limiter.record_rate_limit()
        assert limiter.current_rate == 25.0

        limiter.record_rate_limit()
        assert limiter.current_rate == 12.5

        # Should not go below minimum
        for _ in range(10):
            limiter.record_rate_limit()
        assert limiter.current_rate >= 5.0

    def test_adaptive_wait_time(self):
        """Test calculating wait time based on current rate."""
        limiter = AdaptiveRateLimiter(initial_rate=10.0)

        # At 10 requests per second, wait time should be 0.1 seconds
        wait_time = limiter.get_wait_time()
        assert wait_time == pytest.approx(0.1, rel=0.01)

        # Decrease rate
        limiter.current_rate = 2.0
        wait_time = limiter.get_wait_time()
        assert wait_time == pytest.approx(0.5, rel=0.01)


class TestRateLimiter:
    """Test main RateLimiter class."""

    def test_rate_limiter_with_token_bucket(self, mock_time):
        """Test RateLimiter with token bucket strategy."""
        limiter = RateLimiter(strategy="token_bucket", capacity=10, refill_rate=5.0)

        # Should allow up to capacity
        for _ in range(10):
            assert limiter.allow_request() is True

        # Should deny when empty
        assert limiter.allow_request() is False

        # Wait for refill
        mock_time(1.0)
        assert limiter.allow_request() is True  # 5 tokens refilled

    def test_rate_limiter_with_sliding_window(self, mock_time):
        """Test RateLimiter with sliding window strategy."""
        limiter = RateLimiter(strategy="sliding_window", max_requests=5, window_size=10)

        # Allow up to max_requests
        for _ in range(5):
            assert limiter.allow_request() is True

        assert limiter.allow_request() is False

        # Move past window
        mock_time(11)
        assert limiter.allow_request() is True

    def test_rate_limiter_with_adaptive(self):
        """Test RateLimiter with adaptive strategy."""
        limiter = RateLimiter(strategy="adaptive", initial_rate=10.0)

        # Should adapt based on responses
        limiter.record_response(200)  # Success
        assert limiter.current_rate >= 10.0

        limiter.record_response(429)  # Rate limited
        assert limiter.current_rate < 10.0

    def test_rate_limiter_wait_if_needed(self, mock_time):
        """Test waiting when rate limited."""
        limiter = RateLimiter(strategy="token_bucket", capacity=1, refill_rate=1.0)

        # First request should go through
        limiter.wait_if_needed()
        assert limiter.allow_request() is True

        # Second request should wait
        start_time = time.time()
        limiter.wait_if_needed()
        # Should have waited approximately 1 second
        # (mock_time handles the actual waiting)

    def test_rate_limiter_context_manager(self):
        """Test using rate limiter as context manager."""
        with RateLimiter(strategy="token_bucket", capacity=10) as limiter:
            assert limiter.allow_request() is True

    def test_rate_limiter_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter(strategy="sliding_window", max_requests=3, window_size=10)

        limiter.allow_request()
        limiter.allow_request()
        limiter.reset()

        # Should be able to make max_requests again
        for _ in range(3):
            assert limiter.allow_request() is True
