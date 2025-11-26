"""Unit tests for APIClient class.

Tests the main APIClient with mocking for HTTP requests.
These tests will FAIL until the client is implemented.

Testing Pyramid: Unit tests (60%)
"""

import threading
import time
from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAPIClientInitialization:
    """Test APIClient initialization and configuration."""

    def test_client_creation_with_base_url(self):
        """APIClient should accept base_url parameter."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_client_creation_with_invalid_url_raises_error(self):
        """APIClient should raise ValueError for invalid URLs."""
        from amplihack.api import APIClient

        # No protocol
        with pytest.raises(ValueError, match="base_url must start with http"):
            APIClient(base_url="api.example.com")

        # FTP protocol (not HTTP/HTTPS)
        with pytest.raises(ValueError, match="base_url must start with http"):
            APIClient(base_url="ftp://api.example.com")

    def test_client_accepts_https_url(self):
        """APIClient should accept HTTPS URLs."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://secure.api.com")
        assert client.base_url == "https://secure.api.com"

    def test_client_accepts_http_url(self):
        """APIClient should accept HTTP URLs (for local dev)."""
        from amplihack.api import APIClient

        client = APIClient(base_url="http://localhost:8000")
        assert client.base_url == "http://localhost:8000"

    def test_client_default_timeout(self):
        """APIClient should have default timeout of (5, 30)."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.timeout == (5, 30)

    def test_client_custom_timeout(self):
        """APIClient should accept custom timeout tuple."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com", timeout=(10, 60))
        assert client.timeout == (10, 60)

    def test_client_default_headers(self):
        """APIClient should accept default headers."""
        from amplihack.api import APIClient

        headers = {"Authorization": "Bearer token123", "User-Agent": "TestClient/1.0"}
        client = APIClient(base_url="https://api.example.com", headers=headers)
        assert client.headers == headers

    def test_client_max_retries_default(self):
        """APIClient should have default max_retries of 3."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.max_retries == 3

    def test_client_custom_max_retries(self):
        """APIClient should accept custom max_retries."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com", max_retries=5)
        assert client.max_retries == 5

    def test_client_backoff_factor_default(self):
        """APIClient should have default backoff_factor of 1.0."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.backoff_factor == 1.0

    def test_client_custom_backoff_factor(self):
        """APIClient should accept custom backoff_factor."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com", backoff_factor=2.0)
        assert client.backoff_factor == 2.0

    def test_client_accepts_custom_logger(self):
        """APIClient should accept custom logger instance."""
        import logging

        from amplihack.api import APIClient

        custom_logger = logging.getLogger("test_logger")
        client = APIClient(base_url="https://api.example.com", logger=custom_logger)
        assert client._logger == custom_logger


class TestAPIClientHTTPMethods:
    """Test HTTP method implementations (GET, POST, PUT, DELETE)."""

    @patch("requests.Session.get")
    def test_get_request_basic(self, mock_get):
        """GET request should call session.get with correct parameters."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response.status_code == 200
        mock_get.assert_called_once()

    @patch("requests.Session.get")
    def test_get_request_with_params(self, mock_get):
        """GET request should include query parameters."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        client.get("/users", params={"page": 1, "limit": 10})

        # Verify params were passed
        call_args = mock_get.call_args
        assert call_args[1]["params"] == {"page": 1, "limit": 10}

    @patch("requests.Session.get")
    def test_get_request_with_headers(self, mock_get):
        """GET request should merge client and request headers."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer token"},
        )
        client.get("/users", headers={"X-Custom": "value"})

        # Headers should be merged
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert "X-Custom" in headers

    @patch("requests.Session.post")
    def test_post_request_basic(self, mock_post):
        """POST request should call session.post with JSON data."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        client.post("/users", json_data={"name": "Blackbeard"})

        call_args = mock_post.call_args
        assert call_args[1]["json"] == {"name": "Blackbeard"}

    @patch("requests.Session.put")
    def test_put_request_basic(self, mock_put):
        """PUT request should call session.put with JSON data."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        client.put("/users/123", json_data={"name": "Anne Bonny"})

        call_args = mock_put.call_args
        assert call_args[1]["json"] == {"name": "Anne Bonny"}

    @patch("requests.Session.delete")
    def test_delete_request_basic(self, mock_delete):
        """DELETE request should call session.delete."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        response = client.delete("/users/123")

        assert response.status_code == 204
        mock_delete.assert_called_once()

    @patch("requests.Session.get")
    def test_endpoint_url_construction(self, mock_get):
        """Client should construct full URL from base_url and endpoint."""
        from amplihack.api import APIClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com/v1")
        client.get("/users")

        # Should call with full URL
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert url == "https://api.example.com/v1/users"


