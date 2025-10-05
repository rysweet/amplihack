"""Built-in FastAPI proxy server with OpenAI Responses API support."""

import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Union

import httpx  # type: ignore
import litellm  # type: ignore
from dotenv import load_dotenv  # type: ignore
from fastapi import FastAPI, HTTPException, Request  # type: ignore
from fastapi.responses import StreamingResponse  # type: ignore
from pydantic import BaseModel, field_validator  # type: ignore

from .github_auth import GitHubAuthManager
from .passthrough import PassthroughHandler

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.WARN,  # Change to INFO level to show more details
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Tell uvicorn's loggers to be quiet
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


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

# Get API keys from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Get preferred provider (default to openai)
PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER", "openai").lower()

# Initialize passthrough handler
PASSTHROUGH_MODE = os.environ.get("PASSTHROUGH_MODE", "false").lower() == "true"
passthrough_handler = PassthroughHandler() if PASSTHROUGH_MODE else None

if PASSTHROUGH_MODE:
    logger.info(
        "Passthrough mode enabled - will try Anthropic API first, fallback to Azure on 429 errors"
    )

# Get model mapping configuration from environment
# Default to latest OpenAI models if not set
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

# List of GitHub Copilot models
GITHUB_COPILOT_MODELS = ["copilot-gpt-4", "copilot-gpt-3.5-turbo"]

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
    source: Dict[str, Any]


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any], Any]


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
        elif clean_v.startswith("openai/"):
            clean_v = clean_v[7:]
        elif clean_v.startswith("gemini/"):
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
            elif clean_v in GITHUB_COPILOT_MODELS and not v.startswith("github/"):
                new_model = f"github/{clean_v}"
                mapped = True  # Technically mapped to add prefix
            elif clean_v in OPENAI_MODELS and not v.startswith("openai/"):
                new_model = f"openai/{clean_v}"
                mapped = True  # Technically mapped to add prefix
        # --- Mapping Logic --- END ---

        if mapped:
            logger.debug(f"📌 MODEL MAPPING: '{original_model}' ➡️ '{new_model}'")
        else:
            # If no mapping occurred and no prefix exists, log warning or decide default
            if not v.startswith(("openai/", "gemini/", "github/", "anthropic/")):
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
        elif clean_v.startswith("openai/"):
            clean_v = clean_v[7:]
        elif clean_v.startswith("gemini/"):
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
            elif clean_v in GITHUB_COPILOT_MODELS and not v.startswith("github/"):
                new_model = f"github/{clean_v}"
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
    content: List[Union[ContentBlockText, ContentBlockToolUse]]
    type: Literal["message"] = "message"
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]] = None
    stop_sequence: Optional[str] = None
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


