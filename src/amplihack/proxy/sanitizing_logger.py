"""
Sanitizing Logger Wrapper

Automatically sanitizes sensitive credentials from all log messages.

Philosophy:
- Security by default: All logs automatically sanitized
- Drop-in replacement: Compatible with standard Python logging
- Zero-BS: No configuration needed, works out of the box

Public API:
    get_sanitizing_logger: Get a logger that auto-sanitizes

Created to address Issue #1997: API Keys Logged in Plain Text
"""

import logging
from typing import Any

from .token_sanitizer import TokenSanitizer


class SanitizingLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically sanitizes sensitive data.

    Drop-in replacement for standard logger that ensures no credentials
    are leaked in log messages.
    """

    def process(self, msg: Any, kwargs: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        """
        Process log message to sanitize sensitive data.

        Args:
            msg: Log message (will be sanitized)
            kwargs: Additional keyword arguments

        Returns:
            Tuple of (sanitized_msg, kwargs)
        """
        # Sanitize the message
        if isinstance(msg, str):
            sanitized_msg = TokenSanitizer.sanitize(msg)
        else:
            # Convert to string and sanitize
            sanitized_msg = TokenSanitizer.sanitize(str(msg))

        # Sanitize extra dict if present
        if "extra" in kwargs and isinstance(kwargs["extra"], dict):
            kwargs["extra"] = TokenSanitizer.sanitize_dict(kwargs["extra"])

        return sanitized_msg, kwargs

    # Expose common logger attributes for drop-in replacement compatibility
    @property
    def handlers(self):
        """Access underlying logger handlers."""
        return self.logger.handlers

    @property
    def level(self):
        """Access underlying logger level."""
        return self.logger.level

    def addFilter(self, filter):
        """Add filter to underlying logger."""
        return self.logger.addFilter(filter)

    def removeFilter(self, filter):
        """Remove filter from underlying logger."""
        return self.logger.removeFilter(filter)

    def setLevel(self, level):
        """Set level on underlying logger."""
        return self.logger.setLevel(level)


def get_sanitizing_logger(name: str) -> SanitizingLoggerAdapter:
    """
    Get a logger that automatically sanitizes sensitive data.

    This is a drop-in replacement for logging.getLogger() that ensures
    all log messages are sanitized before being written.

    Args:
        name: Logger name (typically __name__)

    Returns:
        SanitizingLoggerAdapter that wraps standard logger

    Example:
        # Instead of:
        # logger = logging.getLogger(__name__)

        # Use:
        from amplihack.proxy.sanitizing_logger import get_sanitizing_logger
        logger = get_sanitizing_logger(__name__)

        # Now all logs are automatically sanitized:
        logger.debug(f"API key: {api_key}")  # Credentials redacted automatically
    """
    base_logger = logging.getLogger(name)
    return SanitizingLoggerAdapter(base_logger, {})


__all__ = ["get_sanitizing_logger", "SanitizingLoggerAdapter"]
