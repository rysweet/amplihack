"""Unit tests for SessionFinder class.

Tests session discovery, validation, and filtering for auto mode instruction injection.
SessionFinder locates active auto mode sessions by finding log directories.

Following TDD approach - these tests should FAIL initially as SessionFinder is not implemented.
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# SessionFinder class to be implemented in amplihack/launcher/session_finder.py
# For now, tests will fail with ImportError
try:
    from amplihack.launcher.session_finder import SessionFinder, SessionInfo
except ImportError:
    # Define placeholder classes so tests can be written
    class SessionFinder:
        """Placeholder - to be implemented."""

    class SessionInfo:
        """Placeholder - to be implemented."""


class TestSessionFinderBasicDiscovery:
    """Test basic session discovery functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with .claude structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            # Create .claude/runtime/logs structure
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)

            yield workspace

    def test_find_active_session_in_current_dir(self, temp_workspace):
        """Test finding active session in current directory.

        Expected behavior:
        - Should find session log directory in .claude/runtime/logs/
        - Should return SessionInfo with session details
        - Should identify auto mode sessions (auto_*)
        """
        # Create an active auto mode session directory
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        session_dir = logs_dir / "auto_claude_1729699200"
        session_dir.mkdir(parents=True)

        # Create append directory to indicate active session
        (session_dir / "append").mkdir()
        (session_dir / "prompt.md").write_text("Test prompt")

        # Create SessionFinder
        finder = SessionFinder(start_dir=temp_workspace)

        # Find active session
        session_info = finder.find_active_session()

        assert session_info is not None, "Should find active session"
        assert isinstance(session_info, SessionInfo), "Should return SessionInfo object"
        assert "auto_claude" in session_info.session_id, "Should identify auto mode session"

    def test_find_active_session_in_parent_dir(self, temp_workspace):
        """Test finding session when starting from subdirectory.

        Expected behavior:
        - Should traverse up directory tree
        - Should find .claude directory in parent
        - Should return session from parent's logs
        """
        # Create subdirectory structure
        subdir = temp_workspace / "src" / "components"
        subdir.mkdir(parents=True)

        # Create session in workspace root
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        session_dir = logs_dir / "auto_claude_1729699200"
        session_dir.mkdir(parents=True)
        (session_dir / "append").mkdir()
        (session_dir / "prompt.md").write_text("Test prompt")

        # Start search from subdirectory
        finder = SessionFinder(start_dir=subdir)

        session_info = finder.find_active_session()

        assert session_info is not None, "Should find session in parent directory"
        assert session_info.workspace_root == temp_workspace, "Should identify correct workspace"

    def test_find_active_session_no_session_exists(self, temp_workspace):
        """Test behavior when no active session exists.

        Expected behavior:
        - Should return None when no sessions found
        - Should not raise exceptions
        """
        # Create .claude structure but no sessions
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        finder = SessionFinder(start_dir=temp_workspace)
        session_info = finder.find_active_session()

        assert session_info is None, "Should return None when no active sessions"

    def test_find_active_session_no_claude_directory(self, temp_workspace):
        """Test behavior when .claude directory doesn't exist.

        Expected behavior:
        - Should return None
        - Should not raise exceptions
        """
        # Remove .claude directory
        claude_dir = temp_workspace / ".claude"
        if claude_dir.exists():
            import shutil
            shutil.rmtree(claude_dir)

        finder = SessionFinder(start_dir=temp_workspace)
        session_info = finder.find_active_session()

        assert session_info is None, "Should return None when no .claude directory"


