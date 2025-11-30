"""Tests for API client exception hierarchy - TDD approach.

Tests custom exceptions, error propagation, and error messages.
"""

from amplihack.api_client.exceptions import (
    APIClientError,
    AuthenticationError,
    BadGatewayError,
    ClientError,
    ConfigurationError,
    ConnectionError,
    DNSError,
    HTTPError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    SSLError,
    TimeoutError,
    ValidationError,
    error_from_response,
    parse_error_response,
)
from amplihack.api_client.models import ErrorDetail, Request, Response


class TestExceptionHierarchy:
    """Unit tests for exception class hierarchy."""

    def test_base_exception(self):
        """Test base APIClientError."""
        error = APIClientError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response is None
        assert error.request is None

    def test_base_exception_with_context(self):
        """Test base exception with request/response context."""
        request = Request(method="GET", url="https://api.example.com/test")
        response = Response(
            status_code=500,
            headers={},
            data={"error": "Server error"},
            request=request,
        )

        error = APIClientError("Test error", status_code=500, response=response)
        assert error.status_code == 500
        assert error.response == response
        assert error.request == request  # Extracted from response

    def test_exception_inheritance(self):
        """Test exception inheritance chain."""
        # Network errors
        assert issubclass(NetworkError, APIClientError)
        assert issubclass(TimeoutError, NetworkError)
        assert issubclass(ConnectionError, NetworkError)
        assert issubclass(DNSError, NetworkError)
        assert issubclass(SSLError, NetworkError)

        # HTTP errors
        assert issubclass(HTTPError, APIClientError)
        assert issubclass(ClientError, HTTPError)
        assert issubclass(ServerError, HTTPError)

        # Client errors
        assert issubclass(ValidationError, ClientError)
        assert issubclass(AuthenticationError, ClientError)
        assert issubclass(NotFoundError, ClientError)
        assert issubclass(RateLimitError, ClientError)

        # Server errors
        assert issubclass(BadGatewayError, ServerError)
        assert issubclass(ServiceUnavailableError, ServerError)

        # Configuration error
        assert issubclass(ConfigurationError, APIClientError)


class TestNetworkErrors:
    """Unit tests for network-related exceptions."""

    def test_network_error(self):
        """Test generic network error."""
        error = NetworkError("Connection failed")
        assert str(error) == "Network error: Connection failed"
        assert error.message == "Connection failed"

    def test_timeout_error(self):
        """Test timeout error."""
        error = TimeoutError("Request timed out after 30s")
        assert "Request timed out" in str(error)
        assert isinstance(error, NetworkError)

    def test_connection_error(self):
        """Test connection error."""
        error = ConnectionError("Connection refused to api.example.com:443")
        assert "Connection refused" in str(error)
        assert isinstance(error, NetworkError)

    def test_dns_error(self):
        """Test DNS resolution error."""
        error = DNSError("Could not resolve hostname: api.example.com")
        assert "Could not resolve" in str(error)
        assert isinstance(error, NetworkError)

    def test_ssl_error(self):
        """Test SSL/TLS error."""
        error = SSLError("SSL certificate verification failed")
        assert "SSL certificate" in str(error)
        assert isinstance(error, NetworkError)


