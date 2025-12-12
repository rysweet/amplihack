"""Tests for state_lock module.

Tests file locking functionality for concurrent state management.
"""

import os
import threading
import time
from pathlib import Path

import pytest

from ..state_lock import file_lock


def test_file_lock_basic(tmp_path: Path):
    """Test basic file locking functionality."""
    lock_file = tmp_path / "test.lock"

    # Acquire lock
    with file_lock(lock_file):
        # Verify lock file was created
        assert lock_file.exists()

        # Verify secure permissions (owner read/write only)
        stat = os.stat(lock_file)
        assert stat.st_mode & 0o777 == 0o600

    # Lock should be released after context exit
    assert lock_file.exists()  # Lock file persists


def test_file_lock_prevents_concurrent_writes(tmp_path: Path):
    """Test that file lock prevents concurrent writes."""
    lock_file = tmp_path / "test.lock"
    test_file = tmp_path / "data.json"
    results = []

    def writer(name: str, delay: float):
        """Write to file with lock."""
        with file_lock(lock_file):
            # Read current value
            current = test_file.read_text() if test_file.exists() else ""

            # Simulate work
            time.sleep(delay)

            # Write new value
            test_file.write_text(current + name)
            results.append(name)

    # Start two threads that will try to write concurrently
    t1 = threading.Thread(target=writer, args=("A", 0.1))
    t2 = threading.Thread(target=writer, args=("B", 0.1))

    t1.start()
    time.sleep(0.01)  # Small delay to ensure t1 acquires lock first
    t2.start()

    t1.join(timeout=5)
    t2.join(timeout=5)

    # Both threads should complete
    assert len(results) == 2

    # File should contain both values (no corruption)
    content = test_file.read_text()
    assert "A" in content
    assert "B" in content
    assert len(content) == 2  # No interleaved writes


def test_file_lock_creates_parent_directory(tmp_path: Path):
    """Test that file lock creates parent directory if needed."""
    nested_path = tmp_path / "nested" / "dir" / "test.lock"

    with file_lock(nested_path):
        assert nested_path.exists()
        assert nested_path.parent.exists()


def test_file_lock_exception_releases_lock(tmp_path: Path):
    """Test that lock is released even if exception occurs."""
    lock_file = tmp_path / "test.lock"

    # Acquire lock and raise exception
    with pytest.raises(ValueError):
        with file_lock(lock_file):
            raise ValueError("Test error")

    # Lock file should exist but lock should be released
    assert lock_file.exists()

    # We should be able to acquire the lock again immediately
    acquired = False
    with file_lock(lock_file):
        acquired = True

    assert acquired


def test_file_lock_multiple_acquisitions_serial(tmp_path: Path):
    """Test multiple serial acquisitions of same lock."""
    lock_file = tmp_path / "test.lock"

    # First acquisition
    with file_lock(lock_file):
        pass

    # Second acquisition (should succeed immediately)
    with file_lock(lock_file):
        pass

    # Third acquisition
    with file_lock(lock_file):
        pass


def test_file_lock_secure_permissions_on_creation(tmp_path: Path):
    """Test that lock file is created with secure permissions."""
    lock_file = tmp_path / "test.lock"

    with file_lock(lock_file):
        # Check permissions immediately after creation
        stat = os.stat(lock_file)
        mode = stat.st_mode & 0o777

        # Should be 0o600 (owner read/write only)
        assert mode == 0o600


def test_file_lock_concurrent_blocking(tmp_path: Path):
    """Test that second lock acquisition blocks until first releases."""
    lock_file = tmp_path / "test.lock"
    events = []

    def holder(duration: float):
        """Hold lock for specified duration."""
        with file_lock(lock_file):
            events.append(("acquired", threading.current_thread().name))
            time.sleep(duration)
            events.append(("released", threading.current_thread().name))

    # Start first thread that holds lock for 0.2 seconds
    t1 = threading.Thread(target=holder, args=(0.2,), name="T1")
    t2 = threading.Thread(target=holder, args=(0.1,), name="T2")

    t1.start()
    time.sleep(0.05)  # Ensure T1 acquires first
    t2.start()

    t1.join(timeout=5)
    t2.join(timeout=5)

    # Should have 4 events: T1 acquire, T1 release, T2 acquire, T2 release
    assert len(events) == 4
    assert events[0] == ("acquired", "T1")
    assert events[1] == ("released", "T1")
    assert events[2] == ("acquired", "T2")
    assert events[3] == ("released", "T2")
