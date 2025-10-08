"""GitHub Copilot API client implementation."""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin


class GitHubCopilotClient:
    """Client for GitHub Copilot Language Model API."""

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        """Initialize GitHub Copilot client.

        Args:
            token: GitHub access token with Copilot access
            base_url: Base URL for GitHub API
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """Ensure HTTP session is initialized."""
        if not self.session:
            try:
                import aiohttp  # type: ignore

                self.session = aiohttp.ClientSession(
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "amplihack-copilot-client",
                    },
                    timeout=aiohttp.ClientTimeout(total=300),
                )
            except ImportError:
                raise RuntimeError(
                    "aiohttp required for GitHub Copilot client. Install with: pip install aiohttp"
                )

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "copilot-gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], Any]:
        """Create chat completion using GitHub Copilot.

        Args:
            messages: List of message objects
            model: Model name (will be mapped to GitHub Copilot model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            Response dictionary or async generator for streaming.
        """
        await self._ensure_session()

        # Prepare request data
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens is not None:
            data["max_tokens"] = max_tokens

        # Add any additional parameters
        data.update(kwargs)

        # GitHub Copilot endpoint
        url = urljoin(self.base_url, "/copilot/chat/completions")

        if stream:
            return self._stream_completion(url, data)
        return await self._create_completion(url, data)

    async def _create_completion(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create non-streaming completion.

        Args:
            url: API endpoint URL
            data: Request data

        Returns:
            Response dictionary.
        """
        try:
            assert self.session is not None  # Ensured by _ensure_session()
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                error_text = await response.text()
                raise RuntimeError(f"GitHub Copilot API error {response.status}: {error_text}")

        except Exception as e:
            if "aiohttp" in str(type(e)):
                raise RuntimeError(f"Network error: {e}")
            raise

    async def _stream_completion(self, url: str, data: Dict[str, Any]):
        """Create streaming completion.

        Args:
            url: API endpoint URL
            data: Request data

        Yields:
            Streaming response chunks.
        """
        try:
            assert self.session is not None  # Ensured by _ensure_session()
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"GitHub Copilot API error {response.status}: {error_text}")

                async for line in response.content:
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                yield chunk
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            if "aiohttp" in str(type(e)):
                raise RuntimeError(f"Network error: {e}")
            raise

    async def list_models(self) -> Dict[str, Any]:
        """List available models.

        Returns:
            Models list in OpenAI format.
        """
        # GitHub Copilot doesn't have a models endpoint, so return static list
        return {
            "object": "list",
            "data": [
                {
                    "id": "copilot-gpt-4",
                    "object": "model",
                    "created": 1677649963,
                    "owned_by": "github",
                },
                {
                    "id": "copilot-gpt-3.5-turbo",
                    "object": "model",
                    "created": 1677649963,
                    "owned_by": "github",
                },
            ],
        }

    async def get_usage(self) -> Dict[str, Any]:
        """Get Copilot usage information.

        Returns:
            Usage information if available.
        """
        await self._ensure_session()
        assert self.session is not None  # Ensured by _ensure_session()

        try:
            url = urljoin(self.base_url, "/copilot/billing")
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                # Return empty usage if not available
                return {"usage": {}}

        except Exception:
            return {"usage": {}}

    def sync_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "copilot-gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[Dict[str, Any], Any]:
        """Synchronous wrapper for chat completion.

        Args:
            messages: List of message objects
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters

        Returns:
            Response dictionary or generator for streaming.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if stream:
            # For streaming, we need to handle it differently
            # Return a generator function that can be called to start streaming
            def _stream_generator():
                async def _stream_wrapper():
                    async with self:
                        stream_result = await self.chat_completion(
                            messages, model, temperature, max_tokens, stream, **kwargs
                        )
                        async for chunk in stream_result:  # type: ignore[misc]
                            yield chunk

                return _stream_wrapper()

            return _stream_generator

        # For non-streaming, run in event loop
        async def _completion_wrapper():
            async with self:
                return await self.chat_completion(
                    messages, model, temperature, max_tokens, stream, **kwargs
                )

        return loop.run_until_complete(_completion_wrapper())

    def transform_openai_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI request format to GitHub Copilot format.

        Args:
            request_data: OpenAI-format request data

        Returns:
            GitHub Copilot-format request data.
        """
        # GitHub Copilot API is largely compatible with OpenAI format
        github_request = request_data.copy()

        # Map OpenAI models to GitHub Copilot models
        model_mappings = {
            "gpt-4": "copilot-gpt-4",
            "gpt-4-turbo": "copilot-gpt-4",
            "gpt-4o": "copilot-gpt-4",
            "gpt-4o-mini": "copilot-gpt-3.5-turbo",
            "gpt-3.5-turbo": "copilot-gpt-3.5-turbo",
        }

        original_model = github_request.get("model", "gpt-4")
        github_request["model"] = model_mappings.get(original_model, "copilot-gpt-4")

        return github_request

    def transform_github_response(
        self, response: Dict[str, Any], original_model: str
    ) -> Dict[str, Any]:
        """Transform GitHub Copilot response to OpenAI format.

        Args:
            response: GitHub Copilot response
            original_model: Original OpenAI model name requested

        Returns:
            OpenAI-format response.
        """
        openai_response = response.copy()

        # Replace GitHub model name with original OpenAI model name
        if "model" in openai_response:
            openai_response["model"] = original_model

        # Ensure response has required OpenAI fields
        if "object" not in openai_response:
            openai_response["object"] = "chat.completion"

        return openai_response
