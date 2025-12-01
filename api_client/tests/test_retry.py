"""Tests for RetryPolicy exponential backoff implementation.

Testing pyramid distribution:
- 90% Unit tests (retry decisions, backoff calculation, edge cases)
- 10% Integration tests (retry timing, jitter)
"""

import time
from unittest.mock import patch

import pytest


class TestRetryPolicyCreation:
    """Test RetryPolicy initialization and defaults."""

    def test_create_retry_policy_with_default(self):
        """Test creating RetryPolicy with default max_retries (3)."""
        from api_client.retry import RetryPolicy

        # Arrange & Act
        policy = RetryPolicy()

        # Assert
        assert policy is not None

    def test_create_retry_policy_with_custom_retries(self):
        """Test creating RetryPolicy with custom max_retries."""
        from api_client.retry import RetryPolicy

        # Arrange & Act
        policy = RetryPolicy(max_retries=5)

        # Assert
        assert policy is not None

    def test_create_retry_policy_with_zero_retries(self):
        """Test creating RetryPolicy with zero retries (no retries)."""
        from api_client.retry import RetryPolicy

        # Arrange & Act
        policy = RetryPolicy(max_retries=0)

        # Assert
        assert policy is not None

    def test_create_retry_policy_with_high_retries(self):
        """Test creating RetryPolicy with high max_retries (10)."""
        from api_client.retry import RetryPolicy

        # Arrange & Act
        policy = RetryPolicy(max_retries=10)

        # Assert
        assert policy is not None

    def test_create_retry_policy_rejects_negative_retries(self):
        """Test that negative max_retries raises ValueError."""
        from api_client.retry import RetryPolicy

        # Act & Assert
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryPolicy(max_retries=-1)


class TestRetryShouldRetry:
    """Test retry decision logic (which status codes should retry)."""

    def test_should_retry_on_500_error(self):
        """Test that 500 Internal Server Error should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=500, attempt=1) is True

    def test_should_retry_on_502_error(self):
        """Test that 502 Bad Gateway should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=502, attempt=1) is True

    def test_should_retry_on_503_error(self):
        """Test that 503 Service Unavailable should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=503, attempt=1) is True

    def test_should_retry_on_504_error(self):
        """Test that 504 Gateway Timeout should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=504, attempt=1) is True

    def test_should_not_retry_on_400_error(self):
        """Test that 400 Bad Request should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=400, attempt=1) is False

    def test_should_not_retry_on_401_error(self):
        """Test that 401 Unauthorized should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=401, attempt=1) is False

    def test_should_not_retry_on_403_error(self):
        """Test that 403 Forbidden should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=403, attempt=1) is False

    def test_should_not_retry_on_404_error(self):
        """Test that 404 Not Found should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=404, attempt=1) is False

    def test_should_not_retry_on_429_error(self):
        """Test that 429 Too Many Requests should NOT retry (client should handle rate limiting)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=429, attempt=1) is False

    def test_should_retry_on_network_error(self):
        """Test that network errors (status_code=None) should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        assert policy.should_retry(status_code=None, attempt=1) is True

    def test_should_not_retry_on_2xx_success(self):
        """Test that 2xx success codes should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert
        for status_code in [200, 201, 202, 204]:
            assert policy.should_retry(status_code=status_code, attempt=1) is False


class TestRetryMaxRetries:
    """Test max_retries enforcement."""

    def test_should_not_retry_when_max_retries_exceeded(self):
        """Test that retries stop after max_retries."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=3)

        # Act & Assert - attempts 1-3 should retry
        assert policy.should_retry(status_code=500, attempt=1) is True
        assert policy.should_retry(status_code=500, attempt=2) is True
        assert policy.should_retry(status_code=500, attempt=3) is True

        # Act & Assert - attempt 4 should NOT retry (exceeded max)
        assert policy.should_retry(status_code=500, attempt=4) is False

    def test_should_not_retry_when_max_retries_zero(self):
        """Test that no retries occur when max_retries=0."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=0)

        # Act & Assert - first attempt should not retry
        assert policy.should_retry(status_code=500, attempt=1) is False

    def test_should_retry_up_to_max_retries(self):
        """Test that retries work up to max_retries limit."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=5)

        # Act & Assert - attempts 1-5 should retry
        for attempt in range(1, 6):
            assert policy.should_retry(status_code=500, attempt=attempt) is True

        # Act & Assert - attempt 6 should NOT retry
        assert policy.should_retry(status_code=500, attempt=6) is False