class TestHTTPErrors:
    """Unit tests for HTTP status code errors."""

    def test_http_error_base(self):
        """Test base HTTPError."""
        request = Request(method="GET", url="https://api.example.com/test")
        response = Response(
            status_code=500,
            headers={},
            data={"error": "Internal error"},
            request=request,
        )

        error = HTTPError("HTTP error occurred", status_code=500, response=response)
        assert error.status_code == 500
        assert error.response == response
        assert "HTTP 500" in str(error)

    def test_client_error_400(self):
        """Test 400 Bad Request error."""
        error = ValidationError("Invalid request data", status_code=400)
        assert error.status_code == 400
        assert isinstance(error, ClientError)
        assert "Invalid request" in str(error)

    def test_authentication_error_401(self):
        """Test 401 Unauthorized error."""
        error = AuthenticationError("Invalid API key", status_code=401)
        assert error.status_code == 401
        assert isinstance(error, ClientError)
        assert "Authentication failed" in str(error)

    def test_authentication_error_403(self):
        """Test 403 Forbidden error."""
        error = AuthenticationError("Insufficient permissions", status_code=403)
        assert error.status_code == 403
        assert isinstance(error, ClientError)
        assert "Authentication failed" in str(error)

    def test_not_found_error_404(self):
        """Test 404 Not Found error."""
        error = NotFoundError("Resource not found", status_code=404)
        assert error.status_code == 404
        assert isinstance(error, ClientError)
        assert "Not found" in str(error)

    def test_rate_limit_error_429(self):
        """Test 429 Too Many Requests error."""
        error = RateLimitError(
            "Rate limit exceeded",
            status_code=429,
            retry_after=60,
            limit=1000,
            remaining=0,
        )
        assert error.status_code == 429
        assert error.retry_after == 60
        assert error.limit == 1000
        assert error.remaining == 0
        assert isinstance(error, ClientError)
        assert "Rate limit exceeded" in str(error)

    def test_server_error_500(self):
        """Test 500 Internal Server Error."""
        error = ServerError("Internal server error", status_code=500)
        assert error.status_code == 500
        assert isinstance(error, HTTPError)
        assert "Server error" in str(error)

    def test_bad_gateway_error_502(self):
        """Test 502 Bad Gateway error."""
        error = BadGatewayError("Bad gateway", status_code=502)
        assert error.status_code == 502
        assert isinstance(error, ServerError)
        assert "Bad gateway" in str(error)

    def test_service_unavailable_error_503(self):
        """Test 503 Service Unavailable error."""
        error = ServiceUnavailableError("Service temporarily unavailable", status_code=503)
        assert error.status_code == 503
        assert isinstance(error, ServerError)
        assert "Service unavailable" in str(error)


class TestConfigurationError:
    """Unit tests for configuration errors."""

    def test_configuration_error(self):
        """Test configuration validation error."""
        error = ConfigurationError("Invalid API base URL")
        assert "Configuration error" in str(error)
        assert isinstance(error, APIClientError)

    def test_configuration_error_with_field(self):
        """Test configuration error with specific field."""
        error = ConfigurationError("Timeout must be positive", field="timeout")
        assert error.field == "timeout"
        assert "Timeout must be positive" in str(error)


