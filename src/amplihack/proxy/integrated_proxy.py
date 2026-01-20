import asyncio
import json
import logging
import logging.handlers
import os
import ssl
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Literal

import aiohttp  # type: ignore[import-unresolved]
import certifi  # type: ignore[import-unresolved]
import litellm  # type: ignore[import-unresolved]
from dotenv import load_dotenv  # type: ignore[import-unresolved]
from fastapi import FastAPI, HTTPException, Request  # type: ignore[import-unresolved]
from fastapi.responses import StreamingResponse  # type: ignore[import-unresolved]
from litellm import Router  # type: ignore[import-unresolved]
from pydantic import BaseModel, field_validator  # type: ignore[import-unresolved]

# Load environment variables from .env file
load_dotenv()

# Load .azure.env if it exists
if os.path.exists(".azure.env"):
    load_dotenv(".azure.env")

# Import unified Azure integration
from .azure_unified_integration import create_unified_litellm_router, validate_azure_unified_config

# Import sanitizing logger to prevent credential exposure (Issue #1997)
from .sanitizing_logger import SanitizingLoggerAdapter

# Check if we should use LiteLLM router for Azure
USE_LITELLM_ROUTER = os.environ.get("AMPLIHACK_USE_LITELLM", "true").lower() == "true"


# Security utility functions
def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to prevent credential leakage."""
    import re

    # Pattern to match potential API keys (most specific first)
    key_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI-style keys (most specific first)
        r"Bearer\s+[A-Za-z0-9+/=]+",  # Bearer tokens
        r"[a-f0-9]{32,}",  # hex keys (32+ chars)
        r"[A-Za-z0-9+/]{32,}={0,2}",  # base64-like patterns (32+ chars)
    ]

    sanitized = str(error_msg)
    for pattern in key_patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)

    return sanitized


# Phase 2: Tool Configuration Environment Variables
ENFORCE_ONE_TOOL_CALL_PER_RESPONSE = (
    os.environ.get("AMPLIHACK_TOOL_ONE_PER_RESPONSE", "true").lower() == "true"
)
TOOL_CALL_RETRY_ATTEMPTS = int(os.environ.get("AMPLIHACK_TOOL_RETRY_ATTEMPTS", "3"))
TOOL_CALL_TIMEOUT = int(os.environ.get("AMPLIHACK_TOOL_TIMEOUT", "30"))  # seconds
ENABLE_TOOL_FALLBACK = os.environ.get("AMPLIHACK_TOOL_FALLBACK", "true").lower() == "true"
TOOL_STREAM_BUFFER_SIZE = int(os.environ.get("AMPLIHACK_TOOL_STREAM_BUFFER", "1024"))
ENABLE_REASONING_EFFORT = os.environ.get("AMPLIHACK_REASONING_EFFORT", "false").lower() == "true"


# Phase 2: Tool-Specific Exception Types
class ToolCallError(Exception):
    """Base exception for tool call errors"""

    def __init__(self, message: str, tool_name: str | None = None, retry_count: int = 0):
        super().__init__(message)
        self.tool_name = tool_name
        self.retry_count = retry_count


class ToolValidationError(ToolCallError):
    """Exception for tool schema validation errors"""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        schema_errors: list[str] | None = None,
    ):
        super().__init__(message, tool_name)
        self.schema_errors = schema_errors or []


class ToolTimeoutError(ToolCallError):
    """Exception for tool call timeouts"""

    def __init__(
        self, message: str, tool_name: str | None = None, timeout_seconds: int | None = None
    ):
        super().__init__(message, tool_name)
        self.timeout_seconds = timeout_seconds


class ToolStreamingError(ToolCallError):
    """Exception for tool streaming errors"""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        chunk_data: dict[str, Any] | None = None,
    ):
        super().__init__(message, tool_name)
        self.chunk_data = chunk_data or {}


class ConversationStateError(Exception):
    """Exception for conversation state management errors"""

    def __init__(self, message: str, state: str | None = None):
        super().__init__(message)
        self.state = state


# Azure-Specific Exception Types
class AzureAPIError(Exception):
    """Base exception for Azure API errors"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_type: str | None = None,
        retry_count: int = 0,
        is_retryable: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.retry_count = retry_count
        self.is_retryable = is_retryable


class AzureTransientError(AzureAPIError):
    """Exception for transient Azure errors that should be retried"""

    def __init__(self, message: str, status_code: int | None = None, retry_count: int = 0):
        super().__init__(message, status_code, "transient", retry_count, is_retryable=True)


class AzureAuthenticationError(AzureAPIError):
    """Exception for Azure authentication/authorization errors"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code, "authentication", is_retryable=False)


class AzureRateLimitError(AzureAPIError):
    """Exception for Azure rate limiting errors"""

    def __init__(self, message: str, retry_after: int | None = None, retry_count: int = 0):
        super().__init__(message, 429, "rate_limit", retry_count, is_retryable=True)
        self.retry_after = retry_after


class AzureConfigurationError(AzureAPIError):
    """Exception for Azure configuration/deployment errors"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code, "configuration", is_retryable=False)


class AzureFallbackError(AzureAPIError):
    """Exception indicating Azure fallback was triggered"""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, error_type="fallback", is_retryable=False)
        self.original_error = original_error


# Azure Error Classification and Parsing
def classify_azure_error(status_code: int, error_text: str) -> AzureAPIError:
    """Classify Azure API errors into specific exception types with enhanced parsing."""
    import json
    import re

    # Parse JSON error response if possible
    error_data = {}
    try:
        error_data = json.loads(error_text)
    except (json.JSONDecodeError, TypeError):
        # If not JSON, treat as plain text
        pass

    # Extract common error fields
    error_code = error_data.get("code", "")
    error_message = error_data.get("message", error_text)
    inner_error = error_data.get("innererror", {}) or error_data.get("error", {})

    # Extract more details from inner error if available
    if inner_error:
        error_code = inner_error.get("code", error_code)
        if not error_message or error_message == error_text:
            error_message = inner_error.get("message", error_text)

    # Create user-friendly message
    user_message = f"Azure API error: {error_message}"

    # Classify by status code and error patterns
    if status_code in [401, 403]:
        if "unauthorized" in error_message.lower() or "authentication" in error_message.lower():
            return AzureAuthenticationError(
                f"Authentication failed. Please check your Azure API key and permissions. Details: {error_message}",
                status_code,
            )
        if "forbidden" in error_message.lower() or "access denied" in error_message.lower():
            return AzureAuthenticationError(
                f"Access denied. Your API key may lack required permissions. Details: {error_message}",
                status_code,
            )
        return AzureAuthenticationError(user_message, status_code)

    if status_code == 429:
        # Extract retry-after header info if available
        retry_after = None
        if "retry-after" in error_message.lower():
            # Try to extract retry-after value
            retry_match = re.search(r"retry.*?(\d+)", error_message.lower())
            if retry_match:
                retry_after = int(retry_match.group(1))

        return AzureRateLimitError(
            f"Rate limit exceeded. Please wait before retrying. Details: {error_message}",
            retry_after=retry_after,
        )

    if status_code in [500, 502, 503, 504]:
        # Server errors - usually transient
        if status_code == 500:
            message = f"Internal server error on Azure. This is usually temporary. Details: {error_message}"
        elif status_code == 502:
            message = f"Bad gateway error. Azure service may be temporarily unavailable. Details: {error_message}"
        elif status_code == 503:
            message = (
                f"Service unavailable. Azure is temporarily overloaded. Details: {error_message}"
            )
        else:  # 504
            message = f"Gateway timeout. Request took too long to process. Details: {error_message}"

        return AzureTransientError(message, status_code)

    if status_code == 400:
        # Bad request - could be configuration issue
        if any(
            keyword in error_message.lower()
            for keyword in ["deployment", "model", "endpoint", "not found"]
        ):
            return AzureConfigurationError(
                f"Configuration error. Check your Azure deployment name and endpoint. Details: {error_message}",
                status_code,
            )
        return AzureAPIError(
            f"Bad request. Please check your request format. Details: {error_message}",
            status_code,
            "bad_request",
            is_retryable=False,
        )

    if status_code == 404:
        return AzureConfigurationError(
            f"Resource not found. Check your Azure endpoint URL and deployment name. Details: {error_message}",
            status_code,
        )

    if status_code == 408:
        return AzureTransientError(
            f"Request timeout. The request took too long to process. Details: {error_message}",
            status_code,
        )

    # Unknown error type
    is_retryable = status_code >= 500  # Assume server errors are retryable
    return AzureAPIError(
        f"Unexpected Azure API error (status {status_code}). Details: {error_message}",
        status_code,
        "unknown",
        is_retryable=is_retryable,
    )


def extract_user_friendly_message(azure_error: AzureAPIError) -> str:
    """Extract a user-friendly error message from Azure API error."""
    if isinstance(azure_error, AzureAuthenticationError):
        return "Authentication issue with Azure API. Please check your credentials and permissions."
    if isinstance(azure_error, AzureRateLimitError):
        retry_msg = (
            f" Try again in {azure_error.retry_after} seconds."
            if azure_error.retry_after
            else " Please wait before retrying."
        )
        return f"Rate limit exceeded.{retry_msg}"
    if isinstance(azure_error, AzureConfigurationError):
        return "Configuration issue with Azure deployment. Please check your endpoint and model settings."
    if isinstance(azure_error, AzureTransientError):
        return "Temporary Azure service issue. The request will be retried automatically."
    if isinstance(azure_error, AzureFallbackError):
        return "Azure API unavailable. Using fallback processing mode."
    return f"Azure API error: {azure_error!s}"


# Azure Retry Logic with Exponential Backoff
async def retry_azure_request(
    request_func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    request_name: str = "Azure API",
) -> Any:
    """
    Retry Azure API requests with exponential backoff for transient errors.

    Args:
        request_func: Async function that makes the Azure API request
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        request_name: Name of the request for logging

    Returns:
        Result of the successful request

    Raises:
        AzureAPIError: If all retries fail or error is not retryable
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await request_func()

        except AzureAPIError as azure_error:
            last_error = azure_error
            azure_error.retry_count = attempt

            # Don't retry non-retryable errors
            if not azure_error.is_retryable:
                logger.error(
                    f"❌ {request_name} failed with non-retryable error: {azure_error.error_type} - {azure_error!s}"
                )
                raise azure_error

            # Don't retry if this was our last attempt
            if attempt >= max_retries:
                logger.error(
                    f"❌ {request_name} failed after {max_retries + 1} attempts: {azure_error!s}"
                )
                break

            # Calculate delay with exponential backoff
            if isinstance(azure_error, AzureRateLimitError) and azure_error.retry_after:
                # Use server-specified retry time for rate limits
                delay = min(azure_error.retry_after, max_delay)
            else:
                # Standard exponential backoff
                delay = min(base_delay * (backoff_multiplier**attempt), max_delay)

            logger.warning(
                f"⏳ {request_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s: {azure_error.error_type} - {azure_error!s}"
            )

            await asyncio.sleep(delay)

        except TimeoutError as timeout_error:
            # Treat timeouts as transient errors
            last_error = AzureTransientError(
                f"Request timeout: {timeout_error}", status_code=408, retry_count=attempt
            )

            if attempt >= max_retries:
                logger.error(f"❌ {request_name} timed out after {max_retries + 1} attempts")
                break

            delay = min(base_delay * (backoff_multiplier**attempt), max_delay)
            logger.warning(
                f"⏳ {request_name} timed out (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s"
            )
            await asyncio.sleep(delay)

        except aiohttp.ClientError as client_error:
            # Treat other client errors as transient
            last_error = AzureTransientError(
                f"Network error: {client_error!s}", status_code=503, retry_count=attempt
            )

            if attempt >= max_retries:
                logger.error(
                    f"❌ {request_name} failed with network error after {max_retries + 1} attempts"
                )
                break

            delay = min(base_delay * (backoff_multiplier**attempt), max_delay)
            logger.warning(
                f"⏳ {request_name} network error (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s: {client_error!s}"
            )
            await asyncio.sleep(delay)

        except Exception as unexpected_error:
            # For unexpected errors, don't retry
            logger.error(
                f"❌ {request_name} failed with unexpected error: {type(unexpected_error).__name__}: {unexpected_error!s}"
            )
            raise AzureAPIError(
                f"Unexpected error during {request_name}: {unexpected_error!s}",
                error_type="unexpected",
                is_retryable=False,
            )

    # All retries failed
    if last_error:
        raise last_error
    raise AzureAPIError(
        f"All retry attempts failed for {request_name}", error_type="retry_exhausted"
    )


# Fallback Mechanisms
class AzureFallbackManager:
    """Manages fallback behavior when Azure API consistently fails."""

    def __init__(self):
        self.failure_count = 0
        self.consecutive_failures = 0
        self.last_success_time = None
        self.fallback_mode = False
        self.fallback_until = None

    def record_success(self):
        """Record a successful Azure API call."""
        self.consecutive_failures = 0
        self.last_success_time = asyncio.get_event_loop().time()

        # Exit fallback mode on success
        if self.fallback_mode:
            logger.info("🎉 Azure API recovered - exiting fallback mode")
            self.fallback_mode = False
            self.fallback_until = None

    def record_failure(self, azure_error: AzureAPIError):
        """Record a failed Azure API call and determine if fallback should be triggered."""
        self.failure_count += 1
        self.consecutive_failures += 1

        current_time = asyncio.get_event_loop().time()

        # Determine if we should enter fallback mode
        should_fallback = False
        fallback_duration = 300  # 5 minutes default

        if isinstance(azure_error, AzureAuthenticationError):
            # Authentication errors - longer fallback
            should_fallback = True
            fallback_duration = 1800  # 30 minutes
            logger.error("🔒 Azure authentication error - entering extended fallback mode")

        elif isinstance(azure_error, AzureConfigurationError):
            # Configuration errors - longer fallback
            should_fallback = True
            fallback_duration = 3600  # 1 hour
            logger.error("⚙️ Azure configuration error - entering extended fallback mode")

        elif self.consecutive_failures >= 3:
            # Multiple consecutive failures - temporary fallback
            should_fallback = True
            fallback_duration = 300  # 5 minutes
            logger.warning(
                f"⚠️ {self.consecutive_failures} consecutive Azure failures - entering temporary fallback mode"
            )

        elif isinstance(azure_error, AzureTransientError) and self.consecutive_failures >= 2:
            # Multiple transient errors - short fallback
            should_fallback = True
            fallback_duration = 120  # 2 minutes
            logger.warning("⏳ Multiple transient Azure errors - entering short fallback mode")

        if should_fallback and not self.fallback_mode:
            self.fallback_mode = True
            self.fallback_until = current_time + fallback_duration
            logger.warning(
                f"🔄 Entering Azure fallback mode for {fallback_duration / 60:.1f} minutes "
                f"(consecutive failures: {self.consecutive_failures})"
            )

    def should_use_fallback(self) -> bool:
        """Check if fallback mode should be used."""
        if not self.fallback_mode:
            return False

        current_time = asyncio.get_event_loop().time()

        # Check if fallback period has expired
        if self.fallback_until and current_time >= self.fallback_until:
            logger.info("⏰ Fallback period expired - attempting Azure API recovery")
            self.fallback_mode = False
            self.fallback_until = None
            return False

        return True

    def get_fallback_reason(self) -> str:
        """Get a human-readable reason for fallback mode."""
        if not self.fallback_mode:
            return ""

        current_time = asyncio.get_event_loop().time()
        if self.fallback_until:
            remaining = int(self.fallback_until - current_time)
            return f"Azure API fallback active (recovery in {remaining // 60}m {remaining % 60}s)"
        return "Azure API fallback active"


# Global fallback manager instance
azure_fallback_manager = AzureFallbackManager()


async def create_fallback_response(request: dict, fallback_reason: str) -> dict:
    """Create a fallback response when Azure API is unavailable."""
    claude_model = request.get("model", "claude-3-sonnet")

    # Extract user message for context
    user_message = ""
    messages = request.get("messages", [])
    if messages:
        last_msg = messages[-1]
        content = last_msg.get("content", "")
        if isinstance(content, str):
            user_message = content[:200] + "..." if len(content) > 200 else content
        elif isinstance(content, list):
            # Extract text from content blocks
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            user_message = " ".join(text_parts)[:200]
            if len(user_message) > 200:
                user_message += "..."

    fallback_message = f"""I apologize, but I'm currently unable to process your request due to Azure API issues ({fallback_reason}).

