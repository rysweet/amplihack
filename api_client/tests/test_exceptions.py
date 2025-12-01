"""Tests for exception hierarchy and helper methods.

Testing pyramid distribution:
- 100% Unit tests (exceptions are pure, no dependencies)
"""

import pytest


class TestAPIError:
    """Test base APIError exception."""

    def test_create_api_error_minimal(self):
        """Test creating APIError with only message."""
        from api_client.exceptions import APIError

        # Arrange & Act
        error = APIError("Something went wrong")

        # Assert
        assert error.message == "Something went wrong"
        assert error.status_code is None
        assert error.response is None

    def test_create_api_error_with_status_code(self):
        """Test creating APIError with status code."""
        from api_client.exceptions import APIError

        # Arrange & Act
        error = APIError("Bad request", status_code=400)

        # Assert
        assert error.message == "Bad request"
        assert error.status_code == 400
        assert error.response is None

    def test_create_api_error_with_response(self, valid_url):
        """Test creating APIError with response object."""
        from api_client.exceptions import APIError
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response = Response(
            status_code=404, headers={}, body={"error": "Not found"}, request=request
        )

        # Act
        error = APIError("Not found", status_code=404, response=response)

        # Assert
        assert error.message == "Not found"
        assert error.status_code == 404
        assert error.response == response

    def test_api_error_str_representation(self):
        """Test string representation of APIError."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Test error", status_code=500)

        # Act
        error_str = str(error)

        # Assert
        assert "Test error" in error_str

    def test_api_error_is_timeout_true(self):
        """Test is_timeout() returns True for 408 status code."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Request timeout", status_code=408)

        # Act & Assert
        assert error.is_timeout() is True

    def test_api_error_is_timeout_false(self):
        """Test is_timeout() returns False for non-408 status codes."""
        from api_client.exceptions import APIError

        # Test various non-timeout status codes
        for status_code in [200, 400, 404, 429, 500, 503]:
            # Arrange
            error = APIError("Error", status_code=status_code)

            # Act & Assert
            assert error.is_timeout() is False

    def test_api_error_is_timeout_none_status(self):
        """Test is_timeout() returns False when status_code is None."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Error with no status code")

        # Act & Assert
        assert error.is_timeout() is False

    def test_api_error_is_rate_limited_true(self):
        """Test is_rate_limited() returns True for 429 status code."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Too many requests", status_code=429)

        # Act & Assert
        assert error.is_rate_limited() is True

    def test_api_error_is_rate_limited_false(self):
        """Test is_rate_limited() returns False for non-429 status codes."""
        from api_client.exceptions import APIError

        # Test various non-rate-limit status codes
        for status_code in [200, 400, 404, 408, 500, 503]:
            # Arrange
            error = APIError("Error", status_code=status_code)

            # Act & Assert
            assert error.is_rate_limited() is False

    def test_api_error_is_rate_limited_none_status(self):
        """Test is_rate_limited() returns False when status_code is None."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Error with no status code")

        # Act & Assert
        assert error.is_rate_limited() is False

    def test_api_error_inherits_from_exception(self):
        """Test that APIError inherits from base Exception."""
        from api_client.exceptions import APIError

        # Arrange
        error = APIError("Test")

        # Act & Assert
        assert isinstance(error, Exception)

    def test_api_error_can_be_raised(self):
        """Test that APIError can be raised and caught."""
        from api_client.exceptions import APIError

        # Act & Assert
        with pytest.raises(APIError) as exc_info:
            raise APIError("Test error", status_code=500)

        assert exc_info.value.message == "Test error"
        assert exc_info.value.status_code == 500


class TestClientError:
    """Test ClientError exception (4xx errors)."""

    def test_create_client_error(self):
        """Test creating ClientError with message and status."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Bad request", status_code=400)

        # Assert
        assert error.message == "Bad request"
        assert error.status_code == 400

    def test_client_error_inherits_from_api_error(self):
        """Test that ClientError inherits from APIError."""
        from api_client.exceptions import APIError, ClientError

        # Arrange
        error = ClientError("Test", status_code=404)

        # Act & Assert
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_client_error_400_bad_request(self):
        """Test ClientError for 400 Bad Request."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Invalid request body", status_code=400)

        # Assert
        assert error.status_code == 400
        assert "Invalid request body" in error.message

    def test_client_error_401_unauthorized(self):
        """Test ClientError for 401 Unauthorized."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Authentication required", status_code=401)

        # Assert
        assert error.status_code == 401

    def test_client_error_403_forbidden(self):
        """Test ClientError for 403 Forbidden."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Access denied", status_code=403)

        # Assert
        assert error.status_code == 403

    def test_client_error_404_not_found(self):
        """Test ClientError for 404 Not Found."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Resource not found", status_code=404)

        # Assert
        assert error.status_code == 404

    def test_client_error_429_rate_limited(self):
        """Test ClientError for 429 Too Many Requests."""
        from api_client.exceptions import ClientError

        # Arrange & Act
        error = ClientError("Rate limit exceeded", status_code=429)

        # Assert
        assert error.status_code == 429
        assert error.is_rate_limited() is True

    def test_client_error_can_be_caught_as_api_error(self):
        """Test that ClientError can be caught as APIError."""
        from api_client.exceptions import APIError, ClientError

        # Act & Assert
        with pytest.raises(APIError):
            raise ClientError("Test", status_code=404)

    def test_client_error_can_be_caught_specifically(self):
        """Test that ClientError can be caught specifically."""
        from api_client.exceptions import ClientError

        # Act & Assert
        with pytest.raises(ClientError) as exc_info:
            raise ClientError("Not found", status_code=404)

        assert exc_info.value.status_code == 404

    def test_client_error_with_response_object(self, valid_url, mock_error_response):
        """Test ClientError with response object attached."""
        from api_client.exceptions import ClientError
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response = Response(status_code=404, headers={}, body=mock_error_response, request=request)

        # Act
        error = ClientError("Not found", status_code=404, response=response)

        # Assert
        assert error.response == response
        assert error.response is not None
        assert error.response.body == mock_error_response


