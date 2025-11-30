"""Unit tests for retry logic - testing exponential backoff.

Tests retry mechanism with exponential backoff in isolation.
"""

from unittest.mock import Mock, call, patch

import pytest

from rest_api_client.exceptions import HTTPResponseError, NetworkError, TimeoutError
from rest_api_client.retry import ExponentialBackoff, RetryHandler


@pytest.mark.unit
class TestExponentialBackoff:
    """Test exponential backoff calculator."""

    def test_initial_delay(self):
        """Test initial delay calculation."""
        backoff = ExponentialBackoff(base_delay=1.0)
        assert backoff.get_delay(0) == 1.0
        assert backoff.get_delay(1) == 2.0
        assert backoff.get_delay(2) == 4.0
        assert backoff.get_delay(3) == 8.0

    def test_custom_base_delay(self):
        """Test custom base delay."""
        backoff = ExponentialBackoff(base_delay=0.5)
        assert backoff.get_delay(0) == 0.5
        assert backoff.get_delay(1) == 1.0
        assert backoff.get_delay(2) == 2.0

    def test_max_delay_cap(self):
        """Test maximum delay cap."""
        backoff = ExponentialBackoff(base_delay=1.0, max_delay=10.0)
        assert backoff.get_delay(0) == 1.0
        assert backoff.get_delay(3) == 8.0
        assert backoff.get_delay(4) == 10.0  # Capped
        assert backoff.get_delay(10) == 10.0  # Still capped

    def test_jitter(self):
        """Test jitter adds randomness."""
        backoff = ExponentialBackoff(base_delay=1.0, jitter=True)

        # Get multiple delays for same attempt
        delays = [backoff.get_delay(2) for _ in range(10)]

        # All should be around 4.0 but with variation
        assert all(3.0 <= d <= 5.0 for d in delays)
        # Should have some variation
        assert len(set(delays)) > 1

    def test_no_jitter(self):
        """Test no jitter gives consistent delays."""
        backoff = ExponentialBackoff(base_delay=1.0, jitter=False)

        # Get multiple delays for same attempt
        delays = [backoff.get_delay(2) for _ in range(10)]

        # All should be exactly 4.0
        assert all(d == 4.0 for d in delays)


