"""Built-in FastAPI proxy server with OpenAI Responses API support."""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Literal

import httpx  # type: ignore
import litellm  # type: ignore
from dotenv import load_dotenv  # type: ignore
from fastapi import FastAPI, HTTPException, Request, Response  # type: ignore
from fastapi.responses import StreamingResponse  # type: ignore
from pydantic import BaseModel, field_validator  # type: ignore

from .github_auth import GitHubAuthManager
from .github_models import CLAUDE_MODELS, GITHUB_COPILOT_MODELS, OPENAI_MODELS
from .passthrough import PassthroughHandler
from .sanitizing_logger import get_sanitizing_logger
from .security import TokenSanitizer

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARN,  # Change to INFO level to show more details
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)

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


# Apply the filter to the root logger to catch all messages
root_logger = logging.getLogger()
root_logger.addFilter(MessageFilter())


# Custom formatter for model mapping logs
class ColorizedFormatter(logging.Formatter):
    """Custom formatter to highlight model mappings"""

    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        if record.levelno == logging.debug and "MODEL MAPPING" in record.msg:
            # Apply colors and formatting to model mapping logs
            return f"{self.BOLD}{self.GREEN}{record.msg}{self.RESET}"
        return super().format(record)


# Apply custom formatter to console handler
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setFormatter(ColorizedFormatter("%(asctime)s - %(levelname)s - %(message)s"))

app = FastAPI()

# Register LiteLLM callbacks for optional trace logging
from .litellm_callbacks import register_trace_callbacks
_trace_callback = register_trace_callbacks()  # Reads from AMPLIHACK_TRACE_LOGGING env

# Load environment variables from .azure.env if it exists (with security validation)
try:
    # Only load from current directory if it's within the project structure
    from pathlib import Path

    current_dir = Path.cwd()
    azure_env_path = current_dir / ".azure.env"

    # Security: Only load if file exists and is in expected location
    # Prevent path traversal by ensuring it's a direct child of cwd
    if azure_env_path.exists() and azure_env_path.parent == current_dir:
        # Validate file permissions (optional but recommended)
        logger.debug(f"Loading Azure environment from: {azure_env_path}")
        load_dotenv(azure_env_path, override=True)
        logger.debug("Azure environment variables loaded successfully")
    else:
        logger.debug("No .azure.env file found in current directory")
except Exception as e:
    logger.warning(f"Failed to load .azure.env: {e}")
    # Continue without .azure.env - not a critical failure

# Get API keys from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API_KEY = os.environ.get("GITHUB_API_KEY") or GITHUB_TOKEN  # LiteLLM expects GITHUB_API_KEY

# Get preferred provider (default to openai)
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openai").lower()

# Initialize passthrough handler
PASSTHROUGH_MODE = os.environ.get("PASSTHROUGH_MODE", "false").lower() == "true"
passthrough_handler = PassthroughHandler() if PASSTHROUGH_MODE else None

if PASSTHROUGH_MODE:
    logger.info(
        "Passthrough mode enabled - will try Anthropic API first, fallback to Azure on 429 errors"
    )

# Initialize security components
token_sanitizer = TokenSanitizer()


class ModelValidator:
    """Unified model validation and routing (Issue #1922).

    Eliminates duplication between multiple validation functions and
    fixes Sonnet 4 routing conflict from Issue #1920.
    """

    def __init__(self):
        """Initialize ModelValidator with known model lists."""
        self.claude_models = set(CLAUDE_MODELS)
        self.openai_models = set(OPENAI_MODELS)
        self.github_models = set(GITHUB_COPILOT_MODELS)

    def get_provider(self, model: str) -> str:
        """Determine provider from model name.

        Args:
            model: Model name (without provider prefix)

        Returns:
            Provider name ('anthropic', 'openai', 'github')

        Raises:
            ValueError: If model is invalid or unknown
        """
        if not model or not isinstance(model, str):
            raise ValueError(f"Invalid model name: {model}")

        model_lower = model.lower()

        # Check Claude models (includes Sonnet 4 variants)
        # Match if model name matches or starts with known Claude model prefix
        # FIX: Removed overly broad third condition that caused false matches
        if any(
            model_lower == claude_model.lower()
            or model_lower.startswith(claude_model.lower() + "-")
            for claude_model in self.claude_models
        ):
            return "anthropic"

        # Check GitHub Copilot models
        if any(
            model_lower == github_model.lower() or github_model.lower() in model_lower
            for github_model in self.github_models
        ):
            return "github"

        # Check OpenAI models - exact match or starts with known model
        if any(
            model_lower == openai_model.lower()
            or model_lower.startswith(openai_model.lower() + "-")
            for openai_model in self.openai_models
        ):
            return "openai"

        # Unknown model
        raise ValueError(f"Invalid model name: unknown model '{model}'")

    def validate_and_route(self, model: str) -> str:
        """Validate model name and return with provider prefix.

        Args:
            model: Model name to validate

        Returns:
            Model name with provider prefix (e.g., 'anthropic/claude-sonnet-4-20250514')

        Raises:
            ValueError: If model name is invalid
        """
        if not model or not isinstance(model, str):
            raise ValueError(f"Invalid model name: {model}")

        # Get provider
        provider = self.get_provider(model)

        # Return with provider prefix
        return f"{provider}/{model}"


# Get model mapping configuration from environment
# Default to latest OpenAI models if not set
BIG_MODEL = os.environ.get("BIG_MODEL", "gpt-4.1")
SMALL_MODEL = os.environ.get("SMALL_MODEL", "gpt-4.1-mini")

# Timeout configuration
DEFAULT_TIMEOUT = 120.0  # seconds - reasonable default for LLM requests
PROXY_TIMEOUT = float(os.getenv("AMPLIHACK_PROXY_TIMEOUT", DEFAULT_TIMEOUT))

logger.info(f"Proxy timeout configured: {PROXY_TIMEOUT}s")

# Validate timeout configuration
MAX_TIMEOUT = 600.0
if PROXY_TIMEOUT <= 0:
    raise ValueError(f"AMPLIHACK_PROXY_TIMEOUT must be positive, got {PROXY_TIMEOUT}")
