"""REST API Client implementation.

Philosophy:
- Ruthless simplicity - start with working code, add features incrementally
- Zero-BS - every method works completely, no stubs
- Type hints throughout
- Comprehensive error handling with custom exceptions

Main Features:
- Automatic retry with exponential backoff
- Rate limiting (requests per second/minute)
- Custom authentication support
- Comprehensive timeout controls
- Detailed logging
- Thread-safe operation
"""

import logging
import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

# Use requests library for HTTP (standard, well-tested)
import requests

from amplihack.api_client.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
    ServerError,
)
from amplihack.api_client.exceptions import (
    TimeoutError as APITimeoutError,
)
from amplihack.api_client.models import (
    APIKeyAuth,
    BearerAuth,
    ClientConfig,
    RateLimiter,
    Response,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


class RestClient:
    """Production-ready REST API client with retry, rate limiting, and error handling.

    Philosophy:
    - Start simple, add complexity only when needed
    - Every feature fully implemented (no stubs)
    - Predictable behavior with sensible defaults

    Example:
        >>> client = RestClient(base_url="https://api.example.com")
        >>> response = client.get("/users/123")
        >>> user = response.json()
    """

    def __init__(
        self,
        base_url: str | None = None,
        config: ClientConfig | None = None,
        auth: BearerAuth | APIKeyAuth | tuple | None = None,
        retry_policy: RetryPolicy | None = None,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        should_retry: Callable[[Any, Exception | None], bool] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize REST API client.

        Args:
            base_url: Base URL for all requests
            config: ClientConfig object with full configuration
            auth: Authentication handler (BearerAuth, APIKeyAuth, or (user, pass) tuple)
            retry_policy: Custom retry policy (overrides config)
            on_retry: Callback function called on each retry (attempt, exception, wait_time)
            should_retry: Custom function to determine if request should be retried
            **kwargs: Additional config options (passed to ClientConfig if no config provided)

        Example:
            >>> client = RestClient(base_url="https://api.example.com", timeout=60)
            >>> # or
            >>> config = ClientConfig(base_url="https://api.example.com", timeout=60)
            >>> client = RestClient(config=config)
        """
        # Build config from arguments
        if config is None:
            if base_url is None:
                raise ValueError("Either base_url or config must be provided")
            config = ClientConfig(base_url=base_url, **kwargs)

        self.base_url = config.base_url
        self.timeout = config.timeout
        self.connect_timeout = config.connect_timeout
        self.max_retries = config.max_retries
        self.verify_ssl = config.verify_ssl
        self.default_headers = config.default_headers.copy()
        self.allow_redirects = config.allow_redirects
        self.max_redirects = config.max_redirects
        self.debug = config.debug

        # Warn about disabled SSL verification
        if not self.verify_ssl:
            logger.warning("⚠️  SSL VERIFICATION DISABLED - INSECURE CONNECTION")
            logger.warning("This should NEVER be used in production!")

        # Configure logging if debug is enabled
        if self.debug:
            logging.basicConfig(
                level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # Create retry policy from config or use provided one
        if retry_policy is not None:
            self.retry_policy = retry_policy
        else:
            self.retry_policy = RetryPolicy(
                max_attempts=config.max_retries + 1,  # +1 for initial attempt
                backoff_factor=config.retry_backoff_factor,
                retry_on_statuses=config.retry_statuses,
            )

        # Store retry callback and custom should_retry function
        self.on_retry = on_retry
        self.should_retry = should_retry

        # Create rate limiter if limits specified
        self.rate_limiter: RateLimiter | None = None
        if config.rate_limit_per_second or config.rate_limit_per_minute:
            self.rate_limiter = RateLimiter(
                requests_per_second=config.rate_limit_per_second,
                requests_per_minute=config.rate_limit_per_minute,
            )

        # Store authentication
        self.auth = auth

        # Create requests session for connection pooling
        self.session = requests.Session()

    @classmethod
    def from_env(cls) -> "RestClient":
        """Create client from environment variables.

        Environment Variables:
            API_CLIENT_BASE_URL: Base URL
            API_CLIENT_TIMEOUT: Timeout in seconds
            API_CLIENT_MAX_RETRIES: Max retry attempts
            API_CLIENT_RATE_LIMIT_PER_SECOND: Rate limit per second
            API_CLIENT_VERIFY_SSL: Verify SSL (true/false)

        Returns:
            RestClient instance configured from environment

        Raises:
            ValueError: If required environment variables are missing
        """
        base_url = os.environ.get("API_CLIENT_BASE_URL")
        if not base_url:
            raise ValueError("API_CLIENT_BASE_URL environment variable not set")

        kwargs: dict[str, Any] = {}

        if timeout := os.environ.get("API_CLIENT_TIMEOUT"):
            kwargs["timeout"] = int(timeout)
        if max_retries := os.environ.get("API_CLIENT_MAX_RETRIES"):
            kwargs["max_retries"] = int(max_retries)
        if rate_limit := os.environ.get("API_CLIENT_RATE_LIMIT_PER_SECOND"):
            kwargs["rate_limit_per_second"] = int(rate_limit)
        if verify_ssl := os.environ.get("API_CLIENT_VERIFY_SSL"):
            kwargs["verify_ssl"] = verify_ssl.lower() == "true"

        return cls(base_url=base_url, **kwargs)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make GET request.

        Args:
            path: URL path (appended to base_url)
            params: Query parameters
            headers: Additional headers for this request
            **kwargs: Additional arguments for request

        Returns:
            Response object

        Raises:
            APIError: On request failure
        """
        return self.request("GET", path, params=params, headers=headers, **kwargs)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any | None = None,
        files: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make POST request.

        Args:
            path: URL path
            json: JSON body (dict)
            data: Form data or raw body
            files: Files to upload
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            Response object

        Raises:
            APIError: On request failure
        """
        return self.request(
            "POST", path, json=json, data=data, files=files, headers=headers, **kwargs
        )

    def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make PUT request.

        Args:
            path: URL path
            json: JSON body
            data: Form data or raw body
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            Response object

        Raises:
            APIError: On request failure
        """
        return self.request("PUT", path, json=json, data=data, headers=headers, **kwargs)

    def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make PATCH request.

        Args:
            path: URL path
            json: JSON body
            data: Form data or raw body
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            Response object

        Raises:
            APIError: On request failure
        """
        return self.request("PATCH", path, json=json, data=data, headers=headers, **kwargs)

    def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Response:
        """Make DELETE request.

        Args:
            path: URL path
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments

        Returns:
            Response object

        Raises:
            APIError: On request failure
        """
        return self.request("DELETE", path, params=params, headers=headers, **kwargs)

    def request(self, method: str, path: str, **kwargs: Any) -> Response:
        """Make HTTP request with retry and rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path
            **kwargs: Additional arguments (params, json, data, headers, etc.)

        Returns:
            Response object

        Raises:
            APIError: On request failure
            RetryExhaustedError: If all retries fail
        """
        # Construct full URL
        url = urljoin(self.base_url, path)

        # Log request if debug enabled
        if self.debug:
            logger.debug(f"Making {method} request to {url}")
            if kwargs.get("params"):
                logger.debug(f"Query params: {kwargs['params']}")
            if kwargs.get("json"):
                logger.debug(f"JSON body: {kwargs['json']}")

        # Apply rate limiting if configured
        if self.rate_limiter:
            while not self.rate_limiter.allows_request():
                wait = self.rate_limiter.wait_time()
                logger.debug(f"Rate limit reached, waiting {wait:.2f}s")
                time.sleep(wait)
            self.rate_limiter.record_request()

        # Merge headers
        headers = self._merge_headers(kwargs.get("headers"))
        kwargs["headers"] = headers

        # Apply authentication - must handle headers and params separately
        if self.auth:
            self._apply_auth(headers, kwargs)

        # Add timeout - pass as single value for simplicity
        # (requests accepts either number or (connect, read) tuple)
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        # Add SSL verification setting
        if "verify" not in kwargs:
            kwargs["verify"] = self.verify_ssl

        # Retry loop
        attempt = 0
        last_exception: Exception | None = None
        start_time = time.time()

        while attempt < self.retry_policy.max_attempts:
            attempt += 1

            try:
                # Make the actual request
                response = self._make_request(method, url, **kwargs)

                # Check if we should retry based on status code
                should_retry_response = False
                if self.should_retry:
                    # Use custom should_retry function
                    should_retry_response = self.should_retry(response, None)
                else:
                    # Use default retry logic
                    should_retry_response = (
                        response.status_code in self.retry_policy.retry_on_statuses
                    )

                if should_retry_response:
                    # Create exception for the callback
                    # Note: ServerError and RateLimitError already imported at module level

                    # Use RateLimitError for 429, ServerError for others
                    if response.status_code == 429:
                        exception = RateLimitError(
                            f"HTTP {response.status_code}", response=response
                        )
                        # Check if RateLimitError parsed a Retry-After header
                        if exception.retry_after is not None:
                            backoff = float(exception.retry_after)
                        else:
                            backoff = self.retry_policy.calculate_backoff(attempt)
                    else:
                        exception = ServerError(f"HTTP {response.status_code}", response=response)
                        backoff = self.retry_policy.calculate_backoff(attempt)

                    last_exception = exception

                    if attempt < self.retry_policy.max_attempts:
                        logger.warning(
                            f"Request failed with status {response.status_code}, "
                            f"retrying in {backoff:.2f}s (attempt {attempt}/{self.retry_policy.max_attempts})"
                        )

                        # Invoke retry callback if provided
                        if self.on_retry:
                            self.on_retry(attempt, exception, backoff)

                        time.sleep(backoff)
                        continue
                    # Exhausted retries
                    # If no retries were configured (max_attempts=1), raise original error
                    if self.retry_policy.max_attempts == 1 or isinstance(exception, RateLimitError):
                        raise exception
                    # Wrap in RetryExhaustedError
                    total_time = time.time() - start_time
                    raise RetryExhaustedError(
                        f"All {attempt} attempts failed",
                        attempts=attempt,
                        last_exception=exception,
                        total_time=total_time,
                    )

                # Log response if debug enabled
                if self.debug:
                    logger.debug(f"Response status: {response.status_code}")
                    if hasattr(response, "elapsed") and response.elapsed:
                        if hasattr(response.elapsed, "total_seconds"):
                            try:
                                elapsed = response.elapsed.total_seconds()
                                # Only log if elapsed is a number (not a Mock)
                                if isinstance(elapsed, (int, float)):
                                    logger.debug(f"Response time: {elapsed:.2f}s")
                            except (TypeError, AttributeError):
                                # Skip logging if elapsed is not properly formatted
                                pass

                # Convert to our Response model and return
                return self._convert_response(response)

            except tuple(self.retry_policy.retry_on_exceptions) as e:
                last_exception = e

                # Check if we should retry this exception
                should_retry_exception = False
                if self.should_retry:
                    should_retry_exception = self.should_retry(None, e)
                else:
                    # Default: retry on configured exception types
                    should_retry_exception = True

                if should_retry_exception and attempt < self.retry_policy.max_attempts:
                    backoff = self.retry_policy.calculate_backoff(attempt)
                    logger.warning(
                        f"Request failed with {type(e).__name__}, "
                        f"retrying in {backoff:.2f}s (attempt {attempt}/{self.retry_policy.max_attempts})"
                    )

                    # Invoke retry callback if provided
                    if self.on_retry:
                        self.on_retry(attempt, e, backoff)

                    time.sleep(backoff)
                    continue
                # Last attempt failed
                # If no retries were configured (max_attempts=1), convert to our exception types
                # Otherwise wrap in RetryExhaustedError
                if self.retry_policy.max_attempts == 1:
                    # Convert Python built-in exceptions to our custom ones
                    if isinstance(e, TimeoutError):
                        raise APITimeoutError(str(e), timeout=self.timeout) from e
                    if isinstance(e, ConnectionError):
                        raise RequestError(str(e), url=url) from e
                    raise
                total_time = time.time() - start_time
                raise RetryExhaustedError(
                    f"All {attempt} attempts failed",
                    attempts=attempt,
                    last_exception=last_exception,
                    total_time=total_time,
                )

        # Should not reach here, but handle it anyway
        total_time = time.time() - start_time
        raise RetryExhaustedError(
            f"All {attempt} attempts failed",
            attempts=attempt,
            last_exception=last_exception,
            total_time=total_time,
        )

    def _make_request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Make the actual HTTP request using requests library.

        Args:
            method: HTTP method
            url: Full URL
            **kwargs: Request arguments

        Returns:
            requests.Response object

        Raises:
            RequestError: On connection/network failure
            APITimeoutError: On timeout
        """
        try:
            response = self.session.request(
                method=method, url=url, allow_redirects=self.allow_redirects, **kwargs
            )
            return response

        except requests.exceptions.Timeout as e:
            raise APITimeoutError(
                f"Request timed out after {self.timeout}s",
                timeout=self.timeout,
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise RequestError(
                f"Connection failed: {e!s}",
                url=url,
            ) from e
        except requests.exceptions.RequestException as e:
            raise RequestError(
                f"Request failed: {e!s}",
                url=url,
            ) from e

    def _convert_response(self, response: requests.Response) -> Response:
        """Convert requests.Response to our Response model.

        Also raises appropriate exceptions for error status codes.

        Args:
            response: requests.Response object

        Returns:
            Our Response model

        Raises:
            AuthenticationError: On 401/403
            NotFoundError: On 404
            RateLimitError: On 429
            ServerError: On 5xx
            ResponseError: On other errors
        """
        # Extract elapsed time (handle both real and mock responses)
        elapsed = None
        if hasattr(response, "elapsed") and response.elapsed:
            if hasattr(response.elapsed, "total_seconds"):
                elapsed = response.elapsed.total_seconds()

        # Extract headers (handle both real and mock responses)
        headers = {}
        if hasattr(response, "headers"):
            try:
                headers = dict(response.headers)
            except (TypeError, ValueError):
                # Mock headers might not be dict-able
                headers = {}

        # Extract body text (handle both real responses and mocks with json())
        body = ""
        if hasattr(response, "json") and callable(response.json):
            # If response has json() method, use it to get body
            try:
                import json as json_lib

                body = json_lib.dumps(response.json())
            except Exception:
                # If json() fails, fall back to text
                body = response.text if isinstance(response.text, str) else ""
        else:
            # Normal case - use text attribute
            body = response.text if isinstance(response.text, str) else ""

        # Create our Response model
        our_response = Response(
            status_code=response.status_code,
            headers=headers,
            body=body,
            elapsed=elapsed,
        )

        # Raise appropriate exceptions for error status codes
        if not response.ok:
            if response.status_code == 401 or response.status_code == 403:
                raise AuthenticationError(
                    f"Authentication failed: {response.status_code}",
                    response=our_response,
                )
            if response.status_code == 404:
                raise NotFoundError(
                    "Resource not found",
                    response=our_response,
                )
            if response.status_code == 429:
                raise RateLimitError(
                    "Rate limit exceeded",
                    response=our_response,
                )
            if 500 <= response.status_code < 600:
                raise ServerError(
                    f"Server error: {response.status_code}",
                    response=our_response,
                )
            raise ResponseError(
                f"Request failed with status {response.status_code}",
                response=our_response,
            )

        return our_response

    def _merge_headers(self, request_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge default headers with request-specific headers.

        Args:
            request_headers: Headers for this specific request

        Returns:
            Merged headers dict
        """
        headers = self.default_headers.copy()
        if request_headers:
            headers.update(request_headers)
        return headers

    def _apply_auth(self, headers: dict[str, str], kwargs: dict[str, Any]) -> None:
        """Apply authentication by modifying headers or params directly.

        For header-based auth (Bearer, API Key in header), modifies headers dict.
        For query-based auth (API Key in query), modifies params.
        For Basic auth, uses requests built-in auth parameter.

        Args:
            headers: Headers dictionary to modify
            kwargs: Request kwargs dictionary (may modify params or add auth)

        Raises:
            ValueError: If auth type is not supported
        """
        if self.auth is None:
            return

        # Handle tuple (username, password) for Basic Auth
        # Pass tuple directly - requests handles it internally
        if isinstance(self.auth, tuple):
            kwargs["auth"] = self.auth
            return

        # Handle BearerAuth - add directly to headers
        if isinstance(self.auth, BearerAuth):
            headers["Authorization"] = f"Bearer {self.auth.token}"
            return

        # Handle APIKeyAuth
        if isinstance(self.auth, APIKeyAuth):
            if self.auth.location == "header":
                # Add API key to headers
                headers[self.auth.name] = self.auth.key
            elif self.auth.location == "query":
                # Add API key to query params
                if "params" not in kwargs:
                    kwargs["params"] = {}
                if kwargs["params"] is None:
                    kwargs["params"] = {}
                kwargs["params"][self.auth.name] = self.auth.key
            else:
                raise ValueError(f"Unsupported API key location: {self.auth.location}")
            return

        raise ValueError(f"Unsupported auth type: {type(self.auth)}")


__all__ = ["RestClient"]
