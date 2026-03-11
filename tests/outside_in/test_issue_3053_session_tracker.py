"""Outside-in behavioral validation for issue #3053: session_tracker crashes on missing dir.

Verifies that SessionTracker.complete_session() and crash_session() do not raise
FileNotFoundError when .claude/runtime/ does not exist yet.

The fix ensures _end_session() creates the parent directory before writing.

Uses importlib to load session_tracker.py directly from the source tree to avoid
sys.path conflicts with the .claude/tools namespace overlay (see conftest.py).
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

# Load session_tracker directly from source to bypass .claude/tools overlay.
_SESSION_TRACKER_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "amplihack"
    / "launcher"
    / "session_tracker.py"
)
_spec = importlib.util.spec_from_file_location("session_tracker", _SESSION_TRACKER_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SessionTracker = _mod.SessionTracker


@pytest.fixture()
def empty_project_dir(tmp_path, monkeypatch):
    """Create a temp dir with NO .claude/runtime/ and chdir into it.

    SessionTracker.RUNTIME_LOG is relative (".claude/runtime/sessions.jsonl"),
    so the working directory determines where files are created.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestIssue3053EndSessionMissingDir:
    """Verify end_session creates directories instead of crashing."""

    def test_complete_session_creates_dir(self, empty_project_dir):
        """complete_session must not raise when .claude/runtime/ is absent."""
        runtime_dir = empty_project_dir / ".claude" / "runtime"
        assert not runtime_dir.exists(), "Precondition: runtime dir must not exist"

        tracker = SessionTracker()
        # Should not raise FileNotFoundError
        tracker.complete_session("test-session-complete")

        log_file = runtime_dir / "sessions.jsonl"
        assert log_file.exists(), "sessions.jsonl should be created"

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["session_id"] == "test-session-complete"
        assert entry["status"] == "completed"
        assert "end_time" in entry

    def test_crash_session_creates_dir(self, empty_project_dir):
        """crash_session must not raise when .claude/runtime/ is absent."""
        runtime_dir = empty_project_dir / ".claude" / "runtime"
        assert not runtime_dir.exists(), "Precondition: runtime dir must not exist"

        tracker = SessionTracker()
        tracker.crash_session("test-session-crash")

        log_file = runtime_dir / "sessions.jsonl"
        assert log_file.exists(), "sessions.jsonl should be created"

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["session_id"] == "test-session-crash"
        assert entry["status"] == "crashed"
        assert "end_time" in entry

    def test_end_session_after_dir_deleted(self, empty_project_dir):
        """If runtime dir is deleted between start and end, end must still work."""
        tracker = SessionTracker()
        session_id = tracker.start_session(
            pid=os.getpid(),
            launch_dir=str(empty_project_dir),
            argv=["amplihack", "launch"],
            is_auto_mode=False,
            is_nested=False,
            parent_session_id=None,
        )

        runtime_dir = empty_project_dir / ".claude" / "runtime"
        log_file = runtime_dir / "sessions.jsonl"

        # Simulate directory disappearing (e.g., cleanup, race condition)
        log_file.unlink()
        runtime_dir.rmdir()
        (empty_project_dir / ".claude").rmdir()
        assert not runtime_dir.exists()

        # Must recreate and write without error
        tracker.complete_session(session_id)
        assert log_file.exists()

        entry = json.loads(log_file.read_text().strip())
        assert entry["session_id"] == session_id
        assert entry["status"] == "completed"
