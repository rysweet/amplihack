#!/usr/bin/env python3
"""
Tests for enhanced precommit_installer hook with preference system.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

Tests the enhanced hook that:
1. Checks preferences before auto-install
2. Prompts user for "ask" mode
3. Offers config generation
4. Maintains backward compatibility with AMPLIHACK_AUTO_PRECOMMIT
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# These imports will fail until implementation is complete
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from precommit_installer import PrecommitInstallerHook

    PRECOMMIT_INSTALLER_AVAILABLE = True
except ImportError:
    PRECOMMIT_INSTALLER_AVAILABLE = False


class TestPreferenceChecking(unittest.TestCase):
    """Test preference checking before auto-install (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        if not PRECOMMIT_INSTALLER_AVAILABLE:
            self.skipTest("Enhanced precommit_installer not implemented yet")
        self.hook = PrecommitInstallerHook()
        self.hook.project_root = Path(tempfile.mkdtemp())
        self.hook.log = MagicMock()
        self.hook.save_metric = MagicMock()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.hook.project_root, ignore_errors=True)

    def test_preference_always_triggers_auto_install(self):
        """Test that preference='always' triggers automatic installation."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(
                        self.hook, "_install_hooks", return_value={"success": True}
                    ) as mock_install:
                        self.hook.process({})

        mock_install.assert_called_once()

    def test_preference_never_skips_install_silently(self):
        """Test that preference='never' skips install without prompting."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="never"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_install_hooks") as mock_install:
                        with patch.object(self.hook, "_prompt_user") as mock_prompt:
                            self.hook.process({})

        mock_install.assert_not_called()
        mock_prompt.assert_not_called()
        self.hook.save_metric.assert_any_call("precommit_preference_never", True)

    def test_preference_ask_prompts_user(self):
        """Test that preference='ask' prompts user for decision."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_prompt_user", return_value="yes") as mock_prompt:
                        with patch.object(
                            self.hook, "_install_hooks", return_value={"success": True}
                        ):
                            self.hook.process({})

        mock_prompt.assert_called_once()

    def test_backward_compat_env_var_always(self):
        """Test backward compatibility with AMPLIHACK_AUTO_PRECOMMIT=1."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        # When env var is set, it should override "ask" default
        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "1"}):
            with patch("precommit_installer.load_precommit_preference", return_value="always"):
                with patch.object(
                    self.hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        self.hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(
                            self.hook, "_install_hooks", return_value={"success": True}
                        ) as mock_install:
                            self.hook.process({})

        mock_install.assert_called_once()

    def test_backward_compat_env_var_never(self):
        """Test backward compatibility with AMPLIHACK_AUTO_PRECOMMIT=0."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "0"}):
            with patch("precommit_installer.load_precommit_preference", return_value="never"):
                with patch.object(
                    self.hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        self.hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(self.hook, "_install_hooks") as mock_install:
                            self.hook.process({})

        mock_install.assert_not_called()


class TestUserPrompting(unittest.TestCase):
    """Test user prompting for 'ask' mode (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        if not PRECOMMIT_INSTALLER_AVAILABLE:
            self.skipTest("Enhanced precommit_installer not implemented yet")
        self.hook = PrecommitInstallerHook()

    def test_prompt_user_yes_returns_yes(self):
        """Test that user answering 'yes' returns 'yes'."""
        with patch("builtins.input", return_value="yes"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "yes")

    def test_prompt_user_y_returns_yes(self):
        """Test that user answering 'y' returns 'yes'."""
        with patch("builtins.input", return_value="y"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "yes")

    def test_prompt_user_no_returns_no(self):
        """Test that user answering 'no' returns 'no'."""
        with patch("builtins.input", return_value="no"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "no")

    def test_prompt_user_n_returns_no(self):
        """Test that user answering 'n' returns 'no'."""
        with patch("builtins.input", return_value="n"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "no")

    def test_prompt_user_always_returns_always(self):
        """Test that user answering 'always' returns 'always'."""
        with patch("builtins.input", return_value="always"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "always")

    def test_prompt_user_never_returns_never(self):
        """Test that user answering 'never' returns 'never'."""
        with patch("builtins.input", return_value="never"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "never")

    def test_prompt_user_case_insensitive(self):
        """Test that prompt is case insensitive."""
        with patch("builtins.input", return_value="YES"):
            result = self.hook._prompt_user()

        self.assertEqual(result, "yes")

    def test_prompt_user_strips_whitespace(self):
        """Test that prompt strips whitespace."""
        with patch("builtins.input", return_value="  yes  "):
            result = self.hook._prompt_user()

        self.assertEqual(result, "yes")

    def test_prompt_user_invalid_input_reprompts(self):
        """Test that invalid input causes re-prompt."""
        with patch("builtins.input", side_effect=["invalid", "maybe", "yes"]):
            result = self.hook._prompt_user()

        self.assertEqual(result, "yes")

    def test_prompt_user_eof_error_returns_no(self):
        """Test that EOF error (Ctrl+D) defaults to 'no'."""
        with patch("builtins.input", side_effect=EOFError()):
            result = self.hook._prompt_user()

        self.assertEqual(result, "no")

    def test_prompt_user_keyboard_interrupt_returns_no(self):
        """Test that KeyboardInterrupt (Ctrl+C) defaults to 'no'."""
        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            result = self.hook._prompt_user()

        self.assertEqual(result, "no")


class TestPreferenceSaving(unittest.TestCase):
    """Test that user choices are saved to preferences (Integration - 30%)."""

    def setUp(self):
        """Set up test hook instance."""
        if not PRECOMMIT_INSTALLER_AVAILABLE:
            self.skipTest("Enhanced precommit_installer not implemented yet")
        self.hook = PrecommitInstallerHook()
        self.hook.project_root = Path(tempfile.mkdtemp())
        self.hook.log = MagicMock()
        self.hook.save_metric = MagicMock()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.hook.project_root, ignore_errors=True)

    def test_user_choice_always_saved_to_prefs(self):
        """Test that user choosing 'always' saves preference."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_prompt_user", return_value="always"):
                        with patch("precommit_installer.save_precommit_preference") as mock_save:
                            with patch.object(
                                self.hook, "_install_hooks", return_value={"success": True}
                            ):
                                self.hook.process({})

        mock_save.assert_called_with("always")

    def test_user_choice_never_saved_to_prefs(self):
        """Test that user choosing 'never' saves preference."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_prompt_user", return_value="never"):
                        with patch("precommit_installer.save_precommit_preference") as mock_save:
                            with patch.object(self.hook, "_install_hooks") as mock_install:
                                self.hook.process({})

        mock_save.assert_called_with("never")
        mock_install.assert_not_called()

    def test_user_choice_yes_not_saved_to_prefs(self):
        """Test that user choosing 'yes' (one-time) doesn't save preference."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_prompt_user", return_value="yes"):
                        with patch("precommit_installer.save_precommit_preference") as mock_save:
                            with patch.object(
                                self.hook, "_install_hooks", return_value={"success": True}
                            ):
                                self.hook.process({})

        # Should install but not save preference
        mock_save.assert_not_called()

    def test_user_choice_no_not_saved_to_prefs(self):
        """Test that user choosing 'no' (one-time) doesn't save preference."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(self.hook, "_prompt_user", return_value="no"):
                        with patch("precommit_installer.save_precommit_preference") as mock_save:
                            with patch.object(self.hook, "_install_hooks") as mock_install:
                                self.hook.process({})

        # Should skip install and not save preference
        mock_save.assert_not_called()
        mock_install.assert_not_called()


