"""Tests for RetryHandler.

Tests the retry handler using the actual implementation API:
- RetryHandler(config: APIClientConfig)
- Uses config values: max_retries, retry_base_delay, retry_max_delay, retry_multiplier
- Provides: should_retry(), calculate_delay(), sleep()

Testing pyramid target: 60% unit tests
"""

import time
from unittest.mock import patch


class TestRetryHandlerImport:
    """Tests for RetryHandler import and instantiation."""

    def test_import_retry_handler(self) -> None:
        """Test that RetryHandler can be imported."""
        from amplihack.utils.api_client.retry import RetryHandler

        assert RetryHandler is not None

    def test_create_retry_handler_with_config(self) -> None:
        """Test creating RetryHandler with APIClientConfig."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RetryHandler(config)

        assert handler.config == config

    def test_retry_handler_uses_config_values(self) -> None:
        """Test that RetryHandler uses values from config."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=5,
            retry_base_delay=1.0,
            retry_max_delay=120.0,
            retry_multiplier=2.0,
        )
        handler = RetryHandler(config)

        # Should access values through config
        assert handler.config.max_retries == 5
        assert handler.config.retry_base_delay == 1.0
        assert handler.config.retry_max_delay == 120.0
        assert handler.config.retry_multiplier == 2.0


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_backoff_formula_attempt_0(self) -> None:
        """Test backoff delay for attempt 0 (first retry).

        Formula: base_delay * multiplier^0 = 0.5 * 1.5^0 = 0.5 seconds
        """
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.5,
            retry_multiplier=1.5,
        )
        handler = RetryHandler(config)

        delay = handler.calculate_delay(attempt=0)
        # Should be base_delay with some possible jitter
        assert 0.5 <= delay <= 0.75  # Base plus up to 50% jitter

    def test_backoff_formula_attempt_1(self) -> None:
        """Test backoff delay for attempt 1.

        Formula: 0.5 * 1.5^1 = 0.75 seconds
        """
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.5,
            retry_multiplier=1.5,
        )
        handler = RetryHandler(config)

        delay = handler.calculate_delay(attempt=1)
        # Should be around 0.75 with some jitter
        assert 0.75 <= delay <= 1.125

    def test_backoff_formula_attempt_2(self) -> None:
        """Test backoff delay for attempt 2.

        Formula: 0.5 * 1.5^2 = 1.125 seconds
        """
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.5,
            retry_multiplier=1.5,
        )
        handler = RetryHandler(config)

        delay = handler.calculate_delay(attempt=2)
        assert 1.0 <= delay <= 1.7  # Some tolerance for jitter

    def test_backoff_with_custom_base_and_multiplier(self) -> None:
        """Test backoff with custom base_delay and multiplier.

        Formula: 1.0 * 2.0^2 = 4.0 seconds
        """
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=1.0,
            retry_multiplier=2.0,
        )
        handler = RetryHandler(config)

        delay = handler.calculate_delay(attempt=2)
        assert 4.0 <= delay <= 6.0  # Base plus jitter


class TestMaxDelayCap:
    """Tests for max delay capping."""

    def test_delay_capped_at_max_delay(self) -> None:
        """Test that delay is capped at retry_max_delay."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.5,
            retry_multiplier=1.5,
            retry_max_delay=10.0,  # Set a low max for testing
        )
        handler = RetryHandler(config)

        # With high attempt number, would exceed max without capping
        delay = handler.calculate_delay(attempt=20)
        assert delay <= 10.0  # Should be capped

    def test_delay_not_capped_when_below_max(self) -> None:
        """Test delay is not capped when below max."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.5,
            retry_multiplier=1.5,
            retry_max_delay=60.0,
        )
        handler = RetryHandler(config)

        # Attempt 0: 0.5s - well below 60s
        delay = handler.calculate_delay(attempt=0)
        assert delay < 60.0


