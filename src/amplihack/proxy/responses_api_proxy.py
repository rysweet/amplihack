"""
Azure OpenAI Responses API Proxy

A translation proxy that converts between OpenAI Chat API format and Azure Responses API format.
This allows claude-code-proxy (which expects standard OpenAI format) to work with Azure Responses API.
"""

import json
import threading
import time
from typing import Any

import requests
from flask import Flask, jsonify, request

from .sanitizing_logger import get_sanitizing_logger

# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)


class ResponsesAPIProxy:
    """Proxy server that translates between OpenAI Chat API and Azure Responses API formats."""

    def __init__(self, azure_base_url: str, azure_api_key: str, listen_port: int = 8082):
        self.azure_base_url = azure_base_url
        self.azure_api_key = azure_api_key
        self.listen_port = listen_port
        self.app = Flask(__name__)
        self.server_thread = None

        # Set up Flask routes
        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes for proxying requests."""

        @self.app.route("/v1/chat/completions", methods=["POST"])
        def chat_completions():
            """Handle OpenAI chat completions and convert to Responses API."""
            try:
                # Get incoming OpenAI-format request
                openai_request = request.json
                logger.debug(f"Incoming OpenAI request: {json.dumps(openai_request, indent=2)}")

                # Transform to Responses API format
                responses_request = self._transform_to_responses_api(openai_request)
                logger.debug(
                    f"Transformed to Responses API: {json.dumps(responses_request, indent=2)}"
                )

                # Send to Azure Responses API
                headers = {
                    "Content-Type": "application/json",
                    "api-key": self.azure_api_key,
                }

                response = requests.post(
                    self.azure_base_url, json=responses_request, headers=headers, timeout=300
                )

                logger.debug(f"Azure response status: {response.status_code}")
                logger.debug(f"Azure response: {response.text}")

                if response.status_code == 200:
                    # Transform response back to OpenAI format
                    azure_response = response.json()
                    openai_response = self._transform_to_openai_format(azure_response)
                    return jsonify(openai_response)
                # Return error in OpenAI format
                return jsonify(
                    {
                        "error": {
                            "message": f"Azure API error: {response.text}",
                            "type": "azure_api_error",
                            "code": response.status_code,
                        }
                    }
                ), response.status_code

            except Exception as e:
                logger.error(f"Proxy error: {e}")
                return jsonify(
                    {
                        "error": {
                            "message": f"Proxy error: {e!s}",
                            "type": "proxy_error",
                            "code": "internal_error",
                        }
                    }
                ), 500

        @self.app.route("/v1/messages/count_tokens", methods=["POST"])
        def count_tokens():
            """Handle token counting requests."""
            # For now, return a simple estimate
            request_data = request.json
            messages = request_data.get("messages", [])

            # Simple token estimate: ~4 chars per token
            total_chars = sum(len(str(msg)) for msg in messages)
            estimated_tokens = max(1, total_chars // 4)

            return jsonify({"token_count": estimated_tokens})

        @self.app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "healthy", "proxy_type": "responses_api"})

    def _transform_to_responses_api(self, openai_request: dict[str, Any]) -> dict[str, Any]:
        """Transform OpenAI Chat API request to Azure Responses API format."""
        responses_request = {
            "model": openai_request.get("model"),
            "input": openai_request.get("messages", []),  # messages -> input
        }

        # Map other parameters as needed
        # Get configured token limits from environment for Azure Responses API
        import os

        min_tokens_limit = int(os.environ.get("MIN_TOKENS_LIMIT", "4096"))
        max_tokens_limit = int(os.environ.get("MAX_TOKENS_LIMIT", "512000"))

        # Ensure proper token limits for Azure Responses API
        max_tokens_value = openai_request.get("max_tokens", 1)
        if max_tokens_value and max_tokens_value > 1:
            # Ensure we use at least the minimum configured limit
            max_tokens_value = max(min_tokens_limit, max_tokens_value)
            # Cap at maximum configured limit
            max_tokens_value = min(max_tokens_limit, max_tokens_value)
        else:
            # Default to maximum limit for Azure Responses API models
            max_tokens_value = max_tokens_limit

        responses_request["max_tokens"] = max_tokens_value
        # Always use temperature=1.0 for Azure Responses API models
        responses_request["temperature"] = 1.0
        if "stream" in openai_request:
            responses_request["stream"] = openai_request["stream"]

        # Add tool definitions if present - Azure Responses API format
        if openai_request.get("tools"):
            azure_tools = []
            for tool in openai_request["tools"]:
                # OpenAI tools already have the nested function structure
                # Convert OpenAI format to Azure Responses API format
                if isinstance(tool, dict) and tool.get("type") == "function":
                    function = tool.get("function", {})
                    azure_tool = {
                        "type": "function",
                        "function": {
                            "name": function.get("name", ""),
                            "description": function.get("description", ""),
                            "parameters": function.get(
                                "parameters", {}
                            ),  # OpenAI uses "parameters", not "input_schema"
                        },
                    }
                    azure_tools.append(azure_tool)

            responses_request["tools"] = azure_tools

            # Handle tool_choice if present
            if openai_request.get("tool_choice"):
                tool_choice = openai_request["tool_choice"]
                if isinstance(tool_choice, dict):
                    if tool_choice.get("type") == "function":
                        function_name = tool_choice.get("function", {}).get("name")
                        if function_name:
                            responses_request["tool_choice"] = {
                                "type": "function",
                                "function": {"name": function_name},
                            }
                elif tool_choice == "auto":
                    responses_request["tool_choice"] = "auto"
                elif tool_choice == "none":
                    responses_request["tool_choice"] = "none"
                elif tool_choice == "required":
                    responses_request["tool_choice"] = "required"

        return responses_request

    def _transform_to_openai_format(self, azure_response: dict[str, Any]) -> dict[str, Any]:
        """Transform Azure Responses API response to OpenAI Chat API format."""
        # This is a simplified transformation - may need adjustment based on actual response format
        openai_response = {
            "id": azure_response.get("id", "resp-" + str(int(time.time()))),
            "object": "chat.completion",
            "created": azure_response.get("created", int(time.time())),
            "model": azure_response.get("model", "gpt-5-codex"),
            "choices": [],
        }

        # Transform choices
        if "choices" in azure_response:
            for choice in azure_response["choices"]:
                message = {
                    "role": "assistant",
                    "content": choice.get("text", choice.get("message", {}).get("content", "")),
                }

                # Handle tool calls in the response
                tool_calls = None
                if "tool_calls" in choice:
                    tool_calls = choice["tool_calls"]
                elif "message" in choice and "tool_calls" in choice["message"]:
                    tool_calls = choice["message"]["tool_calls"]

                if tool_calls:
                    openai_tool_calls = []
                    for tool_call in tool_calls:
                        # Azure Responses API format -> OpenAI format
                        if isinstance(tool_call, dict):
                            openai_tool_call = {
                                "id": tool_call.get("id", f"call_{int(time.time())}"),
                                "type": "function",
                                "function": {
                                    "name": tool_call.get("function", {}).get("name", ""),
                                    "arguments": tool_call.get("function", {}).get(
                                        "arguments", "{}"
                                    ),
                                },
                            }
                            openai_tool_calls.append(openai_tool_call)

                    if openai_tool_calls:
                        message["tool_calls"] = openai_tool_calls
                        # If there are tool calls, content might be null in OpenAI format
                        if not message["content"]:
                            message["content"] = None

                # Map finish_reason
                finish_reason = choice.get("finish_reason", "stop")
                if finish_reason == "tool_calls" or (tool_calls and finish_reason == "stop"):
                    finish_reason = "tool_calls"
                elif finish_reason == "length":
                    finish_reason = "length"
                else:
                    finish_reason = "stop"

                openai_choice = {
                    "index": choice.get("index", 0),
                    "message": message,
                    "finish_reason": finish_reason,
                }
                openai_response["choices"].append(openai_choice)

        # Add usage info if available
        if "usage" in azure_response:
            openai_response["usage"] = azure_response["usage"]

        return openai_response

    def start(self) -> bool:
        """Start the proxy server in a background thread."""
        try:

            def run_server():
                self.app.run(
                    host="127.0.0.1",
                    port=self.listen_port,
                    debug=False,
                    use_reloader=False,
                    threaded=True,
                )

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            # Wait for server to start
            time.sleep(2)

            # Test if server is responding
            try:
                response = requests.get(f"http://127.0.0.1:{self.listen_port}/health", timeout=5)
                return response.status_code == 200
            except Exception:
                return False

        except Exception as e:
            logger.error(f"Failed to start proxy server: {e}")
            return False

    def stop(self):
        """Stop the proxy server."""
        # Flask doesn't have a clean shutdown mechanism in this setup
        # The thread will be cleaned up when the main process exits


def create_responses_api_proxy(config: dict[str, str], port: int = 8082) -> ResponsesAPIProxy:
    """Create and configure a Responses API proxy instance."""
    azure_base_url = config.get("OPENAI_BASE_URL")
    azure_api_key = config.get("AZURE_OPENAI_KEY") or config.get("OPENAI_API_KEY")

    if not azure_base_url or not azure_api_key:
        raise ValueError(
            "Missing required Azure configuration: OPENAI_BASE_URL and AZURE_OPENAI_KEY"
        )

    return ResponsesAPIProxy(azure_base_url, azure_api_key, port)