This is a temporary service interruption. The system will automatically retry Azure API calls when service is restored.

For urgent requests, you may want to:
1. Wait a few minutes and try again
2. Check the Azure service status
3. Contact system administrators if the issue persists

Your request: "{user_message}"

The system is monitoring Azure API health and will resume normal processing once connectivity is restored."""

    return {
        "id": f"msg_fallback_{uuid.uuid4()}",
        "model": claude_model,
        "role": "assistant",
        "content": [{"type": "text", "text": fallback_message}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": len(user_message.split()),
            "output_tokens": len(fallback_message.split()),
        },
    }


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
            logger.error(
                f"🔒 AZURE AUTH ERROR: {azure_error!s} (Status: {azure_error.status_code})"
            )
        elif isinstance(azure_error, AzureConfigurationError):
            logger.error(
                f"⚙️ AZURE CONFIG ERROR: {azure_error!s} (Status: {azure_error.status_code})"
            )
        elif isinstance(azure_error, AzureRateLimitError):
            retry_msg = (
                f", retry after {azure_error.retry_after}s" if azure_error.retry_after else ""
            )
            logger.warning(f"⏱️ AZURE RATE LIMIT: {azure_error!s}{retry_msg}")
        elif isinstance(azure_error, AzureTransientError):
            logger.warning(
                f"⚠️ AZURE TRANSIENT ERROR: {azure_error!s} (Status: {azure_error.status_code}, Attempt: {azure_error.retry_count})"
            )
        else:
            logger.error(
                f"❌ AZURE API ERROR: {azure_error!s} (Type: {azure_error.error_type}, Status: {azure_error.status_code})"
            )

        # Log context if available
        if request_context:
            model = request_context.get("model", "unknown")
            user_id = request_context.get("user_id", "unknown")
            logger.info(f"📊 Error Context: Model={model}, User={user_id}")

    def log_azure_success(self, request_context: dict | None = None) -> None:
        """Log successful Azure API call for health monitoring."""
        if request_context:
            model = request_context.get("model", "unknown")
            response_time = request_context.get("response_time", "unknown")
            logger.debug(f"✅ AZURE SUCCESS: Model={model}, ResponseTime={response_time}ms")

    def get_error_summary(self) -> dict:
        """Get a summary of recent Azure errors for monitoring."""
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
        logger.info(f"✅ {operation_name} succeeded")
        azure_error_logger.log_azure_success(context)
    else:
        logger.error(f"❌ {operation_name} failed: {str(error) if error else 'Unknown error'}")
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
    base_logger = logging.getLogger(__name__)
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


# Global config for LiteLLM router initialization
_proxy_config: dict[str, str] | None = None


def setup_litellm_router(config: dict[str, str] | None = None) -> Router | None:
    """Set up unified LiteLLM router for both Azure Chat and Responses APIs."""
    if not USE_LITELLM_ROUTER:
        return None

    # Get configuration
    if config is None:
        config = {}

    # Extract required configuration
    AZURE_OPENAI_KEY = config.get("AZURE_OPENAI_KEY", os.environ.get("AZURE_OPENAI_KEY"))
    OPENAI_API_KEY = config.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
    OPENAI_BASE_URL = config.get("OPENAI_BASE_URL", os.environ.get("OPENAI_BASE_URL"))

    # Use AZURE_OPENAI_KEY first, fallback to OPENAI_API_KEY
    api_key = AZURE_OPENAI_KEY or OPENAI_API_KEY

    if not api_key or not OPENAI_BASE_URL:
        logger.warning("Unified LiteLLM router disabled: missing Azure credentials")
        return None

    # Validate configuration
    temp_config = {"OPENAI_API_KEY": api_key, "OPENAI_BASE_URL": OPENAI_BASE_URL}
    if not validate_azure_unified_config(temp_config):
        logger.error("❌ Azure unified configuration validation failed")
        return None

    # Use full URL as base_url - don't strip the path
    # The path (/openai/responses or empty) is needed to detect Responses vs Chat API
    base_url = OPENAI_BASE_URL

    # Get API version - default to Chat API version
    api_version = config.get(
        "AZURE_API_VERSION", os.environ.get("AZURE_API_VERSION", "2025-01-01-preview")
    )

    # Get model deployment names from config
    big_model = config.get("BIG_MODEL", os.environ.get("BIG_MODEL", "gpt-5-codex"))
    middle_model = config.get("MIDDLE_MODEL", os.environ.get("MIDDLE_MODEL", "gpt-5-codex"))
    small_model = config.get("SMALL_MODEL", os.environ.get("SMALL_MODEL", "gpt-5-codex"))

    logger.info(
        f"🚀 Initializing LiteLLM with deployments: BIG={big_model}, MIDDLE={middle_model}, SMALL={small_model}"
    )

    try:
        router = create_unified_litellm_router(
            api_key, base_url, api_version, big_model, middle_model, small_model
        )
        logger.info(f"✅ LiteLLM router initialized: {base_url}")
        return router
    except Exception as e:
        logger.error(f"❌ Failed to initialize LiteLLM router: {e}")
        return None


def create_app(config: dict[str, str] | None = None) -> FastAPI:
    """Create FastAPI app with configuration."""
    global _proxy_config

    app = FastAPI()

    # Get API keys from config or environment
    if config is None:
        config = {}

    # Store config globally for LiteLLM router initialization
    _proxy_config = config

    # Azure-specific configuration
    OPENAI_BASE_URL = config.get("OPENAI_BASE_URL", os.environ.get("OPENAI_BASE_URL"))
    # AZURE_API_VERSION = config.get(
    #     "AZURE_API_VERSION", os.environ.get("AZURE_API_VERSION", "2025-04-01-preview")
    # )  # unused for now

    # Get model mapping configuration from environment variables
    BIG_MODEL = config.get("BIG_MODEL", os.environ.get("BIG_MODEL", "gpt-5-codex"))
    MIDDLE_MODEL = config.get("MIDDLE_MODEL", os.environ.get("MIDDLE_MODEL", "gpt-5-codex"))
    SMALL_MODEL = config.get("SMALL_MODEL", os.environ.get("SMALL_MODEL", "gpt-5-codex"))

    logger.info(f"Model Configuration: BIG={BIG_MODEL}, MIDDLE={MIDDLE_MODEL}, SMALL={SMALL_MODEL}")

    # Unified routing through LiteLLM - no bypass logic needed
    # All model mapping and API routing is handled by AzureUnifiedProvider

    @app.get("/health")
    async def health():
        """Enhanced health check endpoint with Azure monitoring."""
        proxy_type = (
            "integrated_azure_chat" if is_azure_chat_api() else "integrated_azure_responses"
        )
        health_status = {
            "status": "healthy",
            "proxy_type": proxy_type,
            "timestamp": asyncio.get_event_loop().time(),
            "azure": {
                "fallback_active": azure_fallback_manager.fallback_mode,
                "consecutive_failures": azure_fallback_manager.consecutive_failures,
                "total_failures": azure_fallback_manager.failure_count,
                "last_success": azure_fallback_manager.last_success_time,
            },
        }

        # Get error summary
        error_summary = azure_error_logger.get_error_summary()
        health_status["azure"]["error_summary"] = error_summary

        # Determine overall health status
        if azure_fallback_manager.fallback_mode:
            health_status["status"] = "degraded"
            health_status["message"] = azure_fallback_manager.get_fallback_reason()
        elif error_summary["total_errors_last_hour"] > 10:
            health_status["status"] = "unhealthy"
            health_status["message"] = (
                f"High error rate: {error_summary['total_errors_last_hour']} errors in last hour"
            )
        elif azure_error_logger.should_alert():
            health_status["status"] = "warning"
            health_status["message"] = "Azure API experiencing issues"

        return health_status

    @app.get("/azure/status")
    async def azure_status():
        """Detailed Azure API status and error analysis."""
        status = {
            "azure_api": {
                "endpoint": OPENAI_BASE_URL,
                "fallback_manager": {
                    "active": azure_fallback_manager.fallback_mode,
                    "consecutive_failures": azure_fallback_manager.consecutive_failures,
                    "total_failures": azure_fallback_manager.failure_count,
                    "last_success": azure_fallback_manager.last_success_time,
                    "fallback_until": azure_fallback_manager.fallback_until,
                },
                "error_patterns": azure_error_logger.error_patterns,
                "recent_errors": azure_error_logger.error_history[-10:],  # Last 10 errors
                "should_alert": azure_error_logger.should_alert(),
            }
        }
        return status

    @app.get("/")
    async def root():
        return {"message": "Integrated Anthropic Proxy with Azure Responses API Support"}

    async def handle_message_with_litellm_router(request: dict) -> dict[str, Any]:
        """Handle messages using unified LiteLLM router for Chat and Responses APIs."""
        claude_model = request.get("model", "unknown")

        # Input validation for model names
        if not claude_model or not isinstance(claude_model, str):
            raise ValueError("Model name must be a non-empty string")

        # Sanitize model name to prevent injection attacks
        claude_model = claude_model.strip()
        if len(claude_model) > 100:  # Reasonable limit for model names
            raise ValueError("Model name too long (max 100 characters)")

        # Validate model name contains only allowed characters
        import re

        if not re.match(r"^[a-zA-Z0-9\-\._]+$", claude_model):
            raise ValueError(
                "Model name contains invalid characters (only alphanumeric, dash, dot, underscore allowed)"
            )

        # Route based on configured BIG_MODEL (from config file)
        # This allows users to control routing via environment configuration
        # rather than auto-detecting from prompt content
        router_model = (
            BIG_MODEL  # Use configured model (gpt-5 for Chat API, gpt-5-codex for Responses API)
        )
        logger.debug(f"Routing to configured BIG_MODEL: {router_model}")

        # Fallback: if requested model is a Claude model, use it directly
        if claude_model in [
            "claude-3-5-sonnet-20241022",
            "claude-sonnet-4-5-20250929",
            "claude-3-5-haiku-20241022",
        ]:
            router_model = claude_model  # Use exact Claude model mapping
            logger.debug(f"Using explicit Claude model mapping: {claude_model} -> {router_model}")

        # Get configured token limits from environment for Azure Responses API
        min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "4096"))
        max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "512000"))

        # Ensure proper token limits for Azure Responses API
        max_tokens_value = request.get("max_tokens", 1)
        if max_tokens_value and max_tokens_value > 1:
            # Ensure we use at least the minimum configured limit
            max_tokens_value = max(min_tokens_limit, max_tokens_value)
            # Cap at maximum configured limit
            max_tokens_value = min(max_tokens_limit, max_tokens_value)
        else:
            # Default to maximum limit for Azure Responses API models when request has low/no max_tokens
            max_tokens_value = max_tokens_limit

        # Create LiteLLM-compatible request
        litellm_request = {
            "model": router_model,
            "messages": [],
            "max_tokens": max_tokens_value,
            "temperature": 1.0,  # Always use temperature=1 for Azure Responses API models
            "stream": request.get("stream", False),
        }

        # Add system message if present
        system_content = request.get("system")
        if system_content:
            if isinstance(system_content, str):
                litellm_request["messages"].append({"role": "system", "content": system_content})
            elif isinstance(system_content, list):
                system_text = ""
                for block in system_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_text += block.get("text", "") + "\n\n"
                if system_text:
                    litellm_request["messages"].append(
                        {"role": "system", "content": system_text.strip()}
                    )

        # Convert messages
        for msg in request.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                litellm_request["messages"].append({"role": msg.get("role"), "content": content})
            else:
                # Extract text content from complex content blocks
                text_content = ""
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_content += block.get("text", "") + "\n"
                        elif block.get("type") == "tool_result":
                            result_content = block.get("content", "")
                            if isinstance(result_content, str):
                                text_content += result_content + "\n"
                            elif isinstance(result_content, list):
                                for item in result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "") + "\n"
                        elif block.get("type") == "tool_use":
                            # Convert tool_use to text description for now
                            text_content += f"Tool: {block.get('name', 'unknown')} with input: {block.get('input', {})}\n"

                if text_content.strip():
                    litellm_request["messages"].append(
                        {"role": msg.get("role"), "content": text_content.strip()}
                    )
                else:
                    litellm_request["messages"].append({"role": msg.get("role"), "content": "..."})

        # Add tool definitions if present
        if request.get("tools"):
            # Azure Responses API uses flat format, Chat API uses nested format
            use_responses_api_format = is_azure_responses_api()

            formatted_tools = []
            for tool in request["tools"]:
                if use_responses_api_format:
                    # Azure Responses API format: flat structure with name at top level
                    formatted_tool = {
                        "type": "function",
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    }
                else:
                    # OpenAI Chat API format: nested function object
                    formatted_tool = {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "parameters": tool.get("input_schema", {}),
                        },
                    }
                formatted_tools.append(formatted_tool)

            litellm_request["tools"] = formatted_tools

            # Handle tool_choice
            if request.get("tool_choice"):
                choice_type = request["tool_choice"].get("type")
                if choice_type == "auto":
                    litellm_request["tool_choice"] = "auto"
                elif choice_type == "tool" and "name" in request["tool_choice"]:
                    if use_responses_api_format:
                        # Azure Responses API format for tool_choice
                        litellm_request["tool_choice"] = {
                            "type": "function",
                            "name": request["tool_choice"]["name"],
                        }
                    else:
                        # OpenAI Chat API format for tool_choice
                        litellm_request["tool_choice"] = {
                            "type": "function",
                            "function": {"name": request["tool_choice"]["name"]},
                        }

        # Make the request using LiteLLM router
        try:
            logger.debug(f"Making LiteLLM router request to {router_model}")

            # Use LiteLLM router but handle Azure Responses API specifics
            logger.debug(
                f"LiteLLM request: model={litellm_request.get('model')}, tools={len(litellm_request.get('tools', []))}, stream={litellm_request.get('stream')}"
            )

            try:
                active_router = get_litellm_router()
                if active_router is None:
                    raise Exception("LiteLLM router is not initialized")

                # Handle streaming requests
                if litellm_request.get("stream"):
                    # Return streaming response directly
                    response_generator = await active_router.acompletion(**litellm_request)
                    # Convert dict request to MessagesRequest for handle_streaming
                    messages_request = MessagesRequest(**request)
                    return StreamingResponse(
                        handle_streaming(response_generator, messages_request),
                        media_type="text/event-stream",
                    )
                # Non-streaming request
                response = await active_router.acompletion(**litellm_request)
            except Exception as router_error:
                sanitized_error = sanitize_error_message(str(router_error))
                logger.error(f"LiteLLM router failed unexpectedly: {sanitized_error}")
                raise router_error

            # Convert response to Anthropic format
            choices = response.choices if hasattr(response, "choices") else []
            if not choices:
                raise ValueError("No choices in LiteLLM response")

            choice = choices[0]
            message = choice.message if hasattr(choice, "message") else choice.get("message", {})
            content_text = (
                message.content if hasattr(message, "content") else message.get("content", "")
            )
            finish_reason = (
                choice.finish_reason
                if hasattr(choice, "finish_reason")
                else choice.get("finish_reason", "stop")
            )

            # Handle tool calls
            tool_calls = (
                message.tool_calls
                if hasattr(message, "tool_calls")
                else message.get("tool_calls", [])
            )
            content_blocks = []

            # Always add text content, even if empty (Anthropic format requirement)
            if content_text:
                content_blocks.append({"type": "text", "text": content_text})
            elif not tool_calls:  # Only add empty text if no tool calls
                content_blocks.append({"type": "text", "text": ""})

            if tool_calls:
                for tool_call in tool_calls:
                    function = (
                        tool_call.function
                        if hasattr(tool_call, "function")
                        else tool_call.get("function", {})
                    )
                    name = function.name if hasattr(function, "name") else function.get("name", "")
                    arguments = (
                        function.arguments
                        if hasattr(function, "arguments")
                        else function.get("arguments", "{}")
                    )

                    # Parse arguments if they're a string
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {"raw": arguments}

                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tool_call.id
                            if hasattr(tool_call, "id")
                            else tool_call.get("id", f"tool_{uuid.uuid4()}"),
                            "name": name,
                            "input": arguments,
                        }
                    )

            # Extract usage information
            usage_info = getattr(response, "usage", {})
            if isinstance(usage_info, dict):
                input_tokens = usage_info.get("prompt_tokens", 0)
                output_tokens = usage_info.get("completion_tokens", 0)
            else:
                input_tokens = getattr(usage_info, "prompt_tokens", 0)
                output_tokens = getattr(usage_info, "completion_tokens", 0)

            # Map finish reason to Anthropic format
            stop_reason = "end_turn"
            if finish_reason == "length":
                stop_reason = "max_tokens"
            elif finish_reason == "tool_calls":
                stop_reason = "tool_use"

            # Ensure content_blocks is never empty (Anthropic requirement)
            if not content_blocks:
                content_blocks = [{"type": "text", "text": ""}]

            return {
                "id": response.id if hasattr(response, "id") else f"msg_{uuid.uuid4()}",
                "model": claude_model,  # Return original Claude model name
                "role": "assistant",
                "content": content_blocks,
                "stop_reason": stop_reason,
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            }

        except Exception as e:
            logger.debug(f"LiteLLM router request failed (expected): {type(e).__name__}")
            raise

    # Add message handling with unified LiteLLM routing
    @app.post("/v1/messages")
    async def create_message(request: dict):
        """Handle messages using unified LiteLLM router for all requests."""
        try:
            claude_model = request.get("model", "unknown")
            logger.info(f"Processing request for Claude model: {claude_model}")

            # Check if we should use LiteLLM router (lazy initialization)
            active_router = get_litellm_router()
            if active_router and USE_LITELLM_ROUTER:
                # Use LiteLLM router for ALL requests (both with and without tools)
                request_type = "with tools" if request.get("tools") else "text-only"
                logger.info(f"Using LiteLLM router for {request_type} request with {claude_model}")
                return await handle_message_with_litellm_router(request)

            # If LiteLLM router is not available, raise an error
            logger.error("LiteLLM router not available - cannot process request")
            raise HTTPException(
                status_code=503,
                detail="LiteLLM router not configured. Please ensure proper configuration.",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in create_message: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    return app


# Legacy global app instance (for backward compatibility)
app = FastAPI()

# Get API keys from environment (legacy approach)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Azure-specific configuration
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", OPENAI_API_KEY)
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
AZURE_API_VERSION = os.environ.get("AZURE_API_VERSION", "2025-03-01-preview")

# Performance Optimization: Lazy router initialization
_litellm_router = None
_router_init_attempted = False


def get_litellm_router() -> Router | None:
    """Get LiteLLM router with lazy initialization for optimal startup performance."""
    global _litellm_router, _router_init_attempted, _proxy_config

    if not USE_LITELLM_ROUTER:
        return None

    # Return cached router if available
    if _litellm_router is not None:
        return _litellm_router

    # Return None if initialization already failed
    if _router_init_attempted and _litellm_router is None:
        return None

    # Attempt initialization only when first needed
    if not _router_init_attempted:
        _router_init_attempted = True
        try:
            # Pass the global config if available
            _litellm_router = setup_litellm_router(_proxy_config)
            if _litellm_router:
                logger.info("✅ Lazy LiteLLM router initialized successfully")
            else:
                logger.warning("⚠️ LiteLLM router setup returned None")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LiteLLM router: {e}")
            _litellm_router = None

    return _litellm_router


# Legacy compatibility
litellm_router = None  # Will be replaced by lazy getter calls

# Get preferred provider (default to openai)
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openai").lower()

# Get model mapping configuration from environment
# Default to latest OpenAI models if not set
BIG_MODEL = os.environ.get("BIG_MODEL", "gpt-4.1")
SMALL_MODEL = os.environ.get("SMALL_MODEL", "gpt-4.1-mini")

# List of OpenAI models
OPENAI_MODELS = [
    "o3-mini",
    "o1",
    "o1-mini",
    "o1-pro",
    "gpt-4.5-preview",
    "gpt-4o",
    "gpt-4o-audio-preview",
    "chatgpt-4o-latest",
    "gpt-4o-mini",
    "gpt-4o-mini-audio-preview",
    "gpt-4.1",  # Added default big model
    "gpt-4.1-mini",  # Added default small model
]

# List of Gemini models
GEMINI_MODELS = ["gemini-2.5-pro-preview-03-25", "gemini-2.0-flash"]


# Type alias for JSON schema structures
JSONSchema = dict[str, Any] | list[Any] | str | int | float | bool | None


# Helper function to clean schema for Gemini
def clean_gemini_schema(schema: JSONSchema) -> JSONSchema:
    """Recursively removes unsupported fields from a JSON schema for Gemini."""
    if isinstance(schema, dict):
        # Remove specific keys unsupported by Gemini tool parameters
        schema.pop("additionalProperties", None)
        schema.pop("default", None)

        # Check for unsupported 'format' in string types
        if schema.get("type") == "string" and "format" in schema:
            allowed_formats = {"enum", "date-time"}
            if schema["format"] not in allowed_formats:
                logger.debug(
                    f"Removing unsupported format '{schema['format']}' for string type in Gemini schema."
                )
                schema.pop("format")

        # Recursively clean nested schemas (properties, items, etc.)
        for key, value in list(schema.items()):  # Use list() to allow modification during iteration
            schema[key] = clean_gemini_schema(value)
    elif isinstance(schema, list):
        # Recursively clean items in a list
        return [clean_gemini_schema(item) for item in schema]
    return schema


# Models for Anthropic API requests
class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: dict[str, Any]


class ContentBlockToolUse(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields like cache_control
    type: Literal["tool_use"]
    id: str
    name: str | None = None  # Name can be None in partial tool use blocks
    input: dict[str, Any]


class ContentBlockToolResult(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields like cache_control
    type: Literal["tool_result"]
    tool_use_id: str
    content: str | list[dict[str, Any]] | dict[str, Any] | list[Any]


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: (
        str
        | list[ContentBlockText | ContentBlockImage | ContentBlockToolUse | ContentBlockToolResult]
    )


class Tool(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any]


class ThinkingConfig(BaseModel):
    enabled: bool = True


class ConversationState(BaseModel):
    """Phase 2: Manages conversation state for tool call analysis"""

    phase: Literal["normal", "tool_call_pending", "tool_result_pending", "tool_complete"] = "normal"
    pending_tool_calls: list[dict[str, Any]] = []
    completed_tool_calls: list[dict[str, Any]] = []
    last_tool_call_id: str | None = None
    tool_call_count: int = 0
    has_streaming_tools: bool = False
    conversation_turn: int = 0

    def add_tool_call(self, tool_call: dict[str, Any]) -> None:
        """Add a pending tool call"""
        self.pending_tool_calls.append(tool_call)
        self.last_tool_call_id = tool_call.get("id")
        self.tool_call_count += 1
        self.phase = "tool_call_pending"

    def complete_tool_call(self, tool_call_id: str, result: dict[str, Any]) -> None:
        """Mark a tool call as completed"""
        for i, call in enumerate(self.pending_tool_calls):
            if call.get("id") == tool_call_id:
                completed_call = self.pending_tool_calls.pop(i)
                completed_call["result"] = result
                self.completed_tool_calls.append(completed_call)
                break

        if not self.pending_tool_calls:
            self.phase = "tool_complete"

    def reset_for_new_turn(self) -> None:
        """Reset state for a new conversation turn"""
        self.conversation_turn += 1
        self.phase = "normal"
        self.pending_tool_calls = []
        self.has_streaming_tools = False


class MessagesRequest(BaseModel):
    model: str
    max_tokens: int
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    stop_sequences: list[str] | None = None
    stream: bool | None = False
    temperature: float | None = 1.0
    top_p: float | None = None
    top_k: int | None = None
    metadata: dict[str, Any] | None = None
    tools: list[Tool] | None = None
    tool_choice: dict[str, Any] | None = None
    thinking: ThinkingConfig | None = None
    original_model: str | None = None  # Will store the original model name

    @field_validator("model")
    def validate_model_field(cls, v, info):  # Renamed to avoid conflict
        original_model = v
        new_model = v  # Default to original value

        logger.debug(
            f"📋 MODEL VALIDATION: Original='{original_model}', Preferred='{PREFERRED_PROVIDER}', BIG='{BIG_MODEL}', SMALL='{SMALL_MODEL}'"
        )

        # Remove provider prefixes for easier matching
        clean_v = v
        if clean_v.startswith("anthropic/"):
            clean_v = clean_v[10:]
        elif clean_v.startswith("openai/") or clean_v.startswith("gemini/"):
            clean_v = clean_v[7:]

        # --- Mapping Logic --- START ---
        mapped = False
        # Map Haiku to SMALL_MODEL based on provider preference
        if "haiku" in clean_v.lower():
            if PREFERRED_PROVIDER == "google" and SMALL_MODEL in GEMINI_MODELS:
                new_model = f"gemini/{SMALL_MODEL}"
                mapped = True
            else:
                new_model = f"openai/{SMALL_MODEL}"
                mapped = True

        # Map Sonnet to BIG_MODEL based on provider preference
        elif "sonnet" in clean_v.lower():
            if PREFERRED_PROVIDER == "google" and BIG_MODEL in GEMINI_MODELS:
                new_model = f"gemini/{BIG_MODEL}"
                mapped = True
            else:
                new_model = f"openai/{BIG_MODEL}"
                mapped = True

        # Add prefixes to non-mapped models if they match known lists
        elif not mapped:
            if clean_v in GEMINI_MODELS and not v.startswith("gemini/"):
                new_model = f"gemini/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in OPENAI_MODELS and not v.startswith("openai/"):
                new_model = f"openai/{clean_v}"
                mapped = True  # Technically mapped to add prefix
        # --- Mapping Logic --- END ---

        if mapped:
            logger.debug(f"📌 MODEL MAPPING: '{original_model}' ➡️ '{new_model}'")
        else:
            # If no mapping occurred and no prefix exists, log warning or decide default
            if not v.startswith(("openai/", "gemini/", "anthropic/")):
                logger.warning(
                    f"⚠️ No prefix or mapping rule for model: '{original_model}'. Using as is."
                )
            new_model = v  # Ensure we return the original if no rule applied

        # Store the original model in the values dictionary
        values = info.data
        if isinstance(values, dict):
            values["original_model"] = original_model

        return new_model


class TokenCountRequest(BaseModel):
    model: str
    messages: list[Message]
    system: str | list[SystemContent] | None = None
    tools: list[Tool] | None = None
    thinking: ThinkingConfig | None = None
    tool_choice: dict[str, Any] | None = None
    original_model: str | None = None  # Will store the original model name

    @field_validator("model")
    def validate_model_token_count(cls, v, info):  # Renamed to avoid conflict
        # Use the same logic as MessagesRequest validator
        # NOTE: Pydantic validators might not share state easily if not class methods
        # Re-implementing the logic here for clarity, could be refactored
        original_model = v
        new_model = v  # Default to original value

        logger.debug(
            f"📋 TOKEN COUNT VALIDATION: Original='{original_model}', Preferred='{PREFERRED_PROVIDER}', BIG='{BIG_MODEL}', SMALL='{SMALL_MODEL}'"
        )

        # Remove provider prefixes for easier matching
        clean_v = v
        if clean_v.startswith("anthropic/"):
            clean_v = clean_v[10:]
        elif clean_v.startswith("openai/") or clean_v.startswith("gemini/"):
            clean_v = clean_v[7:]

        # --- Mapping Logic --- START ---
        mapped = False
        # Map Haiku to SMALL_MODEL based on provider preference
        if "haiku" in clean_v.lower():
            if PREFERRED_PROVIDER == "google" and SMALL_MODEL in GEMINI_MODELS:
                new_model = f"gemini/{SMALL_MODEL}"
                mapped = True
            else:
                new_model = f"openai/{SMALL_MODEL}"
                mapped = True

        # Map Sonnet to BIG_MODEL based on provider preference
        elif "sonnet" in clean_v.lower():
            if PREFERRED_PROVIDER == "google" and BIG_MODEL in GEMINI_MODELS:
                new_model = f"gemini/{BIG_MODEL}"
                mapped = True
            else:
                new_model = f"openai/{BIG_MODEL}"
                mapped = True

        # Add prefixes to non-mapped models if they match known lists
        elif not mapped:
            if clean_v in GEMINI_MODELS and not v.startswith("gemini/"):
                new_model = f"gemini/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in OPENAI_MODELS and not v.startswith("openai/"):
                new_model = f"openai/{clean_v}"
                mapped = True  # Technically mapped to add prefix
        # --- Mapping Logic --- END ---

        if mapped:
            logger.debug(f"📌 TOKEN COUNT MAPPING: '{original_model}' ➡️ '{new_model}'")
        else:
            if not v.startswith(("openai/", "gemini/", "anthropic/")):
                logger.warning(
                    f"⚠️ No prefix or mapping rule for token count model: '{original_model}'. Using as is."
                )
            new_model = v  # Ensure we return the original if no rule applied

        # Store the original model in the values dictionary
        values = info.data
        if isinstance(values, dict):
            values["original_model"] = original_model

        return new_model


class TokenCountResponse(BaseModel):
    input_tokens: int


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


class MessagesResponse(BaseModel):
    id: str
    model: str
    role: Literal["assistant"] = "assistant"
    content: list[ContentBlockText | ContentBlockToolUse]
    type: Literal["message"] = "message"
    stop_reason: Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"] | None = None
    stop_sequence: str | None = None
    usage: Usage


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Get request details
    method = request.method
    path = request.url.path

    # Log only basic request details at debug level
    logger.debug(f"Request: {method} {path}")

    # Process the request and get the response
    response = await call_next(request)

    return response


# Not using validation function as we're using the environment API key


def parse_tool_result_content(content):
    """Helper function to properly parse and normalize tool result content."""
    if content is None:
        return "No content provided"

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        result = ""
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                result += item.get("text", "") + "\n"
            elif isinstance(item, str):
                result += item + "\n"
            elif isinstance(item, dict):
                if "text" in item:
                    result += item.get("text", "") + "\n"
                else:
                    try:
                        result += json.dumps(item) + "\n"
                    except (TypeError, ValueError, json.decoder.JSONDecodeError):
                        result += str(item) + "\n"
            else:
                try:
                    result += str(item) + "\n"
                except (TypeError, ValueError):
                    result += "Unparseable content\n"
        return result.strip()

    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text", "")
        try:
            return json.dumps(content)
        except (TypeError, ValueError, json.decoder.JSONDecodeError):
            return str(content)

    # Fallback for any other type
    try:
        return str(content)
    except (TypeError, ValueError):
        return "Unparseable content"


def analyze_conversation_for_tools(messages: list[Message]) -> ConversationState:
    """
    Phase 2: Analyze conversation messages to determine tool call state.

    Args:
        messages: List of conversation messages

    Returns:
        ConversationState: Current state of tool interactions

    Raises:
        ConversationStateError: If conversation state cannot be determined
    """
    state = ConversationState()

    try:
        for i, message in enumerate(messages):
            state.conversation_turn = i

            if message.role == "assistant":
                # Check for tool calls in assistant messages
                if isinstance(message.content, list):
                    for content_block in message.content:
                        if (
                            isinstance(content_block, dict)
                            and content_block.get("type") == "tool_use"
                        ):
                            tool_call = {
                                "id": content_block.get("id"),
                                "name": content_block.get("name"),
                                "input": content_block.get("input", {}),
                            }
                            state.add_tool_call(tool_call)
                        elif hasattr(content_block, "type") and content_block.type == "tool_use":
                            tool_call = {
                                "id": getattr(content_block, "id", None),
                                "name": getattr(content_block, "name", None),
                                "input": getattr(content_block, "input", {}),
                            }
                            state.add_tool_call(tool_call)

            elif message.role == "user":
                # Check for tool results in user messages
                if isinstance(message.content, list):
                    for content_block in message.content:
                        if (
                            isinstance(content_block, dict)
                            and content_block.get("type") == "tool_result"
                        ):
                            tool_call_id = content_block.get("tool_use_id")
                            result = content_block.get("content", {})
                            if tool_call_id:
                                state.complete_tool_call(tool_call_id, result)
                        elif hasattr(content_block, "type") and content_block.type == "tool_result":
                            tool_call_id = getattr(content_block, "tool_use_id", None)
                            result = getattr(content_block, "content", {})
                            if tool_call_id:
                                state.complete_tool_call(tool_call_id, result)

        # Determine final phase based on analysis
        if state.pending_tool_calls:
            state.phase = "tool_result_pending"
        elif state.completed_tool_calls and not state.pending_tool_calls:
            state.phase = "tool_complete"
        else:
            state.phase = "normal"

        logger.debug(
            f"🔍 Conversation analysis: {state.phase}, {len(state.pending_tool_calls)} pending, {len(state.completed_tool_calls)} completed"
        )
        return state

    except Exception as e:
        logger.error(f"❌ Error analyzing conversation for tools: {e}")
        raise ConversationStateError(f"Failed to analyze conversation state: {e}")


def is_azure_responses_api() -> bool:
    """Check if we should use Azure Responses API instead of Chat API.

    Returns True for Responses API endpoints (/responses), False for Chat API endpoints (/chat).
    """
    if not OPENAI_BASE_URL:
        return False

    # Detect Responses API endpoints
    if "/responses" in OPENAI_BASE_URL:
        return True

    # Detect Chat API endpoints (includes /chat/completions, /chat, etc.)
    if "/chat" in OPENAI_BASE_URL:
        return False

    # Default to Chat API for unknown patterns
    return False


def is_azure_chat_api() -> bool:
    """Check if we should use Azure Chat API instead of Responses API.

    Returns True for Chat API endpoints (/chat), False for Responses API endpoints (/responses).
    """
    if not OPENAI_BASE_URL:
        return True  # Default to Chat API

    # Detect Chat API endpoints (includes /chat/completions, /chat, etc.)
    if "/chat" in OPENAI_BASE_URL:
        return True

    # Detect Responses API endpoints
    if "/responses" in OPENAI_BASE_URL:
        return False

    # Default to Chat API for unknown patterns
    return True


def should_use_responses_api_for_model(model: str) -> bool:
    """Check if a specific model should use Responses API instead of Chat API.

    This function determines routing based on model name, regardless of the current
    OPENAI_BASE_URL configuration. The proxy can dynamically route to both endpoints.
    """
    # Extract clean model name
    clean_model = model
    if clean_model.startswith("openai/"):
        clean_model = clean_model[len("openai/") :]
    elif "/" in clean_model:
        clean_model = clean_model.split("/")[-1]

    # Models that require Responses API (user's current setup: gpt-5-codex)
    # Note: Model names are determined by user's Azure deployment names, not hardcoded
    responses_api_models = [
        "gpt-5-codex",  # User's specific deployment for Responses API
        "o3-mini",
        "o3-small",
        "o3",
        "o3-large",
        "o1",
        "o1-mini",
        "o1-pro",
        "gpt-5-code",
        # Add other models that specifically need Responses API here
    ]

    # Note: Chat API models are determined by exclusion from responses_api_models
    # This allows for flexible model assignment without hardcoding both lists

    # Return True for Responses API models, False for Chat API models
    return clean_model in responses_api_models


def convert_anthropic_to_azure_responses(anthropic_request: MessagesRequest) -> dict[str, Any]:
    """Convert Anthropic API request format to Azure Responses API format."""
    # Extract model name without provider prefix
    model = anthropic_request.model
    if model.startswith("openai/"):
        model = model[len("openai/") :]
    elif "/" in model:
        # Remove any provider prefix
        model = model.split("/")[-1]

    # Convert messages to Azure Responses API format
    messages = []

    # Add system message if present
    if anthropic_request.system:
        if isinstance(anthropic_request.system, str):
            messages.append({"role": "system", "content": anthropic_request.system})
        elif isinstance(anthropic_request.system, list):
            system_text = ""
            for block in anthropic_request.system:
                if hasattr(block, "type") and block.type == "text":
                    system_text += block.text + "\n\n"
                elif isinstance(block, dict) and block.get("type") == "text":
                    system_text += block.get("text", "") + "\n\n"
            if system_text:
                messages.append({"role": "system", "content": system_text.strip()})

    # Add conversation messages (simplified conversion)
    for msg in anthropic_request.messages:
        content = msg.content
        if isinstance(content, str):
            messages.append({"role": msg.role, "content": content})
        else:
            # Extract text content from complex content blocks
            text_content = ""
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_content += block.get("text", "") + "\n"
                    elif block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, str):
                            text_content += result_content + "\n"
                        elif isinstance(result_content, list):
                            for item in result_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_content += item.get("text", "") + "\n"
                                elif isinstance(item, str):
                                    text_content += item + "\n"
                elif hasattr(block, "type"):
                    if block.type == "text":
                        text_content += block.text + "\n"

            if text_content.strip():
                messages.append({"role": msg.role, "content": text_content.strip()})
            else:
                messages.append({"role": msg.role, "content": "..."})

    # Get configured token limits from environment for Azure Responses API
    min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "4096"))
    max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "512000"))

    # Ensure proper token limits for Azure Responses API
    max_tokens_value = anthropic_request.max_tokens
    if max_tokens_value and max_tokens_value > 1:
        # Ensure we use at least the minimum configured limit
        max_tokens_value = max(min_tokens_limit, max_tokens_value)
        # Cap at maximum configured limit
        max_tokens_value = min(max_tokens_limit, max_tokens_value)
    else:
        # Default to maximum limit for Azure Responses API models when request has low/no max_tokens
        max_tokens_value = max_tokens_limit

    # Convert tools to Azure Responses API format if present
    azure_request = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens_value,
        "temperature": 1.0,  # Always use temperature=1 for Azure Responses API models
        "stream": anthropic_request.stream,
    }

    # Add tool definitions if present - Azure Responses API format
    if anthropic_request.tools:
        azure_tools = []
        for tool in anthropic_request.tools:
            # Convert to dict if it's a pydantic model
            if hasattr(tool, "dict"):
                tool_dict = tool.dict()
            else:
                tool_dict = tool

            # Azure Responses API expects nested function structure
            azure_tool = {
                "type": "function",
                "function": {
                    "name": tool_dict.get("name", ""),
                    "description": tool_dict.get("description", ""),
                    "parameters": tool_dict.get("input_schema", {}),
                },
            }
            azure_tools.append(azure_tool)

        azure_request["tools"] = azure_tools

        # Handle tool_choice if present
        if anthropic_request.tool_choice:
            if isinstance(anthropic_request.tool_choice, dict):
                if anthropic_request.tool_choice.get("type") == "tool":
                    tool_name = anthropic_request.tool_choice.get("name")
                    if tool_name:
                        azure_request["tool_choice"] = {
                            "type": "function",
                            "function": {"name": tool_name},
                        }
                elif anthropic_request.tool_choice.get("type") == "auto":
                    azure_request["tool_choice"] = "auto"
                elif anthropic_request.tool_choice.get("type") == "any":
                    azure_request["tool_choice"] = "required"

    return azure_request


async def make_azure_responses_api_call(request_data: dict[str, Any]) -> dict[str, Any]:
    """Make a direct call to Azure Responses API with robust error handling and retry logic."""

    async def _make_request() -> dict[str, Any]:
        """Internal request function for retry logic."""
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_KEY,
        }

        # Construct full URL with API version
        url = OPENAI_BASE_URL or ""
        if "?" not in url:
            url = f"{url}?api-version={AZURE_API_VERSION}"
        elif "api-version" not in url:
            url = f"{url}&api-version={AZURE_API_VERSION}"

        logger.info(
            f"Making Azure Responses API request to: {url} (API version: {AZURE_API_VERSION})"
        )

        # Create SSL context using certifi certificates to fix SSL verification issues
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        timeout = aiohttp.ClientTimeout(total=120)

        async with aiohttp.ClientSession(
            timeout=timeout, connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.post(url, json=request_data, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Azure Responses API error {response.status}: {error_text}")
                    # Classify and raise appropriate Azure error
                    azure_error = classify_azure_error(response.status, error_text)
                    raise azure_error

                response_data = await response.json()
                return response_data

    # Use retry logic with exponential backoff
    try:
        start_time = asyncio.get_event_loop().time()
        result = await retry_azure_request(
            _make_request, max_retries=3, request_name="Azure Responses API"
        )
        end_time = asyncio.get_event_loop().time()

        # Record success for fallback manager and logger
        azure_fallback_manager.record_success()

        # Log successful operation with context
        context = {
            "model": request_data.get("model", "unknown"),
            "response_time": int((end_time - start_time) * 1000),  # milliseconds
        }
        log_azure_operation("Azure Responses API", True, context)

        return result

    except AzureAPIError as azure_error:
        # Record failure for fallback manager
        azure_fallback_manager.record_failure(azure_error)

        # Log failed operation with context
        context = {"model": request_data.get("model", "unknown"), "endpoint": OPENAI_BASE_URL}
        log_azure_operation("Azure Responses API", False, context, azure_error)

        # Re-raise the Azure error (will be handled by calling code)
        raise azure_error


def convert_azure_responses_to_anthropic(
    azure_response: dict[str, Any] | None, original_request: MessagesRequest
) -> MessagesResponse:
    """Convert Azure Responses API response to Anthropic format."""
    try:
        # Handle None response (streaming chunks may be None)
        if azure_response is None:
            return MessagesResponse(
                id=f"msg_{uuid.uuid4()}",
                model=original_request.model,
                role="assistant",
                content=[],
                stop_reason="end_turn",
                usage=Usage(input_tokens=0, output_tokens=0),
            )

        # Azure Responses API uses 'output' array, not 'choices'
        output_array = azure_response.get("output", [])
        if not output_array:
            raise ValueError("No output in Azure Responses API response")

        # Find the message output (not reasoning)
        message_output = None
        for output_item in output_array:
            if output_item.get("type") == "message":
                message_output = output_item
                break

        if not message_output:
            raise ValueError("No message output in Azure Responses API response")

        # Process content blocks - Azure Responses API format
        content_blocks = []
        message_content = message_output.get("content", [])

        for content_item in message_content:
            content_type = content_item.get("type")

            if content_type == "output_text":
                # Regular text content
                text_content = content_item.get("text", "")
                if text_content.strip():
                    content_blocks.append({"type": "text", "text": text_content})

            elif content_type == "tool_call":
                # Tool call - convert to Anthropic format
                tool_call_data = content_item.get("function", {})
                tool_name = tool_call_data.get("name", "")
                tool_args_str = tool_call_data.get("arguments", "{}")

                try:
                    tool_input = json.loads(tool_args_str) if tool_args_str else {}
                except json.JSONDecodeError:
                    tool_input = {"arguments": tool_args_str}

                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": content_item.get("id", f"tool_{uuid.uuid4()}"),
                        "name": tool_name,
                        "input": tool_input,
                    }
                )

        # If no content blocks, add empty text
        if not content_blocks:
            content_blocks = [{"type": "text", "text": ""}]

        # Extract usage information (Azure Responses API format)
        usage_info = azure_response.get("usage", {})
        input_tokens = usage_info.get("input_tokens", 0)
        output_tokens = usage_info.get("output_tokens", 0)

        # Determine stop reason - check if we have tool calls
        has_tool_calls = any(block.get("type") == "tool_use" for block in content_blocks)
        stop_reason = "tool_use" if has_tool_calls else "end_turn"

        # Create Anthropic response
        return MessagesResponse(
            id=azure_response.get("id", f"msg_{uuid.uuid4()}"),
            model=original_request.model,
            role="assistant",
            content=content_blocks,
            stop_reason=stop_reason,
            stop_sequence=None,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

    except Exception as e:
        logger.error(f"Error converting Azure response to Anthropic format: {e!s}")
        # Fallback response
        return MessagesResponse(
            id=f"msg_{uuid.uuid4()}",
            model=original_request.model,
            role="assistant",
            content=[{"type": "text", "text": f"Error processing Azure response: {e!s}"}],
            stop_reason="end_turn",
            usage=Usage(input_tokens=0, output_tokens=0),
        )


def convert_anthropic_to_litellm(anthropic_request: MessagesRequest) -> dict[str, Any]:
    """Convert Anthropic API request format to LiteLLM format (which follows OpenAI)."""
    # LiteLLM already handles Anthropic models when using the format model="anthropic/claude-3-opus-20240229"
    # So we just need to convert our Pydantic model to a dict in the expected format

    # Get configured token limits from environment for Azure Responses API
    min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "4096"))
    max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "512000"))

    # Ensure proper token limits for Azure Responses API
    max_tokens_value = anthropic_request.max_tokens
    if max_tokens_value and max_tokens_value > 1:
        # Ensure we use at least the minimum configured limit
        max_tokens_value = max(min_tokens_limit, max_tokens_value)
        # Cap at maximum configured limit
        max_tokens_value = min(max_tokens_limit, max_tokens_value)
    else:
        # Default to maximum limit for Azure Responses API models when request has low/no max_tokens
        max_tokens_value = max_tokens_limit

    # Determine appropriate temperature based on target model type
    # For Azure Responses API models, use temperature=1.0; for others, keep original or default to 1.0
    if anthropic_request.model and (
        "o3" in anthropic_request.model.lower() or "gpt" in anthropic_request.model.lower()
    ):
        temperature = 1.0  # Azure Responses API requires temperature=1.0
    else:
        temperature = (
            anthropic_request.temperature if anthropic_request.temperature is not None else 1.0
        )

    # Initialize the LiteLLM request dict first to ensure we always return the right structure
    litellm_request = {
        "model": anthropic_request.model,  # it understands "anthropic/claude-x" format
        "messages": [],
        "max_tokens": max_tokens_value,
        "temperature": temperature,
        "stream": anthropic_request.stream,
    }

    # Reference the messages list for easier manipulation
    messages = litellm_request["messages"]

    # Add system message if present
    if anthropic_request.system:
        # Handle different formats of system messages
        if isinstance(anthropic_request.system, str):
            # Simple string format
            messages.append({"role": "system", "content": anthropic_request.system})
        elif isinstance(anthropic_request.system, list):
            # List of content blocks
            system_text = ""
            for block in anthropic_request.system:
                if hasattr(block, "type") and block.type == "text":
                    system_text += block.text + "\n\n"
                elif isinstance(block, dict) and block.get("type") == "text":
                    system_text += block.get("text", "") + "\n\n"

            if system_text:
                messages.append({"role": "system", "content": system_text.strip()})

    # Add conversation messages
    for idx, msg in enumerate(anthropic_request.messages):
        content = msg.content
        if isinstance(content, str):
            messages.append({"role": msg.role, "content": content})
        else:
            # Special handling for tool_result in user messages
            # OpenAI/LiteLLM format expects the assistant to call the tool,
            # and the user's next message to include the result as plain text
            if msg.role == "user" and any(
                block.type == "tool_result" for block in content if hasattr(block, "type")
            ):
                # For user messages with tool_result, we need to extract the raw result content
                # Extract regular text content
                text_content = ""

                # First extract any normal text blocks
                for block in content:
                    if hasattr(block, "type") and block.type == "text":
                        text_content += block.text + "\n"

                # Extract tool results
                for block in content:
                    if hasattr(block, "type") and block.type == "tool_result":
                        # Get the raw result content without wrapping it in explanatory text
                        # tool_id = block.tool_use_id if hasattr(block, "tool_use_id") else ""  # unused

                        if hasattr(block, "content"):
                            result_content = block.content

                            # Extract the raw content
                            if isinstance(result_content, str):
                                # If this is the only content, use it directly
                                if not text_content.strip():
                                    messages.append({"role": "user", "content": result_content})
                                    text_content = ""  # Clear text_content to prevent double-adding
                                else:
                                    # Otherwise append it to existing text
                                    text_content += result_content + "\n"
                            elif isinstance(result_content, dict):
                                if result_content.get("type") == "text":
                                    text_content += result_content.get("text", "") + "\n"
                                else:
                                    # If we have a structured object, pass it through as JSON
                                    result_str = parse_tool_result_content(result_content)
                                    text_content += result_str + "\n"
                            elif isinstance(result_content, list):
                                result_str = parse_tool_result_content(result_content)
                                text_content += result_str + "\n"
                            else:
                                # Fallback for any other type
                                text_content += str(result_content) + "\n"

                # Add as a single user message with all the content
                messages.append({"role": "user", "content": text_content.strip()})
            else:
                # Regular handling for other message types
                processed_content = []
                for block in content:
                    if hasattr(block, "type"):
                        if block.type == "text":
                            processed_content.append({"type": "text", "text": block.text})
                        elif block.type == "image":
                            processed_content.append({"type": "image", "source": block.source})
                        elif block.type == "tool_use":
                            # Handle tool use blocks if needed
                            processed_content.append(
                                {
                                    "type": "tool_use",
                                    "id": block.id,
                                    "name": block.name,
                                    "input": block.input,
                                }
                            )
                        elif block.type == "tool_result":
                            # Handle different formats of tool result content
                            processed_content_block: dict[str, Any] = {
                                "type": "tool_result",
                                "tool_use_id": block.tool_use_id
                                if hasattr(block, "tool_use_id")
                                else "",
                            }

                            # Process the content field properly
                            if hasattr(block, "content"):
                                if isinstance(block.content, str):
                                    # If it's a simple string, create a text block for it
                                    processed_content_block["content"] = [
                                        {"type": "text", "text": block.content}
                                    ]
                                elif isinstance(block.content, list):
                                    # If it's already a list of blocks, keep it
                                    processed_content_block["content"] = block.content
                                else:
                                    # Default fallback
                                    processed_content_block["content"] = [
                                        {"type": "text", "text": str(block.content)}
                                    ]
                            else:
                                # Default empty content
                                processed_content_block["content"] = [{"type": "text", "text": ""}]

                            processed_content.append(processed_content_block)

                messages.append({"role": msg.role, "content": processed_content})

    # Cap max_tokens for OpenAI models to their limit of 16384
    if anthropic_request.model.startswith("openai/") or anthropic_request.model.startswith(
        "gemini/"
    ):
        litellm_request["max_tokens"] = min(anthropic_request.max_tokens, 16384)
        logger.debug(
            f"Capping max_tokens to 16384 for OpenAI/Gemini model (original value: {anthropic_request.max_tokens})"
        )

    # Set default value for thinking and only include it for Anthropic models
    # The presence of thinking.enabled is expected by Anthropic but rejected by OpenAI
    if anthropic_request.model.startswith("anthropic/"):
        thinking_config = anthropic_request.thinking or ThinkingConfig(enabled=True)
        litellm_request["thinking"] = thinking_config

    # Add optional parameters if present
    if anthropic_request.stop_sequences:
        litellm_request["stop"] = anthropic_request.stop_sequences

    if anthropic_request.top_p:
        litellm_request["top_p"] = anthropic_request.top_p

    if anthropic_request.top_k:
        litellm_request["top_k"] = anthropic_request.top_k

    # Convert tools to OpenAI format
    if anthropic_request.tools:
        openai_tools = []
        is_gemini_model = anthropic_request.model.startswith("gemini/")

        for tool in anthropic_request.tools:
            # Convert to dict if it's a pydantic model
            if hasattr(tool, "dict"):
                tool_dict = tool.dict()
            else:
                # Ensure tool_dict is a dictionary, handle potential errors if 'tool' isn't dict-like
                try:
                    tool_dict = dict(tool) if not isinstance(tool, dict) else tool
                except (TypeError, ValueError):
                    logger.error(f"Could not convert tool to dict: {tool}")
                    continue  # Skip this tool if conversion fails

            # Clean the schema if targeting a Gemini model
            input_schema = tool_dict.get("input_schema", {})
            if is_gemini_model:
                logger.debug(f"Cleaning schema for Gemini tool: {tool_dict.get('name')}")
                input_schema = clean_gemini_schema(input_schema)

            # Create OpenAI-compatible function tool
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool_dict["name"],
                    "description": tool_dict.get("description", ""),
                    "parameters": input_schema,  # Use potentially cleaned schema
                },
            }
            openai_tools.append(openai_tool)

        litellm_request["tools"] = openai_tools

    # Convert tool_choice to OpenAI format if present
    if anthropic_request.tool_choice:
        if isinstance(anthropic_request.tool_choice, dict):
            tool_choice_dict = anthropic_request.tool_choice
        elif hasattr(anthropic_request.tool_choice, "model_dump"):
            tool_choice_dict = anthropic_request.tool_choice.model_dump()
        elif hasattr(anthropic_request.tool_choice, "dict"):
            tool_choice_dict = anthropic_request.tool_choice.dict()
        else:
            # Fallback to treating it as dict-like
            tool_choice_dict = (
                dict(anthropic_request.tool_choice) if anthropic_request.tool_choice else {}
            )

        # Handle Anthropic's tool_choice format
        choice_type = tool_choice_dict.get("type")
        if choice_type == "auto":
            litellm_request["tool_choice"] = "auto"
        elif choice_type == "any":
            litellm_request["tool_choice"] = "any"
        elif choice_type == "tool" and "name" in tool_choice_dict:
            litellm_request["tool_choice"] = {
                "type": "function",
                "function": {"name": tool_choice_dict["name"]},
            }
        else:
            # Default to auto if we can't determine
            litellm_request["tool_choice"] = "auto"

    return litellm_request


def convert_litellm_to_anthropic(
    litellm_response: dict[str, Any] | Any, original_request: MessagesRequest
) -> MessagesResponse:
    """Convert LiteLLM (OpenAI format) response to Anthropic API response format."""

    # Enhanced response extraction with better error handling
    try:
        # Get the clean model name to check capabilities
        clean_model = original_request.model
        if clean_model.startswith("anthropic/"):
            clean_model = clean_model[len("anthropic/") :]
        elif clean_model.startswith("openai/"):
            clean_model = clean_model[len("openai/") :]

        # Check if this is a Claude model (which supports content blocks)
        # Use the original model name from Claude Code, not the mapped Azure model
        original_model = original_request.model
        is_claude_model = original_model.startswith("claude-")

        # Handle ModelResponse object from LiteLLM
        if hasattr(litellm_response, "choices") and hasattr(litellm_response, "usage"):
            # Extract data from ModelResponse object directly
            choices = getattr(litellm_response, "choices", [])
            message = choices[0].message if choices and len(choices) > 0 else None
            content_text = message.content if message and hasattr(message, "content") else ""
            tool_calls = message.tool_calls if message and hasattr(message, "tool_calls") else None
            finish_reason = choices[0].finish_reason if choices and len(choices) > 0 else "stop"
            usage_info = getattr(litellm_response, "usage", {})
            response_id = getattr(litellm_response, "id", f"msg_{uuid.uuid4()}")
        else:
            # For backward compatibility - handle dict responses
            # If response is a dict, use it, otherwise try to convert to dict
            try:
                response_dict = (
                    litellm_response
                    if isinstance(litellm_response, dict)
                    else litellm_response.dict()
                )
            except AttributeError:
                # If .dict() fails, try to use model_dump or __dict__
                try:
                    if hasattr(litellm_response, "model_dump") and callable(
                        getattr(litellm_response, "model_dump", None)
                    ):
                        # Type: ignore because we've already checked hasattr/callable above
                        response_dict = litellm_response.model_dump()  # type: ignore[attr-defined]
                    else:
                        response_dict = getattr(litellm_response, "__dict__", {})
                except AttributeError:
                    # Fallback - manually extract attributes
                    response_dict = {
                        "id": getattr(litellm_response, "id", f"msg_{uuid.uuid4()}"),
                        "choices": getattr(litellm_response, "choices", [{}]),
                        "usage": getattr(litellm_response, "usage", {}),
                    }

            # Extract the content from the response dict
            choices = response_dict.get("choices", [{}])
            message = choices[0].get("message", {}) if choices and len(choices) > 0 else {}
            content_text = message.get("content", "")
            tool_calls = message.get("tool_calls", None)
            finish_reason = (
                choices[0].get("finish_reason", "stop") if choices and len(choices) > 0 else "stop"
            )
            usage_info = response_dict.get("usage", {})
            response_id = response_dict.get("id", f"msg_{uuid.uuid4()}")

        # Create content list for Anthropic format
        content = []

        # Add text content block if present (text might be None or empty for pure tool call responses)
        if content_text is not None and content_text != "":
            content.append({"type": "text", "text": content_text})

        # Add tool calls if present (tool_use in Anthropic format) - only for Claude models
        if tool_calls and is_claude_model:
            logger.debug(f"Processing tool calls: {tool_calls}")

            # Convert to list if it's not already
            if not isinstance(tool_calls, list):
                tool_calls = [tool_calls]

            for idx, tool_call in enumerate(tool_calls):
                logger.debug(f"Processing tool call {idx}: {tool_call}")

                # Extract function data based on whether it's a dict or object
                if isinstance(tool_call, dict):
                    function = tool_call.get("function", {})
                    tool_id = tool_call.get("id", f"tool_{uuid.uuid4()}")
                    name = function.get("name", "")
                    arguments = function.get("arguments", "{}")
                else:
                    function = getattr(tool_call, "function", None)
                    tool_id = getattr(tool_call, "id", f"tool_{uuid.uuid4()}")
                    name = getattr(function, "name", "") if function else ""
                    arguments = getattr(function, "arguments", "{}") if function else "{}"

                # Convert string arguments to dict if needed
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse tool arguments as JSON: {arguments}")
                        arguments = {"raw": arguments}

                logger.debug(f"Adding tool_use block: id={tool_id}, name={name}, input={arguments}")

                content.append(
                    {"type": "tool_use", "id": tool_id, "name": name, "input": arguments}
                )
        elif tool_calls and not is_claude_model:
            # For non-Claude models, convert tool calls to text format
            logger.debug(f"Converting tool calls to text for non-Claude model: {clean_model}")

            # We'll append tool info to the text content
            tool_text = "\n\nTool usage:\n"

            # Convert to list if it's not already
            if not isinstance(tool_calls, list):
                tool_calls = [tool_calls]

            for idx, tool_call in enumerate(tool_calls):
                # Extract function data based on whether it's a dict or object
                if isinstance(tool_call, dict):
                    function = tool_call.get("function", {})
                    tool_id = tool_call.get("id", f"tool_{uuid.uuid4()}")
                    name = function.get("name", "")
                    arguments = function.get("arguments", "{}")
                else:
                    function = getattr(tool_call, "function", None)
                    tool_id = getattr(tool_call, "id", f"tool_{uuid.uuid4()}")
                    name = getattr(function, "name", "") if function else ""
                    arguments = getattr(function, "arguments", "{}") if function else "{}"

                # Convert string arguments to dict if needed
                if isinstance(arguments, str):
                    try:
                        args_dict = json.loads(arguments)
                        arguments_str = json.dumps(args_dict, indent=2)
                    except json.JSONDecodeError:
                        arguments_str = arguments
                else:
                    arguments_str = json.dumps(arguments, indent=2)

                tool_text += f"Tool: {name}\nArguments: {arguments_str}\n\n"

            # Add or append tool text to content
            if content and content[0]["type"] == "text":
                content[0]["text"] += tool_text
            else:
                content.append({"type": "text", "text": tool_text})

        # Get usage information - extract values safely from object or dict
        if isinstance(usage_info, dict):
            prompt_tokens = usage_info.get("prompt_tokens", 0)
            completion_tokens = usage_info.get("completion_tokens", 0)
        else:
            prompt_tokens = getattr(usage_info, "prompt_tokens", 0)
            completion_tokens = getattr(usage_info, "completion_tokens", 0)

        # Map OpenAI finish_reason to Anthropic stop_reason
        stop_reason = None
        if finish_reason == "stop":
            stop_reason = "end_turn"
        elif finish_reason == "length":
            stop_reason = "max_tokens"
        elif finish_reason == "tool_calls":
            stop_reason = "tool_use"
        else:
            stop_reason = "end_turn"  # Default

        # Make sure content is never empty
        if not content:
            content.append({"type": "text", "text": ""})

        # Create Anthropic-style response
        anthropic_response = MessagesResponse(
            id=response_id,
            model=original_request.model,
            role="assistant",
            content=content,
            stop_reason=stop_reason,
            stop_sequence=None,
            usage=Usage(input_tokens=prompt_tokens, output_tokens=completion_tokens),
        )

        return anthropic_response

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        error_message = f"Error converting response: {e!s}\n\nFull traceback:\n{error_traceback}"
        logger.error(error_message)

        # In case of any error, create a fallback response
        return MessagesResponse(
            id=f"msg_{uuid.uuid4()}",
            model=original_request.model,
            role="assistant",
            content=[
                {
                    "type": "text",
                    "text": f"Error converting response: {e!s}. Please check server logs.",
                }
            ],
            stop_reason="end_turn",
            usage=Usage(input_tokens=0, output_tokens=0),
        )


async def retry_tool_call(func, max_attempts: int | None = None, tool_name: str | None = None):
    """
    Phase 2: Retry tool calls with exponential backoff.

    Args:
        func: The async function to retry
        max_attempts: Maximum retry attempts (defaults to TOOL_CALL_RETRY_ATTEMPTS)
        tool_name: Name of the tool for logging

    Returns:
        The result of the successful function call

    Raises:
        ToolCallError: If all retry attempts fail
    """
    max_attempts = max_attempts or TOOL_CALL_RETRY_ATTEMPTS
    last_exception = None

    for attempt in range(max_attempts):
        try:
            logger.debug(
                f"🔄 Attempting tool call (attempt {attempt + 1}/{max_attempts}): {tool_name}"
            )
            return await func()

        except (TimeoutError, aiohttp.ClientError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                # Exponential backoff: 1s, 2s, 4s, etc.
                wait_time = 2**attempt
                logger.warning(
                    f"⏳ Tool call failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_attempts}): {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ Tool call failed after {max_attempts} attempts: {e}")

        except ToolValidationError as e:
            # Don't retry validation errors
            logger.error(f"❌ Tool validation error (no retry): {e}")
            raise

        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = 2**attempt
                logger.warning(
                    f"⏳ Unexpected tool call error, retrying in {wait_time}s (attempt {attempt + 1}/{max_attempts}): {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ Tool call failed after {max_attempts} attempts: {e}")

    raise ToolCallError(
        f"Tool call failed after {max_attempts} attempts: {last_exception}",
        tool_name=tool_name,
        retry_count=max_attempts,
    )


def validate_tool_schema(tool: dict[str, Any]) -> list[str]:
    """
    Phase 2: Validate tool schema and return list of errors.

    Args:
        tool: Tool definition dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not isinstance(tool, dict):
        errors.append("Tool must be a dictionary")
        return errors

    # Required fields
    if "name" not in tool:
        errors.append("Tool must have a 'name' field")
    elif not isinstance(tool["name"], str) or not tool["name"].strip():
        errors.append("Tool name must be a non-empty string")

    if "input_schema" not in tool:
        errors.append("Tool must have an 'input_schema' field")
    elif not isinstance(tool["input_schema"], dict):
        errors.append("Tool input_schema must be a dictionary")

    # Optional fields validation
    if "description" in tool and not isinstance(tool["description"], str):
        errors.append("Tool description must be a string")

    return errors


