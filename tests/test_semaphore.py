"""Unit tests for ReflectionLock semaphore."""

import json
import os

# Add path for imports
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "reflection")
)

from semaphore import ReflectionLock


@pytest.fixture
def temp_runtime_dir():
    """Create temporary runtime directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def lock(temp_runtime_dir):
    """Create ReflectionLock instance with temp directory."""
    return ReflectionLock(runtime_dir=temp_runtime_dir)


class TestLockAcquisition:
    """Tests for lock acquisition."""

    def test_lock_acquire_success_when_not_locked(self, lock):
        """Lock can be acquired when not locked."""
        result = lock.acquire(session_id="test-session", purpose="analysis")
        assert result is True
        assert lock.is_locked() is True

    def test_lock_acquire_fails_when_already_locked(self, lock):
        """Lock acquisition fails when already locked."""
        # First acquisition succeeds
        assert lock.acquire(session_id="session1", purpose="analysis") is True

        # Second acquisition fails
        assert lock.acquire(session_id="session2", purpose="analysis") is False

    def test_lock_acquire_different_sessions_blocked(self, lock):
        """Different sessions can't acquire lock simultaneously."""
        lock.acquire(session_id="session1", purpose="analysis")
        assert lock.acquire(session_id="session2", purpose="issue_creation") is False

    def test_lock_acquire_creates_lock_file(self, lock, temp_runtime_dir):
        """Lock acquisition creates lock file."""
        lock.acquire(session_id="test-session", purpose="analysis")
        lock_file = temp_runtime_dir / "reflection.lock"
        assert lock_file.exists()

    def test_lock_acquire_stores_lock_data(self, lock):
        """Lock data contains PID, timestamp, session_id, purpose."""
        lock.acquire(session_id="test-session", purpose="analysis")
        lock_data = lock.read_lock()

        assert lock_data is not None
        assert lock_data.pid == os.getpid()
        assert lock_data.session_id == "test-session"
        assert lock_data.purpose == "analysis"
        assert isinstance(lock_data.timestamp, float)
        assert lock_data.timestamp <= time.time()


class TestLockRelease:
    """Tests for lock release."""

    def test_lock_release_removes_lock_file(self, lock):
        """Lock can be released."""
        lock.acquire(session_id="test-session", purpose="analysis")
        assert lock.is_locked()

        lock.release()
        assert not lock.is_locked()

    def test_lock_release_allows_reacquisition(self, lock):
        """Lock can be reacquired after release."""
        lock.acquire(session_id="session1", purpose="analysis")
        lock.release()
        assert lock.acquire(session_id="session2", purpose="analysis") is True

    def test_lock_release_on_nonexistent_lock(self, lock):
        """Releasing nonexistent lock doesn't raise error."""
        lock.release()  # Should not raise exception

    def test_lock_release_handles_permission_error(self, lock):
        """Lock release handles permission errors gracefully."""
        lock.acquire(session_id="test-session", purpose="analysis")

        # Mock unlink to raise permission error
        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            lock.release()  # Should not raise exception


class TestStaleLockDetection:
    """Tests for stale lock detection and cleanup."""

    def test_lock_is_stale_after_timeout(self, lock):
        """Locks older than 60 seconds are stale."""
        lock.acquire(session_id="test-session", purpose="analysis")

        # Manually modify timestamp to be old
        lock_data = lock.read_lock()
        lock_data.timestamp = time.time() - 61  # 61 seconds old

        # Write modified data
        with open(lock.lock_file, "w") as f:
            json.dump(
                {
                    "pid": lock_data.pid,
                    "timestamp": lock_data.timestamp,
                    "session_id": lock_data.session_id,
                    "purpose": lock_data.purpose,
                },
                f,
            )

        assert lock.is_stale() is True

    def test_lock_is_not_stale_within_timeout(self, lock):
        """Fresh locks are not stale."""
        lock.acquire(session_id="test-session", purpose="analysis")
        assert lock.is_stale() is False

    def test_stale_lock_is_cleaned_up_on_acquire(self, lock):
        """Stale locks are cleaned up automatically."""
        # Create stale lock
        lock.acquire(session_id="old-session", purpose="analysis")
        lock_data = lock.read_lock()
        lock_data.timestamp = time.time() - 61

        with open(lock.lock_file, "w") as f:
            json.dump(
                {
                    "pid": lock_data.pid,
                    "timestamp": lock_data.timestamp,
                    "session_id": lock_data.session_id,
                    "purpose": lock_data.purpose,
                },
                f,
            )

        # New acquisition should succeed after cleanup
        assert lock.acquire(session_id="new-session", purpose="analysis") is True

    def test_nonexistent_lock_is_not_stale(self, lock):
        """Nonexistent lock returns False for is_stale."""
        assert lock.is_stale() is False


