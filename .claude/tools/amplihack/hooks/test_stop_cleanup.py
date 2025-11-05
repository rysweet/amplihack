#!/usr/bin/env python3
"""
Tests for automatic cleanup functionality in stop hook.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from stop import StopHook


class TestStopHookCleanup(unittest.TestCase):
    """Test cases for automatic cleanup in stop hook."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create necessary directories
        self.runtime_dir = self.project_root / ".claude" / "runtime"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.todo_dir = self.runtime_dir / "todos"
        self.todo_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_cleanup_config_defaults(self):
        """Test that default cleanup config is loaded correctly."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()

        config = hook._load_cleanup_config()

        # Verify defaults
        self.assertTrue(config["auto_cleanup_enabled"])
        self.assertTrue(config["cleanup_on_ultrathink"])
        self.assertTrue(config["cleanup_on_workflow"])

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_cleanup_config_user_override(self):
        """Test that user config overrides defaults."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()

        # Write user config
        user_config = {
            "auto_cleanup_enabled": False,
            "cleanup_on_ultrathink": False,
        }
        with open(hook.cleanup_config_path, "w") as f:
            json.dump(user_config, f)

        config = hook._load_cleanup_config()

        # Verify user overrides
        self.assertFalse(config["auto_cleanup_enabled"])
        self.assertFalse(config["cleanup_on_ultrathink"])
        # Verify default is still present
        self.assertTrue(config["cleanup_on_workflow"])

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_detect_task_completion_all_todos_completed(self):
        """Test task completion detection when all todos are completed."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.log = MagicMock()

        # Create todo file with all completed
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Doing task 1"},
            {"content": "Task 2", "status": "completed", "activeForm": "Doing task 2"},
        ]
        todo_file = self.todo_dir / "todos_test.json"
        with open(todo_file, "w") as f:
            json.dump(todos, f)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0  # No staged changes
            result = hook._detect_task_completion()

        self.assertTrue(result)

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_detect_task_completion_pending_todos(self):
        """Test task completion detection with pending todos."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.log = MagicMock()

        # Create todo file with pending tasks
        todos = [
            {"content": "Task 1", "status": "completed", "activeForm": "Doing task 1"},
            {"content": "Task 2", "status": "pending", "activeForm": "Doing task 2"},
        ]
        todo_file = self.todo_dir / "todos_test.json"
        with open(todo_file, "w") as f:
            json.dump(todos, f)

        result = hook._detect_task_completion()

        self.assertFalse(result)

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_detect_task_completion_staged_changes(self):
        """Test task completion detection with staged changes."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.log = MagicMock()

        # No todo files, but staged changes exist
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1  # Staged changes present
            result = hook._detect_task_completion()

        self.assertFalse(result)

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_cleanup_idempotency(self):
        """Test that cleanup only runs once per session."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.cleanup_marker = self.runtime_dir / ".cleanup_run"
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        # First call should trigger cleanup
        with patch.object(hook, "_load_cleanup_config") as mock_config:
            mock_config.return_value = {"auto_cleanup_enabled": True}
            with patch.object(hook, "_detect_task_completion") as mock_detect:
                mock_detect.return_value = True
                result1 = hook._trigger_cleanup_if_enabled()

        self.assertTrue(result1)
        self.assertTrue(hook.cleanup_marker.exists())

        # Second call should skip (idempotency)
        result2 = hook._trigger_cleanup_if_enabled()
        self.assertFalse(result2)

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_cleanup_disabled_by_config(self):
        """Test that cleanup can be disabled via config."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.cleanup_marker = self.runtime_dir / ".cleanup_run"
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()

        # Create config with cleanup disabled
        config = {"auto_cleanup_enabled": False}
        with open(hook.cleanup_config_path, "w") as f:
            json.dump(config, f)

        result = hook._trigger_cleanup_if_enabled()

        self.assertFalse(result)
        self.assertFalse(hook.cleanup_marker.exists())

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_cleanup_not_triggered_when_task_incomplete(self):
        """Test that cleanup is not triggered when task is not complete."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.cleanup_marker = self.runtime_dir / ".cleanup_run"
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()

        with patch.object(hook, "_load_cleanup_config") as mock_config:
            mock_config.return_value = {"auto_cleanup_enabled": True}
            with patch.object(hook, "_detect_task_completion") as mock_detect:
                mock_detect.return_value = False
                result = hook._trigger_cleanup_if_enabled()

        self.assertFalse(result)
        self.assertFalse(hook.cleanup_marker.exists())

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_process_blocks_for_cleanup(self):
        """Test that process() blocks stop when cleanup is triggered."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.lock_flag = self.runtime_dir / "locks" / ".lock_active"
        hook.cleanup_marker = self.runtime_dir / ".cleanup_run"
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        # Mock cleanup trigger to return True
        with patch.object(hook, "_trigger_cleanup_if_enabled") as mock_cleanup:
            mock_cleanup.return_value = True
            with patch.object(hook, "_trigger_reflection_if_enabled"):
                result = hook.process({})

        # Should block stop to run cleanup
        self.assertEqual(result["decision"], "block")
        self.assertIn("cleanup", result["reason"].lower())

    @patch.object(StopHook, "__init__", lambda self: None)
    def test_process_approves_when_no_cleanup(self):
        """Test that process() approves stop when cleanup is not triggered."""
        hook = StopHook()
        hook.project_root = self.project_root
        hook.lock_flag = self.runtime_dir / "locks" / ".lock_active"
        hook.cleanup_marker = self.runtime_dir / ".cleanup_run"
        hook.cleanup_config_path = self.runtime_dir / ".cleanup_config"
        hook.log = MagicMock()

        # Mock cleanup trigger to return False
        with patch.object(hook, "_trigger_cleanup_if_enabled") as mock_cleanup:
            mock_cleanup.return_value = False
            with patch.object(hook, "_trigger_reflection_if_enabled"):
                result = hook.process({})

        # Should approve stop
        self.assertEqual(result["decision"], "approve")


if __name__ == "__main__":
    unittest.main()