async def handle_tool_call_with_fallback(
    litellm_request: dict[str, Any], original_request: MessagesRequest
):
    """
    Phase 2: Handle tool calls with fallback strategies.

    Args:
        litellm_request: The LiteLLM request with tools
        original_request: The original MessagesRequest

    Returns:
        Response from LiteLLM or fallback response

    Raises:
        ToolCallError: If tools fail and fallback is disabled
    """
    try:
        # Validate tools if present
        if litellm_request.get("tools"):
            for tool in litellm_request["tools"]:
                validation_errors = validate_tool_schema(tool)
                if validation_errors:
                    error_msg = f"Tool validation failed: {', '.join(validation_errors)}"
                    if ENABLE_TOOL_FALLBACK:
                        logger.warning(f"⚠️ {error_msg}, removing invalid tool")
                        continue
                    raise ToolValidationError(error_msg, tool_name=tool.get("name"))

        # Attempt the tool call with retry logic
        async def make_request():
            active_router = get_litellm_router()
            if USE_LITELLM_ROUTER and active_router:
                return await active_router.acompletion(**litellm_request)
            return await litellm.acompletion(**litellm_request)

        return await retry_tool_call(make_request, tool_name="litellm_completion")

    except (ToolCallError, ToolValidationError) as e:
        logger.error(f"❌ Tool call failed: {e}")

        if not ENABLE_TOOL_FALLBACK:
            raise

        logger.info("🔄 Falling back to tool-less completion")

        # Remove tools and tool_choice for fallback
        fallback_request = litellm_request.copy()
        fallback_request.pop("tools", None)
        fallback_request.pop("tool_choice", None)

        # Make fallback request
        async def make_fallback_request():
            active_router = get_litellm_router()
            if USE_LITELLM_ROUTER and active_router:
                return await active_router.acompletion(**fallback_request)
            return await litellm.acompletion(**fallback_request)

        return await retry_tool_call(make_fallback_request, tool_name="fallback_completion")


