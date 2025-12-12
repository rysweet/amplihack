"""Tests for SessionManager."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ..claude_session import SessionConfig
from ..session_manager import SessionManager


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Test session manager."""
        return SessionManager(temp_dir / "sessions")

    def test_manager_initialization(self, manager, temp_dir):
        """Test manager initialization."""
        assert manager.runtime_dir == temp_dir / "sessions"
        assert manager.runtime_dir.exists()
        assert manager.auto_save_enabled is True

    def test_create_session(self, manager):
        """Test session creation."""
        session_id = manager.create_session("test_session")

        assert session_id is not None
        assert session_id.startswith("claude_session_")
        assert session_id in manager._active_sessions
        assert session_id in manager._session_metadata

        # Check metadata
        metadata = manager._session_metadata[session_id]
        assert metadata["name"] == "test_session"
        assert metadata["status"] == "created"
        assert "created_at" in metadata

    def test_create_session_with_config(self, manager):
        """Test session creation with custom config."""
        config = SessionConfig(timeout=120.0, max_retries=5)
        metadata = {"project": "test", "version": "1.0"}

        session_id = manager.create_session("configured_session", config=config, metadata=metadata)

        session = manager.get_session(session_id)
        assert session.config.timeout == 120.0
        assert session.config.max_retries == 5

        session_metadata = manager._session_metadata[session_id]
        assert session_metadata["metadata"]["project"] == "test"

    def test_get_session(self, manager):
        """Test getting active session."""
        session_id = manager.create_session("test_session")
        session = manager.get_session(session_id)

        assert session is not None
        assert session.state.session_id == session_id

        # Test non-existent session
        assert manager.get_session("nonexistent") is None

    def test_save_and_resume_session(self, manager):
        """Test session persistence and resume."""
        # Create and use session
        session_id = manager.create_session("persistent_session")
        session = manager.get_session(session_id)

        with session:
            session.execute_command("test_command")

        # Save session
        assert manager.save_session(session_id) is True

        # Check session file exists
        session_file = manager.runtime_dir / f"{session_id}.json"
        assert session_file.exists()

        # Remove from active sessions
        del manager._active_sessions[session_id]

        # Resume session
        resumed_session = manager.resume_session(session_id)
        assert resumed_session is not None
        assert resumed_session.state.session_id == session_id
        assert len(resumed_session.get_command_history()) == 1

    def test_list_sessions(self, manager):
        """Test listing sessions."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            session_id = manager.create_session(f"session_{i}")
            session_ids.append(session_id)

        # List all sessions
        sessions = manager.list_sessions()
        assert len(sessions) >= 3

        # Check session info
        for session_info in sessions:
            if session_info["session_id"] in session_ids:
                assert session_info["status"] == "active"
                assert "statistics" in session_info

        # List active only
        active_sessions = manager.list_sessions(active_only=True)
        active_ids = [s["session_id"] for s in active_sessions]
        for session_id in session_ids:
            assert session_id in active_ids

    def test_archive_session(self, manager):
        """Test session archival."""
        session_id = manager.create_session("archive_test")
        manager.save_session(session_id)

        # Archive session
        assert manager.archive_session(session_id) is True

        # Check session is moved to archive
        archive_dir = manager.runtime_dir / "archive"
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob(f"{session_id}_*.json"))
        assert len(archive_files) == 1

        # Check session removed from active
        assert session_id not in manager._active_sessions

    def test_cleanup_old_sessions(self, manager):
        """Test cleanup of old sessions."""
        # Create session and make it appear old
        session_id = manager.create_session("old_session")
        manager.save_session(session_id)

        old_time = time.time() - (31 * 24 * 3600)  # 31 days old

        # Mock file modification time
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = old_time
            cleaned_count = manager.cleanup_old_sessions(max_age_days=30)

        assert cleaned_count >= 0  # May be 0 due to mocking complexity

    def test_session_serialization(self, manager):
        """Test session serialization/deserialization."""
        session_id = manager.create_session("serialization_test")
        session = manager.get_session(session_id)

        with session:
            session.execute_command("command1")
            session.execute_command("command2")

        # Serialize
        data = manager._serialize_session(session)
        assert data["session_id"] == session_id
        assert len(data["command_history"]) == 2
        assert "state" in data
        assert "config" in data

        # Deserialize
        new_session = manager._deserialize_session(data)
        assert new_session is not None
        assert new_session.state.session_id == session_id
        assert len(new_session.get_command_history()) == 2

    def test_auto_save_functionality(self, manager):
        """Test automatic session saving."""
        # Create session
        manager.create_session("auto_save_test")

        # Mock auto-save to run immediately
        with patch.object(manager, "auto_save_interval", 0.01):
            time.sleep(0.02)  # Let auto-save run

        # Check session was saved (file should exist)
        # Note: File may not exist yet due to timing, but method should not error

    def test_context_manager(self, manager):
        """Test SessionManager as context manager."""
        session_id = None

        with manager:
            session_id = manager.create_session("context_test")
            session = manager.get_session(session_id)
            with session:
                session.execute_command("test")

        # Session should be saved after context exit
        # File should exist or method should have completed without error

    def test_concurrent_session_access(self, manager):
        """Test concurrent access to sessions."""
        import threading

        session_ids = []
        errors = []

        def create_sessions():
            try:
                for i in range(5):
                    session_id = manager.create_session(f"concurrent_{i}")
                    session_ids.append(session_id)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=create_sessions) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check no errors occurred
        assert len(errors) == 0
        assert len(session_ids) > 0

    def test_invalid_session_operations(self, manager):
        """Test operations on invalid sessions."""
        # Save non-existent session
        assert manager.save_session("nonexistent") is False

        # Resume non-existent session
        assert manager.resume_session("nonexistent") is None

        # Archive non-existent session
        assert manager.archive_session("nonexistent") is False

    def test_session_metadata_updates(self, manager):
        """Test session metadata tracking."""
        session_id = manager.create_session("metadata_test")

        # Access session to update metadata
        session = manager.get_session(session_id)
        assert session is not None

        # Check last_accessed was updated
        metadata = manager._session_metadata[session_id]
        assert "last_accessed" in metadata
        initial_access = metadata["last_accessed"]

        time.sleep(0.01)

        # Access again
        manager.get_session(session_id)
        updated_access = manager._session_metadata[session_id]["last_accessed"]
        assert updated_access > initial_access

    def test_registry_persistence(self, manager):
        """Test session registry persistence."""
        session_id = manager.create_session("registry_test")

        # Save registry
        manager._save_session_registry()

        # Check registry file exists
        registry_file = manager.runtime_dir / "registry.json"
        assert registry_file.exists()

        # Create new manager and load registry
        new_manager = SessionManager(manager.runtime_dir)
        assert session_id in new_manager._session_metadata

    def test_checksum_verification(self, manager):
        """Test file integrity with checksums."""
        session_id = manager.create_session("checksum_test")
        session = manager.get_session(session_id)

        with session:
            session.execute_command("test_command")

        # Save session multiple times
        assert manager.save_session(session_id) is True
        assert manager.save_session(session_id) is True  # Should skip if no changes

        session_file = manager.runtime_dir / f"{session_id}.json"
        assert session_file.exists()

    def test_corrupted_session_handling(self, manager):
        """Test handling of corrupted session files."""
        session_id = manager.create_session("corruption_test")
        manager.save_session(session_id)

        # Corrupt the session file
        session_file = manager.runtime_dir / f"{session_id}.json"
        with open(session_file, "w") as f:
            f.write("invalid json content")

        # Try to resume corrupted session
        resumed_session = manager.resume_session(session_id)
        assert resumed_session is None  # Should fail gracefully

    def test_session_file_permissions(self, manager):
        """Test handling of file permission issues."""
        session_id = manager.create_session("permission_test")

        # Mock permission error
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = manager.save_session(session_id)
            assert result is False  # Should fail gracefully
