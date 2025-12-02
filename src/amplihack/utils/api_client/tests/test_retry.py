"""Tests for RetryHandler.

Tests the retry handler using the actual implementation API:
- RetryHandler(max_retries=3, backoff_base=0.5, backoff_max=60.0, backoff_jitter=0.25)
- should_retry(exception: Exception, attempt: int) -> bool
- get_delay(attempt: int, retry_after: float | None = None) -> float
- execute(operation: Callable[[], T], operation_name: str) -> T

Formula: delay = min(backoff_base * 1.5^attempt + jitter, backoff_max)
Jitter: random(0, backoff_jitter * delay)

Testing pyramid target: 60% unit tests
"""

from unittest.mock import Mock, patch

import pytest


class TestRetryHandlerImport:
    """Tests for RetryHandler import and instantiation."""

    def test_import_retry_handler(self) -> None:
        """Test that RetryHandler can be imported."""
        from amplihack.utils.api_client.retry import RetryHandler

        assert RetryHandler is not None

    def test_create_retry_handler_defaults(self) -> None:
        """Test creating RetryHandler with default values."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()

        assert handler.max_retries == 3
        assert handler.backoff_base == 0.5
        assert handler.backoff_max == 60.0
        assert handler.backoff_jitter == 0.25

    def test_create_retry_handler_custom_values(self) -> None:
        """Test creating RetryHandler with custom values."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(
            max_retries=5,
            backoff_base=1.0,
            backoff_max=120.0,
            backoff_jitter=0.1,
        )

        assert handler.max_retries == 5
        assert handler.backoff_base == 1.0
        assert handler.backoff_max == 120.0
        assert handler.backoff_jitter == 0.1


class TestGetDelay:
    """Tests for get_delay method - exponential backoff calculation."""

    def test_get_delay_attempt_0(self) -> None:
        """Test delay for attempt 0.

        Formula: 0.5 * 1.5^0 = 0.5 + jitter
        """
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)  # Disable jitter

        delay = handler.get_delay(attempt=0)
        assert delay == pytest.approx(0.5, rel=0.01)

    def test_get_delay_attempt_1(self) -> None:
        """Test delay for attempt 1.

        Formula: 0.5 * 1.5^1 = 0.75 + jitter
        """
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)

        delay = handler.get_delay(attempt=1)
        assert delay == pytest.approx(0.75, rel=0.01)

    def test_get_delay_attempt_2(self) -> None:
        """Test delay for attempt 2.

        Formula: 0.5 * 1.5^2 = 1.125 + jitter
        """
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)

        delay = handler.get_delay(attempt=2)
        assert delay == pytest.approx(1.125, rel=0.01)

    def test_get_delay_capped_at_max(self) -> None:
        """Test that delay is capped at backoff_max."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_max=10.0, backoff_jitter=0)

        # High attempt would give huge delay without cap
        delay = handler.get_delay(attempt=20)
        assert delay == 10.0

    def test_get_delay_with_retry_after(self) -> None:
        """Test that retry_after takes precedence over calculated delay."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)

        delay = handler.get_delay(attempt=0, retry_after=30.0)
        assert delay == 30.0

    def test_get_delay_with_negative_retry_after(self) -> None:
        """Test that negative retry_after returns 0."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)

        delay = handler.get_delay(attempt=0, retry_after=-5.0)
        assert delay == 0.0

    def test_get_delay_custom_base_and_max(self) -> None:
        """Test delay with custom backoff_base."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_base=1.0, backoff_jitter=0)

        # 1.0 * 1.5^2 = 2.25
        delay = handler.get_delay(attempt=2)
        assert delay == pytest.approx(2.25, rel=0.01)