async def stream_with_tools(
    response_generator, original_request: MessagesRequest, conversation_state: ConversationState
):
    """
    Phase 2: Handle streaming responses with tool call support.

    Args:
        response_generator: The LiteLLM response generator
        original_request: The original MessagesRequest
        conversation_state: Current conversation state

    Yields:
        Anthropic-formatted streaming events with tool support

    Raises:
        ToolStreamingError: If tool streaming fails
    """
    try:
        message_id = f"msg_{uuid.uuid4().hex[:24]}"
        current_text = ""
        current_tool_calls = []

        logger.debug(
            f"🔧 Starting tool-aware streaming for conversation phase: {conversation_state.phase}"
        )

        # Send message_start event
        yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant', 'model': original_request.model, 'content': [], 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'output_tokens': 0}}})}\n\n"

        async for chunk in response_generator:
            try:
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # Handle text content
                    if hasattr(delta, "content") and delta.content:
                        if not conversation_state.has_streaming_tools:
                            # Regular text streaming
                            yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                            conversation_state.has_streaming_tools = True

                        current_text += delta.content
                        yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': delta.content}})}\n\n"

                    # Handle tool calls
                    if hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            tool_call_id = getattr(
                                tool_call, "id", f"toolu_{uuid.uuid4().hex[:24]}"
                            )

                            if hasattr(tool_call, "function"):
                                function = tool_call.function
                                tool_name = getattr(function, "name", "unknown_tool")
                                arguments = getattr(function, "arguments", "{}")

                                try:
                                    # Parse arguments if they're a string
                                    if isinstance(arguments, str):
                                        tool_input = json.loads(arguments) if arguments else {}
                                    else:
                                        tool_input = arguments or {}
                                except json.JSONDecodeError as e:
                                    logger.warning(f"⚠️ Failed to parse tool arguments: {e}")
                                    tool_input = {"raw_arguments": arguments}

                                # Create Anthropic-style tool use block
                                tool_use_block = {
                                    "type": "tool_use",
                                    "id": tool_call_id,
                                    "name": tool_name,
                                    "input": tool_input,
                                }

                                # Send tool use events
                                content_index = len(current_tool_calls)
                                yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': content_index, 'content_block': tool_use_block})}\n\n"

                                current_tool_calls.append(tool_use_block)
                                conversation_state.add_tool_call(tool_use_block)

                                if (
                                    ENFORCE_ONE_TOOL_CALL_PER_RESPONSE
                                    and len(current_tool_calls) >= 1
                                ):
                                    logger.debug("🚫 Enforcing single tool call limit")
                                    break

                    # Handle finish_reason
                    if (
                        hasattr(chunk.choices[0], "finish_reason")
                        and chunk.choices[0].finish_reason
                    ):
                        finish_reason = chunk.choices[0].finish_reason
                        stop_reason = (
                            "end_turn"
                            if finish_reason in ["stop", "length"]
                            else "tool_use"
                            if current_tool_calls
                            else "end_turn"
                        )

                        # End content blocks
                        if current_text or current_tool_calls:
                            for i in range(len(current_tool_calls) + (1 if current_text else 0)):
                                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': i})}\n\n"

                        # Send message_delta with stop information
                        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': {'output_tokens': len(current_text.split()) if current_text else 0}})}\n\n"

                        # Send message_stop
                        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
                        break

            except Exception as chunk_error:
                logger.error(f"❌ Error processing streaming chunk: {chunk_error}")
                if not ENABLE_TOOL_FALLBACK:
                    raise ToolStreamingError(f"Failed to process streaming chunk: {chunk_error}")
                continue

    except Exception as e:
        logger.error(f"❌ Tool streaming failed: {e}")
        if ENABLE_TOOL_FALLBACK:
            # Fall back to regular streaming
            logger.info("🔄 Falling back to regular streaming")
            async for event in handle_streaming(response_generator, original_request):
                yield event
        else:
            raise ToolStreamingError(f"Tool streaming failed: {e}")


