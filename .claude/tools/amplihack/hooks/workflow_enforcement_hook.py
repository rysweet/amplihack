#!/usr/bin/env python3
"""Workflow Enforcement Hook — PostToolUse guard for recipe runner bypass.

Detects when /dev or dev-orchestrator skill was invoked but the recipe runner
was never actually called, and surfaces a hard WARNING to get Claude back on
track.

State is tracked in /tmp/amplihack-workflow-state/<session_id>.json so it
persists across tool calls within a single session.

Registration: imported and registered by post_tool_use.py via the tool_registry
pattern (same as blarify_staleness_hook and context_automation_hook).
"""

import json

# ---------------------------------------------------------------------------
# Imports for tool registry
# ---------------------------------------------------------------------------
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

try:
    from tool_registry import HookResult, get_global_registry

    REGISTRY_AVAILABLE = True
except ImportError as e:
    REGISTRY_AVAILABLE = False
    print(
        f"WARNING: tool_registry not available - hook registration disabled: {e}", file=sys.stderr
    )

    # Stub so the module can still be imported for testing
    class HookResult:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            self.actions_taken = kwargs.get("actions_taken", [])
            self.warnings = kwargs.get("warnings", [])
            self.metadata = kwargs.get("metadata", {})
            self.skip_remaining = kwargs.get("skip_remaining", False)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = Path("/tmp/amplihack-workflow-state")
# Number of tool calls after /dev invocation before we fire a warning
TOOL_CALL_THRESHOLD = 3

# Skill names that indicate /dev was invoked
DEV_SKILL_NAMES = frozenset(
    {
        "dev-orchestrator",
        "amplihack:dev",
        "amplihack:amplihack:dev",
        "default-workflow",
        "amplihack:default-workflow",
        "amplihack:amplihack:default-workflow",
        ".claude:amplihack:dev",
        ".claude:amplihack:default-workflow",
    }
)

# Tool names that indicate workflow is being followed (not just Read/Edit)
WORKFLOW_EVIDENCE_TOOLS = frozenset(
    {
        "TaskCreate",  # Workflow step tracking
    }
)

# Patterns in Bash commands that indicate real workflow execution
WORKFLOW_EVIDENCE_BASH = (
    "run_recipe_by_name",
    "smart-orchestrator",
    "recipe_runner",
    "amplihack.recipes",
    "git checkout -b",
    "git switch -c",
    "git branch ",
    "gh pr create",
    "gh issue create",
)

# Patterns in Read file paths that indicate workflow is being followed
WORKFLOW_EVIDENCE_READ = (
    "DEFAULT_WORKFLOW.md",
    "smart-orchestrator.yaml",
    "default-workflow.yaml",
    "investigation-workflow.yaml",
)

# Patterns in TodoWrite content that indicate workflow steps
WORKFLOW_EVIDENCE_TODO = (
    "Step ",
    "step ",
    "STEP ",
    "Create GitHub issue",
    "Create feature branch",
    "Recipe Runner",
    "recipe runner",
)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _get_session_id() -> str:
    """Get a stable session identifier.

    Uses a fixed name instead of PID because Copilot CLI spawns hooks as
    separate processes with different PPIDs for UserPromptSubmit vs PostToolUse.
    Since only one interactive session runs at a time per machine, a single
    state file is sufficient.
    """
    return "current"


def _state_path() -> Path:
    """Return the state file path for the current session."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_get_session_id()}.json"


def _read_state() -> dict[str, Any]:
    """Read the current enforcement state (or return empty defaults)."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(state: dict[str, Any]) -> None:
    """Persist enforcement state to disk."""
    try:
        _state_path().write_text(json.dumps(state, indent=2))
    except OSError:
        pass  # Non-fatal — we just lose tracking for this session


def _clear_state() -> None:
    """Remove the state file (workflow evidence found or session done)."""
    try:
        _state_path().unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _is_dev_skill_invocation(input_data: dict[str, Any]) -> bool:
    """Return True if this tool call is a Skill invocation for /dev."""
    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")

    if tool_name != "Skill":
        return False

    tool_input = tool_use.get("input", {})
    skill_name = tool_input.get("skill", "")

    return skill_name in DEV_SKILL_NAMES


def _has_workflow_evidence(input_data: dict[str, Any]) -> bool:
    """Return True if this tool call shows evidence of real workflow execution."""
    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")
    tool_input = tool_use.get("input", {})

    # Check Bash commands for recipe runner / branch creation
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if any(pattern in command for pattern in WORKFLOW_EVIDENCE_BASH):
            return True

    # Check Read for workflow file access
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if any(pattern in file_path for pattern in WORKFLOW_EVIDENCE_READ):
            return True

    # Check TodoWrite for workflow step patterns
    if tool_name == "TodoWrite":
        todos = tool_input.get("todos", [])
        for todo in todos:
            content = todo.get("content", "") + todo.get("activeForm", "")
            if any(pattern in content for pattern in WORKFLOW_EVIDENCE_TODO):
                return True

    # Check Agent tool — launching subagents is evidence of orchestration
    if tool_name == "Agent":
        return True

    # Check tool names that directly indicate workflow execution
    if tool_name in WORKFLOW_EVIDENCE_TOOLS:
        return True

    return False


# ---------------------------------------------------------------------------
# Main hook function
# ---------------------------------------------------------------------------


