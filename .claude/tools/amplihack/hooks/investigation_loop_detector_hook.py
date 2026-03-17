#!/usr/bin/env python3
"""Investigation Loop Detector Hook — PostToolUse guard for read-without-edit loops.

Detects when an agent reads more than a configurable number of files without
making any edits, which indicates an investigation loop that should transition
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
        f"WARNING: tool_registry not available - hook registration disabled: {e}",
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

# Number of consecutive Read calls without an edit before warning fires
READ_THRESHOLD = 5

# Tool names that count as "reading" (investigation activity)
READ_TOOLS = frozenset({"Read", "Grep", "Glob"})

# Tool names that count as "editing" (implementation activity)
EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})

# Tool names that reset the counter (they indicate forward progress)
PROGRESS_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "Bash"})


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def _get_session_id() -> str:
    """Get a stable session identifier.

    Uses a fixed name because only one interactive session runs at a time.
    """
    return "current"


def _state_path() -> Path:
    """Return the state file path for the current session."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_get_session_id()}.json"


def _read_state() -> dict[str, Any]:
    """Read the current loop detection state (or return empty defaults)."""
    path = _state_path()
    if not path.exists():
        return {"read_count": 0, "edit_count": 0, "warning_emitted": False, "files_read": []}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"read_count": 0, "edit_count": 0, "warning_emitted": False, "files_read": []}


def _write_state(state: dict[str, Any]) -> None:
    """Persist loop detection state to disk."""
    try:
        _state_path().write_text(json.dumps(state, indent=2))
    except OSError:
        pass  # Non-fatal


