"""Tests for Claude CLI auto-recovery functionality.

Tests the simplified single-phase recovery approach for corrupted or
non-executable Claude CLI binaries.

Philosophy:
- Single-phase recovery: validation failure → remove → reinstall
- No complex diagnostics (permission vs corruption)
- One retry attempt before requiring manual intervention
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Module under test
from amplihack.utils.claude_cli import (
    _remove_failed_binary,
    _retry_claude_installation,
    _validate_claude_binary,
    get_claude_cli_path,
)


# ============================================================================
# UNIT TESTS - Helper Functions
# ============================================================================


class TestValidateClaude:
    """Tests for _validate_claude_binary()."""

    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_validate_success(self, mock_subprocess):
        """Test validation succeeds when binary returns 0."""
        mock_subprocess.return_value = (0, "Claude CLI v1.0.0", "")

        result = _validate_claude_binary("/fake/path/claude")

        assert result is True
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["/fake/path/claude", "--version"]

    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_validate_fails_nonzero_exit(self, mock_subprocess):
        """Test validation fails when binary returns non-zero."""
        mock_subprocess.return_value = (1, "", "Error: command failed")

        result = _validate_claude_binary("/fake/path/claude")

        assert result is False

    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_validate_timeout(self, mock_subprocess):
        """Test validation fails on timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd=["claude", "--version"], timeout=5
        )

        # Should handle exception gracefully (not crash)
        # Current implementation doesn't catch TimeoutExpired explicitly
        # but safe_subprocess_call should handle it
        with pytest.raises(subprocess.TimeoutExpired):
            _validate_claude_binary("/fake/path/claude")


class TestRemoveFailedBinary:
    """Tests for _remove_failed_binary()."""

    def test_remove_existing_binary(self, tmp_path):
        """Test removal of existing binary."""
        binary = tmp_path / "claude"
        binary.touch()

        _remove_failed_binary(binary)

        assert not binary.exists()

    def test_remove_missing_binary(self, tmp_path):
        """Test removal of non-existent binary (should not error)."""
        binary = tmp_path / "claude"

        # Should not raise exception
        _remove_failed_binary(binary)

        assert not binary.exists()

    def test_remove_permission_error(self, tmp_path, capsys):
        """Test graceful handling of permission errors."""
        binary = tmp_path / "claude"
        binary.touch()

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            # Should not raise, just print warning
            _remove_failed_binary(binary)

        captured = capsys.readouterr()
        assert "Warning: Could not remove binary" in captured.out


class TestRetryClaudeInstallation:
    """Tests for _retry_claude_installation()."""

    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli._remove_failed_binary")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_retry_success(
        self, mock_subprocess, mock_remove, mock_validate, tmp_path, capsys
    ):
        """Test successful retry after validation failure."""
        user_npm_dir = tmp_path / ".npm-global"
        expected_binary = user_npm_dir / "bin" / "claude"
        expected_binary.parent.mkdir(parents=True)
        expected_binary.touch()

        # Mock successful reinstallation
        mock_subprocess.return_value = (0, "installed successfully", "")
        mock_validate.return_value = True

        result = _retry_claude_installation(
            "/usr/bin/npm", user_npm_dir, expected_binary
        )

        assert result is True
        mock_remove.assert_called_once_with(expected_binary)
        mock_subprocess.assert_called_once()

        # Verify output messages
        captured = capsys.readouterr()
        assert "attempting recovery" in captured.out.lower()
        assert "Recovery successful" in captured.out

    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli._remove_failed_binary")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_retry_npm_fails(
        self, mock_subprocess, mock_remove, mock_validate, tmp_path, capsys
    ):
        """Test retry when npm install fails."""
        user_npm_dir = tmp_path / ".npm-global"
        expected_binary = user_npm_dir / "bin" / "claude"

        # Mock failed reinstallation
        mock_subprocess.return_value = (1, "", "npm ERR! network timeout")

        result = _retry_claude_installation(
            "/usr/bin/npm", user_npm_dir, expected_binary
        )

        assert result is False
        mock_remove.assert_called_once()

        captured = capsys.readouterr()
        assert "Reinstallation failed" in captured.out

    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli._remove_failed_binary")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_retry_binary_not_created(
        self, mock_subprocess, mock_remove, mock_validate, tmp_path, capsys
    ):
        """Test retry when binary is not created after npm install."""
        user_npm_dir = tmp_path / ".npm-global"
        expected_binary = user_npm_dir / "bin" / "claude"
        # Don't create the binary

        # Mock successful npm but binary not created
        mock_subprocess.return_value = (0, "installed", "")

        result = _retry_claude_installation(
            "/usr/bin/npm", user_npm_dir, expected_binary
        )

        assert result is False

        captured = capsys.readouterr()
        assert "not created after reinstall" in captured.out.lower()

    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli._remove_failed_binary")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_retry_validation_fails_again(
        self, mock_subprocess, mock_remove, mock_validate, tmp_path, capsys
    ):
        """Test retry when reinstalled binary still fails validation."""
        user_npm_dir = tmp_path / ".npm-global"
        expected_binary = user_npm_dir / "bin" / "claude"
        expected_binary.parent.mkdir(parents=True)
        expected_binary.touch()

        # Mock successful npm but validation still fails
        mock_subprocess.return_value = (0, "installed", "")
        mock_validate.return_value = False

        result = _retry_claude_installation(
            "/usr/bin/npm", user_npm_dir, expected_binary
        )

        assert result is False

        captured = capsys.readouterr()
        assert "binary still invalid" in captured.out.lower()


