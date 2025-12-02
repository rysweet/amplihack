"""Tests for APIClient.

Tests the main API client class using the actual implementation API:
- APIClient(config: APIClientConfig, logger: logging.Logger | None = None)
- Uses APIRequest/APIResponse models
- Raises RequestError, ClientError, ServerError, RateLimitError

Testing pyramid target: 60% unit, 30% integration, 10% E2E
"""

import logging
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAPIClientImport:
    """Tests for APIClient import and instantiation."""

    def test_import_api_client(self) -> None:
        """Test that APIClient can be imported."""
        from amplihack.utils.api_client.client import APIClient

        assert APIClient is not None

    def test_create_api_client_with_config(self) -> None:
        """Test creating APIClient with APIClientConfig."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")
        client = APIClient(config)

        assert client.config == config
        assert client.config.base_url == "https://api.example.com"

    def test_create_api_client_with_custom_logger(self) -> None:
        """Test creating APIClient with custom logger."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")
        custom_logger = logging.getLogger("custom.api")
        client = APIClient(config, logger=custom_logger)

        assert client._logger == custom_logger


class TestAPIClientContextManager:
    """Tests for APIClient context manager (with statement)."""

    def test_context_manager_enter(self) -> None:
        """Test that APIClient works with 'with' statement."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")
        with APIClient(config) as client:
            assert client is not None

    def test_context_manager_closes_session(self) -> None:
        """Test that exiting context closes the session."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")
        client = APIClient(config)

        # Access session to create it
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with client:
                _ = client._active_session  # Force session creation

        # Session should be None after context exit
        assert client._session is None

    def test_context_manager_on_exception(self) -> None:
        """Test that session is closed even on exception."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")
        client = APIClient(config)

        with pytest.raises(ValueError, match="Test error"):
            with client:
                raise ValueError("Test error")

        # Session should still be closed
        assert client._session is None


class TestHTTPMethods:
    """Tests for HTTP method wrappers."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock session for testing."""
        session = MagicMock()
        response = Mock()
        response.status_code = 200
        response.headers = {"Content-Type": "application/json"}
        response.text = '{"result": "success"}'
        session.request.return_value = response
        return session

    def test_get_method(self, mock_session: MagicMock) -> None:
        """Test GET request method."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session", return_value=mock_session):
            with APIClient(config) as client:
                response = client.get("/users")

                assert response.status_code == 200
                mock_session.request.assert_called_once()
                call_args = mock_session.request.call_args
                assert call_args[1]["method"] == "GET"
                assert "/users" in call_args[1]["url"]

    def test_post_method(self, mock_session: MagicMock) -> None:
        """Test POST request method."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session", return_value=mock_session):
            with APIClient(config) as client:
                response = client.post("/users", json_body={"name": "John"})

                assert response.status_code == 200
                call_args = mock_session.request.call_args
                assert call_args[1]["method"] == "POST"

    def test_put_method(self, mock_session: MagicMock) -> None:
        """Test PUT request method."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session", return_value=mock_session):
            with APIClient(config) as client:
                response = client.put("/users/1", json_body={"name": "Jane"})

                assert response.status_code == 200
                call_args = mock_session.request.call_args
                assert call_args[1]["method"] == "PUT"

    def test_delete_method(self, mock_session: MagicMock) -> None:
        """Test DELETE request method."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session", return_value=mock_session):
            with APIClient(config) as client:
                response = client.delete("/users/1")

                assert response.status_code == 200
                call_args = mock_session.request.call_args
                assert call_args[1]["method"] == "DELETE"

    def test_patch_method(self, mock_session: MagicMock) -> None:
        """Test PATCH request method."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session", return_value=mock_session):
            with APIClient(config) as client:
                response = client.patch("/users/1", json_body={"name": "Updated"})

                assert response.status_code == 200
                call_args = mock_session.request.call_args
                assert call_args[1]["method"] == "PATCH"


class TestRequestMethod:
    """Tests for the core request method."""

    def test_request_returns_api_response(self) -> None:
        """Test that request returns APIResponse object."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.models import APIRequest, APIResponse

        config = APIClientConfig(base_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with APIClient(config) as client:
                request = APIRequest(method="GET", path="/test")
                response = client.request(request)

                assert isinstance(response, APIResponse)
                assert response.status_code == 200

    def test_request_with_headers(self) -> None:
        """Test request with custom headers."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.models import APIRequest

        config = APIClientConfig(base_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with APIClient(config) as client:
                request = APIRequest(
                    method="GET",
                    path="/test",
                    headers={"X-Custom-Header": "custom-value"},
                )
                client.request(request)

                call_kwargs = MockSession.return_value.request.call_args[1]
                assert "X-Custom-Header" in call_kwargs["headers"]

    def test_request_with_query_params(self) -> None:
        """Test request with query parameters."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.models import APIRequest

        config = APIClientConfig(base_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with APIClient(config) as client:
                request = APIRequest(
                    method="GET",
                    path="/users",
                    params={"page": "1", "limit": "10"},
                )
                client.request(request)

                call_kwargs = MockSession.return_value.request.call_args[1]
                assert call_kwargs["params"] == {"page": "1", "limit": "10"}

    def test_request_with_json_body(self) -> None:
        """Test request with JSON body."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.models import APIRequest

        config = APIClientConfig(base_url="https://api.example.com")

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = ""

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with APIClient(config) as client:
                request = APIRequest(
                    method="POST",
                    path="/users",
                    json_body={"name": "John", "email": "john@example.com"},
                )
                client.request(request)

                call_kwargs = MockSession.return_value.request.call_args[1]
                assert call_kwargs["json"] == {"name": "John", "email": "john@example.com"}


class TestRetryBehavior:
    """Tests for retry behavior on 5xx errors."""

    def test_retry_on_500_error(self) -> None:
        """Test that 500 errors trigger retry."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        responses = [
            Mock(status_code=500, headers={}, text="Error"),
            Mock(status_code=500, headers={}, text="Error"),
            Mock(status_code=200, headers={}, text="Success"),
        ]

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = responses
            with patch("time.sleep"):  # Don't actually sleep
                with APIClient(config) as client:
                    response = client.get("/test")

                    # Should succeed after retries
                    assert response.status_code == 200
                    # Should have made 3 attempts
                    assert MockSession.return_value.request.call_count == 3

    def test_retry_exhausted_raises_exception(self) -> None:
        """Test that exhausted retries raise RetryExhaustedError."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import RetryExhaustedError

        error_response = Mock()
        error_response.status_code = 503
        error_response.headers = {}
        error_response.text = "Service Unavailable"

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=2,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = error_response
            with patch("time.sleep"):
                with APIClient(config) as client:
                    with pytest.raises(RetryExhaustedError):
                        client.get("/test")

                    # Should have made 3 attempts (1 original + 2 retries)
                    assert MockSession.return_value.request.call_count == 3

    def test_no_retry_on_4xx_errors(self) -> None:
        """Test that 4xx errors do not trigger retry."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ClientError

        error_response = Mock()
        error_response.status_code = 400
        error_response.headers = {}
        error_response.text = "Bad Request"

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = error_response
            with APIClient(config) as client:
                with pytest.raises(ClientError) as exc_info:
                    client.get("/test")

                assert exc_info.value.status_code == 400
                # Should have made only 1 attempt (no retry for 4xx)
                assert MockSession.return_value.request.call_count == 1


class TestRateLimitHandling:
    """Tests for 429 rate limit handling."""

    def test_429_triggers_retry_with_retry_after(self) -> None:
        """Test that 429 with Retry-After header delays retry."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        responses = [
            Mock(status_code=429, headers={"Retry-After": "2"}, text="Rate limited"),
            Mock(status_code=200, headers={}, text="Success"),
        ]

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = responses
            with patch("time.sleep") as mock_sleep:
                with APIClient(config) as client:
                    response = client.get("/test")

                    assert response.status_code == 200
                    # Should have slept for approximately 2 seconds
                    mock_sleep.assert_called()
                    sleep_time = mock_sleep.call_args[0][0]
                    assert sleep_time >= 2

    def test_429_without_retry_after_uses_default(self) -> None:
        """Test that 429 without Retry-After uses default delay."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        responses = [
            Mock(status_code=429, headers={}, text="Rate limited"),
            Mock(status_code=200, headers={}, text="Success"),
        ]

        config = APIClientConfig(
            base_url="https://api.example.com",
            max_retries=3,
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = responses
            with patch("time.sleep") as mock_sleep:
                with APIClient(config) as client:
                    response = client.get("/test")

                    assert response.status_code == 200
                    mock_sleep.assert_called()


class TestExceptionRaising:
    """Tests for exception raising behavior."""

    def test_request_error_on_connection_failure(self) -> None:
        """Test that connection errors raise RequestError."""
        import requests

        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import RequestError

        config = APIClientConfig(base_url="https://api.example.com", max_retries=0)

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = requests.ConnectionError(
                "Connection refused"
            )
            with APIClient(config) as client:
                with pytest.raises(RequestError):
                    client.get("/test")

    def test_request_error_on_timeout(self) -> None:
        """Test that timeouts raise RequestError."""
        import requests

        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import RequestError

        config = APIClientConfig(base_url="https://api.example.com", max_retries=0)

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.side_effect = requests.Timeout("Request timed out")
            with APIClient(config) as client:
                with pytest.raises(RequestError):
                    client.get("/test")

    def test_client_error_includes_response_body(self) -> None:
        """Test that ClientError includes response body."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig
        from amplihack.utils.api_client.exceptions import ClientError

        error_response = Mock()
        error_response.status_code = 400
        error_response.headers = {"Content-Type": "application/json"}
        error_response.text = '{"error": "Invalid input", "field": "email"}'

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = error_response
            with APIClient(config) as client:
                with pytest.raises(ClientError) as exc_info:
                    client.get("/test")

                assert exc_info.value.response_body == '{"error": "Invalid input", "field": "email"}'


class TestHeaderSanitization:
    """Tests for header sanitization in logs."""

    def test_authorization_header_sanitized_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that Authorization header is sanitized in log output."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        config = APIClientConfig(
            base_url="https://api.example.com",
            default_headers={"Authorization": "Bearer secret-token-12345"},
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with caplog.at_level(logging.DEBUG):
                with APIClient(config) as client:
                    client.get("/test")

        # Check that secret token is not in logs
        log_output = caplog.text
        assert "secret-token-12345" not in log_output

    def test_api_key_header_sanitized_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that X-API-Key header is sanitized in log output."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        config = APIClientConfig(
            base_url="https://api.example.com",
            default_headers={"X-API-Key": "super-secret-api-key-xyz"},
        )

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response
            with caplog.at_level(logging.DEBUG):
                with APIClient(config) as client:
                    client.get("/test")

        log_output = caplog.text
        assert "super-secret-api-key-xyz" not in log_output


class TestBaseURLHandling:
    """Tests for base URL handling."""

    def test_trailing_slash_normalized(self) -> None:
        """Test that trailing slash in base_url is handled."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        config = APIClientConfig(base_url="https://api.example.com/")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("/users")

                call_kwargs = MockSession.return_value.request.call_args[1]
                url = call_kwargs["url"]
                # Should not have double slash
                assert "//users" not in url

    def test_path_without_leading_slash(self) -> None:
        """Test that path without leading slash works."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""

        config = APIClientConfig(base_url="https://api.example.com")

        with patch("requests.Session") as MockSession:
            MockSession.return_value.request.return_value = mock_response

            with APIClient(config) as client:
                client.get("users")  # No leading slash

                call_kwargs = MockSession.return_value.request.call_args[1]
                url = call_kwargs["url"]
                assert "api.example.com/users" in url


class TestSuccessfulResponses:
    """Tests for handling successful responses."""

    def test_2xx_does_not_raise_exception(self) -> None:
        """Test that 2xx responses do not raise exceptions."""
        from amplihack.utils.api_client.client import APIClient
        from amplihack.utils.api_client.config import APIClientConfig

        config = APIClientConfig(base_url="https://api.example.com")

        for status_code in [200, 201, 202, 204]:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.headers = {}
            mock_response.text = ""

            with patch("requests.Session") as MockSession:
                MockSession.return_value.request.return_value = mock_response

                with APIClient(config) as client:
                    response = client.get("/test")
                    assert response.status_code == status_code
