"""
Main APIClient orchestrator for REST API interactions.

Philosophy:
- Orchestrates retry, rate limiting, and error handling
- Clean public interface (GET, POST, PUT, DELETE)
- Security by default (SSL verification, input validation)
- Comprehensive logging
- Uses only requests library + standard library
"""

import logging
from typing import Any
from urllib.parse import urlparse

import requests

from .config import RateLimitConfig, RetryConfig
from .exceptions import (
    HTTPError,
    RateLimitError,
    RequestError,
    ResponseError,
)
from .models import APIRequest, APIResponse
from .rate_limit import RateLimitHandler
from .retry import RetryHandler

# Set up module logger
logger = logging.getLogger(__name__)

# Sensitive header keys that should be redacted in logs
SENSITIVE_KEYS = {
    "authorization",
    "api-key",
    "api_key",
    "apikey",
    "x-api-key",
    "x-api_key",
    "token",
    "password",
    "secret",
    "credentials",
}


def _sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize dictionary for logging by redacting sensitive values.

    Args:
        data: Dictionary that may contain sensitive data

    Returns:
        Dictionary with sensitive values redacted
    """
    if not data:
        return {}

    sanitized = {}
    for key, value in data.items():
        key_lower = str(key).lower()
        # Check if key is sensitive
        is_sensitive = any(sensitive in key_lower for sensitive in SENSITIVE_KEYS)

        if is_sensitive:
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value

    return sanitized


def _sanitize_url_for_logging(url: str) -> str:
    """Sanitize URL for logging by removing credentials.

    Args:
        url: URL that may contain credentials

    Returns:
        URL with credentials redacted
    """
    try:
        parsed = urlparse(url)
        # If URL has credentials, redact them
        if parsed.username or parsed.password:
            # Reconstruct URL without credentials
            netloc = parsed.hostname
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            netloc = f"[REDACTED]@{netloc}"

            sanitized = parsed._replace(netloc=netloc)
            return sanitized.geturl()
        return url
    except Exception:
        # If parsing fails, return as-is (better than crashing)
        return url


class APIClient:
    """HTTP client for REST APIs with retry and rate limit handling.

    This client provides a clean interface for making HTTP requests with
    automatic retry logic, rate limit handling, and comprehensive error
    handling. It enforces security by default and provides detailed logging.

    Features:
        - GET, POST, PUT, DELETE methods
        - Automatic retry with exponential backoff
        - Rate limit detection and handling
        - Custom exception hierarchy
        - Request/response dataclasses
        - SSL/TLS enforcement
        - Input validation and security

    Example:
        >>> client = APIClient(base_url="https://api.example.com")
        >>> response = client.get("/users/123")
        >>> print(response.data)
        {'id': 123, 'name': 'Alice'}

    Attributes:
        base_url: Base URL for all requests
        default_headers: Default headers applied to all requests
        default_timeout: Default timeout in seconds for requests
        retry_handler: RetryHandler instance for retry logic
        rate_limit_handler: RateLimitHandler instance for rate limiting
        session: Requests session for connection pooling
    """

    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, str] | None = None,
        default_timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        verify_ssl: bool = True,
        timeout: float | None = None,
        logger: logging.Logger | None = None,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for the API (e.g., "https://api.example.com")
            default_headers: Optional default headers for all requests
            default_timeout: Default timeout in seconds (default: 30.0)
            retry_config: Optional RetryConfig for retry behavior
            rate_limit_config: Optional RateLimitConfig for rate limiting
            verify_ssl: Whether to verify SSL certificates (default: True)
            timeout: Alias for default_timeout (for backwards compatibility)
            logger: Custom logger instance (default: module logger)

        Raises:
            ValueError: If base_url is invalid or uses non-HTTP(S) scheme
            ValueError: If timeout is invalid (must be 1.0-300.0 seconds)
        """
        # Validate and sanitize base URL
        self.base_url = self._validate_base_url(base_url)

        # Handle timeout parameter (use timeout if provided, else default_timeout)
        if timeout is not None:
            default_timeout = timeout

        # Validate timeout bounds (min 1 second, max 300 seconds = 5 minutes)
        if not 1.0 <= default_timeout <= 300.0:
            raise ValueError(
                f"timeout must be between 1.0 and 300.0 seconds, got {default_timeout}"
            )

        # Store configuration
        self.default_headers = default_headers or {}
        self.default_timeout = default_timeout
        self.timeout = default_timeout  # Alias for compatibility
        self.verify_ssl = verify_ssl

        # Set up logger
        self.logger = logger if logger is not None else logging.getLogger(__name__)

        # Initialize handlers
        # If no retry_config provided, use max_retries=0 (no retries)
        # Users must explicitly enable retries
        if retry_config is None:
            retry_config = RetryConfig(max_retries=0)
        if rate_limit_config is None:
            rate_limit_config = RateLimitConfig()

        # Store configs for access
        self.retry_config = retry_config
        self.rate_limit_config = rate_limit_config

        self.retry_handler = RetryHandler(config=retry_config)
        self.rate_limit_handler = RateLimitHandler(config=rate_limit_config)

        # Create requests session for connection pooling
        self.session = requests.Session()
        self.session.verify = verify_ssl

        # Log SSL warning if disabled
        if not verify_ssl:
            self.logger.warning(
                "SSL certificate verification is DISABLED. "
                "This is insecure and should only be used for testing."
            )

        # Sanitize URL for logging (remove credentials if present)
        safe_url = _sanitize_url_for_logging(self.base_url)

        self.logger.info(
            f"APIClient initialized: base_url={safe_url}, "
            f"timeout={self.default_timeout}s, verify_ssl={self.verify_ssl}"
        )

    def _validate_base_url(self, url: str) -> str:
        """Validate and sanitize base URL.

        Args:
            url: Base URL to validate

        Returns:
            Validated and sanitized URL

        Raises:
            ValueError: If URL is invalid or uses non-HTTP(S) scheme
        """
        if not url:
            raise ValueError("base_url cannot be empty")

        # Parse URL
        parsed = urlparse(url)

        # Validate scheme
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."
            )

        # Ensure URL ends without trailing slash for consistent joining
        url = url.rstrip("/")

        return url

    def _sanitize_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Sanitize headers to prevent header injection attacks.

        Args:
            headers: Headers dict to sanitize

        Returns:
            Sanitized headers dict

        Raises:
            ValueError: If header names or values are not strings or contain invalid characters
        """
        if not headers:
            return {}

        sanitized = {}
        for key, value in headers.items():
            # Validate header name is a string
            if not isinstance(key, str):
                raise ValueError(f"Header names must be strings, got {type(key).__name__}")

            # Validate header value is a string
            if not isinstance(value, str):
                raise ValueError(f"Header values must be strings, got {type(value).__name__}")

            # Check for newline characters (header injection attempt)
            if "\r" in key or "\n" in key:
                raise ValueError("Header name contains invalid characters (CR/LF)")

            if "\r" in value or "\n" in value:
                raise ValueError("Header value contains invalid characters (CR/LF)")

            sanitized[key] = value

        return sanitized

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path.

        Args:
            path: Path to append to base URL

        Returns:
            Full URL

        Raises:
            ValueError: If path contains path traversal patterns
        """
        if path.startswith(("http://", "https://")):
            # Absolute URL provided
            return path

        # Check for path traversal attempts
        if "../" in path or "/.." in path:
            raise ValueError(
                f"Path traversal detected in URL path: {path}. "
                "Paths containing '../' are not allowed for security reasons."
            )

        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        return self.base_url + path

    def _merge_headers(self, request_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge default headers with request-specific headers.

        Request headers override defaults.

        Args:
            request_headers: Request-specific headers

        Returns:
            Merged headers dict
        """
        merged = self.default_headers.copy()

        if request_headers:
            sanitized = self._sanitize_headers(request_headers)
            merged.update(sanitized)

        return merged

    def _make_request(self, request: APIRequest) -> APIResponse:
        """Make HTTP request and return APIResponse.

        This is the core request method that handles:
        - Building the full URL
        - Merging headers
        - Making the request via requests library
        - Parsing the response
        - Error handling

        Args:
            request: APIRequest dataclass with request details

        Returns:
            APIResponse dataclass with response details

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            ResponseError: For response parsing errors
        """
        # Build full URL
        url = self._build_url(request.url)

        # Merge headers
        headers = self._merge_headers(request.headers)

        # Use request timeout or default
        timeout = request.timeout or self.default_timeout

        # Sanitize URL and headers for logging
        safe_url = _sanitize_url_for_logging(url)
        safe_headers = _sanitize_for_logging(headers)

        # Log request at INFO level (overview)
        self.logger.info(f"{request.method} {safe_url}")

        # Log request details at DEBUG level
        self.logger.debug(
            f"{request.method} {safe_url} (timeout={timeout}s, headers={safe_headers})"
        )

        try:
            # Make request using requests library
            response = self.session.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.params,
                json=request.json,
                data=request.data,
                timeout=timeout,
                verify=self.verify_ssl,
            )

            # Calculate elapsed time
            elapsed_time = response.elapsed.total_seconds()

            # Log response at INFO level
            self.logger.info(f"Response: {response.status_code}")

            # Log response details at DEBUG level
            self.logger.debug(f"Response: {response.status_code} (elapsed={elapsed_time:.3f}s)")

            # Check for HTTP errors
            if response.status_code >= 400:
                # Parse response data for error details
                try:
                    error_data = response.json()
                except Exception:
                    # Not JSON - use text if available
                    error_data = response.text if response.text else None

                # Check for rate limiting
                if self.rate_limit_handler.is_rate_limited(response.status_code):
                    # Handle rate limit - check if we should wait and retry
                    should_retry, wait_time = self.rate_limit_handler.should_retry_rate_limit(
                        dict(response.headers)
                    )

                    if should_retry:
                        # Wait and retry internally - this doesn't count against max_retries
                        import time

                        self.logger.warning(
                            f"Rate limited. Waiting {wait_time}s before retrying "
                            f"(max: {self.rate_limit_handler.config.max_wait_time}s)"
                        )
                        time.sleep(wait_time)
                        # Retry the request by recursively calling _make_request
                        return self._make_request(request)
                    # Wait time exceeds max - raise error
                    raise RateLimitError(
                        wait_time=wait_time, retry_after=response.headers.get("Retry-After")
                    )

                # Raise HTTPError for other status codes
                # Use response text as message if available, otherwise use reason
                error_message = (
                    response.text
                    if response.text
                    else (response.reason or f"HTTP {response.status_code}")
                )

                # Log error before raising
                self.logger.error(
                    f"HTTP {response.status_code} error for {request.method} {request.url}: {error_message}"
                )

                raise HTTPError(
                    status_code=response.status_code,
                    message=error_message,
                    response_data=error_data,
                )

            # Parse response body
            # Handle 204 No Content specially
            if response.status_code == 204:
                data = None
            else:
                try:
                    # Try to parse as JSON
                    data = response.json()
                except ValueError:
                    # Not JSON - use text (or None if empty)
                    data = response.text if response.text else None

            # Create APIResponse
            return APIResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                data=data,
                text=response.text,
                elapsed_time=elapsed_time,
                url=response.url,
            )

        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request timeout after {timeout}s: {url}")
            raise RequestError(f"Request timeout after {timeout}s: {e!s}")

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error for {url}: {e!s}")
            raise RequestError(f"Connection error: {e!s}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for {url}: {e!s}")
            raise RequestError(f"Request error: {e!s}")

        except (RateLimitError, HTTPError):
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error for {url}: {e!s}")
            raise ResponseError(f"Unexpected error: {e!s}")

    def _execute_request_with_retry(self, request: APIRequest) -> APIResponse:
        """Execute request with retry and rate limit handling.

        Args:
            request: APIRequest to execute

        Returns:
            APIResponse from successful request

        Raises:
            Various exceptions from _make_request or RetryExhaustedError
        """

        def is_retryable(error: Exception) -> bool:
            """Determine if error should trigger retry."""
            # Rate limits are handled internally in _make_request
            # If RateLimitError reaches here, it means wait_time exceeded max and should not be retried
            if isinstance(error, RateLimitError):
                return False

            # Retry on configured HTTP status codes
            if isinstance(error, HTTPError):
                return error.status_code in self.retry_handler.config.retry_on_status

            # Retry on request errors (network issues)
            if isinstance(error, RequestError):
                return True

            # Don't retry on other errors
            return False

        def make_request_func():
            """Wrapper function for retry handler."""
            return self._make_request(request)

        # Execute with retry logic
        return self.retry_handler.execute_with_retry(
            func=make_request_func,
            is_retryable=is_retryable,
            operation_name=f"{request.method} {request.url}",
        )

    def execute(self, request: APIRequest) -> APIResponse:
        """Execute an APIRequest with retry and rate limit handling.

        This method allows direct execution of APIRequest dataclasses,
        providing full control over request parameters.

        Args:
            request: APIRequest dataclass with request details

        Returns:
            APIResponse with response data

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            RetryExhaustedError: If retries are exhausted

        Example:
            >>> client = APIClient(base_url="https://api.example.com")
            >>> request = APIRequest(
            ...     method="POST",
            ...     url="/users",
            ...     json={"name": "Alice"}
            ... )
            >>> response = client.execute(request)
        """
        return self._execute_request_with_retry(request)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make a GET request.

        Args:
            path: URL path or full URL
            params: Optional query parameters
            headers: Optional request headers
            timeout: Optional request timeout in seconds

        Returns:
            APIResponse with response data

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            RetryExhaustedError: If retries are exhausted

        Example:
            >>> client = APIClient(base_url="https://api.example.com")
            >>> response = client.get("/users/123")
            >>> print(response.data)
        """
        request = APIRequest(
            method="GET",
            url=path,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        return self._execute_request_with_retry(request)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make a POST request.

        Args:
            path: URL path or full URL
            json: Optional JSON body (dict)
            data: Optional form data or raw body
            params: Optional query parameters
            headers: Optional request headers
            timeout: Optional request timeout in seconds

        Returns:
            APIResponse with response data

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            RetryExhaustedError: If retries are exhausted

        Example:
            >>> client = APIClient(base_url="https://api.example.com")
            >>> response = client.post("/users", json={"name": "Alice"})
            >>> print(response.status_code)
            201
        """
        request = APIRequest(
            method="POST",
            url=path,
            json=json,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        return self._execute_request_with_retry(request)

    def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make a PUT request.

        Args:
            path: URL path or full URL
            json: Optional JSON body (dict)
            data: Optional form data or raw body
            params: Optional query parameters
            headers: Optional request headers
            timeout: Optional request timeout in seconds

        Returns:
            APIResponse with response data

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            RetryExhaustedError: If retries are exhausted

        Example:
            >>> client = APIClient(base_url="https://api.example.com")
            >>> response = client.put("/users/123", json={"name": "Alice Updated"})
            >>> print(response.data)
        """
        request = APIRequest(
            method="PUT",
            url=path,
            json=json,
            data=data,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        return self._execute_request_with_retry(request)

    def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make a DELETE request.

        Args:
            path: URL path or full URL
            params: Optional query parameters
            headers: Optional request headers
            timeout: Optional request timeout in seconds

        Returns:
            APIResponse with response data

        Raises:
            RequestError: For network/connection errors
            HTTPError: For HTTP error status codes
            RetryExhaustedError: If retries are exhausted

        Example:
            >>> client = APIClient(base_url="https://api.example.com")
            >>> response = client.delete("/users/123")
            >>> print(response.status_code)
            204
        """
        request = APIRequest(
            method="DELETE",
            url=path,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        return self._execute_request_with_retry(request)

    def close(self):
        """Close the requests session and cleanup resources."""
        self.session.close()
        self.logger.debug("APIClient session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes session."""
        self.close()


__all__ = ["APIClient"]