def convert_anthropic_to_litellm(anthropic_request: MessagesRequest) -> Dict[str, Any]:
    """Convert Anthropic API request format to LiteLLM format (which follows OpenAI)."""
    # LiteLLM already handles Anthropic models when using the format model="anthropic/claude-3-opus-20240229"
    # So we just need to convert our Pydantic model to a dict in the expected format

    # Initialize the LiteLLM request dict first to ensure we always return the right structure
    litellm_request = {
        "model": anthropic_request.model,  # it understands "anthropic/claude-x" format
        "messages": [],
        "max_tokens": anthropic_request.max_tokens,
        "temperature": anthropic_request.temperature,
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
                            processed_content_block = {
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
        if hasattr(anthropic_request.tool_choice, "dict"):
            tool_choice_dict = anthropic_request.tool_choice.dict()
        else:
            tool_choice_dict = anthropic_request.tool_choice

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
    litellm_response: Union[Dict[str, Any], Any], original_request: MessagesRequest
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
            choices = litellm_response.choices
            message = choices[0].message if choices and len(choices) > 0 else None
            content_text = message.content if message and hasattr(message, "content") else ""
            tool_calls = message.tool_calls if message and hasattr(message, "tool_calls") else None
            finish_reason = choices[0].finish_reason if choices and len(choices) > 0 else "stop"
            usage_info = litellm_response.usage
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
                    response_dict = (
                        litellm_response.model_dump()
                        if hasattr(litellm_response, "model_dump")
                        else litellm_response.__dict__
                    )
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
        error_message = f"Error converting response: {str(e)}\n\nFull traceback:\n{error_traceback}"
        logger.error(error_message)

        # In case of any error, create a fallback response
        return MessagesResponse(
            id=f"msg_{uuid.uuid4()}",
            model=original_request.model,
            role="assistant",
            content=[
                {
                    "type": "text",
                    "text": f"Error converting response: {str(e)}. Please check server logs.",
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
                        delta_content = delta.content
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
                        delta_tool_calls = delta.tool_calls
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
                                current_index = tool_call.index
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
                logger.error(f"Error processing chunk: {str(e)}")
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
        error_message = f"Error in streaming: {str(e)}\n\nFull traceback:\n{error_traceback}"
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

            # Prepare request data for passthrough
            request_data = {
                "model": clean_model,
                "max_tokens": request.max_tokens,
                "messages": [],
                "stream": request.stream,
                "temperature": request.temperature,
            }

            # Add system message if present
            if request.system:
                request_data["system"] = request.system

            # Convert messages to the format expected by Anthropic API
            for msg in request.messages:
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
                    # TODO: Implement streaming for passthrough mode
                    raise HTTPException(
                        status_code=501, detail="Streaming not yet implemented for passthrough mode"
                    )
                else:
                    return passthrough_response

            except Exception as e:
                logger.error(f"Passthrough mode failed: {e}")
                # Fall back to normal LiteLLM processing
                logger.info("Falling back to LiteLLM processing")
                # Continue with normal processing below

        # Convert Anthropic request to LiteLLM format
        litellm_request = convert_anthropic_to_litellm(request)

        # Determine which API key to use based on the model
        if request.model.startswith("openai/"):
            litellm_request["api_key"] = OPENAI_API_KEY
            logger.debug(f"Using OpenAI API key for model: {request.model}")
        elif request.model.startswith("gemini/"):
            litellm_request["api_key"] = GEMINI_API_KEY
            logger.debug(f"Using Gemini API key for model: {request.model}")
        elif request.model.startswith("github/"):
            litellm_request["api_key"] = GITHUB_TOKEN
            logger.debug(f"Using GitHub token for model: {request.model}")
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
            response_generator = await litellm.acompletion(**litellm_request)

            return StreamingResponse(
                handle_streaming(response_generator, request), media_type="text/event-stream"
            )
        else:
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
            start_time = time.time()
            litellm_response = litellm.completion(**litellm_request)
            logger.debug(
                f"✅ RESPONSE RECEIVED: Model={litellm_request.get('model')}, Time={time.time() - start_time:.2f}s"
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

        # Log all error details (now guaranteed to be JSON-serializable)
        logger.error(f"Error processing request: {json.dumps(error_details, indent=2)}")

        # Format error for response
        error_message = f"Error: {str(e)}"
        if "message" in error_details and error_details["message"]:
            error_message += f"\nMessage: {error_details['message']}"
        if "response" in error_details and error_details["response"]:
            error_message += f"\nResponse: {error_details['response']}"

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
        logger.error(f"Error counting tokens: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Error counting tokens: {str(e)}")


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
            else:
                error_text = azure_response.text
                logger.error(f"Azure API error {azure_response.status_code}: {error_text}")
                raise HTTPException(
                    status_code=azure_response.status_code, detail=f"Azure API error: {error_text}"
                )

    except httpx.RequestError as e:
        logger.error(f"Request error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(f"Error in responses endpoint: {str(e)}\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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


def run_server(host: str = "127.0.0.1", port: int = 8082):
    """Run the built-in proxy server."""
    try:
        import uvicorn  # type: ignore

        uvicorn.run(app, host=host, port=port)
    except ImportError:
        logger.error("uvicorn not available - cannot run built-in server")
        raise


if __name__ == "__main__":
    run_server()
