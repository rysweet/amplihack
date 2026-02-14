"""Tests for npm PATH auto-configuration in Claude CLI.

Tests the fix for the repeating PATH reminder message that appears every session.
Covers three changes:
1. _update_shell_profile_path() - auto-updates shell profile
2. _find_claude_in_common_locations() - fallback to known install path
3. _install_claude_cli() - uses auto-update instead of manual reminder
"""

import os
import sys
import types
from unittest.mock import MagicMock, patch

# Ensure amplihack.utils.prerequisites is importable even on Python <3.11
# (it uses datetime.UTC which is 3.11+). We inject a mock module so that
# patch decorators can resolve the target without triggering the real import.
if "amplihack.utils.prerequisites" not in sys.modules:
    _mock_prereqs = types.ModuleType("amplihack.utils.prerequisites")
    _mock_prereqs.safe_subprocess_call = MagicMock(return_value=(0, "", ""))
    sys.modules["amplihack.utils.prerequisites"] = _mock_prereqs

import amplihack.utils

if not hasattr(amplihack.utils, "prerequisites"):
    amplihack.utils.prerequisites = sys.modules["amplihack.utils.prerequisites"]

from amplihack.utils.claude_cli import (
    _find_claude_in_common_locations,
    _update_shell_profile_path,
)

# ============================================================================
# TESTS: _update_shell_profile_path()
# ============================================================================


class TestUpdateShellProfilePath:
    """Tests for _update_shell_profile_path()."""

    def test_creates_bashrc_entry_when_missing(self, tmp_path, monkeypatch):
        """Test that PATH export is appended to .bashrc when not present."""
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("# existing content\n")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/bash")

        result = _update_shell_profile_path()

        assert result is True
        content = bashrc.read_text()
        assert "# Added by amplihack" in content
        assert 'export PATH="$HOME/.npm-global/bin:$PATH"' in content

    def test_creates_zshrc_entry_for_zsh(self, tmp_path, monkeypatch):
        """Test that zsh users get .zshrc updated."""
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text("# zsh config\n")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/zsh")

        result = _update_shell_profile_path()

        assert result is True
        content = zshrc.read_text()
        assert 'export PATH="$HOME/.npm-global/bin:$PATH"' in content

    def test_idempotent_does_not_duplicate(self, tmp_path, monkeypatch):
        """Test that calling twice does not duplicate the PATH entry."""
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("# existing\n")

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/bash")

        _update_shell_profile_path()
        _update_shell_profile_path()

        content = bashrc.read_text()
        count = content.count('export PATH="$HOME/.npm-global/bin:$PATH"')
        assert count == 1

    def test_idempotent_when_line_already_present(self, tmp_path, monkeypatch):
        """Test no modification when the PATH line already exists in profile."""
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text('# old config\nexport PATH="$HOME/.npm-global/bin:$PATH"\n')

        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/bash")

        result = _update_shell_profile_path()

        assert result is True
        content = bashrc.read_text()
        count = content.count('export PATH="$HOME/.npm-global/bin:$PATH"')
        assert count == 1

    def test_creates_profile_file_if_missing(self, tmp_path, monkeypatch):
        """Test that profile file is created if it does not exist."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/bash")

        bashrc = tmp_path / ".bashrc"
        assert not bashrc.exists()

        result = _update_shell_profile_path()

        assert result is True
        assert bashrc.exists()
        content = bashrc.read_text()
        assert 'export PATH="$HOME/.npm-global/bin:$PATH"' in content

    def test_defaults_to_bashrc_when_shell_not_set(self, tmp_path, monkeypatch):
        """Test fallback to .bashrc when SHELL env var is not set."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("SHELL", raising=False)

        result = _update_shell_profile_path()

        assert result is True
        bashrc = tmp_path / ".bashrc"
        assert bashrc.exists()
        assert ".npm-global/bin" in bashrc.read_text()

    def test_returns_false_on_write_error(self, tmp_path, monkeypatch):
        """Test graceful failure when profile cannot be written."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.setenv("SHELL", "/bin/bash")

        # Make the home directory read-only to force write failure
        readonly_dir = tmp_path / "noaccess"
        readonly_dir.mkdir()

        monkeypatch.setattr("pathlib.Path.home", lambda: readonly_dir)

        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = _update_shell_profile_path()

        assert result is False

    def test_detects_zsh_variants(self, tmp_path, monkeypatch):
        """Test detection of zsh from various SHELL values."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        for shell_path in ["/bin/zsh", "/usr/bin/zsh", "/usr/local/bin/zsh"]:
            # Clean up between iterations
            zshrc = tmp_path / ".zshrc"
            if zshrc.exists():
                zshrc.unlink()

            monkeypatch.setenv("SHELL", shell_path)
            result = _update_shell_profile_path()

            assert result is True
            assert zshrc.exists(), f"Failed for SHELL={shell_path}"


