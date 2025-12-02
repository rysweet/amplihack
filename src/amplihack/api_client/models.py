"""Data models for the API Client module.

Philosophy:
- Immutable data structures for thread safety and predictability
- Frozen dataclasses prevent accidental mutation of dataclass fields
- Clear type hints for IDE support and mypy compliance

Note on Immutability:
    Frozen dataclasses provide SHALLOW immutability - the dataclass fields
    cannot be reassigned, but mutable objects within (like dicts) can still
    be modified. For most use cases this is sufficient since headers/body
    are typically not modified after request creation.

Public API (the "studs"):
    HTTPMethod: Enum of supported HTTP methods
    RetryConfig: Configuration for retry behavior
    APIRequest: Immutable request representation
    APIResponse: Immutable response representation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HTTPMethod(Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""

    max_attempts: int = 3
    base_delay: float = 1.0
    multiplier: float = 2.0
    max_delay: float = 60.0
    jitter: float = 0.1
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass(frozen=True)
class APIRequest:
    """Immutable HTTP request representation."""

    method: HTTPMethod
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    params: dict[str, str] | None = None
    timeout: float = 30.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass(frozen=True)
class APIResponse:
    """Immutable HTTP response representation."""

    status_code: int
    headers: dict[str, str]
    body: dict[str, Any] | str
    elapsed_ms: float
    request_id: str
    retry_count: int = 0

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429


__all__ = ["HTTPMethod", "RetryConfig", "APIRequest", "APIResponse"]