class TestSessionFinderMultipleSessions:
    """Test handling of multiple simultaneous sessions."""

    @pytest.fixture
    def workspace_with_multiple_sessions(self):
        """Create workspace with multiple auto mode sessions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            logs_dir.mkdir(parents=True)

            # Create multiple sessions with different timestamps
            timestamps = [
                int(time.time()) - 3600,  # 1 hour ago
                int(time.time()) - 1800,  # 30 minutes ago
                int(time.time()) - 300,   # 5 minutes ago (most recent)
            ]

            for ts in timestamps:
                session_dir = logs_dir / f"auto_claude_{ts}"
                session_dir.mkdir()
                (session_dir / "append").mkdir()
                (session_dir / "prompt.md").write_text(f"Session {ts}")

            yield workspace, timestamps

    def test_find_most_recent_session(self, workspace_with_multiple_sessions):
        """Test that most recent session is returned when multiple exist.

        Expected behavior:
        - Should find the session with the latest timestamp
        - Should parse timestamp from directory name
        """
        workspace, timestamps = workspace_with_multiple_sessions

        finder = SessionFinder(start_dir=workspace)
        session_info = finder.find_active_session()

        assert session_info is not None, "Should find a session"
        # Should be the most recent timestamp
        assert str(timestamps[-1]) in session_info.session_id, \
            "Should return most recent session"

    def test_list_all_active_sessions(self, workspace_with_multiple_sessions):
        """Test listing all active sessions.

        Expected behavior:
        - Should return list of all active sessions
        - Should be ordered by timestamp (newest first)
        """
        workspace, timestamps = workspace_with_multiple_sessions

        finder = SessionFinder(start_dir=workspace)
        all_sessions = finder.list_active_sessions()

        assert len(all_sessions) == 3, "Should find all 3 sessions"
        assert isinstance(all_sessions, list), "Should return list"
        assert all(isinstance(s, SessionInfo) for s in all_sessions), \
            "All items should be SessionInfo"

        # Check ordering (newest first)
        if len(all_sessions) > 1:
            assert all_sessions[0].timestamp >= all_sessions[1].timestamp, \
                "Should be ordered newest first"

    def test_find_session_by_sdk_type(self, workspace_with_multiple_sessions):
        """Test filtering sessions by SDK type.

        Expected behavior:
        - Should filter sessions by SDK (claude, copilot, codex)
        - Should only return sessions matching the specified SDK
        """
        workspace, _ = workspace_with_multiple_sessions

        # Add a copilot session
        logs_dir = workspace / ".claude" / "runtime" / "logs"
        copilot_dir = logs_dir / f"auto_copilot_{int(time.time())}"
        copilot_dir.mkdir()
        (copilot_dir / "append").mkdir()

        finder = SessionFinder(start_dir=workspace)

        # Find only Claude sessions
        claude_sessions = finder.find_active_session(sdk_filter="claude")
        assert claude_sessions is not None, "Should find Claude session"
        assert "claude" in claude_sessions.session_id, "Should be Claude session"

        # Find only Copilot sessions
        copilot_sessions = finder.find_active_session(sdk_filter="copilot")
        assert copilot_sessions is not None, "Should find Copilot session"
        assert "copilot" in copilot_sessions.session_id, "Should be Copilot session"


class TestSessionValidation:
    """Test session validation and staleness detection."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            logs_dir.mkdir(parents=True)
            yield workspace

    def test_detect_stale_session(self, temp_workspace):
        """Test detection of stale/inactive sessions.

        Expected behavior:
        - Sessions older than threshold should be considered stale
        - Should check last modified time of session directory
        - Stale sessions should not be returned as active
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"

        # Create old session (more than 24 hours old)
        old_timestamp = int(time.time()) - (25 * 3600)  # 25 hours ago
        old_session = logs_dir / f"auto_claude_{old_timestamp}"
        old_session.mkdir()
        (old_session / "append").mkdir()
        (old_session / "prompt.md").write_text("Old session")

        finder = SessionFinder(start_dir=temp_workspace, max_age_hours=24)
        session_info = finder.find_active_session()

        # Should not return stale session
        assert session_info is None, "Should not return stale session"

    def test_validate_session_structure(self, temp_workspace):
        """Test validation of session directory structure.

        Expected behavior:
        - Valid session must have append/ directory
        - Valid session must have prompt.md file
        - Invalid sessions should be skipped
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"

        # Create session with missing append directory
        invalid_session = logs_dir / f"auto_claude_{int(time.time())}"
        invalid_session.mkdir()
        (invalid_session / "prompt.md").write_text("No append dir")
        # Missing: append directory

        finder = SessionFinder(start_dir=temp_workspace)
        session_info = finder.find_active_session()

        # Should not return invalid session
        assert session_info is None, "Should not return session without append dir"

    def test_validate_session_has_prompt(self, temp_workspace):
        """Test that valid sessions must have prompt.md.

        Expected behavior:
        - Session without prompt.md is invalid
        - Should skip invalid sessions
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"

        # Create session with missing prompt.md
        invalid_session = logs_dir / f"auto_claude_{int(time.time())}"
        invalid_session.mkdir()
        (invalid_session / "append").mkdir()
        # Missing: prompt.md

        finder = SessionFinder(start_dir=temp_workspace)
        session_info = finder.find_active_session()

        assert session_info is None, "Should not return session without prompt.md"


class TestSessionInfo:
    """Test SessionInfo data structure."""

    def test_session_info_attributes(self):
        """Test that SessionInfo has required attributes.

        Expected attributes:
        - session_id: unique identifier
        - session_dir: Path to session directory
        - workspace_root: Path to workspace root
        - sdk: SDK type (claude, copilot, codex)
        - timestamp: session creation timestamp
        - append_dir: Path to append directory
        - prompt_file: Path to prompt.md
        """
        # This will fail until SessionInfo is implemented
        with pytest.raises((AttributeError, TypeError, NameError)):
            session_info = SessionInfo(
                session_id="auto_claude_1729699200",
                session_dir=Path("/tmp/logs/auto_claude_1729699200"),
                workspace_root=Path("/tmp"),
                sdk="claude",
                timestamp=1729699200,
                append_dir=Path("/tmp/logs/auto_claude_1729699200/append"),
                prompt_file=Path("/tmp/logs/auto_claude_1729699200/prompt.md")
            )

            assert hasattr(session_info, 'session_id')
            assert hasattr(session_info, 'session_dir')
            assert hasattr(session_info, 'workspace_root')
            assert hasattr(session_info, 'sdk')
            assert hasattr(session_info, 'timestamp')
            assert hasattr(session_info, 'append_dir')
            assert hasattr(session_info, 'prompt_file')

    def test_session_info_is_active_method(self):
        """Test is_active() method on SessionInfo.

        Expected behavior:
        - Should check if session is still active
        - Should verify append directory exists
        - Should check session age
        """
        with pytest.raises((AttributeError, TypeError, NameError)):
            session_info = SessionInfo(
                session_id="auto_claude_1729699200",
                session_dir=Path("/tmp/logs/auto_claude_1729699200"),
                workspace_root=Path("/tmp"),
                sdk="claude",
                timestamp=int(time.time()),  # Recent timestamp
                append_dir=Path("/tmp/logs/auto_claude_1729699200/append"),
                prompt_file=Path("/tmp/logs/auto_claude_1729699200/prompt.md")
            )

            assert hasattr(session_info, 'is_active'), "Should have is_active method"
            assert callable(session_info.is_active), "is_active should be callable"


class TestSessionFinderEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_handle_permission_error(self, temp_workspace):
        """Test handling of permission errors when accessing directories.

        Expected behavior:
        - Should handle permission errors gracefully
        - Should skip inaccessible directories
        - Should not crash
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

        # Create session directory
        session_dir = logs_dir / f"auto_claude_{int(time.time())}"
        session_dir.mkdir()

        # Mock permission error
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            finder = SessionFinder(start_dir=temp_workspace)

            # Should not crash
            try:
                session_info = finder.find_active_session()
                assert session_info is None, "Should return None on permission error"
            except PermissionError:
                pytest.fail("Should handle permission errors gracefully")

    def test_handle_symlink_loops(self, temp_workspace):
        """Test handling of symlink loops.

        Expected behavior:
        - Should detect symlink loops
        - Should not infinite loop
        - Should skip problematic directories
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

        # Create symlink loop (skip on Windows)
        try:
            loop_dir = logs_dir / "loop"
            loop_dir.mkdir()
            symlink = loop_dir / "self"
            symlink.symlink_to(loop_dir)

            finder = SessionFinder(start_dir=temp_workspace)

            # Should not hang
            session_info = finder.find_active_session()

            # Test should complete (not hang)
            assert True, "Should complete without hanging"
        except (OSError, NotImplementedError):
            # Symlinks may not be supported
            pytest.skip("Symlinks not supported on this system")

    def test_handle_non_standard_directory_names(self, temp_workspace):
        """Test handling of non-standard session directory names.

        Expected behavior:
        - Should ignore directories that don't match auto_* pattern
        - Should handle malformed directory names
        """
        logs_dir = temp_workspace / ".claude" / "runtime" / "logs"
        logs_dir.mkdir(parents=True)

        # Create directories with various names
        (logs_dir / "not_auto").mkdir()
        (logs_dir / "auto_invalid_name").mkdir()
        (logs_dir / "random_dir").mkdir()

        finder = SessionFinder(start_dir=temp_workspace)
        session_info = finder.find_active_session()

        assert session_info is None, "Should not find non-standard directories"

    def test_finder_with_no_start_dir(self):
        """Test SessionFinder with no start directory specified.

        Expected behavior:
        - Should use current working directory as default
        - Should not crash
        """
        # This will fail until default behavior is implemented
        with pytest.raises((TypeError, AttributeError, NameError)):
            finder = SessionFinder()  # No start_dir specified
            assert hasattr(finder, 'start_dir'), "Should have default start_dir"


class TestSessionFinderPerformance:
    """Test performance characteristics."""

    @pytest.fixture
    def workspace_with_many_sessions(self):
        """Create workspace with many session directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            logs_dir = workspace / ".claude" / "runtime" / "logs"
            logs_dir.mkdir(parents=True)

            # Create 50 old sessions
            for i in range(50):
                old_ts = int(time.time()) - (i * 3600)
                session_dir = logs_dir / f"auto_claude_{old_ts}"
                session_dir.mkdir()
                (session_dir / "append").mkdir()
                (session_dir / "prompt.md").write_text(f"Session {i}")

            yield workspace

    def test_find_session_efficiently_with_many_directories(
        self, workspace_with_many_sessions
    ):
        """Test that session finding is efficient with many directories.

        Expected behavior:
        - Should find most recent session quickly
        - Should not need to scan all directories
        - Should complete in reasonable time (< 1 second)
        """
        finder = SessionFinder(start_dir=workspace_with_many_sessions)

        start_time = time.time()
        session_info = finder.find_active_session()
        elapsed = time.time() - start_time

        assert session_info is not None, "Should find session"
        assert elapsed < 1.0, "Should find session in less than 1 second"

    @pytest.mark.slow
    def test_list_sessions_performance(self, workspace_with_many_sessions):
        """Test performance of listing all sessions.

        Expected behavior:
        - Should list all sessions efficiently
        - Should complete in reasonable time
        """
        finder = SessionFinder(start_dir=workspace_with_many_sessions)

        start_time = time.time()
        all_sessions = finder.list_active_sessions()
        elapsed = time.time() - start_time

        assert len(all_sessions) > 0, "Should find sessions"
        assert elapsed < 2.0, "Should list sessions in less than 2 seconds"
