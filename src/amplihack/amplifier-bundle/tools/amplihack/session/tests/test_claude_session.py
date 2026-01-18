"""Tests for ClaudeSession wrapper."""

import time
from unittest.mock import patch

import pytest

from ..claude_session import ClaudeSession, SessionConfig, SessionError, SessionState, TimeoutError


class TestSessionConfig:
    """Test SessionConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SessionConfig()
        assert config.timeout == 300.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.heartbeat_interval == 30.0
        assert config.enable_logging is True
        assert config.log_level == "INFO"
        assert config.session_id is None
        assert config.auto_save_interval == 60.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SessionConfig(timeout=120.0, max_retries=5, session_id="test_session")
        assert config.timeout == 120.0
        assert config.max_retries == 5
        assert config.session_id == "test_session"


class TestSessionState:
    """Test SessionState dataclass."""

    def test_default_state(self):
        """Test default state values."""
        state = SessionState("test_session")
        assert state.session_id == "test_session"
        assert state.is_active is True
        assert state.command_count == 0
        assert state.error_count == 0
        assert state.last_error is None
        assert isinstance(state.metadata, dict)

    def test_state_tracking(self):
        """Test state value tracking."""
        state = SessionState("test_session")
        state.command_count = 5
        state.error_count = 1
        state.last_error = "Test error"

        assert state.command_count == 5
        assert state.error_count == 1
        assert state.last_error == "Test error"


class TestClaudeSession:
    """Test ClaudeSession functionality."""

    @pytest.fixture
    def config(self):
        """Test configuration."""
        return SessionConfig(timeout=5.0, heartbeat_interval=0.1, enable_logging=False)

    @pytest.fixture
    def session(self, config):
        """Test session instance."""
        return ClaudeSession(config)

    def test_session_initialization(self, session):
        """Test session initialization."""
        assert session.config.timeout == 5.0
        assert session.state.is_active is False  # Not started yet
        assert session.state.command_count == 0
        assert session.state.session_id.startswith("claude_session_")

    def test_session_start_stop(self, session):
        """Test session lifecycle."""
        # Test start
        session.start()
        assert session.state.is_active is True
        assert session.state.start_time > 0

        # Test stop
        session.stop()
        assert session.state.is_active is False

    def test_context_manager(self, session):
        """Test context manager functionality."""
        with session:
            assert session.state.is_active is True
        assert session.state.is_active is False

    def test_command_execution(self, session):
        """Test command execution."""
        with session:
            result = session.execute_command("test_command", arg1="value1")

            assert result is not None
            assert result["command"] == "test_command"
            assert result["status"] == "completed"
            assert session.state.command_count == 1

    def test_command_timeout(self, session):
        """Test command timeout handling."""
        # Mock a slow command
        with patch.object(session, "_simulate_command_execution") as mock_exec:
            mock_exec.side_effect = lambda *args, **kwargs: time.sleep(10)

            with session, pytest.raises(TimeoutError):
                session.execute_command("slow_command", timeout=0.1)

    def test_command_error_handling(self, session):
        """Test command error handling."""
        # Mock a failing command
        with patch.object(session, "_simulate_command_execution") as mock_exec:
            mock_exec.side_effect = RuntimeError("Test error")

            with session:
                with pytest.raises(RuntimeError):
                    session.execute_command("failing_command")

                assert session.state.error_count == 1
                assert session.state.last_error == "Test error"

    def test_inactive_session_error(self, session):
        """Test error when session is not active."""
        with pytest.raises(SessionError):
            session.execute_command("test_command")

    def test_command_history(self, session):
        """Test command history tracking."""
        with session:
            session.execute_command("command1")
            session.execute_command("command2")

            history = session.get_command_history()
            assert len(history) == 2
            assert history[0]["command"] == "command1"
            assert history[1]["command"] == "command2"

    def test_checkpoints(self, session):
        """Test checkpoint functionality."""
        with session:
            session.execute_command("command1")
            session.save_checkpoint()

            session.execute_command("command2")
            assert session.state.command_count == 2

            # Restore checkpoint
            session.restore_checkpoint()
            assert session.state.command_count == 1

    def test_statistics(self, session):
        """Test session statistics."""
        with session:
            stats = session.get_statistics()

            assert "session_id" in stats
            assert "uptime" in stats
            assert "command_count" in stats
            assert "error_count" in stats
            assert "is_active" in stats
            assert stats["is_active"] is True

    def test_heartbeat_monitoring(self, config):
        """Test heartbeat monitoring."""
        config.heartbeat_interval = 0.01  # Very fast for testing
        session = ClaudeSession(config)

        with session:
            # Let heartbeat run a few times
            time.sleep(0.05)
            assert session.state.is_active is True

    def test_session_timeout_detection(self, config):
        """Test session timeout detection."""
        config.timeout = 0.01  # Very short timeout
        config.heartbeat_interval = 0.005  # Fast heartbeat
        session = ClaudeSession(config)

        with session:
            # Simulate inactivity
            session.state.last_activity = time.time() - 0.02
            time.sleep(0.01)  # Let heartbeat detect timeout

            # Timeout should be detected
            assert session.state.last_error is not None
            assert "timeout" in session.state.last_error.lower()

    def test_clear_history(self, session):
        """Test clearing session history."""
        with session:
            session.execute_command("command1")
            session.save_checkpoint()

            assert len(session.get_command_history()) == 1
            assert len(session._checkpoints) == 1

            session.clear_history()
            assert len(session.get_command_history()) == 0
            assert len(session._checkpoints) == 0

    def test_activity_update(self, session):
        """Test activity timestamp updates."""
        with session:
            initial_activity = session.state.last_activity
            time.sleep(0.01)

            session.execute_command("test")
            assert session.state.last_activity > initial_activity

    def test_multiple_checkpoints(self, session):
        """Test multiple checkpoints."""
        with session:
            # Create multiple checkpoints
            for i in range(3):
                session.execute_command(f"command{i}")
                session.save_checkpoint()

            assert len(session._checkpoints) == 3
            assert session.state.command_count == 3

            # Restore different checkpoints
            session.restore_checkpoint(-2)  # Second to last
            assert session.state.command_count == 2

            session.restore_checkpoint(0)  # First
            assert session.state.command_count == 1

    def test_session_id_generation(self):
        """Test unique session ID generation."""
        session1 = ClaudeSession()
        session2 = ClaudeSession()

        assert session1.state.session_id != session2.state.session_id
        assert session1.state.session_id.startswith("claude_session_")
        assert session2.state.session_id.startswith("claude_session_")

    def test_custom_session_id(self):
        """Test custom session ID."""
        config = SessionConfig(session_id="custom_session_123")
        session = ClaudeSession(config)

        assert session.state.session_id == "custom_session_123"
