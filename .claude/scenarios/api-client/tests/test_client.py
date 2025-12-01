"""
Tests for main APIClient class.

Tests the core RestClient functionality including HTTP methods,
request/response handling, authentication, and configuration.

Coverage areas:
- GET, POST, PUT, PATCH, DELETE methods
- Request headers and parameters
- Response handling
- Authentication integration
- Configuration application
- Error handling
- Timeout handling
- URL construction
"""

from unittest.mock import Mock, patch

import pytest


class TestRestClientCreation:
    """Test RestClient instantiation and configuration."""

    def test_create_client_with_base_url(self) -> None:
        """Test creating client with base URL."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_create_client_with_config(self) -> None:
        """Test creating client with ClientConfig object."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import ClientConfig

        config = ClientConfig(base_url="https://api.example.com", timeout=60, max_retries=5)

        client = RestClient(config=config)
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 60
        assert client.max_retries == 5

    def test_create_client_with_kwargs(self) -> None:
        """Test creating client with keyword arguments."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url="https://api.example.com", timeout=45, max_retries=4)

        assert client.base_url == "https://api.example.com"
        assert client.timeout == 45
        assert client.max_retries == 4

    def test_create_client_from_env(self) -> None:
        """Test creating client from environment variables."""
        import os

        from amplihack.api_client import RestClient

        with patch.dict(
            os.environ,
            {"API_CLIENT_BASE_URL": "https://api.example.com", "API_CLIENT_TIMEOUT": "60"},
        ):
            client = RestClient.from_env()
            assert client.base_url == "https://api.example.com"
            assert client.timeout == 60


class TestGETRequests:
    """Test GET request functionality."""

    def test_simple_get_request(self, base_url: str) -> None:
        """Test making a simple GET request."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(
                status_code=200, ok=True, json=lambda: {"id": 123, "name": "Alice"}
            )

            response = client.get("/users/123")

            assert response.status_code == 200
            assert response.json()["name"] == "Alice"
            mock_request.assert_called_once()

    def test_get_with_query_params(self, base_url: str) -> None:
        """Test GET request with query parameters."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/users", params={"page": 1, "per_page": 50})

            # Verify params were passed
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"] == {"page": 1, "per_page": 50}

    def test_get_with_headers(self, base_url: str) -> None:
        """Test GET request with custom headers."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            headers = {"Authorization": "Bearer token123"}
            client.get("/protected", headers=headers)

            call_kwargs = mock_request.call_args[1]
            assert "Authorization" in call_kwargs["headers"]

    def test_get_constructs_full_url(self, base_url: str) -> None:
        """Test GET constructs full URL from base_url and path."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/users/123")

            call_args = mock_request.call_args[0]
            expected_url = f"{base_url}/users/123"
            assert call_args[1] == expected_url


class TestPOSTRequests:
    """Test POST request functionality."""

    def test_post_with_json_body(self, base_url: str) -> None:
        """Test POST request with JSON body."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(
                status_code=201, ok=True, json=lambda: {"id": 124, "name": "Bob"}
            )

            body = {"name": "Bob", "email": "bob@example.com"}
            response = client.post("/users", json=body)

            assert response.status_code == 201
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"] == body

    def test_post_with_form_data(self, base_url: str) -> None:
        """Test POST request with form data."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            data = {"username": "alice", "password": "secret"}  # pragma: allowlist secret
            client.post("/login", data=data)

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["data"] == data

    def test_post_with_files(self, base_url: str) -> None:
        """Test POST request with file upload."""
        from io import BytesIO

        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=201, ok=True)

            file_data = BytesIO(b"file content")
            files = {"file": file_data}
            client.post("/upload", files=files)

            call_kwargs = mock_request.call_args[1]
            assert "files" in call_kwargs


class TestPUTRequests:
    """Test PUT request functionality."""

    def test_put_request(self, base_url: str) -> None:
        """Test PUT request for full resource update."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            body = {"name": "Alice Smith", "email": "alice.smith@example.com"}
            client.put("/users/123", json=body)

            call_args = mock_request.call_args
            assert call_args[0][0] == "PUT"
            assert call_args[1]["json"] == body


