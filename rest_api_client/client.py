"""Main REST API client implementation.

Combines all components to provide a complete HTTP client with retry,
rate limiting, and comprehensive error handling.
"""

import os
import time
import warnings
from typing import Any
from urllib.parse import urljoin

import httpx

from .config import ClientConfig, RateLimitConfig, RetryConfig
from .exceptions import (
    APIClientError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from .logger import APIClientLogger, get_logger
from .models import APIRequest, APIResponse
from .rate_limiter import RateLimiter
from .retry import RetryHandler
from .session import SessionManager


class APIClient:
    """REST API client with retry, rate limiting, and error handling.

    Example:
        client = APIClient("https://api.example.com")
        response = client.get("/users")
        print(response.json_data)
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_config: RetryConfig | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        enable_logging: bool = True,
        log_level: str = "INFO",
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL for all API requests
            api_key: API key for authentication
            timeout: Default timeout in seconds
            headers: Default headers for all requests
            verify_ssl: Whether to verify SSL certificates
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            retry_config: Retry behavior configuration (overrides max_retries and retry_delay)
            rate_limit_config: Rate limiting configuration
            enable_logging: Whether to enable request logging
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Validate base_url
        if not base_url:
            raise ValidationError("Invalid base URL: URL cannot be empty")
        if not base_url.startswith(("http://", "https://")):
            raise ValidationError("Invalid base URL: Must start with http:// or https://")
        if base_url.startswith("ftp://"):
            raise ValidationError("Invalid base URL: FTP protocol not supported")

        # Check for API key in environment if not provided
        if not api_key:
            api_key = os.environ.get("API_KEY") or os.environ.get("REST_API_KEY")

        # Warn if SSL verification is disabled
        if not verify_ssl:
            warnings.warn(
                "SSL verification is disabled - this is insecure and should only be used in development!",
                UserWarning,
                stacklevel=2,
            )

        # Set up headers with defaults
        default_headers = {"User-Agent": "rest-api-client/1.0.0"}
        if headers:
            default_headers.update(headers)
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"

        # Create retry config if not provided
        if retry_config is None:
            retry_config = RetryConfig(max_retries=max_retries, base_delay=retry_delay)

        self.config = ClientConfig(
            base_url=base_url,
            timeout=timeout,
            headers=default_headers,
            verify_ssl=verify_ssl,
            retry_config=retry_config,
            rate_limit_config=rate_limit_config or RateLimitConfig(),
            enable_logging=enable_logging,
            log_level=log_level,
        )

        # Store attributes that tests expect
        self.base_url = base_url
        self.timeout = timeout
        self.headers = default_headers
        self.max_retries = retry_config.max_retries
        self.retry_delay = retry_config.base_delay

        self.session_manager = SessionManager(self.config)
        self.retry_handler = RetryHandler(self.config.retry_config)
        self.rate_limiter = RateLimiter(self.config.rate_limit_config)
        self.logger: APIClientLogger | None = None

        if self.config.enable_logging:
            self.logger = get_logger("rest_api_client", self.config.log_level)

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint.

        Args:
            endpoint: API endpoint (can be relative or absolute)

        Returns:
            Full URL
        """
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return urljoin(self.config.base_url + "/", endpoint.lstrip("/"))

    def _prepare_request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        timeout: float | None = None,
    ) -> APIRequest:
        """Prepare an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            timeout: Request timeout

        Returns:
            Prepared APIRequest object
        """
        # Merge headers
        request_headers = self.config.headers.copy()
        if headers:
            request_headers.update(headers)

        # Build full URL
        url = self._build_url(endpoint)

        # Use configured timeout if not specified
        if timeout is None:
            timeout = self.config.timeout

        return APIRequest(
            method=method,
            url=url,
            headers=request_headers,
            params=params,
            json_data=json_data,
            data=data,
            timeout=timeout,
        )

    def _convert_response(
        self, httpx_response: httpx.Response, request: APIRequest, elapsed_time: float
    ) -> APIResponse:
        """Convert httpx response to APIResponse.

        Args:
            httpx_response: Response from httpx
            request: Original request
            elapsed_time: Time taken for request

        Returns:
            APIResponse object
        """
        return APIResponse(
            status_code=httpx_response.status_code,
            headers=dict(httpx_response.headers),
            body=httpx_response.text,
            request=request,
            elapsed_time=elapsed_time,
        )

    def _handle_http_error(self, error: httpx.HTTPError, request: APIRequest) -> None:
        """Convert httpx errors to our exception types.

        Args:
            error: httpx exception
            request: The request that caused the error

        Raises:
            NetworkError: For connection errors
            TimeoutError: For timeout errors
            APIClientError: For other errors
        """
        if isinstance(error, httpx.ConnectError):
            raise NetworkError(f"Failed to connect to {request.url}: {error!s}")
        if isinstance(error, httpx.TimeoutException):
            raise TimeoutError(f"Request to {request.url} timed out: {error!s}")
        raise APIClientError(f"HTTP error occurred: {error!s}")

    def _execute_request(self, request: APIRequest) -> APIResponse:
        """Execute a single request without retry.

        Args:
            request: The request to execute

        Returns:
            APIResponse object

        Raises:
            Various APIException subclasses for different error scenarios
        """
        # Generate request ID for tracking
        request_id = None
        if self.logger:
            request_id = self.logger.set_request_id()
            self.logger.log_request(
                method=request.method,
                url=request.url,
                headers=len(request.headers),
                has_params=request.params is not None,
                has_json=request.json_data is not None,
                has_data=request.data is not None,
            )

        start_time = time.time()

        try:
            # Get the HTTP client
            client = self.session_manager.get_sync_client()

            # Prepare kwargs for httpx
            kwargs: dict[str, Any] = {
                "method": request.method,
                "url": request.url,
                "headers": request.headers,
                "timeout": request.timeout,
            }

            if request.params:
                kwargs["params"] = request.params
            if request.json_data is not None:
                kwargs["json"] = request.json_data
            elif request.data is not None:
                kwargs["data"] = request.data

            # Make the request
            httpx_response = client.request(**kwargs)
            elapsed_time = time.time() - start_time

            # Convert to our response type
            response = self._convert_response(httpx_response, request, elapsed_time)

            # Log the response
            if self.logger:
                self.logger.log_response(
                    status_code=response.status_code, elapsed_time=elapsed_time
                )

            # Check for rate limit response
            if response.status_code == 429:
                retry_after = None
                if "Retry-After" in response.headers:
                    try:
                        retry_after = int(response.headers["Retry-After"])
                        self.rate_limiter.set_retry_after(retry_after)
                    except ValueError:
                        pass

                raise RateLimitError(
                    retry_after=retry_after, response_body=response.body, request_id=request_id
                )

            # Raise for error status codes
            response.raise_for_status()

            return response

        except httpx.HTTPError as e:
            elapsed_time = time.time() - start_time
            if self.logger:
                self.logger.log_error(e, elapsed_time=elapsed_time)
            self._handle_http_error(e, request)
            # This line should never be reached due to _handle_http_error raising
            raise APIClientError(f"Unexpected error: {e!s}")

        except APIClientError:
            # Re-raise our own exceptions
            raise

        except Exception as e:
            # Wrap any other exceptions
            if self.logger:
                self.logger.log_error(e)
            raise APIClientError(f"Unexpected error: {e!s}")

        finally:
            # Clear request ID
            if self.logger:
                self.logger.clear_request_id()

    def _request_with_retry_and_rate_limit(self, request: APIRequest) -> APIResponse:
        """Execute request with retry logic and rate limiting.

        Args:
            request: The request to execute

        Returns:
            APIResponse object
        """

        def on_retry(attempt: int, delay: float, reason: str) -> None:
            """Log retry attempts."""
            if self.logger:
                self.logger.log_retry(attempt, delay, reason)

        def execute() -> APIResponse:
            """Execute with rate limiting."""
            # Wait for rate limit token
            wait_time = self.rate_limiter.wait_time()
            if wait_time > 0:
                if self.logger:
                    self.logger.log_rate_limit(wait_time)
                time.sleep(wait_time)

            # Acquire token
            self.rate_limiter.acquire()

            # Execute the request
            return self._execute_request(request)

        # Execute with retry
        return self.retry_handler.execute_with_retry(execute, on_retry)

    def request(
        self,
        method: str,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        timeout: float | None = None,
        skip_retry: bool = False,
        skip_rate_limit: bool = False,
    ) -> APIResponse:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            timeout: Request timeout
            skip_retry: Skip retry logic
            skip_rate_limit: Skip rate limiting

        Returns:
            APIResponse object

        Raises:
            Various APIException subclasses for different error scenarios
        """
        # Prepare the request
        request = self._prepare_request(
            method=method,
            endpoint=endpoint,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data,
            timeout=timeout,
        )

        # Execute based on flags
        if skip_retry and skip_rate_limit:
            return self._execute_request(request)
        if skip_retry:
            # Rate limit but no retry
            wait_time = self.rate_limiter.wait_time()
            if wait_time > 0:
                if self.logger:
                    self.logger.log_rate_limit(wait_time)
                time.sleep(wait_time)
            self.rate_limiter.acquire()
            return self._execute_request(request)
        if skip_rate_limit:
            # Retry but no rate limit
            def on_retry(attempt: int, delay: float, reason: str) -> None:
                if self.logger:
                    self.logger.log_retry(attempt, delay, reason)

            return self.retry_handler.execute_with_retry(
                lambda: self._execute_request(request), on_retry
            )
        # Full retry and rate limit
        return self._request_with_retry_and_rate_limit(request)

    def get(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Make a GET request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            timeout: Request timeout
            **kwargs: Additional arguments for request()

        Returns:
            APIResponse object
        """
        return self.request(
            method="GET",
            endpoint=endpoint,
            headers=headers,
            params=params,
            timeout=timeout,
            **kwargs,
        )

    def post(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Make a POST request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            timeout: Request timeout
            **kwargs: Additional arguments for request()

        Returns:
            APIResponse object
        """
        return self.request(
            method="POST",
            endpoint=endpoint,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data,
            timeout=timeout,
            **kwargs,
        )

    def put(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Make a PUT request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            timeout: Request timeout
            **kwargs: Additional arguments for request()

        Returns:
            APIResponse object
        """
        return self.request(
            method="PUT",
            endpoint=endpoint,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data,
            timeout=timeout,
            **kwargs,
        )

    def patch(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        data: dict[str, Any] | bytes | str | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Make a PATCH request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            json_data: JSON body data
            data: Form data or raw body
            timeout: Request timeout
            **kwargs: Additional arguments for request()

        Returns:
            APIResponse object
        """
        return self.request(
            method="PATCH",
            endpoint=endpoint,
            headers=headers,
            params=params,
            json_data=json_data,
            data=data,
            timeout=timeout,
            **kwargs,
        )

    def delete(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint
            headers: Additional headers
            params: Query parameters
            timeout: Request timeout
            **kwargs: Additional arguments for request()

        Returns:
            APIResponse object
        """
        return self.request(
            method="DELETE",
            endpoint=endpoint,
            headers=headers,
            params=params,
            timeout=timeout,
            **kwargs,
        )

    def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        self.session_manager.close()

    def __enter__(self) -> "APIClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close session."""
        self.close()
