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
    from copilot.session import PermissionHandler  # type: ignore[import-not-found]

    _COPILOT_SDK_OK = True
except ImportError:
    pass

# --- Launcher detection -------------------------------------------------------

_detector_cache: str | None = None

QUERY_TIMEOUT = int(os.environ.get("AMPLIHACK_LLM_TIMEOUT", "60"))

SDK_AVAILABLE = _CLAUDE_SDK_OK or _COPILOT_SDK_OK

# Env vars that explicitly select an LLM provider, in priority order.
# An explicit env override always beats file-based launcher detection so
# that embedded callers (e.g. Simard's OODA daemon, which is a Rust binary
# and never goes through `amplihack copilot` and therefore never writes a
# launcher_context.json) can pin the SDK without faking a launcher context.
#
# Recognized values: "copilot", "claude". Anything else is ignored.
_PROVIDER_ENV_VARS = (
    "AMPLIHACK_LLM_PROVIDER",
    "SIMARD_LLM_PROVIDER",
)

__all__ = ["completion", "SDK_AVAILABLE"]


def _provider_from_env() -> str | None:
    """Return an explicit provider override from env, or None.

    Recognized values are normalized: any of {claude, copilot}. Other
    values (e.g. Simard-specific aliases like "rustyclawd") are mapped
    to copilot when the GitHub Copilot stack is intended, otherwise
    ignored. Unrecognized values fall through to file-based detection.
    """
    for var in _PROVIDER_ENV_VARS:
        raw = os.environ.get(var)
        if not raw:
            continue
        v = raw.strip().lower()
        if v in ("copilot", "github-copilot", "gh-copilot", "rustyclawd"):
            return "copilot"
        if v in ("claude", "anthropic", "claude-code"):
            return "claude"
        # Unrecognized — keep looking, then fall through to file detection.
    return None


def _detect_launcher(project_root: Path) -> str:
    """Detect launcher type, cached per process.

    Order:
      1. Explicit env var override (AMPLIHACK_LLM_PROVIDER /
         SIMARD_LLM_PROVIDER) — wins unconditionally.
      2. File-based detection via LauncherDetector (reads
         <project_root>/.claude/runtime/launcher_context.json).
      3. Fall back to "claude" if both are absent.
    """
    global _detector_cache
    if _detector_cache is not None:
        return _detector_cache

    override = _provider_from_env()
    if override is not None:
        _detector_cache = override
        return override

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
    explicit_override = _provider_from_env()

    # Build a single prompt from the messages list
    prompt = _messages_to_prompt(messages)

    try:
        if explicit_override == "copilot":
            if not _COPILOT_SDK_OK:
                print(
                    "WARNING: AMPLIHACK_LLM_PROVIDER/SIMARD_LLM_PROVIDER=copilot but "
                    "the copilot SDK is not importable. Refusing to silently fall back "
                    "to Claude.",
                    file=sys.stderr,
                )
                return ""
            return await _query_copilot(prompt, project_root)
        if explicit_override == "claude":
            if not _CLAUDE_SDK_OK:
                print(
                    "WARNING: AMPLIHACK_LLM_PROVIDER/SIMARD_LLM_PROVIDER=claude but "
                    "the claude SDK is not importable. Refusing to silently fall back "
                    "to Copilot.",
                    file=sys.stderr,
                )
                return ""
            return await _query_claude(prompt, project_root)

        # No explicit override — use detected launcher with cross-SDK fallback.
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
    """Query via GitHub Copilot SDK (copilot >= 0.1.0)."""
    async with CopilotClient() as client:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            working_directory=str(project_root),
        )
        try:
            async with asyncio.timeout(QUERY_TIMEOUT):
                event = await session.send_and_wait(
                    prompt,
                    timeout=float(QUERY_TIMEOUT),
                )
            if event is None:
                return ""
            data = getattr(event, "data", None)
            if data is None:
                return ""
            content = getattr(data, "content", None)
            return content or ""
        finally:
            try:
                await session.destroy()
            except Exception:
                pass
