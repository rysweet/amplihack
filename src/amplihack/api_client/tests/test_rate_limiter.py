"""Unit tests for rate limiting with Retry-After header support.

Tests RateLimiter class and RateLimitState dataclass.

Testing coverage:
- Rate limit state tracking
- check_rate_limit() with blocked/unblocked endpoints
- record_rate_limit() with consecutive 429s
- clear_rate_limit() after success
- parse_retry_after() with numeric and HTTP-date formats
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from email.utils import format_datetime
from unittest.mock import patch

import pytest

from amplihack.api_client.rate_limiter import RateLimiter, RateLimitState


class TestRateLimitState:
    """Tests for RateLimitState dataclass."""

    def test_default_values(self):
        """Default state should be not limited."""
        state = RateLimitState()
        assert state.is_limited is False
        assert state.retry_after == 0
        assert state.blocked_until == 0
        assert state.consecutive_429s == 0

    def test_custom_values(self):
        """Should accept custom values."""
        state = RateLimitState(
            is_limited=True,
            retry_after=60,
            blocked_until=time.time() + 60,
            consecutive_429s=3,
        )
        assert state.is_limited is True
        assert state.retry_after == 60
        assert state.consecutive_429s == 3


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create limiter with default settings."""
        return RateLimiter(default_retry_after=60)

    @pytest.mark.asyncio
    async def test_new_endpoint_not_limited(self, limiter):
        """New endpoint should not be rate limited."""
        result = await limiter.check_rate_limit("https://api.example.com/users")
        assert result is None

    @pytest.mark.asyncio
    async def test_record_rate_limit_basic(self, limiter):
        """Recording rate limit should return wait time."""
        wait_time = await limiter.record_rate_limit("https://api.example.com/users", retry_after=30)
        assert wait_time == 30

    @pytest.mark.asyncio
    async def test_record_rate_limit_uses_default(self, limiter):
        """Should use default retry_after when not provided."""
        wait_time = await limiter.record_rate_limit("https://api.example.com/users")
        assert wait_time == 60  # Default

    @pytest.mark.asyncio
    async def test_check_rate_limit_returns_wait_time(self, limiter):
        """After recording, should return remaining wait time."""
        # Record rate limit
        await limiter.record_rate_limit("https://api.example.com/users", retry_after=30)

        # Check should return remaining time
        wait_time = await limiter.check_rate_limit("https://api.example.com/users")
        assert wait_time is not None
        assert 0 < wait_time <= 30

    @pytest.mark.asyncio
    async def test_check_rate_limit_after_expiry(self, limiter):
        """After block expires, should return None."""
        # Mock time to test expiry
        with patch("amplihack.api_client.rate_limiter.time.time") as mock_time:
            # Initial time when recording
            mock_time.return_value = 1000.0
            await limiter.record_rate_limit("https://api.example.com/users", retry_after=30)

            # Time after expiry
            mock_time.return_value = 1050.0  # 50 seconds later (> 30)
            result = await limiter.check_rate_limit("https://api.example.com/users")
            assert result is None

    @pytest.mark.asyncio
    async def test_consecutive_429s_increase_wait_time(self, limiter):
        """Consecutive 429s should increase wait time."""
        endpoint = "https://api.example.com/users"

        # First 429
        wait1 = await limiter.record_rate_limit(endpoint, retry_after=30)
        assert wait1 == 30

        # Second consecutive 429
        wait2 = await limiter.record_rate_limit(endpoint, retry_after=30)
        assert wait2 == 60  # 30 * 2

        # Third consecutive 429
        wait3 = await limiter.record_rate_limit(endpoint, retry_after=30)
        assert wait3 == 90  # 30 * 3

    @pytest.mark.asyncio
    async def test_wait_time_capped_at_one_hour(self, limiter):
        """Wait time should be capped at 1 hour (3600 seconds)."""
        endpoint = "https://api.example.com/users"

        # Record many consecutive 429s
        for i in range(100):
            wait = await limiter.record_rate_limit(endpoint, retry_after=100)

        assert wait <= 3600

    @pytest.mark.asyncio
    async def test_clear_rate_limit_resets_state(self, limiter):
        """Clearing should reset all state."""
        endpoint = "https://api.example.com/users"

        # Record rate limit
        await limiter.record_rate_limit(endpoint, retry_after=30)
        await limiter.record_rate_limit(endpoint, retry_after=30)

        # Clear
        await limiter.clear_rate_limit(endpoint)

        # Should not be limited anymore
        result = await limiter.check_rate_limit(endpoint)
        assert result is None

        # Next 429 should start fresh (not consecutive)
        wait = await limiter.record_rate_limit(endpoint, retry_after=30)
        assert wait == 30  # Not multiplied

    @pytest.mark.asyncio
    async def test_different_endpoints_tracked_separately(self, limiter):
        """Different endpoints should have separate rate limit state."""
        endpoint1 = "https://api.example.com/users"
        endpoint2 = "https://api.example.com/posts"

        # Rate limit endpoint1
        await limiter.record_rate_limit(endpoint1, retry_after=30)

        # endpoint2 should not be limited
        result = await limiter.check_rate_limit(endpoint2)
        assert result is None


