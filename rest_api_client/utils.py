"""Utilities for the REST API client.

Contains logging setup and session management helpers.
"""

import json
import logging
import sys
import uuid
import warnings
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry as URLLibRetry  # type: ignore[import-untyped]

# =============================================================================
# Logging Utilities
# =============================================================================


class RequestIDFilter(logging.Filter):
    """Adds request ID to log records for tracking."""

    def __init__(self) -> None:
        """Initialize the filter with a thread-local storage for request IDs."""
        super().__init__()
        self._request_id: str | None = None

    def set_request_id(self, request_id: str | None = None) -> str:
        """Set or generate a request ID.

        Args:
            request_id: Optional request ID to use

        Returns:
            The request ID that was set
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        self._request_id = request_id
        return request_id

    def get_request_id(self) -> str | None:
        """Get the current request ID."""
        return self._request_id

    def clear_request_id(self) -> None:
        """Clear the current request ID."""
        self._request_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to the log record.

        Args:
            record: The log record to modify

        Returns:
            True to allow the record to be logged
        """
        record.request_id = self._request_id or "no-request-id"  # type: ignore
        return True


class StructuredFormatter(logging.Formatter):
    """Formats logs as structured JSON for better parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "no-request-id"),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "request_id",
                "getMessage",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class APIClientLogger:
    """Logger setup for the API client."""

    def __init__(self, name: str = "rest_api_client", level: str = "INFO") -> None:
        """Initialize the logger.

        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create console handler with structured formatter
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())

        # Add request ID filter
        self.request_id_filter = RequestIDFilter()
        handler.addFilter(self.request_id_filter)

        self.logger.addHandler(handler)

    def set_request_id(self, request_id: str | None = None) -> str:
        """Set or generate a request ID for tracking.

        Args:
            request_id: Optional request ID to use

        Returns:
            The request ID that was set
        """
        return self.request_id_filter.set_request_id(request_id)

    def get_request_id(self) -> str | None:
        """Get the current request ID."""
        return self.request_id_filter.get_request_id()

    def clear_request_id(self) -> None:
        """Clear the current request ID."""
        self.request_id_filter.clear_request_id()

    def log_request(self, method: str, url: str, **kwargs: Any) -> None:
        """Log an outgoing request.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional context to log
        """
        self.logger.info(
            "Sending request",
            extra={"event": "request_sent", "method": method, "url": url, **kwargs},
        )

    def log_response(self, status_code: int, elapsed_time: float, **kwargs: Any) -> None:
        """Log an incoming response.

        Args:
            status_code: HTTP status code
            elapsed_time: Time taken for the request in seconds
            **kwargs: Additional context to log
        """
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        self.logger.log(
            level,
            f"Received response: {status_code}",
            extra={
                "event": "response_received",
                "status_code": status_code,
                "elapsed_time": elapsed_time,
                **kwargs,
            },
        )

    def log_retry(self, attempt: int, delay: float, reason: str, **kwargs: Any) -> None:
        """Log a retry attempt.

        Args:
            attempt: Retry attempt number
            delay: Delay before retry in seconds
            reason: Reason for retry
            **kwargs: Additional context to log
        """
        self.logger.warning(
            f"Retrying request (attempt {attempt}) after {delay}s: {reason}",
            extra={
                "event": "retry_attempt",
                "attempt": attempt,
                "delay": delay,
                "reason": reason,
                **kwargs,
            },
        )

    def log_rate_limit(self, wait_time: float, **kwargs: Any) -> None:
        """Log rate limiting.

        Args:
            wait_time: Time to wait in seconds
            **kwargs: Additional context to log
        """
        self.logger.warning(
            f"Rate limited, waiting {wait_time}s",
            extra={"event": "rate_limited", "wait_time": wait_time, **kwargs},
        )

    def log_error(self, error: Exception, **kwargs: Any) -> None:
        """Log an error.

        Args:
            error: The exception that occurred
            **kwargs: Additional context to log
        """
        self.logger.error(
            f"Request failed: {error!s}",
            exc_info=error,
            extra={"event": "request_failed", "error_type": type(error).__name__, **kwargs},
        )


# Global logger instance
_logger: APIClientLogger | None = None


def get_logger(name: str = "rest_api_client", level: str = "INFO") -> APIClientLogger:
    """Get or create the global logger instance.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        The global logger instance
    """
    global _logger
    if _logger is None:
        _logger = APIClientLogger(name, level)
    return _logger


# =============================================================================
# Session Management Utilities
# =============================================================================


def create_session(
    max_retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: list[int] | None = None,
    pool_connections: int = 10,
    pool_maxsize: int = 10,
    pool_block: bool = False,
    verify_ssl: bool = True,
) -> requests.Session:
    """Create a configured requests session with connection pooling.

    Args:
        max_retries: Maximum number of retries for failed requests
        backoff_factor: Factor for exponential backoff between retries
        status_forcelist: HTTP status codes to retry on
        pool_connections: Number of connection pools to cache
        pool_maxsize: Maximum number of connections to save in the pool
        pool_block: Whether to block when no free connections are available
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Configured requests Session
    """
    session = requests.Session()

    # Configure SSL verification with warning
    if not verify_ssl:
        # Make SSL warning more prominent
        ssl_warning = (
            "\n" + "=" * 60 + "\n"
            "WARNING: SSL certificate verification is disabled!\n"
            "This makes the connection vulnerable to man-in-the-middle attacks.\n"
            "Only use this setting in development/testing environments.\n" + "=" * 60 + "\n"
        )

        # Log at WARNING level
        logging.getLogger("rest_api_client").warning(ssl_warning)

        # Print to stderr for immediate visibility
        print(ssl_warning, file=sys.stderr)

        # Also use warnings module (though less visible)
        warnings.warn(
            "SSL certificate verification is disabled. This is insecure!",
            category=Warning,
            stacklevel=2,
        )

        session.verify = False
        # Disable urllib3 SSL warnings to reduce noise after our prominent warning
        import urllib3  # type: ignore[import-untyped]

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Default status codes to retry
    if status_forcelist is None:
        status_forcelist = [500, 502, 503, 504]

    # Configure retry strategy using urllib3's Retry
    retry_strategy = URLLibRetry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
        raise_on_status=False,
    )

    # Create adapter with connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        pool_block=pool_block,
    )

    # Mount adapter for both HTTP and HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def close_session(session: requests.Session) -> None:
    """Properly close a requests session.

    Args:
        session: Session to close
    """
    try:
        session.close()
    except Exception:
        # Ignore errors during cleanup
        pass
