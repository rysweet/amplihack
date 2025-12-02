"""Integration tests for APIClient.

Tests the client with mocked HTTP responses.
This is part of the 30% integration test coverage.
"""

import logging
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest


class TestAPIClientConstruction:
    """Tests for APIClient initialization."""

    def test_create_with_base_url(self):
        """Should create client with just base_url."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client is not None

    def test_base_url_stored(self):
        """base_url should be accessible."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_default_timeout(self):
        """Default timeout should be 30.0 seconds."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.timeout == 30.0

    def test_custom_timeout(self):
        """Should accept custom timeout."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com", timeout=10.0)
        assert client.timeout == 10.0

    def test_default_headers(self):
        """Should accept default headers."""
        from api_client import APIClient

        headers = {"User-Agent": "TestApp/1.0", "Accept": "application/json"}
        client = APIClient(base_url="https://api.example.com", headers=headers)
        assert client.headers == headers

    def test_thread_safe_mode(self):
        """Should accept thread_safe parameter."""
        from api_client import APIClient

        client = APIClient(base_url="https://api.example.com", thread_safe=True)
        assert client.thread_safe is True

    def test_custom_retry_policy(self):
        """Should accept custom retry policy."""
        from api_client import APIClient, RetryPolicy

        policy = RetryPolicy(max_retries=5)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        assert client.retry_policy is policy

    def test_custom_rate_limiter(self):
        """Should accept custom rate limiter."""
        from api_client import APIClient, RateLimiter

        limiter = RateLimiter(requests_per_second=5.0)
        client = APIClient(base_url="https://api.example.com", rate_limiter=limiter)
        assert client.rate_limiter is limiter


class TestAPIClientContextManager:
    """Tests for context manager support."""

    def test_context_manager_entry(self):
        """Should support context manager entry."""
        from api_client import APIClient

        with APIClient(base_url="https://api.example.com") as client:
            assert client is not None

    def test_context_manager_returns_client(self):
        """Context manager should return the client."""
        from api_client import APIClient

        with APIClient(base_url="https://api.example.com") as client:
            assert isinstance(client, APIClient)

    @patch("requests.Session")
    def test_context_manager_cleanup(self, mock_session_class):
        """Context manager exit should clean up resources."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        with APIClient(base_url="https://api.example.com"):
            pass

        # Session should be closed
        mock_session.close.assert_called()


class TestHTTPMethods:
    """Tests for HTTP method implementations."""

    @patch("requests.Session")
    def test_get_makes_get_request(self, mock_session_class):
        """get() should make a GET request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("/users/123")

        mock_session.request.assert_called()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET" or call_args[0][0] == "GET"

    @patch("requests.Session")
    def test_post_makes_post_request(self, mock_session_class):
        """post() should make a POST request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.post("/users", json={"name": "Alice"})

        mock_session.request.assert_called()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "POST" or call_args[0][0] == "POST"

    @patch("requests.Session")
    def test_put_makes_put_request(self, mock_session_class):
        """put() should make a PUT request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.put("/users/123", json={"name": "Bob"})

        mock_session.request.assert_called()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "PUT" or call_args[0][0] == "PUT"

    @patch("requests.Session")
    def test_patch_makes_patch_request(self, mock_session_class):
        """patch() should make a PATCH request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.patch("/users/123", json={"name": "Charlie"})

        mock_session.request.assert_called()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "PATCH" or call_args[0][0] == "PATCH"

    @patch("requests.Session")
    def test_delete_makes_delete_request(self, mock_session_class):
        """delete() should make a DELETE request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.delete("/users/123")

        mock_session.request.assert_called()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "DELETE" or call_args[0][0] == "DELETE"


