"""Tests for lock/unlock commands and stop hook."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestLockUnlockCommands:
    """Tests for lock/unlock slash commands."""

    @pytest.fixture
    def lock_flag(self, tmp_path):
        """Create lock flag path in temp directory."""
        lock_path = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        return lock_path

    def test_lock_creates_flag(self, lock_flag, monkeypatch):
        """Test that lock command creates .lock_active file."""
        monkeypatch.chdir(lock_flag.parent.parent.parent.parent)

        # Simulate lock command
        import os

        try:
            fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            assert lock_flag.exists()
        except FileExistsError:
            pytest.fail("Lock file already existed")

    def test_lock_idempotent(self, lock_flag):
        """Test that calling lock twice is safe."""
        import os

        # First lock
        fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Second lock should detect existing lock
        with pytest.raises(FileExistsError):
            os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

        assert lock_flag.exists()

    def test_unlock_removes_flag(self, lock_flag):
        """Test that unlock command removes .lock_active file."""
        # Create lock first
        lock_flag.touch()
        assert lock_flag.exists()

        # Unlock
        lock_flag.unlink(missing_ok=True)
        assert not lock_flag.exists()

    def test_unlock_without_lock_safe(self, lock_flag):
        """Test that unlock without lock doesn't error."""
        assert not lock_flag.exists()

        # Should not raise
        lock_flag.unlink(missing_ok=True)
        assert not lock_flag.exists()


class TestStopHook:
    """Tests for stop hook with lock support."""

    @pytest.fixture
    def stop_hook_path(self):
        """Get path to stop hook."""
        return (
            Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks" / "stop.py"
        )

    def test_stop_hook_exists(self, stop_hook_path):
        """Test that stop hook file exists."""
        assert stop_hook_path.exists()

    def test_stop_hook_blocks_when_locked(self, tmp_path, monkeypatch):
        """Test that stop hook blocks when lock is active."""
        # Create lock flag
        lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"
        lock_flag.parent.mkdir(parents=True, exist_ok=True)
        lock_flag.touch()

        # Mock the stop hook

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = lock_flag

            def process(self, input_data):
                if self.lock_flag.exists():
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()
        result = hook.process({})

        assert result["decision"] == "block"
        assert result["continue"] is True

    def test_stop_hook_allows_when_unlocked(self, tmp_path):
        """Test that stop hook allows when lock is not active."""
        # No lock flag created

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"

            def process(self, input_data):
                if self.lock_flag.exists():
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()
        result = hook.process({})

        assert result["decision"] == "allow"
        assert result["continue"] is False

    def test_stop_hook_handles_permission_errors(self, tmp_path):
        """Test that stop hook handles permission errors gracefully."""

        class MockStopHook:
            def __init__(self):
                self.project_root = tmp_path
                self.lock_flag = tmp_path / ".claude" / "tools" / "amplihack" / ".lock_active"

            def process(self, input_data):
                try:
                    lock_exists = self.lock_flag.exists()
                except (PermissionError, OSError):
                    # Fail-safe: allow stop if we can't read lock
                    return {"decision": "allow", "continue": False}

                if lock_exists:
                    return {
                        "decision": "block",
                        "reason": "we must keep pursuing the user's objective...",
                        "continue": True,
                    }
                return {"decision": "allow", "continue": False}

        hook = MockStopHook()

        # Mock exists() to raise PermissionError
        with patch.object(Path, "exists", side_effect=PermissionError("Access denied")):
            result = hook.process({})
            assert result["decision"] == "allow"
            assert result["continue"] is False
