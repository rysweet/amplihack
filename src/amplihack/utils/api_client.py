"""REST API Client with retry logic, rate limiting, and comprehensive error handling.

A simple, robust API client following ruthless simplicity principles:
- Direct use of requests.Session()
- Simple exponential backoff
- Flat exception hierarchy (3 exceptions)
- Minimal dataclasses for request/response
- Single execute() method plus convenience methods
"""

import ipaddress
import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

# Configure logging
logger = logging.getLogger(__name__)

# Public API exports
__all__ = [
    "APIClient",
    "APIRequest",
    "APIResponse",
    "APIError",
    "RateLimitError",
    "ValidationError",
]


# Exception hierarchy (flat and simple)
class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request_id: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
        self.request_id = request_id


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(APIError):
    """Raised when input validation fails."""


# Dataclasses for request/response
@dataclass
class APIRequest:
    """Represents an API request."""

    method: str
    endpoint: str
    data: dict[str, Any] | list | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate request parameters."""
        # Validate types
        if not isinstance(self.method, str):
            raise ValidationError("Method must be a string")
        if not isinstance(self.endpoint, str):
            raise ValidationError("Endpoint must be a string")
        if not isinstance(self.headers, dict):
            raise ValidationError("Headers must be a dictionary")

        # Validate method value
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if self.method.upper() not in valid_methods:
            raise ValidationError(f"Invalid HTTP method: {self.method}")

        # Validate endpoint not empty
        if not self.endpoint:
            raise ValidationError("Endpoint cannot be empty")

        # Store method in uppercase for consistency
        self.method = self.method.upper()


@dataclass
class APIResponse:
    """Represents an API response."""

    status_code: int
    data: dict[str, Any] | list | None = None
    headers: dict[str, str] = field(default_factory=dict)
    text: str | None = None  # Store raw text for non-JSON responses

    def __str__(self):
        """String representation including non-JSON text if present."""
        if self.data is not None:
            return f"APIResponse(status_code={self.status_code}, data={self.data})"
        if self.text is not None:
            return f"APIResponse(status_code={self.status_code}, data=None, text='{self.text}')"
        return f"APIResponse(status_code={self.status_code}, data=None)"


class APIClient:
    """REST API client with retry logic and rate limiting.

    Supports context manager usage for automatic session cleanup:
        with APIClient(base_url="https://api.example.com") as client:
            response = client.get("/endpoint")
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        verify_ssl: bool = True,
    ):
        """Initialize the API client.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            backoff_factor: Factor for exponential backoff calculation
            verify_ssl: Whether to verify SSL/TLS certificates (default=True)
        """
        # Validate parameters
        if timeout <= 0:
            raise ValidationError("Timeout must be positive")
        if max_retries < 0:
            raise ValidationError("Max_retries must be non-negative")
        if backoff_factor <= 0:
            raise ValidationError("Backoff_factor must be positive")

        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.verify_ssl = verify_ssl
        self._session = None  # Lazy-initialized session
        self._session_lock = threading.Lock()  # Thread safety for session initialization

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up session."""
        self.close()
        return False

    def close(self):
        """Close the session and clean up resources."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def _get_session(self) -> requests.Session:
        """Get or create session with thread safety."""
        if self._session is None:
            with self._session_lock:
                # Double-checked locking pattern
                if self._session is None:
                    self._session = requests.Session()
        return self._session

    def _mask_sensitive_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Mask sensitive headers for logging.

        Args:
            headers: Original headers dictionary

        Returns:
            Headers dictionary with sensitive values masked
        """
        if not headers:
            return {}

        masked_headers = headers.copy()
        sensitive_keys = {"authorization", "api-key", "x-api-key", "token", "x-auth-token"}

        for key in masked_headers:
            if key.lower() in sensitive_keys:
                masked_headers[key] = "***MASKED***"

        return masked_headers

    def _validate_url(self, url: str) -> None:
        """Validate URL to prevent SSRF attacks.

        Args:
            url: URL to validate

        Raises:
            ValidationError: If URL is invalid or points to internal network
        """
        parsed = urlparse(url)

        # Only validate if we have a full URL (with scheme)
        # Relative URLs are allowed when using base_url
        if not parsed.scheme:
            return

        # Ensure scheme is http or https for absolute URLs
        if parsed.scheme not in ("http", "https"):
            raise ValidationError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed")

        hostname = parsed.hostname
        if not hostname:
            return

        hostname_lower = hostname.lower()

        # Block localhost variations
        blocked_hosts = {
            "localhost", "127.0.0.1", "0.0.0.0",
            "::1", "::ffff:127.0.0.1",  # IPv6 localhost
            "[::1]", "[::ffff:127.0.0.1]"  # Bracketed IPv6
        }
        if hostname_lower in blocked_hosts:
            raise ValidationError(f"Blocked internal host: {hostname}")

        # Try to parse as IP address for more thorough validation
        try:
            ip = ipaddress.ip_address(hostname.strip("[]"))  # Handle bracketed IPv6

            # Check if it's a private or reserved IP
            if ip.is_private or ip.is_reserved or ip.is_loopback or ip.is_multicast:
                raise ValidationError(f"Blocked private/reserved IP: {hostname}")

            # Check for link-local addresses (IPv4: 169.254.0.0/16, IPv6: fe80::/10)
            if ip.is_link_local:
                raise ValidationError(f"Blocked link-local IP: {hostname}")

            # Additional IPv6 checks
            if isinstance(ip, ipaddress.IPv6Address):
                # Block IPv6 unique local addresses (fc00::/7)
                if ip.packed[0] & 0xfe == 0xfc:
                    raise ValidationError(f"Blocked IPv6 unique local address: {hostname}")

        except ValueError:
            # Not an IP address, it's a hostname
            # Block common internal hostnames that might resolve to private IPs
            blocked_patterns = [
                "internal", "intranet", "corp", "private",
                ".local", ".localhost", ".internal"
            ]
            for pattern in blocked_patterns:
                if pattern in hostname_lower:
                    logger.warning(f"Potentially internal hostname detected: {hostname}")
                    # Note: Not blocking these outright as they might be legitimate
                    # but logging for monitoring

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter.

        Args:
            attempt: Retry attempt number (0-based)

        Returns:
            Backoff time in seconds
        """
        # Base exponential backoff: factor * 2^attempt
        base_backoff = min(self.backoff_factor * (2**attempt), 60.0)

        # Add jitter (random value between 0 and base_backoff)
        jitter = random.uniform(0, 1) * base_backoff

        return base_backoff + jitter

    def _should_retry(self, status_code: int) -> bool:
        """Determine if request should be retried based on status code.

        Args:
            status_code: HTTP status code

        Returns:
            True if request should be retried
        """
        # Retry on server errors (5xx) and rate limit (429)
        return status_code >= 500 or status_code == 429

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract error message from response.

        Handles multiple common API error formats:
        - {"error": {"message": "...", "code": "..."}}
        - {"error": "..."}
        - {"message": "..."}
        - {"detail": "..."}
        - {"errors": [...]}
        - {"error_description": "..."}

        Args:
            response: HTTP response object

        Returns:
            Error message string
        """
        base_msg = f"API Error: {response.status_code}"

        # Try to extract error from JSON response
        try:
            error_data = response.json()

            if not isinstance(error_data, dict):
                return base_msg

            # Check error_description first for OAuth/OIDC (highest priority for OAuth)
            if "error_description" in error_data and isinstance(error_data["error_description"], str):
                return f"API Error: {error_data['error_description']}"

            # Format 1: {"error": {"message": "...", "code": "..."}}
            if "error" in error_data:
                error = error_data["error"]
                if isinstance(error, dict):
                    # Try to get message first, then code
                    if "message" in error:
                        return f"API Error: {error['message']}"
                    elif "code" in error:
                        return f"API Error: {error['code']}"
                    elif "description" in error:
                        return f"API Error: {error['description']}"
                # Format 2: {"error": "simple string"}
                elif isinstance(error, str):
                    return f"API Error: {error}"

            # Format 3: {"message": "..."}
            if "message" in error_data and isinstance(error_data["message"], str):
                return f"API Error: {error_data['message']}"

            # Format 4: {"detail": "..."} (common in FastAPI/Django)
            if "detail" in error_data:
                if isinstance(error_data["detail"], str):
                    return f"API Error: {error_data['detail']}"
                elif isinstance(error_data["detail"], list) and error_data["detail"]:
                    # Handle validation error arrays
                    first_error = error_data["detail"][0]
                    if isinstance(first_error, dict) and "msg" in first_error:
                        return f"API Error: {first_error['msg']}"

            # Format 5: {"errors": [...]}
            if "errors" in error_data and isinstance(error_data["errors"], list):
                if error_data["errors"]:
                    first_error = error_data["errors"][0]
                    if isinstance(first_error, dict):
                        # Try common error fields
                        for field in ["message", "msg", "detail", "description"]:
                            if field in first_error:
                                return f"API Error: {first_error[field]}"
                    elif isinstance(first_error, str):
                        return f"API Error: {first_error}"


        except (ValueError, TypeError, KeyError, AttributeError):
            # If JSON parsing fails or structure is unexpected, fall back to base message
            pass

        return base_msg

    def execute(self, request: APIRequest) -> APIResponse:
        """Execute an API request with retry logic and rate limiting.

        Args:
            request: APIRequest object containing request details

        Returns:
            APIResponse object containing response data

        Raises:
            APIError: For general API errors
            RateLimitError: When rate limit is exceeded
            ValidationError: For validation errors
        """
        # Build full URL
        url = f"{self.base_url}{request.endpoint}" if self.base_url else request.endpoint

        # Validate URL for SSRF protection
        self._validate_url(url)

        # Get session
        self._get_session()

        # Generate request ID for tracking
        request_id = str(uuid.uuid4())

        # Add request ID to headers if not already present
        headers = request.headers.copy()
        if "X-Request-Id" not in headers:
            headers["X-Request-Id"] = request_id

        # Prepare request parameters
        kwargs = {
            "method": request.method,
            "url": url,
            "json": request.data,
            "headers": headers,
            "timeout": self.timeout,
            "verify": self.verify_ssl,
        }

        # Log the request with masked headers and request ID
        masked_headers = self._mask_sensitive_headers(headers)
        logger.debug(f"[{request_id}] {request.method} {request.endpoint} headers={masked_headers}")

        # Retry loop
        response = None

        for attempt in range(self.max_retries + 1):
            try:
                # Make the request
                response = requests.request(**kwargs)

                # Extract response request ID (server might send back a different one)
                response_request_id = response.headers.get("X-Request-Id", request_id)

                # Log response with request ID
                logger.debug(f"[{response_request_id}] Response: {response.status_code}")

                # Handle retryable status codes
                if self._should_retry(response.status_code) and attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt)

                    # Special handling for rate limiting
                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            wait_time = float(retry_after)
                            logger.warning(
                                f"[{response_request_id}] Rate limited. Waiting {wait_time} seconds (Retry-After)"
                            )
                        else:
                            logger.warning(
                                f"[{response_request_id}] Rate limited. Waiting {wait_time:.1f} seconds (backoff)"
                            )
                    else:
                        logger.info(
                            f"[{response_request_id}] Server error {response.status_code}. Retrying in {wait_time:.1f} seconds"
                        )

                    logger.info(f"[{response_request_id}] Retrying request (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue

                # Handle client errors (4xx) - don't retry these
                if 400 <= response.status_code < 500:
                    if response.status_code == 429:
                        # Rate limit exceeded after all retries
                        retry_after = response.headers.get("Retry-After")
                        logger.warning(f"[{response_request_id}] Rate limit exceeded. Retry-After: {retry_after}")
                        raise RateLimitError(
                            "Rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None,
                            status_code=response.status_code,
                            response_body=response.text,
                            request_id=response_request_id,
                        )
                    # Other client errors
                    raise APIError(
                        self._extract_error_message(response),
                        status_code=response.status_code,
                        response_body=response.text,
                        request_id=response_request_id,
                    )

                # Handle server errors after max retries
                if response.status_code >= 500 and attempt == self.max_retries:
                    raise APIError(
                        "Max retries exceeded",
                        status_code=response.status_code,
                        response_body=response.text,
                        request_id=response_request_id,
                    )

                # Parse response data
                data = None
                text = None
                if response.content:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        logger.debug(f"[{response_request_id}] Response is not JSON")
                        text = response.text

                # Success - return response with request ID in headers
                response_headers = dict(response.headers)
                response_headers["X-Request-Id"] = response_request_id

                return APIResponse(
                    status_code=response.status_code,
                    data=data,
                    headers=response_headers,
                    text=text if data is None else None,
                )

            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < self.max_retries:
                    wait_time = self._calculate_backoff(attempt)
                    error_type = (
                        "Connection" if isinstance(e, requests.ConnectionError) else "Timeout"
                    )
                    logger.warning(f"[{request_id}] {error_type} error. Retrying in {wait_time:.1f} seconds")
                    logger.info(f"[{request_id}] Retrying request (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                # Max retries exceeded
                error_type = "connection" if isinstance(e, requests.ConnectionError) else "timeout"
                raise APIError(
                    f"Request failed: {error_type} error",
                    request_id=request_id
                ) from e

        # This should not be reached, but handle it defensively
        raise APIError("Unexpected error in retry loop", request_id=request_id)

    # Convenience methods
    def get(self, endpoint: str, headers: dict[str, str] | None = None) -> APIResponse:
        """Convenience method for GET requests."""
        request = APIRequest(method="GET", endpoint=endpoint, headers=headers or {})
        return self.execute(request)

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Convenience method for POST requests."""
        request = APIRequest(method="POST", endpoint=endpoint, data=data, headers=headers or {})
        return self.execute(request)

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Convenience method for PUT requests."""
        request = APIRequest(method="PUT", endpoint=endpoint, data=data, headers=headers or {})
        return self.execute(request)

    def delete(self, endpoint: str, headers: dict[str, str] | None = None) -> APIResponse:
        """Convenience method for DELETE requests."""
        request = APIRequest(method="DELETE", endpoint=endpoint, headers=headers or {})
        return self.execute(request)

    def patch(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Convenience method for PATCH requests."""
        request = APIRequest(method="PATCH", endpoint=endpoint, data=data, headers=headers or {})
        return self.execute(request)
