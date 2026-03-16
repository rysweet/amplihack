"""Pydantic models for the integrated proxy.

All request/response models, content block types, and conversation
state management for Anthropic API compatibility.
"""

import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, field_validator  # type: ignore[import-unresolved]

from amplihack.utils.logging_utils import log_call

# Type alias for JSON schema structures
JSONSchema = dict[str, Any] | list[Any] | str | int | float | bool | None

# Logger for model validation messages
logger = logging.getLogger(__name__)

# Get preferred provider (default to openai)
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openai").lower()

# Get model mapping configuration from environment
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

    @log_call
    def add_tool_call(self, tool_call: dict[str, Any]) -> None:
        """Add a pending tool call"""
        self.pending_tool_calls.append(tool_call)
        self.last_tool_call_id = tool_call.get("id")
        self.tool_call_count += 1
        self.phase = "tool_call_pending"

    @log_call
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

    @log_call
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
    @log_call
    def validate_model_field(cls, v, info):  # Renamed to avoid conflict
        original_model = v
        new_model = v  # Default to original value

        logger.debug(
            f"MODEL VALIDATION: Original='{original_model}', Preferred='{PREFERRED_PROVIDER}', BIG='{BIG_MODEL}', SMALL='{SMALL_MODEL}'"
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
            logger.debug(f"MODEL MAPPING: '{original_model}' -> '{new_model}'")
        else:
            # If no mapping occurred and no prefix exists, log warning or decide default
            if not v.startswith(("openai/", "gemini/", "anthropic/")):
                logger.warning(
                    f"No prefix or mapping rule for model: '{original_model}'. Using as is."
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
    @log_call
    def validate_model_token_count(cls, v, info):  # Renamed to avoid conflict
        # Use the same logic as MessagesRequest validator
        original_model = v
        new_model = v  # Default to original value

        logger.debug(
            f"TOKEN COUNT VALIDATION: Original='{original_model}', Preferred='{PREFERRED_PROVIDER}', BIG='{BIG_MODEL}', SMALL='{SMALL_MODEL}'"
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
            logger.debug(f"TOKEN COUNT MAPPING: '{original_model}' -> '{new_model}'")
        else:
            if not v.startswith(("openai/", "gemini/", "anthropic/")):
                logger.warning(
                    f"No prefix or mapping rule for token count model: '{original_model}'. Using as is."
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
