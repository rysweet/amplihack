"""TDD Tests for API Client Module.

These tests define the expected behavior of the API Client module.
They are written BEFORE implementation and should FAIL until the
implementation is complete.

Testing Pyramid:
- 60% Unit tests (13 tests) - mock requests library
- 30% Integration tests (2 tests) - test multiple components
- 10% E2E tests (0 tests) - would require real server

Run with: pytest tests/test_api_client.py -v
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
from api_client import APIClient, APIError, AuthType

# =============================================================================
# UNIT TESTS (60% - 13 tests)
# =============================================================================


class TestAuthType:
    """Tests for AuthType enumeration."""

    def test_auth_type_has_none_value(self):
        """AuthType.NONE should exist for unauthenticated requests."""
        assert AuthType.NONE is not None
        assert isinstance(AuthType.NONE, AuthType)

    def test_auth_type_has_bearer_value(self):
        """AuthType.BEARER should exist for Bearer token auth."""
        assert AuthType.BEARER is not None
        assert isinstance(AuthType.BEARER, AuthType)

    def test_auth_type_has_api_key_value(self):
        """AuthType.API_KEY should exist for API key auth."""
        assert AuthType.API_KEY is not None
        assert isinstance(AuthType.API_KEY, AuthType)


class TestAPIError:
    """Tests for APIError exception class."""

    def test_api_error_has_status_code(self):
        """APIError should store status_code attribute."""
        error = APIError(status_code=404, message="Not Found")
        assert error.status_code == 404

    def test_api_error_has_message(self):
        """APIError should store message attribute."""
        error = APIError(status_code=500, message="Internal Server Error")
        assert error.message == "Internal Server Error"

    def test_api_error_has_optional_response_body(self):
        """APIError should store optional response_body attribute."""
        error = APIError(
            status_code=400, message="Bad Request", response_body='{"error": "invalid_input"}'
        )
        assert error.response_body == '{"error": "invalid_input"}'

    def test_api_error_response_body_defaults_to_none(self):
        """APIError response_body should default to None."""
        error = APIError(status_code=500, message="Error")
        assert error.response_body is None

    def test_api_error_is_exception(self):
        """APIError should be an Exception subclass."""
        error = APIError(status_code=500, message="Error")
        assert isinstance(error, Exception)


class TestAPIClientInit:
    """Tests for APIClient constructor."""

    def test_client_requires_base_url(self):
        """APIClient should require base_url parameter."""
        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_client_auth_type_defaults_to_none(self):
        """APIClient auth_type should default to AuthType.NONE."""
        client = APIClient(base_url="https://api.example.com")
        assert client.auth_type == AuthType.NONE

    def test_client_accepts_auth_token(self):
        """APIClient should accept auth_token for Bearer auth."""
        client = APIClient(
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER,
            auth_token="secret-token-123",
        )
        assert client.auth_token == "secret-token-123"

    def test_client_accepts_api_key_header(self):
        """APIClient should accept custom api_key_header name."""
        client = APIClient(
            base_url="https://api.example.com",
            auth_type=AuthType.API_KEY,
            auth_token="api-key-456",
            api_key_header="X-Custom-API-Key",  # pragma: allowlist secret
        )
        assert client.api_key_header == "X-Custom-API-Key"  # pragma: allowlist secret

    def test_client_timeout_configurable(self):
        """APIClient should accept configurable timeout."""
        client = APIClient(base_url="https://api.example.com", timeout=60)
        assert client.timeout == 60

    def test_client_timeout_has_default(self):
        """APIClient should have a default timeout."""
        client = APIClient(base_url="https://api.example.com")
        assert client.timeout is not None
        assert client.timeout > 0


class TestAPIClientGet:
    """Tests for APIClient.get() method."""

    @patch("api_client.requests")
    def test_get_returns_json_dict(self, mock_requests):
        """GET request should return parsed JSON as dict."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Test"}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act
        result = client.get("/users/1")

        # Assert
        assert result == {"id": 1, "name": "Test"}
        mock_requests.get.assert_called_once()

    @patch("api_client.requests")
    def test_get_passes_query_params(self, mock_requests):
        """GET request should pass query parameters."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act
        client.get("/search", params={"q": "test", "limit": 10})

        # Assert
        call_kwargs = mock_requests.get.call_args
        assert call_kwargs[1].get("params") == {"q": "test", "limit": 10}


class TestAPIClientPost:
    """Tests for APIClient.post() method."""

    @patch("api_client.requests")
    def test_post_sends_json_body(self, mock_requests):
        """POST request should send JSON body."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "created": True}
        mock_requests.post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        data = {"name": "New Item", "value": 42}

        # Act
        result = client.post("/items", data=data)

        # Assert
        assert result == {"id": 123, "created": True}
        call_kwargs = mock_requests.post.call_args
        assert call_kwargs[1].get("json") == data


class TestAPIClientPut:
    """Tests for APIClient.put() method."""

    @patch("api_client.requests")
    def test_put_sends_json_body(self, mock_requests):
        """PUT request should send JSON body."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "updated": True}
        mock_requests.put.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")
        data = {"name": "Updated Item"}

        # Act
        result = client.put("/items/1", data=data)

        # Assert
        assert result == {"id": 1, "updated": True}
        call_kwargs = mock_requests.put.call_args
        assert call_kwargs[1].get("json") == data


class TestAPIClientDelete:
    """Tests for APIClient.delete() method."""

    @patch("api_client.requests")
    def test_delete_returns_response(self, mock_requests):
        """DELETE request should return response data."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"deleted": True}
        mock_requests.delete.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act
        result = client.delete("/items/1")

        # Assert
        assert result == {"deleted": True}
        mock_requests.delete.assert_called_once()