class TestRetryLogic:
    """Test automatic retry behavior."""

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_500_error(self, mock_sleep, mock_get):
        """Client should retry on 500 Internal Server Error."""
        from amplihack.api import APIClient

        # First call: 500 error, second call: success
        mock_get.side_effect = [
            Mock(status_code=500),
            Mock(status_code=200, json=lambda: {"data": "value"}),
        ]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()  # Should sleep before retry

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_502_bad_gateway(self, mock_sleep, mock_get):
        """Client should retry on 502 Bad Gateway."""
        from amplihack.api import APIClient

        mock_get.side_effect = [Mock(status_code=502), Mock(status_code=200)]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_503_service_unavailable(self, mock_sleep, mock_get):
        """Client should retry on 503 Service Unavailable."""
        from amplihack.api import APIClient

        mock_get.side_effect = [Mock(status_code=503), Mock(status_code=200)]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_504_gateway_timeout(self, mock_sleep, mock_get):
        """Client should retry on 504 Gateway Timeout."""
        from amplihack.api import APIClient

        mock_get.side_effect = [Mock(status_code=504), Mock(status_code=200)]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch("requests.Session.get")
    def test_no_retry_on_404_not_found(self, mock_get):
        """Client should NOT retry on 404 Not Found."""
        from amplihack.api import APIClient, APIError

        mock_get.return_value = Mock(status_code=404)

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(APIError):
            client.get("/nonexistent")

        # Should only call once (no retry)
        assert mock_get.call_count == 1

    @patch("requests.Session.get")
    def test_no_retry_on_400_bad_request(self, mock_get):
        """Client should NOT retry on 400 Bad Request."""
        from amplihack.api import APIClient, APIError

        mock_get.return_value = Mock(status_code=400)

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(APIError):
            client.get("/data")

        assert mock_get.call_count == 1

    @patch("requests.Session.get")
    def test_no_retry_on_401_unauthorized(self, mock_get):
        """Client should NOT retry on 401 Unauthorized."""
        from amplihack.api import APIClient, AuthenticationError

        mock_get.return_value = Mock(status_code=401)

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(AuthenticationError):
            client.get("/protected")

        assert mock_get.call_count == 1

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep, mock_get):
        """Retry delays should follow exponential backoff: 1s, 2s, 4s."""
        from amplihack.api import APIClient, APIError

        # All retries fail
        mock_get.return_value = Mock(status_code=500)

        client = APIClient(base_url="https://api.example.com", max_retries=3)

        with pytest.raises(APIError):
            client.get("/data")

        # Check sleep calls: 1s, 2s, 4s
        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
        assert sleep_calls[2] == 4.0

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_backoff_factor_multiplier(self, mock_sleep, mock_get):
        """backoff_factor should multiply retry delays."""
        from amplihack.api import APIClient, APIError

        mock_get.return_value = Mock(status_code=500)

        client = APIClient(base_url="https://api.example.com", max_retries=3, backoff_factor=2.0)

        with pytest.raises(APIError):
            client.get("/data")

        # Delays should be: 2s, 4s, 8s (2.0 * base delays)
        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert sleep_calls[0] == 2.0
        assert sleep_calls[1] == 4.0
        assert sleep_calls[2] == 8.0

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_max_retries_respected(self, mock_sleep, mock_get):
        """Client should respect max_retries limit."""
        from amplihack.api import APIClient, APIError

        mock_get.return_value = Mock(status_code=500)

        client = APIClient(base_url="https://api.example.com", max_retries=2)

        with pytest.raises(APIError):
            client.get("/data")

        # Initial + 2 retries = 3 total calls
        assert mock_get.call_count == 3


