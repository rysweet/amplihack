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

import asyncio
import logging
import os
from typing import Protocol

from amplihack.fleet._constants import DEFAULT_LLM_MAX_TOKENS, SUBPROCESS_TIMEOUT_SECONDS

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

    def __init__(
        self,
        model: str = "claude-opus-4-6",
        api_key: str = "",
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.max_tokens = max_tokens
        # Client is created once and reused across complete() calls.
        # anthropic.Anthropic manages an internal connection pool; creating
        # a new instance on every call discards that pool and pays the
        # connection-setup cost each time.
        import anthropic  # type: ignore[import-unresolved]

        self._client = anthropic.Anthropic(api_key=self.api_key)
        # Immediately clear the plain-text copy — the SDK holds its own reference.
        # This prevents accidental exposure via repr(), dataclass serialisation, or
        # generic object-dumping utilities that walk instance __dict__.
        self.api_key = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # Anthropic API requires streaming when max_tokens is high enough
        # that the request could exceed 10 minutes.
        with self._client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            return stream.get_final_text()


class CopilotBackend:
    """GitHub Copilot SDK backend.

    Requires: pip install github-copilot-sdk
    Requires: GitHub Copilot subscription + gh auth login
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        # REQ-BRIDGE-1: Guard against nested asyncio.run() which deadlocks.
        # Raise clearly instead of silently hanging or crashing with a cryptic error.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # No loop running — safe to call asyncio.run()
        else:
            raise RuntimeError(
                "CopilotBackend.complete() cannot be called from an async context. "
                "Use await _async_complete() directly instead."
            )
        return asyncio.run(self._async_complete(system_prompt, user_prompt))

    async def _async_complete(self, system_prompt: str, user_prompt: str) -> str:
        from copilot import CopilotClient, PermissionHandler  # type: ignore[import-unresolved]

        client = CopilotClient()
        await client.start()

        try:
            response_parts: list[str] = []
            done = asyncio.Event()

            session = await client.create_session(
                {
                    "model": self.model,
                    "system_message": {"content": system_prompt},
                    "on_permission_request": PermissionHandler.approve_all,
                }
            )

            def on_event(event):
                etype = event.type.value if hasattr(event.type, "value") else str(event.type)
                if etype == "assistant.message":
                    content = getattr(event.data, "content", "") if hasattr(event, "data") else ""
                    if content:
                        response_parts.append(content)
                elif etype == "session.idle":
                    done.set()

            session.on(on_event)
            await session.send({"prompt": user_prompt})

            try:
                await asyncio.wait_for(done.wait(), timeout=SUBPROCESS_TIMEOUT_SECONDS)
            except TimeoutError:
                # Use asyncio.TimeoutError explicitly — avoids platform-alias
                # ambiguity with the builtin TimeoutError on Python < 3.11.
                logging.getLogger(__name__).warning(
                    "Copilot session timed out after %ds", SUBPROCESS_TIMEOUT_SECONDS
                )

            await session.destroy()
            return "".join(response_parts)
        finally:
            await client.stop()


class LiteLLMBackend:
    """LiteLLM backend -- supports 100+ LLM providers.

    Requires: pip install litellm
    Works with: OpenAI, Anthropic, Azure, Copilot, Ollama, etc.
    Set model via constructor: "gpt-4o", "claude-opus-4-6", "ollama/llama3", etc.
    """

    def __init__(self, model: str = "gpt-4o", max_tokens: int = DEFAULT_LLM_MAX_TOKENS):
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        from amplihack.llm.client import completion

        # Nested-loop guard (REQ-BRIDGE-1)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # No loop running — safe to use asyncio.run()
        else:
            raise RuntimeError(
                "LiteLLMBackend.complete() cannot be called from an async context. "
                "Use the async completion() function directly instead."
            )

        return asyncio.run(
            completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
            )
        )


def auto_detect_backend() -> LLMBackend:
    """Auto-detect the best available LLM backend.

    Priority:
    1. Anthropic (if ANTHROPIC_API_KEY set)
    2. Copilot (fallback -- uses GitHub Copilot subscription)

    Always returns a backend; falls back to CopilotBackend.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicBackend()

    # Fall back to GitHub Copilot SDK when running under copilot (no Anthropic key)
    return CopilotBackend()