# ============================================================================
# TESTS: _find_claude_in_common_locations() with fallback
# ============================================================================


class TestFindClaudeFallback:
    """Tests for _find_claude_in_common_locations() fallback to known path."""

    @patch("amplihack.utils.claude_cli.shutil.which")
    def test_returns_which_result_when_found(self, mock_which):
        """Test that shutil.which result is returned when claude is in PATH."""
        mock_which.return_value = "/usr/local/bin/claude"

        result = _find_claude_in_common_locations()

        assert result == "/usr/local/bin/claude"

    @patch("amplihack.utils.claude_cli.shutil.which")
    def test_falls_back_to_npm_global_when_not_in_path(self, mock_which, tmp_path, monkeypatch):
        """Test fallback to ~/.npm-global/bin/claude when not in PATH."""
        mock_which.return_value = None
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Create the known install location
        npm_claude = tmp_path / ".npm-global" / "bin" / "claude"
        npm_claude.parent.mkdir(parents=True)
        npm_claude.touch()
        npm_claude.chmod(0o755)

        result = _find_claude_in_common_locations()

        assert result == str(npm_claude)

    @patch("amplihack.utils.claude_cli.shutil.which")
    def test_fallback_adds_to_path_env(self, mock_which, tmp_path, monkeypatch):
        """Test that fallback adds ~/.npm-global/bin to os.environ PATH."""
        mock_which.return_value = None
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        npm_bin = tmp_path / ".npm-global" / "bin"
        npm_claude = npm_bin / "claude"
        npm_claude.parent.mkdir(parents=True)
        npm_claude.touch()
        npm_claude.chmod(0o755)

        original_path = os.environ.get("PATH", "")
        _find_claude_in_common_locations()

        # PATH should now include the npm-global bin directory
        assert str(npm_bin) in os.environ["PATH"]

        # Restore original PATH
        os.environ["PATH"] = original_path

    @patch("amplihack.utils.claude_cli.shutil.which")
    def test_returns_none_when_fallback_missing(self, mock_which, tmp_path, monkeypatch):
        """Test returns None when neither PATH nor fallback has claude."""
        mock_which.return_value = None
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Do NOT create ~/.npm-global/bin/claude

        result = _find_claude_in_common_locations()

        assert result is None


# ============================================================================
# TESTS: _install_claude_cli() uses auto-update
# ============================================================================


class TestInstallAutoUpdatesProfile:
    """Tests that _install_claude_cli() auto-updates shell profile."""

    @patch("amplihack.utils.claude_cli._update_shell_profile_path")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_no_manual_reminder_on_auto_update_success(
        self,
        mock_subprocess,
        mock_which,
        mock_validate,
        mock_update_profile,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        """Test that manual PATH reminder is NOT shown when auto-update succeeds."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")
        mock_validate.return_value = True
        mock_update_profile.return_value = True

        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        assert result is True
        mock_update_profile.assert_called_once()

        captured = capsys.readouterr()
        # Should NOT contain the old manual reminder
        assert "Add to your shell profile" not in captured.out
        # Should contain the success message
        assert "Shell profile updated" in captured.out

    @patch("amplihack.utils.claude_cli._update_shell_profile_path")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_shows_manual_reminder_on_auto_update_failure(
        self,
        mock_subprocess,
        mock_which,
        mock_validate,
        mock_update_profile,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        """Test that manual PATH reminder IS shown when auto-update fails."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")
        mock_validate.return_value = True
        mock_update_profile.return_value = False

        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        assert result is True
        mock_update_profile.assert_called_once()

        captured = capsys.readouterr()
        # Should contain the fallback manual reminder
        assert 'export PATH="$HOME/.npm-global/bin:$PATH"' in captured.out
