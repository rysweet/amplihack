"""
Unit tests for rate limiting functionality.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import time
import asyncio
from typing import Dict, Any, List

# Import the modules to be tested
from src.amplihack.auth.services import RateLimiter
from src.amplihack.auth.exceptions import RateLimitExceededError


class TestBasicRateLimiting:
    """Test basic rate limiting functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a basic rate limiter."""
        return RateLimiter(
            max_requests=10,
            window_size_seconds=60,
        )

    def test_rate_limit_allows_within_limit(self, rate_limiter):
        """Test requests are allowed within rate limit."""
        identifier = "user_123"

        for i in range(10):  # Within per-minute limit
            allowed = rate_limiter.check_rate_limit(identifier)
            assert allowed is True

    def test_rate_limit_blocks_exceeding_limit(self, rate_limiter):
        """Test requests are blocked when exceeding limit."""
        identifier = "user_123"

        # Use up the limit
        for i in range(10):
            rate_limiter.check_rate_limit(identifier)

        # Next request should be blocked
        allowed = rate_limiter.check_rate_limit(identifier)
        assert allowed is False

    def test_rate_limit_resets_after_window(self, rate_limiter):
        """Test rate limit resets after time window."""
        identifier = "user_123"

        # Use up the limit
        for i in range(10):
            rate_limiter.check_rate_limit(identifier)

        # Should be blocked
        assert rate_limiter.check_rate_limit(identifier) is False

        # Simulate time passing (mock time)
        with patch('time.time', return_value=time.time() + 61):
            # Should be allowed after window resets
            allowed = rate_limiter.check_rate_limit(identifier)
            assert allowed is True

    def test_rate_limit_tracks_per_identifier(self, rate_limiter):
        """Test rate limits are tracked separately per identifier."""
        # Use up limit for user_123
        for i in range(10):
            rate_limiter.check_rate_limit("user_123")

        # user_123 should be blocked
        assert rate_limiter.check_rate_limit("user_123") is False

        # user_456 should still be allowed
        assert rate_limiter.check_rate_limit("user_456") is True

    def test_get_remaining_requests(self, rate_limiter):
        """Test getting remaining requests count."""
        identifier = "user_123"

        # Initially should have full limit
        remaining = rate_limiter.get_remaining_requests(identifier)
        assert remaining == 10

        # Use some requests
        for i in range(3):
            rate_limiter.check_rate_limit(identifier)

        remaining = rate_limiter.get_remaining_requests(identifier)
        assert remaining == 7

    def test_get_reset_time(self, rate_limiter):
        """Test getting rate limit reset time."""
        identifier = "user_123"

        # Make a request
        rate_limiter.check_rate_limit(identifier)

        reset_time = rate_limiter.get_reset_time(identifier)
        assert reset_time is not None
        assert reset_time > datetime.now(timezone.utc)
        assert reset_time < datetime.now(timezone.utc) + timedelta(minutes=2)


class TestLoginRateLimiting:
    """Test login-specific rate limiting."""

    @pytest.fixture
    def login_limiter(self):
        """Create a login rate limiter with strict limits."""
        config = RateLimitConfig(
            max_login_attempts=5,
            lockout_duration_minutes=30,
            progressive_delay=True,
        )
        return LoginRateLimiter(config=config)

    def test_login_attempts_tracking(self, login_limiter):
        """Test tracking of failed login attempts."""
        identifier = "user@example.com"

        for i in range(4):
            allowed = login_limiter.check_login_allowed(identifier)
            assert allowed is True
            login_limiter.record_failed_attempt(identifier)

        # 5th attempt should still be allowed
        allowed = login_limiter.check_login_allowed(identifier)
        assert allowed is True
        login_limiter.record_failed_attempt(identifier)

        # 6th attempt should be blocked (lockout)
        allowed = login_limiter.check_login_allowed(identifier)
        assert allowed is False

    def test_successful_login_resets_attempts(self, login_limiter):
        """Test successful login resets failed attempt counter."""
        identifier = "user@example.com"

        # Record some failed attempts
        for i in range(3):
            login_limiter.record_failed_attempt(identifier)

        attempts = login_limiter.get_failed_attempts(identifier)
        assert attempts == 3

        # Successful login resets counter
        login_limiter.record_successful_login(identifier)

        attempts = login_limiter.get_failed_attempts(identifier)
        assert attempts == 0

    def test_progressive_delay(self, login_limiter):
        """Test progressive delay increases with failed attempts."""
        identifier = "user@example.com"

        delays = []
        for i in range(5):
            delay = login_limiter.get_delay_seconds(identifier)
            delays.append(delay)
            login_limiter.record_failed_attempt(identifier)

        # Delays should increase progressively
        assert delays[0] == 0  # No delay initially
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
        assert delays[3] > delays[2]
        assert delays[4] > delays[3]

    def test_lockout_duration(self, login_limiter):
        """Test account lockout duration."""
        identifier = "user@example.com"

        # Max out failed attempts
        for i in range(5):
            login_limiter.record_failed_attempt(identifier)

        # Should be locked out
        assert login_limiter.check_login_allowed(identifier) is False

        lockout_end = login_limiter.get_lockout_end_time(identifier)
        assert lockout_end is not None
        assert lockout_end > datetime.now(timezone.utc)
        assert lockout_end < datetime.now(timezone.utc) + timedelta(minutes=31)

    def test_ip_based_limiting(self, login_limiter):
        """Test IP-based login rate limiting."""
        ip_address = "192.168.1.1"

        # Multiple users from same IP
        for user_num in range(10):
            email = f"user{user_num}@example.com"
            allowed = login_limiter.check_login_allowed_for_ip(ip_address)

            if user_num < 10:  # IP limit is 10 per minute
                assert allowed is True
            else:
                assert allowed is False

    def test_combined_user_and_ip_limiting(self, login_limiter):
        """Test combined user and IP rate limiting."""
        email = "user@example.com"
        ip_address = "192.168.1.1"

        # Should check both user and IP limits
        user_allowed = login_limiter.check_login_allowed(email)
        ip_allowed = login_limiter.check_login_allowed_for_ip(ip_address)

        combined_allowed = login_limiter.check_combined_limits(email, ip_address)
        assert combined_allowed == (user_allowed and ip_allowed)


class TestTokenRateLimiting:
    """Test token generation/validation rate limiting."""

    @pytest.fixture
    def token_limiter(self):
        """Create a token rate limiter."""
        config = RateLimitConfig(
            max_tokens_per_hour=100,
            max_refresh_per_hour=20,
            max_validation_per_second=10,
        )
        return TokenRateLimiter(config=config)

    def test_token_generation_limit(self, token_limiter):
        """Test rate limiting for token generation."""
        user_id = "user_123"

        # Should allow initial tokens
        for i in range(5):
            allowed = token_limiter.check_generation_allowed(user_id)
            assert allowed is True

        # Track generation count
        count = token_limiter.get_generation_count(user_id)
        assert count == 5

    def test_token_refresh_limit(self, token_limiter):
        """Test separate rate limit for token refresh."""
        user_id = "user_123"

        # Refresh has lower limit than generation
        for i in range(20):
            allowed = token_limiter.check_refresh_allowed(user_id)
            assert allowed is True

        # 21st refresh should be blocked
        allowed = token_limiter.check_refresh_allowed(user_id)
        assert allowed is False

    def test_token_validation_burst_limit(self, token_limiter):
        """Test burst limiting for token validation."""
        # Validation has per-second burst limit
        for i in range(10):
            allowed = token_limiter.check_validation_allowed()
            assert allowed is True

        # 11th validation in same second should be blocked
        allowed = token_limiter.check_validation_allowed()
        assert allowed is False

        # After 1 second, should allow again
        time.sleep(1.1)
        allowed = token_limiter.check_validation_allowed()
        assert allowed is True


class TestAPIRateLimiting:
    """Test API endpoint rate limiting."""

    @pytest.fixture
    def api_limiter(self):
        """Create an API rate limiter."""
        config = RateLimitConfig(
            default_requests_per_minute=60,
            default_requests_per_hour=1000,
            endpoint_limits={
                "/api/auth/login": {"per_minute": 5, "per_hour": 20},
                "/api/auth/register": {"per_minute": 3, "per_hour": 10},
                "/api/users/*": {"per_minute": 30, "per_hour": 500},
            },
        )
        return APIRateLimiter(config=config)

    def test_endpoint_specific_limits(self, api_limiter):
        """Test endpoint-specific rate limits."""
        user_id = "user_123"

        # Login endpoint has strict limit (5 per minute)
        for i in range(5):
            allowed = api_limiter.check_request_allowed(
                user_id, "/api/auth/login"
            )
            assert allowed is True

        # 6th request should be blocked
        allowed = api_limiter.check_request_allowed(user_id, "/api/auth/login")
        assert allowed is False

        # But other endpoints should still work
        allowed = api_limiter.check_request_allowed(user_id, "/api/users/profile")
        assert allowed is True

    def test_wildcard_endpoint_matching(self, api_limiter):
        """Test wildcard pattern matching for endpoints."""
        user_id = "user_123"

        # These should all match /api/users/* pattern
        endpoints = [
            "/api/users/profile",
            "/api/users/123",
            "/api/users/123/posts",
        ]

        for endpoint in endpoints:
            allowed = api_limiter.check_request_allowed(user_id, endpoint)
            assert allowed is True

            # Should use the wildcard limit (30 per minute)
            limit = api_limiter.get_endpoint_limit(endpoint)
            assert limit["per_minute"] == 30

    def test_default_limits_for_unknown_endpoints(self, api_limiter):
        """Test default limits apply to unknown endpoints."""
        user_id = "user_123"
        unknown_endpoint = "/api/unknown/endpoint"

        # Should use default limits
        limit = api_limiter.get_endpoint_limit(unknown_endpoint)
        assert limit["per_minute"] == 60
        assert limit["per_hour"] == 1000

        allowed = api_limiter.check_request_allowed(user_id, unknown_endpoint)
        assert allowed is True

    def test_rate_limit_headers(self, api_limiter):
        """Test rate limit information headers."""
        user_id = "user_123"
        endpoint = "/api/auth/login"

        # Make some requests
        for i in range(3):
            api_limiter.check_request_allowed(user_id, endpoint)

        headers = api_limiter.get_rate_limit_headers(user_id, endpoint)

        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "5"

        assert "X-RateLimit-Remaining" in headers
        assert headers["X-RateLimit-Remaining"] == "2"

        assert "X-RateLimit-Reset" in headers
        assert int(headers["X-RateLimit-Reset"]) > time.time()


class TestDistributedRateLimiting:
    """Test distributed rate limiting with Redis."""

    @pytest.fixture
    def redis_storage(self):
        """Create mock Redis storage."""
        return Mock(spec=RedisStorage)

    @pytest.fixture
    def distributed_limiter(self, redis_storage):
        """Create a distributed rate limiter."""
        config = RateLimitConfig(
            requests_per_minute=100,
            use_sliding_window=True,
        )
        return DistributedRateLimiter(config=config, storage=redis_storage)

    @pytest.mark.asyncio
    async def test_distributed_rate_limit(self, distributed_limiter, redis_storage):
        """Test rate limiting across distributed system."""
        identifier = "user_123"

        # Mock Redis responses
        redis_storage.increment.return_value = 5
        redis_storage.get_ttl.return_value = 45

        allowed = await distributed_limiter.check_rate_limit_async(identifier)
        assert allowed is True

        # Verify Redis was called
        redis_storage.increment.assert_called_with(
            f"rate_limit:{identifier}:minute",
            ttl=60,
        )

    @pytest.mark.asyncio
    async def test_sliding_window_algorithm(self, distributed_limiter):
        """Test sliding window rate limiting algorithm."""
        identifier = "user_123"

        # Sliding window provides smoother rate limiting
        current_window_key = f"rate_limit:{identifier}:current"
        previous_window_key = f"rate_limit:{identifier}:previous"

        with patch.object(distributed_limiter, 'get_sliding_window_count') as mock_count:
            mock_count.return_value = 50  # Half of limit

            allowed = await distributed_limiter.check_rate_limit_async(identifier)
            assert allowed is True

            # When count approaches limit
            mock_count.return_value = 99
            allowed = await distributed_limiter.check_rate_limit_async(identifier)
            assert allowed is True

            # When exceeds limit
            mock_count.return_value = 101
            allowed = await distributed_limiter.check_rate_limit_async(identifier)
            assert allowed is False

    @pytest.mark.asyncio
    async def test_redis_failure_handling(self, distributed_limiter, redis_storage):
        """Test graceful handling of Redis failures."""
        identifier = "user_123"

        # Simulate Redis connection failure
        redis_storage.increment.side_effect = ConnectionError("Redis unavailable")

        # Should fall back to allowing requests (fail open)
        # or use local cache (depending on configuration)
        allowed = await distributed_limiter.check_rate_limit_async(
            identifier,
            fail_open=True,
        )
        assert allowed is True

        # With fail_closed, should block on Redis failure
        allowed = await distributed_limiter.check_rate_limit_async(
            identifier,
            fail_open=False,
        )
        assert allowed is False

    def test_rate_limit_synchronization(self, distributed_limiter):
        """Test rate limit synchronization across instances."""
        identifier = "user_123"

        # Simulate multiple instances checking same user
        instance1 = DistributedRateLimiter(
            config=distributed_limiter.config,
            storage=distributed_limiter.storage,
        )
        instance2 = DistributedRateLimiter(
            config=distributed_limiter.config,
            storage=distributed_limiter.storage,
        )

        # Both instances should see same count
        count1 = instance1.get_current_count(identifier)
        count2 = instance2.get_current_count(identifier)
        assert count1 == count2