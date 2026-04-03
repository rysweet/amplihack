"""SDK-routed LLM client for amplihack.

Auto-detects the active launcher (Claude Code or GitHub Copilot CLI) and
routes LLM completion requests to the appropriate SDK.

Follows the same pattern as power_steering_sdk.py but exposes a
completion() interface matching the eval/fleet calling convention.

Fail-open: if neither SDK is available, completion() returns "".
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# --- Claude Agent SDK ---------------------------------------------------------

_CLAUDE_SDK_OK = False
try:
    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore[import-not-found]
    from claude_agent_sdk import query as _claude_query  # type: ignore[import-not-found]

    _CLAUDE_SDK_OK = True
except ImportError:
    pass

# --- GitHub Copilot SDK -------------------------------------------------------

_COPILOT_SDK_OK = False
try:
    from copilot import CopilotClient  # type: ignore[import-not-found]
    from copilot.types import MessageOptions, SessionConfig  # type: ignore[import-not-found]

    _COPILOT_SDK_OK = True
except ImportError:
    pass

# --- Launcher detection -------------------------------------------------------

_detector_cache: str | None = None

QUERY_TIMEOUT = int(os.environ.get("AMPLIHACK_LLM_TIMEOUT", "60"))

SDK_AVAILABLE = _CLAUDE_SDK_OK or _COPILOT_SDK_OK

__all__ = ["completion", "SDK_AVAILABLE"]


def _detect_launcher(project_root: Path) -> str:
    """Detect launcher type, cached per process."""
    global _detector_cache
    if _detector_cache is not None:
        return _detector_cache
    try:
        from amplihack.context.adaptive.detector import LauncherDetector

        result = LauncherDetector(project_root).detect()
    except Exception:
        result = "claude"
    _detector_cache = result
    return result


def _get_project_root() -> Path:
    """Get the project root from environment or cwd."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


async def completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Send a completion request via the detected SDK.

    Auto-selects Claude Agent SDK or Copilot SDK based on launcher detection.
    Falls back across SDKs if the preferred one is unavailable.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        model: Model name (informational — actual model depends on SDK session).
        temperature: Sampling temperature (passed as hint in prompt if relevant).
        max_tokens: Max tokens (passed as hint in prompt if relevant).

    Returns:
        Response text, or "" on any failure (fail-open).
    """
    project_root = _get_project_root()
    launcher = _detect_launcher(project_root)

    # Build a single prompt from the messages list
    prompt = _messages_to_prompt(messages)

    try:
        if launcher == "copilot" and _COPILOT_SDK_OK:
            return await _query_copilot(prompt, project_root)
        if _CLAUDE_SDK_OK:
            return await _query_claude(prompt, project_root)
        if _COPILOT_SDK_OK:
            return await _query_copilot(prompt, project_root)
    except Exception as e:
        print(f"WARNING: LLM completion failed: {e}", file=sys.stderr)

    return ""


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    """Convert a messages list to a single prompt string.

    Preserves system/user/assistant role structure in the prompt text
    so the SDK can interpret the conversation.
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"<system>\n{content}\n</system>")
        elif role == "assistant":
            parts.append(f"<assistant>\n{content}\n</assistant>")
        else:
            parts.append(content)
    return "\n\n".join(parts)


async def _query_claude(prompt: str, project_root: Path) -> str:
    """Query via Claude Agent SDK."""
    options = ClaudeAgentOptions(cwd=str(project_root))
    response_parts: list[str] = []

    async with asyncio.timeout(QUERY_TIMEOUT):
        async for message in _claude_query(prompt=prompt, options=options):
            content = getattr(message, "content", None)
            if content is None:
                continue
            if isinstance(content, list):
                for block in content:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        response_parts.append(text)
            elif isinstance(content, str):
                response_parts.append(content)

    return "".join(response_parts)


async def _query_copilot(prompt: str, project_root: Path) -> str:
    """Query via GitHub Copilot SDK."""
    client = CopilotClient()
    try:
        await client.start()
        session = await client.create_session(SessionConfig())
        async with asyncio.timeout(QUERY_TIMEOUT):
            event = await session.send_and_wait(
                MessageOptions(prompt=prompt),
                timeout=float(QUERY_TIMEOUT),
            )
        if event and hasattr(event, "data") and event.data:
            return event.data.content or ""
        return ""
    finally:
        try:
            await client.stop()
        except Exception:
            pass
