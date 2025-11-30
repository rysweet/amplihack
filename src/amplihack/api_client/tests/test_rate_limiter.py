"""Tests for rate limiting functionality - TDD approach.

Focus on rate limit tracking, throttling, and bucket management.
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest

from amplihack.api_client.rate_limiter import (
    RateLimitConfig,
    RateLimiter,
    RateLimitExceeded,
    RequestMetadata,
    SlidingWindow,
    TokenBucket,
    adaptive_rate_limit,
)


class TestTokenBucket:
    """Unit tests for Token Bucket rate limiting."""

    def test_token_bucket_initialization(self):
        """Test Token Bucket initialization."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)
        assert bucket.capacity == 10
        assert bucket.refill_rate == 2.0
        assert bucket.tokens == 10  # Starts full

    def test_token_bucket_consume_success(self):
        """Test consuming tokens when available."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume 5 tokens
        assert bucket.try_consume(5) is True
        assert bucket.tokens == 5

        # Consume 3 more
        assert bucket.try_consume(3) is True
        assert bucket.tokens == 2

    def test_token_bucket_consume_failure(self):
        """Test consuming tokens when insufficient."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Try to consume more than available
        assert bucket.try_consume(11) is False
        assert bucket.tokens == 10  # Unchanged

        # Consume all tokens
        assert bucket.try_consume(10) is True
        assert bucket.tokens == 0

        # Now can't consume any
        assert bucket.try_consume(1) is False
        assert bucket.tokens == 0

    def test_token_bucket_refill(self):
        """Test token refilling over time."""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)  # 5 tokens per second

        # Consume all tokens
        bucket.try_consume(10)
        assert bucket.tokens == 0

        # Wait 1 second
        time.sleep(1.0)
        bucket.refill()
        assert 4.5 <= bucket.tokens <= 5.5  # ~5 tokens refilled

        # Wait another second
        time.sleep(1.0)
        bucket.refill()
        assert 9.5 <= bucket.tokens <= 10  # Capped at capacity

    def test_token_bucket_fractional_tokens(self):
        """Test handling fractional token amounts."""
        bucket = TokenBucket(capacity=10, refill_rate=0.5)  # 0.5 tokens per second

        bucket.try_consume(10)
        time.sleep(0.5)  # Should refill 0.25 tokens
        bucket.refill()

        assert 0.2 <= bucket.tokens <= 0.3
        assert bucket.try_consume(1) is False  # Still not enough

    def test_token_bucket_time_until_available(self):
        """Test calculating time until tokens available."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens/sec

        bucket.tokens = 0

        # Need 1 token, at 2 tokens/sec = 0.5 seconds
        wait_time = bucket.time_until_tokens(1)
        assert 0.4 <= wait_time <= 0.6

        # Need 5 tokens, at 2 tokens/sec = 2.5 seconds
        wait_time = bucket.time_until_tokens(5)
        assert 2.4 <= wait_time <= 2.6

        # Need more than capacity
        wait_time = bucket.time_until_tokens(15)
        assert wait_time == float("inf")  # Never available

    @pytest.mark.asyncio
    async def test_token_bucket_async_wait(self):
        """Test async waiting for tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec

        # Consume all tokens
        bucket.try_consume(10)

        # Wait for 1 token to be available
        start = asyncio.get_event_loop().time()
        await bucket.wait_for_tokens(1)
        elapsed = asyncio.get_event_loop().time() - start

        assert 0.08 <= elapsed <= 0.12  # ~0.1 seconds
        assert bucket.try_consume(1) is True


