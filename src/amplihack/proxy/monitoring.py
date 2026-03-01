"""Logging setup, error monitoring, and request logging for the integrated proxy.

Includes logging configuration, Azure error logging/metrics,
colorized formatters, and beautiful request logging.
"""

import asyncio
import logging
import logging.handlers
import sys
from pathlib import Path

from .exceptions import (
    AzureAPIError,
    AzureAuthenticationError,
    AzureConfigurationError,
    AzureRateLimitError,
    AzureTransientError,
)

# Import sanitizing logger to prevent credential exposure (Issue #1997)
from .sanitizing_logger import SanitizingLoggerAdapter


# Enhanced Error Logging and Monitoring
class AzureErrorLogger:
    """Centralized Azure error logging with metrics and analysis."""

    def __init__(self):
        self.error_history = []
        self.error_patterns = {}
        self.last_health_check = None

    def log_azure_error(
        self, azure_error: AzureAPIError, request_context: dict | None = None
    ) -> None:
        """Log Azure error with context and update metrics."""
        error_entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "error_type": azure_error.error_type,
            "status_code": azure_error.status_code,
            "message": str(azure_error),
            "retry_count": azure_error.retry_count,
            "is_retryable": azure_error.is_retryable,
            "context": request_context or {},
        }

        self.error_history.append(error_entry)

        # Keep only last 100 errors to prevent memory issues
        if len(self.error_history) > 100:
            self.error_history.pop(0)

        # Update error patterns
        pattern_key = f"{azure_error.error_type}:{azure_error.status_code}"
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = {
                "count": 0,
                "first_seen": error_entry["timestamp"],
                "last_seen": error_entry["timestamp"],
            }

        self.error_patterns[pattern_key]["count"] += 1
        self.error_patterns[pattern_key]["last_seen"] = error_entry["timestamp"]

        # Log with appropriate level based on error type
        if isinstance(azure_error, AzureAuthenticationError):
            logger.error(f"AZURE AUTH ERROR: {azure_error!s} (Status: {azure_error.status_code})")
        elif isinstance(azure_error, AzureConfigurationError):
            logger.error(f"AZURE CONFIG ERROR: {azure_error!s} (Status: {azure_error.status_code})")
        elif isinstance(azure_error, AzureRateLimitError):
            retry_msg = (
                f", retry after {azure_error.retry_after}s" if azure_error.retry_after else ""
            )
            logger.warning(f"AZURE RATE LIMIT: {azure_error!s}{retry_msg}")
        elif isinstance(azure_error, AzureTransientError):
            logger.warning(
                f"AZURE TRANSIENT ERROR: {azure_error!s} (Status: {azure_error.status_code}, Attempt: {azure_error.retry_count})"
            )
        else:
            logger.error(
                f"AZURE API ERROR: {azure_error!s} (Type: {azure_error.error_type}, Status: {azure_error.status_code})"
            )

        # Log context if available
        if request_context:
            model = request_context.get("model", "unknown")
            user_id = request_context.get("user_id", "unknown")
            logger.info(f"Error Context: Model={model}, User={user_id}")

    def log_azure_success(self, request_context: dict | None = None) -> None:
        """Log successful Azure API call for health monitoring."""
        if request_context:
            model = request_context.get("model", "unknown")
            response_time = request_context.get("response_time", "unknown")
            logger.debug(f"AZURE SUCCESS: Model={model}, ResponseTime={response_time}ms")

    def get_error_summary(self) -> dict:
        """Get a summary of recent Azure errors for monitoring."""
        # Import here to avoid circular dependency at module level
        from .azure_errors import azure_fallback_manager

        current_time = asyncio.get_event_loop().time()
        recent_errors = [
            e for e in self.error_history if current_time - e["timestamp"] < 3600
        ]  # Last hour

        summary = {
            "total_errors_last_hour": len(recent_errors),
            "error_patterns": self.error_patterns.copy(),
            "fallback_active": azure_fallback_manager.fallback_mode,
            "consecutive_failures": azure_fallback_manager.consecutive_failures,
            "last_health_check": self.last_health_check,
        }

        # Count errors by type in last hour
        error_counts = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        summary["recent_error_types"] = error_counts
        return summary

    def should_alert(self) -> bool:
        """Determine if an alert should be triggered based on error patterns."""
        from .azure_errors import azure_fallback_manager

        current_time = asyncio.get_event_loop().time()
        recent_errors = [
            e for e in self.error_history if current_time - e["timestamp"] < 300
        ]  # Last 5 minutes

        # Alert conditions
        if len(recent_errors) >= 5:  # 5 errors in 5 minutes
            return True

        if azure_fallback_manager.consecutive_failures >= 3:  # 3 consecutive failures
            return True

        # Check for critical error types
        for error in recent_errors:
            if error["error_type"] in ["authentication", "configuration"]:
                return True

        return False


