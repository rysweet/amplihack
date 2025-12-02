"""Tests for API Client Exception hierarchy.

Tests the exception classes using the actual implementation API:
- APIClientError (base)
- RequestError (network/connection issues)
- ResponseError (response-related errors)
  - ClientError (4xx)
  - ServerError (5xx)
  - RateLimitError (429)
- RetryExhaustedError
- ConfigurationError

Testing pyramid target: 60% unit tests
"""

import pytest


class TestAPIClientError:
    """Tests for base APIClientError exception."""

    def test_import_base_exception(self) -> None:
        """Test that APIClientError can be imported."""
        from amplihack.utils.api_client.exceptions import APIClientError

        assert APIClientError is not None

    def test_base_exception_inherits_from_exception(self) -> None:
        """Test that APIClientError inherits from Exception."""
        from amplihack.utils.api_client.exceptions import APIClientError

        assert issubclass(APIClientError, Exception)

    def test_create_base_exception_with_message(self) -> None:
        """Test creating base exception with message."""
        from amplihack.utils.api_client.exceptions import APIClientError

        exc = APIClientError("Something went wrong")
        assert str(exc) == "Something went wrong"

    def test_base_exception_can_be_raised(self) -> None:
        """Test that base exception can be raised and caught."""
        from amplihack.utils.api_client.exceptions import APIClientError

        with pytest.raises(APIClientError, match="test error"):
            raise APIClientError("test error")


class TestRequestError:
    """Tests for RequestError exception."""

    def test_import_request_error(self) -> None:
        """Test that RequestError can be imported."""
        from amplihack.utils.api_client.exceptions import RequestError

        assert RequestError is not None

    def test_request_error_inherits_from_api_client_error(self) -> None:
        """Test that RequestError inherits from APIClientError."""
        from amplihack.utils.api_client.exceptions import APIClientError, RequestError

        assert issubclass(RequestError, APIClientError)

    def test_create_request_error(self) -> None:
        """Test creating RequestError with message."""
        from amplihack.utils.api_client.exceptions import RequestError

        exc = RequestError("Connection refused")
        assert str(exc) == "Connection refused"

    def test_request_error_caught_as_api_client_error(self) -> None:
        """Test that RequestError can be caught as APIClientError."""
        from amplihack.utils.api_client.exceptions import APIClientError, RequestError

        with pytest.raises(APIClientError):
            raise RequestError("Connection failed")


class TestResponseError:
    """Tests for ResponseError exception."""

    def test_import_response_error(self) -> None:
        """Test that ResponseError can be imported."""
        from amplihack.utils.api_client.exceptions import ResponseError

        assert ResponseError is not None

    def test_response_error_inherits_from_api_client_error(self) -> None:
        """Test that ResponseError inherits from APIClientError."""
        from amplihack.utils.api_client.exceptions import APIClientError, ResponseError

        assert issubclass(ResponseError, APIClientError)

    def test_create_response_error_with_status_code(self) -> None:
        """Test creating ResponseError with status code."""
        from amplihack.utils.api_client.exceptions import ResponseError

        exc = ResponseError("Not Found", status_code=404)
        assert exc.status_code == 404
        assert "Not Found" in str(exc)

    def test_response_error_with_response_body(self) -> None:
        """Test ResponseError with response body."""
        from amplihack.utils.api_client.exceptions import ResponseError

        exc = ResponseError(
            "Bad Request",
            status_code=400,
            response_body='{"error": "Invalid input"}',
        )
        assert exc.status_code == 400
        assert exc.response_body == '{"error": "Invalid input"}'

    def test_response_error_with_headers(self) -> None:
        """Test ResponseError with response headers."""
        from amplihack.utils.api_client.exceptions import ResponseError

        exc = ResponseError(
            "Unauthorized",
            status_code=401,
            response_headers={"WWW-Authenticate": "Bearer"},
        )
        assert exc.response_headers == {"WWW-Authenticate": "Bearer"}


class TestClientError:
    """Tests for ClientError exception (4xx errors)."""

    def test_import_client_error(self) -> None:
        """Test that ClientError can be imported."""
        from amplihack.utils.api_client.exceptions import ClientError

        assert ClientError is not None

    def test_client_error_inherits_from_response_error(self) -> None:
        """Test that ClientError inherits from ResponseError."""
        from amplihack.utils.api_client.exceptions import ClientError, ResponseError

        assert issubclass(ClientError, ResponseError)

    def test_create_client_error(self) -> None:
        """Test creating ClientError."""
        from amplihack.utils.api_client.exceptions import ClientError

        exc = ClientError("Bad Request", status_code=400)
        assert exc.status_code == 400

    def test_client_error_caught_as_response_error(self) -> None:
        """Test that ClientError can be caught as ResponseError."""
        from amplihack.utils.api_client.exceptions import ClientError, ResponseError

        with pytest.raises(ResponseError):
            raise ClientError("Bad Request", status_code=400)