class TestSlidingWindow:
    """Unit tests for Sliding Window rate limiting."""

    def test_sliding_window_initialization(self):
        """Test Sliding Window initialization."""
        window = SlidingWindow(
            window_size=60,  # 60 seconds
            max_requests=100,
        )
        assert window.window_size == 60
        assert window.max_requests == 100
        assert len(window.requests) == 0

    def test_sliding_window_allow_requests(self):
        """Test allowing requests within limit."""
        window = SlidingWindow(window_size=60, max_requests=5)

        # First 5 requests should be allowed
        for i in range(5):
            assert window.try_request() is True
            time.sleep(0.01)  # Small delay to ensure different timestamps

        assert len(window.requests) == 5

    def test_sliding_window_deny_excess(self):
        """Test denying requests over limit."""
        window = SlidingWindow(window_size=60, max_requests=3)

        # Fill the window
        for i in range(3):
            assert window.try_request() is True

        # Next request should be denied
        assert window.try_request() is False
        assert len(window.requests) == 3  # No new request added

    def test_sliding_window_cleanup(self):
        """Test removing old requests from window."""
        window = SlidingWindow(window_size=1, max_requests=3)  # 1 second window

        # Add 3 requests
        for i in range(3):
            window.try_request()

        # Should be at limit
        assert window.try_request() is False

        # Wait for window to slide
        time.sleep(1.1)

        # Old requests should be cleaned up
        window.cleanup()
        assert len(window.requests) == 0

        # Can make new requests
        assert window.try_request() is True

    def test_sliding_window_request_rate(self):
        """Test calculating current request rate."""
        window = SlidingWindow(window_size=60, max_requests=100)

        # Add 30 requests
        for i in range(30):
            window.try_request()

        rate = window.get_request_rate()
        assert rate == 30  # 30 requests in current window

        # Simulate half the requests being old
        half = len(window.requests) // 2
        old_time = datetime.utcnow() - timedelta(seconds=61)
        for i in range(half):
            window.requests[i] = old_time

        window.cleanup()
        rate = window.get_request_rate()
        assert rate == 15  # Only recent requests count

    def test_sliding_window_time_until_available(self):
        """Test calculating time until slot available."""
        window = SlidingWindow(window_size=10, max_requests=3)

        # Fill the window
        now = datetime.utcnow()
        window.requests = [
            now - timedelta(seconds=8),  # 8 seconds old
            now - timedelta(seconds=5),  # 5 seconds old
            now - timedelta(seconds=2),  # 2 seconds old
        ]

        # Oldest request will expire in 2 seconds (10 - 8)
        wait_time = window.time_until_slot()
        assert 1.5 <= wait_time <= 2.5


class TestRateLimiter:
    """Unit tests for main RateLimiter class."""

    def test_rate_limiter_with_token_bucket(self):
        """Test RateLimiter using Token Bucket strategy."""
        config = RateLimitConfig(
            strategy="token_bucket",
            capacity=10,
            refill_rate=1.0,
        )
        limiter = RateLimiter(config)

        assert isinstance(limiter.strategy, TokenBucket)
        assert limiter.is_allowed() is True

    def test_rate_limiter_with_sliding_window(self):
        """Test RateLimiter using Sliding Window strategy."""
        config = RateLimitConfig(
            strategy="sliding_window",
            window_size=60,
            max_requests=100,
        )
        limiter = RateLimiter(config)

        assert isinstance(limiter.strategy, SlidingWindow)
        assert limiter.is_allowed() is True

    def test_rate_limiter_per_endpoint(self):
        """Test separate rate limits per endpoint."""
        config = RateLimitConfig(
            strategy="token_bucket",
            capacity=5,
            refill_rate=1.0,
            per_endpoint=True,
        )
        limiter = RateLimiter(config)

        # Different endpoints have separate limits
        for i in range(5):
            assert limiter.is_allowed(endpoint="/users") is True

        for i in range(5):
            assert limiter.is_allowed(endpoint="/posts") is True

        # Each endpoint exhausted separately
        assert limiter.is_allowed(endpoint="/users") is False
        assert limiter.is_allowed(endpoint="/posts") is False

    def test_rate_limiter_global(self):
        """Test global rate limit across all endpoints."""
        config = RateLimitConfig(
            strategy="token_bucket",
            capacity=5,
            refill_rate=1.0,
            per_endpoint=False,
        )
        limiter = RateLimiter(config)

        # Share the same limit
        for i in range(3):
            assert limiter.is_allowed(endpoint="/users") is True

        for i in range(2):
            assert limiter.is_allowed(endpoint="/posts") is True

        # Global limit exhausted
        assert limiter.is_allowed(endpoint="/users") is False
        assert limiter.is_allowed(endpoint="/posts") is False

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_for_capacity(self):
        """Test waiting for rate limit capacity."""
        config = RateLimitConfig(
            strategy="token_bucket",
            capacity=2,
            refill_rate=10.0,  # Fast refill for testing
        )
        limiter = RateLimiter(config)

        # Exhaust capacity
        limiter.consume(2)

        # Wait for capacity
        start = asyncio.get_event_loop().time()
        await limiter.wait_for_capacity(1)
        elapsed = asyncio.get_event_loop().time() - start

        assert 0.08 <= elapsed <= 0.12  # ~0.1 seconds for 1 token
        assert limiter.is_allowed() is True

    def test_rate_limiter_update_from_headers(self):
        """Test updating rate limit from response headers."""
        config = RateLimitConfig(
            strategy="token_bucket",
            capacity=1000,
            refill_rate=10.0,
        )
        limiter = RateLimiter(config)

        # Simulate response headers
        headers = {
            "X-RateLimit-Limit": "1000",
            "X-RateLimit-Remaining": "450",
            "X-RateLimit-Reset": str(int(time.time()) + 300),
        }

        limiter.update_from_headers(headers)

        # Should update internal state
        assert limiter.get_remaining() == 450
        assert limiter.get_limit() == 1000

    def test_rate_limit_exceeded_exception(self):
        """Test RateLimitExceeded exception."""
        exc = RateLimitExceeded(
            message="Rate limit exceeded",
            retry_after=60,
            limit=1000,
            remaining=0,
            reset_time=datetime.utcnow() + timedelta(minutes=1),
        )

        assert str(exc) == "Rate limit exceeded"
        assert exc.retry_after == 60
        assert exc.limit == 1000
        assert exc.remaining == 0


