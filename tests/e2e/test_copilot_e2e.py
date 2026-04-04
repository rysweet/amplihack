"""End-to-end outside-in tests for the lock mode co-pilot."""

from __future__ import annotations

import json
import os
import stat

import pytest


pytestmark = pytest.mark.e2e


def test_lock_tool_lifecycle(tmp_path):
    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)

    goal_file = lock_dir / ".lock_goal"
    goal_file.write_text("Goal: Fix auth bug\n\nDefinition of Done:\n- Tests pass", encoding="utf-8")

    lock_file = lock_dir / ".lock_active"
    fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, b"locked\n")
    finally:
        os.close(fd)

    assert goal_file.exists()
    assert stat.S_IMODE(lock_file.stat().st_mode) == 0o600
    assert lock_file.exists()
    assert "Fix auth bug" in goal_file.read_text(encoding="utf-8")

    lock_file.unlink()
    goal_file.unlink()

    assert not lock_file.exists()
    assert not goal_file.exists()


def test_get_copilot_continuation_handles_available_or_unavailable_backend(tmp_path):
    import copilot_stop_handler

    logs: list[str] = []
    result = copilot_stop_handler.get_copilot_continuation(
        goal="Fix auth",
        project_root=tmp_path,
        log_fn=lambda msg, *args: logs.append(str(msg)),
    )

    if result is None:
        assert any("not available" in line.lower() or "error" in line.lower() for line in logs)
        return

    assert result
    assert "Fix auth" in result


def test_log_decision_records_expected_fields(tmp_path):
    import copilot_stop_handler

    copilot_stop_handler._log_decision(
        project_root=tmp_path,
        goal="Fix the bug",
        action="send_input",
        confidence=0.85,
        reasoning="Tests needed",
        input_text="Run pytest",
        progress_pct=60,
    )

    log_file = tmp_path / ".claude" / "runtime" / "copilot-decisions" / "decisions.jsonl"
    entry = json.loads(log_file.read_text(encoding="utf-8").strip())

    assert log_file.exists()
    assert "timestamp" in entry
    assert entry["goal"] == "Fix the bug"
    assert entry["action"] == "send_input"
    assert entry["confidence"] == 0.85
    assert entry["reasoning"] == "Tests needed"
    assert entry["input_text"] == "Run pytest"
    assert entry["progress_pct"] == 60

    copilot_stop_handler._log_decision(
        project_root=tmp_path,
        goal="Fix the bug",
        action="mark_complete",
        confidence=0.95,
        reasoning="All tests pass",
    )

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["action"] == "mark_complete"


def test_disable_lock_files_removes_lock_state(tmp_path):
    import copilot_stop_handler

    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / ".lock_active").write_text("locked", encoding="utf-8")
    (lock_dir / ".lock_goal").write_text("goal", encoding="utf-8")

    copilot_stop_handler.disable_lock_files(tmp_path)

    assert not (lock_dir / ".lock_active").exists()
    assert not (lock_dir / ".lock_goal").exists()

    copilot_stop_handler.disable_lock_files(tmp_path)


def test_build_rich_context_with_large_transcript():
    from amplihack.fleet.fleet_copilot import build_rich_context

    entries = [json.dumps({"type": "human", "message": {"content": "Fix the authentication bug in login.py"}})]
    for i in range(300):
        entries.append(json.dumps({"type": "tool_use", "name": "Read", "message": {"content": f"file {i}"}}))
        entries.append(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": f"Step {i}"}]}}))

    context = build_rich_context("\n".join(entries), recent_message_count=100)

    assert "ORIGINAL USER REQUEST" in context
    assert "Fix the authentication bug" in context
    assert "SESSION HISTORY" in context
    assert "RECENT CONTEXT" in context


def test_extract_last_output_returns_only_latest_message():
    from amplihack.fleet.fleet_copilot import _extract_last_output

    entries = [
        json.dumps({"type": "assistant", "message": {"content": "Old"}}),
        json.dumps({"type": "tool_use", "name": "Bash", "message": {"content": "x"}}),
        json.dumps({"type": "tool_use", "name": "Bash", "message": {"content": "x"}}),
        json.dumps({"type": "assistant", "message": {"content": "Latest"}}),
    ]

    result = _extract_last_output("\n".join(entries))

    assert result == "Latest"
    assert "Old" not in result