if PROXY_TIMEOUT > MAX_TIMEOUT:
    raise ValueError(f"AMPLIHACK_PROXY_TIMEOUT must be <= {MAX_TIMEOUT}s, got {PROXY_TIMEOUT}")


def generate_request_id() -> str:
    """Generate unique request ID for debugging."""
    return f"req_{uuid.uuid4().hex[:12]}"


def log_request_lifecycle(request_id: str, event: str, details: dict[str, Any] | None = None):
    """Log request lifecycle with context for debugging hung requests."""
    log_data = {
        "request_id": request_id,
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if details:
        log_data.update(details)

    logger.info(f"[{request_id}] {event}", extra=log_data)


# Configure LiteLLM for Azure if Azure endpoint is present
# Check Azure-specific variables first, then fall back to generic OPENAI_BASE_URL
AZURE_BASE_URL = (
    os.environ.get("AZURE_OPENAI_ENDPOINT")
    or os.environ.get("AZURE_ENDPOINT")
    or os.environ.get("AZURE_OPENAI_BASE_URL")
    or os.environ.get("OPENAI_BASE_URL", "")
)
if AZURE_BASE_URL:
    # For Azure Responses API with openai/ prefix:
    # LiteLLM DOES read AZURE_API_BASE environment variable (not OPENAI_BASE_URL)
    # We need to set AZURE_API_BASE to the FULL URL with /openai/responses path
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(AZURE_BASE_URL)

    # Strip /responses from path - LiteLLM will add it automatically
    # Also strip query string - LiteLLM will add the api-version parameter
    path = parsed.path
    if path.endswith("/responses"):
        path = path[: -len("/responses")]

    litellm_base_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,  # Path without /responses (e.g., /openai)
            parsed.params,
            "",  # Remove query string - LiteLLM will add it
            parsed.fragment,
        )
    )

    # Set Azure-specific env vars that LiteLLM reads for openai/ prefix
    os.environ["AZURE_API_BASE"] = litellm_base_url
    os.environ["AZURE_ENDPOINT"] = litellm_base_url
    os.environ["AZURE_OPENAI_ENDPOINT"] = litellm_base_url
    os.environ["AZURE_OPENAI_BASE_URL"] = litellm_base_url

    os.environ["AZURE_API_KEY"] = OPENAI_API_KEY or ""
    os.environ["AZURE_OPENAI_API_KEY"] = OPENAI_API_KEY or ""

    # Extract API version from URL if present
    api_version = os.environ.get("AZURE_API_VERSION", "2025-04-01-preview")
    os.environ["AZURE_API_VERSION"] = api_version

    logger.warning("🔧 Azure Configuration:")
    logger.warning(f"  Original URL: {AZURE_BASE_URL}")
    logger.warning(f"  LiteLLM Base: {litellm_base_url}")
    logger.warning(f"  API Version: {api_version}")
    logger.warning(f"  API Key: {'SET' if os.environ['AZURE_API_KEY'] else 'NOT SET'}")

# Additional OpenAI models beyond the constants (merge with imported OPENAI_MODELS)
ADDITIONAL_OPENAI_MODELS = [
    "o3-mini",
    "o1",
    "o1-mini",
    "o1-pro",
    "gpt-4.5-preview",
    "gpt-4o-audio-preview",
    "chatgpt-4o-latest",
    "gpt-4o-mini-audio-preview",
    "gpt-4.1",  # Added default big model
    "gpt-4.1-mini",  # Added default small model
]

# Merge OpenAI models from constants with additional models
OPENAI_MODELS_FULL = list(set(OPENAI_MODELS) | set(ADDITIONAL_OPENAI_MODELS))

# List of Gemini models
GEMINI_MODELS = ["gemini-2.5-pro-preview-03-25", "gemini-2.0-flash"]

# GitHub Copilot models already imported from github_models

# Configure LiteLLM for GitHub Copilot
GITHUB_COPILOT_ENABLED = os.environ.get("GITHUB_COPILOT_ENABLED", "false").lower() == "true"

# Initialize GitHub authentication if needed
if not GITHUB_TOKEN:
    try:
        # Try to get existing GitHub token from gh CLI
        auth_manager = GitHubAuthManager()
        existing_token = auth_manager.get_existing_token()
        if existing_token:
            GITHUB_TOKEN = existing_token
            os.environ["GITHUB_TOKEN"] = existing_token
            logger.info("Using existing GitHub token from gh CLI")
        else:
            logger.warning("No GitHub token found. GitHub Copilot features will be unavailable.")
            logger.info("To enable GitHub Copilot, run: gh auth login --scopes copilot")
    except Exception as e:
        logger.warning(f"Failed to check for existing GitHub token: {e}")

if GITHUB_TOKEN and GITHUB_COPILOT_ENABLED:
    # Set up LiteLLM environment variables for GitHub Copilot provider
    os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
    # LiteLLM expects GITHUB_API_KEY for github_copilot provider
    if GITHUB_API_KEY:
        os.environ["GITHUB_API_KEY"] = GITHUB_API_KEY
    if not os.environ.get("GITHUB_API_BASE"):
        os.environ["GITHUB_API_BASE"] = "https://api.github.com"
    logger.info("GitHub Copilot LiteLLM integration enabled")
elif GITHUB_TOKEN and not GITHUB_COPILOT_ENABLED:
    # Auto-enable if we have a token but flag is not explicitly set
    os.environ["GITHUB_TOKEN"] = GITHUB_TOKEN
    if not os.environ.get("GITHUB_API_BASE"):
        os.environ["GITHUB_API_BASE"] = "https://api.github.com"
    logger.info("GitHub Copilot LiteLLM integration auto-enabled (GITHUB_TOKEN detected)")
    GITHUB_COPILOT_ENABLED = True


# Helper function to clean schema for Gemini
def clean_gemini_schema(schema: Any) -> Any:
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
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str | list[dict[str, Any]] | dict[str, Any] | list[Any] | Any


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: (
        str
        | list[
            ContentBlockText
            | ContentBlockImage
            | ContentBlockToolUse
            | ContentBlockToolResult
            | dict[str, Any]
        ]
    )


class Tool(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any]


