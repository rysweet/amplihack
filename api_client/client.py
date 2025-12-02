"""HTTP API client with retry and rate limiting.

Philosophy:
- Simple HTTP client using requests library
- Integrated retry logic and rate limiting
- Comprehensive error handling
- Structured logging

Public API:
    APIClient: Main HTTP client with retry and rate limiting
"""

import json
import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests

from .exceptions import RateLimitError, RequestError, ResponseError
from .models import Request, Response
from .rate_limiter import RateLimiter
from .retry import RetryHandler

logger = logging.getLogger(__name__)

# Sensitive patterns to redact in logs and exceptions
SENSITIVE_PATTERNS = [
    (re.compile(r'"token"\s*:\s*"[^"]*"', re.IGNORECASE), '"token": "[REDACTED]"'),
    (re.compile(r'"password"\s*:\s*"[^"]*"', re.IGNORECASE), '"password": "[REDACTED]"'),
    (re.compile(r'"api_key"\s*:\s*"[^"]*"', re.IGNORECASE), '"api_key": "[REDACTED]"'),
    (re.compile(r'"secret"\s*:\s*"[^"]*"', re.IGNORECASE), '"secret": "[REDACTED]"'),
    (re.compile(r'"auth"\s*:\s*"[^"]*"', re.IGNORECASE), '"auth": "[REDACTED]"'),
    (re.compile(r"bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE), "Bearer [REDACTED]"),
]


def _sanitize_response_body(text: str) -> str:
    """Sanitize response body by redacting sensitive patterns.

    Args:
        text: Response body text to sanitize

    Returns:
        Sanitized text with sensitive values redacted
    """
    if not text:
        return text

    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


class APIClient:
    """HTTP API client with retry logic and rate limiting.

    Provides a high-level interface for making HTTP requests with:
    - Automatic retries with exponential backoff
    - Rate limiting to respect API limits
    - Structured error handling
    - Request/response logging

    Example:
        >>> client = APIClient(base_url="https://api.example.com")
        >>> request = Request(method="GET", endpoint="/users")
        >>> response = client.send(request)
        >>> print(response.data)
    """

    def __init__(
        self,
        base_url: str,
        rate_limiter: RateLimiter | None = None,
        retry_handler: RetryHandler | None = None,
        default_headers: dict[str, str] | None = None,
        session_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API client.

        Args:
            base_url: Base URL for API (e.g., "https://api.example.com")
            rate_limiter: Optional rate limiter (None = no rate limiting)
            retry_handler: Optional retry handler (None = no retries)
            default_headers: Default headers for all requests
            session_config: Optional session configuration dict
                           (e.g., {'verify': False, 'max_redirects': 10})

        Raises:
            ValueError: If base_url is empty or uses invalid scheme
        """
        if not base_url:
            raise ValueError("base_url cannot be empty")

        # SSRF protection: Only allow HTTP/HTTPS schemes
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ValueError(
                f"Invalid URL scheme. Only http:// and https:// are allowed. Got: {base_url}"
            )

        self._base_url = base_url.rstrip("/")
        self._rate_limiter = rate_limiter
        self._retry_handler = retry_handler or RetryHandler(max_retries=3)
        self._default_headers = default_headers or {}
        self._session = requests.Session()

        # Apply session configuration if provided
        if session_config:
            for key, value in session_config.items():
                setattr(self._session, key, value)

        logger.info(f"APIClient initialized with base_url={base_url}")

    def send(self, request: Request) -> Response:
        """Send HTTP request with retry and rate limiting.

        Args:
            request: Request to send

        Returns:
            Response object

        Raises:
            RequestError: If request fails
            ResponseError: If response indicates error
            RateLimitError: If rate limit exceeded
            RetryExhaustedError: If all retries fail
        """
        logger.debug(f"Sending {request.method} request to {request.endpoint}")

        # Rate limiting
        if self._rate_limiter:
            if not self._rate_limiter.acquire(timeout=30.0):
                raise RateLimitError(message="Rate limit exceeded, timeout waiting for token")

        # Execute with retry
        return self._retry_handler.execute(
            operation=lambda: self._execute_request(request),
            retryable_exceptions=(RequestError, ResponseError),
        )

    def _execute_request(self, request: Request) -> Response:
        """Execute single HTTP request.

        Args:
            request: Request to execute

        Returns:
            Response object

        Raises:
            RequestError: If request fails
            ResponseError: If response indicates error
        """
        # Build full URL
        url = urljoin(self._base_url + "/", request.endpoint.lstrip("/"))

        # Merge headers
        headers = dict(self._default_headers)
        if request.headers:
            headers.update(request.headers)

        # Prepare request kwargs
        kwargs = {
            "headers": headers,
            "timeout": request.timeout,
        }

        if request.params:
            kwargs["params"] = request.params

        if request.data:
            # JSON encode data
            kwargs["json"] = request.data
            headers.setdefault("Content-Type", "application/json")

        # Make request
        try:
            http_response = self._session.request(
                method=request.method.upper(),
                url=url,
                **kwargs,
            )

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise RequestError(
                message=f"Request timeout after {request.timeout}s",
                endpoint=request.endpoint,
                method=request.method,
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise RequestError(
                message="Connection failed",
                endpoint=request.endpoint,
                method=request.method,
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RequestError(
                message=str(e),
                endpoint=request.endpoint,
                method=request.method,
            )

        # Handle rate limiting
        if http_response.status_code == 429:
            retry_after = http_response.headers.get("Retry-After")
            retry_seconds = float(retry_after) if retry_after else None
            logger.warning(f"Rate limit exceeded (429), retry_after={retry_seconds}")
            raise RateLimitError(retry_after=retry_seconds)

        # Parse response
        response = self._parse_response(http_response)

        # Check for errors
        if not response.is_success:
            # Sanitize response body before logging and including in exception
            sanitized_body = _sanitize_response_body(response.raw_text)
            logger.warning(
                f"Request failed with status {response.status_code}: {sanitized_body[:100]}"
            )
            raise ResponseError(
                message=f"Request failed with status {response.status_code}",
                status_code=response.status_code,
                response_body=sanitized_body,
            )

        logger.debug(
            f"Request succeeded: status={response.status_code}, "
            f"elapsed={response.elapsed_seconds:.3f}s"
        )
        return response

    def _parse_response(self, http_response: requests.Response) -> Response:
        """Parse HTTP response into Response object.

        Args:
            http_response: requests.Response object

        Returns:
            Response object
        """
        # Get raw text
        raw_text = http_response.text

        # Try to parse JSON
        data = None
        if raw_text:
            try:
                data = http_response.json()
            except (json.JSONDecodeError, ValueError):
                # Not JSON, leave as None
                logger.debug("Response body is not valid JSON")

        # Convert headers to dict
        headers = dict(http_response.headers)

        return Response(
            status_code=http_response.status_code,
            data=data,
            raw_text=raw_text,
            headers=headers,
            elapsed_seconds=http_response.elapsed.total_seconds(),
        )

    def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        self._session.close()
        logger.info("APIClient closed")

    def __enter__(self) -> "APIClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


__all__ = ["APIClient"]