@pytest.mark.unit
class TestRetryHandler:
    """Test the retry handler."""

    def test_successful_call_no_retry(self):
        """Test successful call doesn't trigger retry."""
        handler = RetryHandler(max_retries=3)
        mock_func = Mock(return_value="success")

        result = handler.execute(mock_func, "arg1", kwarg="value")

        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg="value")

    def test_retry_on_network_error(self):
        """Test retry on network errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        mock_func = Mock(
            side_effect=[
                NetworkError("Connection failed"),
                NetworkError("Connection failed"),
                "success",
            ]
        )

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_on_timeout_error(self):
        """Test retry on timeout errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        mock_func = Mock(side_effect=[TimeoutError("Request timed out"), "success"])

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_on_5xx_errors(self):
        """Test retry on 5xx server errors."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)

        error500 = HTTPResponseError("Server error", status_code=500)
        error502 = HTTPResponseError("Bad gateway", status_code=502)
        error503 = HTTPResponseError("Service unavailable", status_code=503)

        mock_func = Mock(side_effect=[error500, error502, error503, "success"])

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 4

    def test_no_retry_on_4xx_errors(self):
        """Test no retry on 4xx client errors."""
        handler = RetryHandler(max_retries=3)

        error400 = HTTPResponseError("Bad request", status_code=400)
        mock_func = Mock(side_effect=error400)

        with pytest.raises(HTTPResponseError) as exc_info:
            handler.execute(mock_func)

        assert exc_info.value.status_code == 400
        assert mock_func.call_count == 1  # No retry

    def test_no_retry_on_401_unauthorized(self):
        """Test no retry on 401 unauthorized."""
        handler = RetryHandler(max_retries=3)

        error401 = HTTPResponseError("Unauthorized", status_code=401)
        mock_func = Mock(side_effect=error401)

        with pytest.raises(HTTPResponseError) as exc_info:
            handler.execute(mock_func)

        assert exc_info.value.status_code == 401
        assert mock_func.call_count == 1  # No retry

    def test_max_retries_exceeded(self):
        """Test max retries exceeded raises last error."""
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        mock_func = Mock(side_effect=NetworkError("Connection failed"))

        with pytest.raises(NetworkError) as exc_info:
            handler.execute(mock_func)

        assert "Connection failed" in str(exc_info.value)
        assert mock_func.call_count == 4  # Initial + 3 retries

    @patch("time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep):
        """Test exponential backoff delays between retries."""
        handler = RetryHandler(max_retries=3, base_delay=1.0)
        mock_func = Mock(
            side_effect=[
                NetworkError("Failed"),
                NetworkError("Failed"),
                NetworkError("Failed"),
                "success",
            ]
        )

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 4

        # Check sleep was called with exponential delays
        expected_calls = [call(1.0), call(2.0), call(4.0)]
        mock_sleep.assert_has_calls(expected_calls)

    def test_retry_with_different_errors(self):
        """Test retry with mixed error types."""
        handler = RetryHandler(max_retries=4, base_delay=0.01)
        mock_func = Mock(
            side_effect=[
                NetworkError("Connection failed"),
                TimeoutError("Timeout"),
                HTTPResponseError("Server error", status_code=503),
                "success",
            ]
        )

        result = handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 4

    def test_custom_retry_predicate(self):
        """Test custom retry predicate function."""

        def should_retry(error):
            """Custom predicate - only retry on specific message."""
            return isinstance(error, NetworkError) and "temporary" in str(error).lower()

        handler = RetryHandler(max_retries=3, retry_predicate=should_retry, base_delay=0.01)

        # Should retry on temporary errors
        mock_func = Mock(side_effect=[NetworkError("Temporary network issue"), "success"])
        result = handler.execute(mock_func)
        assert result == "success"
        assert mock_func.call_count == 2

        # Should NOT retry on permanent errors
        mock_func = Mock(side_effect=NetworkError("Permanent failure"))
        with pytest.raises(NetworkError):
            handler.execute(mock_func)
        assert mock_func.call_count == 1

    def test_zero_retries(self):
        """Test with zero retries (no retry)."""
        handler = RetryHandler(max_retries=0)
        mock_func = Mock(side_effect=NetworkError("Failed"))

        with pytest.raises(NetworkError):
            handler.execute(mock_func)

        assert mock_func.call_count == 1

    @patch("time.sleep")
    def test_retry_logging(self, mock_sleep):
        """Test that retries are logged appropriately."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        # Mock logger
        with patch("rest_api_client.retry.logger") as mock_logger:
            mock_func = Mock(
                side_effect=[NetworkError("Connection failed"), TimeoutError("Timeout"), "success"]
            )

            result = handler.execute(mock_func)

            assert result == "success"

            # Check logging calls
            assert mock_logger.warning.call_count == 2
            assert "Retry 1/2" in str(mock_logger.warning.call_args_list[0])
            assert "Retry 2/2" in str(mock_logger.warning.call_args_list[1])

    def test_preserve_function_args(self):
        """Test that function arguments are preserved across retries."""
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        call_args = []

        def track_calls(*args, **kwargs):
            call_args.append((args, kwargs))
            if len(call_args) < 3:
                raise NetworkError("Failed")
            return "success"

        result = handler.execute(track_calls, "arg1", "arg2", key="value")

        assert result == "success"
        assert len(call_args) == 3
        # All calls should have same args
        for args, kwargs in call_args:
            assert args == ("arg1", "arg2")
            assert kwargs == {"key": "value"}


@pytest.mark.unit
class TestRetryStatistics:
    """Test retry statistics tracking."""

    def test_track_retry_stats(self):
        """Test tracking of retry statistics."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, track_stats=True)

        # Successful call
        mock_func = Mock(return_value="success")
        handler.execute(mock_func)

        stats = handler.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0
        assert stats["total_retries"] == 0

    def test_track_retry_count(self):
        """Test tracking retry counts."""
        handler = RetryHandler(max_retries=3, base_delay=0.01, track_stats=True)

        mock_func = Mock(side_effect=[NetworkError("Failed"), NetworkError("Failed"), "success"])

        handler.execute(mock_func)

        stats = handler.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["total_retries"] == 2

    def test_track_failures(self):
        """Test tracking of failures."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, track_stats=True)

        mock_func = Mock(side_effect=NetworkError("Always fails"))

        try:
            handler.execute(mock_func)
        except NetworkError:
            pass

        stats = handler.get_stats()
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 1
        assert stats["total_retries"] == 2

    def test_reset_stats(self):
        """Test resetting statistics."""
        handler = RetryHandler(max_retries=2, base_delay=0.01, track_stats=True)

        # Make some calls
        mock_func = Mock(return_value="success")
        handler.execute(mock_func)
        handler.execute(mock_func)

        # Reset stats
        handler.reset_stats()

        stats = handler.get_stats()
        assert stats["total_calls"] == 0
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 0
