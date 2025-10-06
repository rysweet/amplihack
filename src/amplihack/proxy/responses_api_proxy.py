"""
Azure OpenAI Responses API Proxy

A translation proxy that converts between OpenAI Chat API format and Azure Responses API format.
This allows claude-code-proxy (which expects standard OpenAI format) to work with Azure Responses API.
"""

import json
import logging
import threading
import time
from typing import Any, Dict

import requests
from flask import Flask, jsonify, request

logger = logging.getLogger(__name__)


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
                else:
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
                            "message": f"Proxy error: {str(e)}",
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

    def _transform_to_responses_api(self, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI Chat API request to Azure Responses API format."""
        responses_request = {
            "model": openai_request.get("model"),
            "input": openai_request.get("messages", []),  # messages -> input
        }

        # Map other parameters as needed
        if "max_tokens" in openai_request:
            responses_request["max_tokens"] = openai_request["max_tokens"]
        if "temperature" in openai_request:
            responses_request["temperature"] = openai_request["temperature"]
        if "stream" in openai_request:
            responses_request["stream"] = openai_request["stream"]

        return responses_request

    def _transform_to_openai_format(self, azure_response: Dict[str, Any]) -> Dict[str, Any]:
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
                openai_choice = {
                    "index": choice.get("index", 0),
                    "message": {
                        "role": "assistant",
                        "content": choice.get("text", choice.get("message", {}).get("content", "")),
                    },
                    "finish_reason": choice.get("finish_reason", "stop"),
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
        pass


def create_responses_api_proxy(config: Dict[str, str], port: int = 8082) -> ResponsesAPIProxy:
    """Create and configure a Responses API proxy instance."""
    azure_base_url = config.get("OPENAI_BASE_URL")
    azure_api_key = config.get("AZURE_OPENAI_KEY") or config.get("OPENAI_API_KEY")

    if not azure_base_url or not azure_api_key:
        raise ValueError(
            "Missing required Azure configuration: OPENAI_BASE_URL and AZURE_OPENAI_KEY"
        )

    return ResponsesAPIProxy(azure_base_url, azure_api_key, port)
