"""Conversion functions between Anthropic, Azure, and LiteLLM formats.

Handles request/response transformation between different API formats,
including tool call conversion, content block parsing, and schema cleaning.
"""

import asyncio
import json
import os
import ssl
import uuid
from typing import Any

import aiohttp  # type: ignore[import-unresolved]
import certifi  # type: ignore[import-unresolved]

from .azure_errors import (
    azure_fallback_manager,
    classify_azure_error,
    retry_azure_request,
)
from .exceptions import (
    AzureAPIError,
    ConversationStateError,
)
from .models import (
    ConversationState,
    JSONSchema,
    Message,
    MessagesRequest,
    MessagesResponse,
    ThinkingConfig,
    Usage,
)
from .monitoring import log_azure_operation, logger


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
            f"Conversation analysis: {state.phase}, {len(state.pending_tool_calls)} pending, {len(state.completed_tool_calls)} completed"
        )
        return state

    except Exception as e:
        logger.error(f"Error analyzing conversation for tools: {e}")
        raise ConversationStateError(f"Failed to analyze conversation state: {e}")


def is_azure_responses_api() -> bool:
    """Check if we should use Azure Responses API instead of Chat API.

    Returns True for Responses API endpoints (/responses), False for Chat API endpoints (/chat).
    """
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
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
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
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
    AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", os.environ.get("OPENAI_API_KEY"))
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
    AZURE_API_VERSION = os.environ.get("AZURE_API_VERSION", "2025-03-01-preview")

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
