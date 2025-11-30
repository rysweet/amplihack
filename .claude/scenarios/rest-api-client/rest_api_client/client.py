"""Main APIClient class for REST API interactions.

This module provides the main client class that orchestrates all
components to provide a simple, robust API for HTTP requests.
"""

import logging
import ssl
from typing import Any
from urllib.parse import urljoin, urlparse

from .exceptions import (
    exception_from_status_code,
)
from .models import Request, Response
from .rate_limiter import RateLimitConfig, RateLimiter
from .retry import RetryConfig, RetryManager
from .security import SSRFProtector
from .transport import HTTPTransport


class APIClient:
    """Main client for making REST API requests.

    Provides a simple interface for HTTP requests with built-in
    retry logic, rate limiting, SSRF protection, and comprehensive
    error handling.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        connection_timeout: float = 10.0,
        verify_ssl: bool = True,
        ssl_context: ssl.SSLContext | None = None,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        retry_on_status: list[int] | None = None,
        rate_limit_calls: int | None = None,
        rate_limit_period: int | None = None,
        logger: logging.Logger | None = None,
        enforce_https: bool = False,
        max_response_size: int = 100 * 1024 * 1024,  # 100MB default
        enable_ssrf_protection: bool = True,
        allowed_hosts: list[str] | None = None,
        additional_blocked_hosts: list[str] | None = None,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for all requests
            headers: Default headers for all requests
            timeout: Read timeout in seconds
            connection_timeout: Connection timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            ssl_context: Custom SSL context
            max_retries: Maximum retry attempts
            retry_backoff_factor: Backoff multiplier for retries
            retry_on_status: Status codes to retry
            rate_limit_calls: Number of calls allowed per period
            rate_limit_period: Period in seconds for rate limiting
            logger: Logger instance
            enforce_https: Whether to enforce HTTPS URLs
            max_response_size: Maximum response size in bytes
            enable_ssrf_protection: Whether to enable SSRF protection
            allowed_hosts: List of explicitly allowed hosts (bypasses SSRF blocks)
            additional_blocked_hosts: Additional hosts to block

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate base URL
        self._validate_base_url(base_url, enforce_https)
        self.base_url = base_url.rstrip("/")

        # Headers
        self.headers = headers or {}
        self._validate_headers(self.headers)

        # Timeout settings
        self.timeout = timeout
        self.connection_timeout = connection_timeout

        # SSL settings
        self.verify_ssl = verify_ssl
        self.ssl_context = ssl_context

        # Retry configuration
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_on_status = set(retry_on_status or [429, 500, 502, 503, 504])

        # Rate limiting
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period

        # Logger
        self.logger = logger or logging.getLogger(__name__)

        # Security settings
        self.max_response_size = max_response_size
        self.enable_ssrf_protection = enable_ssrf_protection

        # Initialize SSRF protector
        if self.enable_ssrf_protection:
            self.ssrf_protector = SSRFProtector(
                allowed_hosts=allowed_hosts, additional_blocked_hosts=additional_blocked_hosts
            )
        else:
            self.ssrf_protector = None

        # Initialize components
        self._init_components()

    def _validate_base_url(self, base_url: str, enforce_https: bool):
        """Validate base URL format.

        Args:
            base_url: URL to validate
            enforce_https: Whether to enforce HTTPS

        Raises:
            ValueError: If URL is invalid
        """
        if not base_url:
            raise ValueError("Base URL cannot be empty")

        parsed = urlparse(base_url)

        if not parsed.scheme:
            raise ValueError(f"Invalid base URL: {base_url} (missing scheme)")

        if not parsed.netloc:
            raise ValueError(f"Invalid base URL: {base_url} (missing host)")

        if enforce_https and parsed.scheme != "https":
            raise ValueError("Base URL must use https:// scheme when enforce_https=True")

    def _validate_headers(self, headers: dict[str, str]):
        """Validate headers to prevent injection attacks.

        Args:
            headers: Headers to validate

        Raises:
            ValueError: If headers are invalid
        """
        if len(headers) > 100:
            raise ValueError(f"Too many headers: {len(headers)} (max 100)")

        for name, value in headers.items():
            # Check header name
            if "\n" in name or "\r" in name:
                raise ValueError(f"Invalid header name: {name} (contains newline)")

            # Check header value
            value_str = str(value)
            if "\n" in value_str or "\r" in value_str:
                raise ValueError(f"Invalid header value for {name} (contains newline)")

            # Check header size
            if len(value_str) > 8192:
                raise ValueError(
                    f"Header value too large for {name}: {len(value_str)} bytes (max 8KB)"
                )

    def _init_components(self):
        """Initialize internal components."""
        # Transport layer
        self.transport = HTTPTransport(
            timeout=self.timeout,
            verify_ssl=self.verify_ssl,
            ssl_context=self.ssl_context,
            logger=self.logger,
            max_response_size=self.max_response_size,
        )

        # Retry manager
        retry_config = RetryConfig(
            max_attempts=self.max_retries,
            backoff_factor=self.retry_backoff_factor,
            retry_on_status=self.retry_on_status,
        )
        self.retry_manager = RetryManager(retry_config, self.logger)

        # Rate limiter (optional)
        if self.rate_limit_calls:
            rate_config = RateLimitConfig(
                requests_per_second=self.rate_limit_calls / (self.rate_limit_period or 1),
                burst_size=self.rate_limit_calls,
            )
            self.rate_limiter = RateLimiter(rate_config)
        else:
            self.rate_limiter = None

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> Response:
        """Make GET request.

        Args:
            path: Request path (appended to base_url)
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional request options

        Returns:
            Response object

        Raises:
            APIClientError: For various error conditions
        """
        return self._request("GET", path, params=params, headers=headers, **kwargs)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: str | bytes | dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> Response:
        """Make POST request.

        Args:
            path: Request path
            json: JSON data to send
            data: Form data or raw data to send
            files: Files to upload
            headers: Additional headers
            **kwargs: Additional request options

        Returns:
            Response object
        """
        return self._request(
            "POST", path, json=json, data=data, files=files, headers=headers, **kwargs
        )

    def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: str | bytes | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> Response:
        """Make PUT request.

        Args:
            path: Request path
            json: JSON data to send
            data: Raw data to send
            headers: Additional headers
            **kwargs: Additional request options

        Returns:
            Response object
        """
        return self._request("PUT", path, json=json, data=data, headers=headers, **kwargs)

    def delete(self, path: str, headers: dict[str, str] | None = None, **kwargs) -> Response:
        """Make DELETE request.

        Args:
            path: Request path
            headers: Additional headers
            **kwargs: Additional request options

        Returns:
            Response object
        """
        return self._request("DELETE", path, headers=headers, **kwargs)

    def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: str | bytes | dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> Response:
        """Make PATCH request.

        Args:
            path: Request path
            json: JSON data to send
            data: Raw data to send
            headers: Additional headers
            **kwargs: Additional request options

        Returns:
            Response object
        """
        return self._request("PATCH", path, json=json, data=data, headers=headers, **kwargs)

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: str | bytes | dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs,
    ) -> Response:
        """Internal method to make HTTP request.

        Args:
            method: HTTP method
            path: Request path
            params: Query parameters
            json: JSON data
            data: Raw data
            files: Files to upload
            headers: Additional headers
            timeout: Custom timeout
            **kwargs: Additional options

        Returns:
            Response object

        Raises:
            Various exceptions for different error conditions
        """
        # Build full URL
        url = urljoin(self.base_url + "/", path.lstrip("/"))

        # SSRF protection
        if self.ssrf_protector:
            self.ssrf_protector.validate_url(url)

        # Merge headers
        merged_headers = {**self.headers}
        if headers:
            merged_headers.update(headers)
            self._validate_headers(merged_headers)

        # Add User-Agent if not present
        if "User-Agent" not in merged_headers:
            merged_headers["User-Agent"] = "REST-API-Client/1.0.0"

        # Create request object
        request = Request(
            method=method,
            url=url,
            headers=merged_headers,
            params=params,
            json=json,
            data=data,
            files=files,
            timeout=timeout or self.timeout,
        )

        # Log request
        self._log_request(request)

        # Apply rate limiting
        if self.rate_limiter:
            self.rate_limiter.acquire()

        # Execute with retry logic
        def execute():
            return self._execute_request(request)

        response = self.retry_manager.execute_with_retry(execute)

        # Log response
        self._log_response(response)

        # Check for errors
        if response.is_error():
            self._handle_error_response(response)

        return response

    def _execute_request(self, request: Request) -> Response:
        """Execute single request without retry.

        Args:
            request: Request object

        Returns:
            Response object
        """
        # Use transport to make actual HTTP request
        status_code, headers, body, elapsed_time = self.transport.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            params=request.params,
            json_data=request.json,
            data=request.data,
            timeout=request.timeout,
        )

        # Create response object
        response = Response(
            status_code=status_code,
            headers=headers,
            body=body,
            elapsed_time=elapsed_time,
            request=request,
        )

        return response

    def _handle_error_response(self, response: Response):
        """Handle error responses.

        Args:
            response: Response object

        Raises:
            Appropriate exception based on status code
        """
        # Get error message from response
        error_message = None
        try:
            if response.data:
                if isinstance(response.data, dict):
                    error_message = (
                        response.data.get("message")
                        or response.data.get("error")
                        or str(response.data)
                    )
                else:
                    error_message = str(response.data)
        except (AttributeError, TypeError, KeyError):
            # Can't extract error message, will use default
            pass

        # Create appropriate exception
        exception = exception_from_status_code(
            response.status_code,
            message=error_message,
            url=response.request.url if response.request else None,
            method=response.request.method if response.request else None,
            response=response,
        )

        raise exception

    def _log_request(self, request: Request):
        """Log request details (with sensitive data redacted).

        Args:
            request: Request object
        """
        sanitized_headers = self._sanitize_headers(request.headers)

        self.logger.debug(
            f"Request: {request.method} {request.url}",
            extra={"method": request.method, "url": request.url, "headers": sanitized_headers},
        )

    def _log_response(self, response: Response):
        """Log response details.

        Args:
            response: Response object
        """
        self.logger.debug(
            f"Response: {response.status_code} ({response.elapsed_time:.2f}s)",
            extra={
                "status_code": response.status_code,
                "elapsed_time": response.elapsed_time,
                "size": len(response.body) if response.body else 0,
            },
        )

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Sanitize headers for logging (redact sensitive values).

        Args:
            headers: Headers to sanitize

        Returns:
            Sanitized headers
        """
        sensitive_headers = {
            "authorization",
            "x-api-key",
            "x-auth-token",
            "cookie",
            "x-csrf-token",
            "api-key",
            "secret",
        }

        sanitized = {}
        for name, value in headers.items():
            if name.lower() in sensitive_headers:
                sanitized[name] = "[REDACTED]"
            else:
                sanitized[name] = value

        return sanitized

    def close(self):
        """Close client and clean up resources."""
        # Nothing to clean up with urllib

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    # Compatibility with requests-like interface

    def request(self, method: str, url: str, **kwargs) -> Response:
        """Make request with full URL (requests compatibility).

        Args:
            method: HTTP method
            url: Full URL or path
            **kwargs: Request options

        Returns:
            Response object
        """
        # Check if it's a full URL or just a path
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            # Full URL provided, extract path
            path = parsed.path
            if parsed.query:
                path += "?" + parsed.query
        else:
            # Just a path
            path = url

        return self._request(method, path, **kwargs)
