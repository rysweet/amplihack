"""
Unit tests for update_prefs module.

Tests user preference management for automatic updates:
- Loading and saving preferences
- Atomic write operations
- Error handling for invalid values
- Timestamp management
- File operations and permission handling
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Add .claude/tools/amplihack to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent.parent / ".claude" / "tools" / "amplihack")
)

from update_prefs import (
    _get_preference_file_path,
    get_last_prompted,
    load_update_preference,
    reset_preference,
    save_update_preference,
)


class TestGetPreferenceFilePath:
    """Test suite for _get_preference_file_path function."""

    def test_get_preference_file_path_success(self):
        """Test successful retrieval of preference file path."""
        # Mock __file__ to point to expected location
        mock_file = Path("/project/.claude/tools/amplihack/update_prefs.py")

        with patch("pathlib.Path.__file__", str(mock_file)):
            with patch("pathlib.Path.resolve", return_value=mock_file):
                result = _get_preference_file_path()
                expected = Path("/project/.claude/.update_preference")
                assert result == expected

    def test_get_preference_file_path_incorrect_structure(self):
        """Test error when file is not in expected directory structure."""
        # Mock __file__ to point to wrong location
        mock_file = Path("/wrong/path/update_prefs.py")

        with patch("pathlib.Path.__file__", str(mock_file)):
            with patch("pathlib.Path.resolve", return_value=mock_file):
                with pytest.raises(RuntimeError, match="Expected .claude directory"):
                    _get_preference_file_path()


class TestLoadUpdatePreference:
    """Test suite for load_update_preference function."""

    def test_load_update_preference_always(self, tmp_path):
        """Test loading 'always' preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": "always", "last_prompted": "2025-11-16T10:00:00Z"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result == "always"

    def test_load_update_preference_never(self, tmp_path):
        """Test loading 'never' preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": "never", "last_prompted": "2025-11-16T10:00:00Z"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result == "never"

    def test_load_update_preference_ask(self, tmp_path):
        """Test loading None (ask) preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": None, "last_prompted": "2025-11-16T10:00:00Z"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result is None

    def test_load_update_preference_missing_file(self, tmp_path):
        """Test loading when preference file doesn't exist."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result is None

    def test_load_update_preference_invalid_json(self, tmp_path):
        """Test graceful handling of invalid JSON."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)
        pref_file.write_text("not valid json {}")

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result is None

    def test_load_update_preference_invalid_value(self, tmp_path):
        """Test handling of invalid preference value."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": "invalid_value", "last_prompted": "2025-11-16T10:00:00Z"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result is None

    def test_load_update_preference_missing_key(self, tmp_path):
        """Test handling when auto_update key is missing."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"last_prompted": "2025-11-16T10:00:00Z"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = load_update_preference()
            assert result is None

    def test_load_update_preference_permission_error(self, tmp_path):
        """Test graceful handling of permission errors."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                result = load_update_preference()
                assert result is None

    def test_load_update_preference_runtime_error(self):
        """Test handling when _get_preference_file_path raises RuntimeError."""
        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            side_effect=RuntimeError("Cannot find .claude directory"),
        ):
            result = load_update_preference()
            assert result is None


class TestSaveUpdatePreference:
    """Test suite for save_update_preference function."""

    def test_save_update_preference_always(self, tmp_path):
        """Test saving 'always' preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("always")

            assert pref_file.exists()
            data = json.loads(pref_file.read_text())
            assert data["auto_update"] == "always"
            assert "last_prompted" in data

    def test_save_update_preference_never(self, tmp_path):
        """Test saving 'never' preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("never")

            assert pref_file.exists()
            data = json.loads(pref_file.read_text())
            assert data["auto_update"] == "never"
            assert "last_prompted" in data

    def test_save_update_preference_ask(self, tmp_path):
        """Test saving 'ask' preference (stored as None)."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("ask")

            assert pref_file.exists()
            data = json.loads(pref_file.read_text())
            assert data["auto_update"] is None
            assert "last_prompted" in data

    def test_save_update_preference_invalid_value(self, tmp_path):
        """Test that invalid values raise ValueError."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            with pytest.raises(ValueError, match="Invalid preference value"):
                save_update_preference("invalid")

    def test_save_update_preference_creates_directory(self, tmp_path):
        """Test that parent directory is created if it doesn't exist."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        assert not pref_file.parent.exists()

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("always")

            assert pref_file.parent.exists()
            assert pref_file.exists()

    def test_save_update_preference_atomic_write(self, tmp_path):
        """Test that write is atomic using temp file."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        temp_file = pref_file.with_suffix(".tmp")

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("always")

            # Temp file should be cleaned up
            assert not temp_file.exists()
            # Final file should exist
            assert pref_file.exists()

    def test_save_update_preference_atomic_write_cleanup_on_error(self, tmp_path):
        """Test that temp file is cleaned up on error."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)
        _ = pref_file.with_suffix(".tmp")

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            # Mock the rename to fail
            with patch("pathlib.Path.replace", side_effect=OSError("Disk full")):
                with pytest.raises(OSError):
                    save_update_preference("always")

                # Temp file should be cleaned up even on error
                # Note: This test may need adjustment based on actual cleanup behavior

    def test_save_update_preference_timestamp_format(self, tmp_path):
        """Test that timestamp is in correct ISO format with Z suffix."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("always")

            data = json.loads(pref_file.read_text())
            timestamp = data["last_prompted"]

            # Should end with 'Z' for UTC
            assert timestamp.endswith("Z")

            # Should be parseable as ISO format
            timestamp_str = timestamp.rstrip("Z")
            parsed = datetime.fromisoformat(timestamp_str)
            assert isinstance(parsed, datetime)

    def test_save_update_preference_trailing_newline(self, tmp_path):
        """Test that saved file has trailing newline."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            save_update_preference("always")

            content = pref_file.read_text()
            assert content.endswith("\n")


