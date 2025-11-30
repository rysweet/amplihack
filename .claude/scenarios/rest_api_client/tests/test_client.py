"""Unit tests for APIClient."""

import logging
from unittest.mock import patch

import httpx
import pytest

# These imports will fail initially (TDD)
from rest_api_client import APIClient
from rest_api_client.config import APIConfig
from rest_api_client.exceptions import (
    APIClientError,
    AuthenticationError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)


class TestAPIClientCreation:
    """Test APIClient instantiation."""

    def test_create_client_minimal(self):
        """Test creating client with minimal config."""
        client = APIClient(base_url="https://api.example.com")
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 30  # Default
        assert client.headers == {}

    def test_create_client_with_config(self):
        """Test creating client with config object."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=60,
            max_retries=5,
            headers={"X-API-Key": "secret"},
        )
        client = APIClient(config=config)
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 60
        assert client.max_retries == 5
        assert "X-API-Key" in client.headers

    def test_create_client_with_auth(self):
        """Test creating client with authentication."""
        client = APIClient(base_url="https://api.example.com", api_key="test-key-123")
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-key-123"

    def test_client_context_manager(self):
        """Test using client as context manager."""
        with APIClient(base_url="https://api.example.com") as client:
            assert client is not None
            assert hasattr(client, "get")


class TestAPIClientRequests:
    """Test APIClient HTTP methods."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return APIClient(base_url="https://api.example.com")

    def test_get_request(self, client, mock_response, mock_session):
        """Test GET request."""
        mock_session.request.return_value = mock_response(
            status_code=200, json_data={"id": 1, "name": "Test"}
        )

        with patch.object(client, "_session", mock_session):
            response = client.get("/users/1")

        assert response.status_code == 200
        assert response.json["id"] == 1
        mock_session.request.assert_called_once()

    def test_get_with_params(self, client, mock_response, mock_session):
        """Test GET request with query parameters."""
        mock_session.request.return_value = mock_response(200, json_data=[])

        with patch.object(client, "_session", mock_session):
            response = client.get("/users", params={"page": 2, "limit": 10})

        # Verify params were passed
        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["params"]["page"] == 2
        assert call_kwargs["params"]["limit"] == 10

    def test_post_request(self, client, mock_response, mock_session):
        """Test POST request."""
        request_data = {"name": "John", "email": "john@example.com"}
        mock_session.request.return_value = mock_response(
            201, json_data={"id": 123, **request_data}
        )

        with patch.object(client, "_session", mock_session):
            response = client.post("/users", json=request_data)

        assert response.status_code == 201
        assert response.json["id"] == 123
        mock_session.request.assert_called_once()

    def test_put_request(self, client, mock_response, mock_session):
        """Test PUT request."""
        update_data = {"name": "Jane"}
        mock_session.request.return_value = mock_response(200, json_data=update_data)

        with patch.object(client, "_session", mock_session):
            response = client.put("/users/1", json=update_data)

        assert response.status_code == 200
        mock_session.request.assert_called_once()

    def test_delete_request(self, client, mock_response, mock_session):
        """Test DELETE request."""
        mock_session.request.return_value = mock_response(204, json_data=None)

        with patch.object(client, "_session", mock_session):
            response = client.delete("/users/1")

        assert response.status_code == 204
        mock_session.request.assert_called_once()

    def test_patch_request(self, client, mock_response, mock_session):
        """Test PATCH request."""
        patch_data = {"status": "active"}
        mock_session.request.return_value = mock_response(200, json_data=patch_data)

        with patch.object(client, "_session", mock_session):
            response = client.patch("/users/1", json=patch_data)

        assert response.status_code == 200
        mock_session.request.assert_called_once()

    def test_custom_headers(self, client, mock_response, mock_session):
        """Test request with custom headers."""
        mock_session.request.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource", headers={"X-Custom-Header": "value"})

        call_kwargs = mock_session.request.call_args.kwargs
        assert "X-Custom-Header" in call_kwargs["headers"]

    def test_timeout_handling(self, client, mock_session):
        """Test timeout handling."""
        mock_session.request.side_effect = httpx.TimeoutException("Request timed out")

        with patch.object(client, "_session", mock_session):
            with pytest.raises(TimeoutError):
                client.get("/slow-endpoint", timeout=1)


