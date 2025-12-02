"""Tests for exception hierarchy.

TDD tests - these will FAIL until exceptions.py is implemented.

Testing:
- Exception hierarchy and inheritance
- Exception attributes and messages
- Exception creation from responses
- Proper categorization of errors
"""


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_api_client_error_is_base_exception(self):
        """APIClientError is the base exception for all API client errors."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Something went wrong")
        assert isinstance(error, Exception)
        assert str(error) == "Something went wrong"

    def test_connection_error_inherits_from_base(self):
        """ConnectionError inherits from APIClientError."""
        from api_client.exceptions import APIClientError, ConnectionError

        error = ConnectionError("Failed to connect")
        assert isinstance(error, APIClientError)
        assert isinstance(error, Exception)

    def test_timeout_error_inherits_from_base(self):
        """TimeoutError inherits from APIClientError."""
        from api_client.exceptions import APIClientError, TimeoutError

        error = TimeoutError("Request timed out")
        assert isinstance(error, APIClientError)

    def test_rate_limit_error_inherits_from_base(self):
        """RateLimitError inherits from APIClientError."""
        from api_client.exceptions import APIClientError, RateLimitError

        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, APIClientError)

    def test_server_error_inherits_from_base(self):
        """ServerError inherits from APIClientError."""
        from api_client.exceptions import APIClientError, ServerError

        error = ServerError("Internal server error")
        assert isinstance(error, APIClientError)

    def test_client_error_inherits_from_base(self):
        """ClientError inherits from APIClientError."""
        from api_client.exceptions import APIClientError, ClientError

        error = ClientError("Bad request")
        assert isinstance(error, APIClientError)


class TestAPIClientError:
    """Tests for base APIClientError."""

    def test_create_with_message_only(self):
        """APIClientError can be created with just a message."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"

    def test_create_with_status_code(self):
        """APIClientError can include status code."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Server error", status_code=500)

        assert error.status_code == 500
        assert error.message == "Server error"

    def test_create_with_response_body(self):
        """APIClientError can include response body."""
        from api_client.exceptions import APIClientError

        error = APIClientError(
            "Error occurred",
            status_code=400,
            response_body={"error": "validation_failed", "details": ["field required"]},
        )

        assert error.response_body == {"error": "validation_failed", "details": ["field required"]}

    def test_create_with_request_id(self):
        """APIClientError can include request ID for debugging."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Error", request_id="req-abc-123")

        assert error.request_id == "req-abc-123"

    def test_default_attributes_are_none(self):
        """APIClientError defaults optional attributes to None."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Error")

        assert error.status_code is None
        assert error.response_body is None
        assert error.request_id is None


class TestConnectionError:
    """Tests for ConnectionError exception."""

    def test_create_connection_error(self):
        """ConnectionError can be created with connection details."""
        from api_client.exceptions import ConnectionError

        error = ConnectionError("Failed to establish connection to api.example.com")

        assert "Failed to establish connection" in str(error)

    def test_connection_error_with_url(self):
        """ConnectionError includes target URL."""
        from api_client.exceptions import ConnectionError

        error = ConnectionError("Connection failed", url="https://api.example.com/users")

        assert error.url == "https://api.example.com/users"

    def test_connection_error_with_original_exception(self):
        """ConnectionError can wrap original exception."""
        from api_client.exceptions import ConnectionError

        original = OSError("Network unreachable")
        error = ConnectionError("Connection failed", original_error=original)

        assert error.original_error == original


class TestTimeoutError:
    """Tests for TimeoutError exception."""

    def test_create_timeout_error(self):
        """TimeoutError can be created with timeout details."""
        from api_client.exceptions import TimeoutError

        error = TimeoutError("Request timed out after 30 seconds")

        assert "timed out" in str(error).lower()

    def test_timeout_error_with_timeout_value(self):
        """TimeoutError includes timeout value."""
        from api_client.exceptions import TimeoutError

        error = TimeoutError("Request timed out", timeout_seconds=30)

        assert error.timeout_seconds == 30

    def test_timeout_error_with_url(self):
        """TimeoutError includes target URL."""
        from api_client.exceptions import TimeoutError

        error = TimeoutError("Timed out", url="https://api.example.com/slow")

        assert error.url == "https://api.example.com/slow"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_create_rate_limit_error(self):
        """RateLimitError can be created with rate limit details."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limit exceeded")

        assert "rate limit" in str(error).lower()

    def test_rate_limit_error_status_is_429(self):
        """RateLimitError always has status_code 429."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited")

        assert error.status_code == 429

    def test_rate_limit_error_with_retry_after(self):
        """RateLimitError includes retry_after value."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited", retry_after=60)

        assert error.retry_after == 60

    def test_rate_limit_error_retry_after_default(self):
        """RateLimitError defaults retry_after to None."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited")

        assert error.retry_after is None

    def test_rate_limit_error_with_limit_info(self):
        """RateLimitError can include rate limit details."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError(
            "Rate limited",
            retry_after=60,
            limit=100,
            remaining=0,
            reset_at="2024-01-01T12:00:00Z",
        )

        assert error.limit == 100
        assert error.remaining == 0
        assert error.reset_at == "2024-01-01T12:00:00Z"


