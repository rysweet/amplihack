"""Tests for retry logic and exponential backoff - TDD approach.

Focus on retry mechanism, backoff calculations, and retry conditions.
"""

import asyncio
import time
from datetime import datetime, timedelta

import pytest

from amplihack.api_client.retry import (
    ExponentialBackoff,
    FixedBackoff,
    LinearBackoff,
    RetryDecision,
    RetryHandler,
    RetryState,
    calculate_retry_after,
    should_retry_exception,
    should_retry_status,
)


class TestRetryState:
    """Unit tests for RetryState tracking."""

    def test_retry_state_initial(self):
        """Test initial retry state."""
        state = RetryState(max_attempts=3)
        assert state.attempt == 0
        assert state.max_attempts == 3
        assert state.total_delay == 0.0
        assert state.last_exception is None
        assert state.last_status_code is None
        assert state.is_exhausted is False

    def test_retry_state_increment(self):
        """Test incrementing retry state."""
        state = RetryState(max_attempts=3)

        state.increment(delay=1.0)
        assert state.attempt == 1
        assert state.total_delay == 1.0
        assert state.is_exhausted is False

        state.increment(delay=2.0)
        assert state.attempt == 2
        assert state.total_delay == 3.0
        assert state.is_exhausted is False

        state.increment(delay=4.0)
        assert state.attempt == 3
        assert state.total_delay == 7.0
        assert state.is_exhausted is True  # Reached max

    def test_retry_state_record_failure(self):
        """Test recording failure details."""
        state = RetryState(max_attempts=3)

        # Record exception
        exc = ConnectionError("Connection failed")
        state.record_failure(exception=exc)
        assert state.last_exception == exc
        assert state.last_status_code is None

        # Record status code
        state.record_failure(status_code=503)
        assert state.last_exception == exc  # Preserved
        assert state.last_status_code == 503

    def test_retry_state_reset(self):
        """Test resetting retry state."""
        state = RetryState(max_attempts=3)
        state.increment(delay=1.0)
        state.record_failure(status_code=500)

        state.reset()
        assert state.attempt == 0
        assert state.total_delay == 0.0
        assert state.last_exception is None
        assert state.last_status_code is None


class TestBackoffStrategies:
    """Unit tests for different backoff strategies."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            multiplier=2.0,
            max_delay=100.0,
        )

        # Exponential growth: 1, 2, 4, 8, 16...
        assert backoff.calculate(0) == 1.0
        assert backoff.calculate(1) == 2.0
        assert backoff.calculate(2) == 4.0
        assert backoff.calculate(3) == 8.0
        assert backoff.calculate(4) == 16.0

        # Max delay cap
        assert backoff.calculate(10) == 100.0  # Would be 1024, capped at 100

    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter."""
        backoff = ExponentialBackoff(
            base_delay=1.0,
            multiplier=2.0,
            max_delay=100.0,
            jitter=True,
        )

        # With jitter, delay should vary
        delays = [backoff.calculate(2) for _ in range(10)]
        assert min(delays) >= 0.0  # Jitter reduces delay
        assert max(delays) <= 4.0  # Base delay for attempt 2
        assert len(set(delays)) > 1  # Should have variation

    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        backoff = LinearBackoff(
            base_delay=1.0,
            increment=0.5,
            max_delay=5.0,
        )

        # Linear growth: 1, 1.5, 2, 2.5, 3...
        assert backoff.calculate(0) == 1.0
        assert backoff.calculate(1) == 1.5
        assert backoff.calculate(2) == 2.0
        assert backoff.calculate(3) == 2.5
        assert backoff.calculate(4) == 3.0

        # Max delay cap
        assert backoff.calculate(20) == 5.0  # Capped

    def test_fixed_backoff(self):
        """Test fixed backoff (constant delay)."""
        backoff = FixedBackoff(delay=2.0)

        # Always same delay
        assert backoff.calculate(0) == 2.0
        assert backoff.calculate(1) == 2.0
        assert backoff.calculate(10) == 2.0
        assert backoff.calculate(100) == 2.0


class TestRetryDecision:
    """Unit tests for retry decision logic."""

    def test_retry_decision_retry(self):
        """Test positive retry decision."""
        decision = RetryDecision(
            should_retry=True,
            delay=2.0,
            reason="Transient error",
        )
        assert decision.should_retry is True
        assert decision.delay == 2.0
        assert decision.reason == "Transient error"

    def test_retry_decision_stop(self):
        """Test negative retry decision."""
        decision = RetryDecision(
            should_retry=False,
            delay=0.0,
            reason="Non-retryable error",
        )
        assert decision.should_retry is False
        assert decision.delay == 0.0
        assert decision.reason == "Non-retryable error"

    def test_retry_decision_with_override(self):
        """Test retry decision with delay override."""
        decision = RetryDecision(
            should_retry=True,
            delay=5.0,  # From backoff
            reason="Rate limited",
            delay_override=60.0,  # From Retry-After header
        )
        assert decision.should_retry is True
        assert decision.effective_delay == 60.0  # Uses override
        assert decision.reason == "Rate limited"


