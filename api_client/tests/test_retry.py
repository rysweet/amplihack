"""Unit tests for RetryHandler.

Testing pyramid: 60% unit tests (these tests)
"""

from unittest.mock import Mock

import pytest

from api_client.exceptions import RetryExhaustedError
from api_client.retry import RetryHandler


class TestRetryHandlerInit:
    """Tests for RetryHandler initialization."""

    def test_create_with_defaults(self):
        """Test creating handler with default parameters."""
        handler = RetryHandler()
        assert handler._max_retries == 3
        assert handler._base_delay == 1.0
        assert handler._multiplier == 2.0
        assert handler._max_delay == 60.0

    def test_create_with_custom_params(self):
        """Test creating handler with custom parameters."""
        handler = RetryHandler(
            max_retries=5,
            base_delay=2.0,
            multiplier=3.0,
            max_delay=120.0,
        )
        assert handler._max_retries == 5
        assert handler._base_delay == 2.0
        assert handler._multiplier == 3.0
        assert handler._max_delay == 120.0

    def test_validate_negative_max_retries(self):
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryHandler(max_retries=-1)

    def test_validate_invalid_base_delay(self):
        """Test that invalid base_delay raises ValueError."""
        with pytest.raises(ValueError, match="base_delay must be positive"):
            RetryHandler(base_delay=0.0)

    def test_validate_invalid_multiplier(self):
        """Test that invalid multiplier raises ValueError."""
        with pytest.raises(ValueError, match="multiplier must be positive"):
            RetryHandler(multiplier=0.0)

    def test_validate_invalid_max_delay(self):
        """Test that invalid max_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay must be positive"):
            RetryHandler(max_delay=0.0)


class TestRetryHandlerExecute:
    """Tests for RetryHandler.execute method."""

    def test_success_on_first_attempt(self):
        """Test operation succeeds on first attempt."""
        handler = RetryHandler(max_retries=3)
        mock_op = Mock(return_value="success")

        result = handler.execute(mock_op)

        assert result == "success"
        assert mock_op.call_count == 1

    def test_success_after_retry(self):
        """Test operation succeeds after retries."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        # Fail twice, then succeed
        mock_op = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

        result = handler.execute(mock_op)

        assert result == "success"
        assert mock_op.call_count == 3

    def test_retry_exhausted(self):
        """Test all retries fail."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        # Always fail
        mock_op = Mock(side_effect=ValueError("persistent failure"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            handler.execute(mock_op)

        # Should attempt 3 times (initial + 2 retries)
        assert mock_op.call_count == 3

        # Check exception details
        error = exc_info.value
        assert error.context["attempts"] == 3
        assert "persistent failure" in error.context["last_error"]

    def test_non_retryable_exception(self):
        """Test non-retryable exception is not retried."""
        handler = RetryHandler(max_retries=3)

        # Raise non-retryable exception
        class CustomError(Exception):
            pass

        mock_op = Mock(side_effect=CustomError("custom"))

        with pytest.raises(CustomError):
            handler.execute(mock_op, retryable_exceptions=(ValueError,))

        # Should only attempt once
        assert mock_op.call_count == 1

    def test_zero_retries(self):
        """Test handler with zero retries."""
        handler = RetryHandler(max_retries=0)
        mock_op = Mock(side_effect=ValueError("fail"))

        with pytest.raises(RetryExhaustedError):
            handler.execute(mock_op)

        # Should only attempt once
        assert mock_op.call_count == 1


class TestRetryHandlerDelayCalculation:
    """Tests for retry delay calculation."""

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation."""
        handler = RetryHandler(base_delay=1.0, multiplier=2.0, max_delay=100.0)

        # Attempt 0: 1.0 * (2.0 ** 0) = 1.0
        assert handler._calculate_delay(0) == 1.0

        # Attempt 1: 1.0 * (2.0 ** 1) = 2.0
        assert handler._calculate_delay(1) == 2.0

        # Attempt 2: 1.0 * (2.0 ** 2) = 4.0
        assert handler._calculate_delay(2) == 4.0

        # Attempt 3: 1.0 * (2.0 ** 3) = 8.0
        assert handler._calculate_delay(3) == 8.0

    def test_calculate_delay_capped_at_max(self):
        """Test delay is capped at max_delay."""
        handler = RetryHandler(base_delay=1.0, multiplier=2.0, max_delay=5.0)

        # Attempt 10 would be 1024.0, but should be capped at 5.0
        assert handler._calculate_delay(10) == 5.0

    def test_calculate_delay_custom_multiplier(self):
        """Test delay with custom multiplier."""
        handler = RetryHandler(base_delay=2.0, multiplier=3.0, max_delay=100.0)

        # Attempt 0: 2.0 * (3.0 ** 0) = 2.0
        assert handler._calculate_delay(0) == 2.0

        # Attempt 1: 2.0 * (3.0 ** 1) = 6.0
        assert handler._calculate_delay(1) == 6.0

        # Attempt 2: 2.0 * (3.0 ** 2) = 18.0
        assert handler._calculate_delay(2) == 18.0
