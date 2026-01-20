"""
Azure Unified Handler
Provides a single interface for handling both Azure Chat and Responses API requests.
Integrates seamlessly with the existing integrated_proxy.py architecture.
"""

import json
import time
from typing import Any

from .azure_unified_integration import AzureUnifiedProvider
from .sanitizing_logger import get_sanitizing_logger

# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)


class AzureUnifiedHandler:
    """
    Unified handler that automatically routes between Azure Chat and Responses APIs.

    This class provides a single interface that the integrated proxy can use,
    eliminating the need for dual routing logic in the main proxy code.
    """

    def __init__(self, api_key: str, base_url: str, api_version: str = "2025-01-01-preview"):
        """
        Initialize the unified handler.

        Args:
            api_key: Azure API key
            base_url: Azure base URL
            api_version: API version for Chat API
        """
        self.provider = AzureUnifiedProvider(api_key, base_url, api_version)
        logger.info(f"✅ Azure unified handler initialized: {base_url}")

    async def handle_anthropic_request(self, anthropic_request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an Anthropic/Claude format request and route to appropriate Azure API.

        Args:
            anthropic_request: Request in Anthropic format

        Returns:
            Response in Anthropic format
        """
        # Convert Anthropic request to OpenAI format for processing
        openai_request = self._convert_anthropic_to_openai(anthropic_request)

        # Let the provider handle routing and transformation
        azure_response = await self.provider.make_request(
            openai_request, stream=anthropic_request.get("stream", False)
        )

        # Convert back to Anthropic format
        return self._convert_openai_to_anthropic(azure_response)

    async def handle_openai_request(self, openai_request: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an OpenAI format request and route to appropriate Azure API.

        Args:
            openai_request: Request in OpenAI format

        Returns:
            Response in OpenAI format
        """
        # Provider handles everything
        return await self.provider.make_request(
            openai_request, stream=openai_request.get("stream", False)
        )

    def should_use_responses_api(self, model: str) -> bool:
        """
        Check if a model should use Responses API.
        Delegates to the provider's routing logic.

        Args:
            model: Model name

        Returns:
            True if should use Responses API
        """
        return self.provider.should_use_responses_api(model)

    def _convert_anthropic_to_openai(self, anthropic_request: dict[str, Any]) -> dict[str, Any]:
        """Convert Anthropic request format to OpenAI format."""
        openai_request = {
            "model": anthropic_request.get("model", "gpt-5"),
            "messages": anthropic_request.get("messages", []),
            "stream": anthropic_request.get("stream", False),
        }

        # Handle max_tokens
        if "max_tokens" in anthropic_request:
            openai_request["max_tokens"] = anthropic_request["max_tokens"]

        # Handle temperature
        if "temperature" in anthropic_request:
            openai_request["temperature"] = anthropic_request["temperature"]

        # Handle tools
        if "tools" in anthropic_request:
            openai_request["tools"] = anthropic_request["tools"]

        if "tool_choice" in anthropic_request:
            openai_request["tool_choice"] = anthropic_request["tool_choice"]

        return openai_request

    def _convert_openai_to_anthropic(self, openai_response: dict[str, Any]) -> dict[str, Any]:
        """Convert OpenAI response format to Anthropic format."""
        if "error" in openai_response:
            # Return error in Anthropic format
            return {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": openai_response["error"].get("message", "Unknown error"),
                },
            }

        # Convert successful response to Anthropic format
        choices = openai_response.get("choices", [])
        if not choices:
            return {
                "type": "message",
                "id": openai_response.get("id", f"msg_{int(time.time())}"),
                "content": [{"type": "text", "text": ""}],
                "model": openai_response.get("model", "gpt-5"),
                "role": "assistant",
                "stop_reason": "end_turn",
                "usage": openai_response.get("usage", {}),
            }

        choice = choices[0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Build Anthropic response
        anthropic_response = {
            "type": "message",
            "id": openai_response.get("id", f"msg_{int(time.time())}"),
            "content": [],
            "model": openai_response.get("model", "gpt-5"),
            "role": "assistant",
            "stop_reason": self._map_finish_reason(choice.get("finish_reason", "stop")),
            "usage": self._convert_usage(openai_response.get("usage", {})),
        }

        # Handle content (include even if empty to maintain format consistency)
        anthropic_response["content"].append({"type": "text", "text": content or ""})

        # Handle tool calls
        if message.get("tool_calls"):
            for tool_call in message["tool_calls"]:
                anthropic_response["content"].append(
                    {
                        "type": "tool_use",
                        "id": tool_call.get("id", f"toolu_{int(time.time())}"),
                        "name": tool_call.get("function", {}).get("name", ""),
                        "input": json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                    }
                )

        return anthropic_response

    def _map_finish_reason(self, openai_finish_reason: str) -> str:
        """Map OpenAI finish reason to Anthropic format."""
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
            "content_filter": "stop_sequence",
        }
        return mapping.get(openai_finish_reason, "end_turn")

    def _convert_usage(self, openai_usage: dict[str, Any]) -> dict[str, Any]:
        """Convert OpenAI usage format to Anthropic format."""
        return {
            "input_tokens": openai_usage.get("prompt_tokens", 0),
            "output_tokens": openai_usage.get("completion_tokens", 0),
        }


def create_azure_unified_handler(
    api_key: str, base_url: str, api_version: str = "2025-01-01-preview"
) -> AzureUnifiedHandler:
    """
    Create an Azure unified handler instance.

    Args:
        api_key: Azure API key
        base_url: Azure base URL
        api_version: API version

    Returns:
        Configured AzureUnifiedHandler
    """
    return AzureUnifiedHandler(api_key, base_url, api_version)
