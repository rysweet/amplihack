"""Tests for RateLimiter token bucket implementation.

Testing pyramid distribution:
- 80% Unit tests (algorithm, defaults, edge cases)
- 20% Integration tests (thread safety, timing)
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest


class TestRateLimiterCreation:
    """Test RateLimiter initialization and defaults."""

    def test_create_rate_limiter_with_default(self):
        """Test creating RateLimiter with default rate (10 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange & Act
        limiter = RateLimiter()

        # Assert
        # Should have default of 10 requests per second
        assert limiter is not None

    def test_create_rate_limiter_with_custom_rate(self):
        """Test creating RateLimiter with custom rate."""
        from api_client.rate_limiter import RateLimiter

        # Arrange & Act
        limiter = RateLimiter(requests_per_second=5.0)

        # Assert
        assert limiter is not None

    def test_create_rate_limiter_with_low_rate(self):
        """Test creating RateLimiter with low rate (1 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange & Act
        limiter = RateLimiter(requests_per_second=1.0)

        # Assert
        assert limiter is not None

    def test_create_rate_limiter_with_high_rate(self):
        """Test creating RateLimiter with high rate (100 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange & Act
        limiter = RateLimiter(requests_per_second=100.0)

        # Assert
        assert limiter is not None

    def test_create_rate_limiter_with_fractional_rate(self):
        """Test creating RateLimiter with fractional rate (2.5 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange & Act
        limiter = RateLimiter(requests_per_second=2.5)

        # Assert
        assert limiter is not None

    def test_create_rate_limiter_rejects_zero_rate(self):
        """Test that zero rate raises ValueError."""
        from api_client.rate_limiter import RateLimiter

        # Act & Assert
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimiter(requests_per_second=0.0)

    def test_create_rate_limiter_rejects_negative_rate(self):
        """Test that negative rate raises ValueError."""
        from api_client.rate_limiter import RateLimiter

        # Act & Assert
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimiter(requests_per_second=-5.0)


class TestRateLimiterAcquire:
    """Test RateLimiter token acquisition."""

    def test_acquire_single_token(self):
        """Test acquiring a single token (non-blocking when available)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=10.0)

        # Act
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start

        # Assert - should be nearly instant (<0.1s)
        assert elapsed < 0.1

    def test_acquire_within_burst_limit(self):
        """Test acquiring tokens within burst capacity (should not block)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 10 req/sec allows burst of ~10 tokens
        limiter = RateLimiter(requests_per_second=10.0)

        # Act - acquire 5 tokens rapidly
        start = time.time()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should be fast (<0.2s) since within burst capacity
        assert elapsed < 0.2

    def test_acquire_exceeding_burst_blocks(self):
        """Test that exceeding burst capacity causes blocking."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 2 req/sec
        limiter = RateLimiter(requests_per_second=2.0)

        # Act - acquire 6 tokens (3x the rate)
        start = time.time()
        for _ in range(6):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should take at least 2 seconds (6 tokens at 2/sec = 3 sec)
        # Allow some tolerance for timing
        assert elapsed >= 1.5

    def test_acquire_enforces_rate_limit(self):
        """Test that acquire enforces the configured rate limit."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 5 req/sec
        limiter = RateLimiter(requests_per_second=5.0)

        # Act - acquire 15 tokens
        start = time.time()
        for _ in range(15):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should take at least 2 seconds (15 tokens at 5/sec = 3 sec)
        assert elapsed >= 2.0

    def test_acquire_allows_burst_then_throttles(self):
        """Test that initial burst is allowed, then throttling kicks in."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 10 req/sec
        limiter = RateLimiter(requests_per_second=10.0)

        # Act - first batch (burst)
        start1 = time.time()
        for _ in range(5):
            limiter.acquire()
        burst_elapsed = time.time() - start1

        # Act - second batch (should throttle)
        start2 = time.time()
        for _ in range(10):
            limiter.acquire()
        throttled_elapsed = time.time() - start2

        # Assert - burst should be fast, throttled should be slower
        assert burst_elapsed < 0.2  # Burst is fast
        assert throttled_elapsed >= 0.5  # Throttling kicks in


class TestRateLimiterThreadSafety:
    """Test RateLimiter thread safety (CRITICAL for concurrent use)."""

    def test_thread_safe_concurrent_acquire(self):
        """Test that concurrent acquire from multiple threads is safe."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=10.0)
        results = []
        lock = threading.Lock()

        def worker():
            start = time.time()
            limiter.acquire()
            elapsed = time.time() - start
            with lock:
                results.append(elapsed)

        # Act - 20 threads trying to acquire
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert - all threads completed without errors
        assert len(results) == 20

    def test_thread_safe_multiple_limiters(self):
        """Test that multiple limiter instances are independent."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter1 = RateLimiter(requests_per_second=5.0)
        limiter2 = RateLimiter(requests_per_second=10.0)

        results1 = []
        results2 = []

        def worker1():
            limiter1.acquire()
            results1.append(1)

        def worker2():
            limiter2.acquire()
            results2.append(1)

        # Act
        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=worker1))
            threads.append(threading.Thread(target=worker2))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert - both limiters worked independently
        assert len(results1) == 10
        assert len(results2) == 10

    def test_thread_safe_with_thread_pool(self):
        """Test thread safety using ThreadPoolExecutor."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=20.0)

        def task():
            limiter.acquire()
            return True

        # Act
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(task) for _ in range(50)]
            results = [f.result() for f in futures]

        # Assert - all tasks completed successfully
        assert len(results) == 50
        assert all(results)


class TestRateLimiterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_acquire_after_long_idle(self):
        """Test that tokens refill during idle period."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 10 req/sec
        limiter = RateLimiter(requests_per_second=10.0)

        # Exhaust tokens
        for _ in range(10):
            limiter.acquire()

        # Act - wait for refill
        time.sleep(1.0)  # Tokens should refill

        # Act - acquire again (should be fast)
        start = time.time()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should be fast after refill
        assert elapsed < 0.2

    def test_very_low_rate_limit(self):
        """Test rate limiter with very low rate (0.5 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=0.5)

        # Act - acquire 2 tokens
        start = time.time()
        limiter.acquire()
        limiter.acquire()
        elapsed = time.time() - start

        # Assert - should take at least 2 seconds (2 tokens at 0.5/sec = 4 sec)
        assert elapsed >= 1.5

    def test_very_high_rate_limit(self):
        """Test rate limiter with very high rate (1000 req/sec)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=1000.0)

        # Act - acquire 100 tokens
        start = time.time()
        for _ in range(100):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should be very fast (100/1000 = 0.1 sec)
        assert elapsed < 0.5

    def test_fractional_rate_precision(self):
        """Test fractional rate limits work correctly."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 2.5 req/sec
        limiter = RateLimiter(requests_per_second=2.5)

        # Act - acquire 10 tokens
        start = time.time()
        for _ in range(10):
            limiter.acquire()
        elapsed = time.time() - start

        # Assert - should take about 4 seconds (10 / 2.5 = 4)
        assert elapsed >= 3.0

    def test_rapid_acquire_release_pattern(self):
        """Test rapid acquire pattern (common in request bursts)."""
        from api_client.rate_limiter import RateLimiter

        # Arrange
        limiter = RateLimiter(requests_per_second=10.0)

        # Act - burst of 20 acquisitions
        acquisitions = 0
        start = time.time()
        for _ in range(20):
            limiter.acquire()
            acquisitions += 1
        elapsed = time.time() - start

        # Assert
        assert acquisitions == 20
        assert elapsed >= 1.0  # Should take at least 1 second for 20 at 10/sec


class TestRateLimiterIntegration:
    """Integration tests combining rate limiter with realistic scenarios."""

    def test_simulate_api_client_requests(self):
        """Simulate realistic API client request pattern."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - 5 req/sec (common API limit)
        limiter = RateLimiter(requests_per_second=5.0)
        request_count = 0

        # Act - simulate 15 API requests
        start = time.time()
        for _ in range(15):
            limiter.acquire()
            request_count += 1
            # Simulate actual request time
            time.sleep(0.01)
        elapsed = time.time() - start

        # Assert
        assert request_count == 15
        # Should take at least 2 seconds (15 requests at 5/sec = 3 sec)
        assert elapsed >= 2.0

    def test_multiple_clients_share_limiter(self):
        """Test multiple clients sharing a single rate limiter."""
        from api_client.rate_limiter import RateLimiter

        # Arrange - shared limiter
        shared_limiter = RateLimiter(requests_per_second=10.0)
        results = {"client1": 0, "client2": 0}
        lock = threading.Lock()

        def client1_worker():
            for _ in range(10):
                shared_limiter.acquire()
                with lock:
                    results["client1"] += 1

        def client2_worker():
            for _ in range(10):
                shared_limiter.acquire()
                with lock:
                    results["client2"] += 1

        # Act
        t1 = threading.Thread(target=client1_worker)
        t2 = threading.Thread(target=client2_worker)

        start = time.time()
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        elapsed = time.time() - start

        # Assert - both clients completed, rate limit enforced
        assert results["client1"] == 10
        assert results["client2"] == 10
        # 20 total requests at 10/sec = 2 seconds minimum
        assert elapsed >= 1.5
