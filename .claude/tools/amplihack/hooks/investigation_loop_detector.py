#!/usr/bin/env python3
"""Investigation Loop Detector — PostToolUse hook for read-without-edit detection.

Detects when an agent reads more than a configurable number of files without
making any edits, which signals an investigation loop that should transition
to implementation.

State is tracked in /tmp/amplihack-investigation-loop/<session_id>.json so it
persists across tool calls within a single session.

Registration: imported and registered by post_tool_use.py via the tool_registry
pattern (same as workflow_enforcement_hook and context_automation_hook).
"""

import json
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
        f"WARNING: tool_registry not available - investigation loop detector disabled: {e}",
        file=sys.stderr,
    )

    class HookResult:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            self.actions_taken = kwargs.get("actions_taken", [])
            self.warnings = kwargs.get("warnings", [])
            self.metadata = kwargs.get("metadata", {})
            self.skip_remaining = kwargs.get("skip_remaining", False)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = Path("/tmp/amplihack-investigation-loop")

# Number of reads without edits before warning fires
READ_THRESHOLD = 5

# Tool names that count as "reading" (investigation activity)
READ_TOOLS = frozenset({"Read", "Grep", "Glob"})

# Tool names that count as "editing" (implementation activity)
EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})

# Tool names that reset the counter (evidence of implementation)
IMPLEMENTATION_EVIDENCE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})

# Bash commands that count as implementation (not just investigation)
IMPLEMENTATION_BASH_PATTERNS = (
    "git commit",
    "git add",
    "pytest",
    "python -m pytest",
    "npm test",
    "make ",
    "cargo build",
    "cargo test",
    "go build",
    "go test",
)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _get_session_id() -> str:
    """Get a stable session identifier.

    Uses a fixed name since only one interactive session runs at a time
    per machine (same rationale as workflow_enforcement_hook).
    """
    return "current"