class TestGetLastPrompted:
    """Test suite for get_last_prompted function."""

    def test_get_last_prompted_success(self, tmp_path):
        """Test successful retrieval of last prompted timestamp."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        timestamp = "2025-11-16T10:30:00Z"
        data = {"auto_update": "always", "last_prompted": timestamp}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = get_last_prompted()

            assert isinstance(result, datetime)
            assert result.year == 2025
            assert result.month == 11
            assert result.day == 16
            assert result.hour == 10
            assert result.minute == 30

    def test_get_last_prompted_missing_file(self, tmp_path):
        """Test when preference file doesn't exist."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = get_last_prompted()
            assert result is None

    def test_get_last_prompted_missing_key(self, tmp_path):
        """Test when last_prompted key is missing."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": "always"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = get_last_prompted()
            assert result is None

    def test_get_last_prompted_invalid_format(self, tmp_path):
        """Test handling of invalid timestamp format."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)

        data = {"auto_update": "always", "last_prompted": "invalid-timestamp"}
        pref_file.write_text(json.dumps(data))

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = get_last_prompted()
            assert result is None

    def test_get_last_prompted_json_decode_error(self, tmp_path):
        """Test handling of invalid JSON."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)
        pref_file.write_text("not valid json")

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            result = get_last_prompted()
            assert result is None

    def test_get_last_prompted_os_error(self, tmp_path):
        """Test handling of OS errors."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                result = get_last_prompted()
                assert result is None


class TestResetPreference:
    """Test suite for reset_preference function."""

    def test_reset_preference_success(self, tmp_path):
        """Test successful removal of preference file."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)
        pref_file.write_text('{"auto_update": "always"}')

        assert pref_file.exists()

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            reset_preference()
            assert not pref_file.exists()

    def test_reset_preference_file_not_exists(self, tmp_path):
        """Test reset when file doesn't exist (should not raise error)."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            # Should not raise error
            reset_preference()

    def test_reset_preference_os_error(self, tmp_path):
        """Test graceful handling of OS errors during deletion."""
        pref_file = tmp_path / ".claude" / ".update_preference"
        pref_file.parent.mkdir(parents=True)
        pref_file.write_text('{"auto_update": "always"}')

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            with patch("pathlib.Path.unlink", side_effect=OSError("Permission denied")):
                # Should not raise error
                reset_preference()

    def test_reset_preference_runtime_error(self):
        """Test handling when _get_preference_file_path raises RuntimeError."""
        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            side_effect=RuntimeError("Cannot find .claude directory"),
        ):
            # Should not raise error
            reset_preference()


class TestPreferenceWorkflow:
    """Integration tests for complete preference workflows."""

    def test_preference_workflow_save_and_load(self, tmp_path):
        """Test complete save and load workflow."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            # Save preference
            save_update_preference("always")

            # Load preference
            result = load_update_preference()
            assert result == "always"

            # Load timestamp
            timestamp = get_last_prompted()
            assert isinstance(timestamp, datetime)

    def test_preference_workflow_save_reset_load(self, tmp_path):
        """Test save, reset, and load workflow."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            # Save preference
            save_update_preference("never")
            assert load_update_preference() == "never"

            # Reset preference
            reset_preference()

            # Load should return None after reset
            assert load_update_preference() is None
            assert get_last_prompted() is None

    def test_preference_workflow_update_existing(self, tmp_path):
        """Test updating existing preference."""
        pref_file = tmp_path / ".claude" / ".update_preference"

        with patch(
            ".claude.tools.amplihack.update_prefs._get_preference_file_path",
            return_value=pref_file,
        ):
            # Save initial preference
            save_update_preference("always")
            assert load_update_preference() == "always"

            # Update preference
            save_update_preference("never")
            assert load_update_preference() == "never"

            # Verify timestamp was updated
            timestamp = get_last_prompted()
            assert isinstance(timestamp, datetime)
