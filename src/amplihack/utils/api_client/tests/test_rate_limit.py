"""
Test suite for rate limiting functionality.

Tests HTTP 429 detection and handling, Retry-After header parsing (both seconds
and HTTP-date formats), max wait time bounds, and RateLimitError scenarios.

Testing Philosophy:
- Unit tests for rate limit handler logic
- Mock time.sleep to avoid slow tests
- Test both Retry-After header formats
- Verify security bounds (max wait time)
"""

from datetime import UTC, datetime, timedelta
from email.utils import formatdate
from unittest.mock import patch

import pytest
import responses

from amplihack.utils.api_client import (
    APIClient,
    RateLimitConfig,
    RateLimitError,
)


class TestRateLimitConfiguration:
    """Test RateLimitConfig dataclass and configuration"""

    def test_default_rate_limit_config(self):
        """Test default rate limit configuration values"""
        config = RateLimitConfig()

        assert config.max_wait_time == 300.0  # 5 minutes
        assert config.respect_retry_after is True
        assert config.default_backoff == 60.0  # 1 minute

    def test_custom_rate_limit_config(self):
        """Test custom rate limit configuration"""
        config = RateLimitConfig(
            max_wait_time=600.0,
            respect_retry_after=False,
            default_backoff=120.0,
        )

        assert config.max_wait_time == 600.0
        assert config.respect_retry_after is False
        assert config.default_backoff == 120.0

    def test_conservative_rate_limit_config(self):
        """Test conservative rate limit configuration"""
        config = RateLimitConfig(
            max_wait_time=600.0,  # 10 minutes
            respect_retry_after=True,
            default_backoff=120.0,  # 2 minutes
        )

        assert config.max_wait_time == 600.0
        assert config.default_backoff == 120.0


class Test429Detection:
    """Test detection of HTTP 429 (Too Many Requests)"""

    @responses.activate
    def test_429_raises_rate_limit_error(self):
        """Test 429 response raises RateLimitError"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(max_wait_time=30.0),  # Exceeds wait time
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        assert exc_info.value.status_code == 429

    @responses.activate
    def test_429_error_attributes(self):
        """Test RateLimitError contains correct attributes"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "120"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(max_wait_time=60.0),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        error = exc_info.value
        assert error.wait_time == 120.0
        assert error.retry_after == "120"
        assert error.status_code == 429


class TestRetryAfterHeaderSeconds:
    """Test parsing of Retry-After header in seconds format"""

    @responses.activate
    def test_retry_after_seconds_format(self):
        """Test Retry-After header with seconds value"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            # After waiting, subsequent request succeeds
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")

            # Verify we waited the specified time
            mock_sleep.assert_called_once_with(60.0)
            assert response.status_code == 200

    @responses.activate
    def test_retry_after_large_seconds_value(self):
        """Test Retry-After with large seconds value"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "300"},  # 5 minutes
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=600.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")
            mock_sleep.assert_called_once_with(300.0)

    @responses.activate
    def test_retry_after_zero_seconds(self):
        """Test Retry-After with 0 seconds"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "0"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(respect_retry_after=True),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")
            # Should not sleep for 0 seconds (or very brief sleep)
            assert mock_sleep.call_count <= 1


class TestRetryAfterHeaderHTTPDate:
    """Test parsing of Retry-After header in HTTP-date format"""

    @responses.activate
    def test_retry_after_http_date_format(self):
        """Test Retry-After header with HTTP-date format"""
        # Create a future timestamp (60 seconds from now)
        future_time = datetime.now(UTC) + timedelta(seconds=60)
        http_date = formatdate(timeval=future_time.timestamp(), usegmt=True)

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": http_date},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")

            # Should wait approximately 60 seconds
            sleep_call = mock_sleep.call_args[0][0]
            assert 55.0 <= sleep_call <= 65.0  # Allow 5s tolerance

    @responses.activate
    def test_retry_after_http_date_in_past(self):
        """Test Retry-After with HTTP-date in the past"""
        # Create a past timestamp
        past_time = datetime.now(UTC) - timedelta(seconds=60)
        http_date = formatdate(timeval=past_time.timestamp(), usegmt=True)

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": http_date},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(respect_retry_after=True),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")

            # Should not wait (or minimal wait)
            if mock_sleep.called:
                assert mock_sleep.call_args[0][0] <= 1.0


class TestMaxWaitTimeBounds:
    """Test max wait time enforcement for security"""

    @responses.activate
    def test_max_wait_time_exceeded_raises_error(self):
        """Test RateLimitError raised when wait time exceeds max"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "600"},  # 10 minutes
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=300.0,  # Max 5 minutes
                respect_retry_after=True,
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        error = exc_info.value
        assert error.wait_time == 600.0
        assert error.wait_time > 300.0  # Exceeds max

    @responses.activate
    def test_max_wait_time_not_exceeded_waits(self):
        """Test request waits when within max wait time"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,  # Max 2 minutes
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")

            # Should wait since 60s < 120s max
            mock_sleep.assert_called_once_with(60.0)
            assert response.status_code == 200

    @responses.activate
    def test_max_wait_time_security_prevents_indefinite_wait(self):
        """Test max wait time prevents malicious infinite waits"""
        # Malicious API tries to make us wait forever
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "999999"},  # ~11 days
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=300.0,  # Reasonable 5 minute max
                respect_retry_after=True,
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        # Should reject the excessive wait time
        assert exc_info.value.wait_time == 999999.0
        assert exc_info.value.wait_time > client.rate_limit_config.max_wait_time


class TestDefaultBackoff:
    """Test default backoff when Retry-After header is missing"""

    @responses.activate
    def test_missing_retry_after_uses_default_backoff(self):
        """Test default backoff used when Retry-After header missing"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            # No Retry-After header
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                default_backoff=120.0,  # 2 minutes
                max_wait_time=300.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            response = client.get("/resource")

            # Should use default backoff
            mock_sleep.assert_called_once_with(120.0)

    @responses.activate
    def test_default_backoff_respects_max_wait_time(self):
        """Test default backoff is capped by max wait time"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                default_backoff=600.0,  # 10 minutes
                max_wait_time=300.0,  # Max 5 minutes
                respect_retry_after=True,
            ),
        )

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        # Should reject since default_backoff > max_wait_time
        assert exc_info.value.wait_time >= client.rate_limit_config.max_wait_time


class TestRespectRetryAfterFlag:
    """Test respect_retry_after configuration flag"""

    @responses.activate
    def test_respect_retry_after_true(self):
        """Test respect_retry_after=True honors Retry-After header"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            client.get("/resource")

            # Should wait the specified time
            mock_sleep.assert_called_once_with(60.0)

    @responses.activate
    def test_respect_retry_after_false_uses_default(self):
        """Test respect_retry_after=False ignores Retry-After header"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "10"},  # Specify 10 seconds
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,
                respect_retry_after=False,  # Ignore header
                default_backoff=30.0,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            client.get("/resource")

            # Should use default_backoff, not Retry-After value
            mock_sleep.assert_called_once_with(30.0)


class TestRateLimitRetryFlow:
    """Test complete rate limit retry flow"""

    @responses.activate
    def test_rate_limit_then_success(self):
        """Test rate limit followed by successful retry"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "2"},
        )

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"data": "success"},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=10.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep"):
            response = client.get("/resource")

        assert response.status_code == 200
        assert response.data == {"data": "success"}

    @responses.activate
    def test_multiple_rate_limits_sequential(self):
        """Test handling multiple sequential rate limits"""
        # First rate limit
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "1"},
        )

        # Second rate limit
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "2"},
        )

        # Finally success
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            json={"success": True},
            status=200,
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=10.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            response = client.get("/resource")

        assert response.status_code == 200
        # Should have waited twice
        assert mock_sleep.call_count == 2


