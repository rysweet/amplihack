"""Tests for fleet _defaults -- get_azlin_path().

Tests the azlin resolution logic. All external dependencies
(shutil.which, os.environ) are mocked to isolate resolution logic
from the real filesystem.

Testing pyramid:
- 100% unit tests (fast, fully mocked)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from amplihack.fleet._defaults import get_azlin_path


# ---------------------------------------------------------------------------
# get_azlin_path
# ---------------------------------------------------------------------------


class TestGetAzlinPath:
    """Tests for get_azlin_path() resolution logic."""

    def test_get_azlin_path_from_env(self, monkeypatch):
        """AZLIN_PATH env var takes priority over shutil.which."""
        monkeypatch.setenv("AZLIN_PATH", "/custom/path/azlin")
        result = get_azlin_path()
        assert result == "/custom/path/azlin"

    @patch("amplihack.fleet._defaults.shutil.which", return_value="/usr/local/bin/azlin")
    def test_get_azlin_path_from_which(self, mock_which, monkeypatch):
        """Falls back to shutil.which when AZLIN_PATH is not set."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        result = get_azlin_path()
        assert result == "/usr/local/bin/azlin"
        mock_which.assert_called_once_with("azlin")

    @patch("amplihack.fleet._defaults.os.access", return_value=False)
    @patch("amplihack.fleet._defaults.os.path.isfile", return_value=False)
    @patch("amplihack.fleet._defaults.shutil.which", return_value=None)
    def test_get_azlin_path_raises_when_missing(self, mock_which, mock_isfile, mock_access, monkeypatch):
        """Raises ValueError with helpful message when azlin cannot be found."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with pytest.raises(ValueError, match="azlin not found"):
            get_azlin_path()

    @patch("amplihack.fleet._defaults.os.access", return_value=False)
    @patch("amplihack.fleet._defaults.os.path.isfile", return_value=False)
    @patch("amplihack.fleet._defaults.shutil.which", return_value=None)
    def test_get_azlin_path_error_message_includes_install_hint(self, mock_which, mock_isfile, mock_access, monkeypatch):
        """Error message includes AZLIN_PATH instructions."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with pytest.raises(ValueError, match="AZLIN_PATH"):
            get_azlin_path()

    @patch("amplihack.fleet._defaults.shutil.which", return_value=None)
    def test_get_azlin_path_finds_dev_location(self, mock_which, monkeypatch, tmp_path):
        """Falls back to known dev location ~/src/azlin/.venv/bin/azlin."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        dev_azlin = tmp_path / "azlin"
        dev_azlin.touch(mode=0o755)
        with patch("amplihack.fleet._defaults.os.path.expanduser", return_value=str(dev_azlin)):
            result = get_azlin_path()
        assert result == str(dev_azlin)

    def test_get_azlin_path_env_takes_priority_over_which(self, monkeypatch):
        """Even if shutil.which would find azlin, AZLIN_PATH wins."""
        monkeypatch.setenv("AZLIN_PATH", "/env/azlin")
        with patch("amplihack.fleet._defaults.shutil.which", return_value="/which/azlin"):
            result = get_azlin_path()
        assert result == "/env/azlin"
