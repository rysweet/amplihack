"""HTTP client implementation with retry logic and error handling.

Philosophy:
- Single file, ~180 lines
- 3 exception classes only
- Async context manager pattern
- Exponential backoff inline (not separate class)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# EXCEPTIONS (3 classes)
# =============================================================================


class APIClientError(Exception):
    """Base exception for all API client errors."""


class NetworkError(APIClientError):
    """Connection, timeout, or DNS errors. Generally retriable."""


class HTTPError(APIClientError):
    """Non-2xx HTTP response."""

    def __init__(self, status_code: int, message: str, body: str = ""):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {message}")

    @property
    def is_retriable(self) -> bool:
        """429 and 5xx are retriable."""
        return self.status_code == 429 or self.status_code >= 500


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class Request:
    """HTTP request specification."""

    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    body: bytes | None = None


@dataclass
class Response:
    """HTTP response data."""

    status_code: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: float

    def json(self) -> Any:
        """Parse body as JSON."""
        return json.loads(self.body)

    def text(self) -> str:
        """Decode body as UTF-8 text."""
        return self.body.decode("utf-8")


# =============================================================================
# CLIENT
# =============================================================================


class APIClient:
    """HTTP client with retry logic and rate limiting.

    Usage:
        async with APIClient("https://api.example.com") as client:
            response = await client.get("/users")
            users = response.json()
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.default_headers,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(self, req: Request) -> Response:
        """Execute request with automatic retry on retriable errors."""
        if not self._client:
            raise APIClientError("Client not initialized. Use 'async with' context.")

        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._execute(req)
            except (NetworkError, HTTPError) as e:
                last_error = e
                if isinstance(e, HTTPError) and not e.is_retriable:
                    raise

                if attempt < self.max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)

        raise last_error  # type: ignore[misc]

    async def _execute(self, req: Request) -> Response:
        """Execute single request without retry."""
        merged_headers = {**self.default_headers, **req.headers}

        start = time.perf_counter()
        try:
            raw_response = await self._client.request(  # type: ignore[union-attr]
                method=req.method,
                url=req.path,
                headers=merged_headers,
                params=req.params or None,
                json=req.json_body,
                content=req.body,
            )
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}") from e
        except httpx.RequestError as e:
            raise NetworkError(f"Request failed: {e}") from e

        elapsed_ms = (time.perf_counter() - start) * 1000

        response = Response(
            status_code=raw_response.status_code,
            body=raw_response.content,
            headers=dict(raw_response.headers),
            elapsed_ms=elapsed_ms,
        )

        logger.debug(f"{req.method} {req.path} -> {response.status_code} ({elapsed_ms:.0f}ms)")

        if not raw_response.is_success:
            raise HTTPError(
                status_code=raw_response.status_code,
                message=raw_response.reason_phrase or "Unknown error",
                body=response.text() if response.body else "",
            )

        return response

    def _backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Delay doubles each attempt: 1s, 2s, 4s, 8s... capped at 30s.
        """
        return min(30.0, 2**attempt)

    # === Convenience Methods ===

    async def get(self, path: str, **kwargs: Any) -> Response:
        """Execute GET request."""
        return await self.request(Request("GET", path, **kwargs))

    async def post(self, path: str, **kwargs: Any) -> Response:
        """Execute POST request."""
        return await self.request(Request("POST", path, **kwargs))

    async def put(self, path: str, **kwargs: Any) -> Response:
        """Execute PUT request."""
        return await self.request(Request("PUT", path, **kwargs))

    async def delete(self, path: str, **kwargs: Any) -> Response:
        """Execute DELETE request."""
        return await self.request(Request("DELETE", path, **kwargs))