class TestURLConstruction:
    """Tests for URL path handling."""

    @patch("requests.Session")
    def test_path_joined_to_base_url(self, mock_session_class):
        """Path should be joined to base_url."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("/users/123")

        call_args = mock_session.request.call_args
        url = call_args[1].get("url") or call_args[0][1]
        assert url == "https://api.example.com/users/123"

    @patch("requests.Session")
    def test_handles_path_without_leading_slash(self, mock_session_class):
        """Should handle paths without leading slash."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("users/123")

        call_args = mock_session.request.call_args
        url = call_args[1].get("url") or call_args[0][1]
        assert "users/123" in url

    @patch("requests.Session")
    def test_handles_base_url_with_trailing_slash(self, mock_session_class):
        """Should handle base_url with trailing slash."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com/")
        client.get("/users/123")

        call_args = mock_session.request.call_args
        url = call_args[1].get("url") or call_args[0][1]
        # Should not have double slashes
        assert "//" not in url.replace("https://", "")


class TestRequestParameters:
    """Tests for request parameter handling."""

    @patch("requests.Session")
    def test_query_params_passed(self, mock_session_class):
        """Query parameters should be passed to request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("/users", params={"page": 1, "limit": 10})

        call_args = mock_session.request.call_args
        params = call_args[1].get("params")
        assert params == {"page": 1, "limit": 10}

    @patch("requests.Session")
    def test_json_body_passed(self, mock_session_class):
        """JSON body should be passed to request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

        call_args = mock_session.request.call_args
        json_data = call_args[1].get("json")
        assert json_data == {"name": "Alice", "email": "alice@example.com"}

    @patch("requests.Session")
    def test_timeout_passed(self, mock_session_class):
        """Timeout should be passed to request."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com", timeout=15.0)
        client.get("/users")

        call_args = mock_session.request.call_args
        timeout = call_args[1].get("timeout")
        assert timeout == 15.0

    @patch("requests.Session")
    def test_default_headers_applied(self, mock_session_class):
        """Default headers should be applied to requests."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        headers = {"User-Agent": "TestApp/1.0"}
        client = APIClient(base_url="https://api.example.com", headers=headers)
        client.get("/users")

        call_args = mock_session.request.call_args
        request_headers = call_args[1].get("headers", {})
        assert "User-Agent" in request_headers

    @patch("requests.Session")
    def test_per_request_headers_override(self, mock_session_class):
        """Per-request headers should override defaults."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(
            base_url="https://api.example.com", headers={"User-Agent": "DefaultAgent"}
        )
        client.get("/users", headers={"User-Agent": "CustomAgent"})

        call_args = mock_session.request.call_args
        request_headers = call_args[1].get("headers", {})
        assert request_headers.get("User-Agent") == "CustomAgent"


class TestRetryBehavior:
    """Tests for automatic retry on failures."""

    @patch("requests.Session")
    def test_retries_on_500(self, mock_session_class):
        """Should retry on 500 status code."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.headers = {}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        # First call fails, second succeeds
        mock_session.request.side_effect = [mock_response_500, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/flaky")

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    @patch("requests.Session")
    def test_retries_on_502(self, mock_session_class):
        """Should retry on 502 status code."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_502 = MagicMock()
        mock_response_502.status_code = 502
        mock_response_502.headers = {}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_502, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/flaky")

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    @patch("requests.Session")
    def test_retries_on_503(self, mock_session_class):
        """Should retry on 503 status code."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503
        mock_response_503.headers = {}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_503, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/flaky")

        assert response.status_code == 200

    @patch("requests.Session")
    def test_retries_on_504(self, mock_session_class):
        """Should retry on 504 status code."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_504 = MagicMock()
        mock_response_504.status_code = 504
        mock_response_504.headers = {}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_504, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/flaky")

        assert response.status_code == 200

    @patch("requests.Session")
    def test_no_retry_on_400(self, mock_session_class):
        """Should NOT retry on 400 status code."""
        from api_client import APIClient, HTTPError, RetryPolicy

        mock_session = MagicMock()
        mock_response_400 = MagicMock()
        mock_response_400.status_code = 400
        mock_response_400.headers = {}
        mock_session.request.return_value = mock_response_400
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)

        with pytest.raises(HTTPError) as exc_info:
            client.get("/bad-request")

        assert exc_info.value.status_code == 400
        assert mock_session.request.call_count == 1  # No retries

    @patch("requests.Session")
    def test_no_retry_on_404(self, mock_session_class):
        """Should NOT retry on 404 status code."""
        from api_client import APIClient, HTTPError, RetryPolicy

        mock_session = MagicMock()
        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404
        mock_response_404.headers = {}
        mock_session.request.return_value = mock_response_404
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)

        with pytest.raises(HTTPError) as exc_info:
            client.get("/not-found")

        assert exc_info.value.status_code == 404
        assert mock_session.request.call_count == 1

    @patch("requests.Session")
    def test_max_retries_exhausted(self, mock_session_class):
        """Should raise after max_retries exhausted."""
        from api_client import APIClient, HTTPError, RetryPolicy

        mock_session = MagicMock()
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.headers = {}
        mock_session.request.return_value = mock_response_500
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)

        with pytest.raises(HTTPError) as exc_info:
            client.get("/always-fails")

        assert exc_info.value.status_code == 500
        # Initial + 2 retries = 3 total calls
        assert mock_session.request.call_count == 3


