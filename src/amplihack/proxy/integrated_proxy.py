import asyncio
import json
import os
import re
import time
import uuid
from typing import Any

import litellm  # type: ignore[import-unresolved]
from dotenv import load_dotenv  # type: ignore[import-unresolved]
from fastapi import FastAPI, HTTPException, Request  # type: ignore[import-unresolved]
from fastapi.responses import StreamingResponse  # type: ignore[import-unresolved]
from litellm import Router  # type: ignore[import-unresolved]

# Load environment variables from .env file
load_dotenv()

# Load .azure.env if it exists
if os.path.exists(".azure.env"):
    load_dotenv(".azure.env")

# Import unified Azure integration
# --- azure_errors.py ---
from .azure_errors import (  # noqa: F401
    AzureFallbackManager,
    azure_fallback_manager,
    classify_azure_error,
    create_fallback_response,
    extract_user_friendly_message,
    retry_azure_request,
)
from .azure_unified_integration import create_unified_litellm_router, validate_azure_unified_config

# --- conversion.py ---
from .conversion import (  # noqa: F401
    analyze_conversation_for_tools,
    clean_gemini_schema,
    convert_anthropic_to_azure_responses,
    convert_anthropic_to_litellm,
    convert_azure_responses_to_anthropic,
    convert_litellm_to_anthropic,
    is_azure_chat_api,
    is_azure_responses_api,
    is_azure_responses_api_model,
    make_azure_responses_api_call,
    parse_tool_result_content,
    should_use_responses_api_for_model,
)

# =============================================================================
# Re-export everything from the extracted modules for backward compatibility.
# External code importing from amplihack.proxy.integrated_proxy will continue
# to find all the same names here.
# =============================================================================
# --- exceptions.py ---
from .exceptions import (  # noqa: F401
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
)

# --- models.py ---
from .models import (  # noqa: F401
    GEMINI_MODELS,
    OPENAI_MODELS,
    ContentBlockImage,
    ContentBlockText,
    ContentBlockToolResult,
    ContentBlockToolUse,
    ConversationState,
    JSONSchema,
    Message,
    MessagesRequest,
    MessagesResponse,
    SystemContent,
    ThinkingConfig,
    TokenCountRequest,
    TokenCountResponse,
    Tool,
    Usage,
)

# --- monitoring.py ---
from .monitoring import (  # noqa: F401
    AzureErrorLogger,
    ColorizedFormatter,
    Colors,
    MessageFilter,
    azure_error_logger,
    log_azure_operation,
    log_request_beautifully,
    logger,
    setup_logging,
)

# Import sanitizing logger to prevent credential exposure (Issue #1997)
# --- streaming.py ---
from .streaming import (  # noqa: F401
    handle_azure_streaming_with_tools,
    handle_streaming,
    handle_tool_call_with_fallback,
    retry_tool_call,
    stream_with_tools,
    validate_tool_schema,
)

# =============================================================================
# Module-level constants and globals that remain in this file
# =============================================================================

# Check if we should use LiteLLM router for Azure
USE_LITELLM_ROUTER = os.environ.get("AMPLIHACK_USE_LITELLM", "true").lower() == "true"


# Security utility functions
def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to prevent credential leakage."""
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
        logger.error("Azure unified configuration validation failed")
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
        f"Initializing LiteLLM with deployments: BIG={big_model}, MIDDLE={middle_model}, SMALL={small_model}"
    )

    try:
        router = create_unified_litellm_router(
            api_key, base_url, api_version, big_model, middle_model, small_model
        )
        logger.info(f"LiteLLM router initialized: {base_url}")
        return router
    except Exception as e:
        logger.error(f"Failed to initialize LiteLLM router: {e}")
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
        if not re.match(r"^[a-zA-Z0-9\-\._]+$", claude_model):
            raise ValueError(
                "Model name contains invalid characters (only alphanumeric, dash, dot, underscore allowed)"
            )

        # Route based on configured BIG_MODEL (from config file)
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
                logger.info("Lazy LiteLLM router initialized successfully")
            else:
                logger.warning("LiteLLM router setup returned None")
        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM router: {e}")
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

        logger.debug(f"PROCESSING REQUEST: Model={request.model}, Stream={request.stream}")

        # All requests now route through LiteLLM with unified Azure integration
        # The unified routing handles both Chat and Responses APIs transparently
        # Convert Anthropic request to LiteLLM format
        if azure_fallback_manager.should_use_fallback():
            logger.warning("Azure fallback mode active - returning fallback response")
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
                    logger.info("Starting Azure Responses API streaming with tool calling support")

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
                        logger.error(f"Azure streaming failed: {e}")
                        if ENABLE_TOOL_FALLBACK:
                            logger.info("Falling back to Azure non-streaming")
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
                logger.error(f"Azure API failed: {azure_error.error_type} - {azure_error!s}")

                # Check if we should immediately enter fallback mode
                if isinstance(azure_error, (AzureAuthenticationError, AzureConfigurationError)):
                    logger.warning("Critical Azure error - triggering immediate fallback")
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
        logger.debug(f"Conversation state: {conversation_state.phase}")

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
                    logger.error(f"Tool-aware streaming failed: {e}")
                    if ENABLE_TOOL_FALLBACK:
                        logger.info("Falling back to regular streaming")
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
                    logger.error(f"Tool-aware completion failed: {e}")
                    if ENABLE_TOOL_FALLBACK:
                        logger.info("Falling back to regular completion")
                        litellm_response = litellm.completion(**litellm_request)
                    else:
                        raise HTTPException(
                            status_code=500, detail=f"Tool completion failed: {e}"
                        ) from e
            else:
                # Regular completion for non-tool requests
                litellm_response = litellm.completion(**litellm_request)
            logger.debug(
                f"RESPONSE RECEIVED: Model={litellm_request.get('model')}, Time={time.time() - start_time:.2f}s"
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
