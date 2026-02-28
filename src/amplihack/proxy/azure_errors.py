"""Azure error classification, retry logic, and fallback management.

Handles Azure API error parsing, exponential backoff retries,
and fallback behavior when Azure API consistently fails.
"""

import asyncio
import json
import re
import uuid
from typing import Any

import aiohttp  # type: ignore[import-unresolved]

from .exceptions import (
    AzureAPIError,
    AzureAuthenticationError,
    AzureConfigurationError,
    AzureRateLimitError,
    AzureTransientError,
)
from .monitoring import logger


# Azure Error Classification and Parsing
def classify_azure_error(status_code: int, error_text: str) -> AzureAPIError:
    """Classify Azure API errors into specific exception types with enhanced parsing."""
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
    from .exceptions import AzureFallbackError

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
                    f"{request_name} failed with non-retryable error: {azure_error.error_type} - {azure_error!s}"
                )
                raise azure_error

            # Don't retry if this was our last attempt
            if attempt >= max_retries:
                logger.error(
                    f"{request_name} failed after {max_retries + 1} attempts: {azure_error!s}"
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
                f"{request_name} failed (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s: {azure_error.error_type} - {azure_error!s}"
            )

            await asyncio.sleep(delay)

        except TimeoutError as timeout_error:
            # Treat timeouts as transient errors
            last_error = AzureTransientError(
                f"Request timeout: {timeout_error}", status_code=408, retry_count=attempt
            )

            if attempt >= max_retries:
                logger.error(f"{request_name} timed out after {max_retries + 1} attempts")
                break

            delay = min(base_delay * (backoff_multiplier**attempt), max_delay)
            logger.warning(
                f"{request_name} timed out (attempt {attempt + 1}/{max_retries + 1}), "
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
                    f"{request_name} failed with network error after {max_retries + 1} attempts"
                )
                break

            delay = min(base_delay * (backoff_multiplier**attempt), max_delay)
            logger.warning(
                f"{request_name} network error (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {delay:.1f}s: {client_error!s}"
            )
            await asyncio.sleep(delay)

        except Exception as unexpected_error:
            # For unexpected errors, don't retry
            logger.error(
                f"{request_name} failed with unexpected error: {type(unexpected_error).__name__}: {unexpected_error!s}"
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
            logger.info("Azure API recovered - exiting fallback mode")
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
            logger.error("Azure authentication error - entering extended fallback mode")

        elif isinstance(azure_error, AzureConfigurationError):
            # Configuration errors - longer fallback
            should_fallback = True
            fallback_duration = 3600  # 1 hour
            logger.error("Azure configuration error - entering extended fallback mode")

        elif self.consecutive_failures >= 3:
            # Multiple consecutive failures - temporary fallback
            should_fallback = True
            fallback_duration = 300  # 5 minutes
            logger.warning(
                f"{self.consecutive_failures} consecutive Azure failures - entering temporary fallback mode"
            )

        elif isinstance(azure_error, AzureTransientError) and self.consecutive_failures >= 2:
            # Multiple transient errors - short fallback
            should_fallback = True
            fallback_duration = 120  # 2 minutes
            logger.warning("Multiple transient Azure errors - entering short fallback mode")

        if should_fallback and not self.fallback_mode:
            self.fallback_mode = True
            self.fallback_until = current_time + fallback_duration
            logger.warning(
                f"Entering Azure fallback mode for {fallback_duration / 60:.1f} minutes "
                f"(consecutive failures: {self.consecutive_failures})"
            )

    def should_use_fallback(self) -> bool:
        """Check if fallback mode should be used."""
        if not self.fallback_mode:
            return False

        current_time = asyncio.get_event_loop().time()

        # Check if fallback period has expired
        if self.fallback_until and current_time >= self.fallback_until:
            logger.info("Fallback period expired - attempting Azure API recovery")
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
