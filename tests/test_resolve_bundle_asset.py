# File: tests/test_resolve_bundle_asset.py
"""Test suite for src/amplihack/resolve_bundle_asset.py

Covers:
  - Module importability and public API
  - $AMPLIHACK_HOME priority resolution (valid, invalid, missing)
  - Package install and editable install fallbacks
  - Regression: running from /tmp (non-amplihack directory)
  - Path traversal prevention and input validation
  - "No valid path" error messages and exit codes
  - Output safety (single line, absolute, shell-safe characters)
  - CLI interface contract
  - Directory asset resolution (HOOKS_DIR pattern)
  - Fallback chain ordering
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
_MODULE_PATH = REPO_ROOT / "src" / "amplihack" / "resolve_bundle_asset.py"
_ORCH_HELPER_REL = "amplifier-bundle/tools/orch_helper.py"
_SESSION_TREE_REL = "amplifier-bundle/tools/session_tree.py"
_HOOKS_DIR_REL = "amplifier-bundle/tools/amplihack/hooks"


def _run_module(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run ``python3 -m amplihack.resolve_bundle_asset`` with *args*."""
    run_env = {**os.environ}
    if env is not None:
        run_env.update(env)
    # Ensure src/ is on PYTHONPATH so the module is importable.
    src_dir = str(REPO_ROOT / "src")
    run_env["PYTHONPATH"] = src_dir + os.pathsep + run_env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "amplihack.resolve_bundle_asset", *args],
        capture_output=True,
        text=True,
        env=run_env,
    )


