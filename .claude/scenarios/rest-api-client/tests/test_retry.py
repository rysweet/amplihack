"""Unit tests for retry logic with exponential backoff.

Testing focus: Retry mechanisms, exponential backoff calculation,
maximum retry limits, and retry conditions.
"""

import time
from unittest.mock import Mock, patch

import pytest
from rest_api_client.exceptions import APIClientError, ConnectionError, ServerError, TimeoutError

# These imports will fail initially (TDD approach)
from rest_api_client.retry import (
    ExponentialBackoff,
    MaxRetriesExceeded,
    RetryHandler,
    RetryPolicy,
)


class TestExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_calculate_backoff_time(self):
        """Test exponential backoff time calculation."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=60.0, exponential_base=2.0)

        # First retry: 1 * 2^0 = 1 second
        assert backoff.calculate_delay(attempt=1) == 1.0

        # Second retry: 1 * 2^1 = 2 seconds
        assert backoff.calculate_delay(attempt=2) == 2.0

        # Third retry: 1 * 2^2 = 4 seconds
        assert backoff.calculate_delay(attempt=3) == 4.0

        # Fourth retry: 1 * 2^3 = 8 seconds
        assert backoff.calculate_delay(attempt=4) == 8.0

    def test_backoff_with_jitter(self):
        """Test exponential backoff with jitter to prevent thundering herd."""
        backoff = ExponentialBackoff(
            base_delay=1.0, max_delay=60.0, exponential_base=2.0, jitter=True
        )

        # With jitter, delay should be within expected range
        for attempt in range(1, 5):
            delay = backoff.calculate_delay(attempt)
            expected_base = 1.0 * (2.0 ** (attempt - 1))
            # Jitter should add 0-50% variation
            assert expected_base * 0.5 <= delay <= expected_base * 1.5

    def test_max_delay_cap(self):
        """Test that backoff is capped at max_delay."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0, exponential_base=2.0)

        # 10th attempt would be 512 seconds, but should cap at 10
        assert backoff.calculate_delay(attempt=10) == 10.0

    def test_custom_backoff_factor(self):
        """Test custom backoff multiplication factor."""
        backoff = ExponentialBackoff(
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,  # Triple each time
        )

        assert backoff.calculate_delay(attempt=1) == 0.5
        assert backoff.calculate_delay(attempt=2) == 1.5  # 0.5 * 3
        assert backoff.calculate_delay(attempt=3) == 4.5  # 0.5 * 9


class TestRetryPolicy:
    """Test retry policy configuration."""

    def test_default_retry_policy(self):
        """Test default retry policy settings."""
        policy = RetryPolicy()

        assert policy.max_retries == 3
        assert policy.retry_on_status == [429, 500, 502, 503, 504]
        assert policy.retry_on_exceptions == [ConnectionError, TimeoutError, ServerError]
        assert policy.backoff_strategy is not None

    def test_custom_retry_policy(self):
        """Test custom retry policy configuration."""
        policy = RetryPolicy(
            max_retries=5,
            retry_on_status=[500, 503],
            retry_on_exceptions=[ConnectionError],
            backoff_strategy=ExponentialBackoff(base_delay=2.0),
        )

        assert policy.max_retries == 5
        assert 429 not in policy.retry_on_status
        assert TimeoutError not in policy.retry_on_exceptions

    def test_should_retry_on_status(self):
        """Test retry decision based on status code."""
        policy = RetryPolicy(retry_on_status=[500, 503])

        assert policy.should_retry_status(500) is True
        assert policy.should_retry_status(503) is True
        assert policy.should_retry_status(404) is False
        assert policy.should_retry_status(200) is False

    def test_should_retry_on_exception(self):
        """Test retry decision based on exception type."""
        policy = RetryPolicy(retry_on_exceptions=[ConnectionError, TimeoutError])

        assert policy.should_retry_exception(ConnectionError()) is True
        assert policy.should_retry_exception(TimeoutError()) is True
        assert policy.should_retry_exception(ValueError()) is False

    def test_retry_after_header_parsing(self):
        """Test parsing Retry-After header for delay."""
        policy = RetryPolicy()

        # Numeric seconds
        assert policy.parse_retry_after("60") == 60

        # HTTP date format
        future_time = time.time() + 120
        http_date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(future_time))
        parsed_delay = policy.parse_retry_after(http_date)
        assert 118 <= parsed_delay <= 122  # Allow some tolerance


