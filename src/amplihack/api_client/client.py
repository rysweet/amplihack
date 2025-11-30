"""Main APIClient implementation with async HTTP methods.

Provides enterprise-grade API client with retry, rate limiting, and error handling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, TypeVar
from urllib.parse import urljoin

import aiohttp

from .exceptions import (
    APIClientError,
    NetworkError,
    TimeoutError,
    ValidationError,
    exception_from_status_code,
)
from .models import APIConfig, RateLimitInfo, Request, Response, RetryConfig
from .rate_limiter import RateLimitHandler
from .retry import RetryHandler

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _redact_sensitive_data(text: str, field_name: str = "") -> str:
    """Redact sensitive data from logs.

    Args:
        text: Text to redact
        field_name: Name of the field (for context)

    Returns:
        Redacted text
    """
    # List of sensitive header names
    sensitive_headers = [
        "authorization",
        "api-key",
        "x-api-key",
        "token",
        "x-auth-token",
        "cookie",
        "set-cookie",
        "secret",
    ]

    # Check if this is a sensitive header
    if field_name.lower() in sensitive_headers:
        # Keep first 4 chars if longer, otherwise mask all
        if len(text) > 8:
            return text[:4] + "*" * (len(text) - 4)
        return "*" * len(text)

    # Redact API keys in URLs
    import re

    # Pattern for API keys in URLs
    text = re.sub(
        r"(api[_-]?key|token|secret)=([^&\s]+)", r"\1=***REDACTED***", text, flags=re.IGNORECASE
    )

    return text


def _log_request(request: Request, level: int = logging.DEBUG) -> None:
    """Log request details with sensitive data redacted.

    Args:
        request: Request to log
        level: Log level
    """
    # Redact sensitive headers
    safe_headers = {}
    for key, value in request.headers.items():
        safe_headers[key] = _redact_sensitive_data(value, key)

    # Redact URL
    safe_url = _redact_sensitive_data(request.url, "url")

    logger.log(level, f"Request: {request.method} {safe_url}")
    if safe_headers:
        logger.log(level, f"Headers: {safe_headers}")


class APIClient:
    """Async HTTP client with retry and rate limiting."""

    def __init__(self, config: APIConfig | None = None, base_url: str | None = None, **kwargs):
        """Initialize API client.

        Args:
            config: Complete configuration object
            base_url: Base URL (shorthand if only URL needed)
            **kwargs: Additional config parameters
        """
        if config is None:
            if base_url is None:
                raise ValueError("Either config or base_url must be provided")
            config = APIConfig(base_url=base_url, **kwargs)

        self.config = config
        self.session: aiohttp.ClientSession | None = None

        # Configure logging
        logging.basicConfig(level=getattr(logging, config.log_level.upper()))

        # Initialize retry handler
        retry_config = RetryConfig(
            max_retries=config.max_retries,
            initial_delay=config.retry_delay,
            max_delay=config.max_retry_delay,
            exponential_base=config.retry_multiplier,
        )
        self.retry_handler = RetryHandler(retry_config)

        # Initialize rate limiter
        rate_limit_config = kwargs.get("rate_limit_config")
        self.rate_limiter = RateLimitHandler(rate_limit_config)

    async def __aenter__(self) -> "APIClient":
        """Enter async context manager."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            # Warn if SSL verification is disabled
            if not self.config.verify_ssl:
                logger.warning(
                    "SSL certificate verification is disabled. "
                    "This is insecure and should only be used for testing."
                )

            connector = aiohttp.TCPConnector(
                ssl=self.config.verify_ssl,
            )

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": self.config.user_agent},
            )

    async def close(self) -> None:
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    def _validate_url(self, url: str) -> None:
        """Validate URL for security issues.

        Args:
            url: URL to validate

        Raises:
            ValidationError: If URL is invalid or points to restricted location
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)

        # Block localhost and private IPs
        restricted_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "169.254.169.254",  # AWS metadata endpoint
            "::1",  # IPv6 localhost
        ]

        if parsed.hostname:
            hostname_lower = parsed.hostname.lower()
            if hostname_lower in restricted_hosts:
                raise ValidationError(
                    f"Access to {hostname_lower} is restricted for security reasons", field="url"
                )

            # Check for private IP ranges
            if (
                hostname_lower.startswith("10.")
                or hostname_lower.startswith("192.168.")
                or hostname_lower.startswith("172.")
            ):
                # Check if it's in the 172.16.0.0 - 172.31.255.255 range
                if hostname_lower.startswith("172."):
                    parts = hostname_lower.split(".")
                    if len(parts) >= 2:
                        try:
                            second_octet = int(parts[1])
                            if 16 <= second_octet <= 31:
                                raise ValidationError(
                                    f"Access to private IP {hostname_lower} is restricted",
                                    field="url",
                                )
                        except ValueError:
                            pass
                else:
                    raise ValidationError(
                        f"Access to private IP {hostname_lower} is restricted", field="url"
                    )

    def _build_url(self, path: str) -> str:
        """Build full URL from base and path.

        Args:
            path: API endpoint path

        Returns:
            Full URL

        Raises:
            ValidationError: If URL is invalid or restricted
        """
        if path.startswith("http://") or path.startswith("https://"):
            full_url = path
        else:
            # Ensure path starts with /
            if not path.startswith("/"):
                path = "/" + path
            full_url = urljoin(self.config.base_url, path)

        # Validate the URL
        self._validate_url(full_url)
        return full_url

    def _validate_headers(self, headers: dict[str, str]) -> None:
        """Validate headers for security issues.

        Args:
            headers: Headers to validate

        Raises:
            ValidationError: If headers contain invalid values
        """
        # Check for header injection
        for key, value in headers.items():
            # Check for newlines which could lead to header injection
            if "\n" in key or "\r" in key or "\n" in str(value) or "\r" in str(value):
                raise ValidationError(
                    f"Header '{key}' contains invalid characters (newlines)", field="headers"
                )

            # Validate header name (should be ASCII and follow HTTP spec)
            if not key.replace("-", "").replace("_", "").isalnum():
                raise ValidationError(
                    f"Header name '{key}' contains invalid characters", field="headers"
                )

    def _merge_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        """Merge request headers with default headers.

        Args:
            headers: Request-specific headers

        Returns:
            Merged headers dictionary

        Raises:
            ValidationError: If headers contain invalid values
        """
        merged = self.config.headers.copy()
        if headers:
            merged.update(headers)

        # Validate all headers
        self._validate_headers(merged)
        return merged

    def _parse_rate_limit_headers(self, headers: dict) -> RateLimitInfo:
        """Parse rate limit information from response headers.

        Args:
            headers: Response headers dictionary

        Returns:
            RateLimitInfo with parsed values
        """
        from datetime import datetime

        info = RateLimitInfo()

        # Common rate limit headers
        if 'X-RateLimit-Limit' in headers:
            info.limit = int(headers['X-RateLimit-Limit'])
        if 'X-RateLimit-Remaining' in headers:
            info.remaining = int(headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in headers:
            # Unix timestamp
            info.reset = datetime.fromtimestamp(int(headers['X-RateLimit-Reset']))
        if 'Retry-After' in headers:
            # Can be seconds or HTTP date
            retry_after = headers['Retry-After']
            if retry_after.isdigit():
                info.retry_after = int(retry_after)

        return info

    async def _execute_request(self, request: Request) -> tuple[aiohttp.ClientResponse, str]:
        """Execute HTTP request with rate limiting.

        Args:
            request: Request to execute

        Returns:
            Tuple of (aiohttp response object, response body text)

        Raises:
            NetworkError: For connection issues
            TimeoutError: For timeout issues
        """
        await self._ensure_session()

        # Apply rate limiting
        await self.rate_limiter.acquire()

        # Log the request with redaction
        _log_request(request)

        try:
            # Prepare request parameters
            kwargs: dict[str, Any] = {
                "headers": request.headers,
                "timeout": aiohttp.ClientTimeout(total=request.timeout),
            }

            if request.params:
                kwargs["params"] = request.params

            if request.json_data is not None:
                kwargs["json"] = request.json_data
            elif request.data is not None:
                kwargs["data"] = request.data

            # Make request
            async with self.session.request(
                method=request.method, url=request.url, **kwargs
            ) as response:
                # Read response body
                text = await response.text()

                # Update rate limiter from response
                self.rate_limiter.update_from_response(dict(response.headers), response.status)

                # Return tuple with response and body text
                return response, text

        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"Request timed out after {request.timeout}s", request=request
            ) from e
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error: {e!s}", request=request) from e
        except Exception as e:
            raise APIClientError(f"Unexpected error: {e!s}", request=request) from e

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Internal request method with retry logic.

        Args:
            method: HTTP method
            path: API endpoint
            params: Query parameters
            json_data: JSON body
            data: Form data
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object

        Raises:
            Various API exceptions based on response
        """
        # Build request
        request = Request(
            method=method.upper(),
            url=self._build_url(path),
            headers=self._merge_headers(headers),
            params=params,
            json_data=json_data,
            data=data,
            timeout=self.config.timeout,
        )

        # Execute with retry
        start_time = datetime.now()

        async def execute():
            response, body_text = await self._execute_request(request)

            # Check for errors
            if response.status >= 400:
                retry_after = response.headers.get("Retry-After")

                if retry_after:
                    try:
                        retry_after = int(retry_after)
                    except ValueError:
                        retry_after = None

                raise exception_from_status_code(
                    status_code=response.status,
                    message=f"HTTP {response.status}: {response.reason}",
                    response_body=body_text,
                    request=request,
                    retry_after=retry_after,
                )

            return response, body_text

        response, body_text = await self.retry_handler.execute_with_retry(execute)

        # Build response object
        elapsed = datetime.now() - start_time

        # Parse response data - always try to parse JSON if content-type indicates it
        data = None
        if body_text:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type or (
                not content_type and body_text.strip().startswith(("[", "{"))
            ):
                # Try to parse as JSON
                try:
                    data = json.loads(body_text)
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse JSON response: {e}")
                    # Return raw text if JSON parsing fails
                    data = body_text
            elif response_type:
                # If response type specified but not JSON, still try parsing
                try:
                    data = json.loads(body_text)
                except json.JSONDecodeError:
                    data = body_text
            else:
                # For non-JSON responses, just store raw text in data
                data = body_text if body_text.strip() else None

        return Response(
            status_code=response.status,
            headers=dict(response.headers),
            data=data,
            raw_text=body_text,
            elapsed=elapsed,
            request=request,
        )

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Perform GET request.

        Args:
            path: API endpoint
            params: Query parameters
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object
        """
        return await self._request(
            method="GET",
            path=path,
            params=params,
            headers=headers,
            response_type=response_type,
        )

    async def post(
        self,
        path: str,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Perform POST request.

        Args:
            path: API endpoint
            json: JSON body
            data: Form data
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object
        """
        return await self._request(
            method="POST",
            path=path,
            json_data=json,
            data=data,
            headers=headers,
            response_type=response_type,
        )

    async def put(
        self,
        path: str,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Perform PUT request.

        Args:
            path: API endpoint
            json: JSON body
            data: Form data
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object
        """
        return await self._request(
            method="PUT",
            path=path,
            json_data=json,
            data=data,
            headers=headers,
            response_type=response_type,
        )

    async def patch(
        self,
        path: str,
        json: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Perform PATCH request.

        Args:
            path: API endpoint
            json: JSON body
            data: Form data
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object
        """
        return await self._request(
            method="PATCH",
            path=path,
            json_data=json,
            data=data,
            headers=headers,
            response_type=response_type,
        )

    async def delete(
        self,
        path: str,
        headers: dict[str, str] | None = None,
        response_type: type[T] | None = None,
    ) -> Response[T]:
        """Perform DELETE request.

        Args:
            path: API endpoint
            headers: Request headers
            response_type: Expected response type

        Returns:
            Response object
        """
        return await self._request(
            method="DELETE",
            path=path,
            headers=headers,
            response_type=response_type,
        )
