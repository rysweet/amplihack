"""Data models, configuration, and exceptions for the REST API client.

This consolidated module contains all dataclasses, configuration classes,
and exception hierarchy for the REST API client.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# =============================================================================
# Request and Response Models
# =============================================================================


@dataclass
class APIRequest:
    """Represents an API request.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: Full URL for the request
        headers: HTTP headers
        params: Query parameters
        json_data: JSON body data (mutually exclusive with data)
        data: Form data or raw body (mutually exclusive with json_data)
        timeout: Request timeout in seconds
    """

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    data: dict[str, Any] | bytes | str | None = None
    timeout: float | None = None

    def __post_init__(self) -> None:
        """Validate request after initialization."""
        if self.json_data is not None and self.data is not None:
            raise ValueError("Cannot specify both json_data and data")

        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if self.method.upper() not in valid_methods:
            raise ValueError(f"Invalid HTTP method: {self.method}")

        self.method = self.method.upper()

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary for serialization."""
        result: dict[str, Any] = {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
        }

        if self.params:
            result["params"] = self.params
        if self.json_data is not None:
            result["json"] = self.json_data
        if self.data is not None:
            result["data"] = self.data
        if self.timeout is not None:
            result["timeout"] = self.timeout

        return result


@dataclass
class APIResponse:
    """Represents an API response.

    Attributes:
        status_code: HTTP status code
        headers: Response headers
        body: Raw response body as string
        json_data: Parsed JSON data (if applicable)
        request: Original request that generated this response
        elapsed_time: Time taken for the request (in seconds)
        timestamp: When the response was received
    """

    status_code: int
    headers: dict[str, str]
    body: str
    json_data: dict[str, Any] | None = None
    request: APIRequest | None = None
    elapsed_time: float | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        """Parse JSON if possible and set timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.now()

        if self.json_data is None and self.body:
            try:
                self.json_data = json.loads(self.body)
            except (json.JSONDecodeError, ValueError):
                # Body is not valid JSON, that's okay
                pass

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error (4xx status code)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error (5xx status code)."""
        return 500 <= self.status_code < 600

    def raise_for_status(self) -> None:
        """Raise an exception for non-2xx status codes."""
        if self.is_success:
            return

        message = f"Request failed with status {self.status_code}"

        if self.status_code == 401:
            raise AuthenticationError(
                message="Authentication required",
                status_code=self.status_code,
                response_body=self.body,
            )
        if self.status_code == 403:
            raise AuthenticationError(
                message="Access forbidden", status_code=self.status_code, response_body=self.body
            )
        if self.status_code == 400:
            raise ValidationError(
                message="Bad request", status_code=self.status_code, response_body=self.body
            )
        if self.status_code == 429:
            # Try to extract retry-after header
            retry_after = None
            if "Retry-After" in self.headers:
                try:
                    retry_after = int(self.headers["Retry-After"])
                except ValueError:
                    pass

            raise RateLimitError(retry_after=retry_after, response_body=self.body)
        if self.is_client_error:
            raise ClientError(
                message=message, status_code=self.status_code, response_body=self.body
            )
        if self.is_server_error:
            raise ServerError(
                message=message, status_code=self.status_code, response_body=self.body
            )
        raise APIClientError(message=message, status_code=self.status_code, response_body=self.body)


# =============================================================================
# Configuration Classes
# =============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2)
        jitter: Random jitter range in seconds (default: 0.1)
        retry_on_status_codes: Status codes that trigger retry (default: 429, 503, 504)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: int = 2
    jitter: float = 0.1
    retry_on_status_codes: set = field(default_factory=lambda: {429, 503, 504})

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be at least 1")
        if self.jitter < 0:
            raise ValueError("jitter must be non-negative")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        max_tokens: Maximum tokens in the bucket (default: 10)
        refill_rate: Tokens added per second (default: 1.0)
        initial_tokens: Initial tokens in bucket (default: max_tokens)
        respect_retry_after: Honor Retry-After headers (default: True)
    """

    max_tokens: int = 10
    refill_rate: float = 1.0
    initial_tokens: int | None = None
    respect_retry_after: bool = True

    def __post_init__(self) -> None:
        """Set defaults and validate after initialization."""
        if self.initial_tokens is None:
            self.initial_tokens = self.max_tokens

        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        if self.initial_tokens < 0:
            raise ValueError("initial_tokens must be non-negative")
        if self.initial_tokens > self.max_tokens:
            raise ValueError("initial_tokens cannot exceed max_tokens")


@dataclass
class ClientConfig:
    """Main configuration for the API client.

    Attributes:
        base_url: Base URL for all API requests
        timeout: Default timeout in seconds (default: 30.0)
        headers: Default headers for all requests
        verify_ssl: Whether to verify SSL certificates (default: True)
        retry_config: Retry behavior configuration
        rate_limit_config: Rate limiting configuration
        enable_logging: Whether to enable request logging (default: True)
        log_level: Logging level (default: "INFO")
    """

    base_url: str
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    rate_limit_config: RateLimitConfig = field(default_factory=RateLimitConfig)
    enable_logging: bool = True
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Validate and normalize configuration."""
        if not self.base_url:
            raise ValueError("base_url is required")

        # Ensure base_url doesn't end with /
        self.base_url = self.base_url.rstrip("/")

        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}")
        self.log_level = self.log_level.upper()

    def with_defaults(self, **kwargs: Any) -> "ClientConfig":
        """Create a new config with updated values.

        Args:
            **kwargs: Values to override

        Returns:
            New ClientConfig instance with updated values
        """
        # Get current values as dict
        config_dict = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "headers": self.headers.copy(),
            "verify_ssl": self.verify_ssl,
            "retry_config": self.retry_config,
            "rate_limit_config": self.rate_limit_config,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level,
        }

        # Update with provided values
        config_dict.update(kwargs)

        return ClientConfig(**config_dict)