def is_azure_responses_api_model(model: str) -> bool:
    """Check if the model should use Azure Responses API."""
    # These models use Azure Responses API through our proxy
    azure_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-sonnet",
        "claude-haiku",
    ]
    return model in azure_models or "claude" in model


async def handle_azure_streaming_with_tools(
    azure_request: dict[str, Any],
    original_request: MessagesRequest,
    conversation_state: ConversationState,
):
    """
    Handle Azure Responses API streaming with tool calling support.

    Args:
        azure_request: The Azure API request payload
        original_request: The original MessagesRequest
        conversation_state: Current conversation state

    Yields:
        Anthropic-formatted streaming events with tool support
    """
    try:
        message_id = f"msg_{uuid.uuid4().hex[:24]}"
        current_text = ""
        current_tool_calls = []

        # Send message_start event
        message_start_event = {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": original_request.model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }
        yield f"event: message_start\ndata: {json.dumps(message_start_event)}\n\n"

        # Make streaming request to Azure Responses API
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=300)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {AZURE_OPENAI_KEY}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }

            # Enable streaming in Azure request
            azure_request["stream"] = True

            async with session.post(
                (OPENAI_BASE_URL or "").rstrip("/"),
                headers=headers,
                json=azure_request,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise AzureAPIError(f"Azure streaming failed: {response.status} - {error_text}")

                async for line in response.content:
                    line_text = line.decode("utf-8").strip()
                    if not line_text:
                        continue

                    if line_text.startswith("data: "):
                        data_content = line_text[6:]  # Remove "data: " prefix
                        if data_content == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_content)

                            # Azure Responses API format: output[] array
                            output_array = chunk.get("output", [])
                            for output_item in output_array:
                                if output_item.get("type") == "message":
                                    # Process content blocks
                                    content_blocks = output_item.get("content", [])

                                    for content_block in content_blocks:
                                        content_type = content_block.get("type")

                                        if content_type == "output_text":
                                            # Handle text streaming
                                            text_content = content_block.get("text", "")
                                            if text_content:
                                                current_text += text_content

                                                # Send content_block_delta event
                                                delta_event = {
                                                    "type": "content_block_delta",
                                                    "index": 0,
                                                    "delta": {
                                                        "type": "text_delta",
                                                        "text": text_content,
                                                    },
                                                }
                                                yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"

                                        elif content_type == "tool_use":
                                            # Handle tool calls
                                            tool_call = {
                                                "id": content_block.get(
                                                    "id", f"call_{uuid.uuid4().hex[:8]}"
                                                ),
                                                "type": "tool_use",
                                                "name": content_block.get("name", ""),
                                                "input": content_block.get("input", {}),
                                            }
                                            current_tool_calls.append(tool_call)

                                            # Send tool_use event
                                            start_event = {
                                                "type": "content_block_start",
                                                "index": len(current_tool_calls),
                                                "content_block": tool_call,
                                            }
                                            yield f"event: content_block_start\ndata: {json.dumps(start_event)}\n\n"

                                            stop_event = {
                                                "type": "content_block_stop",
                                                "index": len(current_tool_calls),
                                            }
                                            yield f"event: content_block_stop\ndata: {json.dumps(stop_event)}\n\n"

                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse Azure streaming chunk: {e}")
                            continue

        # Send message_stop event
        stop_event = {"type": "message_stop"}
        yield f"event: message_stop\ndata: {json.dumps(stop_event)}\n\n"

    except Exception as e:
        logger.error(f"❌ Azure streaming with tools failed: {e}")
        raise ToolStreamingError(f"Azure streaming failed: {e}")