class TestRetryHandler:
    """Test the main retry handler functionality."""

    def test_successful_request_no_retry(self):
        """Test successful request doesn't trigger retry."""
        handler = RetryHandler(RetryPolicy(max_retries=3))

        mock_func = Mock(return_value=Mock(status_code=200))
        result = handler.execute_with_retry(mock_func)

        assert mock_func.call_count == 1
        assert result.status_code == 200

    def test_retry_on_failure_status(self):
        """Test retry on failure status codes."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=3,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        responses = [Mock(status_code=503), Mock(status_code=503), Mock(status_code=200)]
        mock_func = Mock(side_effect=responses)

        with patch("time.sleep") as mock_sleep:
            result = handler.execute_with_retry(mock_func)

        assert mock_func.call_count == 3
        assert result.status_code == 200
        assert mock_sleep.call_count == 2  # Sleep between retries

    def test_retry_on_exception(self):
        """Test retry on retryable exceptions."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=3,
                retry_on_exceptions=[ConnectionError],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        mock_func = Mock(
            side_effect=[
                ConnectionError("Connection failed"),
                ConnectionError("Connection failed"),
                Mock(status_code=200),
            ]
        )

        with patch("time.sleep") as mock_sleep:
            result = handler.execute_with_retry(mock_func)

        assert mock_func.call_count == 3
        assert result.status_code == 200

    def test_max_retries_exceeded(self):
        """Test max retries exceeded raises exception."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=3,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        mock_func = Mock(return_value=Mock(status_code=503))

        with patch("time.sleep"):
            with pytest.raises(MaxRetriesExceeded) as exc_info:
                handler.execute_with_retry(mock_func)

        assert exc_info.value.attempts == 4  # Initial + 3 retries
        assert mock_func.call_count == 4

    def test_non_retryable_exception_propagates(self):
        """Test non-retryable exceptions are not retried."""
        handler = RetryHandler(RetryPolicy(max_retries=3, retry_on_exceptions=[ConnectionError]))

        mock_func = Mock(side_effect=ValueError("Invalid input"))

        with pytest.raises(ValueError, match="Invalid input"):
            handler.execute_with_retry(mock_func)

        assert mock_func.call_count == 1  # No retry

    def test_retry_with_retry_after_header(self):
        """Test respecting Retry-After header."""
        handler = RetryHandler(RetryPolicy(max_retries=3, retry_on_status=[429]))

        responses = [Mock(status_code=429, headers={"Retry-After": "2"}), Mock(status_code=200)]
        mock_func = Mock(side_effect=responses)

        with patch("time.sleep") as mock_sleep:
            result = handler.execute_with_retry(mock_func)

        assert result.status_code == 200
        # Should sleep for time specified in Retry-After header
        mock_sleep.assert_called_with(2)

    def test_retry_logging(self, mock_logger):
        """Test retry attempts are logged."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=2,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            ),
            logger=mock_logger,
        )

        responses = [Mock(status_code=503), Mock(status_code=200)]
        mock_func = Mock(side_effect=responses)

        with patch("time.sleep"):
            handler.execute_with_retry(mock_func)

        # Check retry was logged
        mock_logger.warning.assert_called()
        warning_calls = mock_logger.warning.call_args_list
        assert any("Retry" in str(call) for call in warning_calls)
        assert any("503" in str(call) for call in warning_calls)

    def test_retry_callback(self):
        """Test retry callback is called on each retry."""
        callback_calls = []

        def retry_callback(attempt, exception, delay):
            callback_calls.append({"attempt": attempt, "exception": exception, "delay": delay})

        handler = RetryHandler(
            RetryPolicy(
                max_retries=2,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            ),
            on_retry_callback=retry_callback,
        )

        responses = [Mock(status_code=503), Mock(status_code=200)]
        mock_func = Mock(side_effect=responses)

        with patch("time.sleep"):
            handler.execute_with_retry(mock_func)

        assert len(callback_calls) == 1
        assert callback_calls[0]["attempt"] == 1
        assert callback_calls[0]["delay"] == 0.01