def workflow_enforcement_hook(input_data: dict[str, Any]) -> HookResult:
    """PostToolUse hook that enforces recipe runner usage after /dev.

    Flow:
    1. If this tool call IS a /dev skill invocation → set tracking state
    2. If tracking is active → check for workflow evidence
    3. If evidence found → clear state (all good)
    4. If no evidence after TOOL_CALL_THRESHOLD calls → emit hard WARNING
    """
    result = HookResult()

    try:
        # ------------------------------------------------------------------
        # Step 1: Detect /dev invocation
        # ------------------------------------------------------------------
        if _is_dev_skill_invocation(input_data):
            state = {
                "dev_invoked_at": time.time(),
                "tool_calls_since": 0,
                "warning_emitted": False,
            }
            _write_state(state)
            result.actions_taken.append(
                "workflow_enforcement: /dev invocation detected, tracking started"
            )
            return result

        # ------------------------------------------------------------------
        # Step 2: Check if we're tracking (post-/dev)
        # ------------------------------------------------------------------
        state = _read_state()
        if not state or "dev_invoked_at" not in state:
            return result  # Not tracking — nothing to do

        # ------------------------------------------------------------------
        # Step 3: Check for workflow evidence
        # ------------------------------------------------------------------
        if _has_workflow_evidence(input_data):
            _clear_state()
            result.actions_taken.append(
                "workflow_enforcement: workflow evidence found, tracking cleared"
            )
            return result

        # ------------------------------------------------------------------
        # Step 4: Increment counter and check threshold
        # ------------------------------------------------------------------
        state["tool_calls_since"] = state.get("tool_calls_since", 0) + 1
        _write_state(state)

        if state["tool_calls_since"] >= TOOL_CALL_THRESHOLD and not state.get("warning_emitted"):
            state["warning_emitted"] = True
            _write_state(state)

            result.warnings.append(
                "WORKFLOW BYPASS DETECTED: /dev was invoked but no recipe runner "
                "execution detected after {} tool calls. You MUST execute via "
                "run_recipe_by_name('smart-orchestrator'). Direct implementation "
                "without the recipe runner is PROHIBITED for Development tasks. "
                "The 23-step workflow, recursion guards, and goal verification are "
                "being skipped. STOP and invoke the recipe runner NOW.".format(
                    state["tool_calls_since"]
                )
            )
            result.metadata["workflow_enforcement"] = "WARNING"
            result.metadata["tool_calls_without_evidence"] = state["tool_calls_since"]

    except Exception as e:
        # Never crash — just note the error
        result.metadata["workflow_enforcement_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_workflow_enforcement_hook():
    """Register this hook with the global tool registry.

    Called by post_tool_use.py during _setup_tool_hooks().
    """
    if not REGISTRY_AVAILABLE:
        return

    registry = get_global_registry()
    registry.register(workflow_enforcement_hook)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing workflow_enforcement_hook...")

    # Clean up any leftover state
    _clear_state()

    # Scenario 1: /dev invocation sets tracking state
    skill_input = {
        "toolUse": {
            "name": "Skill",
            "input": {"skill": "dev-orchestrator"},
        },
        "result": {},
    }
    r = workflow_enforcement_hook(skill_input)
    assert "tracking started" in r.actions_taken[0], (
        f"Expected tracking started, got {r.actions_taken}"
    )
    state = _read_state()
    assert state.get("dev_invoked_at") is not None, "State should have dev_invoked_at"
    print("  [PASS] /dev invocation sets tracking state")

    # Scenario 2: Non-evidence tool calls increment counter
    read_input = {
        "toolUse": {"name": "Read", "input": {"file_path": "/some/random/file.py"}},
        "result": {},
    }
    for i in range(TOOL_CALL_THRESHOLD - 1):
        r = workflow_enforcement_hook(read_input)
        assert len(r.warnings) == 0, f"Should not warn yet at call {i + 1}"
    print(f"  [PASS] No warning before threshold ({TOOL_CALL_THRESHOLD} calls)")

    # Scenario 3: Warning fires at threshold
    r = workflow_enforcement_hook(read_input)
    assert len(r.warnings) == 1, f"Expected 1 warning, got {len(r.warnings)}"
    assert "WORKFLOW BYPASS DETECTED" in r.warnings[0]
    print("  [PASS] Warning fires at threshold")

    # Scenario 4: Warning only fires once
    r = workflow_enforcement_hook(read_input)
    assert len(r.warnings) == 0, "Warning should not repeat"
    print("  [PASS] Warning does not repeat")

    # Clean up
    _clear_state()

    # Scenario 5: Workflow evidence clears tracking
    skill_input2 = {
        "toolUse": {
            "name": "Skill",
            "input": {"skill": "amplihack:dev"},
        },
        "result": {},
    }
    workflow_enforcement_hook(skill_input2)  # Start tracking

    bash_evidence = {
        "toolUse": {
            "name": "Bash",
            "input": {
                "command": "PYTHONPATH=${AMPLIHACK_HOME:-~/.amplihack}/src python3 -c 'from amplihack.recipes import run_recipe_by_name'"
            },
        },
        "result": {},
    }
    r = workflow_enforcement_hook(bash_evidence)
    assert "workflow evidence found" in r.actions_taken[0]
    assert _read_state() == {}, "State should be cleared"
    print("  [PASS] Workflow evidence clears tracking")

    # Clean up
    _clear_state()

    print("\nAll tests passed!")