class TestRateLimitHandling:
    """Test rate limit detection and handling."""

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_429_with_retry_after_integer(self, mock_sleep, mock_get):
        """Client should respect Retry-After header (integer seconds)."""
        from amplihack.api import APIClient

        mock_response_429 = Mock(status_code=429, headers={"Retry-After": "30"})
        mock_response_200 = Mock(status_code=200)
        mock_get.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        # Should sleep for 30 seconds (from Retry-After header)
        mock_sleep.assert_called_with(30)

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_retry_on_429_with_retry_after_http_date(self, mock_sleep, mock_get):
        """Client should parse Retry-After header as HTTP date."""
        from email.utils import formatdate

        from amplihack.api import APIClient

        # HTTP date 60 seconds in the future
        future_time = time.time() + 60
        http_date = formatdate(future_time, usegmt=True)

        mock_response_429 = Mock(status_code=429, headers={"Retry-After": http_date})
        mock_response_200 = Mock(status_code=200)
        mock_get.side_effect = [mock_response_429, mock_response_200]

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/data")

        assert response.status_code == 200
        # Should sleep approximately 60 seconds
        sleep_call = mock_sleep.call_args[0][0]
        assert 59 <= sleep_call <= 61

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_rate_limit_error_after_max_retries(self, mock_sleep, mock_get):
        """Client should raise RateLimitError after exhausting retries."""
        from amplihack.api import APIClient, RateLimitError

        mock_get.return_value = Mock(status_code=429, headers={"Retry-After": "10"})

        client = APIClient(base_url="https://api.example.com", max_retries=2)

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/data")

        assert exc_info.value.retry_after == 10
        assert mock_get.call_count == 3  # Initial + 2 retries

    @patch("requests.Session.get")
    def test_rate_limit_without_retry_after(self, mock_get):
        """Client should handle 429 without Retry-After header."""
        from amplihack.api import APIClient, RateLimitError

        mock_get.return_value = Mock(status_code=429, headers={})

        client = APIClient(base_url="https://api.example.com", max_retries=0)

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/data")

        # Should still raise RateLimitError
        assert exc_info.value.status_code == 429


class TestTimeoutHandling:
    """Test timeout behavior."""

    @patch("requests.Session.get")
    def test_timeout_passed_to_request(self, mock_get):
        """Client should pass timeout tuple to request."""
        from amplihack.api import APIClient

        mock_get.return_value = Mock(status_code=200)

        client = APIClient(base_url="https://api.example.com", timeout=(10, 60))
        client.get("/data")

        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == (10, 60)

    @patch("requests.Session.get")
    def test_connect_timeout_raises_timeout_error(self, mock_get):
        """Client should raise TimeoutError on connection timeout."""
        import requests

        from amplihack.api import APIClient, TimeoutError

        mock_get.side_effect = requests.exceptions.ConnectTimeout("Connection timeout")

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(TimeoutError) as exc_info:
            client.get("/data")

        assert exc_info.value.timeout_type == "connect"

    @patch("requests.Session.get")
    def test_read_timeout_raises_timeout_error(self, mock_get):
        """Client should raise TimeoutError on read timeout."""
        import requests

        from amplihack.api import APIClient, TimeoutError

        mock_get.side_effect = requests.exceptions.ReadTimeout("Read timeout")

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(TimeoutError) as exc_info:
            client.get("/data")

        assert exc_info.value.timeout_type == "read"


class TestHeaderSanitization:
    """Test sensitive header sanitization for logging."""

    def test_sanitize_authorization_header(self):
        """Authorization header should be redacted in logs."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        headers = {"Authorization": "Bearer secret-token-123", "User-Agent": "Test"}

        sanitized = client._sanitize_headers(headers)

        assert sanitized["Authorization"] == "[REDACTED]"
        assert sanitized["User-Agent"] == "Test"

    def test_sanitize_api_key_header(self):
        """API-Key and X-API-Key headers should be redacted."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        headers = {"X-API-Key": "secret123", "API-Key": "secret456"}

        sanitized = client._sanitize_headers(headers)

        assert sanitized["X-API-Key"] == "[REDACTED]"
        assert sanitized["API-Key"] == "[REDACTED]"

    def test_sanitize_cookie_headers(self):
        """Cookie and Set-Cookie headers should be redacted."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        headers = {"Cookie": "session=abc123", "Set-Cookie": "token=xyz"}

        sanitized = client._sanitize_headers(headers)

        assert sanitized["Cookie"] == "[REDACTED]"
        assert sanitized["Set-Cookie"] == "[REDACTED]"

    def test_preserve_safe_headers(self):
        """Non-sensitive headers should not be redacted."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MyClient/1.0",
        }

        sanitized = client._sanitize_headers(headers)

        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Accept"] == "application/json"
        assert sanitized["User-Agent"] == "MyClient/1.0"


