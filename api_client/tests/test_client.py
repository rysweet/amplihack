"""Unit tests for APIClient with mocking.

TDD: These tests define the EXPECTED behavior of APIClient.
All tests should FAIL until api_client/client.py is implemented.

Testing pyramid: Unit tests (60% of total)
Uses mocking to isolate client logic from actual HTTP requests.
"""

from unittest.mock import MagicMock, patch


class TestAPIClientInit:
    """Test APIClient initialization."""

    def test_init_with_base_url(self):
        """Client should store base_url."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_init_strips_trailing_slash(self):
        """Client should strip trailing slash from base_url."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com/")
        assert client.base_url == "https://api.example.com"

    def test_init_default_timeout(self):
        """Default timeout should be 30.0 seconds."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.timeout == 30.0

    def test_init_custom_timeout(self):
        """Should accept custom timeout."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com", timeout=60.0)
        assert client.timeout == 60.0

    def test_init_default_max_retries(self):
        """Default max_retries should be 3."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.max_retries == 3

    def test_init_custom_max_retries(self):
        """Should accept custom max_retries."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com", max_retries=5)
        assert client.max_retries == 5

    def test_init_default_retry_backoff_factor(self):
        """Default retry_backoff_factor should be 0.5."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.retry_backoff_factor == 0.5

    def test_init_default_retry_on_status(self):
        """Default retry_on_status should include standard retryable codes."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert 429 in client.retry_on_status
        assert 500 in client.retry_on_status
        assert 502 in client.retry_on_status
        assert 503 in client.retry_on_status
        assert 504 in client.retry_on_status

    def test_init_custom_retry_on_status(self):
        """Should accept custom retry_on_status."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com", retry_on_status={500, 503})
        assert client.retry_on_status == {500, 503}

    def test_init_default_headers_none(self):
        """Default headers should be empty dict when None provided."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        assert client.default_headers == {} or client.default_headers is None

    def test_init_custom_default_headers(self):
        """Should accept custom default_headers."""
        from api_client.client import APIClient

        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        client = APIClient(base_url="https://api.example.com", default_headers=headers)
        assert "Authorization" in client.default_headers
        assert client.default_headers["Authorization"] == "Bearer token123"

    def test_init_makes_defensive_copy_of_default_headers(self):
        """Client should make a defensive copy of default_headers."""
        from api_client.client import APIClient

        headers = {"Authorization": "Bearer token123"}
        client = APIClient(base_url="https://api.example.com", default_headers=headers)

        # Modifying the original dict should not affect client
        headers["X-New"] = "value"
        assert "X-New" not in client.default_headers


class TestAPIClientContextManager:
    """Test APIClient context manager behavior."""

    def test_enter_returns_self(self):
        """__enter__ should return the client instance."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        with client as ctx:
            assert ctx is client

    def test_exit_closes_session(self):
        """__exit__ should close the underlying session."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")

        with patch.object(client, "_session", create=True) as mock_session:
            mock_session.close = MagicMock()
            client.__enter__()
            client.__exit__(None, None, None)
            # Session should be closed
            mock_session.close.assert_called_once()


class TestAPIClientClose:
    """Test APIClient.close method."""

    def test_close_closes_session(self):
        """close() should close the underlying session."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")

        with patch.object(client, "_session", create=True) as mock_session:
            mock_session.close = MagicMock()
            client.close()
            mock_session.close.assert_called_once()

    def test_close_sets_session_to_none(self):
        """close() should set session to None."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        # Create a session
        client._get_session()
        assert client._session is not None

        client.close()
        assert client._session is None

    def test_close_is_safe_to_call_multiple_times(self):
        """close() should be safe to call multiple times."""
        from api_client.client import APIClient

        client = APIClient(base_url="https://api.example.com")
        client._get_session()

        # First close
        client.close()
        assert client._session is None

        # Second close should not raise
        client.close()
        assert client._session is None


