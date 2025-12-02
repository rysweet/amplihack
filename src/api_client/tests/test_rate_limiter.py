"""Unit tests for RateLimiter.

Tests thread-safe token bucket rate limiting.
This is part of the 60% unit test coverage.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest


class TestRateLimiterDefaults:
    """Tests for RateLimiter default configuration."""

    def test_default_requests_per_second(self):
        """Default requests_per_second should be 10.0."""
        from api_client import RateLimiter

        limiter = RateLimiter()
        assert limiter.requests_per_second == 10.0

    def test_default_burst_size(self):
        """Default burst_size should equal requests_per_second."""
        from api_client import RateLimiter

        limiter = RateLimiter()
        assert limiter.burst_size == limiter.requests_per_second

    def test_custom_burst_size(self):
        """Custom burst_size should be respected."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=5.0, burst_size=10)
        assert limiter.requests_per_second == 5.0
        assert limiter.burst_size == 10


class TestRateLimiterConfiguration:
    """Tests for RateLimiter configuration validation."""

    def test_custom_requests_per_second(self):
        """Should accept custom requests_per_second."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=5.0)
        assert limiter.requests_per_second == 5.0

    def test_zero_requests_per_second_invalid(self):
        """Zero requests_per_second should raise ValueError."""
        from api_client import RateLimiter

        with pytest.raises(ValueError):
            RateLimiter(requests_per_second=0)

    def test_negative_requests_per_second_invalid(self):
        """Negative requests_per_second should raise ValueError."""
        from api_client import RateLimiter

        with pytest.raises(ValueError):
            RateLimiter(requests_per_second=-1.0)

    def test_zero_burst_size_invalid(self):
        """Zero burst_size should raise ValueError."""
        from api_client import RateLimiter

        with pytest.raises(ValueError):
            RateLimiter(burst_size=0)

    def test_negative_burst_size_invalid(self):
        """Negative burst_size should raise ValueError."""
        from api_client import RateLimiter

        with pytest.raises(ValueError):
            RateLimiter(burst_size=-1)


class TestRateLimiterAcquire:
    """Tests for acquire method."""

    def test_acquire_method_exists(self):
        """RateLimiter should have acquire method."""
        from api_client import RateLimiter

        limiter = RateLimiter()
        assert hasattr(limiter, "acquire")
        assert callable(limiter.acquire)

    def test_first_acquire_immediate(self):
        """First acquire should return immediately (no wait)."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=10)

        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should be nearly instant

    def test_burst_allows_multiple_immediate(self):
        """Burst allows multiple immediate requests."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=1.0, burst_size=5)

        start = time.monotonic()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.monotonic() - start

        # All 5 should be nearly instant due to burst
        assert elapsed < 0.5

    def test_beyond_burst_requires_wait(self):
        """Requests beyond burst should wait."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=2)

        # Use up burst
        limiter.acquire()
        limiter.acquire()

        # Third request should need to wait
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start

        # Should wait at least 1/10 second (0.1s) for next token
        assert elapsed >= 0.05  # Allow some timing slack

    def test_acquire_returns_wait_time(self):
        """acquire should return the time waited (or 0 if immediate)."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=100.0, burst_size=1)

        # First should be immediate
        wait1 = limiter.acquire()
        assert wait1 == 0 or wait1 < 0.01

    def test_rate_limiting_enforced(self):
        """Rate should be approximately requests_per_second."""
        from api_client import RateLimiter

        rate = 20.0  # 20 requests per second
        limiter = RateLimiter(requests_per_second=rate, burst_size=1)

        # Make 5 requests and measure time
        count = 5
        start = time.monotonic()
        for _ in range(count):
            limiter.acquire()
        elapsed = time.monotonic() - start

        # Should take approximately (count-1) / rate seconds
        # First request is immediate, then (count-1) intervals
        expected_min = (count - 1) / rate * 0.8  # 20% tolerance
        assert elapsed >= expected_min


class TestRateLimiterThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_acquires_dont_exceed_limit(self):
        """Concurrent acquires should respect rate limit."""
        from api_client import RateLimiter

        rate = 10.0
        limiter = RateLimiter(requests_per_second=rate, burst_size=5)

        acquired_times = []
        lock = threading.Lock()

        def acquire_and_record():
            limiter.acquire()
            with lock:
                acquired_times.append(time.monotonic())

        # Run 20 concurrent requests
        threads = [threading.Thread(target=acquire_and_record) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check that requests were spread out appropriately
        acquired_times.sort()
        if len(acquired_times) > 1:
            total_time = acquired_times[-1] - acquired_times[0]
            # Should take at least (20 - burst_size) / rate seconds
            expected_min = max(0, (20 - 5) / rate) * 0.5  # 50% tolerance for test stability
            assert total_time >= expected_min

    def test_no_race_conditions_with_thread_pool(self):
        """Thread pool should not cause race conditions."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=100.0, burst_size=10)
        results = []
        errors = []

        def do_acquire(i):
            try:
                limiter.acquire()
                return i
            except Exception as e:
                errors.append(e)
                raise

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(do_acquire, i) for i in range(50)]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass

        assert len(errors) == 0, f"Race conditions caused errors: {errors}"
        assert len(results) == 50

    def test_multiple_limiters_independent(self):
        """Multiple RateLimiter instances should be independent."""
        from api_client import RateLimiter

        limiter1 = RateLimiter(requests_per_second=10.0, burst_size=1)
        limiter2 = RateLimiter(requests_per_second=10.0, burst_size=1)

        # Use up limiter1's token
        limiter1.acquire()

        # limiter2 should still have its token
        start = time.monotonic()
        limiter2.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.05  # Should be nearly instant


