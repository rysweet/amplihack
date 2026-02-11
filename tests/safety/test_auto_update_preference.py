"""Unit tests for _read_auto_update_preference helper.

Tests reading auto_update preference from USER_PREFERENCES.md:
1. Returns True when "always"
2. Returns False when "never"
3. Returns False when "ask" (default)
4. Returns False when file missing
5. Returns False when section missing
6. Returns False for nonexistent directory
"""

import tempfile
import unittest
from pathlib import Path

from amplihack.cli import _read_auto_update_preference


class TestAutoUpdatePreference(unittest.TestCase):
    """Test suite for _read_auto_update_preference helper."""

    def test_returns_true_when_always(self):
        """Test Case: Returns True when auto_update is set to 'always'.

        Create temp directory with context/USER_PREFERENCES.md containing
        "### Auto Update\n\nalways\n" and verify function returns True.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            context_dir = temp_path / "context"
            context_dir.mkdir()

            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text("### Auto Update\n\nalways\n")

            result = _read_auto_update_preference(str(temp_path))
            self.assertTrue(result)

    def test_returns_false_when_never(self):
        """Test Case: Returns False when auto_update is set to 'never'.

        Create temp directory with context/USER_PREFERENCES.md containing
        "### Auto Update\n\nnever\n" and verify function returns False.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            context_dir = temp_path / "context"
            context_dir.mkdir()

            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text("### Auto Update\n\nnever\n")

            result = _read_auto_update_preference(str(temp_path))
            self.assertFalse(result)

    def test_returns_false_when_ask(self):
        """Test Case: Returns False when auto_update is set to 'ask'.

        'ask' is the default behavior, meaning prompt user - should return False
        since auto_approve should not happen.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            context_dir = temp_path / "context"
            context_dir.mkdir()

            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text("### Auto Update\n\nask\n")

            result = _read_auto_update_preference(str(temp_path))
            self.assertFalse(result)

    def test_returns_false_when_file_missing(self):
        """Test Case: Returns False when USER_PREFERENCES.md does not exist.

        Pass directory without USER_PREFERENCES.md file and verify function
        returns False (safe default).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            context_dir = temp_path / "context"
            context_dir.mkdir()

            # File does NOT exist
            result = _read_auto_update_preference(str(temp_path))
            self.assertFalse(result)

    def test_returns_false_when_no_auto_update_section(self):
        """Test Case: Returns False when file exists but no Auto Update section.

        Create USER_PREFERENCES.md without the "### Auto Update" section and
        verify function returns False (safe default).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            context_dir = temp_path / "context"
            context_dir.mkdir()

            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text("# User Preferences\n\nSome other content\n")

            result = _read_auto_update_preference(str(temp_path))
            self.assertFalse(result)

    def test_returns_false_for_nonexistent_dir(self):
        """Test Case: Returns False when directory does not exist.

        Pass nonexistent path and verify function returns False (safe default).
        """
        result = _read_auto_update_preference("/nonexistent/path/that/does/not/exist")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
