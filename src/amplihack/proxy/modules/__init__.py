"""
Integrated proxy modules package.

Provides modular components for error handling, request validation,
response conversion, provider routing, and streaming handlers.
"""

# Error handling exports
from .error_handling import (
    # Exceptions
    AzureAPIError,
    AzureAuthenticationError,
    AzureConfigurationError,
    AzureFallbackError,
    AzureRateLimitError,
    AzureTransientError,
    ConversationStateError,
    ToolCallError,
    ToolStreamingError,
    ToolTimeoutError,
    ToolValidationError,
    # Functions
    azure_error_logger,
    azure_fallback_manager,
    classify_azure_error,
    create_fallback_response,
    extract_user_friendly_message,
    log_azure_operation,
    retry_azure_request,
    sanitize_error_message,
)

# Request validation exports
from .request_validation import (
    # Models
    ContentBlockImage,
    ContentBlockText,
    ContentBlockToolResult,
    ContentBlockToolUse,
    ConversationState,
    Message,
    MessagesRequest,
    MessagesResponse,
    SystemContent,
    ThinkingConfig,
    TokenCountRequest,
    TokenCountResponse,
    Tool,
    Usage,
    # Functions
    analyze_conversation_for_tools,
    clean_gemini_schema,
    parse_tool_result_content,
    # Configuration
    BIG_MODEL,
    GEMINI_MODELS,
    OPENAI_MODELS,
    PREFERRED_PROVIDER,
    SMALL_MODEL,
)

__all__ = [
    # Error handling
    "AzureAPIError",
    "AzureAuthenticationError",
    "AzureConfigurationError",
    "AzureFallbackError",
    "AzureRateLimitError",
    "AzureTransientError",
    "ConversationStateError",
    "ToolCallError",
    "ToolStreamingError",
    "ToolTimeoutError",
    "ToolValidationError",
    "azure_error_logger",
    "azure_fallback_manager",
    "classify_azure_error",
    "create_fallback_response",
    "extract_user_friendly_message",
    "log_azure_operation",
    "retry_azure_request",
    "sanitize_error_message",
    # Request validation
    "ContentBlockImage",
    "ContentBlockText",
    "ContentBlockToolResult",
    "ContentBlockToolUse",
    "ConversationState",
    "Message",
    "MessagesRequest",
    "MessagesResponse",
    "SystemContent",
    "ThinkingConfig",
    "TokenCountRequest",
    "TokenCountResponse",
    "Tool",
    "Usage",
    "analyze_conversation_for_tools",
    "clean_gemini_schema",
    "parse_tool_result_content",
    "BIG_MODEL",
    "GEMINI_MODELS",
    "OPENAI_MODELS",
    "PREFERRED_PROVIDER",
    "SMALL_MODEL",
]