class TestAPIClientErrorHandling:
    """Test error handling in APIClient."""

    @pytest.fixture
    def client(self):
        return APIClient(base_url="https://api.example.com")

    def test_handle_404_error(self, client, mock_response, mock_session):
        """Test handling 404 Not Found."""
        mock_session.request.return_value = mock_response(404, json_data={"error": "Not found"})

        with patch.object(client, "_session", mock_session):
            with pytest.raises(NotFoundError) as exc_info:
                client.get("/users/999")

        assert exc_info.value.status_code == 404

    def test_handle_401_error(self, client, mock_response, mock_session):
        """Test handling 401 Unauthorized."""
        mock_session.request.return_value = mock_response(401, json_data={"error": "Invalid token"})

        with patch.object(client, "_session", mock_session):
            with pytest.raises(AuthenticationError):
                client.get("/protected")

    def test_handle_429_rate_limit(self, client, mock_response, mock_session):
        """Test handling 429 rate limit."""
        mock_session.request.return_value = mock_response(
            429, json_data={"error": "Rate limit exceeded"}, headers={"Retry-After": "60"}
        )

        with patch.object(client, "_session", mock_session):
            with pytest.raises(RateLimitError) as exc_info:
                client.get("/resource")

        assert exc_info.value.retry_after == 60

    def test_handle_500_server_error(self, client, mock_response, mock_session):
        """Test handling 500 server error."""
        mock_session.request.return_value = mock_response(
            500, json_data={"error": "Internal error"}
        )

        with patch.object(client, "_session", mock_session):
            with pytest.raises(ServerError) as exc_info:
                client.get("/resource")

        assert exc_info.value.status_code == 500

    def test_handle_validation_error(self, client, mock_response, mock_session):
        """Test handling 422 validation error."""
        mock_session.request.return_value = mock_response(
            422,
            json_data={
                "error": "Validation failed",
                "fields": {"email": "Invalid format", "age": "Must be positive"},
            },
        )

        with patch.object(client, "_session", mock_session):
            with pytest.raises(ValidationError) as exc_info:
                client.post("/users", json={})

        assert exc_info.value.field_errors["email"] == "Invalid format"

    def test_connection_error(self, client, mock_session):
        """Test handling connection errors."""
        mock_session.request.side_effect = httpx.ConnectError("Failed to connect")

        with patch.object(client, "_session", mock_session):
            with pytest.raises(ConnectionError):
                client.get("/resource")


class TestAPIClientRetry:
    """Test retry functionality in APIClient."""

    @pytest.fixture
    def client(self):
        return APIClient(
            base_url="https://api.example.com",
            max_retries=3,
            retry_delay=0.01,  # Short delay for tests
        )

    def test_retry_on_server_error(self, client, mock_response, mock_session):
        """Test retrying on server errors."""
        # Fail twice, then succeed
        mock_session.request.side_effect = [
            mock_response(500, json_data={"error": "Server error"}),
            mock_response(503, json_data={"error": "Unavailable"}),
            mock_response(200, json_data={"success": True}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource")

        assert response.status_code == 200
        assert mock_session.request.call_count == 3

    def test_no_retry_on_client_error(self, client, mock_response, mock_session):
        """Test no retry on client errors."""
        mock_session.request.return_value = mock_response(400, json_data={"error": "Bad request"})

        with patch.object(client, "_session", mock_session):
            with pytest.raises(APIClientError):
                client.get("/resource")

        # Should not retry
        assert mock_session.request.call_count == 1

    def test_max_retries_exceeded(self, client, mock_response, mock_session):
        """Test max retries exceeded."""
        # Always fail
        mock_session.request.return_value = mock_response(500, json_data={"error": "Server error"})

        with patch.object(client, "_session", mock_session):
            with pytest.raises(ServerError):
                client.get("/resource")

        # Initial + 3 retries = 4 total
        assert mock_session.request.call_count == 4


class TestAPIClientRateLimiting:
    """Test rate limiting in APIClient."""

    @pytest.fixture
    def client(self):
        return APIClient(
            base_url="https://api.example.com",
            rate_limit_calls=2,
            rate_limit_period=1,  # 2 calls per second
        )

    def test_rate_limiting_enforced(self, client, mock_response, mock_session, mock_time):
        """Test that rate limiting is enforced."""
        mock_session.request.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            # First 2 calls should be immediate
            client.get("/resource")
            client.get("/resource")

            # 3rd call should be delayed
            client.get("/resource")

        # Verify timing with mock_time

    def test_adaptive_rate_limiting(self, client, mock_response, mock_session):
        """Test adaptive rate limiting on 429 responses."""
        # First call gets rate limited
        mock_session.request.side_effect = [
            mock_response(429, headers={"Retry-After": "2"}),
            mock_response(200, json_data={}),
        ]

        with patch.object(client, "_session", mock_session):
            response = client.get("/resource")

        assert response.status_code == 200
        # Should have adapted rate based on 429


class TestAPIClientLogging:
    """Test logging in APIClient."""

    @pytest.fixture
    def client(self):
        # Note: log_level is not a config parameter
        # Logging is configured at module level in client.py
        return APIClient(base_url="https://api.example.com")

    def test_request_logging(self, client, mock_response, mock_session, caplog):
        """Test that requests are logged."""
        mock_session.request.return_value = mock_response(200, json_data={})

        with patch.object(client, "_session", mock_session):
            with caplog.at_level(logging.DEBUG):
                client.get("/resource")

        assert "GET" in caplog.text
        assert "/resource" in caplog.text

    def test_response_logging(self, client, mock_response, mock_session, caplog):
        """Test that responses are logged."""
        mock_session.request.return_value = mock_response(200, json_data={"data": "test"})

        with patch.object(client, "_session", mock_session):
            with caplog.at_level(logging.DEBUG):
                client.get("/resource")

        assert "200" in caplog.text
        assert "Response" in caplog.text

    def test_error_logging(self, client, mock_response, mock_session, caplog):
        """Test that errors are logged."""
        mock_session.request.return_value = mock_response(500, json_data={"error": "Failed"})

        with patch.object(client, "_session", mock_session):
            with caplog.at_level(logging.ERROR):
                with pytest.raises(ServerError):
                    client.get("/resource")

        assert "500" in caplog.text
        assert "error" in caplog.text.lower()