# =============================================================================
# Exception Hierarchy
# =============================================================================


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
        if hasattr(self, "retry_after") and getattr(self, "retry_after", None) is not None:
            attrs.append(f"retry_after={getattr(self, 'retry_after', None)}")
        if hasattr(self, "status_code") and getattr(self, "status_code", None) is not None:
            attrs.append(f"status_code={getattr(self, 'status_code', None)}")

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
        return True

    def add_context(self, **kwargs: Any) -> "APIClientError":
        """Add context information to the exception.

        Args:
            **kwargs: Context key-value pairs

        Returns:
            Self for chaining
        """
        self.context.update(kwargs)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the exception
        """
        result: dict[str, Any] = {
            "error_type": self.__class__.__name__,
            "message": self.message,
        }

        if self.context:
            result["context"] = self.context

        # Add any custom attributes
        for attr_name in ["status_code", "response_body", "retry_after", "timeout"]:
            if hasattr(self, attr_name):
                attr_value = getattr(self, attr_name)
                if attr_value is not None:
                    result[attr_name] = attr_value

        return result

    def should_retry(self) -> bool:
        """Whether this error should trigger a retry.

        Returns:
            True if the error is retryable, False otherwise
        """
        # Default to not retrying
        return False

    def get_log_context(self) -> dict[str, Any]:
        """Get context for logging this exception.

        Returns:
            Dictionary with logging context
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            **self.context,
        }

    def get_root_cause(self) -> str:
        """Get root cause of the error.

        Returns:
            String describing the root cause
        """
        if hasattr(self, "__cause__") and self.__cause__:
            return str(self.__cause__)
        return self.message


class NetworkError(APIClientError):
    """Base exception for network-related errors."""

    def should_retry(self) -> bool:
        """Network errors are generally retryable."""
        return True


class HTTPResponseError(APIClientError):
    """Base exception for HTTP response errors.

    Attributes:
        status_code: HTTP status code
        response_body: Response body content
    """

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ) -> None:
        """Initialize HTTP response error."""
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TimeoutError(NetworkError):
    """Raised when a request times out.

    Attributes:
        timeout: The timeout value that was exceeded
    """

    def __init__(self, message: str = "Request timed out", timeout: float | None = None) -> None:
        """Initialize timeout error."""
        super().__init__(message)
        self.timeout = timeout

    def get_root_cause(self) -> str:
        """Get detailed timeout information."""
        if self.timeout is not None:
            return f"Request exceeded timeout of {self.timeout} seconds"
        return "Request timed out"


class RateLimitError(HTTPResponseError):
    """Raised when rate limit is exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying (if provided)
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        response_body: str | None = None,
    ) -> None:
        """Initialize rate limit error."""
        super().__init__(message, status_code=429, response_body=response_body)
        self.retry_after = retry_after

    def should_retry(self) -> bool:
        """Rate limit errors are retryable after waiting."""
        return True

    def get_root_cause(self) -> str:
        """Get detailed rate limit information."""
        if self.retry_after is not None:
            return f"Rate limit exceeded. Retry after {self.retry_after} seconds"
        return "Rate limit exceeded"


class AuthenticationError(HTTPResponseError):
    """Raised when authentication fails.

    This includes 401 Unauthorized and 403 Forbidden responses.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        status_code: int = 401,
        response_body: str | None = None,
    ) -> None:
        """Initialize authentication error."""
        super().__init__(message, status_code=status_code, response_body=response_body)

    def should_retry(self) -> bool:
        """Authentication errors are generally not retryable."""
        return False


class ValidationError(HTTPResponseError):
    """Raised when request validation fails.

    Attributes:
        validation_errors: Detailed validation errors (if available)
    """

    def __init__(
        self,
        message: str = "Validation failed",
        status_code: int = 400,
        response_body: str | None = None,
        validation_errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error."""
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.validation_errors = validation_errors or {}

    def should_retry(self) -> bool:
        """Validation errors are not retryable."""
        return False

    def get_root_cause(self) -> str:
        """Get detailed validation error information."""
        if self.validation_errors:
            return f"Validation failed: {self.validation_errors}"
        return self.message


class ServerError(HTTPResponseError):
    """Raised for 5xx server errors."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        response_body: str | None = None,
    ) -> None:
        """Initialize server error."""
        super().__init__(message, status_code=status_code, response_body=response_body)

    def should_retry(self) -> bool:
        """Server errors are generally retryable."""
        # 501 Not Implemented and 505 HTTP Version Not Supported are not retryable
        if self.status_code in [501, 505]:
            return False
        return True


class ClientError(HTTPResponseError):
    """Raised for 4xx client errors (excluding specific ones above)."""

    def __init__(
        self,
        message: str = "Client error",
        status_code: int = 400,
        response_body: str | None = None,
    ) -> None:
        """Initialize client error."""
        super().__init__(message, status_code=status_code, response_body=response_body)

    def should_retry(self) -> bool:
        """Most client errors are not retryable."""
        # 408 Request Timeout and 409 Conflict might be retryable
        if self.status_code in [408, 409]:
            return True
        return False
