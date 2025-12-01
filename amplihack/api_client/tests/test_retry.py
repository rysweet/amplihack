"""Unit tests fer API Client retry logic.

Tests the RetryConfig dataclass, RetryStrategy enum,
backoff calculations, and retry decision logic.

Testing pyramid: Unit tests (60%)
"""

import pytest

# Imports will fail initially - this be TDD!
from amplihack.api_client.retry import RetryConfig, RetryStrategy


class TestRetryStrategy:
    """Test RetryStrategy enum."""

    def test_retry_strategy_exponential_exists(self) -> None:
        """Verify EXPONENTIAL strategy exists."""
        # Act & Assert
        assert hasattr(RetryStrategy, "EXPONENTIAL")
        assert RetryStrategy.EXPONENTIAL.value == "exponential"

    def test_retry_strategy_linear_exists(self) -> None:
        """Verify LINEAR strategy exists."""
        # Act & Assert
        assert hasattr(RetryStrategy, "LINEAR")
        assert RetryStrategy.LINEAR.value == "linear"


class TestRetryConfigDefaults:
    """Test RetryConfig default values."""

    def test_retry_config_default_values(self) -> None:
        """Verify RetryConfig has correct default values."""
        # Act
        config = RetryConfig()

        # Assert
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.strategy == RetryStrategy.EXPONENTIAL
        assert config.jitter is True

    def test_retry_config_custom_values(self) -> None:
        """Verify RetryConfig accepts custom values."""
        # Arrange
        max_attempts = 5
        initial_delay = 2.0
        max_delay = 120.0
        strategy = RetryStrategy.LINEAR
        jitter = False

        # Act
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            strategy=strategy,
            jitter=jitter,
        )

        # Assert
        assert config.max_attempts == max_attempts
        assert config.initial_delay == initial_delay
        assert config.max_delay == max_delay
        assert config.strategy == strategy
        assert config.jitter == jitter


class TestExponentialBackoff:
    """Test exponential backoff delay calculations."""

    def test_exponential_backoff_first_attempt(self) -> None:
        """Verify exponential backoff calculates delay fer attempt 1."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL, jitter=False)

        # Act
        delay = config.calculate_delay(1)

        # Assert
        assert delay == 2.0  # 1 * 2^1

    def test_exponential_backoff_second_attempt(self) -> None:
        """Verify exponential backoff calculates delay fer attempt 2."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL, jitter=False)

        # Act
        delay = config.calculate_delay(2)

        # Assert
        assert delay == 4.0  # 1 * 2^2

    def test_exponential_backoff_third_attempt(self) -> None:
        """Verify exponential backoff calculates delay fer attempt 3."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL, jitter=False)

        # Act
        delay = config.calculate_delay(3)

        # Assert
        assert delay == 8.0  # 1 * 2^3

    def test_exponential_backoff_with_custom_initial_delay(self) -> None:
        """Verify exponential backoff uses custom initial delay."""
        # Arrange
        config = RetryConfig(initial_delay=0.5, strategy=RetryStrategy.EXPONENTIAL, jitter=False)

        # Act
        delay = config.calculate_delay(1)

        # Assert
        assert delay == 1.0  # 0.5 * 2^1

    def test_exponential_backoff_respects_max_delay(self) -> None:
        """Verify exponential backoff caps at max_delay."""
        # Arrange
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=5.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )

        # Act
        delay = config.calculate_delay(10)  # Would be 1024 without cap

        # Assert
        assert delay == 5.0


class TestLinearBackoff:
    """Test linear backoff delay calculations."""

    def test_linear_backoff_first_attempt(self) -> None:
        """Verify linear backoff calculates delay fer attempt 1."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.LINEAR, jitter=False)

        # Act
        delay = config.calculate_delay(1)

        # Assert
        assert delay == 2.0  # 1 + (1 * 1)

    def test_linear_backoff_second_attempt(self) -> None:
        """Verify linear backoff calculates delay fer attempt 2."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.LINEAR, jitter=False)

        # Act
        delay = config.calculate_delay(2)

        # Assert
        assert delay == 3.0  # 1 + (1 * 2)

    def test_linear_backoff_third_attempt(self) -> None:
        """Verify linear backoff calculates delay fer attempt 3."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.LINEAR, jitter=False)

        # Act
        delay = config.calculate_delay(3)

        # Assert
        assert delay == 4.0  # 1 + (1 * 3)

    def test_linear_backoff_with_custom_initial_delay(self) -> None:
        """Verify linear backoff uses custom initial delay."""
        # Arrange
        config = RetryConfig(initial_delay=2.0, strategy=RetryStrategy.LINEAR, jitter=False)

        # Act
        delay = config.calculate_delay(1)

        # Assert
        assert delay == 4.0  # 2 + (2 * 1)

    def test_linear_backoff_respects_max_delay(self) -> None:
        """Verify linear backoff caps at max_delay."""
        # Arrange
        config = RetryConfig(
            initial_delay=1.0,
            max_delay=5.0,
            strategy=RetryStrategy.LINEAR,
            jitter=False,
        )

        # Act
        delay = config.calculate_delay(10)  # Would be 11 without cap

        # Assert
        assert delay == 5.0


