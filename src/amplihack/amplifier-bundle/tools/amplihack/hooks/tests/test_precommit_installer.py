#!/usr/bin/env python3
"""
Tests for precommit_installer hook.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from precommit_installer import PrecommitInstallerHook


class TestEnvironmentDisable(unittest.TestCase):
    """Test environment variable disabling (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        self.hook = PrecommitInstallerHook()

    def test_disabled_with_zero(self):
        """Test AMPLIHACK_AUTO_PRECOMMIT=0 disables hook."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "0"}):
            self.assertTrue(self.hook._is_env_disabled())

    def test_disabled_with_false(self):
        """Test AMPLIHACK_AUTO_PRECOMMIT=false disables hook."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "false"}):
            self.assertTrue(self.hook._is_env_disabled())

    def test_disabled_with_no(self):
        """Test AMPLIHACK_AUTO_PRECOMMIT=no disables hook."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "no"}):
            self.assertTrue(self.hook._is_env_disabled())

    def test_disabled_with_off(self):
        """Test AMPLIHACK_AUTO_PRECOMMIT=off disables hook."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "off"}):
            self.assertTrue(self.hook._is_env_disabled())

    def test_disabled_case_insensitive(self):
        """Test environment variable is case insensitive."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "FALSE"}):
            self.assertTrue(self.hook._is_env_disabled())

    def test_enabled_with_other_values(self):
        """Test other values don't disable hook."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "1"}):
            self.assertFalse(self.hook._is_env_disabled())
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "true"}):
            self.assertFalse(self.hook._is_env_disabled())

    def test_enabled_when_not_set(self):
        """Test hook enabled when environment variable not set."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.hook._is_env_disabled())


class TestPrecommitAvailability(unittest.TestCase):
    """Test pre-commit availability checking (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        self.hook = PrecommitInstallerHook()

    def test_precommit_available(self):
        """Test detection when pre-commit is available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="pre-commit 3.5.0\n",
                stderr="",
            )
            result = self.hook._is_precommit_available()

            self.assertTrue(result["available"])
            self.assertEqual(result["version"], "pre-commit 3.5.0")

    def test_precommit_not_found(self):
        """Test handling when pre-commit command not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = self.hook._is_precommit_available()

            self.assertFalse(result["available"])
            self.assertIn("not found in PATH", result["error"])

    def test_precommit_timeout(self):
        """Test handling when pre-commit check times out."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pre-commit", 5)):
            result = self.hook._is_precommit_available()

            self.assertFalse(result["available"])
            self.assertIn("timed out", result["error"])

    def test_precommit_os_error(self):
        """Test handling of OS errors."""
        with patch("subprocess.run", side_effect=OSError("Disk error")):
            result = self.hook._is_precommit_available()

            self.assertFalse(result["available"])
            self.assertIn("OS error", result["error"])

    def test_precommit_nonzero_exit(self):
        """Test handling when pre-commit returns non-zero exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="error",
            )
            result = self.hook._is_precommit_available()

            self.assertFalse(result["available"])
            self.assertIn("returned 1", result["error"])


class TestHooksInstalled(unittest.TestCase):
    """Test hook installation detection (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance and temp directory."""
        self.hook = PrecommitInstallerHook()
        self.temp_dir = tempfile.mkdtemp()
        self.hook.project_root = Path(self.temp_dir)
        self.hooks_dir = Path(self.temp_dir) / ".git" / "hooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        self.hook_file = self.hooks_dir / "pre-commit"

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_hooks_not_installed_file_missing(self):
        """Test detection when hook file doesn't exist."""
        result = self.hook._are_hooks_installed()
        self.assertFalse(result["installed"])

    def test_hooks_installed_valid_precommit(self):
        """Test detection when valid pre-commit hook exists."""
        self.hook_file.write_text(
            "#!/usr/bin/env python3\n"
            "# This is a pre-commit hook\n"
            "import sys\n"
            "from pre-commit import main\n"
            "sys.exit(main())\n"
        )
        result = self.hook._are_hooks_installed()
        self.assertTrue(result["installed"])

    def test_hooks_corrupted_too_small(self):
        """Test detection of corrupted hook (too small)."""
        self.hook_file.write_text("#!/bin/sh\n")
        result = self.hook._are_hooks_installed()

        self.assertFalse(result["installed"])
        self.assertTrue(result.get("corrupted", False))

    def test_hooks_corrupted_not_precommit(self):
        """Test detection when hook is not pre-commit managed."""
        self.hook_file.write_text(
            "#!/bin/bash\n"
            "# Custom hook that has nothing to do with pre-commit\n"
            "echo 'Running custom validation'\n"
            "exit 0\n"
        )
        result = self.hook._are_hooks_installed()

        self.assertFalse(result["installed"])
        self.assertTrue(result.get("corrupted", False))

    def test_hooks_permission_error(self):
        """Test handling of permission errors."""
        self.hook_file.write_text("content")
        with patch.object(Path, "read_text", side_effect=PermissionError()):
            result = self.hook._are_hooks_installed()

            self.assertFalse(result["installed"])
            self.assertIn("Permission denied", result["error"])

    def test_hooks_unicode_error(self):
        """Test handling of invalid text encoding."""
        self.hook_file.write_bytes(b"\xff\xfe\x00\x00invalid")
        result = self.hook._are_hooks_installed()

        self.assertFalse(result["installed"])
        self.assertTrue(result.get("corrupted", False))