class TestRetryConditions:
    """Unit tests for retry condition checks."""

    def test_should_retry_status_defaults(self):
        """Test default retryable status codes."""
        # Retryable by default
        assert should_retry_status(429) is True  # Rate limit
        assert should_retry_status(500) is True  # Server error
        assert should_retry_status(502) is True  # Bad gateway
        assert should_retry_status(503) is True  # Service unavailable
        assert should_retry_status(504) is True  # Gateway timeout

        # Not retryable by default
        assert should_retry_status(200) is False  # Success
        assert should_retry_status(400) is False  # Bad request
        assert should_retry_status(401) is False  # Unauthorized
        assert should_retry_status(404) is False  # Not found

    def test_should_retry_status_custom(self):
        """Test custom retryable status codes."""
        custom_codes = {500, 503}  # Only these two

        assert should_retry_status(500, custom_codes) is True
        assert should_retry_status(503, custom_codes) is True
        assert should_retry_status(429, custom_codes) is False  # Not in custom
        assert should_retry_status(502, custom_codes) is False  # Not in custom

    def test_should_retry_exception_defaults(self):
        """Test default retryable exceptions."""
        # Retryable exceptions
        assert should_retry_exception(TimeoutError()) is True
        assert should_retry_exception(ConnectionError()) is True
        assert should_retry_exception(ConnectionResetError()) is True
        assert should_retry_exception(BrokenPipeError()) is True
        assert should_retry_exception(OSError("Network unreachable")) is True

        # Not retryable
        assert should_retry_exception(ValueError()) is False
        assert should_retry_exception(TypeError()) is False
        assert should_retry_exception(KeyError()) is False

    def test_calculate_retry_after(self):
        """Test calculating retry delay from headers."""
        # Retry-After as seconds
        headers = {"Retry-After": "60"}
        assert calculate_retry_after(headers) == 60.0

        # Retry-After as HTTP date (1 minute from now)
        future = datetime.utcnow() + timedelta(minutes=1)
        headers = {"Retry-After": future.strftime("%a, %d %b %Y %H:%M:%S GMT")}
        delay = calculate_retry_after(headers)
        assert 55 <= delay <= 65  # Allow some variance

        # No Retry-After header
        assert calculate_retry_after({}) is None
        assert calculate_retry_after({"Other": "header"}) is None


class TestRetryHandler:
    """Unit tests for RetryHandler orchestration."""

    def test_retry_handler_initialization(self):
        """Test RetryHandler initialization."""
        handler = RetryHandler(
            max_attempts=5,
            backoff_strategy=ExponentialBackoff(base_delay=1.0),
            retryable_statuses={429, 503},
            retryable_exceptions=(TimeoutError, ConnectionError),
        )
        assert handler.max_attempts == 5
        assert isinstance(handler.backoff_strategy, ExponentialBackoff)
        assert 429 in handler.retryable_statuses
        assert TimeoutError in handler.retryable_exceptions

    def test_retry_handler_should_retry_status(self):
        """Test RetryHandler decision for status codes."""
        handler = RetryHandler(
            max_attempts=3,
            retryable_statuses={500, 503},
        )

        state = RetryState(max_attempts=3)

        # Should retry on retryable status
        decision = handler.should_retry(state, status_code=503)
        assert decision.should_retry is True

        # Should not retry on non-retryable status
        decision = handler.should_retry(state, status_code=404)
        assert decision.should_retry is False

        # Should not retry when exhausted
        state.attempt = 3
        decision = handler.should_retry(state, status_code=503)
        assert decision.should_retry is False
        assert "exhausted" in decision.reason.lower()

    def test_retry_handler_should_retry_exception(self):
        """Test RetryHandler decision for exceptions."""
        handler = RetryHandler(
            max_attempts=3,
            retryable_exceptions=(ConnectionError,),
        )

        state = RetryState(max_attempts=3)

        # Should retry on retryable exception
        exc = ConnectionError("Failed")
        decision = handler.should_retry(state, exception=exc)
        assert decision.should_retry is True

        # Should not retry on non-retryable exception
        exc = ValueError("Bad value")
        decision = handler.should_retry(state, exception=exc)
        assert decision.should_retry is False

    def test_retry_handler_with_retry_after(self):
        """Test RetryHandler respects Retry-After header."""
        handler = RetryHandler(
            max_attempts=3,
            backoff_strategy=FixedBackoff(delay=1.0),
        )

        state = RetryState(max_attempts=3)
        headers = {"Retry-After": "30"}

        decision = handler.should_retry(state, status_code=429, headers=headers)
        assert decision.should_retry is True
        assert decision.effective_delay == 30.0  # Uses Retry-After

    @pytest.mark.asyncio
    async def test_retry_handler_execute_success(self):
        """Test RetryHandler executing successful request."""
        handler = RetryHandler(max_attempts=3)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return {"success": True}

        result = await handler.execute(operation)
        assert result == {"success": True}
        assert call_count == 1  # No retries needed

    @pytest.mark.asyncio
    async def test_retry_handler_execute_with_retries(self):
        """Test RetryHandler retrying transient failures."""
        handler = RetryHandler(
            max_attempts=3,
            backoff_strategy=FixedBackoff(delay=0.01),
        )

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return {"success": True}

        result = await handler.execute(operation)
        assert result == {"success": True}
        assert call_count == 3  # Failed twice, succeeded on third

    @pytest.mark.asyncio
    async def test_retry_handler_execute_exhausted(self):
        """Test RetryHandler exhausting retries."""
        handler = RetryHandler(
            max_attempts=2,
            backoff_strategy=FixedBackoff(delay=0.01),
        )

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            await handler.execute(operation)

        assert call_count == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_retry_handler_execute_non_retryable(self):
        """Test RetryHandler not retrying non-retryable errors."""
        handler = RetryHandler(
            max_attempts=3,
            retryable_exceptions=(ConnectionError,),
        )

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable")

        with pytest.raises(ValueError):
            await handler.execute(operation)

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_retry_handler_with_callback(self):
        """Test RetryHandler with retry callback."""
        handler = RetryHandler(max_attempts=3)

        retry_attempts = []

        def on_retry(state: RetryState, decision: RetryDecision):
            retry_attempts.append(
                {
                    "attempt": state.attempt,
                    "delay": decision.delay,
                    "reason": decision.reason,
                }
            )

        handler.on_retry = on_retry

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Fail")
            return "success"

        result = await handler.execute(operation)
        assert result == "success"
        assert len(retry_attempts) == 2  # Two retries
        assert retry_attempts[0]["attempt"] == 1
        assert retry_attempts[1]["attempt"] == 2


