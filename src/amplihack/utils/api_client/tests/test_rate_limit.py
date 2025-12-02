"""Tests for RateLimitHandler.

Tests the rate limit handler using the actual implementation API:
- RateLimitHandler(config: APIClientConfig)
- Parses Retry-After header
- Extracts rate limit info from headers

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

    def test_create_rate_limit_handler_with_config(self) -> None:
        """Test creating RateLimitHandler with APIClientConfig."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        assert handler.config == config

    def test_rate_limit_handler_default_values(self) -> None:
        """Test RateLimitHandler has expected default values."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        # Should have reasonable defaults for rate limit handling
        assert handler.default_retry_after >= 0
        assert handler.max_retry_after > 0


class TestParseRetryAfterInteger:
    """Tests for parsing Retry-After as integer (seconds)."""

    def test_parse_retry_after_integer_string(self) -> None:
        """Test parsing Retry-After header with integer value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "60"}
        delay = handler.parse_retry_after(headers)

        assert delay == 60

    def test_parse_retry_after_integer_small_value(self) -> None:
        """Test parsing Retry-After with small integer value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "5"}
        delay = handler.parse_retry_after(headers)

        assert delay == 5

    def test_parse_retry_after_zero(self) -> None:
        """Test parsing Retry-After with zero value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "0"}
        delay = handler.parse_retry_after(headers)

        assert delay == 0

    def test_parse_retry_after_case_insensitive(self) -> None:
        """Test that Retry-After header lookup is case-insensitive."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        # Test various cases
        for key in ["Retry-After", "retry-after", "RETRY-AFTER"]:
            headers = {key: "30"}
            delay = handler.parse_retry_after(headers)
            assert delay == 30, f"Failed for header key: {key}"


class TestParseRetryAfterHTTPDate:
    """Tests for parsing Retry-After as HTTP-date format."""

    def test_parse_retry_after_http_date(self) -> None:
        """Test parsing Retry-After header with HTTP-date value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        # Create a date 60 seconds in the future
        future_time = datetime.now(UTC).timestamp() + 60
        http_date = formatdate(future_time, usegmt=True)

        headers = {"Retry-After": http_date}
        delay = handler.parse_retry_after(headers)

        # Should be approximately 60 seconds (allow some tolerance)
        assert 55 <= delay <= 65

    def test_parse_retry_after_past_date_returns_zero(self) -> None:
        """Test that past date returns 0 or small delay."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        # Create a date in the past
        past_time = datetime.now(UTC).timestamp() - 60
        http_date = formatdate(past_time, usegmt=True)

        headers = {"Retry-After": http_date}
        delay = handler.parse_retry_after(headers)

        # Past date should return 0 or minimum delay
        assert delay >= 0
        assert delay <= 1  # Should be very small or zero


class TestMissingRetryAfter:
    """Tests for handling missing Retry-After header."""

    def test_missing_retry_after_returns_default(self) -> None:
        """Test that missing Retry-After returns default value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Content-Type": "application/json"}  # No Retry-After
        delay = handler.parse_retry_after(headers)

        assert delay == handler.default_retry_after

    def test_empty_headers_returns_default(self) -> None:
        """Test that empty headers returns default value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers: dict[str, str] = {}
        delay = handler.parse_retry_after(headers)

        assert delay == handler.default_retry_after


class TestMaxRetryAfterCap:
    """Tests for max_retry_after cap."""

    def test_retry_after_capped_at_max(self) -> None:
        """Test that Retry-After is capped at max_retry_after."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "999999"}  # Very large value
        delay = handler.parse_retry_after(headers)

        assert delay <= handler.max_retry_after

    def test_retry_after_not_capped_below_max(self) -> None:
        """Test that Retry-After is not capped when below max."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "60"}
        delay = handler.parse_retry_after(headers)

        assert delay == 60  # Not capped


class TestInvalidRetryAfter:
    """Tests for handling invalid Retry-After values."""

    def test_invalid_string_returns_default(self) -> None:
        """Test that invalid string returns default value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "not_a_number"}
        delay = handler.parse_retry_after(headers)

        assert delay == handler.default_retry_after  # Falls back to default

    def test_negative_integer_returns_default(self) -> None:
        """Test that negative integer returns default value."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "-30"}
        delay = handler.parse_retry_after(headers)

        # Should either return default or 0
        assert delay >= 0

    def test_malformed_date_returns_default(self) -> None:
        """Test that malformed HTTP-date returns default."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Retry-After": "Not a valid date format"}
        delay = handler.parse_retry_after(headers)

        assert delay == handler.default_retry_after  # Falls back to default


