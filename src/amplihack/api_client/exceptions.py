"""Exception hierarchy for the API client.

All exceptions carry context about the failed request for debugging.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .models import Request, Response


class APIClientError(Exception):
    """Base exception for all API client errors."""

    def __init__(
        self,
        message: str,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
        status_code: int | None = None,
    ):
        """Initialize exception with message and optional context.

        Args:
            message: Error message describing what went wrong
            request: The Request object that triggered this error
            response: The Response object if available
            status_code: HTTP status code if applicable
        """
        self.message = message
        self.response = response
        self.status_code = status_code

        # Extract request from response if not provided separately
        if request is None and response is not None:
            self.request = getattr(response, "request", None)
        else:
            self.request = request

        super().__init__(message)


class NetworkError(APIClientError):
    """Network-level errors (connection failures, timeouts, DNS errors)."""

    def __str__(self) -> str:
        """Format error message."""
        return f"Network error: {self.message}"


class TimeoutError(NetworkError):
    """Request timeout error."""


class HTTPError(APIClientError):
    """HTTP error response (4xx, 5xx status codes)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
    ):
        """Initialize HTTP error.

        Args:
            message: Error message
            status_code: HTTP status code (required unless response provided)
            response_body: Raw response body for debugging
            request: The request that triggered this error
            response: The Response object if available
        """
        # Extract status_code from response if not provided
        if status_code is None and response is not None:
            status_code = getattr(response, "status_code", None)

        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message, request, response, status_code)

    def __str__(self) -> str:
        """Format error message."""
        return f"HTTP {self.status_code}: {self.message}"


class ClientError(HTTPError):
    """Client error (4xx status codes except 401, 403, 429)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
    ):
        """Initialize client error."""
        super().__init__(message, status_code, response_body, request, response)


class ServerError(HTTPError):
    """Server error (5xx status codes)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
    ):
        """Initialize server error."""
        super().__init__(message, status_code, response_body, request, response)

    def __str__(self) -> str:
        """Format error message."""
        return f"Server error: {self.message}"


class ValidationError(ClientError):
    """Request validation error (400)."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: list | None = None,
        status_code: int = 400,
        request: Optional["Request"] = None,
        response_body: str | None = None,
        response: Optional["Response"] = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            field: The field that failed validation
            details: List of ErrorDetail objects with validation details
            status_code: HTTP status code (defaults to 400)
            request: The request that triggered this error
            response_body: Raw response body
            response: The Response object if available
        """
        self.field = field
        self.details = details or []
        super().__init__(message, status_code, response_body, request, response)


class AuthenticationError(ClientError):
    """Authentication/authorization error (401, 403)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
    ):
        """Initialize authentication error."""
        super().__init__(message, status_code, response_body, request, response)

    def __str__(self) -> str:
        """Format error message."""
        return f"Authentication failed: {self.message}"


class NotFoundError(ClientError):
    """Resource not found (404)."""

    def __str__(self) -> str:
        """Format error message."""
        return f"Not found: {self.message}"


class RateLimitError(ClientError):
    """Rate limit exceeded (HTTP 429 response)."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        limit: int | None = None,
        remaining: int | None = None,
        status_code: int = 429,
        request: Optional["Request"] = None,
        response_body: str | None = None,
        response: Optional["Response"] = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry (from Retry-After header)
            limit: Rate limit (requests per window)
            remaining: Requests remaining in window
            status_code: HTTP status code (defaults to 429)
            request: The request that triggered this error
            response_body: Raw response body
            response: The Response object if available
        """
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        super().__init__(message, status_code, response_body, request, response)


class ServiceUnavailableError(ServerError):
    """Service unavailable (503)."""

    def __str__(self) -> str:
        """Format error message."""
        return f"Service unavailable: {self.message}"


class ConfigurationError(APIClientError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        request: Optional["Request"] = None,
        response: Optional["Response"] = None,
    ):
        """Initialize configuration error.

        Args:
            message: Error message
            field: The configuration field that has an error
            request: The request object if available
            response: The response object if available
        """
        self.field = field
        super().__init__(message, request, response)

    def __str__(self) -> str:
        """Format error message."""
        if self.field:
            return f"Configuration error in {self.field}: {self.message}"
        return f"Configuration error: {self.message}"


# Map status codes to exception classes for easy dispatching
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthenticationError,
    404: NotFoundError,
    429: RateLimitError,
    503: ServiceUnavailableError,
    # Other 4xx mapped to ClientError
    **{code: ClientError for code in range(400, 500) if code not in [400, 401, 403, 404, 429]},
    # Other 5xx mapped to ServerError
    **{code: ServerError for code in range(500, 600) if code not in [503]},
}


def exception_from_status_code(
    status_code: int,
    message: str,
    response_body: str | None = None,
    request: Optional["Request"] = None,
    retry_after: int | None = None,
) -> HTTPError:
    """Create appropriate exception based on HTTP status code.

    Args:
        status_code: HTTP status code
        message: Error message
        response_body: Raw response body
        request: The request that triggered this error
        retry_after: For 429 errors, seconds to wait

    Returns:
        Appropriate HTTPError subclass instance
    """
    exception_cls = STATUS_CODE_EXCEPTIONS.get(status_code, HTTPError)

    if status_code == 429 and retry_after is not None:
        return RateLimitError(
            message,
            retry_after=retry_after,
            status_code=status_code,
            request=request,
            response_body=response_body,
        )

    return exception_cls(
        message, status_code=status_code, response_body=response_body, request=request
    )


def parse_error_response(
    response_text: str | None, content_type: str | None = None
) -> dict[str, Any]:
    """Parse error response body.

    Args:
        response_text: Raw response text
        content_type: Response content type

    Returns:
        Dictionary with parsed error information
    """
    if not response_text:
        return {"error": "Empty response"}

    # Try to parse as JSON
    if content_type and "json" in content_type.lower():
        try:
            import json

            return json.loads(response_text)
        except (json.JSONDecodeError, ValueError):
            return {"error": response_text}

    return {"error": response_text}


def error_from_response(response: "Response") -> APIClientError:
    """Create appropriate exception from response.

    Args:
        response: Response object

    Returns:
        Appropriate exception instance
    """
    # Parse error message
    error_data = parse_error_response(
        getattr(response, "raw_text", None) or str(response.data),
        response.headers.get("Content-Type"),
    )

    # Extract message
    if isinstance(error_data, dict):
        message = (
            error_data.get("error")
            or error_data.get("message")
            or error_data.get("detail")
            or f"HTTP {response.status_code}"
        )
    else:
        message = str(error_data)

    # For 429 errors, parse rate limit headers
    if response.status_code == 429:
        retry_after = None
        limit = None
        remaining = None

        # Parse Retry-After
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header:
            try:
                retry_after = int(retry_after_header)
            except ValueError:
                pass

        # Parse rate limit headers
        limit_header = response.headers.get("X-RateLimit-Limit")
        if limit_header:
            try:
                limit = int(limit_header)
            except ValueError:
                pass

        remaining_header = response.headers.get("X-RateLimit-Remaining")
        if remaining_header:
            try:
                remaining = int(remaining_header)
            except ValueError:
                pass

        return RateLimitError(
            str(message),
            retry_after=retry_after,
            limit=limit,
            remaining=remaining,
            status_code=429,
            request=response.request,
            response_body=getattr(response, "raw_text", None),
        )

    # Create appropriate exception for other status codes
    return exception_from_status_code(
        response.status_code,
        str(message),
        response_body=getattr(response, "raw_text", None),
        request=response.request,
    )
