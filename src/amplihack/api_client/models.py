"""Data models for the API client.

Immutable dataclasses for requests, responses, and configuration.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar
from urllib.parse import urlparse

from .exceptions import ValidationError

T = TypeVar("T")


@dataclass(frozen=True)
class ErrorDetail:
    """Detail about a specific error."""

    code: str | None = None
    field: str | None = None
    message: str | None = None
    value: Any | None = None


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_statuses: frozenset = field(default_factory=lambda: frozenset({429, 502, 503, 504}))

    def __post_init__(self):
        """Validate configuration."""
        if self.max_retries < 0:
            raise ValidationError("max_retries must be non-negative")
        if self.initial_delay <= 0:
            raise ValidationError("initial_delay must be positive")
        if self.max_delay <= 0:
            raise ValidationError("max_delay must be positive")
        if self.exponential_base <= 1:
            raise ValidationError("exponential_base must be greater than 1")


@dataclass
class APIConfig:
    """Configuration for the API client."""

    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0
    max_retry_delay: float = 60.0
    headers: dict[str, str] = field(default_factory=dict)
    user_agent: str = "amplihack/1.0.0"
    verify_ssl: bool = True
    proxy: str | None = None
    follow_redirects: bool = True
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate configuration."""
        # Validate URL
        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid base URL: {self.base_url} - must include scheme and host")

        # Validate timeout
        if self.timeout <= 0:
            raise ValidationError("Timeout must be positive")

        # Validate retries
        if self.max_retries < 0:
            raise ValidationError("max_retries must be non-negative")

        # Validate log level
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValidationError(f"Invalid log_level: {self.log_level} - must be one of {valid_levels}")

        # Ensure base_url doesn't end with slash
        if self.base_url.endswith("/"):
            object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

        # Set default user agent if not provided
        if not self.user_agent:
            object.__setattr__(self, "user_agent", "amplihack/1.0.0")

    def copy_with(self, **kwargs) -> "APIConfig":
        """Create a copy of config with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New APIConfig instance with updates
        """
        current = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "retry_multiplier": self.retry_multiplier,
            "max_retry_delay": self.max_retry_delay,
            "headers": self.headers.copy(),
            "user_agent": self.user_agent,
            "verify_ssl": self.verify_ssl,
            "proxy": self.proxy,
            "follow_redirects": self.follow_redirects,
            "log_level": self.log_level,
        }

        # Merge headers if provided
        if "headers" in kwargs:
            new_headers = current["headers"].copy()
            new_headers.update(kwargs["headers"])
            kwargs["headers"] = new_headers

        current.update(kwargs)
        return APIConfig(**current)


@dataclass(frozen=True)
class Request:
    """Immutable request representation."""

    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] | None = None
    json_data: Any | None = None
    data: Any | None = None
    timeout: float = 30.0


@dataclass
class Response(Generic[T]):
    """Type-safe response wrapper."""

    status_code: int
    headers: dict[str, str]
    data: T | None
    request: Request
    raw_text: str = ""
    elapsed: timedelta = field(default_factory=lambda: timedelta(seconds=0))

    @property
    def is_success(self) -> bool:
        """Check if response indicates success (2xx status)."""
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        """Check if response indicates error (4xx or 5xx)."""
        return self.status_code >= 400

    def json(self) -> Any:
        """Parse response as JSON.

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If response is not valid JSON
        """
        if not self.raw_text:
            return None
        try:
            return json.loads(self.raw_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")


@dataclass
class RateLimitInfo:
    """Information about rate limiting."""

    limit: int | None = None  # Requests per window
    remaining: int | None = None  # Requests remaining
    reset: datetime | None = None  # When window resets
    retry_after: int | None = None  # Seconds to wait
