"""
Request validation module for integrated proxy.

Provides Pydantic models for request/response validation, model mapping,
and conversation state management.
"""

import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, field_validator  # type: ignore[import-unresolved]

# Get logger
logger = logging.getLogger(__name__)

# Model Configuration
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openai").lower()
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
    "gpt-4.1",
    "gpt-4.1-mini",
]

# List of Gemini models
GEMINI_MODELS = ["gemini-2.5-pro-preview-03-25", "gemini-2.0-flash"]


# Pydantic Models for Request/Response Validation
class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: Dict[str, Any]


class ContentBlockToolUse(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields like cache_control
    type: Literal["tool_use"]
    id: str
    name: Optional[str] = None  # Name can be None in partial tool use blocks
    input: Dict[str, Any]


class ContentBlockToolResult(BaseModel):
    model_config = {"extra": "allow"}  # Allow extra fields like cache_control
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any]]


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[
        str,
        List[
            Union[ContentBlockText, ContentBlockImage, ContentBlockToolUse, ContentBlockToolResult]
        ],
    ]


class Tool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]


class ThinkingConfig(BaseModel):
    enabled: bool = True


class ConversationState(BaseModel):
    """Phase 2: Manages conversation state for tool call analysis"""

    phase: Literal["normal", "tool_call_pending", "tool_result_pending", "tool_complete"] = "normal"
    pending_tool_calls: List[Dict[str, Any]] = []
    completed_tool_calls: List[Dict[str, Any]] = []
    last_tool_call_id: Optional[str] = None
    tool_call_count: int = 0
    has_streaming_tools: bool = False
    conversation_turn: int = 0

    def add_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Add a pending tool call"""
        self.pending_tool_calls.append(tool_call)
        self.last_tool_call_id = tool_call.get("id")
        self.tool_call_count += 1
        self.phase = "tool_call_pending"

    def complete_tool_call(self, tool_call_id: str, result: Dict[str, Any]) -> None:
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
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    thinking: Optional[ThinkingConfig] = None
    original_model: Optional[str] = None  # Will store the original model name

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
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    tools: Optional[List[Tool]] = None
    thinking: Optional[ThinkingConfig] = None
    tool_choice: Optional[Dict[str, Any]] = None
    original_model: Optional[str] = None  # Will store the original model name

    @field_validator("model")
    def validate_model_token_count(cls, v, info):  # Renamed to avoid conflict
        # Use the same logic as MessagesRequest validator
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
    content: List[Union[ContentBlockText, ContentBlockToolUse]]
    type: Literal["message"] = "message"
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]] = None
    stop_sequence: Optional[str] = None
    usage: Usage


# Helper Functions
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


def analyze_conversation_for_tools(messages: List[Message]) -> ConversationState:
    """
    Phase 2: Analyze conversation messages to determine tool call state.

    Args:
        messages: List of conversation messages

    Returns:
        ConversationState: Current state of tool interactions
    """
    from .error_handling import ConversationStateError

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


def clean_gemini_schema(schema: Union[Dict[str, Any], List[Any], str, int, float, bool, None]) -> Union[Dict[str, Any], List[Any], str, int, float, bool, None]:
    """
    Recursively clean a JSON schema by removing additionalProperties fields.
    Gemini's function calling doesn't support additionalProperties in schemas.
    """
    if isinstance(schema, dict):
        # Create new dict without additionalProperties
        cleaned = {}
        for key, value in schema.items():
            if key != "additionalProperties":
                cleaned[key] = clean_gemini_schema(value)
        return cleaned
    elif isinstance(schema, list):
        return [clean_gemini_schema(item) for item in schema]
    else:
        # Return primitive types as-is
        return schema