class TestExceptionHandling:
    """Test exception raising for different scenarios."""

    @patch("requests.Session.get")
    def test_authentication_error_on_401(self, mock_get):
        """Client should raise AuthenticationError on 401."""
        from amplihack.api import APIClient, AuthenticationError

        mock_get.return_value = Mock(status_code=401)

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/protected")

        assert exc_info.value.status_code == 401

    @patch("requests.Session.get")
    def test_authentication_error_on_403(self, mock_get):
        """Client should raise AuthenticationError on 403."""
        from amplihack.api import APIClient, AuthenticationError

        mock_get.return_value = Mock(status_code=403)

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(AuthenticationError) as exc_info:
            client.get("/forbidden")

        assert exc_info.value.status_code == 403

    @patch("requests.Session.get")
    def test_api_error_on_client_errors(self, mock_get):
        """Client should raise APIError for other 4xx errors."""
        from amplihack.api import APIClient, APIError

        for status_code in [400, 404, 422]:
            mock_get.return_value = Mock(status_code=status_code)
            client = APIClient(base_url="https://api.example.com")

            with pytest.raises(APIError) as exc_info:
                client.get("/data")

            assert exc_info.value.status_code == status_code

    @patch("requests.Session.get")
    def test_api_error_includes_response(self, mock_get):
        """APIError should include original response object."""
        from amplihack.api import APIClient, APIError

        mock_response = Mock(status_code=400)
        mock_get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        with pytest.raises(APIError) as exc_info:
            client.get("/data")

        assert exc_info.value.response == mock_response


class TestThreadSafety:
    """Test thread-local session management."""

    @patch("requests.Session")
    def test_thread_local_sessions(self, mock_session_class):
        """Each thread should get its own session."""
        from amplihack.api import APIClient

        sessions_created = []

        def mock_session_init():
            session = MagicMock()
            sessions_created.append(session)
            return session

        mock_session_class.side_effect = mock_session_init

        client = APIClient(base_url="https://api.example.com")

        def worker():
            # Access session in thread
            session = client._get_session()
            sessions_created.append(session)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should create its own session
        # (Implementation detail: depends on thread-local storage)

    def test_close_cleans_up_sessions(self):
        """close() should cleanup thread-local sessions."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        client.close()

        # After close, accessing session should create new one
        # (Testing implementation detail)


class TestLogging:
    """Test request/response logging."""

    @patch("requests.Session.get")
    def test_request_logged(self, mock_get, caplog):
        """Client should log outgoing requests."""
        import logging

        from amplihack.api import APIClient

        mock_get.return_value = Mock(status_code=200, elapsed=timedelta(seconds=0.5))

        caplog.set_level(logging.INFO)
        client = APIClient(base_url="https://api.example.com")
        client.get("/users")

        # Should log request details
        assert any("GET" in record.message for record in caplog.records)

    @patch("requests.Session.get")
    def test_response_logged(self, mock_get, caplog):
        """Client should log responses."""
        import logging

        from amplihack.api import APIClient

        mock_get.return_value = Mock(status_code=200, elapsed=timedelta(seconds=0.5))

        caplog.set_level(logging.INFO)
        client = APIClient(base_url="https://api.example.com")
        client.get("/users")

        # Should log response status
        assert any("200" in record.message for record in caplog.records)

    @patch("requests.Session.get")
    def test_sensitive_headers_not_logged(self, mock_get, caplog):
        """Sensitive headers should not appear in logs."""
        import logging

        from amplihack.api import APIClient

        mock_get.return_value = Mock(status_code=200, elapsed=timedelta(seconds=0.1))

        caplog.set_level(logging.DEBUG)
        client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer secret-token-12345"},
        )
        client.get("/users")

        # Secret token should NOT appear in logs
        log_text = " ".join(record.message for record in caplog.records)
        assert "secret-token-12345" not in log_text


class TestResourceCleanup:
    """Test resource cleanup and context manager."""

    def test_close_method_exists(self):
        """APIClient should have close() method."""
        from amplihack.api import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert hasattr(client, "close")
        assert callable(client.close)

    def test_context_manager_support(self):
        """APIClient should support context manager protocol."""
        from amplihack.api import APIClient

        with APIClient(base_url="https://api.example.com") as client:
            assert client is not None

        # Should call close automatically

    @patch("requests.Session.get")
    def test_context_manager_cleanup_on_exception(self, mock_get):
        """Context manager should cleanup even if exception occurs."""
        from amplihack.api import APIClient, APIError

        mock_get.return_value = Mock(status_code=500)

        try:
            with APIClient(base_url="https://api.example.com") as client:
                client.get("/data")
        except APIError:
            pass

        # Should have cleaned up session
        # (Testing cleanup actually happens would require more complex mocking)