class TestInstallHooks(unittest.TestCase):
    """Test hook installation (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        self.hook = PrecommitInstallerHook()

    def test_install_success(self):
        """Test successful hook installation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="pre-commit installed at .git/hooks/pre-commit\n",
                stderr="",
            )
            result = self.hook._install_hooks()

            self.assertTrue(result["success"])
            self.assertNotIn("error", result)

    def test_install_permission_denied(self):
        """Test handling of permission errors during installation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Permission denied writing to .git/hooks",
            )
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("Permission denied", result["error"])

    def test_install_network_error(self):
        """Test handling of network errors during installation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Network connection failed downloading hooks",
            )
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("Network error", result["error"])

    def test_install_invalid_config(self):
        """Test handling of invalid config file."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Invalid YAML in .pre-commit-config.yaml",
            )
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("Invalid .pre-commit-config.yaml", result["error"])

    def test_install_timeout(self):
        """Test handling of installation timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pre-commit", 30)):
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("timed out", result["error"])

    def test_install_file_not_found(self):
        """Test handling when pre-commit not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("not found", result["error"])

    def test_install_os_error(self):
        """Test handling of OS errors during installation."""
        with patch("subprocess.run", side_effect=OSError("Disk full")):
            result = self.hook._install_hooks()

            self.assertFalse(result["success"])
            self.assertIn("OS error", result["error"])


class TestProcessWorkflow(unittest.TestCase):
    """Test complete process workflow (Integration - 30%)."""

    def setUp(self):
        """Set up test hook instance."""
        self.hook = PrecommitInstallerHook()
        self.hook.project_root = Path(tempfile.mkdtemp())
        self.hook.log = MagicMock()
        self.hook.save_metric = MagicMock()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.hook.project_root, ignore_errors=True)

    def test_process_env_disabled(self):
        """Test process early exit when disabled via env."""
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "0"}):
            result = self.hook.process({})

            self.assertEqual(result, {})
            self.hook.save_metric.assert_called_with("precommit_env_disabled", True)

    def test_process_not_git_repo(self):
        """Test process early exit when not a git repo."""
        result = self.hook.process({})

        self.assertEqual(result, {})
        self.hook.save_metric.assert_called_with("precommit_not_git_repo", True)

    def test_process_no_config(self):
        """Test process early exit when no config file."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()

        result = self.hook.process({})

        self.assertEqual(result, {})
        self.hook.save_metric.assert_called_with("precommit_no_config", True)

    def test_process_precommit_not_available(self):
        """Test process when pre-commit not available."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.object(
            self.hook,
            "_is_precommit_available",
            return_value={"available": False, "error": "not found"},
        ):
            result = self.hook.process({})

            self.assertEqual(result, {})
            self.hook.save_metric.assert_called_with("precommit_available", False)

    def test_process_hooks_already_installed(self):
        """Test process when hooks already installed."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.object(
            self.hook,
            "_is_precommit_available",
            return_value={"available": True, "version": "3.5.0"},
        ):
            with patch.object(
                self.hook,
                "_are_hooks_installed",
                return_value={"installed": True},
            ):
                result = self.hook.process({})

                self.assertEqual(result, {})
                self.hook.save_metric.assert_called_with("precommit_already_installed", True)

    def test_process_successful_install(self):
        """Test complete successful installation workflow."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.object(
            self.hook,
            "_is_precommit_available",
            return_value={"available": True, "version": "3.5.0"},
        ):
            with patch.object(
                self.hook,
                "_are_hooks_installed",
                return_value={"installed": False},
            ):
                with patch.object(
                    self.hook,
                    "_install_hooks",
                    return_value={"success": True},
                ):
                    result = self.hook.process({})

                    self.assertEqual(result, {})
                    self.hook.save_metric.assert_called_with("precommit_installed", True)

    def test_process_failed_install(self):
        """Test workflow when installation fails."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.object(
            self.hook,
            "_is_precommit_available",
            return_value={"available": True, "version": "3.5.0"},
        ):
            with patch.object(
                self.hook,
                "_are_hooks_installed",
                return_value={"installed": False},
            ):
                with patch.object(
                    self.hook,
                    "_install_hooks",
                    return_value={"success": False, "error": "Permission denied"},
                ):
                    result = self.hook.process({})

                    self.assertEqual(result, {})
                    # Check both metrics were saved
                    calls = self.hook.save_metric.call_args_list
                    self.assertIn(call("precommit_installed", False), calls)
                    self.assertIn(call("precommit_install_error", "Permission denied"), calls)

    def test_process_graceful_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.object(
            self.hook,
            "_is_precommit_available",
            side_effect=Exception("Unexpected error"),
        ):
            result = self.hook.process({})

            self.assertEqual(result, {})
            # Should log error and save metric
            self.hook.log.assert_called()
            self.hook.save_metric.assert_called()


class TestEndToEnd(unittest.TestCase):
    """Test complete end-to-end scenarios (E2E - 10%)."""

    def test_main_entry_point(self):
        """Test main() entry point executes without errors."""
        from precommit_installer import main

        with patch("precommit_installer.PrecommitInstallerHook") as mock_hook_class:
            mock_instance = MagicMock()
            mock_hook_class.return_value = mock_instance

            main()

            mock_hook_class.assert_called_once()
            mock_instance.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
