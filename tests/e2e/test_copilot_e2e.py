"""End-to-end outside-in test for the lock mode co-pilot."""

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = "/home/azureuser/src/amplihack9"
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "amplifier-bundle/tools/amplihack/hooks"))

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


# ── Test 1: Lock tool lifecycle ──
print("\n=== Test 1: Lock tool lifecycle ===")
with tempfile.TemporaryDirectory() as tmpdir:
    lock_dir = Path(tmpdir) / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)
    goal_file = lock_dir / ".lock_goal"
    goal_file.write_text("Goal: Fix auth bug\n\nDefinition of Done:\n- Tests pass")
    check("Goal file written", goal_file.exists())
    lock_file = lock_dir / ".lock_active"
    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, b"locked\n")
    os.close(fd)
    check("Lock file created with 0o600", oct(lock_file.stat().st_mode)[-3:] == "600")
    check("Lock active", lock_file.exists())
    check("Goal readable", "Fix auth bug" in goal_file.read_text())
    lock_file.unlink()
    goal_file.unlink()
    check("Lock removed", not lock_file.exists())
    check("Goal removed", not goal_file.exists())

# ── Test 2: copilot_stop_handler with fleet module ──
print("\n=== Test 2: copilot_stop_handler get_copilot_continuation ===")
from copilot_stop_handler import disable_lock_files, get_copilot_continuation

with tempfile.TemporaryDirectory() as tmpdir:
    project_root = Path(tmpdir)
    logs = []
    result = get_copilot_continuation(
        goal="Fix auth",
        project_root=project_root,
        log_fn=lambda msg, *a: logs.append(str(msg)),
    )
    # SessionCopilot requires LLM backend — it will either work or gracefully fail
    if result is not None:
        check("Got continuation prompt", len(result) > 0)
        check("Prompt mentions goal", "Fix auth" in result)
    else:
        check("Graceful fallback when copilot unavailable", True)
        check("Logged the failure", any("not available" in l or "error" in l.lower() for l in logs))

# ── Test 3: Decision logging ──
print("\n=== Test 3: Decision logging ===")
from copilot_stop_handler import _log_decision

with tempfile.TemporaryDirectory() as tmpdir:
    project_root = Path(tmpdir)
    _log_decision(
        project_root=project_root,
        goal="Fix the bug",
        action="send_input",
        confidence=0.85,
        reasoning="Tests needed",
        input_text="Run pytest",
        progress_pct=60,
    )
    log_file = project_root / ".claude" / "runtime" / "copilot-decisions" / "decisions.jsonl"
    check("Decision log file created", log_file.exists())
    entry = json.loads(log_file.read_text().strip())
    check("Log has timestamp", "timestamp" in entry)
    check("Log has goal", entry["goal"] == "Fix the bug")
    check("Log has action", entry["action"] == "send_input")
    check("Log has confidence", entry["confidence"] == 0.85)
    check("Log has reasoning", entry["reasoning"] == "Tests needed")
    check("Log has input_text", entry["input_text"] == "Run pytest")
    check("Log has progress", entry["progress_pct"] == 60)

    _log_decision(
        project_root=project_root,
        goal="Fix the bug",
        action="mark_complete",
        confidence=0.95,
        reasoning="All tests pass",
    )
    lines = log_file.read_text().strip().split("\n")
    check("Multiple decisions logged", len(lines) == 2)
    check("Second is mark_complete", json.loads(lines[1])["action"] == "mark_complete")

# ── Test 4: disable_lock_files ──
print("\n=== Test 4: Auto-disable lock files ===")
with tempfile.TemporaryDirectory() as tmpdir:
    project_root = Path(tmpdir)
    lock_dir = project_root / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / ".lock_active").write_text("locked")
    (lock_dir / ".lock_goal").write_text("goal")
    disable_lock_files(project_root)
    check("Lock file removed", not (lock_dir / ".lock_active").exists())
    check("Goal file removed", not (lock_dir / ".lock_goal").exists())
    disable_lock_files(project_root)  # Safe on missing files
    check("No error on missing files", True)

# ── Test 5: build_rich_context ──
print("\n=== Test 5: build_rich_context with 601-entry transcript ===")
from amplihack.fleet.fleet_copilot import build_rich_context

entries = [
    json.dumps({"type": "human", "message": {"content": "Fix the authentication bug in login.py"}})
]
for i in range(300):
    entries.append(
        json.dumps({"type": "tool_use", "name": "Read", "message": {"content": f"file {i}"}})
    )
    entries.append(
        json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": f"Step {i}"}]}}
        )
    )
ctx = build_rich_context("\n".join(entries), recent_message_count=100)
check("Has ORIGINAL USER REQUEST", "ORIGINAL USER REQUEST" in ctx)
check("Has first message content", "Fix the authentication bug" in ctx)
check("Has SESSION HISTORY summary", "SESSION HISTORY" in ctx)
check("Has RECENT CONTEXT", "RECENT CONTEXT" in ctx)

# ── Test 6: _extract_last_output ──
print("\n=== Test 6: _extract_last_output returns only last ===")
from amplihack.fleet.fleet_copilot import _extract_last_output

entries = [
    json.dumps({"type": "assistant", "message": {"content": "Old"}}),
    json.dumps({"type": "tool_use", "name": "Bash", "message": {"content": "x"}}),
    json.dumps({"type": "tool_use", "name": "Bash", "message": {"content": "x"}}),
    json.dumps({"type": "assistant", "message": {"content": "Latest"}}),
]
result = _extract_last_output("\n".join(entries))
check("Returns latest", result == "Latest")
check("No old messages", "Old" not in result)

# ── Summary ──
print(f"\n{'=' * 50}")
print(f"RESULTS: {PASS} passed, {FAIL} failed")
if FAIL > 0:
    sys.exit(1)
print("ALL OUTSIDE-IN TESTS PASSED")
