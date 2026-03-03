"""Tests for fleet _defaults -- get_azlin_path() and ensure_azlin().

Tests the azlin resolution and auto-installation logic. All external
dependencies (shutil.which, subprocess.run, os.environ, os.path.isfile)
are mocked to isolate resolution logic from the real filesystem.

Testing pyramid:
- 100% unit tests (fast, fully mocked)
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._defaults import ensure_azlin, get_azlin_path


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

    @patch("amplihack.fleet._defaults.shutil.which", return_value=None)
    def test_get_azlin_path_raises_when_missing(self, mock_which, monkeypatch):
        """Raises ValueError with helpful message when azlin cannot be found."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with pytest.raises(ValueError, match="azlin not found"):
            get_azlin_path()

    @patch("amplihack.fleet._defaults.shutil.which", return_value=None)
    def test_get_azlin_path_error_message_includes_install_hint(self, mock_which, monkeypatch):
        """Error message includes installation instructions."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        with pytest.raises(ValueError, match="pip install azlin"):
            get_azlin_path()

    def test_get_azlin_path_env_takes_priority_over_which(self, monkeypatch):
        """Even if shutil.which would find azlin, AZLIN_PATH wins."""
        monkeypatch.setenv("AZLIN_PATH", "/env/azlin")
        with patch("amplihack.fleet._defaults.shutil.which", return_value="/which/azlin"):
            result = get_azlin_path()
        assert result == "/env/azlin"


# ---------------------------------------------------------------------------
# ensure_azlin
# ---------------------------------------------------------------------------


class TestEnsureAzlin:
    """Tests for ensure_azlin() auto-installation logic."""

    def test_ensure_azlin_returns_existing(self, monkeypatch):
        """When azlin is already on PATH, returns it without installing."""
        monkeypatch.setenv("AZLIN_PATH", "/already/installed/azlin")
        result = ensure_azlin()
        assert result == "/already/installed/azlin"

    @patch("amplihack.fleet._defaults.shutil.which")
    @patch("amplihack.fleet._defaults.subprocess.run")
    def test_ensure_azlin_installs_via_pip(self, mock_run, mock_which, monkeypatch):
        """When not found, pip install succeeds, verify it tries pip."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)

        # First call: get_azlin_path() -> not found (which returns None)
        # After install: which returns the installed path
        mock_which.side_effect = [None, "/usr/local/bin/azlin"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = ensure_azlin()

        assert result == "/usr/local/bin/azlin"
        # Verify pip was tried (first install method)
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "pip" in " ".join(str(a) for a in call_args[0][0])
        assert "azlin" in call_args[0][0]

    @patch("amplihack.fleet._defaults.os.path.isfile", return_value=False)
    @patch("amplihack.fleet._defaults.shutil.which")
    @patch("amplihack.fleet._defaults.subprocess.run")
    def test_ensure_azlin_falls_back_to_uv_pip(self, mock_run, mock_which, mock_isfile, monkeypatch):
        """When pip fails, tries uv pip as next method."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)

        # get_azlin_path() always fails (not found)
        mock_which.return_value = None

        # First install (pip) fails, second (uv pip) fails with FileNotFoundError,
        # third (system pip) fails, fourth (pipx) fails
        pip_fail = MagicMock()
        pip_fail.returncode = 1
        pip_fail.stderr = "pip install failed"

        mock_run.side_effect = [
            pip_fail,        # sys.executable -m pip install azlin
            FileNotFoundError("uv not found"),  # uv pip install azlin
            pip_fail,        # pip install azlin (system)
            FileNotFoundError("pipx not found"),  # pipx install azlin
        ]

        with pytest.raises(ValueError, match="Could not install azlin"):
            ensure_azlin()

        # Verify multiple install methods were attempted
        assert mock_run.call_count >= 2

    @patch("amplihack.fleet._defaults.os.path.isfile", return_value=False)
    @patch("amplihack.fleet._defaults.shutil.which")
    @patch("amplihack.fleet._defaults.subprocess.run")
    def test_ensure_azlin_raises_when_all_fail(self, mock_run, mock_which, mock_isfile, monkeypatch):
        """When all install methods fail, raises ValueError."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        mock_which.return_value = None

        # All install methods fail
        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stderr = "installation failed"
        mock_run.return_value = fail_result

        with pytest.raises(ValueError, match="Could not install azlin"):
            ensure_azlin()

    @patch("amplihack.fleet._defaults.os.path.isfile")
    @patch("amplihack.fleet._defaults.shutil.which")
    @patch("amplihack.fleet._defaults.subprocess.run")
    def test_ensure_azlin_finds_in_local_bin(self, mock_run, mock_which, mock_isfile, monkeypatch):
        """After install, finds azlin in ~/.local/bin when not on PATH."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)

        # shutil.which never finds it (even after install)
        mock_which.return_value = None

        # pip install succeeds
        success_result = MagicMock()
        success_result.returncode = 0
        mock_run.return_value = success_result

        # os.path.isfile: first candidate (sys.executable dir) misses,
        # second candidate (~/.local/bin/azlin) hits
        def isfile_side_effect(path):
            return path.endswith(".local/bin/azlin")

        mock_isfile.side_effect = isfile_side_effect

        import os
        expected_path = os.path.expanduser("~/.local/bin/azlin")
        result = ensure_azlin()
        assert result == expected_path

    @patch("amplihack.fleet._defaults.shutil.which")
    @patch("amplihack.fleet._defaults.subprocess.run")
    def test_ensure_azlin_timeout_continues(self, mock_run, mock_which, monkeypatch):
        """When an install method times out, continues to next method."""
        monkeypatch.delenv("AZLIN_PATH", raising=False)
        mock_which.return_value = None

        # First method times out, all others fail
        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd="pip", timeout=120),
            FileNotFoundError("uv"),
            MagicMock(returncode=1, stderr="fail"),
            FileNotFoundError("pipx"),
        ]

        with pytest.raises(ValueError, match="Could not install azlin"):
            ensure_azlin()

    def test_ensure_azlin_skips_install_when_already_available(self, monkeypatch):
        """No subprocess calls when azlin is already available."""
        monkeypatch.setenv("AZLIN_PATH", "/existing/azlin")
        with patch("amplihack.fleet._defaults.subprocess.run") as mock_run:
            result = ensure_azlin()
            assert result == "/existing/azlin"
            mock_run.assert_not_called()