class ThinkingConfig(BaseModel):
    enabled: bool = True


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
        # 🚨 CRITICAL FIX: Enforce security validation FIRST (Issue #1922)
        from amplihack.proxy.github_models import GitHubModelMapper

        github_mapper = GitHubModelMapper({})
        github_mapper.validate_model_name(v)

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
        # Determine provider based on configuration
        # Check if we should use GitHub Copilot for Claude models
        if GITHUB_COPILOT_ENABLED and (
            "claude" in clean_v.lower()
            or clean_v in ["claude-sonnet-4", "claude-sonnet-4.5", "claude-opus-4"]
        ):
            provider_prefix = "github_copilot/"
        elif PREFERRED_PROVIDER == "google" and (
            BIG_MODEL in GEMINI_MODELS or SMALL_MODEL in GEMINI_MODELS
        ):
            provider_prefix = "gemini/"
        else:
            # Use azure/ prefix for Azure models (LiteLLM requires this for Azure routing)
            provider_prefix = "azure/"

        # Map Haiku to SMALL_MODEL based on provider preference
        if "haiku" in clean_v.lower():
            new_model = f"{provider_prefix}{SMALL_MODEL}"
            mapped = True

        # Map Sonnet to BIG_MODEL based on provider preference
        elif "sonnet" in clean_v.lower():
            new_model = f"{provider_prefix}{BIG_MODEL}"
            mapped = True

        # Add prefixes to non-mapped models if they match known lists
        elif not mapped:
            if clean_v in GEMINI_MODELS and not v.startswith("gemini/"):
                new_model = f"gemini/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in GITHUB_COPILOT_MODELS and not (
                v.startswith("github/") or v.startswith("github_copilot/")
            ):
                new_model = f"github_copilot/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in OPENAI_MODELS_FULL and not v.startswith("openai/"):
                new_model = f"openai/{clean_v}"
                mapped = True  # Technically mapped to add prefix
        # --- Mapping Logic --- END ---

        if mapped:
            logger.debug(f"📌 MODEL MAPPING: '{original_model}' ➡️ '{new_model}'")
        else:
            # If no mapping occurred and no prefix exists, log warning or decide default
            if not v.startswith(("openai/", "gemini/", "github/", "github_copilot/", "anthropic/")):
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
        # Determine provider based on configuration
        # Check if we should use GitHub Copilot for Claude models
        if GITHUB_COPILOT_ENABLED and (
            "claude" in clean_v.lower()
            or clean_v in ["claude-sonnet-4", "claude-sonnet-4.5", "claude-opus-4"]
        ):
            provider_prefix = "github_copilot/"
        elif PREFERRED_PROVIDER == "google" and (
            BIG_MODEL in GEMINI_MODELS or SMALL_MODEL in GEMINI_MODELS
        ):
            provider_prefix = "gemini/"
        else:
            # Use azure/ prefix for Azure models (LiteLLM requires this for Azure routing)
            provider_prefix = "azure/"

        # Map Haiku to SMALL_MODEL based on provider preference
        if "haiku" in clean_v.lower():
            new_model = f"{provider_prefix}{SMALL_MODEL}"
            mapped = True

        # Map Sonnet to BIG_MODEL based on provider preference
        elif "sonnet" in clean_v.lower():
            new_model = f"{provider_prefix}{BIG_MODEL}"
            mapped = True

        # Add prefixes to non-mapped models if they match known lists
        elif not mapped:
            if clean_v in GEMINI_MODELS and not v.startswith("gemini/"):
                new_model = f"gemini/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in GITHUB_COPILOT_MODELS and not (
                v.startswith("github/") or v.startswith("github_copilot/")
            ):
                new_model = f"github_copilot/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in OPENAI_MODELS_FULL and not v.startswith("openai/"):
                new_model = f"openai/{clean_v}"
                mapped = True  # Technically mapped to add prefix
        # --- Mapping Logic --- END ---

        if mapped:
            logger.debug(f"📌 TOKEN COUNT MAPPING: '{original_model}' ➡️ '{new_model}'")
        else:
            if not v.startswith(("openai/", "gemini/", "github/", "github_copilot/", "anthropic/")):
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


class OpenAIResponsesRequest(BaseModel):
    model: str
    input: str


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
                    except (TypeError, ValueError):
                        result += str(item) + "\n"
            else:
                try:
                    result += str(item) + "\n"
                except (TypeError, ValueError, AttributeError):
                    result += "Unparseable content\n"
        return result.strip()

    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text", "")
        try:
            return json.dumps(content)
        except (TypeError, ValueError):
            return str(content)

    # Fallback for any other type
    try:
        return str(content)
    except (TypeError, ValueError, AttributeError):
        return "Unparseable content"


def sanitize_message_content(
    messages: list[Message], allowed_types: set | None = None
) -> list[Message]:
    """
    Remove unsupported content block types from messages.

    This function defensively filters out content blocks that target
    LLM providers don't support (e.g., 'thinking' blocks from Anthropic's
    extended thinking feature).

    Args:
        messages: List of Message objects in Anthropic format
        allowed_types: Set of allowed content block types
                      Default: {"text", "image", "tool_use", "tool_result"}

    Returns:
        Sanitized list of messages with only allowed content types

    Side Effects:
        Logs filtered blocks at INFO level
    """
    if allowed_types is None:
        allowed_types = {"text", "image", "tool_use", "tool_result"}

    sanitized_messages = []
    filtered_count = 0

    for message in messages:
        # Handle both string content and list content
        content = message.content

        if isinstance(content, list):
            original_length = len(content)
            sanitized_content = []

            for block in content:
                # Handle both dict and object blocks
                if isinstance(block, dict):
                    block_type = block.get("type")
                elif hasattr(block, "type"):
                    block_type = block.type
                else:
                    # Unknown format - pass through defensively
                    sanitized_content.append(block)
                    continue

                if block_type in allowed_types:
                    sanitized_content.append(block)
                else:
                    # Log filtered block type for debugging
                    filtered_count += 1
                    logger.info(
                        f"Filtered unsupported content block type: {block_type} "
                        f"(role: {message.role})"
                    )

            # Only update content if we filtered something
            if len(sanitized_content) < original_length:
                # Create new message with filtered content
                from copy import copy

                sanitized_msg = copy(message)
                sanitized_msg.content = sanitized_content
                message = sanitized_msg

            # Skip messages that have empty content after filtering
            if sanitized_content:
                sanitized_messages.append(message)
            else:
                logger.warning(
                    f"Message with role '{message.role}' has no content "
                    f"after filtering - skipping entire message"
                )
        else:
            # String content or other formats pass through unchanged
            sanitized_messages.append(message)

    if filtered_count > 0:
        logger.info(f"Filtered {filtered_count} unsupported content blocks from messages")

    return sanitized_messages


