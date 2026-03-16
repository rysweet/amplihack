"""Streaming response handlers for the integrated proxy.

Handles streaming responses from LiteLLM and Azure APIs,
including tool call support, retry logic, and format conversion.
"""

import asyncio
import json
import os
import ssl
import uuid
from typing import Any

import aiohttp  # type: ignore[import-unresolved]
import litellm  # type: ignore[import-unresolved]

from amplihack.utils.logging_utils import log_call

from .exceptions import (
    AzureAPIError,
    ToolCallError,
    ToolStreamingError,
    ToolValidationError,
)
from .models import ConversationState, MessagesRequest
from .monitoring import logger

# Phase 2: Tool Configuration Environment Variables
ENFORCE_ONE_TOOL_CALL_PER_RESPONSE = (
    os.environ.get("AMPLIHACK_TOOL_ONE_PER_RESPONSE", "true").lower() == "true"
)
TOOL_CALL_RETRY_ATTEMPTS = int(os.environ.get("AMPLIHACK_TOOL_RETRY_ATTEMPTS", "3"))
TOOL_CALL_TIMEOUT = int(os.environ.get("AMPLIHACK_TOOL_TIMEOUT", "30"))  # seconds
ENABLE_TOOL_FALLBACK = os.environ.get("AMPLIHACK_TOOL_FALLBACK", "true").lower() == "true"
TOOL_STREAM_BUFFER_SIZE = int(os.environ.get("AMPLIHACK_TOOL_STREAM_BUFFER", "1024"))

# Check if we should use LiteLLM router for Azure
USE_LITELLM_ROUTER = os.environ.get("AMPLIHACK_USE_LITELLM", "true").lower() == "true"


@log_call
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
                f"Attempting tool call (attempt {attempt + 1}/{max_attempts}): {tool_name}"
            )
            return await func()

        except (TimeoutError, aiohttp.ClientError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                # Exponential backoff: 1s, 2s, 4s, etc.
                wait_time = 2**attempt
                logger.warning(
                    f"Tool call failed, retrying in {wait_time}s (attempt {attempt + 1}/{max_attempts}): {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Tool call failed after {max_attempts} attempts: {e}")

        except ToolValidationError as e:
            # Don't retry validation errors
            logger.error(f"Tool validation error (no retry): {e}")
            raise

        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = 2**attempt
                logger.warning(
                    f"Unexpected tool call error, retrying in {wait_time}s (attempt {attempt + 1}/{max_attempts}): {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Tool call failed after {max_attempts} attempts: {e}")

    raise ToolCallError(
        f"Tool call failed after {max_attempts} attempts: {last_exception}",
        tool_name=tool_name,
        retry_count=max_attempts,
    )


@log_call
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


@log_call
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
    # Import here to avoid circular dependency
    from .integrated_proxy import get_litellm_router

    try:
        # Validate tools if present
        if litellm_request.get("tools"):
            for tool in litellm_request["tools"]:
                validation_errors = validate_tool_schema(tool)
                if validation_errors:
                    error_msg = f"Tool validation failed: {', '.join(validation_errors)}"
                    if ENABLE_TOOL_FALLBACK:
                        logger.warning(f"{error_msg}, removing invalid tool")
                        continue
                    raise ToolValidationError(error_msg, tool_name=tool.get("name"))

        # Attempt the tool call with retry logic
        @log_call
        async def make_request():
            active_router = get_litellm_router()
            if USE_LITELLM_ROUTER and active_router:
                return await active_router.acompletion(**litellm_request)
            return await litellm.acompletion(**litellm_request)

        return await retry_tool_call(make_request, tool_name="litellm_completion")

    except (ToolCallError, ToolValidationError) as e:
        logger.error(f"Tool call failed: {e}")

        if not ENABLE_TOOL_FALLBACK:
            raise

        logger.info("Falling back to tool-less completion")

        # Remove tools and tool_choice for fallback
        fallback_request = litellm_request.copy()
        fallback_request.pop("tools", None)
        fallback_request.pop("tool_choice", None)

        # Make fallback request
        @log_call
        async def make_fallback_request():
            active_router = get_litellm_router()
            if USE_LITELLM_ROUTER and active_router:
                return await active_router.acompletion(**fallback_request)
            return await litellm.acompletion(**fallback_request)

        return await retry_tool_call(make_fallback_request, tool_name="fallback_completion")


@log_call
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
            f"Starting tool-aware streaming for conversation phase: {conversation_state.phase}"
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
                                    logger.warning(f"Failed to parse tool arguments: {e}")
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
                                    logger.debug("Enforcing single tool call limit")
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
                logger.error(f"Error processing streaming chunk: {chunk_error}")
                if not ENABLE_TOOL_FALLBACK:
                    raise ToolStreamingError(f"Failed to process streaming chunk: {chunk_error}")
                continue

    except Exception as e:
        logger.error(f"Tool streaming failed: {e}")
        if ENABLE_TOOL_FALLBACK:
            # Fall back to regular streaming
            logger.info("Falling back to regular streaming")
            async for event in handle_streaming(response_generator, original_request):
                yield event
        else:
            raise ToolStreamingError(f"Tool streaming failed: {e}")


@log_call
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
    AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", os.environ.get("OPENAI_API_KEY"))
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")

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
        logger.error(f"Azure streaming with tools failed: {e}")
        raise ToolStreamingError(f"Azure streaming failed: {e}")


@log_call
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