# Global error logger instance
azure_error_logger = AzureErrorLogger()


def log_azure_operation(
    operation_name: str,
    success: bool,
    context: dict | None = None,
    error: Exception | None = None,
):
    """Unified logging function for Azure operations."""
    if success:
        logger.info(f"{operation_name} succeeded")
        azure_error_logger.log_azure_success(context)
    else:
        logger.error(f"{operation_name} failed: {str(error) if error else 'Unknown error'}")
        if isinstance(error, AzureAPIError):
            azure_error_logger.log_azure_error(error, context)


# Configure logging with file output and rotation
def setup_logging() -> SanitizingLoggerAdapter:
    """
    Set up logging with file rotation and console output.

    Returns a SanitizingLoggerAdapter that automatically redacts sensitive
    credentials from all log messages (Issue #1997: Prevent API key exposure).
    """
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create base logger
    base_logger = logging.getLogger("amplihack.proxy.integrated_proxy")
    base_logger.setLevel(logging.DEBUG)  # Set to DEBUG for file logging

    # Clear any existing handlers
    base_logger.handlers.clear()

    # File handler with rotation (10MB files, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "proxy.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    base_logger.addHandler(file_handler)

    # Console handler (WARN level and above only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARN)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    base_logger.addHandler(console_handler)

    # Tell uvicorn's loggers to be quiet
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    # Suppress LiteLLM internal logging that appears in UI
    logging.getLogger("litellm").setLevel(logging.ERROR)
    logging.getLogger("litellm.router").setLevel(logging.ERROR)
    logging.getLogger("litellm.utils").setLevel(logging.ERROR)
    logging.getLogger("litellm.cost_calculator").setLevel(logging.ERROR)
    logging.getLogger("litellm.completion").setLevel(logging.ERROR)

    # Wrap logger with sanitizing adapter to prevent credential exposure
    return SanitizingLoggerAdapter(base_logger, {})


# Set up logging
logger = setup_logging()


# Create a filter to block any log messages containing specific strings
class MessageFilter(logging.Filter):
    def filter(self, record):
        # Block messages containing these strings
        blocked_phrases = [
            "LiteLLM completion()",
            "HTTP Request:",
            "selected model name for cost calculation",
            "utils.py",
            "cost_calculator",
        ]

        if hasattr(record, "msg") and isinstance(record.msg, str):
            for phrase in blocked_phrases:
                if phrase in record.msg:
                    return False
        return True


# Apply the filter to the main logger to catch all messages
logger.addFilter(MessageFilter())


# Custom formatter for model mapping logs (only for console)
class ColorizedFormatter(logging.Formatter):
    """Custom formatter to highlight model mappings in console output"""

    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        if record.levelno == logging.DEBUG and "MODEL MAPPING" in getattr(record, "msg", ""):
            # Apply colors and formatting to model mapping logs
            return f"{self.BOLD}{self.GREEN}{record.msg}{self.RESET}"
        return super().format(record)


# Apply custom formatter only to console handler
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler) and not isinstance(
        handler, logging.handlers.RotatingFileHandler
    ):
        handler.setFormatter(ColorizedFormatter("%(asctime)s - %(levelname)s - %(message)s"))


# Define ANSI color codes for terminal output
class Colors:
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"


def log_request_beautifully(
    method, path, claude_model, openai_model, num_messages, num_tools, status_code
):
    """Log requests in a beautiful, twitter-friendly format showing Claude to OpenAI mapping."""
    # Format the Claude model name nicely
    claude_display = f"{Colors.CYAN}{claude_model}{Colors.RESET}"

    # Extract endpoint name
    endpoint = path
    if "?" in endpoint:
        endpoint = endpoint.split("?")[0]

    # Extract just the OpenAI model name without provider prefix
    openai_display = openai_model
    if "/" in openai_display:
        openai_display = openai_display.split("/")[-1]
    openai_display = f"{Colors.GREEN}{openai_display}{Colors.RESET}"

    # Format tools and messages
    tools_str = f"{Colors.MAGENTA}{num_tools} tools{Colors.RESET}"
    messages_str = f"{Colors.BLUE}{num_messages} messages{Colors.RESET}"

    # Format status code
    status_str = (
        f"{Colors.GREEN}{status_code} OK{Colors.RESET}"
        if status_code == 200
        else f"{Colors.RED}{status_code}{Colors.RESET}"
    )

    # Put it all together in a clear, beautiful format
    log_line = f"{Colors.BOLD}{method} {endpoint}{Colors.RESET} {status_str}"
    model_line = f"{claude_display} -> {openai_display} {tools_str} {messages_str}"

    # Log request information (these are significant events worth showing in console)
    logger.warning(log_line)  # Use WARNING level to ensure visibility in console
    logger.warning(model_line)
    sys.stdout.flush()
