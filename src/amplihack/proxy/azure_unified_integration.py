"""
Azure Unified Integration for LiteLLM - Performance Optimized
Provides unified routing for both Azure Chat and Responses APIs through LiteLLM.
This eliminates the dual routing architecture by handling all requests through LiteLLM.

Performance Optimizations:
- Cached model routing decisions with O(1) lookup
- Session connection pooling and reuse
- Configuration caching with LRU cache
- Pre-computed endpoints to avoid string formatting
- Memory-efficient request transformations
- Performance metrics collection
"""

import hashlib
import json
import ssl
import time
from functools import lru_cache
from typing import Any

import aiohttp  # type: ignore[import-untyped]
import certifi  # type: ignore[import-untyped]
from litellm import Router  # type: ignore[import-untyped]

from .sanitizing_logger import get_sanitizing_logger

# Use sanitizing logger to prevent credential exposure (Issue #1997)
logger = get_sanitizing_logger(__name__)

# Placeholder API key for LiteLLM model configurations
# The actual key is injected at runtime from environment variables
_PLACEHOLDER_API_KEY = "PLACEHOLDER"  # pragma: allowlist secret

# Performance optimization: Global caches
_MODEL_ROUTING_CACHE = {}
_SESSION_CACHE = {}
_CONFIG_CACHE = {}
_TRANSFORM_CACHE = {}

# Performance constants
RESPONSES_API_MODELS = {
    "o3-mini",
    "o3-small",
    "o3-medium",
    "o3-large",
    "o4-mini",
    "o4-small",
    "o4-medium",
    "o4-large",
    "gpt-5-code",
    "gpt-5-codex",
}


