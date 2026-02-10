"""Tests for NestingDetector - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import json
import os
from unittest.mock import patch

from amplihack.launcher.nesting_detector import (
    NestingDetector,
    NestingResult,
)


# UNIT TESTS (60%)
class TestNestingResult:
    """Test NestingResult dataclass creation"""

    def test_nesting_result_creation(self):
        """Test creating a NestingResult with all fields"""
        result = NestingResult(
            is_nested=True,
            in_source_repo=False,
            parent_session_id="parent-123",
            active_session=None,
            requires_staging=True,
        )

        assert result.is_nested is True
        assert result.in_source_repo is False
        assert result.parent_session_id == "parent-123"
        assert result.active_session is None
        assert result.requires_staging is True


class TestAmplihackSourceRepoDetection:
    """Test _is_amplihack_source_repo method"""

    def test_detects_amplihack_from_pyproject(self, tmp_path):
        """Test detection when pyproject.toml has name = 'amplihack'"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "amplihack"\nversion = "0.9.0"')

        detector = NestingDetector()
        assert detector._is_amplihack_source_repo(tmp_path) is True

    def test_not_amplihack_when_different_name(self, tmp_path):
        """Test no detection when pyproject.toml has different name"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "other-project"\nversion = "1.0.0"')

        detector = NestingDetector()
        assert detector._is_amplihack_source_repo(tmp_path) is False

    def test_not_amplihack_when_no_pyproject(self, tmp_path):
        """Test no detection when pyproject.toml doesn't exist"""
        detector = NestingDetector()
        assert detector._is_amplihack_source_repo(tmp_path) is False

    def test_not_amplihack_when_invalid_toml(self, tmp_path):
        """Test graceful handling of invalid TOML"""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid toml content [[[")

        detector = NestingDetector()
        assert detector._is_amplihack_source_repo(tmp_path) is False


class TestProcessAliveness:
    """Test _is_process_alive method"""

    def test_current_process_is_alive(self):
        """Test that current process PID is detected as alive"""
        detector = NestingDetector()
        assert detector._is_process_alive(os.getpid()) is True

    def test_invalid_pid_not_alive(self):
        """Test that invalid PID (99999) is not alive"""
        detector = NestingDetector()
        assert detector._is_process_alive(99999) is False

    def test_negative_pid_not_alive(self):
        """Test that negative PID returns False"""
        detector = NestingDetector()
        assert detector._is_process_alive(-1) is False

    @patch("os.kill")
    def test_process_not_exists_error(self, mock_kill):
        """Test handling of ProcessLookupError"""
        mock_kill.side_effect = ProcessLookupError()

        detector = NestingDetector()
        assert detector._is_process_alive(12345) is False

    @patch("os.kill")
    def test_process_permission_error(self, mock_kill):
        """Test handling of PermissionError (process exists but can't signal)"""
        mock_kill.side_effect = PermissionError()

        detector = NestingDetector()
        assert detector._is_process_alive(12345) is True


class TestFindActiveSession:
    """Test _find_active_session method"""

    def test_no_active_session_when_no_log(self, tmp_path):
        """Test returns None when sessions.jsonl doesn't exist"""
        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            result = detector._find_active_session(tmp_path)
            assert result is None

    def test_no_active_session_when_empty_log(self, tmp_path):
        """Test returns None when sessions.jsonl is empty"""
        sessions_log = tmp_path / "sessions.jsonl"
        sessions_log.write_text("")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector._find_active_session(tmp_path)
            assert result is None

    def test_finds_active_session_with_live_pid(self, tmp_path):
        """Test finds active session when PID is still alive"""
        sessions_log = tmp_path / "sessions.jsonl"

        # Write an active session with current PID (guaranteed alive)
        entry = {
            "pid": os.getpid(),
            "session_id": "active-123",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "active",
            "end_time": None,
        }
        sessions_log.write_text(json.dumps(entry) + "\n")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector._find_active_session(tmp_path)

            assert result is not None
            assert result.session_id == "active-123"
            assert result.pid == os.getpid()

    def test_ignores_dead_process_sessions(self, tmp_path):
        """Test ignores active sessions with dead PIDs"""
        sessions_log = tmp_path / "sessions.jsonl"

        # Write an active session with impossible PID
        entry = {
            "pid": 99999,
            "session_id": "dead-123",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "active",
            "end_time": None,
        }
        sessions_log.write_text(json.dumps(entry) + "\n")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector._find_active_session(tmp_path)
            assert result is None

    def test_ignores_completed_sessions(self, tmp_path):
        """Test ignores sessions marked as completed"""
        sessions_log = tmp_path / "sessions.jsonl"

        # Write a completed session
        entry = {
            "pid": os.getpid(),
            "session_id": "completed-123",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "completed",
            "end_time": 1234567900.0,
        }
        sessions_log.write_text(json.dumps(entry) + "\n")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector._find_active_session(tmp_path)
            assert result is None

    def test_handles_corrupted_jsonl(self, tmp_path):
        """Test graceful handling of corrupted/malformed JSON in sessions.jsonl"""
        sessions_log = tmp_path / "sessions.jsonl"

        # Write mix of valid and corrupted JSON lines
        sessions_log.write_text(
            '{"pid": 12345, "session_id": "valid-1", "status": "completed"}\n'
            "this is not valid json at all\n"
            '{"incomplete json without closing brace"\n'
            '{"pid": '
            + str(os.getpid())
            + ', "session_id": "valid-2", "launch_dir": "'
            + str(tmp_path)
            + '", "argv": ["test"], "start_time": 1.0, '
            '"is_auto_mode": false, "is_nested": false, "parent_session_id": null, '
            '"status": "active", "end_time": null}\n'
        )

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            # Should skip corrupted lines and find the valid active session
            result = detector._find_active_session(tmp_path)
            assert result is not None
            assert result.session_id == "valid-2"


# INTEGRATION TESTS (30%)
class TestNestingDetection:
    """Test detect_nesting method (main detection logic)"""

    def test_not_nested_in_normal_project(self, tmp_path):
        """Test no nesting detected in normal user project"""
        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch"])

            assert result.is_nested is False
            assert result.in_source_repo is False
            assert result.parent_session_id is None
            assert result.requires_staging is False

    def test_nested_when_active_session_exists(self, tmp_path):
        """Test nesting detected when active session exists"""
        sessions_log = tmp_path / "sessions.jsonl"

        # Create active session
        entry = {
            "pid": os.getpid(),
            "session_id": "parent-123",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "active",
            "end_time": None,
        }
        sessions_log.write_text(json.dumps(entry) + "\n")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch", "--auto"])

            assert result.is_nested is True
            assert result.parent_session_id == "parent-123"
            assert result.active_session is not None

    def test_in_source_repo_detected(self, tmp_path):
        """Test in_source_repo flag set when running in amplihack source"""
        # Create amplihack pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "amplihack"')

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch"])

            assert result.in_source_repo is True

    def test_requires_staging_in_auto_mode(self, tmp_path):
        """Test requires_staging=True when auto-mode is used (regardless of nesting)"""
        # No active session needed - just test auto-mode flag
        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch", "--auto"])

            # Auto-mode ALWAYS requires staging
            assert result.requires_staging is True

    def test_no_staging_when_only_nested(self, tmp_path):
        """Test requires_staging=False when nested but NO auto-mode flag"""
        # Create active session (nested)
        sessions_log = tmp_path / "sessions.jsonl"
        entry = {
            "pid": os.getpid(),
            "session_id": "parent-123",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "active",
            "end_time": None,
        }
        sessions_log.write_text(json.dumps(entry) + "\n")

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            # No --auto flag means interactive mode (no staging)
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch"])

            assert result.is_nested is True
            assert result.in_source_repo is False
            # No auto-mode = no staging (interactive mode prompts user)
            assert result.requires_staging is False

    def test_requires_staging_any_repo_in_auto_mode(self, tmp_path):
        """Test requires_staging=True in ANY repo when auto-mode is used"""
        # Create normal user project (not amplihack source)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "user-app"\nversion = "1.0.0"')

        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            # Auto-mode in normal user repo
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch", "--auto"])

            # Not nested, not in source repo, but auto-mode = staging required
            assert result.is_nested is False
            assert result.in_source_repo is False
            assert result.requires_staging is True


# E2E TESTS (10%)
class TestNestingDetectorE2E:
    """Test end-to-end nesting scenarios"""

    def test_real_world_auto_mode_in_source_repo(self, tmp_path):
        """Test realistic scenario: user runs auto-mode in amplihack repo"""
        # Setup: amplihack source repo
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "amplihack"\nversion = "0.9.0"')

        # User has active amplihack session
        sessions_log = tmp_path / "sessions.jsonl"
        parent_entry = {
            "pid": os.getpid(),
            "session_id": "dev-session-001",
            "launch_dir": str(tmp_path),
            "argv": ["amplihack", "launch"],
            "start_time": 1234567890.0,
            "is_auto_mode": False,
            "is_nested": False,
            "parent_session_id": None,
            "status": "active",
            "end_time": None,
        }
        sessions_log.write_text(json.dumps(parent_entry) + "\n")

        # User runs auto-mode (self-modification risk!)
        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", sessions_log):
            result = detector.detect_nesting(
                tmp_path, ["amplihack", "launch", "--auto", "--", "-p", "test prompt"]
            )

            # Should detect all three conditions
            assert result.is_nested is True
            assert result.in_source_repo is True
            assert result.requires_staging is True
            assert result.parent_session_id == "dev-session-001"

    def test_normal_user_project_workflow(self, tmp_path):
        """Test normal workflow: user project, no nesting"""
        # Setup: user project (not amplihack source)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "my-app"\nversion = "1.0.0"')

        # No active sessions
        detector = NestingDetector()

        with patch.object(detector, "RUNTIME_LOG", tmp_path / "sessions.jsonl"):
            result = detector.detect_nesting(tmp_path, ["amplihack", "launch"])

            # Should be completely clean
            assert result.is_nested is False
            assert result.in_source_repo is False
            assert result.requires_staging is False
            assert result.parent_session_id is None