async def handle_streaming(response_generator, original_request: MessagesRequest):
    """Handle streaming responses from LiteLLM and convert to Anthropic format."""
    try:
        # Send message_start event
        message_id = f"msg_{uuid.uuid4().hex[:24]}"  # Format similar to Anthropic's IDs

        message_data = {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message",
                "role": "assistant",
                "model": original_request.model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 0,
                },
            },
        }
        yield f"event: message_start\ndata: {json.dumps(message_data)}\n\n"

        # Content block index for the first text block
        yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

        # Send a ping to keep the connection alive (Anthropic does this)
        yield f"event: ping\ndata: {json.dumps({'type': 'ping'})}\n\n"

        tool_index = None
        # current_tool_call = None  # unused
        tool_content = ""
        accumulated_text = ""  # Track accumulated text content
        text_sent = False  # Track if we've sent any text content
        text_block_closed = False  # Track if text block is closed
        # input_tokens = 0  # unused
        output_tokens = 0
        has_sent_stop_reason = False
        last_tool_index = 0
        anthropic_tool_index = 0  # Initialize to avoid unbound variable error

        # Process each chunk
        async for chunk in response_generator:
            try:
                # Check if this is the end of the response with usage data
                if hasattr(chunk, "usage") and chunk.usage is not None:
                    if hasattr(chunk.usage, "completion_tokens"):
                        output_tokens = chunk.usage.completion_tokens

                # Handle text content
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    choice = chunk.choices[0]

                    # Get the delta from the choice
                    if hasattr(choice, "delta"):
                        delta = choice.delta
                    else:
                        # If no delta, try to get message
                        delta = getattr(choice, "message", {})

                    # Check for finish_reason to know when we're done
                    finish_reason = getattr(choice, "finish_reason", None)

                    # Process text content
                    delta_content = None

                    # Handle different formats of delta content
                    if hasattr(delta, "content"):
                        delta_content = getattr(delta, "content", None)
                    elif isinstance(delta, dict) and "content" in delta:
                        delta_content = delta["content"]

                    # Accumulate text content
                    if delta_content is not None and delta_content != "":
                        accumulated_text += delta_content

                        # Always emit text deltas if no tool calls started
                        if tool_index is None and not text_block_closed:
                            text_sent = True
                            yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': delta_content}})}\n\n"

                    # Process tool calls
                    delta_tool_calls = None

                    # Handle different formats of tool calls
                    if hasattr(delta, "tool_calls"):
                        delta_tool_calls = getattr(delta, "tool_calls", None)
                    elif isinstance(delta, dict) and "tool_calls" in delta:
                        delta_tool_calls = delta["tool_calls"]

                    # Process tool calls if any
                    if delta_tool_calls:
                        # First tool call we've seen - need to handle text properly
                        if tool_index is None:
                            # If we've been streaming text, close that text block
                            if text_sent and not text_block_closed:
                                text_block_closed = True
                                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                            # If we've accumulated text but not sent it, we need to emit it now
                            # This handles the case where the first delta has both text and a tool call
                            elif accumulated_text and not text_sent and not text_block_closed:
                                # Send the accumulated text
                                text_sent = True
                                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': accumulated_text}})}\n\n"
                                # Close the text block
                                text_block_closed = True
                                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                            # Close text block even if we haven't sent anything - models sometimes emit empty text blocks
                            elif not text_block_closed:
                                text_block_closed = True
                                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                        # Convert to list if it's not already
                        if not isinstance(delta_tool_calls, list):
                            delta_tool_calls = [delta_tool_calls]

                        for tool_call in delta_tool_calls:
                            # Get the index of this tool call (for multiple tools)
                            current_index = None
                            if isinstance(tool_call, dict) and "index" in tool_call:
                                current_index = tool_call["index"]
                            elif hasattr(tool_call, "index"):
                                current_index = getattr(tool_call, "index", 0)
                            else:
                                current_index = 0

                            # Check if this is a new tool or a continuation
                            if tool_index is None or current_index != tool_index:
                                # New tool call - create a new tool_use block
                                tool_index = current_index
                                last_tool_index += 1
                                anthropic_tool_index = last_tool_index

                                # Extract function info
                                if isinstance(tool_call, dict):
                                    function = tool_call.get("function", {})
                                    name = (
                                        function.get("name", "")
                                        if isinstance(function, dict)
                                        else ""
                                    )
                                    tool_id = tool_call.get("id", f"toolu_{uuid.uuid4().hex[:24]}")
                                else:
                                    function = getattr(tool_call, "function", None)
                                    name = getattr(function, "name", "") if function else ""
                                    tool_id = getattr(
                                        tool_call, "id", f"toolu_{uuid.uuid4().hex[:24]}"
                                    )

                                # Start a new tool_use block
                                yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': anthropic_tool_index, 'content_block': {'type': 'tool_use', 'id': tool_id, 'name': name, 'input': {}}})}\n\n"
                                # current_tool_call = tool_call  # unused
                                tool_content = ""

                            # Extract function arguments
                            arguments = None
                            if isinstance(tool_call, dict) and "function" in tool_call:
                                function = tool_call.get("function", {})
                                arguments = (
                                    function.get("arguments", "")
                                    if isinstance(function, dict)
                                    else ""
                                )
                            elif hasattr(tool_call, "function"):
                                function = getattr(tool_call, "function", None)
                                arguments = getattr(function, "arguments", "") if function else ""

                            # If we have arguments, send them as a delta
                            if arguments:
                                # Try to detect if arguments are valid JSON or just a fragment
                                try:
                                    # If it's already a dict, use it
                                    if isinstance(arguments, dict):
                                        args_json = json.dumps(arguments)
                                    else:
                                        # Otherwise, try to parse it
                                        json.loads(arguments)
                                        args_json = arguments
                                except (json.JSONDecodeError, TypeError):
                                    # If it's a fragment, treat it as a string
                                    args_json = arguments

                                # Add to accumulated tool content
                                tool_content += args_json if isinstance(args_json, str) else ""

                                # Send the update
                                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': anthropic_tool_index, 'delta': {'type': 'input_json_delta', 'partial_json': args_json}})}\n\n"

                    # Process finish_reason - end the streaming response
                    if finish_reason and not has_sent_stop_reason:
                        has_sent_stop_reason = True

                        # Close any open tool call blocks
                        if tool_index is not None:
                            for i in range(1, last_tool_index + 1):
                                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': i})}\n\n"

                        # If we accumulated text but never sent or closed text block, do it now
                        if not text_block_closed:
                            if accumulated_text and not text_sent:
                                # Send the accumulated text
                                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': accumulated_text}})}\n\n"
                            # Close the text block
                            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                        # Map OpenAI finish_reason to Anthropic stop_reason
                        stop_reason = "end_turn"
                        if finish_reason == "length":
                            stop_reason = "max_tokens"
                        elif finish_reason == "tool_calls":
                            stop_reason = "tool_use"
                        elif finish_reason == "stop":
                            stop_reason = "end_turn"

                        # Send message_delta with stop reason and usage
                        usage = {"output_tokens": output_tokens}

                        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': stop_reason, 'stop_sequence': None}, 'usage': usage})}\n\n"

                        # Send message_stop event
                        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

                        # Send final [DONE] marker to match Anthropic's behavior
                        yield "data: [DONE]\n\n"
                        return
            except Exception as e:
                # Log error but continue processing other chunks
                logger.error(f"Error processing chunk: {e!s}")
                continue

        # If we didn't get a finish reason, close any open blocks
        if not has_sent_stop_reason:
            # Close any open tool call blocks
            if tool_index is not None:
                for i in range(1, last_tool_index + 1):
                    yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': i})}\n\n"

            # Close the text content block
            yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

            # Send final message_delta with usage
            usage = {"output_tokens": output_tokens}

            yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None}, 'usage': usage})}\n\n"

            # Send message_stop event
            yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

            # Send final [DONE] marker to match Anthropic's behavior
            yield "data: [DONE]\n\n"

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        error_message = f"Error in streaming: {e!s}\n\nFull traceback:\n{error_traceback}"
        logger.error(error_message)

        # Send error message_delta
        yield f"event: message_delta\ndata: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'error', 'stop_sequence': None}, 'usage': {'output_tokens': 0}})}\n\n"

        # Send message_stop event
        yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

        # Send final [DONE] marker
        yield "data: [DONE]\n\n"