def convert_anthropic_to_litellm(anthropic_request: MessagesRequest) -> dict[str, Any]:
    """Convert Anthropic API request format to LiteLLM format (which follows OpenAI)."""
    # LiteLLM already handles Anthropic models when using the format model="anthropic/claude-3-opus-20240229"
    # So we just need to convert our Pydantic model to a dict in the expected format

    # Get configured token limits from environment for Azure Responses API
    import os

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

    # Map the model to Azure model to check if it uses Responses API
    model_lower = anthropic_request.model.lower()
    azure_model = (
        BIG_MODEL
        if "sonnet" in model_lower or "opus" in model_lower
        else (SMALL_MODEL if "haiku" in model_lower else BIG_MODEL)
    )

    # Check if this should use Responses API
    openai_base_url = os.environ.get("OPENAI_BASE_URL", "")
    use_responses_api = (
        openai_base_url
        and "/responses" in openai_base_url
        and (
            azure_model.startswith(("o3-", "o4-"))
            or azure_model.startswith("gpt-5-code")
            or azure_model == "gpt-5"
        )
    )

    # Determine temperature based on API type
    temperature = (
        1.0
        if use_responses_api
        else (anthropic_request.temperature if anthropic_request.temperature is not None else 1.0)
    )

    # SANITIZE MESSAGES FIRST - filter out unsupported content blocks like "thinking"
    # This prevents 422 errors from Azure/OpenAI when extended thinking is enabled
    sanitized_messages = sanitize_message_content(anthropic_request.messages)
    logger.debug(
        f"Message sanitization: {len(anthropic_request.messages)} -> {len(sanitized_messages)} messages"
    )

    # Initialize the LiteLLM request dict first to ensure we always return the right structure
    # Check if we should route Claude models to GitHub Copilot
    model_name = anthropic_request.model

    # If GitHub Copilot is enabled and this is a Claude model without a provider prefix
    logger.warning(
        f"🔍 Model routing check: model='{model_name}', GITHUB_COPILOT_ENABLED={GITHUB_COPILOT_ENABLED}"
    )
    if (
        GITHUB_COPILOT_ENABLED
        and "/" not in model_name
        and (
            "claude" in model_name.lower()
            or model_name in ["claude-sonnet-4", "claude-sonnet-4.5", "claude-opus-4"]
        )
    ):
        logger.warning(f"🔀 Routing Claude model '{model_name}' to GitHub Copilot")
        # Use github_copilot/ prefix with underscore (not github/)
        model_name = f"github_copilot/{model_name}"

    litellm_request = {
        "model": model_name,  # it understands "anthropic/claude-x" and "github/model-x" format
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

    # Add conversation messages (use sanitized messages)
    for idx, msg in enumerate(sanitized_messages):
        content = msg.content
        if isinstance(content, str):
            messages.append({"role": msg.role, "content": content})
        else:
            # Special handling for tool_result in user messages
            # OpenAI/LiteLLM format expects the assistant to call the tool,
            # and the user's next message to include the result as plain text
            if msg.role == "user" and any(
                getattr(block, "type", None) == "tool_result"
                for block in content
                if hasattr(block, "type")
            ):
                # For user messages with tool_result, we need to extract the raw result content
                # Extract regular text content
                text_content = ""

                # First extract any normal text blocks
                for block in content:
                    if hasattr(block, "type") and getattr(block, "type", None) == "text":
                        text_content += getattr(block, "text", "") + "\n"

                # Extract tool results
                for block in content:
                    if hasattr(block, "type") and getattr(block, "type", None) == "tool_result":
                        # Get the raw result content without wrapping it in explanatory text

                        if hasattr(block, "content"):
                            result_content = getattr(block, "content", "")

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
                        block_type = getattr(block, "type", None)
                        if block_type == "text":
                            processed_content.append(
                                {"type": "text", "text": getattr(block, "text", "")}
                            )
                        elif block_type == "image":
                            processed_content.append(
                                {"type": "image", "source": getattr(block, "source", {})}
                            )
                        elif block_type == "tool_use":
                            # Handle tool use blocks if needed
                            processed_content.append(
                                {
                                    "type": "tool_use",
                                    "id": getattr(block, "id", ""),
                                    "name": getattr(block, "name", ""),
                                    "input": getattr(block, "input", {}),
                                }
                            )
                        elif block_type == "tool_result":
                            # Handle different formats of tool result content
                            processed_content_block: dict[str, Any] = {
                                "type": "tool_result",
                                "tool_use_id": getattr(block, "tool_use_id", "")
                                if hasattr(block, "tool_use_id")
                                else "",
                            }

                            # Process the content field properly
                            if hasattr(block, "content"):
                                block_content = getattr(block, "content", "")
                                if isinstance(block_content, str):
                                    # If it's a simple string, create a text block for it
                                    processed_content_block["content"] = [
                                        {"type": "text", "text": block_content}
                                    ]
                                elif isinstance(block_content, list):
                                    # If it's already a list of blocks, keep it
                                    processed_content_block["content"] = block_content
                                else:
                                    # Default fallback
                                    processed_content_block["content"] = [
                                        {"type": "text", "text": str(block_content)}
                                    ]
                            else:
                                # Default empty content
                                processed_content_block["content"] = [{"type": "text", "text": ""}]

                            processed_content.append(processed_content_block)

                messages.append({"role": msg.role, "content": processed_content})

    # Cap max_tokens for OpenAI and Azure models to their limit of 16384
    if (
        anthropic_request.model.startswith("openai/")
        or anthropic_request.model.startswith("azure/")
        or anthropic_request.model.startswith("gemini/")
    ):
        litellm_request["max_tokens"] = min(anthropic_request.max_tokens, 16384)
        logger.debug(
            f"Capping max_tokens to 16384 for OpenAI/Azure/Gemini model (original value: {anthropic_request.max_tokens})"
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

    # Convert tools to appropriate format
    if anthropic_request.tools:
        openai_tools = []
        is_gemini_model = anthropic_request.model.startswith("gemini/")
        is_azure_model = anthropic_request.model.startswith("azure/")

        # Check if using Azure Responses API (for o3/o4/gpt-5 models)
        use_responses_api = False
        if is_azure_model and AZURE_BASE_URL and "/responses" in AZURE_BASE_URL:
            use_responses_api = True

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

            # Always use standard OpenAI Chat Completions format
            # LiteLLM will automatically transform to Responses API format when needed
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

        # Debug: Log the tool structure we're sending
        logger.warning(
            f"🔧 Sending {len(openai_tools)} tools to LiteLLM (Responses API: {use_responses_api}):"
        )
        for idx, tool in enumerate(openai_tools):
            logger.warning(f"  Tool {idx}: {json.dumps(tool, indent=2)}")

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
        is_claude_model = clean_model.startswith("claude-")

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
        tool_content = ""
        accumulated_text = ""  # Track accumulated text content
        text_sent = False  # Track if we've sent any text content
        text_block_closed = False  # Track if text block is closed
        output_tokens = 0
        has_sent_stop_reason = False
        last_tool_index = 0
        anthropic_tool_index = 0  # Initialize to prevent unbound variable error

        # Track tool call ID to name mapping (Azure Responses API workaround)
        tool_call_names = {}  # Maps tool_call_id -> tool_name

        # Process each chunk
        async for chunk in response_generator:
            try:
                # DIAGNOSTIC: Log full chunk structure for Azure Responses API debugging
                if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, "delta") and choice.delta:
                        delta = choice.delta
                        if hasattr(delta, "tool_calls") and delta.tool_calls:
                            logger.warning("🔍 RAW TOOL_CALL CHUNK:")
                            logger.warning(f"  Chunk type: {type(chunk)}")
                            logger.warning(f"  Delta tool_calls: {delta.tool_calls}")
                            for tc in delta.tool_calls:
                                logger.warning(f"    Tool call ID: {getattr(tc, 'id', 'NO_ID')}")
                                logger.warning(
                                    f"    Tool call index: {getattr(tc, 'index', 'NO_INDEX')}"
                                )
                                logger.warning(
                                    f"    Tool call type: {getattr(tc, 'type', 'NO_TYPE')}"
                                )
                                func = getattr(tc, "function", None)
                                if func:
                                    logger.warning(f"    Function: {func}")
                                    logger.warning(
                                        f"      name: {getattr(func, 'name', 'NO_NAME')}"
                                    )
                                    logger.warning(
                                        f"      arguments: {getattr(func, 'arguments', 'NO_ARGS')}"
                                    )

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
                            # DEBUG: Log the raw tool_call structure
                            logger.warning("🔍 Raw tool_call structure:")
                            logger.warning(f"  Type: {type(tool_call)}")
                            if isinstance(tool_call, dict):
                                logger.warning(f"  Dict keys: {tool_call.keys()}")
                                logger.warning(f"  Full dict: {tool_call}")
                            else:
                                logger.warning(f"  Object attributes: {dir(tool_call)}")
                                logger.warning(f"  Object repr: {tool_call!r}")
                                # Log key attributes
                                for attr in ["id", "index", "function", "type"]:
                                    if hasattr(tool_call, attr):
                                        val = getattr(tool_call, attr)
                                        logger.warning(f"  {attr}: {val} (type: {type(val)})")

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
                                    # Handle None values from Azure Responses API
                                    name = (
                                        function.get("name") or ""
                                        if isinstance(function, dict)
                                        else ""
                                    )
                                    tool_id = tool_call.get("id", f"toolu_{uuid.uuid4().hex[:24]}")
                                else:
                                    function = getattr(tool_call, "function", None)
                                    name = getattr(function, "name", None) or "" if function else ""
                                    tool_id = getattr(
                                        tool_call, "id", f"toolu_{uuid.uuid4().hex[:24]}"
                                    )

                                # Azure Responses API workaround: store tool name if we have it
                                if name and tool_id:
                                    tool_call_names[tool_id] = name
                                elif tool_id in tool_call_names:
                                    # Use previously stored name if current chunk doesn't have it
                                    name = tool_call_names[tool_id]
                                else:
                                    # Log warning if we can't determine tool name
                                    logger.warning(
                                        f"⚠️ Tool call {tool_id} has no name in chunk. "
                                        f"function: {function}"
                                    )
                                    # Try to infer from original request tools
                                    if original_request.tools and len(original_request.tools) > 0:
                                        # Use first tool as fallback (better than null)
                                        name = original_request.tools[0].name
                                        tool_call_names[tool_id] = name
                                        logger.warning(f"  Using fallback tool name: {name}")

                                # Start a new tool_use block
                                yield f"event: content_block_start\ndata: {json.dumps({'type': 'content_block_start', 'index': anthropic_tool_index, 'content_block': {'type': 'tool_use', 'id': tool_id, 'name': name, 'input': {}}})}\n\n"
                                tool_content = ""

                            # Extract function arguments
                            arguments = None
                            if isinstance(tool_call, dict) and "function" in tool_call:
                                function = tool_call.get("function", {})
                                logger.warning("🔍 Extracting arguments from dict function:")
                                logger.warning(f"  function type: {type(function)}")
                                logger.warning(f"  function value: {function}")
                                arguments = (
                                    function.get("arguments", "")
                                    if isinstance(function, dict)
                                    else ""
                                )
                                logger.warning(f"  extracted arguments: {arguments}")
                            elif hasattr(tool_call, "function"):
                                function = getattr(tool_call, "function", None)
                                logger.warning("🔍 Extracting arguments from object function:")
                                logger.warning(f"  function type: {type(function)}")
                                logger.warning(f"  function value: {function}")
                                if function:
                                    logger.warning(f"  function attributes: {dir(function)}")
                                    logger.warning(f"  function repr: {function!r}")
                                arguments = getattr(function, "arguments", "") if function else ""
                                logger.warning(f"  extracted arguments: {arguments}")

                            # If we have arguments, send them as a delta
                            logger.warning(
                                f"🔍 Checking if should send arguments: arguments={arguments!r}, truthiness={bool(arguments)}"
                            )
                            if arguments:
                                logger.warning(
                                    f"🔍 SENDING input_json_delta for arguments: {arguments!r}"
                                )
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

                                logger.warning(
                                    f"🔍 About to yield content_block_delta with args_json={args_json!r}, index={anthropic_tool_index}"
                                )
                                # Send the update
                                yield f"event: content_block_delta\ndata: {json.dumps({'type': 'content_block_delta', 'index': anthropic_tool_index, 'delta': {'type': 'input_json_delta', 'partial_json': args_json}})}\n\n"
                                logger.warning("✅ Yielded content_block_delta successfully")
                            else:
                                logger.warning(
                                    f"⚠️ NOT sending arguments because they are falsy: {arguments!r}"
                                )

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
        # Get request body for logging and passthrough mode
        body = await raw_request.body()
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

        # Check if this is a Claude model and passthrough mode is enabled
        if PASSTHROUGH_MODE and passthrough_handler and clean_model.startswith("claude-"):
            logger.debug("Using passthrough mode for Claude model")

            # Get configured token limits from environment for Azure Responses API
            min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "4096"))
            max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "512000"))

            # Ensure proper token limits for Azure Responses API
            max_tokens_value = request.max_tokens
            if max_tokens_value and max_tokens_value > 1:
                # Ensure we use at least the minimum configured limit
                max_tokens_value = max(min_tokens_limit, max_tokens_value)
                # Cap at maximum configured limit
                max_tokens_value = min(max_tokens_limit, max_tokens_value)
            else:
                # Default to maximum limit for Azure Responses API models
                max_tokens_value = max_tokens_limit

            # Map the model to Azure model for passthrough
            model_lower = clean_model.lower()
            azure_model = (
                BIG_MODEL
                if "sonnet" in model_lower or "opus" in model_lower
                else (SMALL_MODEL if "haiku" in model_lower else BIG_MODEL)
            )

            # Check if this should use Responses API
            openai_base_url = os.environ.get("OPENAI_BASE_URL", "")
            use_responses_api = (
                openai_base_url
                and "/responses" in openai_base_url
                and (
                    azure_model.startswith(("o3-", "o4-"))
                    or azure_model.startswith("gpt-5-code")
                    or azure_model == "gpt-5"
                )
            )

            # Determine temperature
            temperature = (
                1.0
                if use_responses_api
                else (request.temperature if request.temperature is not None else 1.0)
            )

            # Prepare request data for passthrough
            request_data = {
                "model": clean_model,
                "max_tokens": max_tokens_value,
                "messages": [],
                "stream": request.stream,
                "temperature": temperature,
            }

            # Add system message if present
            if request.system:
                request_data["system"] = request.system

            # SANITIZE MESSAGES for passthrough mode too
            # Anthropic API (like Azure) doesn't accept thinking blocks in conversation history
            sanitized_messages = sanitize_message_content(request.messages)
            logger.debug(
                f"Passthrough mode sanitization: {len(request.messages)} -> {len(sanitized_messages)} messages"
            )

            # Convert messages to the format expected by Anthropic API
            for msg in sanitized_messages:
                passthrough_msg = {"role": msg.role, "content": msg.content}
                request_data["messages"].append(passthrough_msg)

            # Add tools if present
            if request.tools:
                request_data["tools"] = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in request.tools
                ]

            # Add tool_choice if present
            if request.tool_choice:
                request_data["tool_choice"] = request.tool_choice

            # Add optional parameters
            if request.stop_sequences:
                request_data["stop_sequences"] = request.stop_sequences
            if request.top_p:
                request_data["top_p"] = request.top_p
            if request.top_k:
                request_data["top_k"] = request.top_k

            try:
                # Use passthrough handler
                async with passthrough_handler:
                    passthrough_response = await passthrough_handler.handle_request(request_data)

                # Log the request
                num_tools = len(request.tools) if request.tools else 0
                log_request_beautifully(
                    "POST",
                    raw_request.url.path,
                    display_model,
                    f"passthrough/{clean_model}",
                    len(request.messages),
                    num_tools,
                    200,
                )

                # Handle streaming response
                if request.stream:
                    raise HTTPException(
                        status_code=501, detail="Streaming not supported in passthrough mode"
                    )
                return passthrough_response

            except Exception as e:
                logger.error(f"Passthrough mode failed: {e}")
                # Fall back to normal LiteLLM processing
                logger.info("Falling back to LiteLLM processing")
                # Continue with normal processing below

        logger.info(f"🔵 REQUEST MODEL AFTER VALIDATION: '{request.model}'")
        # Convert Anthropic request to LiteLLM format
        litellm_request = convert_anthropic_to_litellm(request)
        logger.info(f"🔵 LITELLM_REQUEST MODEL AFTER CONVERSION: '{litellm_request.get('model')}'")

        # Determine which API key to use based on the model
        if request.model.startswith("azure/"):
            # Azure models need explicit api_base configuration
            litellm_request["api_key"] = OPENAI_API_KEY

            if AZURE_BASE_URL:
                # Strip query string from base URL
                clean_azure_base = (
                    AZURE_BASE_URL.split("?")[0] if "?" in AZURE_BASE_URL else AZURE_BASE_URL
                )

                # Detect if using Responses API (for o3/o4/gpt-5 models)
                use_responses_api_endpoint = "/responses" in AZURE_BASE_URL

                # Strip /responses from path if present (we'll add it back explicitly)
                if clean_azure_base.endswith("/responses"):
                    clean_azure_base = clean_azure_base[: -len("/responses")]

                # For Responses API models, explicitly include /responses in api_base
                # This ensures LiteLLM routes to the correct endpoint
                if use_responses_api_endpoint:
                    litellm_request["api_base"] = clean_azure_base + "/responses"
                else:
                    litellm_request["api_base"] = clean_azure_base

                litellm_request["api_version"] = os.environ.get(
                    "AZURE_API_VERSION", "2025-04-01-preview"
                )

                logger.warning(f"🔧 Azure config for {request.model}:")
                logger.warning(f"  api_base: {litellm_request['api_base']}")
                logger.warning(f"  using_responses_api: {use_responses_api_endpoint}")
                logger.warning(f"  api_version: {litellm_request['api_version']}")
                logger.warning(f"  api_key: {'SET' if OPENAI_API_KEY else 'NOT SET'}")
        elif request.model.startswith("openai/"):
            litellm_request["api_key"] = OPENAI_API_KEY
            logger.debug(f"Using OpenAI API key for model: {request.model}")
        elif request.model.startswith("gemini/"):
            litellm_request["api_key"] = GEMINI_API_KEY
            logger.debug(f"Using Gemini API key for model: {request.model}")
        elif request.model.startswith("github/") or request.model.startswith("github_copilot/"):
            litellm_request["api_key"] = GITHUB_TOKEN
            # Add GitHub Copilot specific headers
            if request.model.startswith("github_copilot/"):
                litellm_request["extra_headers"] = {
                    "editor-version": "vscode/1.95.0",
                    "editor-plugin-version": "copilot-chat/0.26.7",
                }
            logger.debug(f"Using GitHub token for model: {request.model}")
        else:
            litellm_request["api_key"] = ANTHROPIC_API_KEY
            logger.debug(f"Using Anthropic API key for model: {request.model}")

        # For OpenAI and Azure models - modify request format to work with limitations
        if (
            "openai" in litellm_request["model"] or "azure" in litellm_request["model"]
        ) and "messages" in litellm_request:
            logger.debug(f"Processing OpenAI/Azure model request: {litellm_request['model']}")

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
                            except (TypeError, ValueError):
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
                                    except (TypeError, ValueError):
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
                                                except (TypeError, ValueError):
                                                    text_content += str(item) + "\n"
                                    elif isinstance(result_content, dict):
                                        # Handle dictionary content
                                        if result_content.get("type") == "text":
                                            text_content += result_content.get("text", "") + "\n"
                                        else:
                                            try:
                                                text_content += json.dumps(result_content) + "\n"
                                            except (TypeError, ValueError):
                                                text_content += str(result_content) + "\n"
                                    else:
                                        # Fallback for any other type
                                        try:
                                            text_content += str(result_content) + "\n"
                                        except (TypeError, ValueError, AttributeError):
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

        # Handle streaming mode
        if request.stream:
            # Use LiteLLM for streaming
            num_tools = len(request.tools) if request.tools else 0

            log_request_beautifully(
                "POST",
                raw_request.url.path,
                display_model,
                litellm_request.get("model"),
                len(litellm_request["messages"]),
                num_tools,
                200,  # Assuming success at this point
            )
            # Ensure we use the async version for streaming
            # Add timeout to request parameters
            litellm_request["timeout"] = PROXY_TIMEOUT

            # Add request tracking
            request_id = generate_request_id()
            log_request_lifecycle(
                request_id,
                "request_start",
                {"model": litellm_request.get("model"), "stream": litellm_request.get("stream")},
            )

            try:
                # Use asyncio.wait_for for defense-in-depth timeout enforcement
                response_generator = await asyncio.wait_for(
                    litellm.acompletion(**litellm_request),
                    timeout=PROXY_TIMEOUT + 5.0,  # Add 5s buffer for cleanup
                )
                log_request_lifecycle(request_id, "request_complete")
            except TimeoutError:
                log_request_lifecycle(request_id, "request_timeout", {"timeout": PROXY_TIMEOUT})
                raise HTTPException(
                    status_code=504,
                    detail=f"Request {request_id} timed out after {PROXY_TIMEOUT}s",
                )
            except Exception as e:
                log_request_lifecycle(
                    request_id,
                    "request_error",
                    {"error": str(e), "error_type": type(e).__name__},
                )
                raise

            return StreamingResponse(
                handle_streaming(response_generator, request),
                media_type="text/event-stream",
                headers={"X-Request-ID": request_id},
            )
        # Use LiteLLM for regular completion
        num_tools = len(request.tools) if request.tools else 0

        log_request_beautifully(
            "POST",
            raw_request.url.path,
            display_model,
            litellm_request.get("model"),
            len(litellm_request["messages"]),
            num_tools,
            200,  # Assuming success at this point
        )
        logger.info(
            f"🔥 LITELLM REQUEST MODEL: '{litellm_request.get('model')}', api_base: '{litellm_request.get('api_base', 'NOT SET')}'"
        )
        logger.info(f"🔥 LITELLM REQUEST KEYS: {list(litellm_request.keys())}")
        start_time = time.time()
        # Add timeout to request parameters
        litellm_request["timeout"] = PROXY_TIMEOUT

        # Add request tracking
        request_id = generate_request_id()
        log_request_lifecycle(
            request_id,
            "request_start",
            {"model": litellm_request.get("model"), "stream": litellm_request.get("stream")},
        )

        try:
            # Run sync function in executor with timeout
            litellm_response = await asyncio.wait_for(
                asyncio.to_thread(litellm.completion, **litellm_request),
                timeout=PROXY_TIMEOUT + 5.0,
            )
            log_request_lifecycle(request_id, "request_complete")
        except TimeoutError:
            log_request_lifecycle(request_id, "request_timeout", {"timeout": PROXY_TIMEOUT})
            raise HTTPException(
                status_code=504, detail=f"Request {request_id} timed out after {PROXY_TIMEOUT}s"
            )
        except Exception as e:
            log_request_lifecycle(
                request_id,
                "request_error",
                {"error": str(e), "error_type": type(e).__name__},
            )
            raise
        logger.debug(
            f"✅ RESPONSE RECEIVED: Model={litellm_request.get('model')}, Time={time.time() - start_time:.2f}s"
        )

        # Convert LiteLLM response to Anthropic format
        anthropic_response = convert_litellm_to_anthropic(litellm_response, request)

        # Return response with request ID header
        return Response(
            content=anthropic_response.model_dump_json(),
            media_type="application/json",
            headers={"X-Request-ID": request_id},
        )

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()

        # Capture as much info as possible about the error
        error_details = {"error": str(e), "type": type(e).__name__, "traceback": error_traceback}

        # Check for LiteLLM-specific attributes
        for attr in ["message", "status_code", "response", "llm_provider", "model"]:
            if hasattr(e, attr):
                attr_value = getattr(e, attr)
                # Convert non-serializable objects to string representation
                try:
                    json.dumps(attr_value)  # Test if it's JSON serializable
                    error_details[attr] = attr_value
                except (TypeError, ValueError):
                    # If not serializable, convert to string
                    error_details[attr] = str(attr_value)

        # Check for additional exception details in dictionaries
        if hasattr(e, "__dict__"):
            for key, value in e.__dict__.items():
                if key not in error_details and key not in ["args", "__traceback__"]:
                    # Always convert to string to ensure JSON serializability
                    error_details[key] = str(value)

        # SECURITY: Sanitize tokens from error details before logging (Issue #1922)
        sanitized_error_details = token_sanitizer.sanitize(error_details)

        # Log all error details (sanitized and JSON-serializable)
        logger.error(f"Error processing request: {json.dumps(sanitized_error_details, indent=2)}")

        # Format error for response (also sanitized)
        error_message = f"Error: {token_sanitizer.sanitize(str(e))}"
        if sanitized_error_details.get("message"):
            error_message += f"\nMessage: {sanitized_error_details['message']}"
        if sanitized_error_details.get("response"):
            error_message += f"\nResponse: {sanitized_error_details['response']}"

        # Return detailed error
        status_code = error_details.get("status_code", 500)
        raise HTTPException(status_code=status_code, detail=error_message)


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
            from litellm import token_counter  # type: ignore

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
        raise HTTPException(status_code=500, detail=f"Error counting tokens: {e!s}")