# ============================================================================
# INTEGRATION TESTS - Full Installation Flow
# ============================================================================


class TestInstallWithRecovery:
    """Integration tests for full installation with recovery."""

    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_install_success_first_try(
        self, mock_subprocess, mock_which, mock_validate, tmp_path, monkeypatch
    ):
        """Test successful installation without needing recovery."""
        # Setup
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")

        # Create the binary file (npm would do this)
        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        # First validation succeeds
        mock_validate.return_value = True

        # Import here to get patched home
        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        assert result is True
        # Should only validate once (no retry)
        assert mock_validate.call_count == 1

    @patch("amplihack.utils.claude_cli._retry_claude_installation")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_install_with_recovery_success(
        self, mock_subprocess, mock_which, mock_validate, mock_retry, tmp_path, monkeypatch
    ):
        """Test installation that needs recovery but succeeds."""
        # Setup
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")

        # Create the binary file (npm would do this)
        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        # First validation fails, retry succeeds
        mock_validate.return_value = False
        mock_retry.return_value = True

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        assert result is True
        mock_retry.assert_called_once()

    @patch("amplihack.utils.claude_cli._retry_claude_installation")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_install_with_recovery_fails(
        self, mock_subprocess, mock_which, mock_validate, mock_retry, tmp_path, monkeypatch, capsys
    ):
        """Test installation where recovery also fails."""
        # Setup
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")

        # Create the binary file (npm would do this)
        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        # Both validation and retry fail
        mock_validate.return_value = False
        mock_retry.return_value = False

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        assert result is False
        mock_retry.assert_called_once()

        # Should show manual installation instructions
        captured = capsys.readouterr()
        assert "install manually" in captured.out.lower()


# ============================================================================
# END-TO-END TESTS
# ============================================================================


class TestGetClaudeCliPath:
    """E2E tests for get_claude_cli_path() with recovery."""

    @patch("amplihack.utils.claude_cli._find_claude_in_common_locations")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    def test_found_and_valid_no_install(self, mock_validate, mock_find):
        """Test when claude is already installed and valid."""
        mock_find.return_value = "/usr/local/bin/claude"
        mock_validate.return_value = True

        result = get_claude_cli_path(auto_install=True)

        assert result == "/usr/local/bin/claude"
        # Should not attempt installation

    @patch("amplihack.utils.claude_cli._install_claude_cli")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli._find_claude_in_common_locations")
    def test_not_found_auto_install_with_recovery(
        self, mock_find, mock_validate, mock_install, tmp_path, monkeypatch
    ):
        """Test auto-install with recovery when not found."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

        # Not found initially
        mock_find.return_value = None
        # Installation succeeds (with internal recovery)
        mock_install.return_value = True

        result = get_claude_cli_path(auto_install=True)

        assert result is not None
        mock_install.assert_called_once()

    @patch("amplihack.utils.claude_cli._install_claude_cli")
    @patch("amplihack.utils.claude_cli._find_claude_in_common_locations")
    def test_not_found_install_fails_with_recovery(
        self, mock_find, mock_install, capsys
    ):
        """Test when installation and recovery both fail."""
        mock_find.return_value = None
        mock_install.return_value = False

        result = get_claude_cli_path(auto_install=True)

        assert result is None
        captured = capsys.readouterr()
        assert "installation failed" in captured.out.lower()


# ============================================================================
# SCENARIO TESTS - Real-World Cases
# ============================================================================


class TestRecoveryScenarios:
    """Tests for real-world recovery scenarios."""

    @patch("amplihack.utils.claude_cli._retry_claude_installation")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_scenario_corrupted_binary_from_disk_space(
        self, mock_subprocess, mock_which, mock_validate, mock_retry, tmp_path, monkeypatch
    ):
        """
        Scenario: Binary partially written due to disk space, validation fails.
        Expected: Auto-recovery removes and reinstalls.
        """
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")

        # Create the binary file (npm would do this)
        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        # Validation fails first time (corrupted), succeeds after recovery
        mock_validate.return_value = False
        mock_retry.return_value = True

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        # Should succeed after recovery
        assert result is True
        mock_retry.assert_called_once()

    @patch("amplihack.utils.claude_cli._retry_claude_installation")
    @patch("amplihack.utils.claude_cli._validate_claude_binary")
    @patch("amplihack.utils.claude_cli.shutil.which")
    @patch("amplihack.utils.prerequisites.safe_subprocess_call")
    def test_scenario_non_executable_binary(
        self, mock_subprocess, mock_which, mock_validate, mock_retry, tmp_path, monkeypatch
    ):
        """
        Scenario: Binary installed but not executable (permissions issue).
        Expected: Auto-recovery removes and reinstalls with correct permissions.
        """
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        mock_which.return_value = "/usr/bin/npm"
        mock_subprocess.return_value = (0, "installed", "")

        # Create the binary file (npm would do this)
        binary_path = tmp_path / ".npm-global" / "bin" / "claude"
        binary_path.parent.mkdir(parents=True)
        binary_path.touch()

        # Validation fails (not executable), recovery fixes it
        mock_validate.return_value = False
        mock_retry.return_value = True

        from amplihack.utils.claude_cli import _install_claude_cli

        result = _install_claude_cli()

        # Should succeed after recovery
        assert result is True
        # Note: We don't distinguish between permission and corruption
        # Both handled by single recovery path
        mock_retry.assert_called_once()
