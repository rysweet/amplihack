#!/usr/bin/env python3
"""
dev_intent_router.py — Injects intent-routing guidance into every prompt.

Instead of regex-based classification (which required 366 lines and still
found 5+ bugs per audit round), this module injects a short classification
prompt that lets the LLM itself classify intent with full natural language
understanding.

The LLM already processes every message — making it classify intent is
essentially free (happens during existing thinking) and infinitely more
accurate than any regex pattern.

Toggle during a session:
    Create  .claude/runtime/locks/.auto_dev_active  → enabled (default)
    Delete  .claude/runtime/locks/.auto_dev_active  → disabled
    Or use /amplihack:auto-dev and /amplihack:no-auto-dev commands.

Legacy env var still respected: export AMPLIHACK_AUTO_DEV=false
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Routing prompt (injected as additionalContext)
# ---------------------------------------------------------------------------

_ROUTING_PROMPT = """\
<system-reminder source="auto-intent-router">
Before responding, classify this prompt into one of these categories and act accordingly:

  DEV (build, fix, write, test, verify, deploy, document, refactor, configure, review code, add feature)
    → Say "[auto-routed] DEV → launching dev-orchestrator" then Invoke Skill(skill="dev-orchestrator"). Do not answer inline.

  INVESTIGATE (analyze, understand, explore, research, audit, trace, map out, what's broken, what's failing)
    → Say "[auto-routed] INVESTIGATE → launching dev-orchestrator" then Invoke Skill(skill="dev-orchestrator"). Do not answer inline. It will use INVESTIGATION_WORKFLOW.

  HYBRID (investigate/understand THEN implement/fix/build, or run command THEN fix — two phases in one prompt)
    → Say "[auto-routed] HYBRID → launching dev-orchestrator" then Invoke Skill(skill="dev-orchestrator"). Do not answer inline. It will create parallel workstreams.

  Q&A (what is, how does, explain, describe, compare, define — knowledge questions)
    → Answer directly and concisely. No workflow invocation needed.

  OPS (run git, show disk, run tests, run linter, check logs, delete temp files, restart service — admin/shell tasks)
    → Execute directly. No workflow invocation needed.

  SKIP (bypass phrases: "just answer", "skip workflow", "skip orchestration", "without workflow")
    → Respect the bypass. Do not invoke any workflow.

Key: "make sure it works" = DEV. "write docs" = DEV. "review this PR" = DEV.
     "run tests" = OPS. "run tests and fix failures" = HYBRID. "what's broken?" = INVESTIGATE.
     "tests are failing" without a clear action request = ask if they want you to investigate/fix.
     "investigate X then fix Y" = HYBRID. "what is OAuth?" = Q&A.
</system-reminder>"""

_WELCOME_BANNER = (
    "NOTE: amplihack auto-routing is active. Development tasks automatically "
    "use the smart orchestrator. "
    "Disable: /amplihack:no-auto-dev  |  "
    'One-time bypass: include "just answer" in your message.'
)

# Minimum prompt length to inject routing (saves ~400 tokens on trivial turns)
_MIN_PROMPT_LENGTH = 10


# ---------------------------------------------------------------------------
# Semaphore file helpers
# ---------------------------------------------------------------------------


def _get_semaphore_path() -> Path:
    """Return the path to the auto-dev semaphore file."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir) / ".claude" / "runtime" / "locks" / ".auto_dev_active"
    return Path.cwd() / ".claude" / "runtime" / "locks" / ".auto_dev_active"


def _get_banner_flag_path() -> Path:
    """Return the path to the per-session welcome-banner-shown flag."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    base = Path(project_dir) if project_dir else Path.cwd()
    return base / ".claude" / "runtime" / "locks" / ".auto_dev_banner_shown"


def is_auto_dev_enabled() -> bool:
    """Check whether auto-routing is enabled.

    Priority order:
    1. Semaphore file absent  → disabled (explicit opt-out via command)
    2. Semaphore file present → enabled
    3. If no semaphore has ever been created, check legacy env var
       AMPLIHACK_AUTO_DEV (default: enabled).
    """
    sem = _get_semaphore_path()

    # If the locks dir exists, the semaphore system is active — use file presence.
    if sem.parent.exists():
        return sem.exists()

    # Locks dir doesn't exist yet → fall back to env var (legacy / first run).
    auto_dev = os.environ.get("AMPLIHACK_AUTO_DEV", "true").lower().strip()
    return auto_dev not in ("false", "0", "no", "off")


def enable_auto_dev() -> str:
    """Create the semaphore file. Returns a status message."""
    sem = _get_semaphore_path()
    sem.parent.mkdir(parents=True, exist_ok=True)
    if sem.exists():
        return "Auto-routing was already enabled."
    try:
        fd = os.open(str(sem), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"enabled\n")
        os.close(fd)
    except FileExistsError:
        pass  # race — another call created it first
    return "Auto-routing enabled. Development tasks will use the smart orchestrator."


def disable_auto_dev() -> str:
    """Remove the semaphore file. Returns a status message."""
    sem = _get_semaphore_path()
    # Ensure locks dir exists so future checks use file-based detection.
    sem.parent.mkdir(parents=True, exist_ok=True)
    try:
        sem.unlink()
    except FileNotFoundError:
        pass
    # Also clear the banner flag so it re-shows if re-enabled.
    try:
        _get_banner_flag_path().unlink()
    except FileNotFoundError:
        pass
    return "Auto-routing disabled. Type /amplihack:auto-dev to re-enable."


# ---------------------------------------------------------------------------
# Workflow-active semaphore (skip injection while orchestrator is running)
# ---------------------------------------------------------------------------


def _get_workflow_active_path() -> Path:
    """Return the path to the workflow-in-progress semaphore."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    base = Path(project_dir) if project_dir else Path.cwd()
    return base / ".claude" / "runtime" / "locks" / ".workflow_active"