@app.post("/openai/responses")
async def openai_responses(request: OpenAIResponsesRequest, raw_request: Request):
    """
    Azure OpenAI Responses API endpoint.

    This endpoint accepts direct OpenAI Responses API format requests:
    {"model": "gpt-5-codex", "input": "text"}

    And forwards them to Azure OpenAI Responses API.
    """
    try:
        logger.debug(
            f"📊 RESPONSES API REQUEST: Model={request.model}, Input length={len(request.input)}"
        )

        # Construct Azure OpenAI endpoint URL
        azure_endpoint = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
        if not azure_endpoint:
            raise HTTPException(status_code=500, detail="OPENAI_BASE_URL not configured")

        # Get API key
        azure_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
        if not azure_api_key:
            raise HTTPException(status_code=500, detail="Azure API key not configured")

        # Prepare Azure request data
        azure_request_data = {"model": request.model, "input": request.input}

        # Prepare headers
        headers = {"Content-Type": "application/json", "api-key": azure_api_key}

        logger.debug(f"Making request to Azure: {azure_endpoint}")
        logger.debug(f"Request data: {azure_request_data}")

        # Make request to Azure OpenAI Responses API
        async with httpx.AsyncClient(timeout=60.0) as client:
            azure_response = await client.post(
                azure_endpoint, json=azure_request_data, headers=headers
            )

            logger.debug(f"Azure response status: {azure_response.status_code}")

            if azure_response.status_code == 200:
                response_data = azure_response.json()
                logger.debug(f"✅ RESPONSES API SUCCESS: {response_data.get('id', 'no-id')}")

                # Log the request beautifully
                log_request_beautifully(
                    "POST",
                    "/openai/responses",
                    request.model,
                    request.model,
                    1,  # Single input
                    0,  # No tools
                    200,
                )

                return response_data
            error_text = azure_response.text
            logger.error(f"Azure API error {azure_response.status_code}: {error_text}")
            raise HTTPException(
                status_code=azure_response.status_code, detail=f"Azure API error: {error_text}"
            )

    except httpx.RequestError as e:
        logger.error(f"Request error: {e!s}")
        raise HTTPException(status_code=500, detail=f"Request error: {e!s}")
    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(f"Error in responses endpoint: {e!s}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e!s}")


