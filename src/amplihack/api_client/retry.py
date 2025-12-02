"""Retry logic with exponential backoff and jitter.

Philosophy:
- Exponential backoff prevents thundering herd
- Jitter adds randomness to spread out retries
- Configurable behavior via RetryConfig
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .exceptions import RetryExhaustedError
from .models import RetryConfig

logger = logging.getLogger(__name__)
T = TypeVar("T")


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay with exponential backoff and jitter.

    Formula: min(max_delay, base_delay * (multiplier ^ attempt) * (1 + random(-jitter, +jitter)))
    """
    base = config.base_delay * (config.multiplier**attempt)
    if config.jitter > 0:
        jitter_factor = 1 + random.uniform(-config.jitter, config.jitter)
        base = base * jitter_factor
    return min(config.max_delay, max(0, base))


async def retry_async(
    func: Callable[[], Awaitable[T]],
    config: RetryConfig,
    should_retry: Callable[[Exception], bool] | None = None,
    on_retry: Callable[[Exception, int, float], Any] | None = None,
    request_id: str | None = None,
) -> T:
    """Execute async function with retry logic."""
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        try:
            return await func()
        except Exception as exc:
            last_exception = exc
            if should_retry is not None and not should_retry(exc):
                raise
            if attempt == config.max_attempts - 1:
                break
            delay = calculate_delay(attempt, config)
            if on_retry is not None:
                on_retry(exc, attempt + 1, delay)
            logger.info(f"[{request_id}] Retry {attempt + 1} after {delay:.2f}s: {exc}")
            await asyncio.sleep(delay)

    raise RetryExhaustedError(
        message=f"Operation failed after {config.max_attempts} attempts",
        attempts=config.max_attempts,
        last_error=str(last_exception) if last_exception else None,
        request_id=request_id,
    )


__all__ = ["calculate_delay", "retry_async"]
