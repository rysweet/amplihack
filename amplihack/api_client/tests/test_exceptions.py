"""Unit tests fer API Client exception hierarchy.

Tests the exception classes, inheritance, factory functions,
and context attribute preservation.

Testing pyramid: Unit tests (60%)
"""

import pytest

# Imports will fail initially - this be TDD!
from amplihack.api_client.exceptions import (
    APIError,
    BadGatewayError,
    BadRequestError,
    ClientError,
    ForbiddenError,
    GatewayTimeoutError,
    InternalServerError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    UnauthorizedError,
    create_exception_for_status,
)


class TestAPIErrorBase:
    """Test the base APIError exception class."""

    def test_api_error_is_exception(self) -> None:
        """Verify APIError inherits from Exception."""
        # Arrange & Act
        error = APIError("test message")

        # Assert
        assert isinstance(error, Exception)

    def test_api_error_message(self) -> None:
        """Verify APIError stores the error message."""
        # Arrange
        message = "Something went wrong"

        # Act
        error = APIError(message)

        # Assert
        assert str(error) == message
        assert error.message == message

    def test_api_error_with_context(self) -> None:
        """Verify APIError stores context attributes."""
        # Arrange
        message = "Request failed"
        status_code = 500
        request_data = {"url": "https://api.example.com"}
        response_data = {"error": "Server error"}

        # Act
        error = APIError(
            message=message,
            status_code=status_code,
            request=request_data,
            response=response_data,
        )

        # Assert
        assert error.message == message
        assert error.status_code == status_code
        assert error.request == request_data
        assert error.response == response_data


class TestClientError:
    """Test ClientError exception class (4xx errors)."""

    def test_client_error_inherits_from_api_error(self) -> None:
        """Verify ClientError inherits from APIError."""
        # Arrange & Act
        error = ClientError("client error")

        # Assert
        assert isinstance(error, APIError)
        assert isinstance(error, ClientError)

    def test_bad_request_error_is_400(self) -> None:
        """Verify BadRequestError represents 400 status."""
        # Arrange & Act
        error = BadRequestError("bad request", status_code=400)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == 400

    def test_unauthorized_error_is_401(self) -> None:
        """Verify UnauthorizedError represents 401 status."""
        # Arrange & Act
        error = UnauthorizedError("unauthorized", status_code=401)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == 401

    def test_forbidden_error_is_403(self) -> None:
        """Verify ForbiddenError represents 403 status."""
        # Arrange & Act
        error = ForbiddenError("forbidden", status_code=403)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == 403

    def test_not_found_error_is_404(self) -> None:
        """Verify NotFoundError represents 404 status."""
        # Arrange & Act
        error = NotFoundError("not found", status_code=404)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == 404

    def test_rate_limit_error_is_429(self) -> None:
        """Verify RateLimitError represents 429 status."""
        # Arrange & Act
        error = RateLimitError("rate limited", status_code=429)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == 429


class TestServerError:
    """Test ServerError exception class (5xx errors)."""

    def test_server_error_inherits_from_api_error(self) -> None:
        """Verify ServerError inherits from APIError."""
        # Arrange & Act
        error = ServerError("server error")

        # Assert
        assert isinstance(error, APIError)
        assert isinstance(error, ServerError)

    def test_internal_server_error_is_500(self) -> None:
        """Verify InternalServerError represents 500 status."""
        # Arrange & Act
        error = InternalServerError("internal error", status_code=500)

        # Assert
        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_bad_gateway_error_is_502(self) -> None:
        """Verify BadGatewayError represents 502 status."""
        # Arrange & Act
        error = BadGatewayError("bad gateway", status_code=502)

        # Assert
        assert isinstance(error, ServerError)
        assert error.status_code == 502

    def test_service_unavailable_error_is_503(self) -> None:
        """Verify ServiceUnavailableError represents 503 status."""
        # Arrange & Act
        error = ServiceUnavailableError("service unavailable", status_code=503)

        # Assert
        assert isinstance(error, ServerError)
        assert error.status_code == 503

    def test_gateway_timeout_error_is_504(self) -> None:
        """Verify GatewayTimeoutError represents 504 status."""
        # Arrange & Act
        error = GatewayTimeoutError("gateway timeout", status_code=504)

        # Assert
        assert isinstance(error, ServerError)
        assert error.status_code == 504


class TestNetworkErrors:
    """Test network-related exception classes."""

    def test_network_error_inherits_from_api_error(self) -> None:
        """Verify NetworkError inherits from APIError."""
        # Arrange & Act
        error = NetworkError("network failure")

        # Assert
        assert isinstance(error, APIError)
        assert isinstance(error, NetworkError)

    def test_timeout_error_inherits_from_api_error(self) -> None:
        """Verify TimeoutError inherits from APIError."""
        # Arrange & Act
        error = TimeoutError("request timeout")

        # Assert
        assert isinstance(error, APIError)
        assert isinstance(error, TimeoutError)


class TestExceptionFactory:
    """Test create_exception_for_status factory function."""

    @pytest.mark.parametrize(
        "status_code,expected_exception",
        [
            (400, BadRequestError),
            (401, UnauthorizedError),
            (403, ForbiddenError),
            (404, NotFoundError),
            (429, RateLimitError),
            (500, InternalServerError),
            (502, BadGatewayError),
            (503, ServiceUnavailableError),
            (504, GatewayTimeoutError),
        ],
    )
    def test_factory_creates_correct_exception(
        self, status_code: int, expected_exception: type
    ) -> None:
        """Verify factory creates correct exception fer status code."""
        # Arrange
        message = f"Error {status_code}"

        # Act
        error = create_exception_for_status(status_code, message)

        # Assert
        assert isinstance(error, expected_exception)
        assert error.status_code == status_code
        assert error.message == message

    def test_factory_with_4xx_creates_client_error(self) -> None:
        """Verify factory creates ClientError fer unspecified 4xx codes."""
        # Arrange
        status_code = 418  # I'm a teapot
        message = "Teapot error"

        # Act
        error = create_exception_for_status(status_code, message)

        # Assert
        assert isinstance(error, ClientError)
        assert error.status_code == status_code

    def test_factory_with_5xx_creates_server_error(self) -> None:
        """Verify factory creates ServerError fer unspecified 5xx codes."""
        # Arrange
        status_code = 599  # Custom server error
        message = "Custom server error"

        # Act
        error = create_exception_for_status(status_code, message)

        # Assert
        assert isinstance(error, ServerError)
        assert error.status_code == status_code

    def test_factory_with_context_attributes(self) -> None:
        """Verify factory preserves context attributes."""
        # Arrange
        status_code = 404
        message = "Not found"
        request_data = {"url": "https://api.example.com/missing"}
        response_data = {"error": "Resource not found"}

        # Act
        error = create_exception_for_status(
            status_code=status_code,
            message=message,
            request=request_data,
            response=response_data,
        )

        # Assert
        assert error.request == request_data
        assert error.response == response_data

    def test_factory_with_none_context(self) -> None:
        """Verify factory handles None context gracefully."""
        # Arrange
        status_code = 500
        message = "Server error"

        # Act
        error = create_exception_for_status(
            status_code=status_code, message=message, request=None, response=None
        )

        # Assert
        assert error.request is None
        assert error.response is None