class TestJitter:
    """Tests for jitter in delay calculation."""

    def test_jitter_adds_randomness(self) -> None:
        """Test that jitter adds variability to delays."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0.25)

        delays = [handler.get_delay(attempt=2) for _ in range(50)]
        unique_delays = set(delays)

        # With jitter, we should get different values
        assert len(unique_delays) > 1

    def test_jitter_within_bounds(self) -> None:
        """Test that jitter stays within 0 to jitter_factor * base_delay."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0.25)
        base_delay = 0.5 * (1.5**2)  # 1.125

        for _ in range(100):
            delay = handler.get_delay(attempt=2)
            # Delay should be >= base_delay and <= base_delay * (1 + jitter_factor)
            assert delay >= base_delay, f"Delay {delay} below base {base_delay}"
            assert delay <= base_delay * 1.25, f"Delay {delay} above max {base_delay * 1.25}"

    def test_zero_jitter_deterministic(self) -> None:
        """Test that zero jitter gives consistent delays."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(backoff_jitter=0)

        delays = [handler.get_delay(attempt=1) for _ in range(10)]
        assert all(d == delays[0] for d in delays)


class TestShouldRetry:
    """Tests for should_retry method."""

    def test_should_retry_on_request_error(self) -> None:
        """Test that RequestError is retryable."""
        from amplihack.utils.api_client.exceptions import RequestError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        exc = RequestError("Connection failed")

        assert handler.should_retry(exc, attempt=0) is True

    def test_should_retry_on_server_error(self) -> None:
        """Test that ServerError is retryable."""
        from amplihack.utils.api_client.exceptions import ServerError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        exc = ServerError(
            message="Internal Server Error",
            status_code=500,
            response_body="Error",
        )

        assert handler.should_retry(exc, attempt=0) is True

    def test_should_retry_on_rate_limit_error(self) -> None:
        """Test that RateLimitError is retryable."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        exc = RateLimitError(
            message="Rate limited",
            retry_after=60.0,
        )

        assert handler.should_retry(exc, attempt=0) is True

    def test_should_not_retry_on_client_error(self) -> None:
        """Test that ClientError (4xx) is NOT retryable."""
        from amplihack.utils.api_client.exceptions import ClientError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        exc = ClientError(
            message="Bad Request",
            status_code=400,
            response_body="Invalid input",
        )

        assert handler.should_retry(exc, attempt=0) is False

    def test_should_not_retry_on_generic_exception(self) -> None:
        """Test that generic Exception is NOT retryable."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        exc = ValueError("Invalid parameter")

        assert handler.should_retry(exc, attempt=0) is False

    def test_should_not_retry_when_max_exceeded(self) -> None:
        """Test that retry stops when max_retries exceeded."""
        from amplihack.utils.api_client.exceptions import ServerError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=3)
        exc = ServerError(
            message="Server Error",
            status_code=500,
            response_body="Error",
        )

        # Attempts 0, 1, 2 should allow retry
        assert handler.should_retry(exc, attempt=0) is True
        assert handler.should_retry(exc, attempt=1) is True
        assert handler.should_retry(exc, attempt=2) is True

        # Attempt 3 should NOT allow retry
        assert handler.should_retry(exc, attempt=3) is False

    def test_should_not_retry_with_zero_max_retries(self) -> None:
        """Test that zero max_retries means no retries."""
        from amplihack.utils.api_client.exceptions import ServerError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=0)
        exc = ServerError(
            message="Server Error",
            status_code=500,
            response_body="Error",
        )

        assert handler.should_retry(exc, attempt=0) is False


class TestExecute:
    """Tests for execute method."""

    def test_execute_success_first_try(self) -> None:
        """Test execute succeeds on first attempt."""
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler()
        operation = Mock(return_value="success")

        result = handler.execute(operation, "test_op")

        assert result == "success"
        assert operation.call_count == 1

    def test_execute_success_after_retry(self) -> None:
        """Test execute succeeds after transient failure."""
        from amplihack.utils.api_client.exceptions import ServerError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=3, backoff_jitter=0)

        # First call fails, second succeeds
        operation = Mock(
            side_effect=[
                ServerError(message="Error", status_code=500, response_body="Error"),
                "success",
            ]
        )

        with patch("time.sleep"):
            result = handler.execute(operation, "test_op")

        assert result == "success"
        assert operation.call_count == 2

    def test_execute_raises_original_error_after_max_retries(self) -> None:
        """Test execute raises original error after max retries exhausted.

        The implementation re-raises the original exception when should_retry
        returns False (attempt >= max_retries).
        """
        from amplihack.utils.api_client.exceptions import ServerError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=2, backoff_jitter=0)

        # All calls fail
        operation = Mock(
            side_effect=ServerError(message="Error", status_code=500, response_body="Error")
        )

        with patch("time.sleep"):
            with pytest.raises(ServerError):
                handler.execute(operation, "test_op")

        # Should have tried: initial + 2 retries = 3 times
        assert operation.call_count == 3

    def test_execute_raises_non_retryable_immediately(self) -> None:
        """Test execute raises non-retryable exceptions immediately."""
        from amplihack.utils.api_client.exceptions import ClientError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=3)

        # Non-retryable error
        operation = Mock(
            side_effect=ClientError(message="Bad Request", status_code=400, response_body="Invalid")
        )

        with pytest.raises(ClientError):
            handler.execute(operation, "test_op")

        # Should only be called once - no retries for client errors
        assert operation.call_count == 1

    def test_execute_uses_retry_after(self) -> None:
        """Test execute respects RateLimitError retry_after."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.retry import RetryHandler

        handler = RetryHandler(max_retries=3, backoff_jitter=0)

        # First call rate limited, second succeeds
        operation = Mock(
            side_effect=[
                RateLimitError(message="Rate limited", retry_after=30.0),
                "success",
            ]
        )

        with patch("time.sleep") as mock_sleep:
            result = handler.execute(operation, "test_op")

        assert result == "success"
        # Should have slept for the retry_after value
        mock_sleep.assert_called_once_with(30.0)
