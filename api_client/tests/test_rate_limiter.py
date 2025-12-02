"""Unit tests for RateLimiter.

Testing pyramid: 60% unit tests (these tests)
"""

import threading
import time

import pytest

from api_client.rate_limiter import RateLimiter


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_create_with_valid_params(self):
        """Test creating rate limiter with valid parameters."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)
        assert limiter._max_requests == 10
        assert limiter._time_window == 60.0
        assert limiter._tokens == 10.0

    def test_validate_invalid_max_requests(self):
        """Test that invalid max_requests raises ValueError."""
        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimiter(max_requests=0, time_window=60.0)

        with pytest.raises(ValueError, match="max_requests must be positive"):
            RateLimiter(max_requests=-1, time_window=60.0)

    def test_validate_invalid_time_window(self):
        """Test that invalid time_window raises ValueError."""
        with pytest.raises(ValueError, match="time_window must be positive"):
            RateLimiter(max_requests=10, time_window=0.0)

        with pytest.raises(ValueError, match="time_window must be positive"):
            RateLimiter(max_requests=10, time_window=-1.0)


class TestRateLimiterAcquire:
    """Tests for RateLimiter.acquire method."""

    def test_acquire_immediate_success(self):
        """Test acquiring token when available."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)

        # First 10 acquires should succeed immediately
        for _ in range(10):
            assert limiter.acquire(timeout=0.1) is True

    def test_acquire_blocks_when_empty(self):
        """Test acquiring blocks when no tokens available."""
        limiter = RateLimiter(max_requests=1, time_window=0.5)

        # First acquire succeeds
        assert limiter.acquire() is True

        # Second acquire should block briefly then succeed as tokens refill
        start = time.monotonic()
        assert limiter.acquire(timeout=1.0) is True
        elapsed = time.monotonic() - start

        # Should have waited at least part of the refill time
        assert elapsed >= 0.1  # At least some waiting occurred

    def test_acquire_timeout(self):
        """Test acquire timeout when tokens unavailable."""
        limiter = RateLimiter(max_requests=1, time_window=10.0)

        # Exhaust tokens
        limiter.acquire()

        # Next acquire should timeout
        start = time.monotonic()
        result = limiter.acquire(timeout=0.1)
        elapsed = time.monotonic() - start

        assert result is False
        assert elapsed < 0.5  # Should timeout quickly


class TestRateLimiterRefill:
    """Tests for token refill behavior."""

    def test_tokens_refill_over_time(self):
        """Test that tokens refill over time."""
        limiter = RateLimiter(max_requests=10, time_window=1.0)

        # Consume some tokens
        for _ in range(5):
            limiter.acquire()

        # Check available tokens
        assert limiter.available_tokens == pytest.approx(5.0, abs=0.1)

        # Wait for partial refill
        time.sleep(0.2)

        # Should have refilled ~2 tokens (10 tokens/sec * 0.2 sec)
        assert limiter.available_tokens >= 6.5
        assert limiter.available_tokens <= 7.5

    def test_tokens_capped_at_max(self):
        """Test that tokens don't exceed max_requests."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)

        # Wait for full refill and then some
        time.sleep(2.0)

        # Tokens should be capped at max
        assert limiter.available_tokens == pytest.approx(5.0, abs=0.1)


class TestRateLimiterReset:
    """Tests for RateLimiter.reset method."""

    def test_reset_refills_tokens(self):
        """Test that reset refills all tokens."""
        limiter = RateLimiter(max_requests=10, time_window=60.0)

        # Consume all tokens
        for _ in range(10):
            limiter.acquire()

        assert limiter.available_tokens == pytest.approx(0.0, abs=0.1)

        # Reset
        limiter.reset()

        assert limiter.available_tokens == pytest.approx(10.0, abs=0.1)


class TestRateLimiterThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_acquire(self):
        """Test that concurrent acquires are thread-safe."""
        limiter = RateLimiter(max_requests=100, time_window=1.0)
        success_count = []

        def acquire_token():
            if limiter.acquire(timeout=2.0):
                success_count.append(1)

        # Launch 100 threads to acquire tokens
        threads = [threading.Thread(target=acquire_token) for _ in range(100)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All 100 should succeed (we have 100 tokens)
        assert len(success_count) == 100

    def test_concurrent_acquire_exceeding_limit(self):
        """Test concurrent acquires when exceeding limit."""
        limiter = RateLimiter(max_requests=10, time_window=10.0)
        results = []

        def acquire_with_result():
            result = limiter.acquire(timeout=0.1)
            results.append(result)

        # Launch 20 threads to acquire 10 tokens
        threads = [threading.Thread(target=acquire_with_result) for _ in range(20)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have at least 10 successes (initial tokens)
        success_count = sum(1 for r in results if r)
        assert success_count >= 10

        # Not all should succeed immediately
        assert success_count < 20
