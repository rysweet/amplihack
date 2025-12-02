"""Tests for retry and rate limiting logic.

TDD tests - these will FAIL until resilience.py is implemented.

Testing:
- Exponential backoff retry logic
- Rate limit handling with Retry-After
- Retry configuration
- Retry decision logic
"""

import time
from unittest.mock import Mock, patch

import pytest


class TestRetryConfiguration:
    """Tests for retry configuration."""

    def test_default_retry_config(self):
        """RetryConfig has sensible defaults."""
        from api_client.resilience import RetryConfig

        config = RetryConfig()

        assert config.max_retries == 3
        assert config.initial_delay > 0
        assert config.max_delay > config.initial_delay
        assert config.exponential_base >= 2

    def test_custom_retry_config(self):
        """RetryConfig accepts custom values."""
        from api_client.resilience import RetryConfig

        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3,
        )

        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3

    def test_retry_config_validates_max_retries(self):
        """RetryConfig validates max_retries is non-negative."""
        from api_client.resilience import RetryConfig

        # Zero is valid (no retries)
        config = RetryConfig(max_retries=0)
        assert config.max_retries == 0

        # Negative is invalid
        with pytest.raises(ValueError, match="max_retries"):
            RetryConfig(max_retries=-1)

    def test_retry_config_validates_delays(self):
        """RetryConfig validates delay values are positive."""
        from api_client.resilience import RetryConfig

        with pytest.raises(ValueError, match="initial_delay"):
            RetryConfig(initial_delay=0)

        with pytest.raises(ValueError, match="max_delay"):
            RetryConfig(max_delay=0)

    def test_retry_config_validates_max_greater_than_initial(self):
        """RetryConfig validates max_delay >= initial_delay."""
        from api_client.resilience import RetryConfig

        with pytest.raises(ValueError, match="max_delay.*initial_delay"):
            RetryConfig(initial_delay=10, max_delay=5)


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_calculate_backoff_first_retry(self):
        """First retry uses initial delay."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, exponential_base=2)

        delay = calculate_backoff(attempt=1, config=config)

        assert delay == pytest.approx(1.0, rel=0.1)

    def test_calculate_backoff_second_retry(self):
        """Second retry doubles the delay."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, exponential_base=2)

        delay = calculate_backoff(attempt=2, config=config)

        assert delay == pytest.approx(2.0, rel=0.1)

    def test_calculate_backoff_third_retry(self):
        """Third retry quadruples the initial delay."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, exponential_base=2)

        delay = calculate_backoff(attempt=3, config=config)

        assert delay == pytest.approx(4.0, rel=0.1)

    def test_calculate_backoff_respects_max_delay(self):
        """Backoff is capped at max_delay."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, max_delay=5.0, exponential_base=2)

        # Attempt 10 would be 1 * 2^9 = 512, but should be capped at 5
        delay = calculate_backoff(attempt=10, config=config)

        assert delay <= 5.0

    def test_calculate_backoff_with_jitter(self):
        """Backoff includes jitter to prevent thundering herd."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, exponential_base=2, jitter=True)

        # Run multiple times to verify jitter adds randomness
        delays = [calculate_backoff(attempt=2, config=config) for _ in range(10)]

        # With jitter, delays should not all be identical
        unique_delays = set(round(d, 3) for d in delays)
        assert len(unique_delays) > 1, "Jitter should produce varying delays"

    def test_calculate_backoff_without_jitter(self):
        """Backoff without jitter is deterministic."""
        from api_client.resilience import RetryConfig, calculate_backoff

        config = RetryConfig(initial_delay=1.0, exponential_base=2, jitter=False)

        delays = [calculate_backoff(attempt=2, config=config) for _ in range(5)]

        # Without jitter, all delays should be identical
        assert all(d == delays[0] for d in delays)


class TestRetryDecision:
    """Tests for retry decision logic."""

    def test_should_retry_on_server_error(self):
        """Should retry on 5xx server errors."""
        from api_client.exceptions import ServerError
        from api_client.resilience import should_retry

        error = ServerError("Internal error", status_code=500)

        assert should_retry(error, attempt=1, max_retries=3) is True

    def test_should_retry_on_rate_limit(self):
        """Should retry on rate limit errors."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import should_retry

        error = RateLimitError("Rate limited", retry_after=60)

        assert should_retry(error, attempt=1, max_retries=3) is True

    def test_should_retry_on_connection_error(self):
        """Should retry on connection errors."""
        from api_client.exceptions import ConnectionError
        from api_client.resilience import should_retry

        error = ConnectionError("Connection failed")

        assert should_retry(error, attempt=1, max_retries=3) is True

    def test_should_retry_on_timeout(self):
        """Should retry on timeout errors."""
        from api_client.exceptions import TimeoutError
        from api_client.resilience import should_retry

        error = TimeoutError("Timed out")

        assert should_retry(error, attempt=1, max_retries=3) is True

    def test_should_not_retry_on_client_error(self):
        """Should NOT retry on 4xx client errors (except rate limit)."""
        from api_client.exceptions import ClientError
        from api_client.resilience import should_retry

        error = ClientError("Bad request", status_code=400)

        assert should_retry(error, attempt=1, max_retries=3) is False

    def test_should_not_retry_on_404(self):
        """Should NOT retry on 404 Not Found."""
        from api_client.exceptions import ClientError
        from api_client.resilience import should_retry

        error = ClientError("Not found", status_code=404)

        assert should_retry(error, attempt=1, max_retries=3) is False

    def test_should_not_retry_when_max_attempts_reached(self):
        """Should NOT retry when max attempts reached."""
        from api_client.exceptions import ServerError
        from api_client.resilience import should_retry

        error = ServerError("Error", status_code=500)

        assert should_retry(error, attempt=3, max_retries=3) is False

    def test_should_not_retry_when_retries_disabled(self):
        """Should NOT retry when max_retries is 0."""
        from api_client.exceptions import ServerError
        from api_client.resilience import should_retry

        error = ServerError("Error", status_code=500)

        assert should_retry(error, attempt=1, max_retries=0) is False

    def test_should_not_retry_501_not_implemented(self):
        """Should NOT retry 501 Not Implemented."""
        from api_client.exceptions import ServerError
        from api_client.resilience import should_retry

        error = ServerError("Not implemented", status_code=501)

        assert should_retry(error, attempt=1, max_retries=3) is False


