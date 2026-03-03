"""TUI status classification -- classify session status from tmux capture text.

Public API:
    classify_status: Classify session status from tmux capture text.
"""

from __future__ import annotations

__all__ = ["classify_status"]


def classify_status(tmux_text: str) -> str:
    # NOTE: This is a simplified status classifier for TUI display purposes.
    # The canonical status classifier is infer_agent_status() in fleet_session_reasoner.py.
    # These two systems return different value sets -- unification is tracked in issue #2799.
    """Classify session status from tmux capture text.

    Reuses patterns from fleet_session_reasoner._infer_status:
    - Active tool indicators (filled circle, streaming) = thinking
    - Processing markers = thinking
    - Claude Code prompt with status bar = idle/waiting
    - Shell prompt = shell
    - Error markers = error
    - Completion markers = completed
    - Substantial output = running
    """
    last_lines = tmux_text.strip().split("\n")[-10:]
    combined = "\n".join(last_lines)
    combined_lower = combined.lower()
    last_line = last_lines[-1].strip() if last_lines else ""

    # --- THINKING/WORKING (highest priority) ---
    for line in reversed(last_lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Active Claude Code tool call
        if stripped.startswith("\u25cf") and not stripped.startswith("\u25cf Bash("):
            return "thinking"
        # Streaming output
        if stripped.startswith("\u23bf"):
            return "thinking"
        # Processing timer
        if "\u273b" in stripped and ("for" in stripped.lower() or "saut" in stripped.lower()):
            return "thinking"
        break

    # Copilot thinking indicators
    if any(p in combined_lower for p in ["thinking...", "running:", "loading"]):
        return "thinking"

    # Claude Code tool call with output
    tool_prefixes = [
        "\u25cf Bash(",
        "\u25cf Read(",
        "\u25cf Write(",
        "\u25cf Edit(",
    ]
    if any(p in combined for p in tool_prefixes):
        if "\u23f5\u23f5" in last_line:
            return "idle"
        return "thinking"

    # --- ERROR ---
    if any(p in combined_lower for p in ["error:", "traceback", "fatal:", "panic:"]):
        return "error"

    # --- COMPLETED ---
    if any(p in combined for p in ["GOAL_STATUS: ACHIEVED", "Workflow Complete"]):
        return "completed"
    if any(p in combined for p in ["gh pr create", "PR #", "pull request"]):
        if any(p in combined_lower for p in ["created", "opened", "merged"]):
            return "completed"

    # --- IDLE (shell prompt, no agent) ---
    if last_line.endswith("$ ") or last_line.endswith("$"):
        return "shell"

    # Claude Code idle prompt
    if last_line.strip() == "\u276f" or last_line.strip().endswith("\u276f"):
        if not any("\u23f5\u23f5" in l for l in last_lines[-3:]):
            return "shell"
        return "idle"

    # --- Default: running if there is substantial output ---
    if len(combined.strip()) > 50:
        return "running"

    return "unknown"