class TestAPIClientGet:
    """Test APIClient.get method."""

    @patch("api_client.client.requests.Session")
    def test_get_calls_correct_url(self, mock_session_class):
        """GET request should call correct full URL."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"data": "test"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("/users")

        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://api.example.com/users"

    @patch("api_client.client.requests.Session")
    def test_get_with_params(self, mock_session_class):
        """GET request should pass query parameters."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.get("/search", params={"q": "test", "page": 1})

        call_args = mock_session.request.call_args
        assert call_args[1]["params"] == {"q": "test", "page": 1}


class TestAPIClientPost:
    """Test APIClient.post method."""

    @patch("api_client.client.requests.Session")
    def test_post_sends_json_body(self, mock_session_class):
        """POST request should send JSON body."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b'{"id": 1}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.post("/users", json_data={"name": "Test", "email": "test@example.com"})

        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["json"] == {"name": "Test", "email": "test@example.com"}


class TestAPIClientPut:
    """Test APIClient.put method."""

    @patch("api_client.client.requests.Session")
    def test_put_sends_json_body(self, mock_session_class):
        """PUT request should send JSON body."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{"id": 1, "name": "Updated"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.put("/users/1", json_data={"name": "Updated"})

        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "PUT"


class TestAPIClientPatch:
    """Test APIClient.patch method."""

    @patch("api_client.client.requests.Session")
    def test_patch_sends_json_body(self, mock_session_class):
        """PATCH request should send JSON body."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b'{"id": 1}'
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.patch("/users/1", json_data={"status": "active"})

        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "PATCH"


class TestAPIClientDelete:
    """Test APIClient.delete method."""

    @patch("api_client.client.requests.Session")
    def test_delete_method(self, mock_session_class):
        """DELETE request should use DELETE method."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        client.delete("/users/1")

        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "DELETE"


class TestAPIClientHeaders:
    """Test header merging behavior."""

    @patch("api_client.client.requests.Session")
    def test_default_headers_included(self, mock_session_class):
        """Default headers should be included in requests."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer token123"},
        )
        client.get("/protected")

        call_args = mock_session.request.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer token123"

    @patch("api_client.client.requests.Session")
    def test_per_request_headers_merged(self, mock_session_class):
        """Per-request headers should be merged with defaults."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer token123"},
        )
        client.get("/data", headers={"X-Request-Id": "req-123"})

        call_args = mock_session.request.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer token123"
        assert headers["X-Request-Id"] == "req-123"

    @patch("api_client.client.requests.Session")
    def test_per_request_headers_override_defaults(self, mock_session_class):
        """Per-request headers should override defaults when same key."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer default-token"},
        )
        client.get("/data", headers={"Authorization": "Bearer override-token"})

        call_args = mock_session.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer override-token"


class TestAPIClientTimeout:
    """Test timeout handling."""

    @patch("api_client.client.requests.Session")
    def test_timeout_passed_to_request(self, mock_session_class):
        """Timeout should be passed to the underlying request."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com", timeout=45.0)
        client.get("/slow-endpoint")

        call_args = mock_session.request.call_args
        assert call_args[1]["timeout"] == 45.0

    @patch("api_client.client.requests.Session")
    def test_per_request_timeout_override(self, mock_session_class):
        """Per-request timeout should override default."""
        from api_client.client import APIClient

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com", timeout=30.0)
        client.get("/very-slow", timeout=120.0)

        call_args = mock_session.request.call_args
        assert call_args[1]["timeout"] == 120.0


class TestAPIClientResponse:
    """Test that client returns proper Response objects."""

    @patch("api_client.client.requests.Session")
    def test_returns_response_object(self, mock_session_class):
        """Client should return our Response dataclass."""
        from api_client.client import APIClient
        from api_client.models import Response

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"success": true}'
        mock_response.elapsed.total_seconds.return_value = 0.123
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/test")

        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body == b'{"success": true}'


class TestAPIClientExport:
    """Test that APIClient is properly exported."""

    def test_api_client_is_importable(self):
        """APIClient should be importable from client module."""
        from api_client.client import APIClient  # noqa: F401

        assert True
