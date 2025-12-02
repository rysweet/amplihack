"""Structured logging with header sanitization.

Philosophy:
- Never log sensitive headers in plaintext
- Structured logging for observability
- Auto-detection of sensitive patterns
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .models import APIRequest, APIResponse

logger = logging.getLogger(__name__)

SENSITIVE_HEADERS: frozenset[str] = frozenset(
    {
        # Note: "authorization" handled separately to preserve "Bearer " prefix
        "x-api-key",
        "x-auth-token",
        "api-key",
        "cookie",
        "set-cookie",
        "x-csrf-token",
        "x-access-token",
        "proxy-authorization",
    }
)

MASK_VALUE = "***MASKED***"
BEARER_PATTERN = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Sanitize headers by masking sensitive values."""
    sanitized = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_HEADERS:
            sanitized[key] = MASK_VALUE
        elif key_lower == "authorization" and value:
            sanitized[key] = BEARER_PATTERN.sub(rf"\1{MASK_VALUE}", value)
        elif any(s in key_lower for s in ("secret", "token", "key", "password")):
            sanitized[key] = MASK_VALUE
        else:
            sanitized[key] = value
    return sanitized


def log_request(
    request: APIRequest,
    level: int = logging.DEBUG,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log outgoing request with sanitized headers."""
    log_extra = {
        "request_id": request.request_id,
        "method": request.method.value,
        "url": request.url,
        "headers": sanitize_headers(request.headers),
        "has_body": request.body is not None,
    }
    if extra:
        log_extra.update(extra)
    logger.log(
        level,
        f"[{request.request_id}] {request.method.value} {request.url}",
        extra=log_extra,
    )


def log_response(
    response: APIResponse,
    level: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log incoming response with sanitized headers."""
    if level is None:
        level = logging.DEBUG if response.is_success else logging.WARNING
    log_extra = {
        "request_id": response.request_id,
        "status_code": response.status_code,
        "elapsed_ms": response.elapsed_ms,
        "retry_count": response.retry_count,
        "headers": sanitize_headers(response.headers),
    }
    if extra:
        log_extra.update(extra)
    logger.log(
        level,
        f"[{response.request_id}] Response: {response.status_code} ({response.elapsed_ms:.0f}ms)",
        extra=log_extra,
    )


__all__ = ["SENSITIVE_HEADERS", "MASK_VALUE", "sanitize_headers", "log_request", "log_response"]