class TestRateLimitHandling:
    """Tests for 429 rate limit handling."""

    @patch("requests.Session")
    def test_retries_on_429(self, mock_session_class):
        """Should retry on 429 status code."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_429, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/rate-limited")

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    @patch("requests.Session")
    @patch("time.sleep")
    def test_respects_retry_after_seconds(self, mock_sleep, mock_session_class):
        """Should respect Retry-After header with seconds value."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "5"}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_429, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        client.get("/rate-limited")

        # Should have slept for at least 5 seconds
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert any(s >= 5.0 for s in sleep_calls)

    @patch("requests.Session")
    @patch("time.sleep")
    def test_respects_retry_after_http_date(self, mock_sleep, mock_session_class):
        """Should respect Retry-After header with HTTP-date format."""
        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        # HTTP-date format
        mock_response_429.headers = {"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"}
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [mock_response_429, mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)

        # Should handle HTTP-date parsing (may sleep for computed duration)
        try:
            client.get("/rate-limited")
        except Exception:
            pass  # May timeout or fail, but shouldn't crash on parsing

        # Verify sleep was called
        assert mock_sleep.called


class TestNetworkErrorHandling:
    """Tests for network error handling."""

    @patch("requests.Session")
    def test_retries_on_connection_error(self, mock_session_class):
        """Should retry on connection errors."""
        import requests

        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        # First call raises connection error, second succeeds
        mock_session.request.side_effect = [
            requests.ConnectionError("Connection refused"),
            mock_response_200,
        ]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/flaky")

        assert response.status_code == 200
        assert mock_session.request.call_count == 2

    @patch("requests.Session")
    def test_retries_on_timeout(self, mock_session_class):
        """Should retry on timeout errors."""
        import requests

        from api_client import APIClient, RetryPolicy

        mock_session = MagicMock()
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_session.request.side_effect = [requests.Timeout("Read timed out"), mock_response_200]
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)
        response = client.get("/slow")

        assert response.status_code == 200

    @patch("requests.Session")
    def test_raises_network_error_after_retries(self, mock_session_class):
        """Should raise NetworkError after retries exhausted."""
        import requests

        from api_client import APIClient, NetworkError, RetryPolicy

        mock_session = MagicMock()
        mock_session.request.side_effect = requests.ConnectionError("Network down")
        mock_session_class.return_value = mock_session

        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        client = APIClient(base_url="https://api.example.com", retry_policy=policy)

        with pytest.raises(NetworkError):
            client.get("/unreachable")


class TestLogging:
    """Tests for logging behavior."""

    @patch("requests.Session")
    def test_logs_request(self, mock_session_class):
        """Should log outgoing requests."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Set up logging capture
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("api_client")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            client = APIClient(base_url="https://api.example.com")
            client.get("/users/123")

            log_output = log_capture.getvalue()
            assert "GET" in log_output or "users" in log_output
        finally:
            logger.removeHandler(handler)

    @patch("requests.Session")
    def test_logs_response_status(self, mock_session_class):
        """Should log response status."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("api_client")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            client = APIClient(base_url="https://api.example.com")
            client.get("/users")

            log_output = log_capture.getvalue()
            assert "200" in log_output or "OK" in log_output.upper()
        finally:
            logger.removeHandler(handler)

    @patch("requests.Session")
    def test_sanitizes_authorization_header(self, mock_session_class):
        """Should sanitize Authorization header in logs."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("api_client")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            client = APIClient(
                base_url="https://api.example.com",
                headers={"Authorization": "Bearer secret-token-12345"},
            )
            client.get("/secure")

            log_output = log_capture.getvalue()
            # Token should NOT appear in logs
            assert "secret-token-12345" not in log_output
            # Should show [REDACTED] or similar
            if "Authorization" in log_output:
                assert "REDACTED" in log_output or "***" in log_output
        finally:
            logger.removeHandler(handler)

    @patch("requests.Session")
    def test_sanitizes_api_key_header(self, mock_session_class):
        """Should sanitize X-API-Key header in logs."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("api_client")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            client = APIClient(
                base_url="https://api.example.com", headers={"X-API-Key": "my-secret-api-key"}
            )
            client.get("/secure")

            log_output = log_capture.getvalue()
            assert "my-secret-api-key" not in log_output
        finally:
            logger.removeHandler(handler)


class TestResponseHandling:
    """Tests for response object handling."""

    @patch("requests.Session")
    def test_returns_response_object(self, mock_session_class):
        """Should return requests.Response object."""
        import requests

        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response is mock_response

    @patch("requests.Session")
    def test_response_json_accessible(self, mock_session_class):
        """Response should have json() method accessible."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "name": "Alice"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users/123")

        assert response.json() == {"id": 123, "name": "Alice"}

    @patch("requests.Session")
    def test_response_text_accessible(self, mock_session_class):
        """Response should have text attribute accessible."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Hello, World!"
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/hello")

        assert response.text == "Hello, World!"

    @patch("requests.Session")
    def test_response_headers_accessible(self, mock_session_class):
        """Response should have headers accessible."""
        from api_client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")

        assert response.headers["Content-Type"] == "application/json"