class TestParseRetryAfter:
    """Tests for parse_retry_after method."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        return RateLimiter()

    def test_numeric_seconds(self, limiter):
        """Should parse numeric seconds."""
        headers = {"Retry-After": "60"}
        result = limiter.parse_retry_after(headers)
        assert result == 60

    def test_numeric_seconds_lowercase(self, limiter):
        """Should handle lowercase header name."""
        headers = {"retry-after": "120"}
        result = limiter.parse_retry_after(headers)
        assert result == 120

    def test_http_date_format(self, limiter):
        """Should parse HTTP-date format."""
        # Create a date 60 seconds in the future
        future = datetime.now(UTC).replace(microsecond=0)
        future_ts = future.timestamp() + 60

        with patch("amplihack.api_client.rate_limiter.time.time", return_value=future_ts - 60):
            future_dt = datetime.fromtimestamp(future_ts, tz=UTC)
            http_date = format_datetime(future_dt, usegmt=True)
            headers = {"Retry-After": http_date}

            result = limiter.parse_retry_after(headers)
            assert result is not None
            # Should be approximately 60 seconds
            assert 55 <= result <= 65

    def test_missing_header(self, limiter):
        """Should return None if header missing."""
        headers = {"Content-Type": "application/json"}
        result = limiter.parse_retry_after(headers)
        assert result is None

    def test_empty_headers(self, limiter):
        """Should return None for empty headers."""
        result = limiter.parse_retry_after({})
        assert result is None

    def test_invalid_value(self, limiter):
        """Should return None for invalid value."""
        headers = {"Retry-After": "not-a-number"}
        result = limiter.parse_retry_after(headers)
        assert result is None

    def test_negative_numeric(self, limiter):
        """Should handle negative numeric values."""
        headers = {"Retry-After": "-30"}
        result = limiter.parse_retry_after(headers)
        assert result == -30  # Parsed as-is

    def test_zero_seconds(self, limiter):
        """Should handle zero seconds."""
        headers = {"Retry-After": "0"}
        result = limiter.parse_retry_after(headers)
        assert result == 0

    def test_http_date_in_past(self, limiter):
        """HTTP-date in past should return 0."""
        past = datetime.now(UTC).replace(microsecond=0)
        past_ts = past.timestamp() - 60  # 60 seconds ago

        with patch("amplihack.api_client.rate_limiter.time.time", return_value=past_ts + 60):
            past_dt = datetime.fromtimestamp(past_ts, tz=UTC)
            http_date = format_datetime(past_dt, usegmt=True)
            headers = {"Retry-After": http_date}

            result = limiter.parse_retry_after(headers)
            assert result == 0  # max(0, negative) = 0


class TestRateLimiterConcurrency:
    """Tests for thread-safety of RateLimiter."""

    @pytest.mark.asyncio
    async def test_concurrent_record_rate_limit(self):
        """Concurrent record calls should not corrupt state."""
        import asyncio

        limiter = RateLimiter()
        endpoint = "https://api.example.com/test"

        # Run 100 concurrent record calls
        async def record():
            await limiter.record_rate_limit(endpoint, retry_after=10)

        await asyncio.gather(*[record() for _ in range(100)])

        # State should be consistent
        state = limiter._state.get(endpoint)
        assert state is not None
        assert state.consecutive_429s == 100

    @pytest.mark.asyncio
    async def test_concurrent_check_and_record(self):
        """Concurrent check and record should not deadlock."""
        import asyncio

        limiter = RateLimiter()
        endpoint = "https://api.example.com/test"

        async def check_or_record(should_record: bool):
            if should_record:
                await limiter.record_rate_limit(endpoint)
            else:
                await limiter.check_rate_limit(endpoint)

        # Mix of check and record operations
        tasks = [check_or_record(i % 2 == 0) for i in range(100)]
        await asyncio.gather(*tasks)

        # Should complete without deadlock
