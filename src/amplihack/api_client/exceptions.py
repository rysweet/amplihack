"""Exception hierarchy for the API Client module.

Philosophy:
- Rich exceptions with actionable context for debugging
- Structured error_code for programmatic handling
- Recovery suggestions guide users to solutions
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class APIClientError(Exception):
    """Base exception for all API client errors."""

    message: str
    error_code: str = "API_ERROR"
    details: dict[str, Any] = field(default_factory=dict)
    recovery_suggestion: str | None = None
    request_id: str | None = None
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "recovery_suggestion": self.recovery_suggestion,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RateLimitError(APIClientError):
    """Rate limit exceeded - includes retry timing."""

    retry_after: int = 60

    def __post_init__(self) -> None:
        self.error_code = "RATE_LIMIT_EXCEEDED"
        self.details["retry_after_seconds"] = self.retry_after
        self.recovery_suggestion = f"Wait {self.retry_after} seconds before retrying."
        super().__post_init__()


@dataclass
class RetryExhaustedError(APIClientError):
    """All retry attempts failed."""

    attempts: int = 0
    last_error: str | None = None

    def __post_init__(self) -> None:
        self.error_code = "RETRY_EXHAUSTED"
        self.details["attempts"] = self.attempts
        if self.last_error:
            self.details["last_error"] = self.last_error
        self.recovery_suggestion = "Check network connectivity and API availability."
        super().__post_init__()


@dataclass
class APIConnectionError(APIClientError):
    """Network connectivity failure.

    Named APIConnectionError to avoid shadowing builtins.ConnectionError.
    """

    host: str = ""
    port: int | None = None

    def __post_init__(self) -> None:
        self.error_code = "CONNECTION_FAILED"
        self.details["host"] = self.host
        if self.port:
            self.details["port"] = self.port
        self.recovery_suggestion = "Check network connectivity and endpoint URL."
        super().__post_init__()


@dataclass
class APITimeoutError(APIClientError):
    """Request timed out.

    Named APITimeoutError to avoid shadowing builtins.TimeoutError.
    """

    timeout: float = 0.0
    operation: str = "request"

    def __post_init__(self) -> None:
        self.error_code = "TIMEOUT"
        self.details["timeout_seconds"] = self.timeout
        self.details["operation"] = self.operation
        self.recovery_suggestion = "Increase timeout or check endpoint response time."
        super().__post_init__()


__all__ = [
    "APIClientError",
    "RateLimitError",
    "RetryExhaustedError",
    "APIConnectionError",
    "APITimeoutError",
]
