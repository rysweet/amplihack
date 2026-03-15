"""Regression tests for issue #3053: FileNotFoundError in _end_session.

16 tests covering:
- TestEnsureRuntimeDir: directory creation, idempotency, mode=0o700
- TestEndSessionRuntimeDirMissing: complete_session/crash_session without pre-existing dir
- TestOsErrorHandling: OSError during mkdir raises RuntimeError
- TestSessionLifecycleWithoutPreExistingDir: full lifecycle without pre-existing dir
- TestIssue3053Regression: E2E test - full lifecycle survives runtime dir deletion
"""
from __future__ import annotations

import json
import logging
import os
import stat
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.launcher.session_tracker import SessionTracker


# ---------------------------------------------------------------------------
# TestEnsureRuntimeDir
# ---------------------------------------------------------------------------

class TestEnsureRuntimeDir:
    """Tests for the _ensure_runtime_dir() guard."""

    def test_creates_directory_when_absent(self, tmp_path):
        """_ensure_runtime_dir creates the directory when it does not exist."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"
        assert not runtime_log.parent.exists(), "Precondition: dir must be absent"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

        assert runtime_log.parent.exists(), "_ensure_runtime_dir must create parent dir"

    def test_idempotent_when_dir_already_exists(self, tmp_path):
        """Calling _ensure_runtime_dir twice does not raise."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            # Second call must not raise (exist_ok=True)
            tracker._ensure_runtime_dir()

        assert runtime_log.parent.exists()

    def test_directory_mode_is_0o700(self, tmp_path):
        """Created directory has mode 0o700 (owner rwx only)."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

        runtime_dir = runtime_log.parent
        actual_mode = stat.S_IMODE(runtime_dir.stat().st_mode)
        assert actual_mode == 0o700, (
            f"Expected mode 0o700, got 0o{actual_mode:o}"
        )

    def test_creates_nested_parents(self, tmp_path):
        """_ensure_runtime_dir creates deeply nested parent dirs (parents=True)."""
        runtime_log = tmp_path / "a" / "b" / "c" / "d" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

        assert runtime_log.parent.exists(), "Nested parent dirs must be created"

    def test_reinvoked_after_deletion_recreates_dir(self, tmp_path):
        """_ensure_runtime_dir recreates dir after external deletion."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            assert runtime_log.parent.exists()

            shutil.rmtree(runtime_log.parent)
            assert not runtime_log.parent.exists()

            # Must recreate without error
            tracker._ensure_runtime_dir()

        assert runtime_log.parent.exists(), "Dir must be recreated on second call"


# ---------------------------------------------------------------------------
# TestEndSessionRuntimeDirMissing
# ---------------------------------------------------------------------------

