"""Main API client implementation."""

import ipaddress
import json as json_lib
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import ClientConfig
from .exceptions import APIError, HTTPError
from .rate_limiter import RateLimiter
from .response import Response


class APIClient:
    """REST API client with automatic retries and rate limiting.

    Provides a simple interface for making HTTP requests with:
    - Automatic retry on 5xx errors with exponential backoff
    - Rate limiting (default 10 requests/second)
    - Thread-safe operation
    - Zero external dependencies (uses only urllib)
    """

    def __init__(self, config: ClientConfig):
        """Initialize API client with configuration.

        Args:
            config: Client configuration object
        """
        self.config = config
        self._rate_limiter = RateLimiter(requests_per_second=10.0)

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a GET request.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional custom headers

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        return self._request("GET", endpoint, params=params, headers=headers)

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        data: bytes | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a POST request.

        Args:
            endpoint: API endpoint path
            json: Optional JSON data to send
            data: Optional raw bytes to send
            params: Optional query parameters
            headers: Optional custom headers

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        return self._request("POST", endpoint, json=json, data=data, params=params, headers=headers)

    def put(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        data: bytes | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a PUT request.

        Args:
            endpoint: API endpoint path
            json: Optional JSON data to send
            data: Optional raw bytes to send
            params: Optional query parameters
            headers: Optional custom headers

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        return self._request("PUT", endpoint, json=json, data=data, params=params, headers=headers)

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            headers: Optional custom headers

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        return self._request("DELETE", endpoint, params=params, headers=headers)

    def _request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
        data: bytes | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Internal method to make HTTP requests with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            json: Optional JSON data
            data: Optional raw data
            params: Optional query parameters
            headers: Optional custom headers

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        # Apply rate limiting
        self._rate_limiter.acquire()

        # Build full URL
        url = self._build_url(endpoint, params)

        # Prepare request data
        request_data = None
        if json is not None:
            request_data = json_lib.dumps(json).encode("utf-8")
        elif data is not None:
            request_data = data

        # Prepare headers
        request_headers = self._prepare_headers(headers, json is not None)

        # Create request object
        request = urllib.request.Request(url, data=request_data, method=method)
        # Set headers directly to preserve case
        request.headers = request_headers

        # Execute request with retry logic
        return self._execute_with_retry(request)

    def _validate_url(self, url: str) -> None:
        """Validate URL to prevent SSRF attacks.

        Args:
            url: URL to validate

        Raises:
            APIError: If URL is not allowed (private IPs, non-HTTP schemes, etc)
        """
        # Parse the URL
        parsed = urllib.parse.urlparse(url)

        # Only allow HTTP and HTTPS schemes
        if parsed.scheme not in ("http", "https"):
            raise APIError(
                f"URL scheme not allowed: {parsed.scheme}. Only http and https are permitted."
            )

        # Get hostname
        hostname = parsed.hostname
        if not hostname:
            raise APIError("Invalid URL: no hostname found")

        # Try to resolve the hostname to check for private IPs
        try:
            # Resolve hostname to IP
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)

                    # Block private IP ranges
                    if ip.is_private:
                        raise APIError(f"Access to private IP addresses is not allowed: {ip_str}")
                    if ip.is_loopback:
                        raise APIError(f"Access to loopback addresses is not allowed: {ip_str}")
                    if ip.is_link_local:
                        raise APIError(f"Access to link-local addresses is not allowed: {ip_str}")
                    if ip.is_multicast:
                        raise APIError(f"Access to multicast addresses is not allowed: {ip_str}")
                    # Block metadata service IPs (AWS, GCP, Azure)
                    metadata_ips = ["169.254.169.254", "fd00:ec2::254"]
                    if str(ip) in metadata_ips:
                        raise APIError(f"Access to cloud metadata service is not allowed: {ip_str}")
                except (ipaddress.AddressValueError, ValueError):
                    # Not a valid IP, might be IPv6 or something else
                    # Let it through if we can't parse it as IP
                    pass
        except (OSError, socket.gaierror):
            # Can't resolve hostname - this will fail later anyway
            pass

    def _build_url(self, endpoint: str, params: dict[str, Any] | None) -> str:
        """Build full URL from endpoint and parameters.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            Complete URL string
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint

        # Build base URL
        url = self.config.base_url + endpoint

        # Add query parameters
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        # Validate URL for SSRF prevention (always enabled for security)
        self._validate_url(url)

        return url

    def _prepare_headers(
        self, custom_headers: dict[str, str] | None, is_json: bool
    ) -> dict[str, str]:
        """Prepare request headers.

        Args:
            custom_headers: Optional custom headers
            is_json: Whether request contains JSON data

        Returns:
            Combined headers dictionary
        """
        headers = {}

        # Add default headers
        if is_json:
            headers["Content-Type"] = "application/json"

        # Add API key if configured
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        # Add custom headers (may override defaults)
        if custom_headers:
            for key, value in custom_headers.items():
                # Keep the original casing for headers
                headers[key] = value

        return headers

    def _execute_with_retry(self, request: urllib.request.Request) -> Response:
        """Execute request with retry logic for 5xx errors.

        Args:
            request: Prepared urllib request object

        Returns:
            Response object

        Raises:
            HTTPError: For HTTP error responses
            APIError: For other API-related errors
        """
        last_exception = None

        for retry_count in range(self.config.max_retries + 1):
            try:
                # Execute request
                with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                    # Read response data
                    content = response.read()
                    headers = dict(response.headers.items())

                    return Response(status_code=response.status, content=content, headers=headers)

            except urllib.error.HTTPError as e:
                # Handle HTTP errors
                status_code = e.code

                # Read error response body
                error_content = e.read() if hasattr(e, "read") else b""
                error_data = None
                try:
                    if error_content:
                        error_data = json_lib.loads(error_content.decode("utf-8"))
                except (json_lib.JSONDecodeError, UnicodeDecodeError):
                    pass

                # Check if we should retry
                should_retry = retry_count < self.config.max_retries and (
                    status_code == 429 or 500 <= status_code < 600
                )

                if should_retry:
                    # Calculate wait time
                    if status_code == 429:
                        # Try to use Retry-After header for 429
                        retry_after = e.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_time = int(retry_after)
                            except ValueError:
                                wait_time = (2**retry_count) * 0.5
                        else:
                            wait_time = (2**retry_count) + 1
                    else:
                        # Standard exponential backoff for 5xx errors
                        wait_time = (2**retry_count) * 0.5

                    time.sleep(wait_time)
                    last_exception = e
                    continue

                # No retry - raise HTTPError
                raise HTTPError(
                    status_code=status_code,
                    message=e.reason or f"HTTP {status_code}",
                    response_data=error_data,
                )

            except (TimeoutError, OSError, urllib.error.URLError) as e:
                # Network errors - retry if attempts remain
                if retry_count < self.config.max_retries:
                    wait_time = (2**retry_count) * 0.5
                    time.sleep(wait_time)
                    last_exception = e
                    continue

                # Convert to APIError
                if isinstance(e, socket.timeout):
                    raise APIError(f"Request timeout after {self.config.timeout} seconds")
                if isinstance(e, urllib.error.URLError):
                    if isinstance(e.reason, socket.gaierror):
                        raise APIError(f"Failed to resolve host: {e.reason}")
                    raise APIError(f"Failed to connect to server: {e.reason}")
                raise APIError(f"Network error: {e!s}")

            except Exception as e:
                # Mask API key in error messages if present
                error_msg = str(e)
                if self.config.api_key and self.config.api_key in error_msg:
                    masked_key = self.config.get_masked_api_key()
                    if masked_key:
                        error_msg = error_msg.replace(self.config.api_key, masked_key)
                # Unexpected errors
                raise APIError(f"Unexpected error during request: {error_msg}")

        # If we exhausted retries, raise the last exception
        if last_exception:
            if isinstance(last_exception, urllib.error.HTTPError):
                raise HTTPError(
                    status_code=last_exception.code,
                    message=last_exception.reason or f"HTTP {last_exception.code}",
                    response_data=None,
                )
            raise APIError(
                f"Request failed after {self.config.max_retries} retries: {last_exception!s}"
            )

        # Should not reach here
        raise APIError("Request failed for unknown reason")
