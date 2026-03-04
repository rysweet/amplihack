"""
Lock handler module for the stop hook.

Handles lock flag detection, continuation prompts, and lock mode counters.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hook_processor import HookProcessor

# Default continuation prompt when no custom prompt is provided
DEFAULT_CONTINUATION_PROMPT = (
    "we must keep pursuing the user's objective and must not stop the turn - "
    "look for any additional TODOs, next steps, or unfinished work and pursue it "
    "diligently in as many parallel tasks as you can"
)


def check_lock(hook: "HookProcessor", lock_flag: Path, continuation_prompt_file: Path) -> dict | None:
    """Check if lock is active and return block decision if so.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        lock_flag: Path to the lock flag file
        continuation_prompt_file: Path to the custom continuation prompt file

    Returns:
        Block decision dict if lock is active, None otherwise
    """
    try:
        lock_exists = lock_flag.exists()
    except (PermissionError, OSError) as e:
        hook.log(f"Cannot access lock file: {e}", "WARNING")
        hook.log("=== STOP HOOK ENDED (fail-safe: approve) ===")
        return {"decision": "approve"}

    if not lock_exists:
        return None

    # Lock is active - block stop and continue working
    hook.log("Lock is active - blocking stop to continue working")
    hook.save_metric("lock_blocks", 1)

    # Get session ID for per-session tracking
    session_id = _get_current_session_id(hook)

    # Increment lock mode counter
    increment_lock_counter(hook, session_id)

    # Read custom continuation prompt or use default
    continuation_prompt = read_continuation_prompt(hook, continuation_prompt_file)

    hook.log("=== STOP HOOK ENDED (decision: block - lock active) ===")
    return {
        "decision": "block",
        "reason": continuation_prompt,
    }


def read_continuation_prompt(hook: "HookProcessor", continuation_prompt_file: Path) -> str:
    """Read custom continuation prompt from file or return default.

    Args:
        hook: The HookProcessor instance (for logging)
        continuation_prompt_file: Path to the custom continuation prompt file

    Returns:
        str: Custom prompt content or DEFAULT_CONTINUATION_PROMPT
    """
    if not continuation_prompt_file.exists():
        hook.log("No custom continuation prompt file - using default")
        return DEFAULT_CONTINUATION_PROMPT

    try:
        content = continuation_prompt_file.read_text(encoding="utf-8").strip()

        if not content:
            hook.log("Custom continuation prompt file is empty - using default")
            return DEFAULT_CONTINUATION_PROMPT

        content_len = len(content)

        if content_len > 1000:
            hook.log(
                f"Custom prompt too long ({content_len} chars) - using default",
                "WARNING",
            )
            return DEFAULT_CONTINUATION_PROMPT

        if content_len > 500:
            hook.log(
                f"Custom prompt is long ({content_len} chars) - consider shortening for clarity",
                "WARNING",
            )

        hook.log(f"Using custom continuation prompt ({content_len} chars)")
        return content

    except (PermissionError, OSError, UnicodeDecodeError) as e:
        hook.log(f"Error reading custom prompt: {e} - using default", "WARNING")
        return DEFAULT_CONTINUATION_PROMPT


def increment_lock_counter(hook: "HookProcessor", session_id: str) -> int:
    """Increment lock mode invocation counter for session.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        session_id: Session identifier

    Returns:
        New count value (for logging/metrics)
    """
    try:
        counter_file = (
            hook.project_root
            / ".claude"
            / "runtime"
            / "locks"
            / session_id
            / "lock_invocations.txt"
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)

        current_count = 0
        if counter_file.exists():
            try:
                current_count = int(counter_file.read_text().strip())
            except (ValueError, OSError):
                current_count = 0

        new_count = current_count + 1
        counter_file.write_text(str(new_count))

        hook.log(f"Lock mode invocation count: {new_count}")
        return new_count

    except (OSError, ValueError) as e:
        hook.log(f"Failed to update lock counter: {e}", "WARNING")
        return 0


def _get_current_session_id(hook: "HookProcessor") -> str:
    """Detect current session ID from environment or logs.

    Args:
        hook: The HookProcessor instance (for logging/metrics)

    Returns:
        Session ID string
    """
    import os
    from datetime import datetime

    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    logs_dir = hook.project_root / ".claude" / "runtime" / "logs"
    if logs_dir.exists():
        try:
            sessions = [p for p in logs_dir.iterdir() if p.is_dir()]
            sessions = sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)
            if sessions:
                return sessions[0].name
        except (OSError, PermissionError) as e:
            hook.log(
                f"[CAUSE] Cannot access logs directory to detect session ID. [IMPACT] Will use timestamp-based ID instead. [ACTION] Check directory permissions. Error: {e}",
                "WARNING",
            )
            hook.save_metric("session_id_detection_errors", 1)

    return datetime.now().strftime("%Y%m%d_%H%M%S")