def _import_module():
    """Import and return the resolve_bundle_asset module."""
    spec = importlib.util.spec_from_file_location(
        "amplihack.resolve_bundle_asset", _MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# 1. Module exists and is importable
# ─────────────────────────────────────────────────────────────────────────────

class TestModuleExists(unittest.TestCase):
    """The module file must exist and expose the correct public API."""

    def test_module_file_exists(self):
        self.assertTrue(
            _MODULE_PATH.exists(),
            f"resolve_bundle_asset.py not found at: {_MODULE_PATH}",
        )

    def test_module_is_importable(self):
        mod = _import_module()
        self.assertIsNotNone(mod)

    def test_resolve_asset_is_callable(self):
        mod = _import_module()
        self.assertTrue(callable(getattr(mod, "resolve_asset", None)))

    def test_validate_relative_path_is_callable(self):
        mod = _import_module()
        self.assertTrue(callable(getattr(mod, "_validate_relative_path", None)))


# ─────────────────────────────────────────────────────────────────────────────
# 2. $AMPLIHACK_HOME resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestAmplihackHomeResolution(unittest.TestCase):
    """$AMPLIHACK_HOME has highest priority in the fallback chain."""

    def test_valid_amplihack_home_resolves_orch_helper(self):
        """When AMPLIHACK_HOME points to the repo root, orch_helper.py is found."""
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        resolved = Path(result.stdout.strip())
        self.assertTrue(resolved.is_file(), f"Expected file at: {resolved}")
        self.assertTrue(str(resolved).endswith("orch_helper.py"))

    def test_invalid_amplihack_home_falls_back_and_warns(self):
        """When AMPLIHACK_HOME is a non-existent directory, warn and fall back."""
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": "/nonexistent/path/that/does/not/exist"},
        )
        # Should still succeed via fallback (the repo root contains the file)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Warning must appear on stderr — must NOT print the env var value
        self.assertIn("WARNING", result.stderr)
        self.assertIn("AMPLIHACK_HOME", result.stderr)
        self.assertNotIn("/nonexistent", result.stderr, "Should not leak AMPLIHACK_HOME value")

    def test_amplihack_home_set_to_file_warns_and_falls_back(self):
        """When AMPLIHACK_HOME points to a file (not a dir), warn and fall back."""
        some_file = str(_MODULE_PATH)
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": some_file},
        )
        self.assertEqual(result.returncode, 0, f"Should fall back; stderr: {result.stderr}")
        self.assertIn("WARNING", result.stderr)

    def test_amplihack_home_takes_priority_over_pkg_dir(self):
        """$AMPLIHACK_HOME must be tried before pkg_dir candidates."""
        # When AMPLIHACK_HOME is valid, the returned path should be under it.
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        resolved = result.stdout.strip()
        self.assertTrue(
            resolved.startswith(str(REPO_ROOT)),
            f"Expected path under AMPLIHACK_HOME={REPO_ROOT}, got: {resolved}",
        )

    def test_amplihack_home_unset_uses_fallback(self):
        """Without $AMPLIHACK_HOME, fallback candidates are tried."""
        env = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_HOME"}
        result = _run_module(_ORCH_HELPER_REL, env={**env, "AMPLIHACK_HOME": ""})
        self.assertEqual(result.returncode, 0, f"Fallback failed; stderr: {result.stderr}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Package install / editable install fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageInstallResolution(unittest.TestCase):
    """Fallback candidates (pkg_dir and editable install) find assets."""

    def test_resolve_asset_python_api_finds_orch_helper(self):
        """resolve_asset() Python API resolves orch_helper.py."""
        mod = _import_module()
        env_backup = os.environ.pop("AMPLIHACK_HOME", None)
        try:
            resolved = mod.resolve_asset(_ORCH_HELPER_REL)
            self.assertTrue(resolved.exists(), f"Expected file at: {resolved}")
            self.assertTrue(str(resolved).endswith("orch_helper.py"))
        finally:
            if env_backup is not None:
                os.environ["AMPLIHACK_HOME"] = env_backup

    def test_resolve_asset_python_api_finds_session_tree(self):
        """resolve_asset() Python API resolves session_tree.py."""
        mod = _import_module()
        resolved = mod.resolve_asset(_SESSION_TREE_REL)
        self.assertTrue(resolved.exists(), f"Expected file at: {resolved}")
        self.assertTrue(str(resolved).endswith("session_tree.py"))

    def test_editable_install_parent_parent_path_works(self):
        """Candidate 3 (pkg_dir.parent.parent) must reach the repo root."""
        pkg_dir = Path(_MODULE_PATH).parent  # src/amplihack/
        candidate = pkg_dir.parent.parent / _ORCH_HELPER_REL
        self.assertTrue(
            candidate.exists(),
            f"Editable install candidate does not exist: {candidate}\n"
            "This means the .parent.parent depth calculation is wrong.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Regression: running from /tmp (the core issue #3092)
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionOutsideRepo(unittest.TestCase):
    """Core regression: parse-decomposition must not fail outside amplihack repo."""

    def _run_from(self, cwd: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        run_env = {**os.environ}
        if env is not None:
            run_env.update(env)
        src_dir = str(REPO_ROOT / "src")
        run_env["PYTHONPATH"] = src_dir + os.pathsep + run_env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "amplihack.resolve_bundle_asset", *args],
            capture_output=True,
            text=True,
            env=run_env,
            cwd=cwd,
        )

    def test_resolves_from_tmp_directory(self):
        """Running from /tmp must succeed — this is the skwaqr scenario from #3092."""
        result = self._run_from(
            "/tmp",
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, f"Failed from /tmp: {result.stderr}")
        resolved = Path(result.stdout.strip())
        self.assertTrue(resolved.is_file(), f"Not a file: {resolved}")

    def test_resolves_from_non_git_directory(self):
        """Running from a non-git directory must not use git rev-parse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_from(
                tmpdir,
                _ORCH_HELPER_REL,
                env={"AMPLIHACK_HOME": str(REPO_ROOT)},
            )
            self.assertEqual(result.returncode, 0, f"Failed from non-git dir: {result.stderr}")

    def test_no_git_rev_parse_dependency(self):
        """The module must not call git rev-parse (grep the source)."""
        source = _MODULE_PATH.read_text()
        self.assertNotIn(
            "git rev-parse",
            source,
            "resolve_bundle_asset.py must not use 'git rev-parse' — "
            "this is the root cause of issue #3092.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Path traversal prevention
# ─────────────────────────────────────────────────────────────────────────────

class TestPathTraversalPrevention(unittest.TestCase):
    """All path traversal attempts must be rejected with exit code 2."""

    def _expect_exit2(self, path: str):
        result = _run_module(path)
        self.assertEqual(
            result.returncode,
            2,
            f"Expected exit 2 for {path!r}, got {result.returncode}. "
            f"stderr: {result.stderr}",
        )
        self.assertTrue(result.stderr.strip(), "Expected error message on stderr")

    def test_dotdot_in_path(self):
        self._expect_exit2("amplifier-bundle/../../../etc/passwd")

    def test_absolute_path(self):
        self._expect_exit2("/etc/passwd")

    def test_home_tilde_path(self):
        self._expect_exit2("~/secret")

    def test_missing_required_prefix(self):
        self._expect_exit2("tools/orch_helper.py")

    def test_empty_path(self):
        self._expect_exit2("")

    def test_null_byte_in_path(self):
        # The OS rejects null bytes before the subprocess even launches, so
        # test the Python API (_validate_relative_path) directly instead of
        # going through the CLI subprocess.
        mod = _import_module()
        with self.assertRaises(ValueError):
            mod._validate_relative_path("amplifier-bundle/tools/orch_helper\x00.py")

    def test_dot_component(self):
        self._expect_exit2("amplifier-bundle/./tools/orch_helper.py")

    def test_traversal_attempt_after_valid_prefix(self):
        """Even with valid prefix, .. is rejected."""
        self._expect_exit2("amplifier-bundle/tools/../../secret")


# ─────────────────────────────────────────────────────────────────────────────
# 6. No valid path found — exit 1 with actionable error
# ─────────────────────────────────────────────────────────────────────────────

class TestNoValidPathFound(unittest.TestCase):
    """When no candidate contains the asset, exit 1 with a helpful message."""

    def test_nonexistent_asset_exits_1(self):
        """A syntactically valid but nonexistent asset path → exit 1."""
        result = _run_module(
            "amplifier-bundle/tools/nonexistent_file_xyzzy_12345.py",
            env={"AMPLIHACK_HOME": "/tmp"},
        )
        self.assertEqual(result.returncode, 1, f"stderr: {result.stderr}")

    def test_error_message_mentions_amplihack_home(self):
        """The error message must guide the user to set AMPLIHACK_HOME."""
        result = _run_module(
            "amplifier-bundle/tools/nonexistent_file_xyzzy_12345.py",
            env={"AMPLIHACK_HOME": "/tmp"},
        )
        self.assertIn("AMPLIHACK_HOME", result.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Output safety
# ─────────────────────────────────────────────────────────────────────────────

class TestOutputSafety(unittest.TestCase):
    """Stdout output must be safe for unquoted bash use."""

    def test_output_is_single_line(self):
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(len(lines), 1, f"Expected single-line output, got: {result.stdout!r}")

    def test_output_is_absolute_path(self):
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        resolved = result.stdout.strip()
        self.assertTrue(resolved.startswith("/"), f"Expected absolute path, got: {resolved!r}")

    def test_output_contains_only_safe_characters(self):
        """No shell-dangerous characters in stdout."""
        import re
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        resolved = result.stdout.strip()
        safe_re = re.compile(r"^[A-Za-z0-9_\-./]+$")
        self.assertTrue(
            safe_re.match(resolved),
            f"Output contains shell-unsafe characters: {resolved!r}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. CLI interface
# ─────────────────────────────────────────────────────────────────────────────

class TestCLIInterface(unittest.TestCase):
    """CLI contract: argument count, exit codes, usage message."""

    def test_no_args_exits_2_with_usage(self):
        result = _run_module()  # no asset path arg
        self.assertEqual(result.returncode, 2, f"stderr: {result.stderr}")
        self.assertIn("Usage", result.stderr)

    def test_too_many_args_exits_2(self):
        result = _run_module("amplifier-bundle/tools/orch_helper.py", "extra-arg")
        self.assertEqual(result.returncode, 2, f"stderr: {result.stderr}")

    def test_valid_asset_exits_0(self):
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    def test_usage_message_on_stderr_not_stdout(self):
        result = _run_module()
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.strip(), "Usage must appear on stderr")
        self.assertFalse(result.stdout.strip(), "No output expected on stdout for errors")


# ─────────────────────────────────────────────────────────────────────────────
# 9. _validate_relative_path internal API
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateRelativePath(unittest.TestCase):
    """Direct tests of the _validate_relative_path() internal function."""

    def setUp(self):
        self.mod = _import_module()
        self.validate = self.mod._validate_relative_path

    def test_valid_file_path_passes(self):
        self.validate("amplifier-bundle/tools/orch_helper.py")  # must not raise

    def test_valid_directory_path_passes(self):
        self.validate("amplifier-bundle/tools/amplihack/hooks")  # must not raise

    def test_empty_path_raises(self):
        with self.assertRaises(ValueError):
            self.validate("")

    def test_dotdot_raises(self):
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/../secret")

    def test_dot_raises(self):
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/./tools/orch_helper.py")

    def test_absolute_path_raises(self):
        with self.assertRaises(ValueError):
            self.validate("/etc/passwd")

    def test_missing_prefix_raises(self):
        with self.assertRaises(ValueError):
            self.validate("tools/orch_helper.py")

    def test_backslash_raises(self):
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle\\tools\\orch_helper.py")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Fallback chain ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackChainOrder(unittest.TestCase):
    """AMPLIHACK_HOME must take priority; pkg_dir used when env var absent."""

    def test_amplihack_home_wins_over_pkg_dir(self):
        """Path returned is under AMPLIHACK_HOME when it is valid."""
        result = _run_module(
            _ORCH_HELPER_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(
            result.stdout.strip().startswith(str(REPO_ROOT)),
            f"Result should start with AMPLIHACK_HOME={REPO_ROOT}",
        )

    def test_pkg_dir_used_without_amplihack_home(self):
        """Without AMPLIHACK_HOME, fallback finds the file via pkg_dir chain."""
        env = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_HOME"}
        src_dir = str(REPO_ROOT / "src")
        env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")
        env["AMPLIHACK_HOME"] = ""
        result = subprocess.run(
            [sys.executable, "-m", "amplihack.resolve_bundle_asset", _ORCH_HELPER_REL],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 0, f"Fallback failed: {result.stderr}")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Directory asset resolution (HOOKS_DIR pattern)
# ─────────────────────────────────────────────────────────────────────────────

class TestDirectoryAssetResolution(unittest.TestCase):
    """resolve_asset() must work for directories, not just files (HOOKS_DIR)."""

    def test_resolves_hooks_directory(self):
        mod = _import_module()
        resolved = mod.resolve_asset(_HOOKS_DIR_REL)
        self.assertTrue(resolved.exists(), f"Hooks directory not found: {resolved}")
        self.assertTrue(resolved.is_dir(), f"Expected directory at: {resolved}")

    def test_cli_resolves_hooks_directory(self):
        result = _run_module(
            _HOOKS_DIR_REL,
            env={"AMPLIHACK_HOME": str(REPO_ROOT)},
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        resolved = Path(result.stdout.strip())
        self.assertTrue(resolved.is_dir(), f"Expected directory at: {resolved}")


# ─────────────────────────────────────────────────────────────────────────────
# 12. orch_helper import regression (the exact skwaqr failure scenario)
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchHelperImportRegression(unittest.TestCase):
    """Simulate the exact failure pattern described in issue #3092."""

    def test_resolve_bundle_asset_finds_orch_helper_from_tmp(self):
        """From /tmp with AMPLIHACK_HOME set, orch_helper.py is found."""
        src_dir = str(REPO_ROOT / "src")
        env = {
            **os.environ,
            "AMPLIHACK_HOME": str(REPO_ROOT),
            "PYTHONPATH": src_dir + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        result = subprocess.run(
            [sys.executable, "-m", "amplihack.resolve_bundle_asset", _ORCH_HELPER_REL],
            capture_output=True,
            text=True,
            env=env,
            cwd="/tmp",
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Issue #3092 regression: parse-decomposition would fail.\n"
            f"stderr: {result.stderr}",
        )
        resolved = result.stdout.strip()
        self.assertTrue(
            Path(resolved).is_file(),
            f"Resolved path is not a file: {resolved}",
        )

    def test_resolved_path_importable_as_orch_helper(self):
        """The resolved orch_helper.py path is importable — matching the recipe pattern."""
        mod = _import_module()
        resolved = mod.resolve_asset(_ORCH_HELPER_REL)

        import importlib.util as ilu
        spec = ilu.spec_from_file_location("orch_helper", resolved)
        h = ilu.module_from_spec(spec)
        spec.loader.exec_module(h)

        # Verify the module exposes its public API.
        self.assertTrue(callable(getattr(h, "extract_json", None)))
        self.assertTrue(callable(getattr(h, "normalise_type", None)))


if __name__ == "__main__":
    unittest.main()