def _state_path() -> Path:
    """Return the state file path for the current session."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_get_session_id()}.json"


def _read_state() -> dict[str, Any]:
    """Read the current detection state (or return empty defaults)."""
    path = _state_path()
    if not path.exists():
        return {"reads_without_edit": 0, "files_read": [], "warning_emitted": False}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"reads_without_edit": 0, "files_read": [], "warning_emitted": False}


def _write_state(state: dict[str, Any]) -> None:
    """Persist detection state to disk."""
    try:
        _state_path().write_text(json.dumps(state, indent=2))
    except OSError:
        pass  # Non-fatal — we just lose tracking for this session


def _clear_state() -> None:
    """Reset the state (edit detected, loop broken)."""
    try:
        _state_path().unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------


def _is_read_operation(input_data: dict[str, Any]) -> tuple[bool, str]:
    """Return (True, file_path) if this tool call is a read/investigation operation."""
    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")
    tool_input = tool_use.get("input", {})

    if tool_name in READ_TOOLS:
        # Extract a meaningful identifier for the read
        file_path = tool_input.get("file_path", "")
        pattern = tool_input.get("pattern", "")
        identifier = file_path or pattern or tool_name
        return True, identifier

    return False, ""


def _is_edit_operation(input_data: dict[str, Any]) -> bool:
    """Return True if this tool call is an edit/implementation operation."""
    tool_use = input_data.get("toolUse", {})
    tool_name = tool_use.get("name", "")
    tool_input = tool_use.get("input", {})

    if tool_name in IMPLEMENTATION_EVIDENCE_TOOLS:
        return True

    # Check Bash commands for implementation evidence
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if any(pattern in command for pattern in IMPLEMENTATION_BASH_PATTERNS):
            return True

    return False


# ---------------------------------------------------------------------------
# Main hook function
# ---------------------------------------------------------------------------


def investigation_loop_detector(input_data: dict[str, Any]) -> HookResult:
    """PostToolUse hook that detects investigation loops (reads without edits).

    Flow:
    1. If this is an edit operation -> reset counter (implementation happening)
    2. If this is a read operation -> increment counter
    3. If counter exceeds READ_THRESHOLD -> emit WARNING
    """
    result = HookResult()

    try:
        # ------------------------------------------------------------------
        # Step 1: Check for edit/implementation evidence -> reset
        # ------------------------------------------------------------------
        if _is_edit_operation(input_data):
            state = _read_state()
            if state.get("reads_without_edit", 0) > 0:
                result.actions_taken.append(
                    "investigation_loop_detector: edit detected after {} reads, counter reset".format(
                        state["reads_without_edit"]
                    )
                )
            _clear_state()
            return result

        # ------------------------------------------------------------------
        # Step 2: Check for read/investigation operation -> increment
        # ------------------------------------------------------------------
        is_read, identifier = _is_read_operation(input_data)
        if not is_read:
            return result  # Not a read or edit — skip

        state = _read_state()
        state["reads_without_edit"] = state.get("reads_without_edit", 0) + 1

        # Track which files were read (keep last 10 for context)
        files_read = state.get("files_read", [])
        if identifier and identifier not in files_read:
            files_read.append(identifier)
            if len(files_read) > 10:
                files_read = files_read[-10:]
        state["files_read"] = files_read

        state.setdefault("first_read_at", time.time())
        _write_state(state)

        # ------------------------------------------------------------------
        # Step 3: Check threshold and emit warning
        # ------------------------------------------------------------------
        if state["reads_without_edit"] > READ_THRESHOLD and not state.get("warning_emitted"):
            state["warning_emitted"] = True
            _write_state(state)

            files_summary = ", ".join(state["files_read"][-5:])
            result.warnings.append(
                "INVESTIGATION LOOP DETECTED: You have read {} files/patterns "
                "without making any edits. Recent reads: [{}]. "
                "If you have enough context, transition from investigation to "
                "implementation. Start making edits to move the task forward.".format(
                    state["reads_without_edit"], files_summary
                )
            )
            result.metadata["investigation_loop"] = "WARNING"
            result.metadata["reads_without_edit"] = state["reads_without_edit"]
            result.metadata["files_read"] = state["files_read"]

    except Exception as e:
        # Never crash — just note the error
        result.metadata["investigation_loop_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_investigation_loop_detector():
    """Register this hook with the global tool registry.

    Called by post_tool_use.py during _setup_tool_hooks().
    """
    if not REGISTRY_AVAILABLE:
        return

    registry = get_global_registry()
    registry.register(investigation_loop_detector)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing investigation_loop_detector...")

    # Clean up any leftover state
    _clear_state()

    # Scenario 1: Reads increment counter
    for i in range(READ_THRESHOLD):
        read_input = {
            "toolUse": {
                "name": "Read",
                "input": {"file_path": f"/some/file_{i}.py"},
            },
            "result": {},
        }
        r = investigation_loop_detector(read_input)
        assert len(r.warnings) == 0, f"Should not warn at read {i + 1}"

    state = _read_state()
    assert state["reads_without_edit"] == READ_THRESHOLD, (
        f"Expected {READ_THRESHOLD} reads, got {state['reads_without_edit']}"
    )
    print(f"  [PASS] {READ_THRESHOLD} reads without warning")

    # Scenario 2: Warning fires after threshold exceeded
    read_input = {
        "toolUse": {
            "name": "Read",
            "input": {"file_path": "/some/file_extra.py"},
        },
        "result": {},
    }
    r = investigation_loop_detector(read_input)
    assert len(r.warnings) == 1, f"Expected 1 warning, got {len(r.warnings)}"
    assert "INVESTIGATION LOOP DETECTED" in r.warnings[0]
    print("  [PASS] Warning fires after threshold exceeded")

    # Scenario 3: Warning only fires once
    r = investigation_loop_detector(read_input)
    assert len(r.warnings) == 0, "Warning should not repeat"
    print("  [PASS] Warning does not repeat")

    # Scenario 4: Edit resets counter
    edit_input = {
        "toolUse": {
            "name": "Edit",
            "input": {"file_path": "/some/file.py", "old_string": "a", "new_string": "b"},
        },
        "result": {},
    }
    r = investigation_loop_detector(edit_input)
    assert "counter reset" in r.actions_taken[0]
    state = _read_state()
    assert state.get("reads_without_edit", 0) == 0 or not Path(_state_path()).exists()
    print("  [PASS] Edit resets counter")

    # Clean up
    _clear_state()

    # Scenario 5: Grep and Glob also count as reads
    grep_input = {
        "toolUse": {
            "name": "Grep",
            "input": {"pattern": "TODO"},
        },
        "result": {},
    }
    glob_input = {
        "toolUse": {
            "name": "Glob",
            "input": {"pattern": "**/*.py"},
        },
        "result": {},
    }
    investigation_loop_detector(grep_input)
    investigation_loop_detector(glob_input)
    state = _read_state()
    assert state["reads_without_edit"] == 2, (
        f"Expected 2 reads, got {state['reads_without_edit']}"
    )
    print("  [PASS] Grep and Glob count as reads")

    # Scenario 6: Bash with implementation patterns resets counter
    _clear_state()
    for i in range(3):
        investigation_loop_detector(
            {"toolUse": {"name": "Read", "input": {"file_path": f"/f{i}.py"}}, "result": {}}
        )
    bash_impl = {
        "toolUse": {
            "name": "Bash",
            "input": {"command": "git commit -m 'fix something'"},
        },
        "result": {},
    }
    r = investigation_loop_detector(bash_impl)
    assert any("counter reset" in a for a in r.actions_taken)
    print("  [PASS] Bash implementation patterns reset counter")

    # Clean up
    _clear_state()

    print("\nAll tests passed!")