class TestErrorParsing:
    """Unit tests for error response parsing."""

    def test_parse_json_error_response(self):
        """Test parsing JSON error response."""
        response_text = '{"error": {"code": "INVALID", "message": "Invalid input"}}'

        result = parse_error_response(response_text, "application/json")
        assert result["error"]["code"] == "INVALID"
        assert result["error"]["message"] == "Invalid input"

    def test_parse_text_error_response(self):
        """Test parsing plain text error response."""
        response_text = "Bad request: Missing required field"

        result = parse_error_response(response_text, "text/plain")
        assert result["error"] == "Bad request: Missing required field"

    def test_parse_html_error_response(self):
        """Test parsing HTML error response."""
        response_text = "<html><body><h1>404 Not Found</h1></body></html>"

        result = parse_error_response(response_text, "text/html")
        assert "404 Not Found" in result["error"]

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON falls back to text."""
        response_text = "{'invalid': json}"

        result = parse_error_response(response_text, "application/json")
        assert result["error"] == "{'invalid': json}"

    def test_parse_empty_response(self):
        """Test parsing empty response."""
        result = parse_error_response("", "application/json")
        assert result == {"error": "Empty response"}

        result = parse_error_response(None, "application/json")
        assert result == {"error": "Empty response"}


class TestErrorFactory:
    """Unit tests for error_from_response factory function."""

    def test_error_from_400_response(self):
        """Test creating ValidationError from 400 response."""
        request = Request(method="POST", url="https://api.example.com/users")
        response = Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            data={"error": "Invalid email format"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, ValidationError)
        assert error.status_code == 400
        assert "Invalid email format" in str(error)

    def test_error_from_401_response(self):
        """Test creating AuthenticationError from 401 response."""
        request = Request(method="GET", url="https://api.example.com/protected")
        response = Response(
            status_code=401,
            headers={},
            data={"error": "Invalid token"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, AuthenticationError)
        assert error.status_code == 401

    def test_error_from_403_response(self):
        """Test creating AuthenticationError from 403 response."""
        request = Request(method="DELETE", url="https://api.example.com/admin")
        response = Response(
            status_code=403,
            headers={},
            data={"error": "Forbidden"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, AuthenticationError)
        assert error.status_code == 403

    def test_error_from_404_response(self):
        """Test creating NotFoundError from 404 response."""
        request = Request(method="GET", url="https://api.example.com/users/999")
        response = Response(
            status_code=404,
            headers={},
            data={"error": "User not found"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, NotFoundError)
        assert error.status_code == 404

    def test_error_from_429_response(self):
        """Test creating RateLimitError from 429 response."""
        request = Request(method="GET", url="https://api.example.com/data")
        response = Response(
            status_code=429,
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": "1000",
                "X-RateLimit-Remaining": "0",
            },
            data={"error": "Rate limit exceeded"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, RateLimitError)
        assert error.status_code == 429
        assert error.retry_after == 60
        assert error.limit == 1000
        assert error.remaining == 0

    def test_error_from_500_response(self):
        """Test creating ServerError from 500 response."""
        request = Request(method="POST", url="https://api.example.com/process")
        response = Response(
            status_code=500,
            headers={},
            data={"error": "Internal server error"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_error_from_502_response(self):
        """Test creating BadGatewayError from 502 response."""
        request = Request(method="GET", url="https://api.example.com/proxy")
        response = Response(
            status_code=502,
            headers={},
            data=None,
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, BadGatewayError)
        assert error.status_code == 502

    def test_error_from_503_response(self):
        """Test creating ServiceUnavailableError from 503 response."""
        request = Request(method="GET", url="https://api.example.com/health")
        response = Response(
            status_code=503,
            headers={"Retry-After": "300"},
            data={"error": "Service under maintenance"},
            request=request,
        )

        error = error_from_response(response)
        assert isinstance(error, ServiceUnavailableError)
        assert error.status_code == 503

    def test_error_from_unknown_status(self):
        """Test creating generic HTTPError for unknown status codes."""
        request = Request(method="GET", url="https://api.example.com/test")

        # Unknown 4xx
        response = Response(
            status_code=418,  # I'm a teapot
            headers={},
            data={"error": "I'm a teapot"},
            request=request,
        )
        error = error_from_response(response)
        assert isinstance(error, ClientError)
        assert error.status_code == 418

        # Unknown 5xx
        response = Response(
            status_code=507,  # Insufficient Storage
            headers={},
            data={"error": "Insufficient storage"},
            request=request,
        )
        error = error_from_response(response)
        assert isinstance(error, ServerError)
        assert error.status_code == 507

        # Unknown other
        response = Response(
            status_code=999,
            headers={},
            data={"error": "Unknown error"},
            request=request,
        )
        error = error_from_response(response)
        assert isinstance(error, HTTPError)
        assert error.status_code == 999


class TestExceptionFormatting:
    """Unit tests for exception string formatting."""

    def test_exception_with_details(self):
        """Test exception formatting with ErrorDetail."""
        detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid input",
            field="email",
            details={"pattern": "^[a-z]+@[a-z]+\\.[a-z]+$"},
        )

        error = ValidationError("Validation failed", status_code=400, details=[detail])
        error_str = str(error)
        assert "Validation failed" in error_str
        assert "VALIDATION_ERROR" in error_str or "400" in error_str

    def test_exception_chaining(self):
        """Test exception chaining with __cause__."""
        original = ConnectionError("Connection refused")
        wrapped = NetworkError("Failed to connect to API")
        wrapped.__cause__ = original

        assert wrapped.__cause__ == original
        assert "Connection refused" in str(original)
        assert "Failed to connect" in str(wrapped)

    def test_exception_context_preservation(self):
        """Test that request/response context is preserved."""
        request = Request(
            method="POST",
            url="https://api.example.com/users",
            headers={"X-Request-ID": "123"},
            json_data={"email": "invalid"},
        )
        response = Response(
            status_code=400,
            headers={"X-Response-ID": "456"},
            data={"error": "Invalid email"},
            request=request,
        )

        error = ValidationError("Validation failed", status_code=400, response=response)

        # Context is preserved
        assert error.request == request
        assert error.response == response
        assert error.request.headers["X-Request-ID"] == "123"
        assert error.response.headers["X-Response-ID"] == "456"