class TestRateLimitLogging:
    """Test logging of rate limit events"""

    @responses.activate
    def test_rate_limit_logged_at_warning_level(self, caplog):
        """Test rate limit events are logged at WARNING level"""
        import logging

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "60"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                max_wait_time=120.0,
                respect_retry_after=True,
            ),
        )

        with caplog.at_level(logging.WARNING):
            with patch("time.sleep"):
                responses.add(
                    responses.GET,
                    "https://api.example.com/resource",
                    json={"success": True},
                    status=200,
                )

                client.get("/resource")

        # Verify rate limit was logged
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_logs) > 0
        assert any(
            "rate" in msg.lower() or "429" in msg for msg in [r.message for r in warning_logs]
        )

    @responses.activate
    def test_wait_time_logged(self, caplog):
        """Test wait time is included in log messages"""
        import logging

        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "30"},
        )

        client = APIClient(base_url="https://api.example.com")

        with caplog.at_level(logging.WARNING):
            with patch("time.sleep"):
                responses.add(
                    responses.GET,
                    "https://api.example.com/resource",
                    json={"success": True},
                    status=200,
                )

                client.get("/resource")

        # Verify wait time appears in logs
        log_messages = [r.message for r in caplog.records]
        assert any("30" in msg or "wait" in msg.lower() for msg in log_messages)


class TestInvalidRetryAfterHeader:
    """Test handling of invalid Retry-After header values"""

    @responses.activate
    def test_invalid_retry_after_uses_default(self):
        """Test invalid Retry-After value falls back to default"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "invalid-value"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                default_backoff=60.0,
                max_wait_time=120.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            client.get("/resource")

            # Should fall back to default_backoff
            mock_sleep.assert_called_once_with(60.0)

    @responses.activate
    def test_negative_retry_after_uses_default(self):
        """Test negative Retry-After value falls back to default"""
        responses.add(
            responses.GET,
            "https://api.example.com/resource",
            status=429,
            headers={"Retry-After": "-10"},
        )

        client = APIClient(
            base_url="https://api.example.com",
            rate_limit_config=RateLimitConfig(
                default_backoff=30.0,
                max_wait_time=60.0,
                respect_retry_after=True,
            ),
        )

        with patch("time.sleep") as mock_sleep:
            responses.add(
                responses.GET,
                "https://api.example.com/resource",
                json={"success": True},
                status=200,
            )

            client.get("/resource")

            # Should use default backoff for invalid negative value
            mock_sleep.assert_called_once_with(30.0)
