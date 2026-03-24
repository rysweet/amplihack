"""Unified async LLM routing layer.

Detects the active launcher (claude vs copilot) and dispatches to the
appropriate SDK. Callers receive a plain ``str`` and are never aware of
which backend ran.

Public API:
    completion: async entry-point for all LLM calls
    SDK_AVAILABLE: True when at least one SDK is importable at import time
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SDK availability guards (set once at import time)
# ---------------------------------------------------------------------------

try:
    import claude_agent_sdk as _claude_sdk  # type: ignore[import-unresolved]  # noqa: F401

    _CLAUDE_SDK_OK = True
except ImportError:
    _CLAUDE_SDK_OK = False

try:
    from copilot import (  # type: ignore[import-unresolved]
        CopilotClient as _CopilotClient,  # noqa: F401
    )

    _COPILOT_SDK_OK = True
except ImportError:
    _COPILOT_SDK_OK = False

SDK_AVAILABLE: bool = _CLAUDE_SDK_OK or _COPILOT_SDK_OK

# ---------------------------------------------------------------------------
# LauncherDetector import (module-level so it can be patched in tests)
# ---------------------------------------------------------------------------

try:
    from amplihack.context.adaptive.detector import LauncherDetector
except ImportError:
    LauncherDetector = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Module-level launcher cache
# ---------------------------------------------------------------------------

#: Cached launcher string. ``None`` means not yet detected.
#: The launcher is an environment-level property that does not change
#: during process lifetime, so we detect it once and reuse the result.
_detector_cache: str | None = None

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

#: Allowlisted display names for message roles (REQ-INPUT-2).
#: Unknown roles are NOT passed through verbatim to prevent prompt injection.
ROLE_LABELS: dict[str, str] = {
    "system": "System",
    "user": "User",
    "assistant": "Assistant",
}

#: Valid model name pattern (REQ-INPUT-3) — prevents log injection.
_MODEL_PATTERN = re.compile(r"^[a-zA-Z0-9/_:.-]{1,100}$")

#: Maximum permitted max_tokens value (REQ-INPUT-4).
_MAX_TOKENS_CAP = 100_000

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """Route an LLM request to the active SDK backend.

    Never raises — returns ``""`` on any failure (fail-open contract).

    Args:
        model: Model identifier (validated against ``_MODEL_PATTERN``).
        messages: List of ``{"role": ..., "content": ...}`` dicts.
        temperature: Sampling temperature (default 0.7).
        max_tokens: Token budget; capped at 100,000.

    Returns:
        Plain string response, or ``""`` on any failure.
    """
    try:
        # --- Input validation (REQ-INPUT-1, REQ-INPUT-3, REQ-INPUT-4) ----
        if not _validate_inputs(model, messages):
            return ""

        # Cap max_tokens
        if max_tokens is not None:
            max_tokens = min(max_tokens, _MAX_TOKENS_CAP)

        # --- Launcher detection (cached) ---------------------------------
        try:
            launcher = _get_launcher()
        except Exception:
            launcher = "claude"

        logger.debug(
            "completion: launcher=%s messages=%d",
            launcher,
            len(messages),
        )

        # --- 5-branch routing --------------------------------------------
        # Branch 1: copilot launcher + copilot SDK
        if launcher == "copilot" and _COPILOT_SDK_OK:
            return await _query_copilot(model, messages, temperature, max_tokens)

        # Branch 2: claude launcher + claude SDK
        if launcher == "claude" and _CLAUDE_SDK_OK:
            return await _query_claude(model, messages, temperature, max_tokens)

        # Branch 3: copilot launcher but no copilot SDK, try claude SDK
        if _CLAUDE_SDK_OK:
            return await _query_claude(model, messages, temperature, max_tokens)

        # Branch 4: fallback to copilot SDK
        if _COPILOT_SDK_OK:
            return await _query_copilot(model, messages, temperature, max_tokens)

        # Branch 5: no SDK available
        logger.error("completion: no SDK available for model=%r — returning empty string", model)
        return ""

    except Exception as exc:
        # REQ-DATA-2: log only type, never str(exc) which may contain prompt text
        logger.warning("completion failed: %s", type(exc).__name__)
        return ""


async def strict_completion(
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """Like :func:`completion` but raises on empty result instead of silently failing.

    Use this when an empty LLM response is a hard error — graders, sessions,
    and other correctness-sensitive callers should prefer this over the
    fail-open :func:`completion` variant.

    Args:
        model: Model identifier (validated against ``_MODEL_PATTERN``).
        messages: List of ``{"role": ..., "content": ...}`` dicts.
        temperature: Sampling temperature (default 0.7).
        max_tokens: Token budget; capped at 100,000.

    Returns:
        Plain string response (guaranteed non-empty).

    Raises:
        RuntimeError: When the underlying ``completion()`` call returns ``""``,
            indicating either an infrastructure failure or an SDK not being
            available for the requested model.
    """
    result = await completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if result == "":
        raise RuntimeError(
            f"LLM completion returned empty — check SDK availability for model={model!r}"
        )
    return result


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------


def _validate_inputs(model: object, messages: object) -> bool:
    """Return True iff inputs are valid for routing.

    Checks:
    - model matches _MODEL_PATTERN
    - messages is a non-empty list of dicts with 'role' and 'content'
    """
    # Model validation
    if not isinstance(model, str) or not _MODEL_PATTERN.match(model):
        return False

    # Messages validation
    if not isinstance(messages, list) or not messages:
        return False

    for msg in messages:
        if not isinstance(msg, dict):
            return False
        if "role" not in msg or "content" not in msg:
            return False
        # REQ-INPUT-1: Reject unknown roles — allowlist prevents prompt injection via
        # malformed role values from propagating to SDK dispatch or prompt formatting.
        if msg["role"] not in ROLE_LABELS:
            return False

    return True


# ---------------------------------------------------------------------------
# Launcher detection
# ---------------------------------------------------------------------------


def _get_launcher() -> str:
    """Return the cached launcher type, detecting it on first call.

    The launcher is stable for the lifetime of a process (it reflects the
    environment in which the process was started).  Caching avoids repeated
    filesystem/env-var probing on every ``completion()`` call.
    """
    global _detector_cache
    if _detector_cache is None:
        _detector_cache = _detect_launcher()
    return _detector_cache


def _detect_launcher(project_root: Path | None = None) -> str:
    """Return the active launcher type ('claude', 'copilot', or 'unknown').

    Delegates to LauncherDetector(project_root).detect() and falls back to
    'claude' on any exception. Only the launcher string is stored, never
    response content (REQ-DATA-3).

    Args:
        project_root: Project root for launcher context file lookup.
                      Defaults to ``Path.cwd()``.

    Returns:
        Launcher type string; falls back to ``"claude"`` on any error.
    """
    root = project_root if project_root is not None else Path.cwd()

    try:
        if LauncherDetector is None:
            return "claude"
        detector = LauncherDetector(root)
        result = detector.detect()
        return str(result)
    except Exception as exc:
        # Log exception TYPE only — not str(exc) which may contain path or env details.
        # A warning makes detector failures visible without leaking sensitive context.
        logger.warning("_detect_launcher fallback to 'claude': %s", type(exc).__name__)
        return "claude"


# ---------------------------------------------------------------------------
# SDK query helpers
# ---------------------------------------------------------------------------


async def _query_claude(
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int | None,
) -> str:
    """Call claude_agent_sdk and return the response as a plain string."""
    import claude_agent_sdk  # type: ignore[import-unresolved]

    prompt = _messages_to_prompt(messages)
    kwargs: dict = {"model": model, "prompt": prompt, "temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    result = await claude_agent_sdk.query(**kwargs)
    if isinstance(result, str):
        return result
    # Handle SDK response objects — check for expected .text attribute first.
    # If the response lacks .text the SDK contract has changed; log a warning
    # so shape mismatches are visible rather than silently returning "".
    text = getattr(result, "text", None)
    if text is None:
        logger.warning(
            "_query_claude: unexpected SDK response shape %s — falling back to str()",
            type(result).__name__,
        )
        text = str(result) or ""
    return text


async def _query_copilot(
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int | None,
) -> str:
    """Call CopilotClient and return the response as a plain string."""
    import asyncio

    from copilot import CopilotClient, PermissionHandler  # type: ignore[import-unresolved]

    system_msg = ""
    user_msg = _messages_to_prompt(messages)
    for m in messages:
        if m.get("role") == "system":
            system_msg = str(m.get("content", ""))
            break

    client = CopilotClient()
    await client.start()

    try:
        response_parts: list[str] = []
        done = asyncio.Event()

        session_opts: dict = {
            "model": model,
            "on_permission_request": PermissionHandler.approve_all,
        }
        if system_msg:
            session_opts["system_message"] = {"content": system_msg}

        session = await client.create_session(session_opts)

        def on_event(event):
            etype = event.type.value if hasattr(event.type, "value") else str(event.type)
            if etype == "assistant.message":
                content = getattr(event.data, "content", "") if hasattr(event, "data") else ""
                if content:
                    response_parts.append(content)
            elif etype == "session.idle":
                done.set()

        session.on(on_event)
        await session.send({"prompt": user_msg})

        try:
            await asyncio.wait_for(done.wait(), timeout=120)
        except TimeoutError:
            logger.warning("_query_copilot: session timed out after 120s")

        await session.destroy()
        return "".join(response_parts)
    finally:
        await client.stop()


# ---------------------------------------------------------------------------
# Prompt formatting helper
# ---------------------------------------------------------------------------


def _messages_to_prompt(messages: list[dict]) -> str:
    """Format a messages list into a plain text prompt string.

    Uses ``ROLE_LABELS`` allowlist for display names to prevent prompt
    injection via malformed role values (REQ-INPUT-2).

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts.

    Returns:
        Newline-separated labelled prompt string.
    """
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "")
        content = str(msg.get("content", ""))
        label = ROLE_LABELS.get(role, "Message")
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


__all__ = ["completion", "strict_completion", "SDK_AVAILABLE"]
