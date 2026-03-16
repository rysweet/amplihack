"""Agent status inference from terminal/tmux output.

Standalone classifier that examines the last lines of a tmux pane capture
and returns a status string used by both SessionReasoner and SessionCopilot.

Public API:
    infer_agent_status: Classify agent state from tmux text
"""

from __future__ import annotations

from amplihack.fleet._constants import MIN_SUBSTANTIAL_OUTPUT_LEN
from amplihack.utils.logging_utils import log_call

__all__ = ["infer_agent_status"]


@log_call
def infer_agent_status(tmux_text: str) -> str:
    """Infer agent status from tmux/terminal output.

    Critically distinguishes between:
    - THINKING: Agent is actively processing (LLM call in flight, tool running)
    - WAITING_INPUT: Agent needs user input to proceed
    - IDLE: No agent running (bare shell prompt), or agent at prompt with no input
    - RUNNING: Agent actively producing output (or status bar says "(running)")
    - ERROR/COMPLETED: Terminal states

    Returns one of:
        "thinking" -- Agent is actively processing (LLM call, tool running)
        "running" -- Agent producing output or status bar shows active
        "waiting_input" -- Agent needs user input (Y/n, permission prompt)
        "idle" -- Agent at its prompt (❯) with no input
        "shell" -- Bare shell prompt ($), agent is dead/crashed
        "error" -- Error indicators in output
        "completed" -- Goal achieved or PR created
        "unknown" -- Cannot determine status
    """
    all_lines = tmux_text.strip().split("\n")
    combined = "\n".join(all_lines)
    combined_lower = combined.lower()
    last_line = all_lines[-1].strip() if all_lines else ""
    last_line_lower = last_line.lower()
    # Use all lines for pattern matching — status inference needs full context
    last_lines = all_lines

    # Helper: find the prompt line and check if user typed input
    prompt_line_text = ""
    has_prompt = False
    for line in reversed(last_lines):
        stripped = line.strip()
        if stripped.startswith("\u276f"):
            has_prompt = True
            prompt_line_text = stripped[len("\u276f") :].strip()
            break

    # STATUS BAR "(running)" detection (high priority)
    for line in last_lines:
        if "(running)" in line and "\u23f5\u23f5" in line:
            return "running"

    # THINKING/WORKING detection (highest priority)
    for line in last_lines:
        stripped = line.strip()
        if stripped.startswith("\u00b7 "):
            return "thinking"

    # Check last non-empty line for tool/streaming indicators
    for line in reversed(last_lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("\u25cf") and not stripped.startswith("\u25cf Bash("):
            return "thinking"
        if stripped.startswith("\u23bf"):
            return "thinking"
        break

    # "\u273b" = JUST FINISHED thinking
    has_finished_indicator = False
    for line in last_lines:
        stripped = line.strip()
        if "\u273b" in stripped:
            has_finished_indicator = True
            break

    if has_finished_indicator and has_prompt:
        if prompt_line_text:
            return "thinking"
        return "idle"
    if has_finished_indicator and not has_prompt:
        return "thinking"

    # Copilot: explicit thinking indicators
    if any(p in combined_lower for p in ["thinking...", "running:", "loading"]):
        return "thinking"

    # Claude Code actively streaming (tool call with output)
    if (
        "\u25cf Bash(" in combined
        or "\u25cf Read(" in combined
        or "\u25cf Write(" in combined
        or "\u25cf Edit(" in combined
    ):
        if "\u23f5\u23f5" in last_line:
            return "waiting_input"
        return "thinking"

    # PROMPT with user input = agent processing
    if has_prompt and prompt_line_text:
        return "thinking"

    # IDLE detection: agent at its prompt (❯) vs bare shell ($)
    if has_prompt and not prompt_line_text:
        return "idle"
    # Bare shell prompt = agent is dead/crashed, back at bash
    if last_line_lower.endswith("$ ") or last_line_lower.endswith("$"):
        return "shell"

    # WAITING_INPUT detection
    if any(p in combined_lower for p in ["y/n]", "yes/no", "[y/n", "(yes/no)"]):
        return "waiting_input"
    if "\u23f5\u23f5" in combined and ("bypass" in combined_lower or "allow" in combined_lower):
        return "waiting_input"
    if last_line_lower.endswith("?"):
        return "waiting_input"

    # ERROR detection
    if any(p in combined_lower for p in ["error:", "traceback", "fatal:", "panic:"]):
        return "error"

    # COMPLETED detection
    if any(p in combined for p in ["GOAL_STATUS: ACHIEVED", "Workflow Complete"]):
        return "completed"
    if any(p in combined for p in ["gh pr create", "PR #", "pull request"]):
        if any(p in combined_lower for p in ["created", "opened", "merged"]):
            return "completed"

    # Default: assume running if substantial output
    if len(combined.strip()) > MIN_SUBSTANTIAL_OUTPUT_LEN:
        return "running"

    return "unknown"
