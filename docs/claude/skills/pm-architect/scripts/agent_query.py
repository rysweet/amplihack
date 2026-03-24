#!/usr/bin/env python3
"""Dual-SDK query abstraction for PM Architect scripts.

Auto-detects the active agent runtime (Claude Code or GitHub Copilot CLI) and
routes LLM queries to the appropriate SDK. Falls back to the other supported
SDK when the preferred SDK is unavailable, but surfaces query failures
explicitly.

Detection priority:
  1. AMPLIHACK_AGENT_BINARY env var (set by CLI launcher)
  2. LauncherDetector (reads .claude/runtime/launcher_context.json)
  3. Default to whichever SDK is importable

Explicit failure: if neither SDK is available, or if the SDK query fails,
query_agent() raises AgentQueryError.
"""

import asyncio
import os
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

# --- Public API ---------------------------------------------------------------

SDK_AVAILABLE = _CLAUDE_SDK_OK or _COPILOT_SDK_OK

QUERY_TIMEOUT = int(os.environ.get("PM_ARCHITECT_QUERY_TIMEOUT", "120"))

__all__ = ["AgentQueryError", "query_agent", "SDK_AVAILABLE", "detect_runtime"]


class AgentQueryError(RuntimeError):
    """Raised when PM Architect cannot query any supported agent SDK."""


def detect_runtime() -> str:
    """Detect which agent runtime is active.

    Returns:
        "copilot", "claude", or "unknown"
    """
    # 1. Explicit env var (set by amplihack CLI launcher)
    agent_binary = os.environ.get("AMPLIHACK_AGENT_BINARY", "").strip().lower()
    if agent_binary in ("copilot", "claude"):
        return agent_binary

    # 2. LauncherDetector (reads runtime context file)
    try:
        from amplihack.context.adaptive.detector import LauncherDetector

        return LauncherDetector(Path.cwd()).detect()
    except Exception:
        pass

    # 3. Fallback: infer from available SDKs
    if _COPILOT_SDK_OK and not _CLAUDE_SDK_OK:
        return "copilot"
    if _CLAUDE_SDK_OK:
        return "claude"
    return "unknown"


async def query_agent(prompt: str, project_root: Path) -> str:
    """Send a prompt to the detected SDK and return the text response.

    Auto-selects Claude Agent SDK or Copilot SDK based on runtime detection.
    Falls back to the other SDK if the preferred one is unavailable.

    Args:
        prompt: The full prompt to send
        project_root: Project root directory (used as cwd for SDK)

    Returns:
        Response text from the selected SDK.

    Raises:
        AgentQueryError: If no supported SDK is available or the query fails.
    """
    runtime = detect_runtime()
    if not (_CLAUDE_SDK_OK or _COPILOT_SDK_OK):
        raise AgentQueryError(
            "No supported agent SDK is available. Install claude-agent-sdk or github-copilot-sdk."
        )

    try:
        if runtime == "copilot" and _COPILOT_SDK_OK:
            return await _query_copilot(prompt, project_root)
        if _CLAUDE_SDK_OK:
            return await _query_claude(prompt, project_root)
        if _COPILOT_SDK_OK:
            return await _query_copilot(prompt, project_root)
        raise AgentQueryError(
            f"No supported SDK implementation is available for runtime '{runtime}'."
        )
    except TimeoutError as error:
        raise AgentQueryError(
            f"{runtime} SDK query timed out after {QUERY_TIMEOUT}s. "
            "Increase PM_ARCHITECT_QUERY_TIMEOUT if needed."
        ) from error
    except Exception as e:
        hint = ""
        err_str = str(e).lower()
        if "api" in err_str or "key" in err_str or "auth" in err_str:
            hint = " Check your API key (ANTHROPIC_API_KEY for Claude)."
        elif "connect" in err_str or "network" in err_str or "timeout" in err_str:
            hint = " Check network connectivity and retry."
        raise AgentQueryError(f"Error querying {runtime} SDK: {e}{hint}") from e


async def _query_claude(prompt: str, project_root: Path) -> str:
    """Query via Claude Agent SDK."""
    options = ClaudeAgentOptions(
        cwd=str(project_root),
        permission_mode="bypassPermissions",
    )
    response_parts: list[str] = []

    async with asyncio.timeout(QUERY_TIMEOUT):
        async for message in _claude_query(prompt=prompt, options=options):
            text = getattr(message, "text", None)
            if text:
                response_parts.append(text)
                continue
            content = getattr(message, "content", None)
            if content is None:
                continue
            if isinstance(content, list):
                for block in content:
                    block_text = getattr(block, "text", None)
                    if isinstance(block_text, str):
                        response_parts.append(block_text)
            elif isinstance(content, str):
                response_parts.append(content)

    return "".join(response_parts)


async def _query_copilot(prompt: str, project_root: Path) -> str:
    """Query via GitHub Copilot SDK.

    CopilotClient communicates over JSON-RPC with the copilot binary.
    """
    client = CopilotClient()
    try:
        await client.start()
        session = await client.create_session(SessionConfig())
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