class TestGracefulFailures(unittest.TestCase):
    """Test graceful handling of missing pre-commit and corrupted config (Unit - 60%)."""

    def setUp(self):
        """Set up test hook instance."""
        if not PRECOMMIT_INSTALLER_AVAILABLE:
            self.skipTest("Enhanced precommit_installer not implemented yet")
        self.hook = PrecommitInstallerHook()
        self.hook.project_root = Path(tempfile.mkdtemp())
        self.hook.log = MagicMock()
        self.hook.save_metric = MagicMock()

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.hook.project_root, ignore_errors=True)

    def test_missing_precommit_binary_fails_gracefully(self):
        """Test that missing pre-commit binary fails gracefully."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(
                self.hook,
                "_is_precommit_available",
                return_value={"available": False, "error": "not found"},
            ):
                result = self.hook.process({})

        self.assertEqual(result, {})
        self.hook.log.assert_called()
        self.hook.save_metric.assert_any_call("precommit_available", False)

    def test_corrupted_config_yaml_handled(self):
        """Test that corrupted YAML config is handled gracefully."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("this is: not: valid: yaml: {{{{")

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(
                        self.hook,
                        "_install_hooks",
                        return_value={"success": False, "error": "Invalid YAML"},
                    ):
                        result = self.hook.process({})

        self.assertEqual(result, {})
        self.hook.save_metric.assert_any_call("precommit_installed", False)

    def test_permission_error_during_install_handled(self):
        """Test that permission errors during install are handled."""
        git_dir = self.hook.project_root / ".git"
        git_dir.mkdir()
        config_file = self.hook.project_root / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(
                self.hook, "_is_precommit_available", return_value={"available": True}
            ):
                with patch.object(
                    self.hook, "_are_hooks_installed", return_value={"installed": False}
                ):
                    with patch.object(
                        self.hook,
                        "_install_hooks",
                        return_value={"success": False, "error": "Permission denied"},
                    ):
                        result = self.hook.process({})

        self.assertEqual(result, {})
        self.hook.save_metric.assert_any_call("precommit_install_error", "Permission denied")


class TestEndToEndScenarios(unittest.TestCase):
    """Test complete end-to-end scenarios (E2E - 10%)."""

    def setUp(self):
        """Set up test hook instance."""
        if not PRECOMMIT_INSTALLER_AVAILABLE:
            self.skipTest("Enhanced precommit_installer not implemented yet")

    def test_scenario_fresh_clone_no_preference(self):
        """Test fresh clone scenario with no preference set (should prompt)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            hook = PrecommitInstallerHook()
            hook.project_root = temp_dir
            hook.log = MagicMock()
            hook.save_metric = MagicMock()

            git_dir = temp_dir / ".git"
            git_dir.mkdir()
            config_file = temp_dir / ".pre-commit-config.yaml"
            config_file.write_text("repos: []")

            with patch("precommit_installer.load_precommit_preference", return_value="ask"):
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(hook, "_prompt_user", return_value="yes"):
                            with patch.object(
                                hook, "_install_hooks", return_value={"success": True}
                            ):
                                hook.process({})

            hook.save_metric.assert_any_call("precommit_installed", True)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_scenario_already_installed_skip_silently(self):
        """Test scenario where hooks already installed (should skip silently)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            hook = PrecommitInstallerHook()
            hook.project_root = temp_dir
            hook.log = MagicMock()
            hook.save_metric = MagicMock()

            git_dir = temp_dir / ".git"
            git_dir.mkdir()
            config_file = temp_dir / ".pre-commit-config.yaml"
            config_file.write_text("repos: []")

            with patch("precommit_installer.load_precommit_preference", return_value="ask"):
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": True}
                    ):
                        with patch.object(hook, "_install_hooks") as mock_install:
                            hook.process({})

            mock_install.assert_not_called()
            hook.save_metric.assert_any_call("precommit_already_installed", True)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_scenario_no_config_skip_silently(self):
        """Test scenario with no config file (should skip silently)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            hook = PrecommitInstallerHook()
            hook.project_root = temp_dir
            hook.log = MagicMock()
            hook.save_metric = MagicMock()

            git_dir = temp_dir / ".git"
            git_dir.mkdir()
            # No config file

            with patch.object(hook, "_install_hooks") as mock_install:
                with patch.object(hook, "_prompt_user") as mock_prompt:
                    hook.process({})

            mock_install.assert_not_called()
            mock_prompt.assert_not_called()
            hook.save_metric.assert_any_call("precommit_no_config", True)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_scenario_preference_always_auto_install(self):
        """Test scenario with preference='always' (should auto-install)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            hook = PrecommitInstallerHook()
            hook.project_root = temp_dir
            hook.log = MagicMock()
            hook.save_metric = MagicMock()

            git_dir = temp_dir / ".git"
            git_dir.mkdir()
            config_file = temp_dir / ".pre-commit-config.yaml"
            config_file.write_text("repos: []")

            with patch("precommit_installer.load_precommit_preference", return_value="always"):
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(hook, "_prompt_user") as mock_prompt:
                            with patch.object(
                                hook, "_install_hooks", return_value={"success": True}
                            ) as mock_install:
                                hook.process({})

            mock_prompt.assert_not_called()
            mock_install.assert_called_once()
            hook.save_metric.assert_any_call("precommit_installed", True)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_scenario_precommit_unavailable_fail_gracefully(self):
        """Test scenario where pre-commit binary unavailable (fail gracefully)."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            hook = PrecommitInstallerHook()
            hook.project_root = temp_dir
            hook.log = MagicMock()
            hook.save_metric = MagicMock()

            git_dir = temp_dir / ".git"
            git_dir.mkdir()
            config_file = temp_dir / ".pre-commit-config.yaml"
            config_file.write_text("repos: []")

            with patch("precommit_installer.load_precommit_preference", return_value="always"):
                with patch.object(
                    hook,
                    "_is_precommit_available",
                    return_value={"available": False, "error": "not found in PATH"},
                ):
                    with patch.object(hook, "_install_hooks") as mock_install:
                        hook.process({})

            mock_install.assert_not_called()
            hook.save_metric.assert_any_call("precommit_available", False)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
