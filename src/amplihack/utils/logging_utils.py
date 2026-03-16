"""Logging utilities for amplihack.

Philosophy:
- Ruthless simplicity: one decorator, zero config required
- Modular: drop-in decorator, no framework changes needed
- Zero-BS: DEBUG level by default — no noise unless you opt in
- Exception-safe: always re-raises, never swallows

Public API:
    log_call: Decorator that logs function entry, exit, and exceptions
    get_logger: Convenience wrapper for logging.getLogger(__name__)
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def log_call(func: F) -> F:
    """Decorator that logs function entry, exit, and exceptions at DEBUG level.

    Usage::

        from amplihack.utils.logging_utils import log_call

        @log_call
        def my_function(x, y):
            return x + y

    Logging output (when DEBUG is enabled)::

        DEBUG amplihack.module → my_function
        DEBUG amplihack.module ← my_function
        # or on exception:
        ERROR amplihack.module ✗ my_function raised
        Traceback ...

    Args:
        func: The function to wrap. Supports both sync and async functions.

    Returns:
        Wrapped function with entry/exit/exception logging.

    Notes:
        - Uses ``func.__module__`` as the logger name for consistent namespacing
        - Uses ``func.__qualname__`` for accurate nested/class method names
        - Fully transparent: preserves ``__name__``, ``__doc__``, ``__annotations__``
          via ``functools.wraps``
        - Async functions are wrapped with an async wrapper automatically
    """
    logger = logging.getLogger(func.__module__ or __name__)

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.debug("→ %s", func.__qualname__)
            try:
                result = await func(*args, **kwargs)
                logger.debug("← %s", func.__qualname__)
                return result
            except Exception:
                logger.exception("✗ %s raised", func.__qualname__)
                raise

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.debug("→ %s", func.__qualname__)
        try:
            result = func(*args, **kwargs)
            logger.debug("← %s", func.__qualname__)
            return result
        except Exception:
            logger.exception("✗ %s raised", func.__qualname__)
            raise

    return sync_wrapper  # type: ignore[return-value]


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper for logging.getLogger.

    Intended to be used at module level::

        logger = get_logger(__name__)

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A standard Python :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)


__all__ = ["log_call", "get_logger"]
