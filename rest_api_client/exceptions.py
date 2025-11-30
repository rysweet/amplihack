"""Custom exception hierarchy for the REST API client.

This module defines all custom exceptions used by the API client,
providing detailed error information for different failure scenarios.
"""

from typing import Any


class APIClientError(Exception):
    """Base exception for all API client errors.

    Attributes:
        message: Human-readable error message
        context: Additional context information
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        """Initialize the API exception.

        Args:
            message: Error message
            **kwargs: Additional attributes to set
        """
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = {}

        # Set any additional attributes passed in
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation of the exception."""
        # Get all custom attributes
        attrs = []
        for attr_name in dir(self):
            if not attr_name.startswith("_") and attr_name not in [
                "message",
                "context",
                "add_context",
                "to_dict",
                "should_retry",
                "get_log_context",
                "get_root_cause",
            ]:
                attr_value = getattr(self, attr_name)
                if not callable(attr_value) and attr_value is not None:
                    if attr_name not in [
                        "status_code",
                        "response",
                        "response_body",
                        "request_id",
                        "retry_after",
                        "timeout",
                        "validation_errors",
                    ]:
                        attrs.append(f"{attr_name}={attr_value!r}")

        # Special handling for known attributes
        if hasattr(self, "retry_after") and self.retry_after is not None:
            attrs.append(f"retry_after={self.retry_after}")
        if hasattr(self, "status_code") and self.status_code is not None:
            attrs.append(f"status_code={self.status_code}")

        if attrs:
            return f"{self.__class__.__name__}('{self.message}', {', '.join(attrs)})"
        return f"{self.__class__.__name__}('{self.message}')"

    def __eq__(self, other: object) -> bool:
        """Check equality with another exception.

        Args:
            other: Other object to compare with

        Returns:
            True if equal, False otherwise
        """
        if not isinstance(other, self.__class__):
            return False
        # Compare message and all attributes
        if self.message != other.message:
            return False
        # Compare all other attributes that were set
        for attr_name in dir(self):
            if not attr_name.startswith("_") and attr_name not in [
                "message",
                "context",
                "add_context",
                "to_dict",
            ]:
                attr_value = getattr(self, attr_name)
                if not callable(attr_value):
                    if hasattr(other, attr_name):
                        if getattr(self, attr_name) != getattr(other, attr_name):
                            return False
                    else:
                        return False
        return True

    def add_context(self, key: str, value: Any) -> None:
        """Add context information to the exception.

        Args:
            key: Context key
            value: Context value
        """
        self.context[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary representation.

        Returns:
            Dictionary with exception details
        """
        result = {
            "message": self.message,
            "type": self.__class__.__name__,
        }

        # Add all attributes that were set via kwargs
        for attr_name in dir(self):
            if not attr_name.startswith("_") and attr_name not in [
                "message",
                "context",
                "add_context",
                "to_dict",
            ]:
                attr_value = getattr(self, attr_name)
                # Skip methods
                if not callable(attr_value):
                    result[attr_name] = attr_value

        # Add context if it exists
        if self.context:
            result["context"] = self.context

        return result

    def should_retry(self) -> bool:
        """Check if this exception indicates a retryable error.

        Returns:
            True if the error is retryable, False otherwise
        """
        # By default, not retryable
        return False

    def get_log_context(self) -> dict[str, Any]:
        """Get context for logging.

        Returns:
            Dictionary with logging context
        """
        return self.to_dict()

    def get_root_cause(self) -> Exception:
        """Get the root cause of the exception chain.

        Returns:
            The deepest cause in the exception chain
        """
        if hasattr(self, "cause") and self.cause is not None:
            if hasattr(self.cause, "get_root_cause"):
                return self.cause.get_root_cause()
            return self.cause
        return self


class HTTPResponseError(APIClientError):
    """Raised for HTTP response errors with status code and optional response.

    Attributes:
        status_code: HTTP status code
        response: Optional response object
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: Any | None = None,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize HTTP response error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: Response object (if available)
            request_id: Request ID for tracking
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response = response
        self.response_body = getattr(response, "text", None) if response else None
        self.request_id = request_id

    def should_retry(self) -> bool:
        """Check if this HTTP error is retryable.

        Returns:
            True for 5xx errors (server errors), False otherwise
        """
        if self.status_code and self.status_code >= 500:
            return True
        return False


class NetworkError(APIClientError):
    """Raised when unable to connect to the API server.

    Attributes:
        cause: The underlying cause of the network error
    """

    def __init__(self, message: str, cause: Exception | None = None, **kwargs: Any) -> None:
        """Initialize network error.

        Args:
            message: Error message
            cause: The underlying exception that caused this error
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.cause = cause

    def should_retry(self) -> bool:
        """Network errors are typically retryable.

        Returns:
            True
        """
        return True


class TimeoutError(APIClientError):
    """Raised when a request times out.

    Attributes:
        timeout: The timeout value that was exceeded (optional)
    """

    def __init__(self, message: str, timeout: float | None = None, **kwargs: Any) -> None:
        """Initialize timeout error.

        Args:
            message: Error message
            timeout: The timeout value that was exceeded
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.timeout = timeout

    def should_retry(self) -> bool:
        """Timeout errors are typically retryable.

        Returns:
            True
        """
        return True


class RateLimitError(APIClientError):
    """Raised when rate limit is exceeded (HTTP 429).

    Attributes:
        retry_after: Seconds to wait before retrying (if provided by server)
    """

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None, **kwargs: Any
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.status_code = 429

    def should_retry(self) -> bool:
        """Rate limit errors are always retryable.

        Returns:
            True
        """
        return True


class AuthenticationError(HTTPResponseError):
    """Raised for authentication failures (HTTP 401/403)."""

    def __init__(self, message: str, status_code: int | None = None, **kwargs: Any) -> None:
        """Initialize authentication error.

        Args:
            message: Error message
            status_code: HTTP status code (401 or 403)
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, status_code=status_code or 401, **kwargs)


class ValidationError(APIClientError):
    """Raised for request validation errors (HTTP 400).

    Attributes:
        validation_errors: Dict of field names to error messages
        field: The specific field that failed validation (optional)
        value: The value that failed validation (optional)
    """

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        value: Any | None = None,
        validation_errors: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: The specific field that failed validation
            value: The value that failed validation
            validation_errors: Field-specific validation errors
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value
        self.validation_errors = validation_errors or {}
        self.status_code = 400


class ServerError(APIClientError):
    """Raised for server-side errors (HTTP 5xx)."""

    def __init__(self, message: str, status_code: int | None = None, **kwargs: Any) -> None:
        """Initialize server error.

        Args:
            message: Error message
            status_code: HTTP status code (5xx)
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code or 500


class ClientError(APIClientError):
    """Raised for client-side errors (HTTP 4xx, excluding specific cases)."""

    def __init__(self, message: str, status_code: int | None = None, **kwargs: Any) -> None:
        """Initialize client error.

        Args:
            message: Error message
            status_code: HTTP status code (4xx)
            **kwargs: Additional arguments for parent class
        """
        super().__init__(message, **kwargs)
        self.status_code = status_code or 400