class TestServerError:
    """Tests for ServerError exception (5xx errors)."""

    def test_create_server_error(self):
        """ServerError can be created for 5xx responses."""
        from api_client.exceptions import ServerError

        error = ServerError("Internal server error", status_code=500)

        assert error.status_code == 500

    def test_server_error_common_codes(self):
        """ServerError works with common 5xx status codes."""
        from api_client.exceptions import ServerError

        codes = [500, 501, 502, 503, 504]
        for code in codes:
            error = ServerError(f"Server error {code}", status_code=code)
            assert error.status_code == code

    def test_server_error_is_retryable(self):
        """ServerError indicates if the error is retryable."""
        from api_client.exceptions import ServerError

        error_500 = ServerError("Internal error", status_code=500)
        error_503 = ServerError("Service unavailable", status_code=503)

        # 500, 502, 503, 504 are typically retryable
        assert error_500.is_retryable is True
        assert error_503.is_retryable is True

    def test_server_error_not_implemented_not_retryable(self):
        """501 Not Implemented is not retryable."""
        from api_client.exceptions import ServerError

        error = ServerError("Not implemented", status_code=501)

        assert error.is_retryable is False


class TestClientError:
    """Tests for ClientError exception (4xx errors)."""

    def test_create_client_error(self):
        """ClientError can be created for 4xx responses."""
        from api_client.exceptions import ClientError

        error = ClientError("Bad request", status_code=400)

        assert error.status_code == 400

    def test_client_error_common_codes(self):
        """ClientError works with common 4xx status codes."""
        from api_client.exceptions import ClientError

        codes = [400, 401, 403, 404, 422]
        for code in codes:
            error = ClientError(f"Client error {code}", status_code=code)
            assert error.status_code == code

    def test_client_error_is_not_retryable(self):
        """ClientError is generally not retryable."""
        from api_client.exceptions import ClientError

        error = ClientError("Bad request", status_code=400)

        assert error.is_retryable is False

    def test_client_error_with_validation_details(self):
        """ClientError can include validation error details."""
        from api_client.exceptions import ClientError

        error = ClientError(
            "Validation failed",
            status_code=422,
            response_body={
                "errors": [
                    {"field": "email", "message": "Invalid email format"},
                    {"field": "age", "message": "Must be positive"},
                ]
            },
        )

        assert error.response_body["errors"][0]["field"] == "email"


class TestExceptionFactory:
    """Tests for creating exceptions from HTTP responses."""

    def test_create_from_response_429(self):
        """Factory creates RateLimitError for 429 response."""
        from api_client.exceptions import RateLimitError, create_exception_from_response
        from api_client.models import Response

        response = Response(
            status_code=429,
            body={"error": "Too many requests"},
            headers={"Retry-After": "60"},
        )

        error = create_exception_from_response(response)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_create_from_response_5xx(self):
        """Factory creates ServerError for 5xx response."""
        from api_client.exceptions import ServerError, create_exception_from_response
        from api_client.models import Response

        response = Response(status_code=500, body={"error": "Internal error"})

        error = create_exception_from_response(response)

        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_create_from_response_4xx(self):
        """Factory creates ClientError for 4xx response."""
        from api_client.exceptions import ClientError, create_exception_from_response
        from api_client.models import Response

        response = Response(status_code=404, body={"error": "Not found"})

        error = create_exception_from_response(response)

        assert isinstance(error, ClientError)
        assert error.status_code == 404

    def test_create_from_response_preserves_body(self):
        """Factory preserves response body in exception."""
        from api_client.exceptions import create_exception_from_response
        from api_client.models import Response

        response = Response(
            status_code=400,
            body={"error": "validation_failed", "details": ["missing field"]},
        )

        error = create_exception_from_response(response)

        assert error.response_body == response.body

    def test_create_from_response_preserves_request_id(self):
        """Factory preserves request ID in exception."""
        from api_client.exceptions import create_exception_from_response
        from api_client.models import Response

        response = Response(
            status_code=500,
            body={},
            request_id="req-xyz-789",
        )

        error = create_exception_from_response(response)

        assert error.request_id == "req-xyz-789"


class TestExceptionMessages:
    """Tests for exception message formatting."""

    def test_api_client_error_str(self):
        """APIClientError has informative string representation."""
        from api_client.exceptions import APIClientError

        error = APIClientError("Request failed", status_code=500, request_id="req-123")

        error_str = str(error)
        assert "Request failed" in error_str

    def test_rate_limit_error_includes_retry_info(self):
        """RateLimitError string includes retry information."""
        from api_client.exceptions import RateLimitError

        error = RateLimitError("Rate limited", retry_after=60)

        error_str = str(error)
        assert "60" in error_str or "retry" in error_str.lower()

    def test_timeout_error_includes_timeout_value(self):
        """TimeoutError string includes timeout value."""
        from api_client.exceptions import TimeoutError

        error = TimeoutError("Timed out", timeout_seconds=30)

        error_str = str(error)
        assert "30" in error_str or "timeout" in error_str.lower()

    def test_exception_repr(self):
        """Exceptions have useful repr for debugging."""
        from api_client.exceptions import ServerError

        error = ServerError("Server error", status_code=500, request_id="req-123")

        repr_str = repr(error)
        assert "ServerError" in repr_str
        assert "500" in repr_str
