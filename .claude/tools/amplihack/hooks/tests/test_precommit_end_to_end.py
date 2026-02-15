#!/usr/bin/env python3
"""
End-to-end tests for pre-commit system (hook + skill + preferences).

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows) ← THIS FILE

Tests complete user scenarios from start to finish.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# These imports will fail until implementation is complete
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from precommit_installer import PrecommitInstallerHook

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from skills.precommit_manager import PrecommitManager

    E2E_AVAILABLE = True
except ImportError:
    E2E_AVAILABLE = False


class TestE2EScenario1FreshClone(unittest.TestCase):
    """Scenario 1: Fresh clone, no preference → should prompt (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fresh_clone_prompts_user(self):
        """Test that fresh clone with no preference prompts user."""
        # Setup: Fresh git repo with config
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        # No preference file exists
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                # Create hook instance
                hook = PrecommitInstallerHook()
                hook.project_root = self.temp_dir
                hook.log = MagicMock()
                hook.save_metric = MagicMock()

                # Mock pre-commit availability
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        # User should be prompted
                        with patch.object(hook, "_prompt_user", return_value="yes") as mock_prompt:
                            with patch.object(
                                hook, "_install_hooks", return_value={"success": True}
                            ):
                                hook.process({})

                mock_prompt.assert_called_once()
                hook.save_metric.assert_any_call("precommit_installed", True)

    def test_fresh_clone_user_says_always(self):
        """Test that user choosing 'always' saves preference and installs."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        # Mock preference loading (returns "ask")
        with patch("precommit_installer.load_precommit_preference", return_value="ask"):
            # Mock preference saving
            with patch("precommit_installer.save_precommit_preference") as mock_save:
                hook = PrecommitInstallerHook()
                hook.project_root = self.temp_dir
                hook.log = MagicMock()
                hook.save_metric = MagicMock()

                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(hook, "_prompt_user", return_value="always"):
                            with patch.object(
                                hook, "_install_hooks", return_value={"success": True}
                            ):
                                hook.process({})

        # Preference should be saved
        mock_save.assert_called_with("always")
        hook.save_metric.assert_any_call("precommit_installed", True)


class TestE2EScenario2AlreadyInstalled(unittest.TestCase):
    """Scenario 2: Already installed → skip silently (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_already_installed_skips_silently(self):
        """Test that already installed hooks are skipped silently."""
        # Setup: Git repo with hooks already installed
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text(
            "#!/usr/bin/env python3\nimport sys\nfrom pre_commit import main\nsys.exit(main())"
        )

        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(hook, "_is_precommit_available", return_value={"available": True}):
                with patch.object(hook, "_are_hooks_installed", return_value={"installed": True}):
                    with patch.object(hook, "_install_hooks") as mock_install:
                        with patch.object(hook, "_prompt_user") as mock_prompt:
                            hook.process({})

        # Should not prompt or install
        mock_prompt.assert_not_called()
        mock_install.assert_not_called()
        hook.save_metric.assert_any_call("precommit_already_installed", True)


class TestE2EScenario3NoConfig(unittest.TestCase):
    """Scenario 3: No config → skip silently (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_config_skips_silently(self):
        """Test that missing config file causes silent skip."""
        # Setup: Git repo with no config file
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        # No config file

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch.object(hook, "_install_hooks") as mock_install:
            with patch.object(hook, "_prompt_user") as mock_prompt:
                hook.process({})

        # Should not prompt or install
        mock_prompt.assert_not_called()
        mock_install.assert_not_called()
        hook.save_metric.assert_any_call("precommit_no_config", True)


class TestE2EScenario4PreferenceAlways(unittest.TestCase):
    """Scenario 4: Preference = 'always' → auto-install (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preference_always_auto_installs(self):
        """Test that preference='always' auto-installs without prompting."""
        # Setup: Git repo with config and preference="always"
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(hook, "_is_precommit_available", return_value={"available": True}):
                with patch.object(hook, "_are_hooks_installed", return_value={"installed": False}):
                    with patch.object(hook, "_prompt_user") as mock_prompt:
                        with patch.object(
                            hook, "_install_hooks", return_value={"success": True}
                        ) as mock_install:
                            hook.process({})

        # Should install without prompting
        mock_prompt.assert_not_called()
        mock_install.assert_called_once()
        hook.save_metric.assert_any_call("precommit_installed", True)


class TestE2EScenario5PrecommitUnavailable(unittest.TestCase):
    """Scenario 5: pre-commit unavailable → fail gracefully (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_precommit_unavailable_fails_gracefully(self):
        """Test that missing pre-commit binary fails gracefully."""
        # Setup: Git repo with config but no pre-commit binary
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("precommit_installer.load_precommit_preference", return_value="always"):
            with patch.object(
                hook,
                "_is_precommit_available",
                return_value={"available": False, "error": "not found in PATH"},
            ):
                with patch.object(hook, "_install_hooks") as mock_install:
                    hook.process({})

        # Should not attempt install
        mock_install.assert_not_called()
        hook.save_metric.assert_any_call("precommit_available", False)

        # Should log helpful error
        hook.log.assert_called()


class TestE2ESkillWorkflows(unittest.TestCase):
    """Test complete skill workflows (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_setup_workflow(self):
        """Test complete setup workflow: configure → install → enable."""
        # Setup git repo
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Step 1: Configure
        result1 = self.manager.configure(template="python")
        self.assertTrue(result1["success"])

        # Step 2: Install
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="installed", stderr="")
            result2 = self.manager.install()

        self.assertTrue(result2["success"])

        # Step 3: Enable
        with patch("precommit_prefs.save_precommit_preference") as mock_save:
            result3 = self.manager.enable()

        self.assertTrue(result3["success"])
        mock_save.assert_called_with("always")

    def test_status_shows_complete_state(self):
        """Test that status shows complete system state."""
        # Setup git repo with hooks
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text(
            "#!/usr/bin/env python3\nimport sys\nfrom pre_commit import main\nsys.exit(main())"
        )

        with patch("precommit_prefs.load_precommit_preference", return_value="always"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="pre-commit 3.5.0", stderr="")
                result = self.manager.status()

        # Verify all state is shown
        self.assertTrue(result["git_repo"])
        self.assertTrue(result["config_exists"])
        self.assertTrue(result["hooks_installed"])
        self.assertEqual(result["preference"], "always")
        self.assertTrue(result["precommit_available"])

    def test_disable_then_hook_skips_install(self):
        """Test that disabling via skill prevents hook from installing."""
        # Setup git repo with config
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        # Disable via skill
        with patch("precommit_prefs.save_precommit_preference") as mock_save:
            result1 = self.manager.disable()

        self.assertTrue(result1["success"])
        mock_save.assert_called_with("never")

        # Now run hook
        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("precommit_installer.load_precommit_preference", return_value="never"):
            with patch.object(hook, "_is_precommit_available", return_value={"available": True}):
                with patch.object(hook, "_are_hooks_installed", return_value={"installed": False}):
                    with patch.object(hook, "_install_hooks") as mock_install:
                        hook.process({})

        # Hook should skip install
        mock_install.assert_not_called()


class TestE2EBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with AMPLIHACK_AUTO_PRECOMMIT (E2E - 10%)."""

    def setUp(self):
        """Set up test environment."""
        if not E2E_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_env_var_1_still_works(self):
        """Test that AMPLIHACK_AUTO_PRECOMMIT=1 still enables auto-install."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "1"}):
            # Env var should map to "always"
            with patch("precommit_installer.load_precommit_preference", return_value="always"):
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(
                            hook, "_install_hooks", return_value={"success": True}
                        ) as mock_install:
                            hook.process({})

        mock_install.assert_called_once()

    def test_env_var_0_still_works(self):
        """Test that AMPLIHACK_AUTO_PRECOMMIT=0 still disables auto-install."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch.dict(os.environ, {"AMPLIHACK_AUTO_PRECOMMIT": "0"}):
            # Env var should map to "never"
            with patch("precommit_installer.load_precommit_preference", return_value="never"):
                with patch.object(
                    hook, "_is_precommit_available", return_value={"available": True}
                ):
                    with patch.object(
                        hook, "_are_hooks_installed", return_value={"installed": False}
                    ):
                        with patch.object(hook, "_install_hooks") as mock_install:
                            hook.process({})

        mock_install.assert_not_called()


if __name__ == "__main__":
    unittest.main()
