#!/usr/bin/env python3
"""SDK abstraction for power-steering LLM queries.

Auto-detects the active launcher (Claude Code or GitHub Copilot CLI) and
routes LLM queries to the appropriate SDK. Both SDKs support stateless
prompt→response queries used by power-steering analysis.

Detection uses the existing LauncherDetector which reads
.claude/runtime/launcher_context.json written at session start.

Fail-open: if neither SDK is available, query_llm() returns "".
"""

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


def _detect_launcher(project_root: Path) -> str:
    """Detect launcher type, cached per process."""
    global _detector_cache
    if _detector_cache is not None:
        return _detector_cache
    try:
        sys.path.insert(0, str(Path(__file__).parents[3] / "src" / "amplihack"))
        from amplihack.context.adaptive.detector import LauncherDetector

        result = LauncherDetector(project_root).detect()
    except Exception:
        result = "claude"
    _detector_cache = result
    return result


# Timeout per query (within the 60s parallel budget)
QUERY_TIMEOUT = int(os.environ.get("PSC_QUERY_TIMEOUT", "25"))

# Public API
SDK_AVAILABLE = _CLAUDE_SDK_OK or _COPILOT_SDK_OK
__all__ = ["query_llm", "SDK_AVAILABLE"]


async def query_llm(prompt: str, project_root: Path) -> str:
    """Send a prompt to the detected SDK and return the text response.

    Auto-selects Claude Agent SDK or Copilot SDK based on launcher detection.
    Falls back to Claude if detected launcher's SDK is unavailable.

    Args:
        prompt: The full prompt to send
        project_root: Project root directory (used as cwd for SDK)

    Returns:
        Response text, or "" on any failure (fail-open)
    """
    launcher = _detect_launcher(project_root)

    # Route to the correct backend
    if launcher == "copilot" and _COPILOT_SDK_OK:
        return await _query_copilot(prompt, project_root)
    if _CLAUDE_SDK_OK:
        return await _query_claude(prompt, project_root)
    if _COPILOT_SDK_OK:
        return await _query_copilot(prompt, project_root)

    # Neither SDK available
    return ""


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
    """Query via GitHub Copilot SDK.

    CopilotClient methods are async coroutines. Create a session,
    send_and_wait for the response, then extract text from the event.
    """
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
