"""LLM backend protocol and implementations for fleet reasoning.

Provides a protocol-based abstraction over multiple LLM providers so the
SessionReasoner can call any supported backend interchangeably.

Public API:
    LLMBackend: Protocol defining the complete() method
    AnthropicBackend: Anthropic SDK backend
    CopilotBackend: GitHub Copilot SDK backend
    auto_detect_backend: Pick the best available backend
"""

from __future__ import annotations

import os
from typing import Protocol

from amplihack.fleet._constants import DEFAULT_LLM_MAX_TOKENS, SUBPROCESS_TIMEOUT_SECONDS

__all__ = [
    "LLMBackend",
    "AnthropicBackend",
    "CopilotBackend",
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

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        # Anthropic API requires streaming when max_tokens is high enough
        # that the request could exceed 10 minutes.
        with client.messages.stream(
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
        import asyncio

        # WARNING: asyncio.run() will crash if called from async context. See PATTERNS.md.
        return asyncio.run(self._async_complete(system_prompt, user_prompt))

    async def _async_complete(self, system_prompt: str, user_prompt: str) -> str:
        import asyncio

        from copilot import CopilotClient, PermissionHandler

        client = CopilotClient()
        await client.start()

        try:
            response_parts: list[str] = []
            done = asyncio.Event()

            session = await client.create_session({
                "model": self.model,
                "system_message": {"content": system_prompt},
                "on_permission_request": PermissionHandler.approve_all,
            })

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
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "Copilot session timed out after %ds", SUBPROCESS_TIMEOUT_SECONDS
                )

            await session.destroy()
            return "".join(response_parts)
        finally:
            await client.stop()


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