class TestPATCHRequests:
    """Test PATCH request functionality."""

    def test_patch_request(self, base_url: str) -> None:
        """Test PATCH request for partial resource update."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            body = {"email": "newemail@example.com"}
            client.patch("/users/123", json=body)

            call_args = mock_request.call_args
            assert call_args[0][0] == "PATCH"
            assert call_args[1]["json"] == body


class TestDELETERequests:
    """Test DELETE request functionality."""

    def test_delete_request(self, base_url: str) -> None:
        """Test DELETE request."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=204, ok=True)

            response = client.delete("/users/123")

            assert response.status_code == 204
            call_args = mock_request.call_args
            assert call_args[0][0] == "DELETE"

    def test_delete_with_params(self, base_url: str) -> None:
        """Test DELETE request with query parameters."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=204, ok=True)

            client.delete("/users/123", params={"confirm": "yes"})

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"] == {"confirm": "yes"}


class TestGenericRequest:
    """Test generic request() method."""

    def test_request_with_custom_method(self, base_url: str) -> None:
        """Test request() with custom HTTP method."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.request("OPTIONS", "/users")

            call_args = mock_request.call_args
            assert call_args[0][0] == "OPTIONS"

    def test_request_with_all_parameters(self, base_url: str) -> None:
        """Test request() with all parameters."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.request(
                "POST",
                "/endpoint",
                json={"data": "test"},
                headers={"X-Custom": "value"},
                params={"key": "value"},
                timeout=60,
            )

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["json"] == {"data": "test"}
            assert "X-Custom" in call_kwargs["headers"]
            assert call_kwargs["params"] == {"key": "value"}
            assert call_kwargs["timeout"] == 60


class TestAuthentication:
    """Test authentication integration."""

    def test_bearer_auth_integration(self, base_url: str) -> None:
        """Test Bearer token authentication."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import BearerAuth

        auth = BearerAuth(token="test_token_123")
        client = RestClient(base_url=base_url, auth=auth)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/protected")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test_token_123"

    def test_api_key_auth_in_header(self, base_url: str) -> None:
        """Test API key authentication in header."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import APIKeyAuth

        auth = APIKeyAuth(key="test_key", location="header", name="X-API-Key")
        client = RestClient(base_url=base_url, auth=auth)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["X-API-Key"] == "test_key"

    def test_api_key_auth_in_query(self, base_url: str) -> None:
        """Test API key authentication in query parameter."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.models import APIKeyAuth

        auth = APIKeyAuth(key="test_key", location="query", name="api_key")
        client = RestClient(base_url=base_url, auth=auth)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["params"]["api_key"] == "test_key"  # pragma: allowlist secret

    def test_basic_auth(self, base_url: str) -> None:
        """Test basic authentication."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, auth=("username", "password"))

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            # Verify auth tuple was passed
            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["auth"] == ("username", "password")


class TestDefaultHeaders:
    """Test default headers configuration."""

    def test_default_headers_applied(self, base_url: str) -> None:
        """Test default headers are applied to all requests."""
        from amplihack.api_client import RestClient

        default_headers = {"User-Agent": "MyApp/1.0", "Accept": "application/json"}

        client = RestClient(base_url=base_url, default_headers=default_headers)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["User-Agent"] == "MyApp/1.0"
            assert call_kwargs["headers"]["Accept"] == "application/json"

    def test_request_headers_override_defaults(self, base_url: str) -> None:
        """Test request headers override default headers."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, default_headers={"Accept": "application/json"})

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint", headers={"Accept": "text/plain"})

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["headers"]["Accept"] == "text/plain"


class TestTimeoutHandling:
    """Test timeout configuration and handling."""

    def test_default_timeout(self, base_url: str) -> None:
        """Test default timeout is applied."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, timeout=30)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == 30

    def test_per_request_timeout_override(self, base_url: str) -> None:
        """Test per-request timeout overrides default."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, timeout=30)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/slow-endpoint", timeout=120)

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["timeout"] == 120

    def test_timeout_error_handling(self, base_url: str) -> None:
        """Test handling of timeout errors."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import TimeoutError as APITimeoutError

        client = RestClient(base_url=base_url, timeout=1, max_retries=0)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = TimeoutError("Request timed out")

            with pytest.raises(APITimeoutError):
                client.get("/slow")


class TestErrorHandling:
    """Test error handling in client."""

    def test_connection_error_handling(self, base_url: str) -> None:
        """Test handling of connection errors."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import RequestError

        client = RestClient(base_url=base_url, max_retries=0)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = ConnectionError("Connection refused")

            with pytest.raises(RequestError):
                client.get("/endpoint")

    def test_404_error_handling(self, base_url: str) -> None:
        """Test handling of 404 Not Found."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import NotFoundError

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=404, ok=False)

            with pytest.raises(NotFoundError):
                client.get("/missing")

    def test_401_error_handling(self, base_url: str) -> None:
        """Test handling of 401 Unauthorized."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import AuthenticationError

        client = RestClient(base_url=base_url)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=401, ok=False)

            with pytest.raises(AuthenticationError):
                client.get("/protected")

    def test_500_error_handling(self, base_url: str) -> None:
        """Test handling of 500 Internal Server Error."""
        from amplihack.api_client import RestClient
        from amplihack.api_client.exceptions import ServerError

        client = RestClient(base_url=base_url, max_retries=0)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=500, ok=False)

            with pytest.raises(ServerError):
                client.get("/error")


class TestLogging:
    """Test logging functionality."""

    def test_request_logging(self, base_url: str) -> None:
        """Test requests are logged."""

        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, debug=True)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            with patch("logging.Logger.debug") as mock_log:
                client.get("/endpoint")

                # Verify logging was called
                assert mock_log.called

    def test_response_logging(self, base_url: str) -> None:
        """Test responses are logged."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, debug=True)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            with patch("logging.Logger.debug") as mock_log:
                client.get("/endpoint")

                assert mock_log.called


class TestSSLVerification:
    """Test SSL certificate verification."""

    def test_ssl_verification_enabled_by_default(self, base_url: str) -> None:
        """Test SSL verification is enabled by default."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url)
        assert client.verify_ssl is True

    def test_ssl_verification_can_be_disabled(self, base_url: str) -> None:
        """Test SSL verification can be disabled."""
        from amplihack.api_client import RestClient

        client = RestClient(base_url=base_url, verify_ssl=False)
        assert client.verify_ssl is False

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = Mock(status_code=200, ok=True)

            client.get("/endpoint")

            call_kwargs = mock_request.call_args[1]
            assert call_kwargs["verify"] is False


class TestTypeHints:
    """Test type hints are properly defined."""

    def test_client_methods_have_type_hints(self) -> None:
        """Test all client methods have proper type hints."""
        import inspect

        from amplihack.api_client import RestClient

        # Check get method
        get_sig = inspect.signature(RestClient.get)
        assert get_sig.return_annotation != inspect.Signature.empty

        # Check post method
        post_sig = inspect.signature(RestClient.post)
        assert post_sig.return_annotation != inspect.Signature.empty

        # Check put method
        put_sig = inspect.signature(RestClient.put)
        assert put_sig.return_annotation != inspect.Signature.empty
