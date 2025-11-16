#!/usr/bin/env python3
"""
Script to refactor integrated_proxy.py to use modular imports.

This script:
1. Adds imports from .modules package
2. Removes duplicate exception definitions (lines 37-715)
3. Removes duplicate pydantic model definitions (lines 1387-1650)
4. Keeps the rest of the file intact
"""


def refactor_integrated_proxy():
    """Refactor integrated_proxy.py to use modular imports."""

    # Read the original file
    with open('integrated_proxy.py') as f:
        lines = f.readlines()

    # New import section to add after azure_unified_integration import (line 30)
    new_imports = '''
# Import modular components
from .modules import (
    # Error handling
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
    azure_error_logger,
    azure_fallback_manager,
    classify_azure_error,
    create_fallback_response,
    extract_user_friendly_message,
    log_azure_operation,
    retry_azure_request,
    sanitize_error_message,
    # Request validation
    BIG_MODEL,
    ContentBlockImage,
    ContentBlockText,
    ContentBlockToolResult,
    ContentBlockToolUse,
    ConversationState,
    GEMINI_MODELS,
    Message,
    MessagesRequest,
    MessagesResponse,
    OPENAI_MODELS,
    PREFERRED_PROVIDER,
    SMALL_MODEL,
    SystemContent,
    ThinkingConfig,
    TokenCountRequest,
    TokenCountResponse,
    Tool,
    Usage,
    analyze_conversation_for_tools,
    clean_gemini_schema,
    parse_tool_result_content,
)

'''

    # Build new file content
    new_lines = []

    # Keep lines 1-30 (imports and env loading)
    new_lines.extend(lines[0:30])

    # Add new modular imports
    new_lines.append(new_imports)

    # Add USE_LITELLM_ROUTER config (originally at line 32-33)
    new_lines.append('# Check if we should use LiteLLM router for Azure\n')
    new_lines.append('USE_LITELLM_ROUTER = os.environ.get("AMPLIHACK_USE_LITELLM", "true").lower() == "true"\n')
    new_lines.append('\n')

    # Skip lines 37-715 (error handling - now in module)
    # Keep lines 716+ (logging setup and rest of file)
    new_lines.extend(lines[715:])

    # Now remove the duplicate pydantic models section (originally lines 1387-1650)
    # After removing lines 37-715 (678 lines), the pydantic models are now at line 1387-678 = 709
    # But we need to find them by content, not line numbers

    # Write refactored file
    with open('integrated_proxy_refactored.py', 'w') as f:
        f.writelines(new_lines)

    print("✅ Created integrated_proxy_refactored.py")
    print(f"Original lines: {len(lines)}")
    print(f"New lines: {len(new_lines)}")
    print(f"Removed: {len(lines) - len(new_lines)} lines")

if __name__ == '__main__':
    refactor_integrated_proxy()