class TestRateLimitHandler:
    """Tests for rate limit handling."""

    def test_get_retry_delay_from_retry_after_header(self):
        """Rate limiter extracts delay from Retry-After header."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import RateLimitHandler

        handler = RateLimitHandler()
        error = RateLimitError("Rate limited", retry_after=60)

        delay = handler.get_retry_delay(error)

        assert delay == 60

    def test_get_retry_delay_default_when_no_header(self):
        """Rate limiter uses default delay when Retry-After missing."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import RateLimitHandler

        handler = RateLimitHandler(default_delay=30)
        error = RateLimitError("Rate limited")  # No retry_after

        delay = handler.get_retry_delay(error)

        assert delay == 30

    def test_get_retry_delay_respects_max_delay(self):
        """Rate limiter caps delay at max_delay."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import RateLimitHandler

        handler = RateLimitHandler(max_delay=30)
        error = RateLimitError("Rate limited", retry_after=300)

        delay = handler.get_retry_delay(error)

        assert delay <= 30

    def test_rate_limit_handler_tracks_calls(self):
        """Rate limiter tracks number of rate limit hits."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import RateLimitHandler

        handler = RateLimitHandler()

        assert handler.rate_limit_count == 0

        handler.record_rate_limit(RateLimitError("Limited"))
        assert handler.rate_limit_count == 1

        handler.record_rate_limit(RateLimitError("Limited again"))
        assert handler.rate_limit_count == 2


class TestRetryExecutor:
    """Tests for retry execution logic."""

    def test_retry_executor_succeeds_first_try(self):
        """Executor returns result on first success."""
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3))
        operation = Mock(return_value="success")

        result = executor.execute(operation)

        assert result == "success"
        assert operation.call_count == 1

    def test_retry_executor_retries_on_failure(self):
        """Executor retries operation on retryable failure."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3, initial_delay=0.01))
        operation = Mock(side_effect=[ServerError("Error", status_code=500), "success"])

        result = executor.execute(operation)

        assert result == "success"
        assert operation.call_count == 2

    def test_retry_executor_respects_max_retries(self):
        """Executor stops after max retries exceeded."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3, initial_delay=0.01))
        error = ServerError("Always fails", status_code=500)
        operation = Mock(side_effect=error)

        with pytest.raises(ServerError):
            executor.execute(operation)

        # Initial attempt + 3 retries = 4 total
        assert operation.call_count == 4

    def test_retry_executor_does_not_retry_client_error(self):
        """Executor does not retry on client errors."""
        from api_client.exceptions import ClientError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3))
        error = ClientError("Bad request", status_code=400)
        operation = Mock(side_effect=error)

        with pytest.raises(ClientError):
            executor.execute(operation)

        # Only initial attempt, no retries
        assert operation.call_count == 1

    def test_retry_executor_waits_between_retries(self):
        """Executor waits appropriate time between retries."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=2, initial_delay=0.1))
        operation = Mock(
            side_effect=[
                ServerError("Error", status_code=500),
                ServerError("Error", status_code=500),
                "success",
            ]
        )

        with patch("time.sleep") as mock_sleep:
            result = executor.execute(operation)

        assert result == "success"
        assert mock_sleep.call_count == 2

    def test_retry_executor_uses_rate_limit_delay(self):
        """Executor uses Retry-After delay for rate limits."""
        from api_client.exceptions import RateLimitError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3, initial_delay=1.0))
        operation = Mock(
            side_effect=[
                RateLimitError("Limited", retry_after=5),
                "success",
            ]
        )

        with patch("time.sleep") as mock_sleep:
            result = executor.execute(operation)

        assert result == "success"
        # Should use Retry-After value (5), not exponential backoff
        mock_sleep.assert_called_with(5)

    def test_retry_executor_calls_on_retry_callback(self):
        """Executor calls on_retry callback with retry info."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        on_retry = Mock()
        executor = RetryExecutor(
            RetryConfig(max_retries=3, initial_delay=0.01),
            on_retry=on_retry,
        )
        operation = Mock(
            side_effect=[
                ServerError("Error", status_code=500),
                "success",
            ]
        )

        executor.execute(operation)

        on_retry.assert_called_once()
        call_args = on_retry.call_args
        assert call_args[0][0] == 1  # attempt number
        assert isinstance(call_args[0][1], ServerError)  # exception