class TestJitter:
    """Test jitter application to delays."""

    def test_jitter_adds_randomness(self) -> None:
        """Verify jitter adds randomness to calculated delay."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL, jitter=True)

        # Act - calculate delay multiple times
        delays = [config.calculate_delay(1) for _ in range(10)]

        # Assert - delays should vary but be within reasonable bounds
        assert len(set(delays)) > 1  # Not all the same
        assert all(0.5 <= d <= 3.0 for d in delays)  # Within reasonable range

    def test_jitter_disabled_returns_consistent_delay(self) -> None:
        """Verify disabled jitter returns consistent delays."""
        # Arrange
        config = RetryConfig(initial_delay=1.0, strategy=RetryStrategy.EXPONENTIAL, jitter=False)

        # Act - calculate delay multiple times
        delays = [config.calculate_delay(1) for _ in range(10)]

        # Assert - all delays should be identical
        assert len(set(delays)) == 1
        assert all(d == 2.0 for d in delays)


class TestShouldRetry:
    """Test retry decision logic."""

    def test_should_retry_on_500_error(self) -> None:
        """Verify should_retry returns True fer 500 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=500, attempt=1)

        # Assert
        assert should_retry is True

    def test_should_retry_on_502_error(self) -> None:
        """Verify should_retry returns True fer 502 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=502, attempt=1)

        # Assert
        assert should_retry is True

    def test_should_retry_on_503_error(self) -> None:
        """Verify should_retry returns True fer 503 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=503, attempt=1)

        # Assert
        assert should_retry is True

    def test_should_retry_on_504_error(self) -> None:
        """Verify should_retry returns True fer 504 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=504, attempt=1)

        # Assert
        assert should_retry is True

    def test_should_retry_on_429_rate_limit(self) -> None:
        """Verify should_retry returns True fer 429 status (rate limiting)."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=429, attempt=1)

        # Assert
        assert should_retry is True

    def test_should_not_retry_on_400_error(self) -> None:
        """Verify should_retry returns False fer 400 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=400, attempt=1)

        # Assert
        assert should_retry is False

    def test_should_not_retry_on_401_error(self) -> None:
        """Verify should_retry returns False fer 401 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=401, attempt=1)

        # Assert
        assert should_retry is False

    def test_should_not_retry_on_403_error(self) -> None:
        """Verify should_retry returns False fer 403 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=403, attempt=1)

        # Assert
        assert should_retry is False

    def test_should_not_retry_on_404_error(self) -> None:
        """Verify should_retry returns False fer 404 status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=404, attempt=1)

        # Assert
        assert should_retry is False

    def test_should_not_retry_on_2xx_success(self) -> None:
        """Verify should_retry returns False fer 2xx status."""
        # Arrange
        config = RetryConfig()

        # Act
        should_retry = config.should_retry(status_code=200, attempt=1)

        # Assert
        assert should_retry is False

    def test_should_not_retry_when_max_attempts_exceeded(self) -> None:
        """Verify should_retry returns False when max attempts exceeded."""
        # Arrange
        config = RetryConfig(max_attempts=3)

        # Act
        should_retry = config.should_retry(status_code=500, attempt=3)

        # Assert
        assert should_retry is False

    def test_should_retry_within_max_attempts(self) -> None:
        """Verify should_retry returns True within max attempts."""
        # Arrange
        config = RetryConfig(max_attempts=3)

        # Act & Assert
        assert config.should_retry(status_code=500, attempt=1) is True
        assert config.should_retry(status_code=500, attempt=2) is True
        assert config.should_retry(status_code=500, attempt=3) is False


class TestRetryConfigValidation:
    """Test RetryConfig validation logic."""

    def test_invalid_max_attempts_raises_error(self) -> None:
        """Verify RetryConfig raises error fer invalid max_attempts."""
        # Act & Assert
        with pytest.raises(ValueError, match="max_attempts must be positive"):
            RetryConfig(max_attempts=0)

    def test_invalid_initial_delay_raises_error(self) -> None:
        """Verify RetryConfig raises error fer invalid initial_delay."""
        # Act & Assert
        with pytest.raises(ValueError, match="initial_delay must be positive"):
            RetryConfig(initial_delay=-1.0)

    def test_invalid_max_delay_raises_error(self) -> None:
        """Verify RetryConfig raises error fer invalid max_delay."""
        # Act & Assert
        with pytest.raises(ValueError, match="max_delay must be positive"):
            RetryConfig(max_delay=0.0)

    def test_max_delay_less_than_initial_delay_raises_error(self) -> None:
        """Verify RetryConfig raises error when max_delay < initial_delay."""
        # Act & Assert
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):
            RetryConfig(initial_delay=10.0, max_delay=5.0)