@app.get("/")
async def root():
    return {"message": "Anthropic Proxy for LiteLLM with OpenAI Responses API"}


@app.get("/status")
async def status():
    """Get proxy status including passthrough mode and GitHub Copilot information."""
    status_info = {
        "proxy_active": True,
        "anthropic_api_key_configured": bool(ANTHROPIC_API_KEY),
        "openai_api_key_configured": bool(OPENAI_API_KEY),
        "gemini_api_key_configured": bool(GEMINI_API_KEY),
        "github_token_configured": bool(GITHUB_TOKEN),
        "github_copilot_enabled": GITHUB_COPILOT_ENABLED,
        "github_copilot_models": GITHUB_COPILOT_MODELS,
        "preferred_provider": PREFERRED_PROVIDER,
        "passthrough_mode": PASSTHROUGH_MODE,
    }

    if PASSTHROUGH_MODE and passthrough_handler:
        status_info["passthrough_status"] = passthrough_handler.get_status()

    return status_info


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

    # Print to console
    print(log_line)
    print(model_line)
    sys.stdout.flush()


def find_available_port(preferred_port: int, max_attempts: int = 50) -> int:
    """Find an available port starting from preferred_port.

    Args:
        preferred_port: The preferred port to try first
        max_attempts: Maximum number of ports to try

    Returns:
        An available port number

    Raises:
        RuntimeError: If no available port is found within max_attempts
    """
    import socket

    for port_offset in range(max_attempts):
        port = preferred_port + port_offset
        try:
            # Try to bind to the port to check availability
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return port  # Port is available
        except OSError:
            continue  # Port is in use, try the next one

    raise RuntimeError(
        f"No available port found starting from {preferred_port} (tried {max_attempts} ports)"
    )


def run_server(host: str = "127.0.0.1", port: int = 8082):
    """Run the built-in proxy server with dynamic port selection."""
    try:
        import uvicorn  # type: ignore

        # Try to find an available port
        try:
            available_port = find_available_port(port)
            if available_port != port:
                print(f"Port {port} is in use, using port {available_port} instead")

            uvicorn.run(app, host=host, port=available_port)
        except RuntimeError as e:
            print(f"Error finding available port: {e}")
            print(f"Attempting to start on original port {port}")
            uvicorn.run(app, host=host, port=port)
    except ImportError:
        logger.error("uvicorn not available - cannot run built-in server")
        raise


if __name__ == "__main__":
    import os

    # Read PORT from environment with error handling
    port = 8082  # Default port
    port_env = os.environ.get("PORT")
    if port_env:
        try:
            port = int(port_env)
            if not (1 <= port <= 65535):
                print(f"Warning: PORT={port_env} is invalid (must be 1-65535), using default 8082")
                port = 8082
        except ValueError:
            print(f"Warning: PORT={port_env} is not a valid number, using default 8082")
            port = 8082

    run_server(port=port)