class TestRetryBackoffCalculation:
    """Test exponential backoff delay calculation."""

    def test_get_backoff_first_retry(self):
        """Test backoff delay for first retry (should be 1 second)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act
        delay = policy.get_backoff(attempt=1)

        # Assert - first retry is 1 second (2^0 = 1)
        assert delay >= 0.75  # With jitter, allow 25% variation
        assert delay <= 1.25

    def test_get_backoff_second_retry(self):
        """Test backoff delay for second retry (should be 2 seconds)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act
        delay = policy.get_backoff(attempt=2)

        # Assert - second retry is 2 seconds (2^1 = 2)
        assert delay >= 1.5  # With jitter
        assert delay <= 2.5

    def test_get_backoff_third_retry(self):
        """Test backoff delay for third retry (should be 4 seconds)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act
        delay = policy.get_backoff(attempt=3)

        # Assert - third retry is 4 seconds (2^2 = 4)
        assert delay >= 3.0  # With jitter
        assert delay <= 5.0

    def test_get_backoff_exponential_growth(self):
        """Test that backoff grows exponentially."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act
        delays = [policy.get_backoff(attempt=i) for i in range(1, 6)]

        # Assert - each delay should be roughly double the previous
        # (allowing for jitter)
        for i in range(1, len(delays)):
            assert delays[i] > delays[i - 1]

    def test_get_backoff_with_jitter(self):
        """Test that backoff includes random jitter (±25%)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act - get multiple backoff values for same attempt
        delays = [policy.get_backoff(attempt=2) for _ in range(10)]

        # Assert - delays should vary (due to jitter)
        # Not all values should be identical
        assert len(set(delays)) > 1  # At least some variation

    def test_get_backoff_zero_attempt(self):
        """Test backoff for attempt 0 (edge case, should be minimal)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act
        delay = policy.get_backoff(attempt=0)

        # Assert - should be very small (2^-1 = 0.5)
        assert delay < 1.0

    def test_get_backoff_high_attempt(self):
        """Test backoff for high attempt number (should cap or grow large)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=10)

        # Act
        delay = policy.get_backoff(attempt=10)

        # Assert - should be large (2^9 = 512 seconds)
        # But may have a cap
        assert delay > 0


class TestRetryPolicyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_retry_all_5xx_errors(self):
        """Test that all 5xx errors should retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert - test range of 5xx codes
        for status_code in range(500, 600):
            assert policy.should_retry(status_code=status_code, attempt=1) is True

    def test_no_retry_all_4xx_errors(self):
        """Test that all 4xx errors should NOT retry."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act & Assert - test range of 4xx codes
        for status_code in range(400, 500):
            assert policy.should_retry(status_code=status_code, attempt=1) is False

    def test_retry_decision_consistent(self):
        """Test that retry decision is consistent for same inputs."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy()

        # Act - call multiple times with same inputs
        result1 = policy.should_retry(status_code=500, attempt=1)
        result2 = policy.should_retry(status_code=500, attempt=1)
        result3 = policy.should_retry(status_code=500, attempt=1)

        # Assert - should always return same decision
        assert result1 and result2 and result3

    def test_backoff_max_cap(self):
        """Test that backoff has a reasonable maximum cap."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=20)

        # Act
        delay = policy.get_backoff(attempt=20)

        # Assert - should not be absurdly large (e.g., should cap at some reasonable value)
        # Exponential would be 2^19 = 524288 seconds, but should have a cap
        assert delay < 3600  # Less than 1 hour


class TestRetryPolicyIntegration:
    """Integration tests for retry logic in realistic scenarios."""

    def test_retry_sequence_timing(self):
        """Test complete retry sequence with actual timing."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=3)

        # Act - simulate retry sequence
        attempt = 1
        total_wait = 0

        while policy.should_retry(status_code=500, attempt=attempt):
            backoff = policy.get_backoff(attempt=attempt)
            total_wait += backoff
            attempt += 1

        # Assert
        assert attempt == 4  # Made 3 retry attempts (attempts 1, 2, 3)
        # Total wait should be approximately 1 + 2 + 4 = 7 seconds (with jitter)
        assert total_wait >= 5.0
        assert total_wait <= 10.0

    @patch("time.sleep")
    def test_retry_with_sleep_mock(self, mock_sleep):
        """Test retry with mocked sleep (for speed)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=3)
        attempts = []

        # Act - simulate retries
        for attempt in range(1, 5):
            if policy.should_retry(status_code=503, attempt=attempt):
                backoff = policy.get_backoff(attempt=attempt)
                time.sleep(backoff)  # Will be mocked
                attempts.append(attempt)

        # Assert
        assert len(attempts) == 3  # Retried 3 times
        assert mock_sleep.call_count == 3

    def test_mixed_error_retry_behavior(self):
        """Test retry behavior with mixed error types."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=3)

        # Act & Assert - simulate sequence of different errors
        assert policy.should_retry(status_code=503, attempt=1) is True  # Retry
        assert policy.should_retry(status_code=500, attempt=2) is True  # Retry
        assert policy.should_retry(status_code=404, attempt=1) is False  # Don't retry
        assert policy.should_retry(status_code=502, attempt=3) is True  # Retry
        assert policy.should_retry(status_code=400, attempt=1) is False  # Don't retry

    def test_retry_until_success_pattern(self):
        """Test realistic retry-until-success pattern."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=5)
        mock_responses = [503, 503, 500, 200]  # Fail, fail, fail, success
        attempt = 0

        # Act
        for status_code in mock_responses:
            attempt += 1
            if status_code == 200:
                # Success, stop retrying
                break
            if not policy.should_retry(status_code=status_code, attempt=attempt):
                break

        # Assert - should succeed on 4th attempt
        assert attempt == 4
        assert mock_responses[attempt - 1] == 200

    def test_retry_until_max_retries_pattern(self):
        """Test realistic retry-until-max pattern (all retries exhausted)."""
        from api_client.retry import RetryPolicy

        # Arrange
        policy = RetryPolicy(max_retries=3)
        mock_responses = [500, 500, 500, 500, 500]  # All failures
        attempt = 0

        # Act
        for status_code in mock_responses:
            attempt += 1
            if not policy.should_retry(status_code=status_code, attempt=attempt):
                break

        # Assert - should stop after 3 retries (total 4 attempts)
        assert attempt == 4  # Initial + 3 retries