@app.post("/v1/messages")
async def create_message(request: MessagesRequest, raw_request: Request):
    try:
        # print the body here
        body = await raw_request.body()

        # Parse the raw body as JSON since it's bytes
        body_json = json.loads(body.decode("utf-8"))
        original_model = body_json.get("model", "unknown")

        # Get the display name for logging, just the model name without provider prefix
        display_model = original_model
        if "/" in display_model:
            display_model = display_model.split("/")[-1]

        # Clean model name for capability check
        clean_model = request.model
        if clean_model.startswith("anthropic/"):
            clean_model = clean_model[len("anthropic/") :]
        elif clean_model.startswith("openai/"):
            clean_model = clean_model[len("openai/") :]

        logger.debug(f"📊 PROCESSING REQUEST: Model={request.model}, Stream={request.stream}")

        # All requests now route through LiteLLM with unified Azure integration
        # The unified routing handles both Chat and Responses APIs transparently
        # Convert Anthropic request to LiteLLM format
        if azure_fallback_manager.should_use_fallback():
            logger.warning("🔄 Azure fallback mode active - returning fallback response")
            fallback_reason = azure_fallback_manager.get_fallback_reason()

            # Create fallback response in the expected format
            fallback_response = await create_fallback_response(body_json, fallback_reason)

            # Convert to MessagesResponse format
            anthropic_response = MessagesResponse(
                id=fallback_response["id"],
                model=fallback_response["model"],
                role=fallback_response["role"],
                content=fallback_response["content"],
                stop_reason=fallback_response["stop_reason"],
                usage=Usage(
                    input_tokens=fallback_response["usage"]["input_tokens"],
                    output_tokens=fallback_response["usage"]["output_tokens"],
                ),
            )
        else:
            # Try Azure API with robust error handling
            azure_request = None  # Initialize to avoid unbound variable
            try:
                # Convert to Azure Responses format
                azure_request = convert_anthropic_to_azure_responses(request)

                # Handle streaming mode for Azure
                if request.stream:
                    logger.info(
                        "🚀 Starting Azure Responses API streaming with tool calling support"
                    )

                    # Convert to Azure format for streaming
                    azure_stream_request = convert_anthropic_to_azure_responses(request)

                    # Phase 2: Tool Call Lifecycle Management for Azure
                    conversation_state = analyze_conversation_for_tools(request.messages)

                    # Use Azure streaming with tool support
                    try:
                        return StreamingResponse(
                            handle_azure_streaming_with_tools(
                                azure_stream_request, request, conversation_state
                            ),
                            media_type="text/event-stream",
                        )
                    except Exception as e:
                        logger.error(f"❌ Azure streaming failed: {e}")
                        if ENABLE_TOOL_FALLBACK:
                            logger.info("🔄 Falling back to Azure non-streaming")
                            azure_request["stream"] = False
                            # Continue with non-streaming below
                        else:
                            raise AzureAPIError(f"Azure streaming failed: {e}")
                else:
                    azure_request["stream"] = False

                # Make direct Azure API call with robust error handling (non-streaming fallback)
                azure_response = await make_azure_responses_api_call(azure_request)

                # Convert back to Anthropic format
                anthropic_response = convert_azure_responses_to_anthropic(azure_response, request)

            except AzureAPIError as azure_error:
                logger.error(f"❌ Azure API failed: {azure_error.error_type} - {azure_error!s}")

                # Check if we should immediately enter fallback mode
                if isinstance(azure_error, (AzureAuthenticationError, AzureConfigurationError)):
                    logger.warning("🔄 Critical Azure error - triggering immediate fallback")
                    fallback_reason = azure_fallback_manager.get_fallback_reason()
                    if not fallback_reason:
                        fallback_reason = f"Critical Azure error: {azure_error.error_type}"

                    # Create fallback response
                    fallback_response = await create_fallback_response(body_json, fallback_reason)

                    # Convert to MessagesResponse format
                    anthropic_response = MessagesResponse(
                        id=fallback_response["id"],
                        model=fallback_response["model"],
                        role=fallback_response["role"],
                        content=fallback_response["content"],
                        stop_reason=fallback_response["stop_reason"],
                        usage=Usage(
                            input_tokens=fallback_response["usage"]["input_tokens"],
                            output_tokens=fallback_response["usage"]["output_tokens"],
                        ),
                    )
                else:
                    # For other errors, return user-friendly error message
                    user_friendly_msg = extract_user_friendly_message(azure_error)
                    raise HTTPException(
                        status_code=azure_error.status_code or 500, detail=user_friendly_msg
                    )

            num_tools = len(request.tools) if request.tools else 0
            log_request_beautifully(
                "POST",
                raw_request.url.path,
                display_model,
                azure_request.get("model", "unknown") if azure_request else "unknown",
                len(azure_request.get("messages", [])) if azure_request else 0,
                num_tools,
                200,
            )

            return anthropic_response

        # Convert Anthropic request to LiteLLM format
        litellm_request = convert_anthropic_to_litellm(request)

        # Determine which API key to use based on the model
        if request.model.startswith("openai/"):
            litellm_request["api_key"] = OPENAI_API_KEY
            logger.debug(f"Using OpenAI API key for model: {request.model}")
        elif request.model.startswith("gemini/"):
            litellm_request["api_key"] = GEMINI_API_KEY
            logger.debug(f"Using Gemini API key for model: {request.model}")
        else:
            litellm_request["api_key"] = ANTHROPIC_API_KEY
            logger.debug(f"Using Anthropic API key for model: {request.model}")

        # For OpenAI models - modify request format to work with limitations
        if "openai" in litellm_request["model"] and "messages" in litellm_request:
            logger.debug(f"Processing OpenAI model request: {litellm_request['model']}")

            # For OpenAI models, we need to convert content blocks to simple strings
            # and handle other requirements
            for i, msg in enumerate(litellm_request["messages"]):
                # Special case - handle message content directly when it's a list of tool_result
                # This is a specific case we're seeing in the error
                if "content" in msg and isinstance(msg["content"], list):
                    is_only_tool_result = True
                    for block in msg["content"]:
                        if not isinstance(block, dict) or block.get("type") != "tool_result":
                            is_only_tool_result = False
                            break

                    if is_only_tool_result and len(msg["content"]) > 0:
                        logger.warning(
                            "Found message with only tool_result content - converting to function result format"
                        )

                        # Get the first tool result to extract as a direct function result
                        # This handles bash and other tools properly
                        block = msg["content"][0]  # Take the first tool result
                        # tool_use_id = block.get("tool_use_id", "")  # unused
                        result_content = block.get("content", "")

                        # For function tools like Bash, we need to pass the raw result
                        # rather than embedding it in explanatory text
                        if isinstance(result_content, str):
                            # Direct string result - pass it directly
                            litellm_request["messages"][i]["content"] = result_content
                        elif isinstance(result_content, dict):
                            # Dictionary result - pass it as JSON
                            try:
                                litellm_request["messages"][i]["content"] = json.dumps(
                                    result_content
                                )
                            except (TypeError, ValueError, json.decoder.JSONDecodeError):
                                litellm_request["messages"][i]["content"] = str(result_content)
                        elif isinstance(result_content, list):
                            # Extract text content if available
                            extracted_content = ""
                            for item in result_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    extracted_content += item.get("text", "") + "\n"
                                elif isinstance(item, str):
                                    extracted_content += item + "\n"
                                else:
                                    try:
                                        extracted_content += json.dumps(item) + "\n"
                                    except (TypeError, ValueError, json.decoder.JSONDecodeError):
                                        extracted_content += str(item) + "\n"
                            litellm_request["messages"][i]["content"] = (
                                extracted_content.strip() or "..."
                            )
                        else:
                            # Fallback for any other type
                            litellm_request["messages"][i]["content"] = str(result_content) or "..."

                        logger.warning(
                            f"Converted tool_result to raw content format: {litellm_request['messages'][i]['content'][:200]}..."
                        )
                        continue  # Skip normal processing for this message

                # 1. Handle content field - normal case
                if "content" in msg:
                    # Check if content is a list (content blocks)
                    if isinstance(msg["content"], list):
                        # Convert complex content blocks to simple string
                        text_content = ""
                        for block in msg["content"]:
                            if isinstance(block, dict):
                                # Handle different content block types
                                if block.get("type") == "text":
                                    text_content += block.get("text", "") + "\n"

                                # Handle tool_result content blocks - extract raw content
                                elif block.get("type") == "tool_result":
                                    # For tools like Bash, we need to extract the raw content
                                    # rather than embedding it in explanatory text
                                    result_content = block.get("content", "")

                                    # Extract the raw content without wrapping it
                                    if isinstance(result_content, str):
                                        # Direct string result
                                        text_content += result_content + "\n"
                                    elif isinstance(result_content, list):
                                        # Extract text content if available
                                        for item in result_content:
                                            if (
                                                isinstance(item, dict)
                                                and item.get("type") == "text"
                                            ):
                                                text_content += item.get("text", "") + "\n"
                                            elif isinstance(item, str):
                                                text_content += item + "\n"
                                            else:
                                                try:
                                                    text_content += json.dumps(item) + "\n"
                                                except (
                                                    TypeError,
                                                    ValueError,
                                                    json.decoder.JSONDecodeError,
                                                ):
                                                    text_content += str(item) + "\n"
                                    elif isinstance(result_content, dict):
                                        # Handle dictionary content
                                        if result_content.get("type") == "text":
                                            text_content += result_content.get("text", "") + "\n"
                                        else:
                                            try:
                                                text_content += json.dumps(result_content) + "\n"
                                            except (
                                                TypeError,
                                                ValueError,
                                                json.decoder.JSONDecodeError,
                                            ):
                                                text_content += str(result_content) + "\n"
                                    else:
                                        # Fallback for any other type
                                        try:
                                            text_content += str(result_content) + "\n"
                                        except (TypeError, ValueError):
                                            text_content += "Unparseable content\n"

                                # Handle tool_use content blocks
                                elif block.get("type") == "tool_use":
                                    tool_name = block.get("name", "unknown")
                                    tool_id = block.get("id", "unknown")
                                    tool_input = json.dumps(block.get("input", {}))
                                    text_content += f"[Tool: {tool_name} (ID: {tool_id})]\nInput: {tool_input}\n\n"

                                # Handle image content blocks
                                elif block.get("type") == "image":
                                    text_content += (
                                        "[Image content - not displayed in text format]\n"
                                    )

                        # Make sure content is never empty for OpenAI models
                        if not text_content.strip():
                            text_content = "..."

                        litellm_request["messages"][i]["content"] = text_content.strip()
                    # Also check for None or empty string content
                    elif msg["content"] is None:
                        litellm_request["messages"][i]["content"] = (
                            "..."  # Empty content not allowed
                        )

                # 2. Remove any fields OpenAI doesn't support in messages
                for key in list(msg.keys()):
                    if key not in ["role", "content", "name", "tool_call_id", "tool_calls"]:
                        logger.warning(f"Removing unsupported field from message: {key}")
                        del msg[key]

            # 3. Final validation - check for any remaining invalid values and dump full message details
            for i, msg in enumerate(litellm_request["messages"]):
                # Log the message format for debugging
                logger.debug(
                    f"Message {i} format check - role: {msg.get('role')}, content type: {type(msg.get('content'))}"
                )

                # If content is still a list or None, replace with placeholder
                if isinstance(msg.get("content"), list):
                    logger.warning(
                        f"CRITICAL: Message {i} still has list content after processing: {json.dumps(msg.get('content'))}"
                    )
                    # Last resort - stringify the entire content as JSON
                    litellm_request["messages"][i]["content"] = (
                        f"Content as JSON: {json.dumps(msg.get('content'))}"
                    )
                elif msg.get("content") is None:
                    logger.warning(f"Message {i} has None content - replacing with placeholder")
                    litellm_request["messages"][i]["content"] = "..."  # Fallback placeholder

        # Only log basic info about the request, not the full details
        logger.debug(
            f"Request for model: {litellm_request.get('model')}, stream: {litellm_request.get('stream', False)}"
        )

        # Phase 2: Tool Call Lifecycle Management
        # Analyze conversation state for tool handling
        conversation_state = analyze_conversation_for_tools(request.messages)
        logger.debug(f"🔍 Conversation state: {conversation_state.phase}")

        num_tools = len(request.tools) if request.tools else 0

        # Handle streaming mode with tool support
        if request.stream:
            log_request_beautifully(
                "POST",
                raw_request.url.path,
                display_model,
                litellm_request.get("model"),
                len(litellm_request["messages"]),
                num_tools,
                200,  # Assuming success at this point
            )

            # Use Phase 2 tool-aware streaming if tools are present
            if num_tools > 0 or conversation_state.phase != "normal":
                try:
                    response_generator = await handle_tool_call_with_fallback(
                        litellm_request, request
                    )
                    return StreamingResponse(
                        stream_with_tools(response_generator, request, conversation_state),
                        media_type="text/event-stream",
                    )
                except Exception as e:
                    logger.error(f"❌ Tool-aware streaming failed: {e}")
                    if ENABLE_TOOL_FALLBACK:
                        logger.info("🔄 Falling back to regular streaming")
                        response_generator = await litellm.acompletion(**litellm_request)
                        return StreamingResponse(
                            handle_streaming(response_generator, request),
                            media_type="text/event-stream",
                        )
                    raise HTTPException(
                        status_code=500, detail=f"Tool streaming failed: {e}"
                    ) from e
            else:
                # Regular streaming for non-tool requests
                response_generator = await litellm.acompletion(**litellm_request)
                return StreamingResponse(
                    handle_streaming(response_generator, request), media_type="text/event-stream"
                )
        else:
            # Handle non-streaming mode with tool support
            log_request_beautifully(
                "POST",
                raw_request.url.path,
                display_model,
                litellm_request.get("model"),
                len(litellm_request["messages"]),
                num_tools,
                200,  # Assuming success at this point
            )
            start_time = time.time()

            # Use Phase 2 tool-aware completion if tools are present
            if num_tools > 0 or conversation_state.phase != "normal":
                try:
                    litellm_response = await handle_tool_call_with_fallback(
                        litellm_request, request
                    )
                except Exception as e:
                    logger.error(f"❌ Tool-aware completion failed: {e}")
                    if ENABLE_TOOL_FALLBACK:
                        logger.info("🔄 Falling back to regular completion")
                        litellm_response = litellm.completion(**litellm_request)
                    else:
                        raise HTTPException(
                            status_code=500, detail=f"Tool completion failed: {e}"
                        ) from e
            else:
                # Regular completion for non-tool requests
                litellm_response = litellm.completion(**litellm_request)
            logger.debug(
                f"✅ RESPONSE RECEIVED: Model={litellm_request.get('model')}, Time={time.time() - start_time:.2f}s"
            )

            # Convert LiteLLM response to Anthropic format
            anthropic_response = convert_litellm_to_anthropic(litellm_response, request)

        return anthropic_response

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()

        # Capture as much info as possible about the error
        error_details = {"error": str(e), "type": type(e).__name__, "traceback": error_traceback}

        # Check for LiteLLM-specific attributes
        for attr in ["message", "status_code", "response", "llm_provider", "model"]:
            if hasattr(e, attr):
                error_details[attr] = getattr(e, attr)

        # Check for additional exception details in dictionaries
        if hasattr(e, "__dict__"):
            for key, value in e.__dict__.items():
                if key not in error_details and key not in ["args", "__traceback__"]:
                    error_details[key] = str(value)

        # Log all error details
        def safe_json_serialize(obj, indent=2):
            """Safely serialize objects to JSON, handling non-serializable types."""
            try:
                return json.dumps(obj, indent=indent)
            except (TypeError, ValueError):
                # Handle non-serializable objects by converting them to strings
                safe_obj = {}
                for key, value in obj.items():
                    try:
                        json.dumps(value)  # Test if value is serializable
                        safe_obj[key] = value
                    except (TypeError, ValueError):
                        safe_obj[key] = str(value)  # Convert non-serializable to string
                return json.dumps(safe_obj, indent=indent)

        logger.error(f"Error processing request: {safe_json_serialize(error_details)}")

        # Format error for response
        error_message = f"Error: {e!s}"
        if error_details.get("message"):
            error_message += f"\nMessage: {error_details['message']}"
        if error_details.get("response"):
            error_message += f"\nResponse: {error_details['response']}"

        # Return detailed error
        status_code = error_details.get("status_code", 500)
        raise HTTPException(status_code=status_code, detail=error_message) from e


