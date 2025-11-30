"""REST API Client implementation.

Simple HTTP client with rate limiting and exponential backoff retry.
Uses only standard library for maximum portability.

Consolidated implementation merging best features from original
client and optimized versions with proper error handling.
"""

import json
import logging
import random
import threading
import time
from collections.abc import Iterator
from typing import Any
from urllib import error, parse, request

from .exceptions import (
    APIConnectionError,
    APITimeoutError,
    ConfigurationError,
    HTTPError,
    RateLimitError,
)
from .models import Request, Response

# Configure logging
logger = logging.getLogger(__name__)


class StreamingResponse:
    """Response that can stream large payloads without loading all into memory."""

    def __init__(self, status_code: int, headers: dict[str, str], response_obj, url: str):
        """Initialize streaming response.

        Args:
            status_code: HTTP status code
            headers: Response headers
            response_obj: The urllib response object for streaming
            url: Final URL after redirects
        """
        self.status_code = status_code
        self.headers = headers
        self.url = url
        self._response_obj = response_obj
        self._body_cache = None

    @property
    def body(self) -> bytes:
        """Get full response body (loads all into memory)."""
        if self._body_cache is None:
            self._body_cache = self._response_obj.read()
        return self._body_cache

    def json(self) -> Any:
        """Parse response body as JSON."""
        return json.loads(self.body.decode("utf-8"))

    @property
    def text(self) -> str:
        """Get response body as text."""
        return self.body.decode("utf-8")

    def iter_chunks(self, chunk_size: int = 8192) -> Iterator[bytes]:
        """Iterate over response in chunks.

        Args:
            chunk_size: Size of chunks to read

        Yields:
            Chunks of response body
        """
        while True:
            chunk = self._response_obj.read(chunk_size)
            if not chunk:
                break
            yield chunk


