"""Passthrough mode handler for Anthropic -> Azure OpenAI fallback."""

import json
import os
import time
from typing import Any

import httpx  # type: ignore

from .sanitizing_logger import get_sanitizing_logger

# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)


class PassthroughHandler:
    """Handles passthrough mode with fallback from Anthropic to Azure OpenAI on 429 errors."""

    def __init__(self):
        """Initialize passthrough handler."""
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

        # Passthrough mode configuration
        self.passthrough_enabled = os.getenv("PASSTHROUGH_MODE", "false").lower() == "true"
        self.fallback_enabled = os.getenv("PASSTHROUGH_FALLBACK_ENABLED", "true").lower() == "true"
        self.max_retries = int(os.getenv("PASSTHROUGH_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("PASSTHROUGH_RETRY_DELAY", "1.0"))
        self.fallback_after_failures = int(os.getenv("PASSTHROUGH_FALLBACK_AFTER_FAILURES", "2"))

        # Azure deployment mappings
        self.azure_deployments = {
            "claude-3-5-sonnet-20241022": os.getenv("AZURE_CLAUDE_SONNET_DEPLOYMENT", "gpt-4"),
            "claude-3-5-haiku-20241022": os.getenv("AZURE_CLAUDE_HAIKU_DEPLOYMENT", "gpt-4o-mini"),
            "claude-3-opus-20240229": os.getenv("AZURE_CLAUDE_OPUS_DEPLOYMENT", "gpt-4"),
            "claude-3-sonnet-20240229": os.getenv("AZURE_CLAUDE_SONNET_DEPLOYMENT", "gpt-4"),
            "claude-3-haiku-20240307": os.getenv("AZURE_CLAUDE_HAIKU_DEPLOYMENT", "gpt-4o-mini"),
        }

        # Rate limiting tracking
        self.anthropic_failure_count = 0
        self.last_failure_time = 0
        self.failure_window = 300  # 5 minutes
        self.switched_to_fallback = False

        # HTTP clients
        self.anthropic_client = None
        self.azure_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.anthropic_client = httpx.AsyncClient(timeout=60.0)
        self.azure_client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.anthropic_client:
            await self.anthropic_client.aclose()
        if self.azure_client:
            await self.azure_client.aclose()

    def is_enabled(self) -> bool:
        """Check if passthrough mode is enabled."""
        return self.passthrough_enabled

    def should_use_fallback(self) -> bool:
        """Determine if we should use Azure fallback based on failure count."""
        if not self.fallback_enabled:
            return False

        current_time = time.time()

        # Reset failure count if outside failure window
        if current_time - self.last_failure_time > self.failure_window:
            self.anthropic_failure_count = 0
            self.switched_to_fallback = False

        # Use fallback if we've had too many failures
        if self.anthropic_failure_count >= self.fallback_after_failures:
            self.switched_to_fallback = True
            return True

        return self.switched_to_fallback

    def record_anthropic_failure(self):
        """Record a failure when calling Anthropic API."""
        self.anthropic_failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            f"Anthropic API failure recorded. Count: {self.anthropic_failure_count}/{self.fallback_after_failures}"
        )

    def record_anthropic_success(self):
        """Record a successful call to Anthropic API."""
        if self.anthropic_failure_count > 0:
            logger.info("Anthropic API call successful, resetting failure count")
            self.anthropic_failure_count = 0
            self.switched_to_fallback = False

    async def handle_request(self, request_data: dict[str, Any]) -> dict[str, Any] | httpx.Response:
        """
        Handle a request in passthrough mode.

        Args:
            request_data: The request data in Anthropic format

        Returns:
            Response data or httpx.Response object
        """
        if not self.is_enabled():
            raise ValueError("Passthrough mode is not enabled")

        # Check if we should go straight to fallback
        if self.should_use_fallback():
            logger.info("Using Azure fallback due to previous failures")
            return await self._call_azure_api(request_data)

        # Try Anthropic API first
        try:
            logger.debug("Attempting Anthropic API call")
            response = await self._call_anthropic_api(request_data)
            self.record_anthropic_success()
            return response

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"Anthropic API returned 429 rate limit error: {e}")
                self.record_anthropic_failure()

                if self.fallback_enabled:
                    logger.info("Switching to Azure OpenAI fallback due to 429 error")
                    return await self._call_azure_api(request_data)
                raise

            logger.error(f"Anthropic API returned error {e.response.status_code}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic API: {e}")
            self.record_anthropic_failure()

            if self.fallback_enabled and self.should_use_fallback():
                logger.info("Switching to Azure OpenAI fallback due to unexpected error")
                return await self._call_azure_api(request_data)
            raise

    async def _call_anthropic_api(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Call the Anthropic API directly."""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        }

        url = "https://api.anthropic.com/v1/messages"

        logger.debug(f"Making request to Anthropic API: {url}")

        if self.anthropic_client is None:
            raise ValueError("Anthropic client not initialized")
        response = await self.anthropic_client.post(url, json=request_data, headers=headers)

        response.raise_for_status()
        return response.json()

    async def _call_azure_api(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Call Azure OpenAI API as fallback."""
        if not self.azure_openai_key or not self.azure_openai_endpoint:
            raise ValueError("Azure OpenAI configuration not complete")

        # Convert Anthropic request to Azure OpenAI format
        azure_request = self._convert_anthropic_to_azure(request_data)

        # Get the deployment name for the model
        model = request_data.get("model", "")
        deployment = self.azure_deployments.get(model, "gpt-4")

        # Construct Azure URL
        url = f"{self.azure_openai_endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.azure_openai_key,
        }

        params = {"api-version": self.azure_openai_api_version}

        logger.debug(f"Making request to Azure OpenAI: {url}")
        logger.debug(f"Using deployment: {deployment} for model: {model}")

        if self.azure_client is None:
            raise ValueError("Azure client not initialized")
        response = await self.azure_client.post(
            url, json=azure_request, headers=headers, params=params
        )

        response.raise_for_status()
        azure_response = response.json()

        # Convert Azure response back to Anthropic format
        return self._convert_azure_to_anthropic(azure_response, request_data.get("model", ""))

    def _convert_anthropic_to_azure(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Convert Anthropic request format to Azure OpenAI format."""
        azure_request = {
            "messages": [],
            "max_tokens": request_data.get("max_tokens", 1000),
            "temperature": request_data.get("temperature", 1.0),
            "stream": request_data.get("stream", False),
        }

        # Add system message if present
        if request_data.get("system"):
            system_content = request_data["system"]
            if isinstance(system_content, list):
                # Handle list of system content blocks
                system_text = ""
                for block in system_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_text += block.get("text", "") + "\n"
                    elif isinstance(block, str):
                        system_text += block + "\n"
                azure_request["messages"].append({"role": "system", "content": system_text.strip()})
            else:
                azure_request["messages"].append({"role": "system", "content": str(system_content)})

        # Convert messages
        for msg in request_data.get("messages", []):
            azure_msg = {"role": msg["role"]}

            content = msg.get("content", "")
            if isinstance(content, str):
                azure_msg["content"] = content
            elif isinstance(content, list):
                # Handle content blocks
                text_content = ""
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_content += block.get("text", "") + "\n"
                        elif block.get("type") == "tool_result":
                            # Extract tool result content
                            result_content = block.get("content", "")
                            if isinstance(result_content, str):
                                text_content += result_content + "\n"
                            elif isinstance(result_content, list):
                                for item in result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "") + "\n"
                                    else:
                                        text_content += str(item) + "\n"
                            else:
                                text_content += str(result_content) + "\n"
                        elif block.get("type") == "tool_use":
                            # Convert tool use to text representation
                            tool_name = block.get("name", "unknown")
                            tool_input = json.dumps(block.get("input", {}))
                            text_content += f"Tool: {tool_name}\nInput: {tool_input}\n\n"

                azure_msg["content"] = text_content.strip() or "..."
            else:
                azure_msg["content"] = str(content)

            azure_request["messages"].append(azure_msg)

        # Handle optional parameters
        if "stop_sequences" in request_data:
            azure_request["stop"] = request_data["stop_sequences"]

        if "top_p" in request_data:
            azure_request["top_p"] = request_data["top_p"]

        return azure_request

    def _convert_azure_to_anthropic(
        self, azure_response: dict[str, Any], original_model: str
    ) -> dict[str, Any]:
        """Convert Azure OpenAI response to Anthropic format."""
        choice = azure_response.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = azure_response.get("usage", {})

        # Create Anthropic-style response
        anthropic_response = {
            "id": azure_response.get("id", f"msg_{int(time.time())}"),
            "type": "message",
            "role": "assistant",
            "model": original_model,
            "content": [{"type": "text", "text": message.get("content", "")}],
            "stop_reason": self._map_finish_reason(choice.get("finish_reason", "stop")),
            "stop_sequence": None,
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        }

        return anthropic_response

    def _map_finish_reason(self, finish_reason: str) -> str:
        """Map Azure finish_reason to Anthropic stop_reason."""
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "function_call": "tool_use",
            "content_filter": "end_turn",
        }
        return mapping.get(finish_reason, "end_turn")

    def get_status(self) -> dict[str, Any]:
        """Get current status of passthrough handler."""
        return {
            "passthrough_enabled": self.passthrough_enabled,
            "fallback_enabled": self.fallback_enabled,
            "anthropic_configured": bool(self.anthropic_api_key),
            "azure_configured": bool(self.azure_openai_key and self.azure_openai_endpoint),
            "failure_count": self.anthropic_failure_count,
            "using_fallback": self.should_use_fallback(),
            "last_failure_time": self.last_failure_time,
            "max_retries": self.max_retries,
            "fallback_after_failures": self.fallback_after_failures,
        }
