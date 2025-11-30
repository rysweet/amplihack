"""Unit tests for retry logic."""

from unittest.mock import Mock

import pytest

# These imports will fail initially (TDD)
from rest_api_client.retry import ExponentialBackoff, LinearBackoff, RetryManager, should_retry


class TestExponentialBackoff:
    """Test exponential backoff retry strategy."""

    def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        strategy = ExponentialBackoff(initial_delay=1.0, max_delay=60.0, multiplier=2.0)

        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0
        assert strategy.get_delay(3) == 8.0
        assert strategy.get_delay(4) == 16.0

    def test_exponential_backoff_max_delay(self):
        """Test that delay is capped at max_delay."""
        strategy = ExponentialBackoff(initial_delay=1.0, max_delay=10.0, multiplier=3.0)

        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 3.0
        assert strategy.get_delay(2) == 9.0
        assert strategy.get_delay(3) == 10.0  # Capped at max
        assert strategy.get_delay(10) == 10.0  # Still capped

    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter."""
        strategy = ExponentialBackoff(
            initial_delay=1.0, max_delay=60.0, multiplier=2.0, jitter=True
        )

        # With jitter, delay should vary but be bounded
        delays = [strategy.get_delay(2) for _ in range(10)]
        assert all(0 <= d <= 4.0 for d in delays)
        assert len(set(delays)) > 1  # Should have variation

    def test_should_retry_status_codes(self):
        """Test which status codes should be retried."""
        strategy = ExponentialBackoff()

        # Should retry server errors
        assert strategy.should_retry(500) is True
        assert strategy.should_retry(502) is True
        assert strategy.should_retry(503) is True
        assert strategy.should_retry(504) is True

        # Should retry rate limiting
        assert strategy.should_retry(429) is True

        # Should not retry client errors
        assert strategy.should_retry(400) is False
        assert strategy.should_retry(401) is False
        assert strategy.should_retry(403) is False
        assert strategy.should_retry(404) is False

        # Should not retry success
        assert strategy.should_retry(200) is False
        assert strategy.should_retry(201) is False


class TestLinearBackoff:
    """Test linear backoff retry strategy."""

    def test_linear_backoff_delay(self):
        """Test linear backoff delay calculation."""
        strategy = LinearBackoff(delay=5.0, max_delay=30.0)

        assert strategy.get_delay(0) == 5.0
        assert strategy.get_delay(1) == 5.0
        assert strategy.get_delay(10) == 5.0

    def test_linear_backoff_incremental(self):
        """Test linear backoff with increment."""
        strategy = LinearBackoff(delay=2.0, increment=3.0, max_delay=20.0)

        assert strategy.get_delay(0) == 2.0
        assert strategy.get_delay(1) == 5.0
        assert strategy.get_delay(2) == 8.0
        assert strategy.get_delay(3) == 11.0
        assert strategy.get_delay(10) == 20.0  # Capped at max


class TestRetryManager:
    """Test retry manager."""

    def test_retry_manager_success_first_try(self):
        """Test successful request on first try."""
        manager = RetryManager(max_retries=3, strategy=ExponentialBackoff())

        func = Mock(return_value="success")
        result = manager.execute(func)

        assert result == "success"
        assert func.call_count == 1

    def test_retry_manager_retry_on_exception(self):
        """Test retry on exception."""
        manager = RetryManager(max_retries=3, strategy=ExponentialBackoff(initial_delay=0.01))

        func = Mock(
            side_effect=[ConnectionError("Failed"), ConnectionError("Failed again"), "success"]
        )

        result = manager.execute(func)
        assert result == "success"
        assert func.call_count == 3

    def test_retry_manager_max_retries_exceeded(self):
        """Test that max retries is respected."""
        manager = RetryManager(max_retries=2, strategy=ExponentialBackoff(initial_delay=0.01))

        func = Mock(side_effect=ConnectionError("Always fails"))

        with pytest.raises(ConnectionError):
            manager.execute(func)

        # Initial attempt + 2 retries = 3 total
        assert func.call_count == 3

    def test_retry_manager_with_predicate(self):
        """Test retry with custom predicate."""

        def custom_predicate(exception):
            return isinstance(exception, ValueError)

        manager = RetryManager(
            max_retries=3,
            strategy=ExponentialBackoff(initial_delay=0.01),
            retry_predicate=custom_predicate,
        )

        # Should retry ValueError
        func = Mock(side_effect=[ValueError("retry"), "success"])
        result = manager.execute(func)
        assert result == "success"
        assert func.call_count == 2

        # Should not retry TypeError
        func = Mock(side_effect=TypeError("no retry"))
        with pytest.raises(TypeError):
            manager.execute(func)
        assert func.call_count == 1

    def test_retry_manager_backoff_timing(self, mock_time):
        """Test that backoff delays are applied correctly."""
        strategy = ExponentialBackoff(initial_delay=1.0, max_delay=10.0, multiplier=2.0)
        manager = RetryManager(max_retries=3, strategy=strategy)

        func = Mock(side_effect=[ConnectionError("Failed"), ConnectionError("Failed"), "success"])

        result = manager.execute(func)
        assert result == "success"

        # Verify delays were applied (1.0 and 2.0 seconds)
        # mock_time fixture handles time advancing

    def test_retry_manager_context_manager(self):
        """Test retry manager as context manager."""
        strategy = ExponentialBackoff()

        with RetryManager(max_retries=2, strategy=strategy) as manager:
            func = Mock(return_value="success")
            result = manager.execute(func)
            assert result == "success"

    def test_retry_manager_async_support(self):
        """Test retry manager with async functions."""
        import asyncio

        async def async_func():
            return "async_success"

        manager = RetryManager(max_retries=3, strategy=ExponentialBackoff())

        # Should handle async functions
        result = asyncio.run(manager.execute_async(async_func))
        assert result == "async_success"


class TestShouldRetry:
    """Test should_retry helper function."""

    def test_should_retry_by_status_code(self):
        """Test should_retry based on status codes."""
        # Retryable status codes
        assert should_retry(status_code=500) is True
        assert should_retry(status_code=502) is True
        assert should_retry(status_code=503) is True
        assert should_retry(status_code=429) is True

        # Non-retryable status codes
        assert should_retry(status_code=400) is False
        assert should_retry(status_code=401) is False
        assert should_retry(status_code=404) is False

    def test_should_retry_by_exception(self):
        """Test should_retry based on exception types."""
        from rest_api_client.exceptions import (
            ConnectionError,
            RateLimitError,
            TimeoutError,
            ValidationError,
        )

        # Retryable exceptions
        assert should_retry(exception=ConnectionError()) is True
        assert should_retry(exception=TimeoutError()) is True
        assert should_retry(exception=RateLimitError("")) is True

        # Non-retryable exceptions
        assert should_retry(exception=ValidationError("")) is False
        assert should_retry(exception=ValueError()) is False

    def test_should_retry_custom_logic(self):
        """Test should_retry with custom logic."""

        def custom_logic(status_code=None, exception=None):
            if exception and "temporary" in str(exception):
                return True
            return False

        assert (
            should_retry(exception=Exception("temporary failure"), custom_predicate=custom_logic)
            is True
        )

        assert (
            should_retry(exception=Exception("permanent failure"), custom_predicate=custom_logic)
            is False
        )