class TestRetryWithContext:
    """Tests for retry behavior with request context."""

    def test_retry_preserves_request_context(self):
        """Retry executor preserves request context across retries."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3, initial_delay=0.01))

        attempts = []

        def operation():
            attempts.append(executor.current_attempt)
            if len(attempts) < 2:
                raise ServerError("Error", status_code=500)
            return "success"

        result = executor.execute(operation)

        assert result == "success"
        assert attempts == [1, 2]

    def test_retry_context_tracks_total_time(self):
        """Retry context tracks total elapsed time."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=3, initial_delay=0.05))
        operation = Mock(
            side_effect=[
                ServerError("Error", status_code=500),
                "success",
            ]
        )

        executor.execute(operation)

        assert executor.total_elapsed_ms > 0

    def test_retry_context_available_in_exception(self):
        """Final exception includes retry context."""
        from api_client.exceptions import ServerError
        from api_client.resilience import RetryConfig, RetryExecutor

        executor = RetryExecutor(RetryConfig(max_retries=2, initial_delay=0.01))
        operation = Mock(side_effect=ServerError("Always fails", status_code=500))

        with pytest.raises(ServerError) as exc_info:
            executor.execute(operation)

        # Exception should indicate retries were attempted
        assert exc_info.value.attempts_made == 3  # initial + 2 retries


class TestCircuitBreaker:
    """Tests for circuit breaker pattern (optional enhancement)."""

    def test_circuit_starts_closed(self):
        """Circuit breaker starts in closed (allowing requests) state."""
        from api_client.resilience import CircuitBreaker

        breaker = CircuitBreaker()

        assert breaker.state == "closed"
        assert breaker.is_closed is True

    def test_circuit_opens_after_threshold_failures(self):
        """Circuit opens after consecutive failure threshold."""
        from api_client.exceptions import ServerError
        from api_client.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure(ServerError("Error", status_code=500))

        assert breaker.state == "open"
        assert breaker.is_open is True

    def test_circuit_resets_on_success(self):
        """Circuit resets failure count on success."""
        from api_client.exceptions import ServerError
        from api_client.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure(ServerError("Error", status_code=500))
        breaker.record_failure(ServerError("Error", status_code=500))
        breaker.record_success()

        assert breaker.state == "closed"
        assert breaker.consecutive_failures == 0

    def test_circuit_allows_test_request_after_timeout(self):
        """Circuit allows test request after reset timeout."""
        from api_client.exceptions import ServerError
        from api_client.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)

        breaker.record_failure(ServerError("Error", status_code=500))
        breaker.record_failure(ServerError("Error", status_code=500))

        assert breaker.is_open is True

        time.sleep(0.15)

        assert breaker.state == "half-open"
        assert breaker.should_allow_request() is True

    def test_circuit_closes_after_successful_test(self):
        """Circuit closes after successful test request."""
        from api_client.exceptions import ServerError
        from api_client.resilience import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, reset_timeout=0.01)

        breaker.record_failure(ServerError("Error", status_code=500))
        breaker.record_failure(ServerError("Error", status_code=500))

        time.sleep(0.02)  # Wait for reset timeout

        breaker.record_success()  # Successful test request

        assert breaker.state == "closed"