class TestLockFileCorruption:
    """Tests for corrupt lock file handling."""

    def test_corrupt_lock_file_treated_as_no_lock(self, lock, temp_runtime_dir):
        """Corrupt lock file is treated as no lock."""
        # Write invalid JSON
        lock_file = temp_runtime_dir / "reflection.lock"
        with open(lock_file, "w") as f:
            f.write("not valid json {{{")

        lock_data = lock.read_lock()
        assert lock_data is None

    def test_corrupt_lock_file_considered_stale(self, lock, temp_runtime_dir):
        """Corrupt lock file is considered stale."""
        # Write invalid JSON
        lock_file = temp_runtime_dir / "reflection.lock"
        with open(lock_file, "w") as f:
            f.write("corrupt data")

        assert lock.is_stale() is True

    def test_lock_file_with_missing_fields(self, lock, temp_runtime_dir):
        """Lock file with missing fields returns None."""
        lock_file = temp_runtime_dir / "reflection.lock"
        with open(lock_file, "w") as f:
            json.dump({"pid": 12345}, f)  # Missing fields

        lock_data = lock.read_lock()
        assert lock_data is None

    def test_lock_acquire_overwrites_corrupt_lock(self, lock, temp_runtime_dir):
        """Acquiring lock overwrites corrupt lock file."""
        # Create corrupt lock file
        lock_file = temp_runtime_dir / "reflection.lock"
        with open(lock_file, "w") as f:
            f.write("corrupt")

        # Should successfully acquire
        assert lock.acquire(session_id="test-session", purpose="analysis") is True
        assert lock.read_lock() is not None


class TestLockDataIntegrity:
    """Tests for lock data integrity."""

    def test_lock_data_contains_all_fields(self, lock):
        """Lock data contains all required fields."""
        lock.acquire(session_id="test-session", purpose="analysis")
        lock_data = lock.read_lock()

        assert hasattr(lock_data, "pid")
        assert hasattr(lock_data, "timestamp")
        assert hasattr(lock_data, "session_id")
        assert hasattr(lock_data, "purpose")

    def test_lock_data_purpose_variations(self, lock):
        """Lock data correctly stores different purposes."""
        purposes = ["analysis", "issue_creation", "starting_work"]

        for purpose in purposes:
            lock.acquire(session_id="test-session", purpose=purpose)
            lock_data = lock.read_lock()
            assert lock_data.purpose == purpose
            lock.release()

    def test_lock_data_timestamps_monotonic(self, lock):
        """Lock timestamps are monotonically increasing."""
        lock.acquire(session_id="session1", purpose="analysis")
        timestamp1 = lock.read_lock().timestamp
        lock.release()

        time.sleep(0.01)  # Small delay

        lock.acquire(session_id="session2", purpose="analysis")
        timestamp2 = lock.read_lock().timestamp

        assert timestamp2 > timestamp1


class TestConcurrentAccess:
    """Tests for concurrent lock access."""

    def test_is_locked_returns_true_when_locked(self, lock):
        """is_locked() returns True when lock is held."""
        lock.acquire(session_id="test-session", purpose="analysis")
        assert lock.is_locked() is True

    def test_is_locked_returns_false_when_not_locked(self, lock):
        """is_locked() returns False when no lock."""
        assert lock.is_locked() is False

    def test_lock_prevents_concurrent_operations(self, lock):
        """Lock prevents concurrent operations from different purposes."""
        lock.acquire(session_id="session1", purpose="analysis")

        # Try to acquire for different purpose
        assert lock.acquire(session_id="session1", purpose="issue_creation") is False


class TestLockTimeout:
    """Tests for lock timeout behavior."""

    def test_stale_timeout_is_configurable(self, temp_runtime_dir):
        """Stale timeout can be configured."""
        lock = ReflectionLock(runtime_dir=temp_runtime_dir)
        assert lock.stale_timeout == 60.0

        lock.stale_timeout = 120.0
        assert lock.stale_timeout == 120.0

    def test_custom_timeout_affects_staleness(self, temp_runtime_dir):
        """Custom timeout affects staleness detection."""
        lock = ReflectionLock(runtime_dir=temp_runtime_dir)
        lock.stale_timeout = 1.0  # 1 second timeout

        lock.acquire(session_id="test-session", purpose="analysis")
        assert not lock.is_stale()

        time.sleep(1.1)
        assert lock.is_stale()


class TestRuntimeDirDiscovery:
    """Tests for runtime directory discovery."""

    def test_runtime_dir_discovery_fails_without_claude_dir(self):
        """Raises ValueError when .claude directory not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary file structure without .claude directory
            test_file = Path(tmpdir) / "test.py"
            test_file.touch()

            # Mock __file__ to be in this temporary directory
            with patch.object(Path, "resolve", return_value=test_file):
                with pytest.raises(ValueError, match="Could not find .claude/runtime/ directory"):
                    ReflectionLock(runtime_dir=None)

    def test_explicit_runtime_dir_used_when_provided(self, temp_runtime_dir):
        """Explicit runtime_dir is used when provided."""
        lock = ReflectionLock(runtime_dir=temp_runtime_dir)
        assert lock.lock_file.parent == temp_runtime_dir
