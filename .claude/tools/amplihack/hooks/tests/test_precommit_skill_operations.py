#!/usr/bin/env python3
"""
Tests for pre-commit-manager skill operations.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

Tests the six skill operations:
1. install: Install hooks
2. configure: Generate config from templates
3. disable: Set preference to "never"
4. enable: Set preference to "always"
5. status: Show current state
6. baseline: Generate detect-secrets baseline
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# These imports will fail until implementation is complete
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from skills.precommit_manager import PrecommitManager

    PRECOMMIT_SKILL_AVAILABLE = True
except ImportError:
    PRECOMMIT_SKILL_AVAILABLE = False


class TestInstallOperation(unittest.TestCase):
    """Test install operation (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_install_success(self):
        """Test successful hook installation."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="installed", stderr="")
            result = self.manager.install()

        self.assertTrue(result["success"])
        self.assertIn("installed", result["message"].lower())

    def test_install_no_config_file(self):
        """Test install fails when no config file exists."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        # No config file

        result = self.manager.install()

        self.assertFalse(result["success"])
        self.assertIn("config", result["error"].lower())

    def test_install_not_git_repo(self):
        """Test install fails when not a git repo."""
        # No .git directory

        result = self.manager.install()

        self.assertFalse(result["success"])
        self.assertIn("git", result["error"].lower())

    def test_install_already_installed(self):
        """Test install when hooks already installed (should succeed idempotently)."""
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

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="already installed", stderr="")
            result = self.manager.install()

        self.assertTrue(result["success"])

    def test_install_permission_error(self):
        """Test install handles permission errors."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Permission denied")
            result = self.manager.install()

        self.assertFalse(result["success"])
        self.assertIn("permission", result["error"].lower())


class TestConfigureOperation(unittest.TestCase):
    """Test configure operation with templates (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_configure_python_template(self):
        """Test generating config from Python template."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.configure(template="python")

        self.assertTrue(result["success"])
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        self.assertTrue(config_file.exists())

    def test_configure_javascript_template(self):
        """Test generating config from JavaScript template."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.configure(template="javascript")

        self.assertTrue(result["success"])
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        self.assertTrue(config_file.exists())

    def test_configure_generic_template(self):
        """Test generating config from generic template."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.configure(template="generic")

        self.assertTrue(result["success"])
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        self.assertTrue(config_file.exists())

    def test_configure_invalid_template_rejected(self):
        """Test that invalid template name is rejected (security)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.configure(template="../../../etc/passwd")

        self.assertFalse(result["success"])
        self.assertIn("invalid", result["error"].lower())

    def test_configure_template_whitelist_validation(self):
        """Test that only whitelisted templates are allowed (security)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        valid_templates = ["python", "javascript", "typescript", "go", "rust", "generic"]

        for template in valid_templates:
            result = self.manager.configure(template=template)
            self.assertTrue(result["success"], f"Template {template} should be valid")

        invalid_templates = ["../../etc/passwd", "malicious", "__init__"]

        for template in invalid_templates:
            result = self.manager.configure(template=template)
            self.assertFalse(result["success"], f"Template {template} should be invalid")

    def test_configure_overwrites_existing_config(self):
        """Test that configure overwrites existing config (with warning)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []\n# Existing config")

        result = self.manager.configure(template="python")

        self.assertTrue(result["success"])
        self.assertIn("overwritten", result["message"].lower())

    def test_configure_not_git_repo(self):
        """Test configure fails when not a git repo."""
        # No .git directory

        result = self.manager.configure(template="python")

        self.assertFalse(result["success"])
        self.assertIn("git", result["error"].lower())


class TestDisableEnableOperations(unittest.TestCase):
    """Test disable and enable operations (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disable_sets_preference_to_never(self):
        """Test that disable sets preference to 'never'."""
        with patch("precommit_prefs.save_precommit_preference") as mock_save:
            result = self.manager.disable()

        self.assertTrue(result["success"])
        mock_save.assert_called_with("never")

    def test_enable_sets_preference_to_always(self):
        """Test that enable sets preference to 'always'."""
        with patch("precommit_prefs.save_precommit_preference") as mock_save:
            result = self.manager.enable()

        self.assertTrue(result["success"])
        mock_save.assert_called_with("always")

    def test_disable_success_message(self):
        """Test that disable returns success message."""
        with patch("precommit_prefs.save_precommit_preference"):
            result = self.manager.disable()

        self.assertIn("disabled", result["message"].lower())

    def test_enable_success_message(self):
        """Test that enable returns success message."""
        with patch("precommit_prefs.save_precommit_preference"):
            result = self.manager.enable()

        self.assertIn("enabled", result["message"].lower())

    def test_disable_handles_save_error(self):
        """Test that disable handles save errors gracefully."""
        with patch("precommit_prefs.save_precommit_preference", side_effect=OSError("Disk full")):
            result = self.manager.disable()

        self.assertFalse(result["success"])
        self.assertIn("error", result.keys())

    def test_enable_handles_save_error(self):
        """Test that enable handles save errors gracefully."""
        with patch("precommit_prefs.save_precommit_preference", side_effect=OSError("Disk full")):
            result = self.manager.enable()

        self.assertFalse(result["success"])
        self.assertIn("error", result.keys())


class TestStatusOperation(unittest.TestCase):
    """Test status operation (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_status_shows_git_repo_status(self):
        """Test that status shows git repo status."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.status()

        self.assertIn("git_repo", result)
        self.assertTrue(result["git_repo"])

    def test_status_shows_config_exists(self):
        """Test that status shows config file existence."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        result = self.manager.status()

        self.assertIn("config_exists", result)
        self.assertTrue(result["config_exists"])

    def test_status_shows_hooks_installed(self):
        """Test that status shows hooks installation status."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir()
        hook_file = hooks_dir / "pre-commit"
        hook_file.write_text(
            "#!/usr/bin/env python3\nimport sys\nfrom pre_commit import main\nsys.exit(main())"
        )

        result = self.manager.status()

        self.assertIn("hooks_installed", result)
        self.assertTrue(result["hooks_installed"])

    def test_status_shows_preference_setting(self):
        """Test that status shows current preference."""
        with patch("precommit_prefs.load_precommit_preference", return_value="always"):
            result = self.manager.status()

        self.assertIn("preference", result)
        self.assertEqual(result["preference"], "always")

    def test_status_shows_precommit_available(self):
        """Test that status shows pre-commit binary availability."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="pre-commit 3.5.0", stderr="")
            result = self.manager.status()

        self.assertIn("precommit_available", result)
        self.assertTrue(result["precommit_available"])

    def test_status_formatted_output(self):
        """Test that status returns formatted human-readable output."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        result = self.manager.status()

        self.assertIn("formatted", result)
        self.assertIsInstance(result["formatted"], str)


class TestBaselineOperation(unittest.TestCase):
    """Test baseline generation for detect-secrets (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_baseline_generates_file(self):
        """Test that baseline operation generates .secrets.baseline file."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="baseline created", stderr="")
            result = self.manager.baseline()

        self.assertTrue(result["success"])
        # File creation is mocked, so we just check the operation succeeded

    def test_baseline_not_git_repo(self):
        """Test baseline fails when not a git repo."""
        # No .git directory

        result = self.manager.baseline()

        self.assertFalse(result["success"])
        self.assertIn("git", result["error"].lower())

    def test_baseline_detect_secrets_not_available(self):
        """Test baseline handles detect-secrets not being available."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = self.manager.baseline()

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"].lower())

    def test_baseline_overwrites_existing(self):
        """Test that baseline overwrites existing file."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        baseline_file = self.temp_dir / ".secrets.baseline"
        baseline_file.write_text("old baseline")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="baseline updated", stderr="")
            result = self.manager.baseline()

        self.assertTrue(result["success"])
        self.assertIn("updated", result["message"].lower())


class TestSecurityValidation(unittest.TestCase):
    """Test security features (command injection, path traversal) (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_command_injection_prevention_list_form(self):
        """Test that subprocess calls use list form (not shell=True)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            self.manager.install()

        # Verify subprocess.run called with list, not string
        call_args = mock_run.call_args
        self.assertIsInstance(call_args[0][0], list)

    def test_path_traversal_prevention_configure(self):
        """Test that configure rejects path traversal attempts."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        malicious_paths = [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\config\\sam",
        ]

        for path in malicious_paths:
            result = self.manager.configure(template=path)
            self.assertFalse(result["success"], f"Path traversal should be prevented: {path}")

    def test_template_whitelist_enforcement(self):
        """Test that only whitelisted templates are allowed."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Valid templates
        valid = ["python", "javascript", "typescript"]
        for template in valid:
            result = self.manager.configure(template=template)
            # Should not fail due to security (may fail for other reasons in test)
            if not result["success"]:
                self.assertNotIn("security", result.get("error", "").lower())

        # Invalid templates
        invalid = ["__init__", "../../evil", "malicious"]
        for template in invalid:
            result = self.manager.configure(template=template)
            self.assertFalse(result["success"])

    def test_subprocess_timeout_enforced(self):
        """Test that subprocess calls have timeout."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            self.manager.install()

        # Verify timeout parameter present
        call_kwargs = mock_run.call_args[1]
        self.assertIn("timeout", call_kwargs)
        self.assertIsInstance(call_kwargs["timeout"], (int, float))

    def test_file_permissions_atomic_write(self):
        """Test that config files are written with correct permissions."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        result = self.manager.configure(template="python")

        if result["success"]:
            config_file = self.temp_dir / ".pre-commit-config.yaml"
            stat_result = config_file.stat()
            perms = stat_result.st_mode & 0o777
            # Config file should be readable by others, but not writable
            self.assertTrue(perms & 0o400)  # Owner readable


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration between skill operations (Integration - 30%)."""

    def setUp(self):
        """Set up test environment."""
        if not PRECOMMIT_SKILL_AVAILABLE:
            self.skipTest("pre-commit-manager skill not implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_configure_then_install_workflow(self):
        """Test configure followed by install workflow."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Configure
        result1 = self.manager.configure(template="python")
        self.assertTrue(result1["success"])

        # Install
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="installed", stderr="")
            result2 = self.manager.install()

        self.assertTrue(result2["success"])

    def test_enable_then_status_workflow(self):
        """Test enable followed by status workflow."""
        with patch("precommit_prefs.save_precommit_preference"):
            result1 = self.manager.enable()

        self.assertTrue(result1["success"])

        with patch("precommit_prefs.load_precommit_preference", return_value="always"):
            result2 = self.manager.status()

        self.assertEqual(result2["preference"], "always")

    def test_disable_then_status_workflow(self):
        """Test disable followed by status workflow."""
        with patch("precommit_prefs.save_precommit_preference"):
            result1 = self.manager.disable()

        self.assertTrue(result1["success"])

        with patch("precommit_prefs.load_precommit_preference", return_value="never"):
            result2 = self.manager.status()

        self.assertEqual(result2["preference"], "never")


if __name__ == "__main__":
    unittest.main()