@app.post("/v1/messages/count_tokens")
async def count_tokens(request: TokenCountRequest, raw_request: Request):
    try:
        # Log the incoming token count request
        original_model = request.original_model or request.model

        # Get the display name for logging, just the model name without provider prefix
        display_model = original_model
        if "/" in display_model:
            display_model = display_model.split("/")[-1]

        # Clean model name for capability check
        clean_model = request.model
        if clean_model.startswith("anthropic/"):
            clean_model = clean_model[len("anthropic/") :]
        elif clean_model.startswith("openai/"):
            clean_model = clean_model[len("openai/") :]

        # Convert the messages to a format LiteLLM can understand
        converted_request = convert_anthropic_to_litellm(
            MessagesRequest(
                model=request.model,
                max_tokens=100,  # Arbitrary value not used for token counting
                messages=request.messages,
                system=request.system,
                tools=request.tools,
                tool_choice=request.tool_choice,
                thinking=request.thinking,
            )
        )

        # Use LiteLLM's token_counter function
        try:
            # Import token_counter function
            from litellm import token_counter  # type: ignore[import-unresolved]

            # Log the request beautifully
            num_tools = len(request.tools) if request.tools else 0

            log_request_beautifully(
                "POST",
                raw_request.url.path,
                display_model,
                converted_request.get("model"),
                len(converted_request["messages"]),
                num_tools,
                200,  # Assuming success at this point
            )

            # Count tokens
            token_count = token_counter(
                model=converted_request["model"],
                messages=converted_request["messages"],
            )

            # Return Anthropic-style response
            return TokenCountResponse(input_tokens=token_count)

        except ImportError:
            logger.error("Could not import token_counter from litellm")
            # Fallback to a simple approximation
            return TokenCountResponse(input_tokens=1000)  # Default fallback

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(f"Error counting tokens: {e!s}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Error counting tokens: {e!s}") from e


@app.get("/")
async def root():
    return {"message": "Anthropic Proxy for LiteLLM"}


@app.get("/performance/metrics")
async def performance_metrics():
    """Get comprehensive performance metrics for the proxy."""
    from .azure_unified_integration import get_global_performance_metrics

    # Get router metrics
    router = get_litellm_router()

    # Get Azure integration metrics
    global_metrics = get_global_performance_metrics()

    # Compile comprehensive metrics
    metrics = {
        "router": {
            "initialized": router is not None,
            "initialization_attempted": _router_init_attempted,
            "lazy_loading": True,
        },
        "azure_integration": global_metrics,
        "system": {
            "use_litellm_router": USE_LITELLM_ROUTER,
            "azure_api_version": AZURE_API_VERSION,
            "base_url_configured": bool(OPENAI_BASE_URL),
        },
    }

    return metrics


@app.get("/performance/cache/status")
async def cache_status():
    """Get detailed cache status and statistics."""
    from .azure_unified_integration import _MODEL_ROUTING_CACHE, _SESSION_CACHE, _TRANSFORM_CACHE

    return {
        "caches": {
            "model_routing": {
                "size": len(_MODEL_ROUTING_CACHE),
                "entries": list(_MODEL_ROUTING_CACHE.keys())[:10],  # First 10 for security
            },
            "sessions": {
                "size": len(_SESSION_CACHE),
                "active_endpoints": list(_SESSION_CACHE.keys())[:5],  # First 5 for security
            },
            "transformations": {
                "size": len(_TRANSFORM_CACHE),
                "cache_efficiency": "high" if len(_TRANSFORM_CACHE) > 10 else "medium",
            },
        },
        "optimization_status": {
            "lazy_router_initialization": True,
            "session_pooling": True,
            "request_transformation_caching": True,
            "model_routing_optimization": True,
        },
    }


@app.get("/performance/cache/clear")
async def clear_caches():
    """Clear all performance caches (admin operation)."""
    from .azure_unified_integration import (
        _MODEL_ROUTING_CACHE,
        _SESSION_CACHE,
        _TRANSFORM_CACHE,
        cleanup_cached_sessions,
    )

    # Get counts before clearing
    before_counts = {
        "routing_cache": len(_MODEL_ROUTING_CACHE),
        "session_cache": len(_SESSION_CACHE),
        "transform_cache": len(_TRANSFORM_CACHE),
    }

    # Clear caches
    _MODEL_ROUTING_CACHE.clear()
    _TRANSFORM_CACHE.clear()

    # Clean up sessions properly
    await cleanup_cached_sessions()

    return {
        "status": "caches_cleared",
        "before_counts": before_counts,
        "after_counts": {
            "routing_cache": len(_MODEL_ROUTING_CACHE),
            "session_cache": len(_SESSION_CACHE),
            "transform_cache": len(_TRANSFORM_CACHE),
        },
    }


@app.get("/performance/benchmark")
async def performance_benchmark():
    """Run a quick performance benchmark of the routing system."""
    import time

    # Test model routing performance
    models = ["gpt-5", "claude-3-5-sonnet-20241022", "o3-mini", "gpt-5-chat"]

    # Cold routing (first time)
    cold_start = time.time()
    from .azure_unified_integration import AzureUnifiedProvider

    provider = AzureUnifiedProvider(
        "test", "https://test.cognitiveservices.azure.com", "2025-01-01-preview"
    )

    for model in models:
        provider.should_use_responses_api(model)
    cold_end = time.time()

    # Warm routing (cached)
    warm_start = time.time()
    for model in models:
        provider.should_use_responses_api(model)
    warm_end = time.time()

    return {
        "routing_performance": {
            "cold_routing_ms": (cold_end - cold_start) * 1000,
            "warm_routing_ms": (warm_end - warm_start) * 1000,
            "speedup_factor": (cold_end - cold_start) / max(warm_end - warm_start, 0.001),
            "models_tested": models,
        },
        "optimization_effectiveness": {
            "caching_enabled": True,
            "lazy_initialization": True,
            "session_pooling": True,
        },
    }


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
        f"{Colors.GREEN}✓ {status_code} OK{Colors.RESET}"
        if status_code == 200
        else f"{Colors.RED}✗ {status_code}{Colors.RESET}"
    )

    # Put it all together in a clear, beautiful format
    log_line = f"{Colors.BOLD}{method} {endpoint}{Colors.RESET} {status_str}"
    model_line = f"{claude_display} → {openai_display} {tools_str} {messages_str}"

    # Log request information (these are significant events worth showing in console)
    logger.warning(log_line)  # Use WARNING level to ensure visibility in console
    logger.warning(model_line)
    sys.stdout.flush()


# Test endpoint for validating Azure error handling
@app.get("/azure/test-error-handling")
async def test_azure_error_handling():
    """Test endpoint to validate Azure error handling mechanisms."""
    test_results = {}

    # Test 1: Error classification
    test_results["error_classification"] = {}

    # Test different error types
    test_cases = [
        (401, '{"error": {"message": "Unauthorized access"}}', "authentication"),
        (403, '{"error": {"message": "Access denied"}}', "authentication"),
        (429, '{"error": {"message": "Rate limit exceeded", "retry_after": 60}}', "rate_limit"),
        (500, '{"error": {"message": "Internal server error"}}', "transient"),
        (502, '{"error": {"message": "Bad gateway"}}', "transient"),
        (400, '{"error": {"message": "Invalid deployment name"}}', "configuration"),
        (404, '{"error": {"message": "Resource not found"}}', "configuration"),
    ]

    for status_code, error_text, expected_type in test_cases:
        try:
            azure_error = classify_azure_error(status_code, error_text)
            test_results["error_classification"][f"status_{status_code}"] = {
                "expected_type": expected_type,
                "actual_type": azure_error.error_type,
                "is_retryable": azure_error.is_retryable,
                "user_message": extract_user_friendly_message(azure_error),
                "passed": azure_error.error_type == expected_type,
            }
        except Exception as e:
            test_results["error_classification"][f"status_{status_code}"] = {
                "error": str(e),
                "passed": False,
            }

    # Test 2: Fallback manager
    test_results["fallback_manager"] = {
        "initial_state": {
            "fallback_mode": azure_fallback_manager.fallback_mode,
            "consecutive_failures": azure_fallback_manager.consecutive_failures,
            "failure_count": azure_fallback_manager.failure_count,
        }
    }

    # Test simulated failures
    try:
        # Simulate authentication error
        auth_error = AzureAuthenticationError("Test auth error", 401)
        azure_fallback_manager.record_failure(auth_error)

        test_results["fallback_manager"]["after_auth_error"] = {
            "fallback_mode": azure_fallback_manager.fallback_mode,
            "consecutive_failures": azure_fallback_manager.consecutive_failures,
            "should_use_fallback": azure_fallback_manager.should_use_fallback(),
        }

        # Test recovery
        azure_fallback_manager.record_success()

        test_results["fallback_manager"]["after_success"] = {
            "fallback_mode": azure_fallback_manager.fallback_mode,
            "consecutive_failures": azure_fallback_manager.consecutive_failures,
            "should_use_fallback": azure_fallback_manager.should_use_fallback(),
        }

    except Exception as e:
        fallback_manager_result = test_results.get("fallback_manager", {})
        if isinstance(fallback_manager_result, dict):
            fallback_manager_result["error"] = str(e)
            test_results["fallback_manager"] = fallback_manager_result
        else:
            test_results["fallback_manager"] = {"error": str(e)}

    # Test 3: Error logging
    test_results["error_logging"] = {
        "error_history_count": len(azure_error_logger.error_history),
        "error_patterns_count": len(azure_error_logger.error_patterns),
        "should_alert": azure_error_logger.should_alert(),
        "error_summary": azure_error_logger.get_error_summary(),
    }

    return {
        "message": "Azure error handling validation completed",
        "timestamp": asyncio.get_event_loop().time(),
        "test_results": test_results,
        "system_status": {
            "fallback_active": azure_fallback_manager.fallback_mode,
            "error_count": len(azure_error_logger.error_history),
            "health_check_available": True,
        },
    }