class TestRetryIntegration:
    """Integration tests for complete retry scenarios."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test actual timing of exponential backoff."""
        handler = RetryHandler(
            max_attempts=3,
            backoff_strategy=ExponentialBackoff(
                base_delay=0.1,
                multiplier=2.0,
            ),
        )

        timestamps: list[float] = []

        async def operation():
            timestamps.append(time.time())
            if len(timestamps) < 3:
                raise ConnectionError("Fail")
            return "success"

        start = time.time()
        result = await handler.execute(operation)
        total_time = time.time() - start

        assert result == "success"
        assert len(timestamps) == 3

        # Verify delays (allowing for execution time)
        delay1 = timestamps[1] - timestamps[0]
        delay2 = timestamps[2] - timestamps[1]

        assert 0.08 <= delay1 <= 0.12  # ~0.1s
        assert 0.18 <= delay2 <= 0.22  # ~0.2s
        assert total_time >= 0.3  # At least sum of delays

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test handling rate limits with Retry-After."""
        handler = RetryHandler(
            max_attempts=3,
            retryable_statuses={429},
        )

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate rate limit response
                error = Exception("Rate limited")
                error.status_code = 429
                error.headers = {"Retry-After": "0.2"}
                raise error
            return "success"

        # Custom error handler to extract status and headers
        async def wrapped_operation():
            try:
                return await operation()
            except Exception as e:
                if hasattr(e, "status_code") and hasattr(e, "headers"):
                    state = RetryState(max_attempts=3)
                    decision = handler.should_retry(
                        state,
                        status_code=e.status_code,
                        headers=e.headers,
                    )
                    if decision.should_retry:
                        await asyncio.sleep(decision.effective_delay)
                        return await operation()
                raise

        start = time.time()
        result = await wrapped_operation()
        elapsed = time.time() - start

        assert result == "success"
        assert call_count == 2
        assert elapsed >= 0.18  # Waited for Retry-After

    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """Test multiple concurrent operations with retries."""
        handler = RetryHandler(
            max_attempts=2,
            backoff_strategy=FixedBackoff(delay=0.01),
        )

        results = []

        async def operation(task_id: int):
            # First attempt fails for all
            if len(results) < 3:
                raise ConnectionError(f"Task {task_id} failed")
            return f"Task {task_id} success"

        # Run 3 operations concurrently
        tasks = [handler.execute(lambda: operation(i)) for i in range(3)]

        with pytest.raises(ConnectionError):
            # All should fail (max 2 attempts, need 3)
            await asyncio.gather(*tasks)

        # Now with enough retries
        handler.max_attempts = 4
        results = []
        tasks = [handler.execute(lambda: operation(i)) for i in range(3)]
        completed = await asyncio.gather(*tasks)

        assert len(completed) == 3
        assert all("success" in r for r in completed)