class TestAPIClientAuthentication:
    """Tests for authentication handling."""

    @patch("api_client.requests")
    def test_bearer_auth_adds_header(self, mock_requests):
        """Bearer auth should add Authorization header."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER,
            auth_token="my-bearer-token",
        )

        # Act
        client.get("/protected")

        # Assert
        call_kwargs = mock_requests.get.call_args
        headers = call_kwargs[1].get("headers", {})
        assert headers.get("Authorization") == "Bearer my-bearer-token"

    @patch("api_client.requests")
    def test_api_key_auth_adds_custom_header(self, mock_requests):
        """API key auth should add custom header."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            auth_type=AuthType.API_KEY,
            auth_token="api-key-secret",
            api_key_header="X-API-Key",  # pragma: allowlist secret
        )

        # Act
        client.get("/protected")

        # Assert
        call_kwargs = mock_requests.get.call_args
        headers = call_kwargs[1].get("headers", {})
        assert headers.get("X-API-Key") == "api-key-secret"  # pragma: allowlist secret

    @patch("api_client.requests")
    def test_no_auth_no_header(self, mock_requests):
        """No auth should not add Authorization header."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com", auth_type=AuthType.NONE)

        # Act
        client.get("/public")

        # Assert
        call_kwargs = mock_requests.get.call_args
        headers = call_kwargs[1].get("headers", {})
        assert "Authorization" not in headers


class TestAPIClientTimeout:
    """Tests for timeout handling."""

    @patch("api_client.requests")
    def test_timeout_configurable(self, mock_requests):
        """Request should use configured timeout."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com", timeout=45)

        # Act
        client.get("/slow-endpoint")

        # Assert
        call_kwargs = mock_requests.get.call_args
        assert call_kwargs[1].get("timeout") == 45


class TestAPIClientErrorHandling:
    """Tests for error handling."""

    @patch("api_client.requests")
    def test_4xx_raises_api_error(self, mock_requests):
        """4xx responses should raise APIError."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = '{"error": "Not Found"}'
        mock_response.json.return_value = {"error": "Not Found"}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.get("/nonexistent")

        assert exc_info.value.status_code == 404

    @patch("api_client.requests")
    def test_5xx_raises_api_error(self, mock_requests):
        """5xx responses should raise APIError."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.get("/broken")

        assert exc_info.value.status_code == 500

    @patch("api_client.requests")
    def test_connection_error_raises_api_error(self, mock_requests):
        """Connection errors should raise APIError."""
        import requests as real_requests

        # Arrange
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError(
            "Failed to connect"
        )
        mock_requests.exceptions = real_requests.exceptions

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.get("/unreachable")

        assert exc_info.value.status_code == 0  # Convention for connection errors

    @patch("api_client.requests")
    def test_timeout_raises_api_error(self, mock_requests):
        """Timeout errors should raise APIError."""
        import requests as real_requests

        # Arrange
        mock_requests.get.side_effect = real_requests.exceptions.Timeout("Request timed out")
        mock_requests.exceptions = real_requests.exceptions

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.get("/slow")

        assert "timeout" in exc_info.value.message.lower()

    @patch("api_client.requests")
    def test_invalid_json_raises_api_error(self, mock_requests):
        """Invalid JSON response should raise APIError."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "not valid json {"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.get("/bad-json")

        assert "json" in exc_info.value.message.lower()


# =============================================================================
# INTEGRATION TESTS (30% - 2 tests)
# =============================================================================


class TestAPIClientIntegration:
    """Integration tests for APIClient - test multiple components together."""

    @patch("api_client.requests")
    def test_full_request_flow_mocked(self, mock_requests):
        """Test complete request flow: auth + request + response parsing."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 999,
            "name": "Integration Test",
            "status": "created",
        }
        mock_requests.post.return_value = mock_response

        client = APIClient(
            base_url="https://api.example.com",
            auth_type=AuthType.BEARER,
            auth_token="integration-test-token",
            timeout=30,
        )

        # Act
        result = client.post("/resources", data={"name": "Integration Test", "type": "test"})

        # Assert - verify complete flow
        # 1. URL was constructed correctly
        call_args = mock_requests.post.call_args
        assert "https://api.example.com/resources" in str(call_args)

        # 2. Auth header was added
        headers = call_args[1].get("headers", {})
        assert headers.get("Authorization") == "Bearer integration-test-token"

        # 3. JSON body was sent
        assert call_args[1].get("json") == {"name": "Integration Test", "type": "test"}

        # 4. Timeout was set
        assert call_args[1].get("timeout") == 30

        # 5. Response was parsed correctly
        assert result == {"id": 999, "name": "Integration Test", "status": "created"}

    @patch("api_client.requests")
    def test_error_message_format(self, mock_requests):
        """Test that error messages contain useful information."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = '{"errors": ["field_x is required", "field_y invalid"]}'
        mock_response.json.return_value = {"errors": ["field_x is required", "field_y invalid"]}
        mock_requests.post.return_value = mock_response

        client = APIClient(base_url="https://api.example.com")

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            client.post("/validate", data={"incomplete": "data"})

        error = exc_info.value

        # Error should contain:
        # 1. Status code
        assert error.status_code == 422

        # 2. Meaningful message
        assert error.message is not None
        assert len(error.message) > 0

        # 3. Response body for debugging
        assert error.response_body is not None
        assert "field_x" in error.response_body or "errors" in error.response_body


# =============================================================================
# TEST MARKERS FOR ORGANIZATION
# =============================================================================


# Mark slow tests (if any become slow in future)
# @pytest.mark.slow

# Mark tests requiring network (none currently, all mocked)
# @pytest.mark.network


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