class TestAdaptiveRateLimiting:
    """Unit tests for adaptive rate limiting."""

    def test_adaptive_rate_limit_backoff(self):
        """Test adaptive rate limiting backs off on errors."""
        limiter = adaptive_rate_limit()

        # Simulate successful requests
        for i in range(10):
            limiter.record_success()

        initial_rate = limiter.get_current_rate()

        # Simulate rate limit errors
        for i in range(5):
            limiter.record_rate_limit()

        reduced_rate = limiter.get_current_rate()
        assert reduced_rate < initial_rate  # Should back off

    def test_adaptive_rate_limit_recovery(self):
        """Test adaptive rate limiting recovers after success."""
        limiter = adaptive_rate_limit()

        # Reduce rate through errors
        for i in range(5):
            limiter.record_rate_limit()

        low_rate = limiter.get_current_rate()

        # Successful requests should increase rate
        for i in range(20):
            limiter.record_success()
            time.sleep(0.01)

        recovered_rate = limiter.get_current_rate()
        assert recovered_rate > low_rate  # Should recover

    def test_adaptive_rate_limit_circuit_breaker(self):
        """Test circuit breaker pattern in adaptive limiting."""
        limiter = adaptive_rate_limit(circuit_breaker_threshold=3)

        # Trigger circuit breaker with consecutive failures
        for i in range(3):
            limiter.record_rate_limit()

        assert limiter.is_circuit_open() is True
        assert limiter.is_allowed() is False  # Circuit open, deny all

        # Wait for circuit to half-open
        time.sleep(limiter.circuit_reset_time)
        assert limiter.is_circuit_half_open() is True

        # Success should close circuit
        limiter.record_success()
        assert limiter.is_circuit_open() is False


class TestRequestMetadata:
    """Unit tests for request metadata tracking."""

    def test_request_metadata_creation(self):
        """Test creating request metadata."""
        metadata = RequestMetadata(
            endpoint="/users",
            method="GET",
            timestamp=datetime.utcnow(),
            response_time=0.5,
            status_code=200,
        )

        assert metadata.endpoint == "/users"
        assert metadata.method == "GET"
        assert metadata.response_time == 0.5
        assert metadata.status_code == 200

    def test_request_metadata_categorization(self):
        """Test categorizing requests by endpoint."""
        metadata_list = [
            RequestMetadata("/users", "GET", datetime.utcnow(), 0.1, 200),
            RequestMetadata("/users", "POST", datetime.utcnow(), 0.2, 201),
            RequestMetadata("/posts", "GET", datetime.utcnow(), 0.15, 200),
            RequestMetadata("/users", "GET", datetime.utcnow(), 0.1, 200),
        ]

        by_endpoint = RequestMetadata.categorize_by_endpoint(metadata_list)
        assert len(by_endpoint["/users"]) == 3
        assert len(by_endpoint["/posts"]) == 1

    def test_request_metadata_statistics(self):
        """Test calculating request statistics."""
        metadata_list = [
            RequestMetadata("/api", "GET", datetime.utcnow(), 0.1, 200),
            RequestMetadata("/api", "GET", datetime.utcnow(), 0.2, 200),
            RequestMetadata("/api", "GET", datetime.utcnow(), 0.3, 429),
            RequestMetadata("/api", "GET", datetime.utcnow(), 0.15, 200),
        ]

        stats = RequestMetadata.calculate_stats(metadata_list)
        assert stats["total_requests"] == 4
        assert stats["success_rate"] == 0.75  # 3/4 successful
        assert stats["avg_response_time"] == 0.1875  # Average of all
        assert stats["rate_limited"] == 1  # One 429