class TestServerError:
    """Tests for ServerError exception (5xx errors)."""

    def test_import_server_error(self) -> None:
        """Test that ServerError can be imported."""
        from amplihack.utils.api_client.exceptions import ServerError

        assert ServerError is not None

    def test_server_error_inherits_from_response_error(self) -> None:
        """Test that ServerError inherits from ResponseError."""
        from amplihack.utils.api_client.exceptions import ResponseError, ServerError

        assert issubclass(ServerError, ResponseError)

    def test_create_server_error(self) -> None:
        """Test creating ServerError."""
        from amplihack.utils.api_client.exceptions import ServerError

        exc = ServerError("Internal Server Error", status_code=500)
        assert exc.status_code == 500

    def test_server_error_caught_as_response_error(self) -> None:
        """Test that ServerError can be caught as ResponseError."""
        from amplihack.utils.api_client.exceptions import ResponseError, ServerError

        with pytest.raises(ResponseError):
            raise ServerError("Server Error", status_code=500)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_import_rate_limit_error(self) -> None:
        """Test that RateLimitError can be imported."""
        from amplihack.utils.api_client.exceptions import RateLimitError

        assert RateLimitError is not None

    def test_rate_limit_error_inherits_from_client_error(self) -> None:
        """Test that RateLimitError inherits from ClientError."""
        from amplihack.utils.api_client.exceptions import ClientError, RateLimitError

        assert issubclass(RateLimitError, ClientError)

    def test_create_rate_limit_error(self) -> None:
        """Test creating RateLimitError."""
        from amplihack.utils.api_client.exceptions import RateLimitError

        exc = RateLimitError("Rate limit exceeded")
        assert exc.status_code == 429  # Default status code
        assert "Rate limit" in str(exc)

    def test_rate_limit_error_with_retry_after(self) -> None:
        """Test RateLimitError with retry_after attribute."""
        from amplihack.utils.api_client.exceptions import RateLimitError

        exc = RateLimitError("Rate limit exceeded", retry_after=60)
        assert exc.retry_after == 60

    def test_rate_limit_error_caught_as_client_error(self) -> None:
        """Test that RateLimitError can be caught as ClientError."""
        from amplihack.utils.api_client.exceptions import ClientError, RateLimitError

        with pytest.raises(ClientError):
            raise RateLimitError("Too many requests")


class TestRetryExhaustedError:
    """Tests for RetryExhaustedError exception."""

    def test_import_retry_exhausted_error(self) -> None:
        """Test that RetryExhaustedError can be imported."""
        from amplihack.utils.api_client.exceptions import RetryExhaustedError

        assert RetryExhaustedError is not None

    def test_retry_exhausted_error_inherits_from_api_client_error(self) -> None:
        """Test that RetryExhaustedError inherits from APIClientError."""
        from amplihack.utils.api_client.exceptions import APIClientError, RetryExhaustedError

        assert issubclass(RetryExhaustedError, APIClientError)

    def test_create_retry_exhausted_error(self) -> None:
        """Test creating RetryExhaustedError."""
        from amplihack.utils.api_client.exceptions import RetryExhaustedError

        exc = RetryExhaustedError("Max retries exceeded", attempts=3)
        assert exc.attempts == 3
        assert "Max retries" in str(exc)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_import_configuration_error(self) -> None:
        """Test that ConfigurationError can be imported."""
        from amplihack.utils.api_client.exceptions import ConfigurationError

        assert ConfigurationError is not None

    def test_configuration_error_inherits_from_api_client_error(self) -> None:
        """Test that ConfigurationError inherits from APIClientError."""
        from amplihack.utils.api_client.exceptions import APIClientError, ConfigurationError

        assert issubclass(ConfigurationError, APIClientError)

    def test_create_configuration_error(self) -> None:
        """Test creating ConfigurationError."""
        from amplihack.utils.api_client.exceptions import ConfigurationError

        exc = ConfigurationError("Invalid configuration: base_url required")
        assert "Invalid configuration" in str(exc)


class TestExceptionHierarchy:
    """Tests for complete exception hierarchy."""

    def test_all_exceptions_importable_from_module(self) -> None:
        """Test that all exceptions are importable from main module."""
        from amplihack.utils.api_client.exceptions import (
            APIClientError,
            ClientError,
            ConfigurationError,
            RateLimitError,
            RequestError,
            ResponseError,
            RetryExhaustedError,
            ServerError,
        )

        assert all([
            APIClientError,
            RequestError,
            ResponseError,
            ClientError,
            ServerError,
            RateLimitError,
            RetryExhaustedError,
            ConfigurationError,
        ])

    def test_exception_hierarchy_diagram(self) -> None:
        """Test the complete exception hierarchy.

        Expected hierarchy:
        Exception
        └── APIClientError
            ├── RequestError (network/connection)
            ├── ResponseError (HTTP response)
            │   ├── ClientError (4xx)
            │   │   └── RateLimitError (429)
            │   └── ServerError (5xx)
            ├── RetryExhaustedError
            └── ConfigurationError
        """
        from amplihack.utils.api_client.exceptions import (
            APIClientError,
            ClientError,
            ConfigurationError,
            RateLimitError,
            RequestError,
            ResponseError,
            RetryExhaustedError,
            ServerError,
        )

        # APIClientError is base
        assert issubclass(APIClientError, Exception)

        # First level children
        assert issubclass(RequestError, APIClientError)
        assert issubclass(ResponseError, APIClientError)
        assert issubclass(RetryExhaustedError, APIClientError)
        assert issubclass(ConfigurationError, APIClientError)

        # ResponseError children
        assert issubclass(ClientError, ResponseError)
        assert issubclass(ServerError, ResponseError)

        # RateLimitError is under ClientError
        assert issubclass(RateLimitError, ClientError)
        assert issubclass(RateLimitError, ResponseError)
        assert issubclass(RateLimitError, APIClientError)

    def test_catch_all_with_base_exception(self) -> None:
        """Test that all exceptions can be caught with APIClientError."""
        from amplihack.utils.api_client.exceptions import (
            APIClientError,
            ClientError,
            ConfigurationError,
            RateLimitError,
            RequestError,
            RetryExhaustedError,
            ServerError,
        )

        exceptions_to_test = [
            RequestError("network"),
            ClientError("client", status_code=400),
            ServerError("server", status_code=500),
            RateLimitError("rate limit"),
            RetryExhaustedError("retry", attempts=3),
            ConfigurationError("config"),
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except APIClientError as caught:
                assert caught is exc
            except Exception:
                pytest.fail(f"Failed to catch {type(exc).__name__} as APIClientError")
