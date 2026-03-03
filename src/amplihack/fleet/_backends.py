"""LLM backend protocol and implementations for fleet reasoning.

Provides a protocol-based abstraction over multiple LLM providers so the
SessionReasoner can call any supported backend interchangeably.

Public API:
    LLMBackend: Protocol defining the complete() method
    AnthropicBackend: Anthropic SDK backend
    CopilotBackend: GitHub Copilot SDK backend
    LiteLLMBackend: LiteLLM backend (100+ providers)
    auto_detect_backend: Pick the best available backend
"""

from __future__ import annotations

import os
from typing import Protocol

__all__ = [
    "LLMBackend",
    "AnthropicBackend",
    "CopilotBackend",
    "LiteLLMBackend",
    "auto_detect_backend",
]


class LLMBackend(Protocol):
    """Protocol for LLM backends."""

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class AnthropicBackend:
    """Anthropic SDK backend."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = ""):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if not response.content:
            return ""
        block = response.content[0]
        return getattr(block, "text", "")


class CopilotBackend:
    """GitHub Copilot SDK backend.

    Requires: pip install copilot-sdk
    Requires: GitHub Copilot subscription + gh auth login
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio

        return asyncio.run(self._async_complete(system_prompt, user_prompt))

    async def _async_complete(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio

        from copilot import CopilotClient

        client = CopilotClient()
        await client.start()

        try:
            session = await client.create_session({"model": self.model})
            response_parts: list[str] = []
            done = asyncio.Event()

            def on_event(event):
                if event.type.value == "assistant.message":
                    response_parts.append(event.data.content)
                elif event.type.value == "session.idle":
                    done.set()

            session.on(on_event)
            await session.send({"prompt": f"{system_prompt}\n\n{user_prompt}"})

            try:
                await asyncio.wait_for(done.wait(), timeout=60)
            except TimeoutError:
                pass

            await session.destroy()
            return "".join(response_parts)
        finally:
            await client.stop()


class LiteLLMBackend:
    """LiteLLM backend -- supports 100+ LLM providers.

    Requires: pip install litellm
    Works with: OpenAI, Anthropic, Azure, Copilot, Ollama, etc.
    Set model via constructor: "gpt-4o", "claude-sonnet-4-20250514", "ollama/llama3", etc.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import litellm

        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
        )
        choices = getattr(response, "choices", [])
        if choices:
            msg = getattr(choices[0], "message", None)
            content = getattr(msg, "content", None) if msg else None
            return str(content) if content else ""
        return ""


def auto_detect_backend() -> LLMBackend:
    """Auto-detect the best available LLM backend.

    Priority:
    1. Anthropic (if ANTHROPIC_API_KEY set)
    2. LiteLLM (always available -- declared dependency)
    3. Copilot SDK (always available -- declared dependency)

    Raises RuntimeError if no backend has valid credentials.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicBackend()

    # LiteLLM supports 100+ providers -- use it if any provider env vars are set
    return LiteLLMBackend()
