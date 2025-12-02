"""Tests for RateLimitHandler.

Tests the rate limit handler using the actual implementation API:
- RateLimitHandler() - no arguments in constructor
- parse_retry_after(headers: Mapping[str, str]) -> float | None
- handle_429(headers, response_body, request_id) -> RateLimitError

Note: RateLimitHandler takes NO constructor arguments.

Testing pyramid target: 60% unit tests
"""

from datetime import UTC, datetime
from email.utils import formatdate


class TestRateLimitHandlerImport:
    """Tests for RateLimitHandler import and instantiation."""

    def test_import_rate_limit_handler(self) -> None:
        """Test that RateLimitHandler can be imported."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        assert RateLimitHandler is not None

    def test_create_rate_limit_handler(self) -> None:
        """Test creating RateLimitHandler with no arguments."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        assert handler is not None


class TestParseRetryAfterInteger:
    """Tests for parsing Retry-After as integer (seconds)."""

    def test_parse_retry_after_integer_string(self) -> None:
        """Test parsing Retry-After header with integer value."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "60"}
        delay = handler.parse_retry_after(headers)

        assert delay == 60.0

    def test_parse_retry_after_integer_small_value(self) -> None:
        """Test parsing Retry-After with small integer value."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "5"}
        delay = handler.parse_retry_after(headers)

        assert delay == 5.0

    def test_parse_retry_after_zero(self) -> None:
        """Test parsing Retry-After with zero value."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "0"}
        delay = handler.parse_retry_after(headers)

        assert delay == 0.0

    def test_parse_retry_after_case_insensitive(self) -> None:
        """Test that Retry-After header lookup is case-insensitive."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        # Test various cases
        for key in ["Retry-After", "retry-after", "RETRY-AFTER"]:
            headers = {key: "30"}
            delay = handler.parse_retry_after(headers)
            assert delay == 30.0, f"Failed for header key: {key}"


class TestParseRetryAfterHTTPDate:
    """Tests for parsing Retry-After as HTTP-date format."""

    def test_parse_retry_after_http_date(self) -> None:
        """Test parsing Retry-After header with HTTP-date value."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        # Create a date 60 seconds in the future
        future_time = datetime.now(UTC).timestamp() + 60
        http_date = formatdate(future_time, usegmt=True)

        headers = {"Retry-After": http_date}
        delay = handler.parse_retry_after(headers)

        # Should be approximately 60 seconds (allow some tolerance)
        assert delay is not None
        assert 55 <= delay <= 65

    def test_parse_retry_after_past_date_returns_zero_or_none(self) -> None:
        """Test that past date returns 0 or None."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        # Create a date in the past
        past_time = datetime.now(UTC).timestamp() - 60
        http_date = formatdate(past_time, usegmt=True)

        headers = {"Retry-After": http_date}
        delay = handler.parse_retry_after(headers)

        # Past date should return 0 or None
        if delay is not None:
            assert delay <= 1  # Should be very small or zero


class TestMissingRetryAfter:
    """Tests for handling missing Retry-After header."""

    def test_missing_retry_after_returns_none(self) -> None:
        """Test that missing Retry-After returns None."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Content-Type": "application/json"}  # No Retry-After
        delay = handler.parse_retry_after(headers)

        assert delay is None

    def test_empty_headers_returns_none(self) -> None:
        """Test that empty headers returns None."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers: dict[str, str] = {}
        delay = handler.parse_retry_after(headers)

        assert delay is None


class TestInvalidRetryAfter:
    """Tests for handling invalid Retry-After values."""

    def test_invalid_string_returns_none(self) -> None:
        """Test that invalid string returns None."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "not_a_number"}
        delay = handler.parse_retry_after(headers)

        assert delay is None  # Falls back to None for invalid

    def test_negative_integer_handling(self) -> None:
        """Test handling of negative integer value."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "-30"}
        delay = handler.parse_retry_after(headers)

        # Implementation parses as float directly, returns -30.0
        assert delay == -30.0

    def test_malformed_date_returns_none(self) -> None:
        """Test that malformed HTTP-date returns None."""
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "Not a valid date format"}
        delay = handler.parse_retry_after(headers)

        assert delay is None  # Falls back to None for invalid


class TestHandle429:
    """Tests for handle_429 method that creates RateLimitError."""

    def test_handle_429_creates_rate_limit_error(self) -> None:
        """Test that handle_429 creates RateLimitError."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "60"}
        response_body = '{"error": "rate_limited"}'
        request_id = "req-123"

        error = handler.handle_429(headers, response_body, request_id)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429
        assert error.retry_after == 60.0
        assert error.response_body == response_body
        assert error.request_id == request_id

    def test_handle_429_without_retry_after(self) -> None:
        """Test handle_429 when Retry-After header is missing."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers: dict[str, str] = {}
        response_body = '{"error": "rate_limited"}'
        request_id = None

        error = handler.handle_429(headers, response_body, request_id)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429
        # retry_after should be None when not provided
        assert error.retry_after is None

    def test_handle_429_with_empty_body(self) -> None:
        """Test handle_429 with empty response body."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        headers = {"Retry-After": "30"}
        response_body = ""
        request_id = "req-456"

        error = handler.handle_429(headers, response_body, request_id)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 30.0
        assert error.response_body == ""

    def test_handle_429_with_http_date(self) -> None:
        """Test handle_429 with HTTP-date Retry-After."""
        from amplihack.utils.api_client.exceptions import RateLimitError
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        handler = RateLimitHandler()

        # Create a date 30 seconds in the future
        future_time = datetime.now(UTC).timestamp() + 30
        http_date = formatdate(future_time, usegmt=True)

        headers = {"Retry-After": http_date}
        response_body = '{"error": "rate_limited"}'
        request_id = "req-789"

        error = handler.handle_429(headers, response_body, request_id)

        assert isinstance(error, RateLimitError)
        assert error.status_code == 429
        # Should have parsed the date and calculated delay
        assert error.retry_after is not None
        assert 25 <= error.retry_after <= 35