class TestEndSessionRuntimeDirMissing:
    """_end_session() / complete_session() / crash_session() with no pre-existing dir."""

    def test_complete_session_does_not_raise_file_not_found(self, tmp_path):
        """complete_session() must not raise FileNotFoundError when dir is absent.

        Simulates the exact scenario of issue #3053: runtime dir removed after
        tracker is created but before complete_session() is called.
        """
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            session_id = tracker.start_session(
                pid=os.getpid(),
                launch_dir=str(tmp_path),
                argv=["amplihack"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            # Remove dir to simulate issue #3053
            shutil.rmtree(runtime_log.parent)
            assert not runtime_log.parent.exists()

            # Must NOT raise FileNotFoundError
            tracker.complete_session(session_id)

        assert runtime_log.exists(), "Log file must be re-created"
        entry = json.loads(runtime_log.read_text().strip())
        assert entry["status"] == "completed"

    def test_crash_session_does_not_raise_file_not_found(self, tmp_path):
        """crash_session() must not raise FileNotFoundError when dir is absent."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            session_id = tracker.start_session(
                pid=os.getpid(),
                launch_dir=str(tmp_path),
                argv=["amplihack"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            shutil.rmtree(runtime_log.parent)
            assert not runtime_log.parent.exists()

            tracker.crash_session(session_id)

        assert runtime_log.exists(), "Log file must be re-created"
        entry = json.loads(runtime_log.read_text().strip())
        assert entry["status"] == "crashed"

    def test_complete_session_without_prior_start(self, tmp_path):
        """complete_session() works even with no prior start_session call."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"
        assert not runtime_log.parent.exists()

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            # Remove dir after init
            shutil.rmtree(runtime_log.parent)
            # Call complete without a prior start
            tracker.complete_session("orphan-session-id")

        assert runtime_log.exists()
        entry = json.loads(runtime_log.read_text().strip())
        assert entry["session_id"] == "orphan-session-id"
        assert entry["status"] == "completed"


# ---------------------------------------------------------------------------
# TestOsErrorHandling
# ---------------------------------------------------------------------------

class TestOsErrorHandling:
    """OSError from mkdir propagates as RuntimeError."""

    def test_oserror_during_mkdir_raises_runtime_error(self, tmp_path):
        """An OSError during mkdir is re-raised as RuntimeError."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            # First instantiate successfully so RUNTIME_LOG is set
            tracker = SessionTracker.__new__(SessionTracker)

        # Patch mkdir on the Path class to raise OSError
        with patch.object(Path, "mkdir", side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError, match="Session tracking unavailable"):
                tracker._ensure_runtime_dir()

    def test_oserror_logs_debug_message(self, tmp_path, caplog):
        """An OSError during mkdir is logged at DEBUG level before raising."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker.__new__(SessionTracker)

        with patch.object(Path, "mkdir", side_effect=OSError("no space")):
            with caplog.at_level(logging.DEBUG, logger="amplihack.launcher.session_tracker"):
                with pytest.raises(RuntimeError):
                    tracker._ensure_runtime_dir()

        assert any("no space" in r.message for r in caplog.records), (
            "OSError message should be logged at DEBUG level"
        )

    def test_oserror_does_not_leak_path_info(self, tmp_path):
        """RuntimeError raised from OSError must not expose path details (from None)."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker.__new__(SessionTracker)

        with patch.object(Path, "mkdir", side_effect=OSError("permission denied")):
            with pytest.raises(RuntimeError) as exc_info:
                tracker._ensure_runtime_dir()

        # __cause__ must be None because we used `raise ... from None`
        assert exc_info.value.__cause__ is None, (
            "_ensure_runtime_dir must use 'raise ... from None' to suppress cause"
        )


# ---------------------------------------------------------------------------
# TestSessionLifecycleWithoutPreExistingDir
# ---------------------------------------------------------------------------

class TestSessionLifecycleWithoutPreExistingDir:
    """Full lifecycle works correctly when .claude/runtime/ never existed."""

    def test_start_then_complete_creates_log(self, tmp_path):
        """start_session + complete_session writes two entries to JSONL."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"
        assert not runtime_log.parent.exists()

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            sid = tracker.start_session(
                pid=42,
                launch_dir=str(tmp_path),
                argv=["amplihack", "launch"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )
            tracker.complete_session(sid)

        lines = runtime_log.read_text().strip().splitlines()
        assert len(lines) == 2
        start_entry = json.loads(lines[0])
        complete_entry = json.loads(lines[1])
        assert start_entry["status"] == "active"
        assert complete_entry["status"] == "completed"
        assert complete_entry["session_id"] == sid

    def test_start_then_crash_creates_log(self, tmp_path):
        """start_session + crash_session writes two entries to JSONL."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            sid = tracker.start_session(
                pid=99,
                launch_dir="/some/dir",
                argv=["amplihack"],
                is_auto_mode=True,
                is_nested=False,
                parent_session_id=None,
            )
            tracker.crash_session(sid)

        lines = runtime_log.read_text().strip().splitlines()
        assert len(lines) == 2
        crash_entry = json.loads(lines[1])
        assert crash_entry["status"] == "crashed"
        assert crash_entry["session_id"] == sid

    def test_multiple_sessions_no_pre_existing_dir(self, tmp_path):
        """Multiple start/end cycles accumulate in the JSONL file correctly."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            sid1 = tracker.start_session(1, "/dir1", ["cmd"], False, False, None)
            sid2 = tracker.start_session(2, "/dir2", ["cmd"], False, False, None)
            tracker.complete_session(sid1)
            tracker.crash_session(sid2)

        lines = runtime_log.read_text().strip().splitlines()
        assert len(lines) == 4, f"Expected 4 JSONL entries, got {len(lines)}"


# ---------------------------------------------------------------------------
# TestIssue3053Regression
# ---------------------------------------------------------------------------

class TestIssue3053Regression:
    """E2E regression test: full lifecycle survives runtime dir deletion mid-session."""

    def test_regression_3053_crash_session_survives_dir_deletion(self, tmp_path):
        """E2E: crash_session survives runtime dir deletion (mirrors issue #3053 for crash path)."""
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()
            sid = tracker.start_session(
                pid=os.getpid(),
                launch_dir=str(tmp_path),
                argv=["amplihack"],
                is_auto_mode=False,
                is_nested=False,
                parent_session_id=None,
            )

            shutil.rmtree(runtime_log.parent)
            assert not runtime_log.parent.exists()

            tracker.crash_session(sid)

        assert runtime_log.exists()
        entries = [json.loads(l) for l in runtime_log.read_text().strip().splitlines()]
        assert entries[-1]["status"] == "crashed"
        assert entries[-1]["session_id"] == sid

    def test_full_lifecycle_survives_dir_deletion(self, tmp_path):
        """E2E: session survives runtime dir being deleted between start and end.

        This is the exact regression scenario from issue #3053:
        1. Tracker initialises and creates the runtime dir.
        2. Session starts, log file is written.
        3. Runtime dir is deleted entirely (external cleanup, race condition, etc.)
        4. complete_session() is called — must NOT raise FileNotFoundError.
        5. The dir and log file are re-created with the completion entry.
        """
        runtime_log = tmp_path / ".claude" / "runtime" / "sessions.jsonl"

        with patch.object(SessionTracker, "RUNTIME_LOG", runtime_log):
            tracker = SessionTracker()

            # Step 1: start session (dir exists, file created)
            sid = tracker.start_session(
                pid=os.getpid(),
                launch_dir=str(tmp_path),
                argv=["amplihack", "launch", "--auto"],
                is_auto_mode=True,
                is_nested=False,
                parent_session_id=None,
            )
            assert runtime_log.exists(), "Log file must exist after start_session"

            # Step 2: simulate full dir deletion
            shutil.rmtree(runtime_log.parent)
            assert not runtime_log.parent.exists(), "Dir must be gone for test to be valid"

            # Step 3: complete_session must recreate dir and write entry
            tracker.complete_session(sid)

        # Verify re-creation
        assert runtime_log.parent.exists(), "Dir must be re-created by complete_session"
        assert runtime_log.exists(), "Log file must be re-created"

        # Only the completion entry should be present (start entry was lost with dir)
        entries = [json.loads(l) for l in runtime_log.read_text().strip().splitlines()]
        assert len(entries) == 1
        assert entries[0]["session_id"] == sid
        assert entries[0]["status"] == "completed"
        assert "end_time" in entries[0]