def set_workflow_active(task_type: str = "", workstreams: int = 0, pid: int = 0) -> None:
    """Mark a workflow as in progress. Called by the orchestrator recipe.

    Args:
        pid: Process ID to track for liveness. If 0, uses os.getppid()
             (parent process) which is typically the recipe runner, not
             the ephemeral bash step.
    """
    path = _get_workflow_active_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    import time

    data = json.dumps(
        {
            "active": True,
            "task_type": task_type,
            "workstreams": workstreams,
            "started_at": time.time(),
            "pid": pid or os.getppid(),
        }
    )
    try:
        path.write_text(data + "\n")
    except OSError:
        pass


def clear_workflow_active() -> None:
    """Clear the workflow-in-progress semaphore. Called when orchestrator finishes."""
    try:
        _get_workflow_active_path().unlink()
    except FileNotFoundError:
        pass


def is_workflow_active() -> bool:
    """Check if a workflow is currently in progress (skip injection if so)."""
    path = _get_workflow_active_path()
    if not path.exists():
        return False
    try:
        import json
        import time

        age = time.time() - path.stat().st_mtime

        # Check PID liveness first (handles normal process termination)
        try:
            data = json.loads(path.read_text())
            pid = data.get("pid", 0)
            if pid > 0:
                os.kill(pid, 0)  # raises OSError if process doesn't exist
        except (json.JSONDecodeError, OSError, ValueError):
            # Process dead or JSON corrupt — semaphore is orphaned
            path.unlink(missing_ok=True)
            return False

        # Stale timeout as fallback (PID could be recycled)
        if age > 7200:  # 2 hours
            path.unlink(missing_ok=True)
            return False

        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def should_auto_route(prompt: str) -> tuple[bool, str]:
    """
    Returns (should_inject, injection_text).

    Returns (False, "") when:
    1. Disabled via semaphore file or AMPLIHACK_AUTO_DEV env var
    2. Prompt is not a string
    3. Prompt is empty or whitespace-only
    4. Prompt starts with / (existing slash command)
    5. Prompt is very short (< 10 chars) — likely conversational, not a task

    When injecting for the first time in a session, prepends a one-line
    welcome banner explaining auto-routing and how to disable it.
    """
    # 1. Check disable flag (semaphore file or env var)
    if not is_auto_dev_enabled():
        return False, ""

    # 1b. Skip if a workflow is already running (avoid re-classification mid-task)
    if is_workflow_active():
        return False, ""

    # 2. Type guard
    if not isinstance(prompt, str):
        return False, ""

    # 3. Empty / whitespace
    stripped = prompt.strip()
    if not stripped:
        return False, ""

    # 4. Slash commands
    if stripped.startswith("/"):
        return False, ""

    # 5. Short conversational messages (saves ~400 tokens per turn)
    if len(stripped) < _MIN_PROMPT_LENGTH:
        return False, ""

    # 6. Build injection text — prepend welcome banner on first injection
    injection = _ROUTING_PROMPT
    banner_flag = _get_banner_flag_path()
    try:
        if not banner_flag.exists():
            banner_flag.parent.mkdir(parents=True, exist_ok=True)
            banner_flag.write_text("shown\n")
            # Ensure the auto-dev semaphore exists so the locks dir being
            # created doesn't accidentally disable routing (the dir existing
            # flips from env-var to file-based detection). Use enable_auto_dev()
            # for atomic creation instead of raw write_text.
            if not _get_semaphore_path().exists():
                enable_auto_dev()
            injection = _WELCOME_BANNER + "\n\n" + _ROUTING_PROMPT
    except OSError:
        pass  # fail-open: skip banner if we can't write the flag

    return True, injection