class APIClient:
    """REST API client with rate limiting and retry logic.

    Features:
    - All HTTP methods (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - Rate limiting with configurable requests per second
    - Exponential backoff retry with jitter for transient failures
    - HTTP/1.1 Keep-Alive for connection reuse
    - Optional streaming responses for large payloads
    - Custom exception hierarchy for clear error handling
    - Comprehensive logging throughout
    - Type hints for all methods
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        requests_per_second: float | None = None,
        raise_for_status: bool = True,
        use_keep_alive: bool = True,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for all API requests
            headers: Default headers to include in all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            requests_per_second: Rate limit (None = no limit)
            raise_for_status: If True, raise HTTPError for 4xx/5xx
            use_keep_alive: If True, use HTTP/1.1 Keep-Alive (default True)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not base_url:
            raise ConfigurationError("base_url is required")
        if max_retries < 0:
            raise ConfigurationError("max_retries must be non-negative")
        if requests_per_second is not None and requests_per_second <= 0:
            raise ConfigurationError("requests_per_second must be positive or None")

        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.raise_for_status = raise_for_status
        self.use_keep_alive = use_keep_alive

        # Rate limiting
        self.requests_per_second = requests_per_second
        self._last_request_time = 0.0
        self._rate_limit_lock = threading.Lock()

        logger.info(f"APIClient initialized for {base_url}")

    def _calculate_backoff(self, attempt: int, base: float = 2.0) -> float:
        """Calculate jittered exponential backoff delay.

        Args:
            attempt: Retry attempt number (0-based)
            base: Base for exponential calculation

        Returns:
            Delay in seconds with random jitter
        """
        # Base exponential delay: 2^attempt seconds
        delay = base**attempt

        # Add 0-25% random jitter to prevent thundering herd
        jitter = random.random() * 0.25
        delay *= 1 + jitter

        # Cap at 60 seconds
        return min(delay, 60.0)

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting by sleeping if necessary."""
        if self.requests_per_second is None:
            return

        with self._rate_limit_lock:
            current_time = time.time()
            min_interval = 1.0 / self.requests_per_second
            time_since_last = current_time - self._last_request_time

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _build_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        data: bytes | None = None,
    ) -> Request:
        """Build a Request object from parameters."""
        # Merge headers
        req_headers = self.headers.copy()

        # Add Keep-Alive header for connection reuse
        if self.use_keep_alive:
            req_headers["Connection"] = "keep-alive"

        if headers:
            req_headers.update(headers)

        # Handle query parameters
        if params:
            query_string = parse.urlencode(params)
            url = f"{url}?{query_string}"

        # Handle body data
        body = None
        if json_data is not None:
            body = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        elif data is not None:
            body = data

        return Request(method=method, url=url, headers=req_headers, body=body)

    def _execute(self, req: Request, stream: bool = False) -> Response | StreamingResponse:
        """Execute a single HTTP request without retry.

        Args:
            req: Request object to execute
            stream: If True, return StreamingResponse

        Returns:
            Response or StreamingResponse object

        Raises:
            HTTPError: For HTTP errors (4xx/5xx) if raise_for_status is True
            APITimeoutError: If request times out
            APIConnectionError: For connection failures
        """
        logger.debug(f"{req.method} {req.url}")

        try:
            # Create urllib request
            urllib_req = request.Request(
                req.url, data=req.body, headers=req.headers, method=req.method
            )

            # Execute request
            response_obj = request.urlopen(urllib_req, timeout=self.timeout)

            # Return appropriate response type
            if stream:
                resp = StreamingResponse(
                    status_code=response_obj.status,
                    headers=dict(response_obj.headers),
                    response_obj=response_obj,
                    url=response_obj.url,
                )
            else:
                with response_obj:
                    resp = Response(
                        status_code=response_obj.status,
                        headers=dict(response_obj.headers),
                        body=response_obj.read(),
                        url=response_obj.url,
                    )

            logger.info(f"{req.method} {req.url} -> {resp.status_code}")
            return resp

        except error.HTTPError as e:
            # Handle HTTP errors
            body = b""
            if e.fp:
                try:
                    body = e.fp.read()
                except Exception as read_error:
                    # Log the error but don't fail - body is optional
                    logger.debug(f"Could not read error response body: {read_error}")

            logger.warning(f"{req.method} {req.url} -> HTTP {e.code}")

            # Check for rate limiting
            if e.code == 429:
                retry_after = float(e.headers.get("Retry-After", 60))
                if self.raise_for_status:
                    raise RateLimitError(retry_after, body)
            elif self.raise_for_status and e.code >= 400:
                raise HTTPError(e.code, str(e.reason), body)

            # Return as Response if not raising
            return Response(
                status_code=e.code,
                headers=dict(e.headers) if e.headers else {},
                body=body,
                url=req.url,
            )

        except TimeoutError:
            logger.error(f"{req.method} {req.url} -> Timeout after {self.timeout}s")
            raise APITimeoutError(f"Request timed out after {self.timeout} seconds")

        except error.URLError as e:
            logger.error(f"{req.method} {req.url} -> Connection error: {e}")
            raise APIConnectionError(f"Connection failed: {e}")

    def _execute_with_retry(
        self, req: Request, stream: bool = False
    ) -> Response | StreamingResponse:
        """Execute request with exponential backoff retry.

        Args:
            req: Request object to execute
            stream: If True, return StreamingResponse

        Returns:
            Response or StreamingResponse object

        Raises:
            Last exception if all retries fail
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # Enforce rate limit
                self._enforce_rate_limit()

                # Try to execute
                response = self._execute(req, stream=stream)

                # Return successful response or client errors
                if isinstance(response, (Response, StreamingResponse)):
                    if response.status_code < 500:
                        return response

                    # Server error - might retry
                    if attempt < self.max_retries:
                        delay = self._calculate_backoff(attempt)
                        logger.info(
                            f"Server error {response.status_code}, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        last_error = HTTPError(
                            response.status_code,
                            "Server error",
                            response.body if isinstance(response, Response) else b"",
                        )
                        continue

                return response

            except (APIConnectionError, APITimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.info(
                        f"Transient error, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries}): {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded: {e}")
                    raise

            except RateLimitError as e:
                # Handle rate limit with Retry-After
                if attempt < self.max_retries and e.retry_after > 0:
                    # Use Retry-After header value, but cap at reasonable limit
                    wait_time = min(e.retry_after, 300)  # Cap at 5 minutes
                    logger.info(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                    last_error = e
                else:
                    raise

            except HTTPError:
                # Don't retry client errors (4xx)
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected error in retry logic")

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> Response | StreamingResponse:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            json: JSON data to send in body
            data: Raw bytes data (used if json is None)
            headers: Additional headers
            stream: If True, return StreamingResponse

        Returns:
            Response or StreamingResponse object

        Raises:
            HTTPError: For HTTP errors if raise_for_status is True
            APITimeoutError: If request times out after all retries
            APIConnectionError: For connection failures after all retries
        """
        # Build URL
        if path.startswith("http"):
            url = path  # Absolute URL
        elif path.startswith("/"):
            url = f"{self.base_url}{path}"
        else:
            url = f"{self.base_url}/{path}"

        # Build and execute request
        req = self._build_request(method, url, headers, params, json, data)
        return self._execute_with_retry(req, stream=stream)

    def get(self, path: str, **kwargs) -> Response:
        """Make GET request."""
        return self.request("GET", path, **kwargs)

    def get_stream(self, path: str, **kwargs) -> StreamingResponse:
        """Make GET request with streaming response."""
        kwargs["stream"] = True
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Response:
        """Make POST request."""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> Response:
        """Make PUT request."""
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> Response:
        """Make DELETE request."""
        return self.request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> Response:
        """Make PATCH request."""
        return self.request("PATCH", path, **kwargs)

    def head(self, path: str, **kwargs) -> Response:
        """Make HEAD request."""
        return self.request("HEAD", path, **kwargs)

    def options(self, path: str, **kwargs) -> Response:
        """Make OPTIONS request."""
        return self.request("OPTIONS", path, **kwargs)


# Backward compatibility aliases
RESTClient = APIClient
OptimizedRESTClient = APIClient
