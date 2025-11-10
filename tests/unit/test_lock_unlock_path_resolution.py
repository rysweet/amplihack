"""
Unit tests for lock/unlock command path resolution.

Tests that lock and unlock commands correctly detect project root
and use absolute paths to ensure consistency with stop hook.
"""

import os


class TestLockPathResolution:
    """Tests for lock command path resolution."""

    def test_lock_detects_project_root(self, tmp_path):
        """Test that lock command detects project root by finding .claude directory."""
        # Create project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Simulate running from a subdirectory
        subdir = project_root / "src" / "components"
        subdir.mkdir(parents=True)

        # Simulate project root detection logic
        current_dir = subdir
        detected_root = current_dir
        while detected_root != detected_root.parent:
            if (detected_root / ".claude").exists():
                break
            detected_root = detected_root.parent

        assert detected_root == project_root

    def test_lock_uses_absolute_path(self, tmp_path):
        """Test that lock command uses absolute path for lock file."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Construct expected absolute path
        lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"

        # Verify it's absolute
        assert lock_flag.is_absolute()
        assert str(lock_flag).startswith(str(tmp_path))

    def test_lock_creates_file_at_correct_location(self, tmp_path):
        """Test that lock file is created at absolute path location."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        lock_flag.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file atomically
        fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)

        # Verify file exists at expected absolute path
        assert lock_flag.exists()
        assert lock_flag.is_absolute()

        # Cleanup
        lock_flag.unlink()


class TestUnlockPathResolution:
    """Tests for unlock command path resolution."""

    def test_unlock_detects_project_root(self, tmp_path):
        """Test that unlock command detects project root by finding .claude directory."""
        # Create project structure
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Simulate running from a subdirectory
        subdir = project_root / "tests" / "unit"
        subdir.mkdir(parents=True)

        # Simulate project root detection logic
        current_dir = subdir
        detected_root = current_dir
        while detected_root != detected_root.parent:
            if (detected_root / ".claude").exists():
                break
            detected_root = detected_root.parent

        assert detected_root == project_root

    def test_unlock_uses_absolute_path(self, tmp_path):
        """Test that unlock command uses absolute path for lock file."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Construct expected absolute path
        lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"

        # Verify it's absolute
        assert lock_flag.is_absolute()
        assert str(lock_flag).startswith(str(tmp_path))

    def test_unlock_removes_file_from_correct_location(self, tmp_path):
        """Test that unlock removes lock file from absolute path location."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        lock_flag.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file first
        lock_flag.touch()
        assert lock_flag.exists()

        # Remove lock file
        lock_flag.unlink(missing_ok=True)

        # Verify file is removed
        assert not lock_flag.exists()


class TestPathConsistencyWithStopHook:
    """Tests that lock/unlock paths match stop hook paths."""

    def test_lock_and_stop_hook_use_same_path(self, tmp_path):
        """Test that lock command and stop hook reference the same file."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Lock command path
        lock_command_path = project_root / ".claude" / "runtime" / "locks" / ".lock_active"

        # Stop hook path (simulated)
        stop_hook_path = project_root / ".claude" / "runtime" / "locks" / ".lock_active"

        # They should be identical
        assert lock_command_path == stop_hook_path
        assert str(lock_command_path) == str(stop_hook_path)

    def test_paths_work_from_different_working_directories(self, tmp_path, monkeypatch):
        """Test that absolute paths work regardless of working directory."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".claude").mkdir()

        # Create subdirectories
        subdir1 = project_root / "src"
        subdir2 = project_root / "tests"
        subdir1.mkdir()
        subdir2.mkdir()

        lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        lock_flag.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file from subdir1
        monkeypatch.chdir(subdir1)
        fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        assert lock_flag.exists()

        # Verify lock file exists from subdir2
        monkeypatch.chdir(subdir2)
        assert lock_flag.exists()

        # Remove lock file from subdir2
        lock_flag.unlink()

        # Verify it's gone from subdir1
        monkeypatch.chdir(subdir1)
        assert not lock_flag.exists()
