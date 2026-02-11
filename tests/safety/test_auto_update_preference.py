"""Unit tests for _read_auto_update_preference in cli.py."""

import tempfile
import unittest
from pathlib import Path

from amplihack.cli import _read_auto_update_preference


class TestReadAutoUpdatePreference(unittest.TestCase):
    """Test suite for _read_auto_update_preference."""

    def test_returns_true_when_always(self):
        """Test returns True when auto_update is 'always'."""
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp) / "context"
            context_dir.mkdir()
            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text(
                "# Preferences\n\n### Auto Update\n\nalways\n\n### Other\n\nstuff\n"
            )
            self.assertTrue(_read_auto_update_preference(tmp))

    def test_returns_false_when_never(self):
        """Test returns False when auto_update is 'never'."""
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp) / "context"
            context_dir.mkdir()
            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text(
                "# Preferences\n\n### Auto Update\n\nnever\n\n### Other\n\nstuff\n"
            )
            self.assertFalse(_read_auto_update_preference(tmp))

    def test_returns_false_when_ask(self):
        """Test returns False when auto_update is 'ask'."""
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp) / "context"
            context_dir.mkdir()
            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text(
                "# Preferences\n\n### Auto Update\n\nask\n\n### Other\n\nstuff\n"
            )
            self.assertFalse(_read_auto_update_preference(tmp))

    def test_returns_false_when_file_missing(self):
        """Test returns False when USER_PREFERENCES.md doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(_read_auto_update_preference(tmp))

    def test_returns_false_when_no_auto_update_section(self):
        """Test returns False when file exists but has no Auto Update section."""
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp) / "context"
            context_dir.mkdir()
            prefs_file = context_dir / "USER_PREFERENCES.md"
            prefs_file.write_text("# Preferences\n\nSome content\n")
            self.assertFalse(_read_auto_update_preference(tmp))

    def test_returns_false_for_nonexistent_dir(self):
        """Test returns False for a directory that doesn't exist."""
        self.assertFalse(_read_auto_update_preference("/nonexistent/path"))


if __name__ == "__main__":
    unittest.main()
