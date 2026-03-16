"""Exception classes for the integrated proxy.

All tool-specific and Azure-specific exception types used across
the proxy modules.
"""

from typing import Any

from amplihack.utils.logging_utils import log_call


# Phase 2: Tool-Specific Exception Types
class ToolCallError(Exception):
    """Base exception for tool call errors"""

    @log_call
    def __init__(self, message: str, tool_name: str | None = None, retry_count: int = 0):
        super().__init__(message)
        self.tool_name = tool_name
        self.retry_count = retry_count


class ToolValidationError(ToolCallError):
    """Exception for tool schema validation errors"""

    @log_call
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

    @log_call
    def __init__(
        self, message: str, tool_name: str | None = None, timeout_seconds: int | None = None
    ):
        super().__init__(message, tool_name)
        self.timeout_seconds = timeout_seconds


class ToolStreamingError(ToolCallError):
    """Exception for tool streaming errors"""

    @log_call
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

    @log_call
    def __init__(self, message: str, state: str | None = None):
        super().__init__(message)
        self.state = state


# Azure-Specific Exception Types
class AzureAPIError(Exception):
    """Base exception for Azure API errors"""

    @log_call
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

    @log_call
    def __init__(self, message: str, status_code: int | None = None, retry_count: int = 0):
        super().__init__(message, status_code, "transient", retry_count, is_retryable=True)


class AzureAuthenticationError(AzureAPIError):
    """Exception for Azure authentication/authorization errors"""

    @log_call
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code, "authentication", is_retryable=False)


class AzureRateLimitError(AzureAPIError):
    """Exception for Azure rate limiting errors"""

    @log_call
    def __init__(self, message: str, retry_after: int | None = None, retry_count: int = 0):
        super().__init__(message, 429, "rate_limit", retry_count, is_retryable=True)
        self.retry_after = retry_after


class AzureConfigurationError(AzureAPIError):
    """Exception for Azure configuration/deployment errors"""

    @log_call
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code, "configuration", is_retryable=False)


class AzureFallbackError(AzureAPIError):
    """Exception indicating Azure fallback was triggered"""

    @log_call
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, error_type="fallback", is_retryable=False)
        self.original_error = original_error