def _clear_state() -> None:
    """Remove the state file (edit detected, loop broken)."""
    try:
        _state_path().unlink(missing_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Main hook function
# ---------------------------------------------------------------------------


def investigation_loop_detector_hook(input_data: dict[str, Any]) -> HookResult:
    """PostToolUse hook that detects investigation loops (reads without edits).

    Flow:
    1. If tool is a read/search tool -> increment read counter, track file
    2. If tool is an edit/write tool -> reset counters (loop broken)
    3. If tool is Bash -> reset counters (forward progress)
    4. If read_count > READ_THRESHOLD and no edits -> emit warning
    """
    result = HookResult()

    try:
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        state = _read_state()

        # ------------------------------------------------------------------
        # Edit/progress tool: reset counters — implementation is happening
        # ------------------------------------------------------------------
        if tool_name in PROGRESS_TOOLS:
            if state.get("read_count", 0) > 0:
                result.actions_taken.append(
                    f"investigation_loop_detector: progress detected ({tool_name}), "
                    f"resetting after {state.get('read_count', 0)} reads"
                )
            _clear_state()
            return result

        # ------------------------------------------------------------------
        # Read/search tool: increment counter, track file path
        # ------------------------------------------------------------------
        if tool_name in READ_TOOLS:
            state["read_count"] = state.get("read_count", 0) + 1
            state.setdefault("files_read", [])
            state.setdefault("warning_emitted", False)
            state.setdefault("started_at", time.time())

            # Track the file path for diagnostic context
            file_path = tool_input.get("file_path", tool_input.get("pattern", ""))
            if file_path and file_path not in state["files_read"]:
                # Keep last 20 entries to avoid unbounded growth
                state["files_read"] = state["files_read"][-19:] + [file_path]

            _write_state(state)

            # Check threshold
            if state["read_count"] > READ_THRESHOLD and not state.get("warning_emitted"):
                state["warning_emitted"] = True
                _write_state(state)

                files_summary = ", ".join(state["files_read"][-5:])
                result.warnings.append(
                    "INVESTIGATION LOOP DETECTED: You have read {} files/patterns "
                    "without making any edits. Recent targets: [{}]. "
                    "If you have enough context to proceed, transition from "
                    "investigation to implementation. Consider using Edit, Write, "
                    "or Bash to make progress.".format(
                        state["read_count"], files_summary
                    )
                )
                result.metadata["investigation_loop"] = "WARNING"
                result.metadata["reads_without_edit"] = state["read_count"]
                result.metadata["files_read"] = state["files_read"][-5:]

            return result

        # ------------------------------------------------------------------
        # Other tools (Skill, Agent, etc.): no-op — don't affect counters
        # ------------------------------------------------------------------

    except Exception as e:
        # Never crash — just note the error
        result.metadata["investigation_loop_detector_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_investigation_loop_detector_hook():
    """Register this hook with the global tool registry.

    Called by post_tool_use.py during _setup_tool_hooks().
    """
    if not REGISTRY_AVAILABLE:
        return

    registry = get_global_registry()
    registry.register(investigation_loop_detector_hook)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing investigation_loop_detector_hook...")

    # Clean up any leftover state
    _clear_state()

    # Scenario 1: Reading files increments counter
    for i in range(READ_THRESHOLD):
        read_input = {
            "toolUse": {
                "name": "Read",
                "input": {"file_path": f"/some/file_{i}.py"},
            },
            "result": {},
        }
        r = investigation_loop_detector_hook(read_input)
        assert len(r.warnings) == 0, f"Should not warn at read {i + 1}"

    state = _read_state()
    assert state["read_count"] == READ_THRESHOLD, (
        f"Expected {READ_THRESHOLD} reads, got {state['read_count']}"
    )
    print(f"  [PASS] {READ_THRESHOLD} reads without warning")

    # Scenario 2: Warning fires after threshold
    read_input = {
        "toolUse": {
            "name": "Read",
            "input": {"file_path": "/some/file_extra.py"},
        },
        "result": {},
    }
    r = investigation_loop_detector_hook(read_input)
    assert len(r.warnings) == 1, f"Expected 1 warning, got {len(r.warnings)}"
    assert "INVESTIGATION LOOP DETECTED" in r.warnings[0]
    print("  [PASS] Warning fires after threshold exceeded")

    # Scenario 3: Warning only fires once
    r = investigation_loop_detector_hook(read_input)
    assert len(r.warnings) == 0, "Warning should not repeat"
    print("  [PASS] Warning does not repeat")

    # Scenario 4: Grep and Glob also count as reads
    _clear_state()
    for i in range(READ_THRESHOLD + 1):
        tool_name = ["Read", "Grep", "Glob"][i % 3]
        inp = {
            "toolUse": {
                "name": tool_name,
                "input": {"file_path": f"/file_{i}.py", "pattern": "test"},
            },
            "result": {},
        }
        investigation_loop_detector_hook(inp)

    state = _read_state()
    assert state.get("warning_emitted") is True, "Warning should have fired for mixed read tools"
    print("  [PASS] Grep and Glob count toward threshold")

    # Scenario 5: Edit resets counters
    _clear_state()
    for i in range(3):
        read_input = {
            "toolUse": {"name": "Read", "input": {"file_path": f"/file_{i}.py"}},
            "result": {},
        }
        investigation_loop_detector_hook(read_input)

    edit_input = {
        "toolUse": {
            "name": "Edit",
            "input": {"file_path": "/file_0.py", "old_string": "x", "new_string": "y"},
        },
        "result": {},
    }
    r = investigation_loop_detector_hook(edit_input)
    assert "progress detected" in r.actions_taken[0]
    assert not _state_path().exists(), "State file should be deleted after edit"
    print("  [PASS] Edit resets counters")

    # Scenario 6: Bash resets counters
    _clear_state()
    for i in range(3):
        read_input = {
            "toolUse": {"name": "Read", "input": {"file_path": f"/file_{i}.py"}},
            "result": {},
        }
        investigation_loop_detector_hook(read_input)

    bash_input = {
        "toolUse": {
            "name": "Bash",
            "input": {"command": "pytest tests/"},
        },
        "result": {},
    }
    r = investigation_loop_detector_hook(bash_input)
    assert "progress detected" in r.actions_taken[0]
    print("  [PASS] Bash resets counters")

    # Clean up
    _clear_state()

    print("\nAll tests passed!")
