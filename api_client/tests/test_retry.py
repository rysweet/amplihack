"""Tests for retry strategy logic.

TDD: These tests define the EXPECTED behavior of RetryStrategy.
All tests should FAIL until api_client/retry.py is implemented.

Testing pyramid: Unit tests (60% of total)
"""


class TestRetryStrategyInit:
    """Test RetryStrategy initialization."""

    def test_default_max_retries(self):
        """Default max_retries should be 3."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.max_retries == 3

    def test_default_backoff_factor(self):
        """Default backoff_factor should be 0.5."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.backoff_factor == 0.5

    def test_default_retry_on_status(self):
        """Default retry_on_status should be {429, 500, 502, 503, 504}."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.retry_on_status == {429, 500, 502, 503, 504}

    def test_custom_max_retries(self):
        """Should accept custom max_retries."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(max_retries=5)
        assert strategy.max_retries == 5

    def test_custom_backoff_factor(self):
        """Should accept custom backoff_factor."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=1.0)
        assert strategy.backoff_factor == 1.0

    def test_custom_retry_on_status(self):
        """Should accept custom retry_on_status codes."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(retry_on_status={500, 503})
        assert strategy.retry_on_status == {500, 503}


class TestShouldRetry:
    """Test RetryStrategy.should_retry method."""

    def test_should_retry_true_for_429(self):
        """should_retry returns True for 429 on first attempt."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=429) is True

    def test_should_retry_true_for_500(self):
        """should_retry returns True for 500 on first attempt."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=500) is True

    def test_should_retry_true_for_502(self):
        """should_retry returns True for 502."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=502) is True

    def test_should_retry_true_for_503(self):
        """should_retry returns True for 503."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=503) is True

    def test_should_retry_true_for_504(self):
        """should_retry returns True for 504."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=504) is True

    def test_should_retry_false_for_200(self):
        """should_retry returns False for successful 200."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=200) is False

    def test_should_retry_false_for_404(self):
        """should_retry returns False for 404 Not Found."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=404) is False

    def test_should_retry_false_for_400(self):
        """should_retry returns False for 400 Bad Request."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy()
        assert strategy.should_retry(attempt=0, status_code=400) is False

    def test_should_retry_false_when_max_retries_exceeded(self):
        """should_retry returns False when attempt >= max_retries."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(max_retries=3)

        # Attempts 0, 1, 2 should allow retry
        assert strategy.should_retry(attempt=0, status_code=500) is True
        assert strategy.should_retry(attempt=1, status_code=500) is True
        assert strategy.should_retry(attempt=2, status_code=500) is True

        # Attempt 3 should NOT allow retry (we've done 3 retries)
        assert strategy.should_retry(attempt=3, status_code=500) is False

    def test_should_retry_false_when_max_retries_zero(self):
        """should_retry returns False when max_retries is 0."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(max_retries=0)
        assert strategy.should_retry(attempt=0, status_code=500) is False

    def test_should_retry_with_custom_status_codes(self):
        """should_retry respects custom retry_on_status."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(retry_on_status={418})  # I'm a teapot

        assert strategy.should_retry(attempt=0, status_code=418) is True
        assert strategy.should_retry(attempt=0, status_code=500) is False


class TestGetDelay:
    """Test RetryStrategy.get_delay method."""

    def test_get_delay_first_attempt(self):
        """First retry delay should be backoff_factor (0.5s with default)."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)
        delay = strategy.get_delay(attempt=0)
        assert delay == 0.5

    def test_get_delay_second_attempt(self):
        """Second retry delay should be backoff_factor * 2 (1.0s with default)."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)
        delay = strategy.get_delay(attempt=1)
        assert delay == 1.0

    def test_get_delay_third_attempt(self):
        """Third retry delay should be backoff_factor * 4 (2.0s with default)."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)
        delay = strategy.get_delay(attempt=2)
        assert delay == 2.0

    def test_get_delay_exponential_backoff_pattern(self):
        """Verify exponential backoff: 0.5, 1.0, 2.0, 4.0, 8.0..."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)

        expected_delays = [0.5, 1.0, 2.0, 4.0, 8.0]
        for attempt, expected in enumerate(expected_delays):
            assert strategy.get_delay(attempt) == expected

    def test_get_delay_with_custom_backoff_factor(self):
        """Verify delays with custom backoff_factor of 1.0."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=1.0)

        expected_delays = [1.0, 2.0, 4.0, 8.0]
        for attempt, expected in enumerate(expected_delays):
            assert strategy.get_delay(attempt) == expected

    def test_get_delay_respects_retry_after(self):
        """get_delay should use retry_after when provided and larger."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)

        # retry_after is larger than calculated delay
        delay = strategy.get_delay(attempt=0, retry_after=30.0)
        assert delay == 30.0

    def test_get_delay_uses_calculated_when_larger_than_retry_after(self):
        """get_delay should use calculated delay if larger than retry_after."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)

        # For attempt=2, calculated is 2.0, retry_after is 0.5
        delay = strategy.get_delay(attempt=2, retry_after=0.5)
        # Should use the larger of the two (2.0)
        assert delay == 2.0

    def test_get_delay_retry_after_none(self):
        """get_delay should work normally when retry_after is None."""
        from api_client.retry import RetryStrategy

        strategy = RetryStrategy(backoff_factor=0.5)
        delay = strategy.get_delay(attempt=1, retry_after=None)
        assert delay == 1.0


class TestParseRetryAfter:
    """Test RetryStrategy.parse_retry_after static method."""

    def test_parse_retry_after_integer_seconds(self):
        """Should parse integer seconds."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("60")
        assert result == 60.0

    def test_parse_retry_after_float_seconds(self):
        """Should parse float seconds."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("30.5")
        assert result == 30.5

    def test_parse_retry_after_zero(self):
        """Should parse zero."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("0")
        assert result == 0.0

    def test_parse_retry_after_http_date_format(self):
        """Should parse HTTP-date format (RFC 7231)."""
        from api_client.retry import RetryStrategy

        # HTTP-date format: "Wed, 21 Oct 2015 07:28:00 GMT"
        # We test with a date that results in a reasonable positive delay
        http_date = "Wed, 02 Dec 2099 12:00:00 GMT"
        result = RetryStrategy.parse_retry_after(http_date)

        # Should return a positive float (seconds until that date)
        assert result is not None
        assert isinstance(result, float)
        assert result > 0

    def test_parse_retry_after_invalid_string(self):
        """Should return None for invalid input."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("invalid")
        assert result is None

    def test_parse_retry_after_empty_string(self):
        """Should return None for empty string."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("")
        assert result is None

    def test_parse_retry_after_negative_number(self):
        """Should return None for negative number."""
        from api_client.retry import RetryStrategy

        result = RetryStrategy.parse_retry_after("-10")
        assert result is None

    def test_parse_retry_after_past_http_date(self):
        """Should return 0 or small positive for past HTTP-date."""
        from api_client.retry import RetryStrategy

        # A date in the past
        http_date = "Mon, 01 Jan 2020 00:00:00 GMT"
        result = RetryStrategy.parse_retry_after(http_date)

        # Should return 0 or a very small positive value (not negative)
        assert result is not None
        assert result >= 0


class TestRetryStrategyExport:
    """Test that RetryStrategy is properly exported."""

    def test_retry_strategy_is_importable(self):
        """RetryStrategy should be importable from retry module."""
        from api_client.retry import RetryStrategy  # noqa: F401

        assert True
