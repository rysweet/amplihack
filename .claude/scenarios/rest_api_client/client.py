"""Main REST API Client implementation.

This module provides the core APIClient class that handles HTTP requests,
retries, rate limiting, and error handling.
"""

import json
import logging
from urllib.parse import urljoin

import httpx

from .config import APIConfig
from .exceptions import (
    APIClientError,
    AuthenticationError,
    ConnectionError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models import Request, RequestMethod, Response
from .rate_limiter import RateLimiter
from .retry import ExponentialBackoff, RetryManager

logger = logging.getLogger(__name__)


class APIClient:
    """REST API Client with retry and rate limiting capabilities.

    This client provides a simple interface for making HTTP requests with
    automatic retry logic, rate limiting, and comprehensive error handling.

    Attributes:
        base_url: Base URL for all API requests
        timeout: Default timeout for requests
        headers: Default headers for all requests
        max_retries: Maximum number of retry attempts
    """

    def __init__(
        self,
        base_url: str | None = None,
        config: APIConfig | None = None,
        api_key: str | None = None,
        **kwargs,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for API requests
            config: APIConfig object with full configuration
            api_key: API key for authentication
            **kwargs: Additional configuration parameters
        """
        # Use config if provided, otherwise create from parameters
        if config:
            self._config = config
        else:
            # Merge provided parameters with defaults
            params = {"base_url": base_url or ""} | kwargs
            self._config = APIConfig(**params)

        # Set up authentication if api_key provided
        self._headers = dict(self._config.headers)
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

        # Initialize components
        self._session = httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
            verify=self._config.verify_ssl,
        )

        self._retry_manager = RetryManager(
            max_retries=self._config.max_retries,
            strategy=ExponentialBackoff(
                initial_delay=self._config.retry_delay, max_delay=self._config.max_retry_delay
            ),
        )

        self._rate_limiter = RateLimiter(
            strategy="token_bucket",
            capacity=self._config.rate_limit_calls,
            refill_rate=self._config.rate_limit_calls / self._config.rate_limit_period,
        )

    @property
    def base_url(self) -> str:
        """Get base URL."""
        return self._config.base_url

    @property
    def timeout(self) -> int:
        """Get timeout value."""
        return self._config.timeout

    @property
    def headers(self) -> dict[str, str]:
        """Get default headers."""
        return self._headers.copy()

    @property
    def max_retries(self) -> int:
        """Get max retries."""
        return self._config.max_retries

    def get(self, path: str, **kwargs) -> Response:
        """Make GET request.

        Args:
            path: Request path (appended to base_url)
            **kwargs: Additional request parameters

        Returns:
            Response object with results

        Raises:
            Various APIClientError subclasses on failure
        """
        return self._request(RequestMethod.GET, path, **kwargs)

    def post(self, path: str, **kwargs) -> Response:
        """Make POST request.

        Args:
            path: Request path
            **kwargs: Additional request parameters (json, data, etc.)

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses on failure
        """
        return self._request(RequestMethod.POST, path, **kwargs)

    def put(self, path: str, **kwargs) -> Response:
        """Make PUT request.

        Args:
            path: Request path
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses on failure
        """
        return self._request(RequestMethod.PUT, path, **kwargs)

    def delete(self, path: str, **kwargs) -> Response:
        """Make DELETE request.

        Args:
            path: Request path
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses on failure
        """
        return self._request(RequestMethod.DELETE, path, **kwargs)

    def patch(self, path: str, **kwargs) -> Response:
        """Make PATCH request.

        Args:
            path: Request path
            **kwargs: Additional request parameters

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses on failure
        """
        return self._request(RequestMethod.PATCH, path, **kwargs)

    def _request(self, method: RequestMethod, path: str, **kwargs) -> Response:
        """Internal method to make HTTP request.

        Args:
            method: HTTP method
            path: Request path
            **kwargs: Request parameters

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses
        """
        # Build full URL
        url = urljoin(self.base_url, path) if self.base_url else path

        # Merge headers
        headers = {**self._headers, **kwargs.pop("headers", {})}

        # Extract parameters
        params = kwargs.pop("params", {})
        json_data = kwargs.pop("json", None)
        data = kwargs.pop("data", None)
        timeout = kwargs.pop("timeout", self.timeout)

        # Create request object for logging
        request = Request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
            data=data,
            timeout=timeout,
        )

        logger.debug(f"Making {method.value} request to {url}")

        # Apply rate limiting
        self._rate_limiter.wait_if_needed()

        # Execute with retry
        def make_request():
            return self._execute_request(request)

        # Only retry on safe/idempotent methods or server errors
        if method in (RequestMethod.GET, RequestMethod.PUT, RequestMethod.DELETE):
            return self._retry_manager.execute(make_request)
        # POST and PATCH without retry (unless it's a server error)
        try:
            return make_request()
        except ServerError:
            # Server errors can be retried even for non-idempotent operations
            return self._retry_manager.execute(make_request)

    def _execute_request(self, request: Request) -> Response:
        """Execute single HTTP request.

        Args:
            request: Request object with all parameters

        Returns:
            Response object

        Raises:
            Various APIClientError subclasses
        """
        try:
            # Prepare request parameters
            request_kwargs = {
                "method": request.method.value,
                "url": request.url,
                "headers": request.headers,
                "params": request.params,
                "timeout": request.timeout,
            }

            if request.json is not None:
                request_kwargs["json"] = request.json
            elif request.data is not None:
                request_kwargs["data"] = request.data

            # Make request
            httpx_response = self._session.request(**request_kwargs)

            # Parse response
            response = self._parse_response(httpx_response, request.url)

            # Record rate limit response
            self._rate_limiter.record_response(response.status_code)

            # Handle errors
            if response.is_error:
                self._handle_error_response(response)

            return response

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise TimeoutError(f"Request timed out after {request.timeout} seconds")

        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise ConnectionError(f"Failed to connect to {request.url}")

        except Exception as e:
            if isinstance(e, APIClientError):
                raise
            logger.error(f"Unexpected error: {e}")
            raise APIClientError(f"Unexpected error: {e}")

    def _parse_response(self, httpx_response: httpx.Response, url: str) -> Response:
        """Parse httpx response into Response object.

        Args:
            httpx_response: Raw httpx response
            url: Request URL

        Returns:
            Response object
        """
        # Try to parse JSON
        json_data = None
        text = httpx_response.text

        if httpx_response.headers.get("content-type", "").startswith("application/json"):
            try:
                json_data = httpx_response.json()
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON response")

        return Response(
            status_code=httpx_response.status_code,
            headers=dict(httpx_response.headers),
            json=json_data,
            text=text,
            elapsed=httpx_response.elapsed.total_seconds(),
            url=str(httpx_response.url),
        )

    def _handle_error_response(self, response: Response) -> None:
        """Handle error responses by raising appropriate exceptions.

        Args:
            response: Response object with error status

        Raises:
            Appropriate APIClientError subclass
        """
        status_code = response.status_code
        error_data = response.json or {}
        error_message = error_data.get("error", response.text) or f"HTTP {status_code} error"

        if status_code == 400:
            # Check if it's a validation error
            if "fields" in error_data or "validation" in error_message.lower():
                field_errors = error_data.get("fields", {})
                raise ValidationError(error_message, field_errors=field_errors)
            raise HTTPError(error_message, status_code=400, response_body=error_data)

        if status_code == 401:
            raise AuthenticationError(error_message)

        if status_code == 404:
            raise NotFoundError(error_message, resource=None, resource_id=None)

        if status_code == 422:
            # Validation error (common in REST APIs)
            field_errors = error_data.get("fields", {})
            raise ValidationError(error_message, field_errors=field_errors)

        if status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise RateLimitError(error_message, retry_after=retry_after_int)

        if 500 <= status_code < 600:
            raise ServerError(error_message, status_code=status_code)

        raise HTTPError(error_message, status_code=status_code, response_body=error_data)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and close session."""
        self.close()
        return False


__all__ = ["APIClient"]
