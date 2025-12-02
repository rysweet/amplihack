"""Unit tests for RetryPolicy.

Tests exponential backoff calculation with jitter.
This is part of the 60% unit test coverage.
"""

from unittest.mock import patch

import pytest


class TestRetryPolicyDefaults:
    """Tests for RetryPolicy default configuration."""

    def test_default_max_retries(self):
        """Default max_retries should be 3."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert policy.max_retries == 3

    def test_default_base_delay(self):
        """Default base_delay should be 1.0 seconds."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert policy.base_delay == 1.0

    def test_default_max_delay(self):
        """Default max_delay should be 60.0 seconds."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert policy.max_delay == 60.0

    def test_default_retryable_status_codes(self):
        """Default retryable status codes should be {429, 500, 502, 503, 504}."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        expected = {429, 500, 502, 503, 504}
        assert policy.retryable_status_codes == expected


class TestRetryPolicyCustomConfiguration:
    """Tests for custom RetryPolicy configuration."""

    def test_custom_max_retries(self):
        """Should accept custom max_retries."""
        from api_client import RetryPolicy

        policy = RetryPolicy(max_retries=5)
        assert policy.max_retries == 5

    def test_custom_base_delay(self):
        """Should accept custom base_delay."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=0.5)
        assert policy.base_delay == 0.5

    def test_custom_max_delay(self):
        """Should accept custom max_delay."""
        from api_client import RetryPolicy

        policy = RetryPolicy(max_delay=30.0)
        assert policy.max_delay == 30.0

    def test_custom_retryable_status_codes(self):
        """Should accept custom retryable status codes."""
        from api_client import RetryPolicy

        custom_codes = {500, 503}
        policy = RetryPolicy(retryable_status_codes=custom_codes)
        assert policy.retryable_status_codes == custom_codes

    def test_zero_max_retries_valid(self):
        """Zero max_retries should be valid (no retries)."""
        from api_client import RetryPolicy

        policy = RetryPolicy(max_retries=0)
        assert policy.max_retries == 0

    def test_negative_max_retries_invalid(self):
        """Negative max_retries should raise ValueError."""
        from api_client import RetryPolicy

        with pytest.raises(ValueError):
            RetryPolicy(max_retries=-1)

    def test_negative_base_delay_invalid(self):
        """Negative base_delay should raise ValueError."""
        from api_client import RetryPolicy

        with pytest.raises(ValueError):
            RetryPolicy(base_delay=-1.0)

    def test_negative_max_delay_invalid(self):
        """Negative max_delay should raise ValueError."""
        from api_client import RetryPolicy

        with pytest.raises(ValueError):
            RetryPolicy(max_delay=-1.0)

    def test_base_delay_greater_than_max_delay_invalid(self):
        """base_delay > max_delay should raise ValueError."""
        from api_client import RetryPolicy

        with pytest.raises(ValueError):
            RetryPolicy(base_delay=100.0, max_delay=10.0)


class TestBackoffCalculation:
    """Tests for exponential backoff delay calculation."""

    def test_calculate_backoff_exists(self):
        """RetryPolicy should have calculate_backoff method."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert hasattr(policy, "calculate_backoff")
        assert callable(policy.calculate_backoff)

    def test_first_attempt_delay_bounded(self):
        """First attempt delay should be between 0 and base_delay * 2."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0)
        for _ in range(100):  # Test multiple times due to jitter
            delay = policy.calculate_backoff(attempt=0)
            assert 0 <= delay <= 2.0  # base_delay * 2^0 * 2 = 2.0 max

    def test_exponential_increase(self):
        """Delay cap should increase exponentially with attempt number."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0, max_delay=1000.0)

        # With jitter, we test that the theoretical max increases
        # attempt 0: max = min(1000, 1.0 * 2^0) = 1.0
        # attempt 1: max = min(1000, 1.0 * 2^1) = 2.0
        # attempt 2: max = min(1000, 1.0 * 2^2) = 4.0
        # attempt 3: max = min(1000, 1.0 * 2^3) = 8.0

        samples_per_attempt = 50
        for attempt in range(4):
            theoretical_max = min(policy.max_delay, policy.base_delay * (2**attempt))
            delays = [policy.calculate_backoff(attempt) for _ in range(samples_per_attempt)]

            # All delays should be <= theoretical_max
            for delay in delays:
                assert delay <= theoretical_max

    def test_max_delay_caps_backoff(self):
        """Delay should never exceed max_delay."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0, max_delay=10.0)

        for attempt in range(20):  # Even for high attempt numbers
            for _ in range(10):
                delay = policy.calculate_backoff(attempt)
                assert delay <= policy.max_delay

    def test_jitter_produces_variation(self):
        """calculate_backoff should produce varied results due to jitter."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0, max_delay=60.0)

        delays = [policy.calculate_backoff(attempt=2) for _ in range(100)]

        # With full jitter, we should see variation
        unique_delays = set(round(d, 6) for d in delays)
        assert len(unique_delays) > 1, "Jitter should produce varied delays"

    def test_delay_always_non_negative(self):
        """Delay should always be non-negative."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0)

        for attempt in range(10):
            for _ in range(20):
                delay = policy.calculate_backoff(attempt)
                assert delay >= 0

    @patch("random.random")
    def test_full_jitter_formula(self, mock_random):
        """Should use full jitter: random(0, min(max_delay, base_delay * 2^attempt))."""
        from api_client import RetryPolicy

        policy = RetryPolicy(base_delay=1.0, max_delay=60.0)

        # Test with known random values
        mock_random.return_value = 0.5

        # attempt 0: cap = min(60, 1 * 2^0) = 1.0, delay = 0.5 * 1.0 = 0.5
        delay = policy.calculate_backoff(attempt=0)
        assert abs(delay - 0.5) < 0.01

        # attempt 2: cap = min(60, 1 * 2^2) = 4.0, delay = 0.5 * 4.0 = 2.0
        delay = policy.calculate_backoff(attempt=2)
        assert abs(delay - 2.0) < 0.01

        # attempt 5: cap = min(60, 1 * 2^5) = 32.0, delay = 0.5 * 32.0 = 16.0
        delay = policy.calculate_backoff(attempt=5)
        assert abs(delay - 16.0) < 0.01

        # attempt 10: cap = min(60, 1 * 2^10) = 60.0, delay = 0.5 * 60.0 = 30.0
        delay = policy.calculate_backoff(attempt=10)
        assert abs(delay - 30.0) < 0.01


class TestRetryAfterParsing:
    """Tests for Retry-After header parsing."""

    def test_parse_retry_after_seconds(self):
        """Should parse Retry-After header with seconds value."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        # Retry-After: 120
        delay = policy.parse_retry_after("120")
        assert delay == 120.0

    def test_parse_retry_after_float_seconds(self):
        """Should parse Retry-After header with float seconds."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        delay = policy.parse_retry_after("30.5")
        assert delay == 30.5

    def test_parse_retry_after_http_date(self):
        """Should parse Retry-After header with HTTP-date format."""

        from api_client import RetryPolicy

        policy = RetryPolicy()

        # HTTP-date format: Wed, 21 Oct 2099 07:28:00 GMT (far future date)
        http_date = "Wed, 21 Oct 2099 07:28:00 GMT"
        delay = policy.parse_retry_after(http_date)

        # Should return the number of seconds until that time
        assert isinstance(delay, float)
        assert delay > 0  # Date is in the future

    def test_parse_retry_after_past_date_returns_zero(self):
        """Retry-After with past date should return 0 or minimal delay."""
        from api_client import RetryPolicy

        policy = RetryPolicy()

        # Past date
        http_date = "Wed, 21 Oct 2020 07:28:00 GMT"
        delay = policy.parse_retry_after(http_date)

        assert delay is not None and delay >= 0  # Should not be negative

    def test_parse_retry_after_invalid_returns_none(self):
        """Invalid Retry-After should return None."""
        from api_client import RetryPolicy

        policy = RetryPolicy()

        delay = policy.parse_retry_after("invalid-value")
        assert delay is None

    def test_parse_retry_after_empty_returns_none(self):
        """Empty Retry-After should return None."""
        from api_client import RetryPolicy

        policy = RetryPolicy()

        delay = policy.parse_retry_after("")
        assert delay is None

    def test_parse_retry_after_none_returns_none(self):
        """None Retry-After should return None."""
        from api_client import RetryPolicy

        policy = RetryPolicy()

        delay = policy.parse_retry_after(None)
        assert delay is None


class TestRetryableStatusCodeCheck:
    """Tests for checking if a status code is retryable."""

    def test_is_retryable_method_exists(self):
        """RetryPolicy should have is_retryable method."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert hasattr(policy, "is_retryable")
        assert callable(policy.is_retryable)

    @pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
    def test_default_retryable_codes(self, status_code):
        """Default retryable status codes should return True."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert policy.is_retryable(status_code) is True

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 405, 409, 422])
    def test_non_retryable_codes(self, status_code):
        """Non-retryable status codes should return False."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        assert policy.is_retryable(status_code) is False

    def test_custom_retryable_codes(self):
        """Custom retryable codes should be respected."""
        from api_client import RetryPolicy

        policy = RetryPolicy(retryable_status_codes={408, 500})

        assert policy.is_retryable(408) is True
        assert policy.is_retryable(500) is True
        assert policy.is_retryable(429) is False  # Not in custom set
        assert policy.is_retryable(502) is False  # Not in custom set


class TestRetryPolicyImmutability:
    """Tests that RetryPolicy is effectively immutable after creation."""

    def test_retryable_status_codes_is_copy(self):
        """Modifying the original set should not affect the policy."""
        from api_client import RetryPolicy

        codes = {500, 503}
        policy = RetryPolicy(retryable_status_codes=codes)

        # Modify original set
        codes.add(429)

        # Policy should not be affected
        assert 429 not in policy.retryable_status_codes

    def test_retryable_status_codes_not_modifiable(self):
        """Attempting to modify retryable_status_codes should not work."""
        from api_client import RetryPolicy

        policy = RetryPolicy()
        original = policy.retryable_status_codes.copy()

        # Attempt to modify (should either raise or be ignored)
        try:
            policy.retryable_status_codes.add(418)  # type: ignore[attr-defined]
        except (TypeError, AttributeError):
            pass  # Expected if using frozenset

        # Verify unchanged (works regardless of whether modification raised)
        assert policy.retryable_status_codes == original or 418 not in policy.retryable_status_codes