class TestRetryStatistics:
    """Test retry statistics and monitoring."""

    def test_retry_statistics_tracking(self):
        """Test tracking of retry statistics."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=3,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        responses = [Mock(status_code=503), Mock(status_code=503), Mock(status_code=200)]
        mock_func = Mock(side_effect=responses)

        with patch("time.sleep"):
            handler.execute_with_retry(mock_func)

        stats = handler.get_statistics()
        assert stats["total_requests"] == 1
        assert stats["total_retries"] == 2
        assert stats["successful_retries"] == 1
        assert stats["failed_retries"] == 0

    def test_retry_statistics_with_failure(self):
        """Test statistics when all retries fail."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=2,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        mock_func = Mock(return_value=Mock(status_code=503))

        with patch("time.sleep"):
            try:
                handler.execute_with_retry(mock_func)
            except MaxRetriesExceeded:
                pass

        stats = handler.get_statistics()
        assert stats["total_requests"] == 1
        assert stats["total_retries"] == 2
        assert stats["successful_retries"] == 0
        assert stats["failed_retries"] == 1


class TestCircuitBreaker:
    """Test circuit breaker pattern with retries."""

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after consecutive failures."""
        handler = RetryHandler(
            RetryPolicy(max_retries=1), circuit_breaker_threshold=3, circuit_breaker_timeout=60
        )

        mock_func = Mock(return_value=Mock(status_code=503))

        # Make requests until circuit breaker opens
        for i in range(3):
            with patch("time.sleep"):
                try:
                    handler.execute_with_retry(mock_func)
                except MaxRetriesExceeded:
                    pass

        # Circuit should be open, next request should fail immediately
        with pytest.raises(APIClientError, match="Circuit breaker is open"):
            handler.execute_with_retry(mock_func)

    def test_circuit_breaker_half_open_state(self, mock_time):
        """Test circuit breaker half-open state after timeout."""
        handler = RetryHandler(
            RetryPolicy(max_retries=1), circuit_breaker_threshold=2, circuit_breaker_timeout=60
        )

        mock_func = Mock(return_value=Mock(status_code=503))

        # Open the circuit
        for i in range(2):
            with patch("time.sleep"):
                try:
                    handler.execute_with_retry(mock_func)
                except MaxRetriesExceeded:
                    pass

        # Circuit is open
        with pytest.raises(APIClientError, match="Circuit breaker is open"):
            handler.execute_with_retry(mock_func)

        # Advance time past timeout
        mock_time.advance(61)

        # Circuit should be half-open, allow one test request
        mock_func.return_value = Mock(status_code=200)
        result = handler.execute_with_retry(mock_func)
        assert result.status_code == 200

        # Circuit should be closed again
        assert handler.circuit_breaker.state == "closed"


class TestRetryWithDifferentMethods:
    """Test retry behavior with different HTTP methods."""

    def test_idempotent_methods_retry(self):
        """Test idempotent methods (GET, PUT, DELETE) are retried."""
        handler = RetryHandler(
            RetryPolicy(
                max_retries=2,
                retry_on_status=[503],
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        for method in ["GET", "PUT", "DELETE"]:
            responses = [Mock(status_code=503), Mock(status_code=200)]
            mock_func = Mock(side_effect=responses)

            with patch("time.sleep"):
                result = handler.execute_with_retry(mock_func, method=method)

            assert result.status_code == 200
            assert mock_func.call_count == 2

    def test_non_idempotent_methods_configurable(self):
        """Test non-idempotent methods (POST) retry is configurable."""
        # Default: POST not retried on network errors
        handler = RetryHandler(
            RetryPolicy(
                max_retries=2, retry_on_exceptions=[ConnectionError], retry_non_idempotent=False
            )
        )

        mock_func = Mock(side_effect=ConnectionError())

        with pytest.raises(ConnectionError):
            handler.execute_with_retry(mock_func, method="POST")

        assert mock_func.call_count == 1  # No retry

        # With retry_non_idempotent=True
        handler_retry_post = RetryHandler(
            RetryPolicy(
                max_retries=2,
                retry_on_exceptions=[ConnectionError],
                retry_non_idempotent=True,
                backoff_strategy=ExponentialBackoff(base_delay=0.01),
            )
        )

        mock_func = Mock(side_effect=[ConnectionError(), Mock(status_code=201)])

        with patch("time.sleep"):
            result = handler_retry_post.execute_with_retry(mock_func, method="POST")

        assert result.status_code == 201
        assert mock_func.call_count == 2