class AzureUnifiedProvider:
    """
    Performance-optimized unified Azure provider for Chat and Responses APIs.

    This class eliminates the bypass logic by providing consistent request/response
    transformation for both API types within the LiteLLM framework, with optimizations
    for high-throughput scenarios.
    """

    def __init__(self, api_key: str, base_url: str, api_version: str):
        self.api_key = api_key
        self.base_url = base_url
        self.chat_api_version = api_version  # For Chat API
        self.responses_api_version = (
            "2025-04-01-preview"  # Responses API requires different version
        )

        # Pre-compute endpoints for performance (avoid string formatting on each request)
        self.chat_endpoint = f"{base_url}/openai/deployments/gpt-5/chat/completions?api-version={self.chat_api_version}"
        self.responses_endpoint = (
            f"{base_url}/openai/responses?api-version={self.responses_api_version}"
        )

        # Performance metrics for monitoring
        self._request_count = 0
        self._cache_hits = 0
        self._session_reuse_count = 0

    async def get_cached_session(self) -> aiohttp.ClientSession:
        """Get cached aiohttp session with optimized connection pooling."""
        cache_key = f"{self.base_url}:{self.api_key[:8]}"  # Use base_url + key prefix as cache key

        # Check if cached session exists and is still open
        if cache_key in _SESSION_CACHE:
            session = _SESSION_CACHE[cache_key]
            if not session.closed:
                self._session_reuse_count += 1
                return session
            # Clean up closed session
            del _SESSION_CACHE[cache_key]

        # Create new optimized session with enhanced connection pooling
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=200,  # Increased total connection pool size
            limit_per_host=50,  # Increased per-host connection limit
            keepalive_timeout=60,  # Longer keepalive for better reuse
            enable_cleanup_closed=True,
            ttl_dns_cache=300,  # DNS cache for 5 minutes
            use_dns_cache=True,
            force_close=False,  # Keep connections alive
        )

        timeout = aiohttp.ClientTimeout(total=120, connect=10)

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
            "User-Agent": "AmplihackUnifiedAzureProvider/2.0-Optimized",
            "Connection": "keep-alive",  # Explicit keep-alive header
        }

        session = aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers)

        # Cache the session for future reuse
        _SESSION_CACHE[cache_key] = session
        return session

    @lru_cache(maxsize=512)
    def should_use_responses_api(self, model: str) -> bool:
        """
        Determine which Azure API to use based on model type.
        Optimized with LRU cache and set-based lookups for O(1) performance.

        Args:
            model: Model name (e.g., "gpt-5", "o3-mini", etc.)

        Returns:
            True if should use Responses API, False for Chat API
        """
        # Check cache first for maximum performance
        if model in _MODEL_ROUTING_CACHE:
            self._cache_hits += 1
            return _MODEL_ROUTING_CACHE[model]

        # Fast set lookup for exact matches (O(1) vs O(n) list lookup)
        if model in RESPONSES_API_MODELS or (
            model.startswith(("o3", "o4")) and not model.startswith("gpt")
        ):
            result = True
        else:
            # Everything else uses Chat API (including base gpt-5, gpt-5-chat, claude models)
            result = False

        # Cache the result for future requests
        _MODEL_ROUTING_CACHE[model] = result
        return result

    def get_cached_chat_transform(
        self, request_hash: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Get cached Chat API transformation or compute and cache it."""
        if request_hash in _TRANSFORM_CACHE:
            return _TRANSFORM_CACHE[request_hash].copy()

        chat_request = {
            "model": request.get("model", "gpt-5"),
            "messages": request.get("messages", []),
            "temperature": 1.0,  # Azure Chat API requires temperature=1.0
        }

        # Handle max_tokens -> max_completion_tokens
        if "max_tokens" in request:
            chat_request["max_completion_tokens"] = request["max_tokens"]
        elif "max_completion_tokens" in request:
            chat_request["max_completion_tokens"] = request["max_completion_tokens"]
        else:
            chat_request["max_completion_tokens"] = 128000  # Azure max limit

        # Handle streaming
        if request.get("stream"):
            chat_request["stream"] = True

        # Handle tools (Chat API uses nested function structure)
        if request.get("tools"):
            chat_request["tools"] = request["tools"]

        if request.get("tool_choice"):
            chat_request["tool_choice"] = request["tool_choice"]

        # Cache the transformation
        _TRANSFORM_CACHE[request_hash] = chat_request.copy()
        return chat_request

    def transform_request_to_chat_api(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request to Azure Chat API format with caching optimization.

        Args:
            request: LiteLLM request

        Returns:
            Azure Chat API formatted request
        """
        # Create a hash of the request for caching (exclude dynamic fields)
        request_key = json.dumps(
            {
                k: v
                for k, v in request.items()
                if k not in ["stream"]  # Exclude dynamic fields from cache key
            },
            sort_keys=True,
        )
        request_hash = hashlib.md5(request_key.encode()).hexdigest()[:16]

        return self.get_cached_chat_transform(request_hash, request)

    def get_cached_responses_transform(
        self, request_hash: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Get cached Responses API transformation or compute and cache it."""
        if request_hash in _TRANSFORM_CACHE:
            return _TRANSFORM_CACHE[request_hash].copy()

        responses_request = {
            "model": request.get("model", "gpt-5"),
            "input": request.get("messages", []),  # messages -> input
            "temperature": 1.0,  # Always 1.0 for Responses API
        }

        # Handle max_tokens -> max_output_tokens
        if "max_tokens" in request:
            responses_request["max_output_tokens"] = request["max_tokens"]
        elif "max_output_tokens" in request:
            responses_request["max_output_tokens"] = request["max_output_tokens"]
        else:
            responses_request["max_output_tokens"] = 512000  # Default high limit

        # Handle streaming
        if request.get("stream"):
            responses_request["stream"] = True

        # Handle tools (Responses API has different schema requirements)
        if request.get("tools"):
            # Transform tools for Responses API format
            responses_tools = []
            for tool in request["tools"]:
                if tool.get("type") == "function" and "function" in tool:
                    func_def = tool["function"]
                    # Responses API expects flatter structure
                    responses_tool = {
                        "type": "function",
                        "name": func_def.get("name", ""),
                        "description": func_def.get("description", ""),
                        "parameters": func_def.get("parameters", {}),
                    }
                    responses_tools.append(responses_tool)

            if responses_tools:
                responses_request["tools"] = responses_tools

        if request.get("tool_choice"):
            responses_request["tool_choice"] = request["tool_choice"]

        # Cache the transformation
        _TRANSFORM_CACHE[request_hash] = responses_request.copy()
        return responses_request

    def transform_request_to_responses_api(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request to Azure Responses API format with caching optimization.

        Args:
            request: LiteLLM request

        Returns:
            Azure Responses API formatted request
        """
        # Create a hash of the request for caching (exclude dynamic fields)
        request_key = json.dumps(
            {
                k: v
                for k, v in request.items()
                if k not in ["stream"]  # Exclude dynamic fields from cache key
            },
            sort_keys=True,
        )
        request_hash = hashlib.md5(request_key.encode()).hexdigest()[:16]

        return self.get_cached_responses_transform(request_hash, request)

    def transform_chat_api_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Transform Azure Chat API response to standard OpenAI format.
        Chat API already returns standard OpenAI format, so minimal processing.
        """
        return response

    def transform_responses_api_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        Transform Azure Responses API response to standard OpenAI format.
        Optimized for memory efficiency and speed.
        """
        # Pre-allocate response structure for better memory efficiency
        openai_response = {
            "id": response.get("id", f"resp-{int(time.time())}"),
            "object": "chat.completion",
            "created": response.get("created_at", int(time.time())),
            "model": response.get("model", "gpt-5"),
            "choices": [],
        }

        # Transform output to choices with optimized processing
        output_items = response.get("output", [])
        if output_items:
            choices = []
            for i, item in enumerate(output_items):
                choice = {
                    "index": i,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }

                # Handle different output types efficiently
                item_type = item.get("type")
                if item_type == "text":
                    choice["message"]["content"] = item.get("text", "")
                elif item_type == "tool_call" and "function" in item:
                    # Transform tool calls to OpenAI format
                    tool_call = {
                        "id": item.get("id", f"call_{int(time.time())}"),
                        "type": "function",
                        "function": {
                            "name": item["function"].get("name", ""),
                            "arguments": json.dumps(item["function"].get("arguments", {})),
                        },
                    }
                    choice["message"]["tool_calls"] = [tool_call]
                    choice["message"]["content"] = None
                    choice["finish_reason"] = "tool_calls"

                choices.append(choice)
            openai_response["choices"] = choices
        else:
            # No output, create empty response
            openai_response["choices"] = [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                    "finish_reason": "stop",
                }
            ]

        # Add usage information if available
        if "usage" in response:
            usage = response["usage"]
            openai_response["usage"] = {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

        return openai_response

    async def make_request(self, request: dict[str, Any], stream: bool = False) -> dict[str, Any]:
        """
        Make unified request to appropriate Azure API with performance optimizations.

        Args:
            request: LiteLLM request
            stream: Whether to stream response

        Returns:
            Transformed response in standard OpenAI format
        """
        self._request_count += 1

        model = request.get("model", "gpt-5")
        use_responses_api = self.should_use_responses_api(model)

        logger.debug(
            f"🔀 Azure Unified: {model} -> {'Responses API' if use_responses_api else 'Chat API'}"
        )

        # Use cached transformations for better performance
        if use_responses_api:
            azure_request = self.transform_request_to_responses_api(request)
            endpoint = self.responses_endpoint
        else:
            azure_request = self.transform_request_to_chat_api(request)
            endpoint = self.chat_endpoint

        # Use cached session for optimal performance
        session = await self.get_cached_session()

        try:
            # Direct session usage (no context manager needed for cached session)
            async with session.post(endpoint, json=azure_request) as response:
                if response.status == 200:
                    azure_response = await response.json()

                    # Transform response based on API type
                    if use_responses_api:
                        return self.transform_responses_api_response(azure_response)
                    return self.transform_chat_api_response(azure_response)
                error_text = await response.text()
                logger.error(f"❌ Azure API error {response.status}: {error_text}")

                # Return error in OpenAI format
                return {
                    "error": {
                        "message": f"Azure API error: {error_text}",
                        "type": "azure_api_error",
                        "code": response.status,
                    }
                }

        except TimeoutError:
            logger.error("❌ Azure API timeout")
            return {
                "error": {"message": "Request timeout", "type": "timeout_error", "code": "timeout"}
            }
        except Exception as e:
            logger.error(f"❌ Azure API request failed: {e}")
            return {"error": {"message": str(e), "type": "request_error", "code": "request_failed"}}

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for monitoring."""
        return {
            "request_count": self._request_count,
            "cache_hits": self._cache_hits,
            "session_reuse_count": self._session_reuse_count,
            "cache_hit_ratio": self._cache_hits / max(self._request_count, 1),
            "active_sessions": len(_SESSION_CACHE),
            "routing_cache_size": len(_MODEL_ROUTING_CACHE),
            "transform_cache_size": len(_TRANSFORM_CACHE),
        }


@lru_cache(maxsize=16)
def _get_cached_model_list_template(
    base_url: str,
    api_version: str,
    big_model: str = "gpt-5-codex",
    middle_model: str = "gpt-5-codex",
    small_model: str = "gpt-5-codex",
) -> list[dict[str, Any]]:
    """Get cached model list template for router creation."""

    # Determine if this is a Responses API endpoint
    is_responses_api = "/openai/responses" in base_url

    if is_responses_api:
        # Responses API models (uses different endpoint and API version)
        responses_api_version = "2025-04-01-preview"  # Use the user's specified API version

        # For Azure Responses API, we need to keep the full endpoint path
        # First remove any query parameters (api-version will be added by LiteLLM)
        clean_base_url = base_url.split("?")[0] if "?" in base_url else base_url
        # Keep the /openai/responses path for Responses API
        # clean_base_url = clean_base_url.replace("/openai/responses", "")  # DON'T strip this for Responses API

        # Create model list with Claude model names mapped to user's deployment names
        # All Claude models route to the BIG_MODEL deployment for Responses API
        model_list = [
            # Claude model mappings - all use BIG_MODEL deployment
            {
                "model_name": "claude-3-5-sonnet-20241022",
                "litellm_params": {
                    "model": f"azure/{big_model}",  # LiteLLM routes based on model format
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": clean_base_url,  # Base URL only - LiteLLM adds endpoint path
                    "api_version": responses_api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "litellm_params": {
                    "model": f"azure/{big_model}",  # LiteLLM routes based on model format
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": clean_base_url,  # Base URL only - LiteLLM adds endpoint path
                    "api_version": responses_api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            {
                "model_name": "claude-3-5-haiku-20241022",
                "litellm_params": {
                    "model": f"azure/{small_model}",  # Use small model deployment
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": clean_base_url,  # Base URL only - LiteLLM adds endpoint path
                    "api_version": responses_api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            # Direct deployment name (whatever user configured)
            {
                "model_name": big_model,  # User's actual deployment name
                "litellm_params": {
                    "model": f"azure/{big_model}",
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": clean_base_url,  # Base URL only - LiteLLM adds endpoint path
                    "api_version": responses_api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
        ]
    else:
        # Chat API models (standard Azure OpenAI)
        model_list = [
            {
                "model_name": "claude-3-5-sonnet-20241022",
                "litellm_params": {
                    "model": f"azure/{big_model}",  # Use user's deployment name
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": f"{base_url}/openai/deployments/{big_model}",
                    "api_version": api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            {
                "model_name": "claude-sonnet-4-5-20250929",
                "litellm_params": {
                    "model": f"azure/{big_model}",  # Use user's deployment name
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": f"{base_url}/openai/deployments/{big_model}",
                    "api_version": api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            {
                "model_name": "claude-3-5-haiku-20241022",
                "litellm_params": {
                    "model": f"azure/{small_model}",  # Use small model deployment
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": f"{base_url}/openai/deployments/{small_model}",
                    "api_version": api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
            # Direct deployment name entries
            {
                "model_name": big_model,  # User's actual deployment name
                "litellm_params": {
                    "model": f"azure/{big_model}",
                    "api_key": _PLACEHOLDER_API_KEY,
                    "api_base": f"{base_url}/openai/deployments/{big_model}",
                    "api_version": api_version,
                    "drop_params": True,
                    "temperature": 1.0,
                    "max_completion_tokens": 128000,
                },
            },
        ]

    return model_list


def create_unified_litellm_router(
    api_key: str,
    base_url: str,
    api_version: str = "2025-01-01-preview",
    big_model: str = "gpt-5-codex",
    middle_model: str = "gpt-5-codex",
    small_model: str = "gpt-5-codex",
) -> Router:
    """
    Create LiteLLM router with unified Azure configuration.
    Optimized with configuration caching for faster initialization.

    Args:
        api_key: Azure API key
        base_url: Azure base URL
        api_version: Azure API version
        big_model: Azure deployment name for large models (BIG_MODEL)
        middle_model: Azure deployment name for medium models (MIDDLE_MODEL)
        small_model: Azure deployment name for small models (SMALL_MODEL)

    Returns:
        Configured LiteLLM Router
    """
    # Get cached model list template with deployment names
    model_list_template = _get_cached_model_list_template(
        base_url, api_version, big_model, middle_model, small_model
    )

    # Replace template placeholders with actual API key
    model_list = []
    for model_config in model_list_template:
        model_copy = {
            "model_name": model_config["model_name"],
            "litellm_params": model_config["litellm_params"].copy(),
        }
        model_copy["litellm_params"]["api_key"] = api_key
        model_list.append(model_copy)

    # Create router with optimized configuration
    try:
        router = Router(model_list=model_list)
        logger.info(
            f"✅ Optimized Azure LiteLLM router created with {len(model_list)} model mappings"
        )
        logger.debug(f"📊 Router supports: {[m['model_name'] for m in model_list]}")
        return router
    except Exception as e:
        logger.error(f"❌ Failed to create unified Azure router: {e}")
        raise


@lru_cache(maxsize=32)
def validate_azure_unified_config_cached(
    config_hash: str, base_url: str, has_api_key: bool
) -> bool:
    """
    Validate configuration for unified Azure integration with caching.

    Args:
        config_hash: Hash of configuration for cache key
        base_url: Azure base URL
        has_api_key: Whether API key is present

    Returns:
        True if configuration is valid
    """
    # Fast validation with early returns
    if not has_api_key:
        logger.error("❌ Missing required config: OPENAI_API_KEY")
        return False

    if not base_url:
        logger.error("❌ Missing required config: OPENAI_BASE_URL")
        return False

    # Optimized URL validation
    if not base_url.startswith("https://"):
        logger.error("❌ Base URL must use HTTPS")
        return False

    if "cognitiveservices.azure.com" not in base_url:
        logger.error("❌ Invalid Azure Cognitive Services URL")
        return False

    logger.debug("✅ Azure unified configuration validated")
    return True


def validate_azure_unified_config(config: dict[str, str]) -> bool:
    """
    Legacy interface for configuration validation with caching optimization.

    Args:
        config: Configuration dictionary

    Returns:
        True if configuration is valid
    """
    api_key = config.get("OPENAI_API_KEY", "")
    base_url = config.get("OPENAI_BASE_URL", "")

    # Create cache key from configuration
    config_str = f"{base_url}:{bool(api_key)}"
    config_hash = hashlib.md5(config_str.encode()).hexdigest()[:16]

    return validate_azure_unified_config_cached(config_hash, base_url, bool(api_key))


async def cleanup_cached_sessions() -> None:
    """Clean up closed sessions from cache to prevent memory leaks."""
    closed_sessions = []
    for cache_key, session in _SESSION_CACHE.items():
        if session.closed:
            closed_sessions.append(cache_key)

    for cache_key in closed_sessions:
        del _SESSION_CACHE[cache_key]

    if closed_sessions:
        logger.debug(f"🧹 Cleaned up {len(closed_sessions)} closed sessions from cache")


def get_global_performance_metrics() -> dict[str, Any]:
    """Get global performance metrics across all providers."""
    return {
        "total_cached_sessions": len(_SESSION_CACHE),
        "routing_cache_entries": len(_MODEL_ROUTING_CACHE),
        "transform_cache_entries": len(_TRANSFORM_CACHE),
        "config_cache_entries": len(_CONFIG_CACHE),
    }
