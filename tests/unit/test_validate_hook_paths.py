"""Unit tests for validate_hook_paths function.

Tests the hook path validation logic that ensures hook files exist
before configuring them in settings.json.
"""

import tempfile
import unittest
from pathlib import Path

from src.amplihack.settings import validate_hook_paths


class TestValidateHookPaths(unittest.TestCase):
    """Test cases for validate_hook_paths function."""

    def setUp(self):
        """Create temporary directory for test hooks."""
        self.temp_dir = tempfile.mkdtemp()
        self.hooks_dir = Path(self.temp_dir) / "hooks"
        self.hooks_dir.mkdir()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_validate_all_hooks_exist(self):
        """All hooks present should return (True, [])."""
        # Create test hooks
        (self.hooks_dir / "session_start.py").touch()
        (self.hooks_dir / "stop.py").touch()

        hooks_to_validate = [
            {"type": "SessionStart", "file": "session_start.py", "timeout": 10},
            {"type": "Stop", "file": "stop.py", "timeout": 120},
        ]

        all_valid, missing = validate_hook_paths(
            "amplihack", hooks_to_validate, str(self.hooks_dir)
        )

        self.assertTrue(all_valid)
        self.assertEqual(missing, [])

    def test_validate_missing_single_hook(self):
        """Missing one hook should return (False, [missing list])."""
        # Create only one hook
        (self.hooks_dir / "session_start.py").touch()

        hooks_to_validate = [
            {"type": "SessionStart", "file": "session_start.py"},
            {"type": "Stop", "file": "stop.py"},  # Missing
        ]

        all_valid, missing = validate_hook_paths(
            "amplihack", hooks_to_validate, str(self.hooks_dir)
        )

        self.assertFalse(all_valid)
        self.assertEqual(len(missing), 1)
        self.assertIn("amplihack/stop.py", missing[0])
        self.assertIn(str(self.hooks_dir), missing[0])

    def test_validate_all_hooks_missing(self):
        """All hooks missing should return (False, [all missing])."""
        # Don't create any hooks

        hooks_to_validate = [
            {"type": "SessionStart", "file": "session_start.py"},
            {"type": "Stop", "file": "stop.py"},
        ]

        all_valid, missing = validate_hook_paths(
            "amplihack", hooks_to_validate, str(self.hooks_dir)
        )

        self.assertFalse(all_valid)
        self.assertEqual(len(missing), 2)

    def test_validate_empty_hooks_list(self):
        """Empty hooks list should return (True, [])."""
        hooks_to_validate = []

        all_valid, missing = validate_hook_paths(
            "amplihack", hooks_to_validate, str(self.hooks_dir)
        )

        self.assertTrue(all_valid)
        self.assertEqual(missing, [])

    def test_validate_path_expansion_home(self):
        """Paths with $HOME should be expanded correctly."""
        # Create hooks in home directory equivalent
        home_hooks = Path.home() / ".test_hooks"
        home_hooks.mkdir(exist_ok=True)
        (home_hooks / "test_hook.py").touch()

        try:
            hooks_to_validate = [
                {"type": "Test", "file": "test_hook.py"},
            ]

            # Use $HOME in path
            hooks_path = "$HOME/.test_hooks"

            all_valid, missing = validate_hook_paths("test", hooks_to_validate, hooks_path)

            self.assertTrue(all_valid)
            self.assertEqual(missing, [])
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(home_hooks)

    def test_validate_path_expansion_tilde(self):
        """Paths with ~ should be expanded correctly."""
        # Create hooks in home directory equivalent
        home_hooks = Path.home() / ".test_hooks_tilde"
        home_hooks.mkdir(exist_ok=True)
        (home_hooks / "test_hook.py").touch()

        try:
            hooks_to_validate = [
                {"type": "Test", "file": "test_hook.py"},
            ]

            # Use ~ in path
            hooks_path = "~/.test_hooks_tilde"

            all_valid, missing = validate_hook_paths("test", hooks_to_validate, hooks_path)

            self.assertTrue(all_valid)
            self.assertEqual(missing, [])
        finally:
            # Cleanup
            import shutil

            shutil.rmtree(home_hooks)

    def test_validate_nonexistent_directory(self):
        """Hooks dir doesn't exist - all hooks should be missing."""
        nonexistent_dir = str(Path(self.temp_dir) / "nonexistent")

        hooks_to_validate = [
            {"type": "SessionStart", "file": "session_start.py"},
        ]

        all_valid, missing = validate_hook_paths("amplihack", hooks_to_validate, nonexistent_dir)

        self.assertFalse(all_valid)
        self.assertEqual(len(missing), 1)
        self.assertIn("amplihack/session_start.py", missing[0])

    def test_validate_hook_with_additional_fields(self):
        """Hooks with timeout and matcher fields should validate correctly."""
        (self.hooks_dir / "post_tool_use.py").touch()

        hooks_to_validate = [
            {"type": "PostToolUse", "file": "post_tool_use.py", "matcher": "*"},
        ]

        all_valid, missing = validate_hook_paths(
            "amplihack", hooks_to_validate, str(self.hooks_dir)
        )

        self.assertTrue(all_valid)
        self.assertEqual(missing, [])

    def test_validate_symlink_hook(self):
        """Symlinked hooks should validate correctly."""
        # Create actual hook
        real_hook = self.hooks_dir / "real_hook.py"
        real_hook.touch()

        # Create symlink
        symlink_hook = self.hooks_dir / "symlink_hook.py"
        symlink_hook.symlink_to(real_hook)

        hooks_to_validate = [
            {"type": "Test", "file": "symlink_hook.py"},
        ]

        all_valid, missing = validate_hook_paths("test", hooks_to_validate, str(self.hooks_dir))

        self.assertTrue(all_valid)
        self.assertEqual(missing, [])

    def test_validate_broken_symlink(self):
        """Broken symlinks should be treated as missing."""
        # Create symlink to nonexistent file
        broken_symlink = self.hooks_dir / "broken.py"
        broken_symlink.symlink_to(self.hooks_dir / "nonexistent.py")

        hooks_to_validate = [
            {"type": "Test", "file": "broken.py"},
        ]

        all_valid, missing = validate_hook_paths("test", hooks_to_validate, str(self.hooks_dir))

        self.assertFalse(all_valid)
        self.assertEqual(len(missing), 1)


if __name__ == "__main__":
    unittest.main()
