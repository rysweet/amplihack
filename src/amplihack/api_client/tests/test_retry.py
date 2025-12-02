"""Unit tests for retry logic with exponential backoff.

Tests calculate_delay() and retry_async() functions.

Testing coverage:
- Exponential backoff calculation
- Max delay capping
- Jitter application
- Retry execution with success
- Retry execution with exhausted attempts
- should_retry callback behavior
- on_retry callback invocation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.api_client.exceptions import RetryExhaustedError
from amplihack.api_client.models import RetryConfig
from amplihack.api_client.retry import calculate_delay, retry_async


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_first_attempt_returns_base_delay(self):
        """First attempt (0) should return base_delay."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter=0.0)
        delay = calculate_delay(attempt=0, config=config)
        assert delay == 1.0

    def test_exponential_backoff(self):
        """Delay should increase exponentially."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=0.0)

        # attempt 0: 1.0 * 2^0 = 1.0
        assert calculate_delay(0, config) == 1.0
        # attempt 1: 1.0 * 2^1 = 2.0
        assert calculate_delay(1, config) == 2.0
        # attempt 2: 1.0 * 2^2 = 4.0
        assert calculate_delay(2, config) == 4.0
        # attempt 3: 1.0 * 2^3 = 8.0
        assert calculate_delay(3, config) == 8.0

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, max_delay=5.0, jitter=0.0)

        # attempt 5 would be 32.0 without cap
        delay = calculate_delay(5, config)
        assert delay == 5.0

    def test_jitter_adds_randomness(self):
        """Jitter should add variance to delay."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=0.5)

        # With 50% jitter, delay should be between 0.5 and 1.5 for attempt 0
        delays = [calculate_delay(0, config) for _ in range(100)]

        # Should have some variance
        assert min(delays) < max(delays)
        # Should be in expected range (base * (1 - jitter) to base * (1 + jitter))
        assert all(0.5 <= d <= 1.5 for d in delays)

    def test_zero_jitter_deterministic(self):
        """Zero jitter should produce consistent results."""
        config = RetryConfig(base_delay=1.0, multiplier=2.0, jitter=0.0)

        delays = [calculate_delay(0, config) for _ in range(10)]
        assert all(d == 1.0 for d in delays)

    def test_negative_delay_prevented(self):
        """Delay should never be negative."""
        config = RetryConfig(base_delay=0.1, multiplier=1.0, jitter=0.5)

        # Even with high jitter, should not go negative
        delays = [calculate_delay(0, config) for _ in range(1000)]
        assert all(d >= 0 for d in delays)

    def test_custom_multiplier(self):
        """Custom multiplier should affect backoff rate."""
        config = RetryConfig(base_delay=1.0, multiplier=3.0, max_delay=1000.0, jitter=0.0)

        # attempt 0: 1.0 * 3^0 = 1.0
        assert calculate_delay(0, config) == 1.0
        # attempt 1: 1.0 * 3^1 = 3.0
        assert calculate_delay(1, config) == 3.0
        # attempt 2: 1.0 * 3^2 = 9.0
        assert calculate_delay(2, config) == 9.0


class TestRetryAsync:
    """Tests for retry_async function."""

    @pytest.fixture
    def fast_retry_config(self) -> RetryConfig:
        """Config with minimal delays for fast testing."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.001,  # 1ms
            multiplier=2.0,
            max_delay=0.01,
            jitter=0.0,
        )

    @pytest.mark.asyncio
    async def test_success_on_first_try(self, fast_retry_config):
        """Function that succeeds immediately should not retry."""
        func = AsyncMock(return_value="success")

        result = await retry_async(func, fast_retry_config)

        assert result == "success"
        assert func.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self, fast_retry_config):
        """Function should succeed after failures."""
        func = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])

        result = await retry_async(func, fast_retry_config)

        assert result == "success"
        assert func.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_raises_error(self, fast_retry_config):
        """Should raise RetryExhaustedError after max attempts."""
        func = AsyncMock(side_effect=Exception("always fails"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_async(func, fast_retry_config)

        assert exc_info.value.attempts == 3
        assert "always fails" in exc_info.value.last_error

    @pytest.mark.asyncio
    async def test_should_retry_callback_false_stops_retrying(self, fast_retry_config):
        """should_retry returning False should stop immediately."""
        func = AsyncMock(side_effect=ValueError("don't retry this"))
        should_retry = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="don't retry this"):
            await retry_async(func, fast_retry_config, should_retry=should_retry)

        assert func.call_count == 1  # No retries
        should_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_retry_callback_true_continues(self, fast_retry_config):
        """should_retry returning True should continue retrying."""
        func = AsyncMock(side_effect=[ValueError("retry this"), "success"])
        should_retry = MagicMock(return_value=True)

        result = await retry_async(func, fast_retry_config, should_retry=should_retry)

        assert result == "success"
        assert func.call_count == 2
        should_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_retry_callback_invoked(self, fast_retry_config):
        """on_retry callback should be called on each retry."""
        func = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        on_retry = MagicMock()

        await retry_async(func, fast_retry_config, on_retry=on_retry)

        assert on_retry.call_count == 2  # Called twice (before retries 2 and 3)

        # Check first call
        first_call = on_retry.call_args_list[0]
        assert isinstance(first_call[0][0], Exception)  # exception
        assert first_call[0][1] == 1  # attempt number
        assert isinstance(first_call[0][2], float)  # delay

    @pytest.mark.asyncio
    async def test_request_id_in_exhausted_error(self, fast_retry_config):
        """request_id should be included in RetryExhaustedError."""
        func = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_async(func, fast_retry_config, request_id="test-123")

        assert exc_info.value.request_id == "test-123"

    @pytest.mark.asyncio
    async def test_zero_max_attempts_fails_immediately(self):
        """With 0 max_attempts, should immediately raise."""
        config = RetryConfig(max_attempts=0, base_delay=0.001)
        func = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(RetryExhaustedError):
            await retry_async(func, config)

        assert func.call_count == 0

    @pytest.mark.asyncio
    async def test_single_attempt_no_retry(self):
        """With 1 max_attempt, should not retry on failure."""
        config = RetryConfig(max_attempts=1, base_delay=0.001)
        func = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_async(func, config)

        assert func.call_count == 1
        assert exc_info.value.attempts == 1

    @pytest.mark.asyncio
    async def test_delay_is_applied(self, fast_retry_config):
        """Should actually wait between retries."""
        func = AsyncMock(side_effect=[Exception("fail"), "success"])

        with patch(
            "amplihack.api_client.retry.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep:
            await retry_async(func, fast_retry_config)

            # Should have slept once before the retry
            assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_different_exception_types(self, fast_retry_config):
        """Should handle different exception types."""
        func = AsyncMock(
            side_effect=[
                ValueError("value error"),
                TypeError("type error"),
                "success",
            ]
        )

        result = await retry_async(func, fast_retry_config)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_last_error_captured(self, fast_retry_config):
        """Last error message should be captured in RetryExhaustedError."""
        func = AsyncMock(
            side_effect=[
                Exception("first error"),
                Exception("second error"),
                Exception("final error"),
            ]
        )

        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_async(func, fast_retry_config)

        assert "final error" in exc_info.value.last_error