class TestJitter:
    """Tests for jitter (randomness) in backoff."""

    def test_jitter_adds_randomness(self) -> None:
        """Test that jitter adds randomness to delays."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=1.0,
            retry_multiplier=1.5,
        )
        handler = RetryHandler(config)

        # Run multiple times, delays should vary
        delays = [handler.calculate_delay(attempt=2) for _ in range(20)]
        unique_delays = set(delays)

        # With jitter, we should get different values
        # (allowing for rare case of identical values)
        assert len(unique_delays) > 1 or len(delays) < 3


class TestShouldRetry:
    """Tests for should_retry logic."""

    def test_should_retry_on_500(self) -> None:
        """Test that 500 Internal Server Error is retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=500, attempt=0) is True

    def test_should_retry_on_502(self) -> None:
        """Test that 502 Bad Gateway is retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=502, attempt=0) is True

    def test_should_retry_on_503(self) -> None:
        """Test that 503 Service Unavailable is retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=503, attempt=0) is True

    def test_should_retry_on_504(self) -> None:
        """Test that 504 Gateway Timeout is retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=504, attempt=0) is True

    def test_should_retry_on_429(self) -> None:
        """Test that 429 Too Many Requests is retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=429, attempt=0) is True

    def test_should_not_retry_on_400(self) -> None:
        """Test that 400 Bad Request is NOT retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=400, attempt=0) is False

    def test_should_not_retry_on_401(self) -> None:
        """Test that 401 Unauthorized is NOT retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=401, attempt=0) is False

    def test_should_not_retry_on_403(self) -> None:
        """Test that 403 Forbidden is NOT retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=403, attempt=0) is False

    def test_should_not_retry_on_404(self) -> None:
        """Test that 404 Not Found is NOT retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=404, attempt=0) is False

    def test_should_not_retry_on_200(self) -> None:
        """Test that 200 OK is NOT retryable (success!)."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=200, attempt=0) is False

    def test_should_not_retry_when_max_retries_exceeded(self) -> None:
        """Test that retry stops when max_retries exceeded."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        # Attempt 0, 1, 2 should allow retry
        assert handler.should_retry(status_code=500, attempt=0) is True
        assert handler.should_retry(status_code=500, attempt=1) is True
        assert handler.should_retry(status_code=500, attempt=2) is True

        # Attempt 3 should NOT allow retry (we've already tried 3 times)
        assert handler.should_retry(status_code=500, attempt=3) is False

    def test_should_retry_with_zero_max_retries(self) -> None:
        """Test that zero max_retries means no retries."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=0)
        handler = RetryHandler(config)

        assert handler.should_retry(status_code=500, attempt=0) is False


class TestRetryableStatusCodes:
    """Tests for retryable status codes."""

    def test_default_retryable_codes(self) -> None:
        """Test default list of retryable status codes."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        # These should be the default retryable codes
        retryable_codes = [429, 500, 502, 503, 504]
        for code in retryable_codes:
            assert handler.should_retry(status_code=code, attempt=0) is True

        # These should NOT be retryable
        non_retryable_codes = [400, 401, 403, 404, 200]
        for code in non_retryable_codes:
            assert handler.should_retry(status_code=code, attempt=0) is False


class TestRetryOnException:
    """Tests for retry behavior on exceptions."""

    def test_should_retry_on_connection_error(self) -> None:
        """Test that connection errors are retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        exc = ConnectionError("Connection refused")
        assert handler.should_retry_exception(exc, attempt=0) is True

    def test_should_retry_on_timeout_error(self) -> None:
        """Test that timeout errors are retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        exc = TimeoutError("Connection timed out")
        assert handler.should_retry_exception(exc, attempt=0) is True

    def test_should_not_retry_on_value_error(self) -> None:
        """Test that ValueError is NOT retryable."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=3)
        handler = RetryHandler(config)

        exc = ValueError("Invalid parameter")
        assert handler.should_retry_exception(exc, attempt=0) is False

    def test_should_not_retry_exception_when_max_exceeded(self) -> None:
        """Test exception retry stops when max_retries exceeded."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com", max_retries=2)
        handler = RetryHandler(config)

        exc = ConnectionError("Connection refused")
        assert handler.should_retry_exception(exc, attempt=0) is True
        assert handler.should_retry_exception(exc, attempt=1) is True
        assert handler.should_retry_exception(exc, attempt=2) is False


class TestSleepDelay:
    """Tests for actual sleep behavior."""

    def test_sleep_delays_execution(self) -> None:
        """Test that sleep method actually delays execution."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(
            base_url="https://api.example.com",
            retry_base_delay=0.1,  # Short delay for test
            retry_multiplier=1.5,
        )
        handler = RetryHandler(config)

        start = time.time()
        handler.sleep(attempt=0)  # Should sleep ~0.1s
        elapsed = time.time() - start

        assert elapsed >= 0.05  # Allow some tolerance
        assert elapsed < 0.3

    def test_sleep_can_be_mocked(self) -> None:
        """Test that sleep can be mocked for fast tests."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.retry import RetryHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RetryHandler(config)

        with patch("time.sleep") as mock_sleep:
            handler.sleep(attempt=5)
            mock_sleep.assert_called_once()
