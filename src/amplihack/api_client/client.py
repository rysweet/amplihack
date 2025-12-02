"""Core HTTP client with retry, rate limiting, and comprehensive error handling.

Philosophy:
- Async-first with context manager for resource cleanup
- Lazy session initialization for efficiency
- Automatic retry with exponential backoff
- Full type hints for IDE and mypy support

Pattern: Follows GitHubCopilotClient async context manager with lazy init.
"""

from __future__ import annotations

import asyncio
import logging
import time
import types
import uuid
from typing import Any, Self

from .exceptions import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)
from .logging import log_request, log_response
from .models import APIRequest, APIResponse, HTTPMethod, RetryConfig
from .rate_limiter import RateLimiter
from .retry import retry_async

logger = logging.getLogger(__name__)


class APIClient:
    """Async HTTP client with retry logic and rate limiting.

    Usage:
        async with APIClient(base_url="https://api.example.com") as client:
            response = await client.get("/users/123")

    Features:
        - Exponential backoff with jitter
        - Rate limit handling (429 + Retry-After)
        - Comprehensive exception hierarchy
        - Request/Response logging with header sanitization
    """

    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, str] | None = None,
        retry_config: RetryConfig | None = None,
        timeout: float = 30.0,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for all requests
            default_headers: Headers to include with every request
            retry_config: Retry behavior configuration
            timeout: Default request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.retry_config = retry_config or RetryConfig()
        self.timeout = timeout
        self._session: Any | None = None
        self._rate_limiter = RateLimiter()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit - cleanup session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is initialized (lazy init)."""
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                )
            except ImportError as e:
                raise RuntimeError(
                    "aiohttp required for APIClient. Install with: pip install aiohttp"
                ) from e

    async def request(
        self,
        method: HTTPMethod,
        path: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make HTTP request with retry and rate limiting."""
        await self._ensure_session()
        url = f"{self.base_url}{path}"
        request_id = str(uuid.uuid4())[:8]
        merged_headers = {**self.default_headers, **(headers or {})}
        effective_timeout = timeout or self.timeout

        request = APIRequest(
            method=method,
            url=url,
            headers=merged_headers,
            body=body,
            params=params,
            timeout=effective_timeout,
            request_id=request_id,
        )

        # Check rate limit
        wait_time = await self._rate_limiter.check_rate_limit(url)
        if wait_time:
            logger.warning(f"[{request_id}] Rate limited, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)

        log_request(request)
        start_time = time.monotonic()
        retry_count = 0

        async def make_request() -> APIResponse:
            nonlocal retry_count
            return await self._execute_request(request, retry_count)

        def should_retry(exc: Exception) -> bool:
            nonlocal retry_count
            retry_count += 1
            if isinstance(exc, RateLimitError):
                return True
            if isinstance(exc, APIClientError):
                status = exc.details.get("status_code")
                return status in self.retry_config.retry_on_status
            return False

        try:
            response = await retry_async(
                make_request,
                self.retry_config,
                should_retry=should_retry,
                request_id=request_id,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000
            final_response = APIResponse(
                status_code=response.status_code,
                headers=response.headers,
                body=response.body,
                elapsed_ms=elapsed_ms,
                request_id=request_id,
                retry_count=retry_count,
            )
            log_response(final_response)
            await self._rate_limiter.clear_rate_limit(url)
            return final_response
        except Exception as exc:
            if isinstance(exc, APIClientError):
                exc.request_id = request_id
            raise

    async def _execute_request(self, request: APIRequest, retry_count: int) -> APIResponse:
        """Execute single HTTP request."""
        import aiohttp

        try:
            async with self._session.request(
                request.method.value,
                request.url,
                headers=request.headers,
                json=request.body if request.body else None,
                params=request.params,
                timeout=aiohttp.ClientTimeout(total=request.timeout),
            ) as resp:
                try:
                    body: dict[str, Any] | str = await resp.json()
                except (aiohttp.ContentTypeError, ValueError):
                    body = await resp.text()

                if resp.status == 429:
                    retry_after = self._rate_limiter.parse_retry_after(dict(resp.headers))
                    wait_time = await self._rate_limiter.record_rate_limit(request.url, retry_after)
                    raise RateLimitError(
                        message=f"Rate limited by {request.url}",
                        retry_after=wait_time,
                        request_id=request.request_id,
                    )

                if resp.status >= 400:
                    raise APIClientError(
                        message=f"HTTP {resp.status}",
                        error_code=f"HTTP_{resp.status}",
                        details={"status_code": resp.status, "body": body},
                        request_id=request.request_id,
                    )

                return APIResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    body=body,
                    elapsed_ms=0,
                    request_id=request.request_id,
                    retry_count=retry_count,
                )

        except aiohttp.ClientConnectorError as exc:
            raise APIConnectionError(
                message=f"Connection failed: {exc}",
                host=request.url,
                request_id=request.request_id,
            ) from exc
        except TimeoutError as exc:
            raise APITimeoutError(
                message=f"Request timed out after {request.timeout}s",
                timeout=request.timeout,
                request_id=request.request_id,
            ) from exc

    async def get(self, path: str, **kwargs: Any) -> APIResponse:
        """GET request."""
        return await self.request(HTTPMethod.GET, path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> APIResponse:
        """POST request."""
        return await self.request(HTTPMethod.POST, path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> APIResponse:
        """PUT request."""
        return await self.request(HTTPMethod.PUT, path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> APIResponse:
        """PATCH request."""
        return await self.request(HTTPMethod.PATCH, path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> APIResponse:
        """DELETE request."""
        return await self.request(HTTPMethod.DELETE, path, **kwargs)


__all__ = ["APIClient"]