class TestServerError:
    """Test ServerError exception (5xx errors)."""

    def test_create_server_error(self):
        """Test creating ServerError with message and status."""
        from api_client.exceptions import ServerError

        # Arrange & Act
        error = ServerError("Internal server error", status_code=500)

        # Assert
        assert error.message == "Internal server error"
        assert error.status_code == 500

    def test_server_error_inherits_from_api_error(self):
        """Test that ServerError inherits from APIError."""
        from api_client.exceptions import APIError, ServerError

        # Arrange
        error = ServerError("Test", status_code=500)

        # Act & Assert
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)

    def test_server_error_500_internal_server_error(self):
        """Test ServerError for 500 Internal Server Error."""
        from api_client.exceptions import ServerError

        # Arrange & Act
        error = ServerError("Internal server error", status_code=500)

        # Assert
        assert error.status_code == 500

    def test_server_error_502_bad_gateway(self):
        """Test ServerError for 502 Bad Gateway."""
        from api_client.exceptions import ServerError

        # Arrange & Act
        error = ServerError("Bad gateway", status_code=502)

        # Assert
        assert error.status_code == 502

    def test_server_error_503_service_unavailable(self):
        """Test ServerError for 503 Service Unavailable."""
        from api_client.exceptions import ServerError

        # Arrange & Act
        error = ServerError("Service unavailable", status_code=503)

        # Assert
        assert error.status_code == 503

    def test_server_error_504_gateway_timeout(self):
        """Test ServerError for 504 Gateway Timeout."""
        from api_client.exceptions import ServerError

        # Arrange & Act
        error = ServerError("Gateway timeout", status_code=504)

        # Assert
        assert error.status_code == 504

    def test_server_error_can_be_caught_as_api_error(self):
        """Test that ServerError can be caught as APIError."""
        from api_client.exceptions import APIError, ServerError

        # Act & Assert
        with pytest.raises(APIError):
            raise ServerError("Test", status_code=500)

    def test_server_error_can_be_caught_specifically(self):
        """Test that ServerError can be caught specifically."""
        from api_client.exceptions import ServerError

        # Act & Assert
        with pytest.raises(ServerError) as exc_info:
            raise ServerError("Internal error", status_code=500)

        assert exc_info.value.status_code == 500

    def test_server_error_with_response_object(self, valid_url):
        """Test ServerError with response object attached."""
        from api_client.exceptions import ServerError
        from api_client.models import Request, Response

        # Arrange
        request = Request(url=valid_url, method="GET")
        response = Response(
            status_code=500, headers={}, body={"error": "Internal server error"}, request=request
        )

        # Act
        error = ServerError("Server error", status_code=500, response=response)

        # Assert
        assert error.response == response
        assert error.response is not None
        assert error.response.status_code == 500


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance."""

    def test_exception_inheritance_chain(self):
        """Test complete exception inheritance chain."""
        from api_client.exceptions import APIError, ClientError, ServerError

        # Arrange
        client_error = ClientError("Test", status_code=404)
        server_error = ServerError("Test", status_code=500)

        # Act & Assert - ClientError
        assert isinstance(client_error, ClientError)
        assert isinstance(client_error, APIError)
        assert isinstance(client_error, Exception)

        # Act & Assert - ServerError
        assert isinstance(server_error, ServerError)
        assert isinstance(server_error, APIError)
        assert isinstance(server_error, Exception)

    def test_catch_all_api_errors(self):
        """Test catching both ClientError and ServerError as APIError."""
        from api_client.exceptions import APIError, ClientError, ServerError

        # Test ClientError
        with pytest.raises(APIError):
            raise ClientError("Client error", status_code=404)

        # Test ServerError
        with pytest.raises(APIError):
            raise ServerError("Server error", status_code=500)

    def test_specific_exception_catch_order(self):
        """Test that specific exceptions can be caught before generic."""
        from api_client.exceptions import APIError, ClientError

        # Arrange
        caught_specific = False
        caught_generic = False

        # Act
        try:
            raise ClientError("Test", status_code=404)
        except ClientError:
            caught_specific = True
        except APIError:
            caught_generic = True

        # Assert
        assert caught_specific is True
        assert caught_generic is False

    def test_client_error_not_server_error(self):
        """Test that ClientError is not an instance of ServerError."""
        from api_client.exceptions import ClientError, ServerError

        # Arrange
        error = ClientError("Test", status_code=404)

        # Act & Assert
        assert not isinstance(error, ServerError)

    def test_server_error_not_client_error(self):
        """Test that ServerError is not an instance of ClientError."""
        from api_client.exceptions import ClientError, ServerError

        # Arrange
        error = ServerError("Test", status_code=500)

        # Act & Assert
        assert not isinstance(error, ClientError)