class TestRateLimitInfo:
    """Tests for extracting rate limit information from headers."""

    def test_extract_rate_limit_info(self) -> None:
        """Test extracting rate limit info from standard headers."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler, RateLimitInfo

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "45",
            "X-RateLimit-Reset": "1701532800",
        }

        info = handler.extract_rate_limit_info(headers)

        assert isinstance(info, RateLimitInfo)
        assert info.limit == 100
        assert info.remaining == 45
        assert info.reset_timestamp == 1701532800

    def test_extract_rate_limit_info_missing_headers(self) -> None:
        """Test extracting rate limit info when headers are missing."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {"Content-Type": "application/json"}

        info = handler.extract_rate_limit_info(headers)

        assert info is None or (info.limit is None and info.remaining is None)

    def test_extract_rate_limit_info_partial_headers(self) -> None:
        """Test extracting rate limit info with partial headers."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        headers = {
            "X-RateLimit-Remaining": "10",
        }

        info = handler.extract_rate_limit_info(headers)

        # Should handle partial info gracefully
        if info is not None:
            assert info.remaining == 10


class TestShouldThrottle:
    """Tests for proactive throttling based on remaining quota."""

    def test_should_throttle_when_near_limit(self) -> None:
        """Test that throttling is suggested when near rate limit."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler, RateLimitInfo

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        info = RateLimitInfo(limit=100, remaining=2, reset_timestamp=None)

        # When only 2 requests remaining out of 100, should throttle
        result = handler.should_throttle(info, threshold_percent=5)
        assert result is True

    def test_should_not_throttle_when_quota_available(self) -> None:
        """Test no throttling when plenty of quota available."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler, RateLimitInfo

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        info = RateLimitInfo(limit=100, remaining=90, reset_timestamp=None)

        result = handler.should_throttle(info, threshold_percent=5)
        assert result is False

    def test_should_throttle_with_custom_threshold(self) -> None:
        """Test throttling with custom threshold percentage."""
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.rate_limit import RateLimitHandler, RateLimitInfo

        config = APIClientConfig(base_url="https://api.example.com")
        handler = RateLimitHandler(config)

        info = RateLimitInfo(limit=100, remaining=15, reset_timestamp=None)

        # 15% remaining, should throttle at 20% threshold
        result = handler.should_throttle(info, threshold_percent=20)
        assert result is True

        # 15% remaining, should not throttle at 10% threshold
        result = handler.should_throttle(info, threshold_percent=10)
        assert result is False


class TestRateLimitInfoDataClass:
    """Tests for RateLimitInfo data class."""

    def test_import_rate_limit_info(self) -> None:
        """Test that RateLimitInfo can be imported."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        assert RateLimitInfo is not None

    def test_create_rate_limit_info(self) -> None:
        """Test creating RateLimitInfo with all fields."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        info = RateLimitInfo(
            limit=1000,
            remaining=750,
            reset_timestamp=1701532800,
        )

        assert info.limit == 1000
        assert info.remaining == 750
        assert info.reset_timestamp == 1701532800

    def test_rate_limit_info_with_none_values(self) -> None:
        """Test RateLimitInfo with None values."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        info = RateLimitInfo(
            limit=None,
            remaining=None,
            reset_timestamp=None,
        )

        assert info.limit is None
        assert info.remaining is None
        assert info.reset_timestamp is None

    def test_rate_limit_info_percentage_used(self) -> None:
        """Test percentage_used property."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        info = RateLimitInfo(limit=100, remaining=25, reset_timestamp=None)

        assert info.percentage_used == 75.0

    def test_rate_limit_info_percentage_remaining(self) -> None:
        """Test percentage_remaining property."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        info = RateLimitInfo(limit=100, remaining=25, reset_timestamp=None)

        assert info.percentage_remaining == 25.0

    def test_rate_limit_info_seconds_until_reset(self) -> None:
        """Test seconds_until_reset property."""
        from amplihack.utils.api_client.rate_limit import RateLimitInfo

        # Set reset time 60 seconds in the future
        future_timestamp = int(datetime.now(UTC).timestamp()) + 60

        info = RateLimitInfo(limit=100, remaining=10, reset_timestamp=future_timestamp)

        seconds = info.seconds_until_reset
        assert 55 <= seconds <= 65
