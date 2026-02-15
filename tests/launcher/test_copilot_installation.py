"""Tests for Copilot CLI installation false negative bug (Issue #2278).

This test suite validates the fix for the redundant check_copilot() call after
successful install_copilot(). The bug caused false installation failures because
the newly installed binary wasn't in PATH for the re-check.

Tests follow TDD methodology - they expose the bug BEFORE the fix is applied.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from amplihack.launcher.copilot import install_copilot, launch_copilot


class TestCopilotInstallationLogic:
    """Unit tests for installation logic in launch_copilot()."""

    @patch("amplihack.launcher.copilot.disable_github_mcp_server")
    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.LauncherDetector")
    @patch("amplihack.launcher.copilot.get_copilot_directories")
    @patch("amplihack.launcher.copilot.stage_agents")
    @patch("amplihack.launcher.copilot.stage_directory")
    @patch("amplihack.launcher.copilot.generate_copilot_instructions")
    def test_installation_succeeds_no_redundant_check(
        self,
        mock_gen_instructions,
        mock_stage_dir,
        mock_stage_agents,
        mock_get_dirs,
        mock_detector,
        mock_check_update,
        mock_subprocess,
        mock_install,
        mock_check,
        mock_disable_mcp,
    ):
        """Test: Installation succeeds, no re-check after successful install.

        BUG: Current code calls check_copilot() twice when installation succeeds:
        1. Initial check (line 618) returns False
        2. install_copilot() (line 619) returns True
        3. Redundant check_copilot() (line 619) returns False (not in PATH yet)
        4. Raises false negative installation failure

        EXPECTED: check_copilot() should be called only ONCE (initial check).
        After install_copilot() returns True, we should trust it succeeded.
        """
        # Setup mocks
        mock_check_update.return_value = None
        mock_get_dirs.return_value = ["/home/user"]
        mock_detector.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0)
        mock_disable_mcp.return_value = False
        mock_stage_agents.return_value = 0
        mock_stage_dir.return_value = 0

        # Initial check: not installed
        # After install: DO NOT call check again
        mock_check.return_value = False
        mock_install.return_value = True

        # Execute
        result = launch_copilot(args=[], interactive=False)

        # Verify: Should succeed with exit code 0
        assert result == 0, "Installation succeeded but launch_copilot() returned non-zero"

        # CRITICAL: check_copilot() should be called ONLY ONCE (initial check)
        # The redundant second check is the bug we're fixing
        assert mock_check.call_count == 1, (
            f"Expected check_copilot() called once, got {mock_check.call_count} calls"
        )

        # Verify install was called (installation path triggered)
        mock_install.assert_called_once()

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.LauncherDetector")
    @patch("amplihack.launcher.copilot.get_copilot_directories")
    def test_installation_fails_returns_error(
        self,
        mock_get_dirs,
        mock_detector,
        mock_check_update,
        mock_subprocess,
        mock_install,
        mock_check,
    ):
        """Test: Installation fails, returns error code 1.

        When install_copilot() returns False, launch_copilot() should return 1
        without attempting to launch copilot.
        """
        # Setup mocks
        mock_check_update.return_value = None
        mock_get_dirs.return_value = ["/home/user"]
        mock_detector.return_value = Mock()

        # Not installed and installation fails
        mock_check.return_value = False
        mock_install.return_value = False

        # Execute
        result = launch_copilot(args=[], interactive=False)

        # Verify: Should fail with exit code 1
        assert result == 1, "Installation failed but launch_copilot() returned 0"

        # Verify subprocess.run was NOT called (copilot not launched)
        mock_subprocess.assert_not_called()

    @patch("amplihack.launcher.copilot.disable_github_mcp_server")
    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.LauncherDetector")
    @patch("amplihack.launcher.copilot.get_copilot_directories")
    @patch("amplihack.launcher.copilot.stage_agents")
    @patch("amplihack.launcher.copilot.stage_directory")
    @patch("amplihack.launcher.copilot.generate_copilot_instructions")
    def test_already_installed_skips_installation(
        self,
        mock_gen_instructions,
        mock_stage_dir,
        mock_stage_agents,
        mock_get_dirs,
        mock_detector,
        mock_check_update,
        mock_subprocess,
        mock_install,
        mock_check,
        mock_disable_mcp,
    ):
        """Test: Already installed, skips installation entirely.

        When check_copilot() returns True, install_copilot() should not be called.
        """
        # Setup mocks
        mock_check_update.return_value = None
        mock_get_dirs.return_value = ["/home/user"]
        mock_detector.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0)
        mock_disable_mcp.return_value = False
        mock_stage_agents.return_value = 0
        mock_stage_dir.return_value = 0

        # Already installed
        mock_check.return_value = True

        # Execute
        result = launch_copilot(args=[], interactive=False)

        # Verify: Should succeed with exit code 0
        assert result == 0, "Already installed but launch_copilot() returned non-zero"

        # Verify install was NOT called (skipped installation)
        mock_install.assert_not_called()

        # Verify subprocess.run was called (copilot launched)
        mock_subprocess.assert_called_once()


class TestInstallCopilotPathUpdate:
    """Integration test for PATH update during installation."""

    @patch("subprocess.run")
    @patch("amplihack.launcher.copilot.Path.mkdir")
    def test_install_updates_path_for_current_process(self, mock_mkdir, mock_subprocess):
        """Test: install_copilot() adds npm-global/bin to PATH.

        When install_copilot() succeeds, it should:
        1. Add npm-global/bin to os.environ["PATH"]
        2. Make 'copilot' command available in current process

        This validates the PATH update happens correctly so subsequent
        check_copilot() calls would succeed IF we called them (but we shouldn't).
        """
        # Setup: npm install succeeds
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Save original PATH
        original_path = os.environ.get("PATH", "")

        try:
            # Execute installation
            result = install_copilot()

            # Verify: Installation succeeded
            assert result is True, "install_copilot() should return True on success"

            # Verify: npm-global/bin added to PATH
            expected_bin = str(Path.home() / ".npm-global" / "bin")
            current_path = os.environ.get("PATH", "")
            assert expected_bin in current_path, f"Expected {expected_bin} in PATH: {current_path}"

            # Verify: npm command called with correct args
            npm_prefix = str(Path.home() / ".npm-global")
            mock_subprocess.assert_called_once_with(
                ["npm", "install", "-g", "--prefix", npm_prefix, "@github/copilot"], check=False
            )

        finally:
            # Cleanup: Restore original PATH
            os.environ["PATH"] = original_path


class TestInstallationErrorMessages:
    """Tests for error message clarity during installation failures."""

    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.LauncherDetector")
    @patch("amplihack.launcher.copilot.Path")
    @patch("amplihack.launcher.copilot.get_copilot_directories")
    def test_clear_error_message_on_failure(
        self,
        mock_get_dirs,
        mock_path,
        mock_detector,
        mock_check_update,
        mock_install,
        mock_check,
        capsys,
    ):
        """Test: Clear error message when installation fails.

        When installation fails, user should see:
        'Failed to install Copilot CLI'
        """
        # Setup mocks
        mock_check_update.return_value = None
        mock_get_dirs.return_value = ["/home/user"]
        mock_path.return_value = Mock()
        mock_detector.return_value = Mock()

        # Not installed and installation fails
        mock_check.return_value = False
        mock_install.return_value = False

        # Execute
        result = launch_copilot(args=[], interactive=False)

        # Verify: Exit code 1
        assert result == 1

        # Verify: Error message printed
        captured = capsys.readouterr()
        assert "Failed to install Copilot CLI" in captured.out


class TestBugReproduction:
    """Direct reproduction of the bug for documentation purposes."""

    @patch("amplihack.launcher.copilot.disable_github_mcp_server")
    @patch("amplihack.launcher.copilot.check_copilot")
    @patch("amplihack.launcher.copilot.install_copilot")
    @patch("amplihack.launcher.copilot.subprocess.run")
    @patch("amplihack.launcher.copilot.check_for_update")
    @patch("amplihack.launcher.copilot.LauncherDetector")
    @patch("amplihack.launcher.copilot.get_copilot_directories")
    @patch("amplihack.launcher.copilot.stage_agents")
    @patch("amplihack.launcher.copilot.stage_directory")
    @patch("amplihack.launcher.copilot.generate_copilot_instructions")
    def test_bug_false_negative_after_successful_install(
        self,
        mock_gen_instructions,
        mock_stage_dir,
        mock_stage_agents,
        mock_get_dirs,
        mock_detector,
        mock_check_update,
        mock_subprocess,
        mock_install,
        mock_check,
        mock_disable_mcp,
    ):
        """REPRODUCTION: False negative when install succeeds but re-check fails.

        This test documents the exact bug scenario:
        1. check_copilot() returns False (not installed)
        2. install_copilot() returns True (installation succeeds)
        3. BUGGY CODE: check_copilot() called again, returns False (PATH not updated for subprocess)
        4. RESULT: False negative error "Failed to install Copilot CLI"

        After fix:
        - Step 3 eliminated (no redundant check)
        - Result: Success (exit code 0)
        """
        # Setup mocks
        mock_check_update.return_value = None
        mock_get_dirs.return_value = ["/home/user"]
        mock_detector.return_value = Mock()
        mock_subprocess.return_value = Mock(returncode=0)
        mock_disable_mcp.return_value = False
        mock_stage_agents.return_value = 0
        mock_stage_dir.return_value = 0

        # Simulate bug scenario:
        # - First check: not installed
        # - Install succeeds
        # - Second check: STILL not found (PATH issue)
        mock_check.return_value = False  # Both checks return False
        mock_install.return_value = True  # But install succeeded

        # Execute
        result = launch_copilot(args=[], interactive=False)

        # EXPECTED (after fix): Should succeed because install_copilot() returned True
        assert result == 0, (
            "BUG REPRODUCED: Installation succeeded but launch_copilot() returned 1. "
            "This is the false negative we're fixing."
        )

        # EXPECTED (after fix): check_copilot() called only once
        assert mock_check.call_count == 1, (
            f"BUG REPRODUCED: check_copilot() called {mock_check.call_count} times. "
            "Expected 1 call (initial check only). The second call is the bug."
        )
