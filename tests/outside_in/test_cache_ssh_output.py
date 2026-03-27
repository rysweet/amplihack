"""Outside-in tests for SSH output caching between discovery and reasoning phases.

Tests that SSH commands are cached so repeated calls within the TTL window
return the cached result without re-running the SSH command.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the amplifier-bundle tools to the path so we can import directly
_tools_dir = Path(__file__).resolve().parents[2] / "amplifier-bundle" / "tools"
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from amplihack.remote.session import SessionManager


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "remote-state.json"


@pytest.fixture
def manager(state_file):
    return SessionManager(state_file=state_file, ssh_cache_ttl=30.0)


@pytest.fixture
def running_session(manager):
    session = manager.create_session(vm_name="test-vm", prompt="test task")
    archive = Path(tempfile.mktemp(suffix=".tar.gz"))
    archive.touch()
    manager.start_session(session.session_id, archive)
    return session


class TestSSHCacheDefaultConfiguration:
    """SSH cache is initialized with sensible defaults."""

    def test_default_ttl_is_thirty_seconds(self):
        assert SessionManager.SSH_CACHE_TTL == 30.0

    def test_cache_starts_empty(self, manager):
        assert manager._ssh_cache == {}

    def test_custom_ttl_is_respected(self, state_file):
        m = SessionManager(state_file=state_file, ssh_cache_ttl=5.0)
        assert m._ssh_cache_ttl == 5.0

    def test_default_ttl_used_when_not_specified(self, state_file):
        m = SessionManager(state_file=state_file)
        assert m._ssh_cache_ttl == SessionManager.SSH_CACHE_TTL


class TestSSHCacheHit:
    """Second SSH call within TTL reuses cached output."""

    def test_second_capture_does_not_call_ssh_again(self, manager, running_session):
        with patch.object(
            manager, "_execute_ssh_command", wraps=manager._execute_ssh_command
        ) as mock_exec:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="tmux output line 1\nline 2\n")

                # First call — discovery phase
                output1 = manager.capture_output(running_session.session_id)
                # Second call — reasoning phase
                output2 = manager.capture_output(running_session.session_id)

        # SSH (subprocess.run) should only have been called once
        assert mock_run.call_count == 1
        assert output1 == output2 == "tmux output line 1\nline 2\n"

    def test_cached_output_matches_original(self, manager, running_session):
        expected = "Session output: task running\nStep 2 complete\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=expected)

            first = manager.capture_output(running_session.session_id)
            second = manager.capture_output(running_session.session_id)

        assert first == expected
        assert second == expected

    def test_different_sessions_cached_independently(self, manager):
        # Create two sessions on different VMs
        s1 = manager.create_session(vm_name="vm-alpha", prompt="task 1")
        s2 = manager.create_session(vm_name="vm-beta", prompt="task 2")
        archive = Path(tempfile.mktemp(suffix=".tar.gz"))
        archive.touch()
        manager.start_session(s1.session_id, archive)
        manager.start_session(s2.session_id, archive)

        call_count = 0

        def ssh_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(stdout=f"output from call {call_count}\n")

        with patch("subprocess.run", side_effect=ssh_side_effect):
            out1a = manager.capture_output(s1.session_id)
            out1b = manager.capture_output(s1.session_id)  # cache hit
            out2a = manager.capture_output(s2.session_id)
            out2b = manager.capture_output(s2.session_id)  # cache hit

        # Each VM gets one SSH call; second calls are served from cache
        assert call_count == 2
        assert out1a == out1b
        assert out2a == out2b
        assert out1a != out2a  # different VMs produce different output


class TestSSHCacheMiss:
    """Cache miss triggers a fresh SSH call."""

    def test_expired_cache_triggers_new_ssh_call(self, state_file, running_session):
        import time

        manager = SessionManager(state_file=state_file, ssh_cache_ttl=0.01)
        # Re-load the session by reusing the same state file
        manager2 = SessionManager(state_file=state_file, ssh_cache_ttl=0.01)
        session = manager2.create_session(vm_name="test-vm", prompt="task")
        archive = Path(tempfile.mktemp(suffix=".tar.gz"))
        archive.touch()
        manager2.start_session(session.session_id, archive)

        call_count = 0

        def ssh_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(stdout=f"call {call_count}\n")

        with patch("subprocess.run", side_effect=ssh_side_effect):
            manager2.capture_output(session.session_id)
            time.sleep(0.05)  # Wait for TTL to expire
            manager2.capture_output(session.session_id)

        assert call_count == 2

    def test_different_line_count_bypasses_cache(self, manager, running_session):
        """Different 'lines' parameter means a different SSH command — no cache sharing."""
        call_count = 0

        def ssh_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(stdout=f"call {call_count}\n")

        with patch("subprocess.run", side_effect=ssh_side_effect):
            manager.capture_output(running_session.session_id, lines=50)
            manager.capture_output(running_session.session_id, lines=200)

        # Different commands → 2 SSH calls (no cache reuse)
        assert call_count == 2

    def test_no_ssh_for_nonexistent_session(self, manager):
        """Missing session returns empty string without any SSH call."""
        with patch("subprocess.run") as mock_run:
            result = manager.capture_output("nonexistent-session-id")

        assert result == ""
        mock_run.assert_not_called()


class TestSSHCacheIntegrity:
    """Cache stores and retrieves correct data."""

    def test_cache_is_populated_after_first_call(self, manager, running_session):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="hello\n")
            manager.capture_output(running_session.session_id)

        assert len(manager._ssh_cache) == 1

    def test_cache_key_includes_vm_and_command(self, manager, running_session):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="hello\n")
            manager.capture_output(running_session.session_id)

        key = list(manager._ssh_cache.keys())[0]
        assert key[0] == "test-vm"
        assert "tmux capture-pane" in key[1]