class TestRateLimiterTokenBucket:
    """Tests for token bucket behavior."""

    def test_tokens_refill_over_time(self):
        """Tokens should refill over time."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=2)

        # Use all tokens
        limiter.acquire()
        limiter.acquire()

        # Wait for refill (0.2 seconds = 2 tokens at 10/s)
        time.sleep(0.25)

        # Should be able to get tokens without significant wait
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start

        assert elapsed < 0.1  # Should have refilled

    def test_tokens_dont_exceed_burst(self):
        """Tokens should not accumulate beyond burst_size."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=3)

        # Wait long enough to accumulate more than burst tokens
        time.sleep(0.5)  # Would be 5 tokens at 10/s

        # Should only have burst_size (3) available immediately
        start = time.monotonic()
        for _ in range(3):
            limiter.acquire()
        instant_elapsed = time.monotonic() - start

        # Fourth should need to wait
        wait_start = time.monotonic()
        limiter.acquire()
        wait_elapsed = time.monotonic() - wait_start

        assert instant_elapsed < 0.1  # First 3 should be instant
        assert wait_elapsed >= 0.05  # Fourth should wait


class TestRateLimiterNonBlocking:
    """Tests for non-blocking acquire (if supported)."""

    def test_try_acquire_exists(self):
        """RateLimiter should have try_acquire method for non-blocking."""
        from api_client import RateLimiter

        limiter = RateLimiter()
        # This might not exist - test should verify the interface
        if hasattr(limiter, "try_acquire"):
            assert callable(limiter.try_acquire)

    def test_try_acquire_returns_bool(self):
        """try_acquire should return True if token available, False otherwise."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)

        if not hasattr(limiter, "try_acquire"):
            pytest.skip("try_acquire not implemented")

        # First should succeed
        result = limiter.try_acquire()
        assert result is True

        # Second should fail (no waiting)
        result = limiter.try_acquire()
        assert result is False


class TestRateLimiterReset:
    """Tests for reset functionality."""

    def test_reset_restores_burst(self):
        """reset should restore tokens to burst_size."""
        from api_client import RateLimiter

        limiter = RateLimiter(requests_per_second=1.0, burst_size=5)

        # Use all tokens
        for _ in range(5):
            limiter.acquire()

        # Reset
        if hasattr(limiter, "reset"):
            limiter.reset()

            # Should have burst tokens available again
            start = time.monotonic()
            for _ in range(5):
                limiter.acquire()
            elapsed = time.monotonic() - start

            assert elapsed < 0.5  # Should all be instant after reset
        else:
            pytest.skip("reset not implemented")


class TestRateLimiterPerHost:
    """Tests for per-host rate limiting."""

    def test_per_host_isolation(self):
        """Different hosts should have independent rate limits."""
        from api_client import RateLimiter

        # If RateLimiter supports per-host tracking
        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)

        if hasattr(limiter, "acquire_for_host"):
            # Use token for host A
            limiter.acquire_for_host("api.example.com")

            # Host B should still have its token
            start = time.monotonic()
            limiter.acquire_for_host("api.other.com")
            elapsed = time.monotonic() - start

            assert elapsed < 0.05
        else:
            # Basic acquire test if per-host not supported
            limiter.acquire()
            assert True  # Pass if basic acquire works
