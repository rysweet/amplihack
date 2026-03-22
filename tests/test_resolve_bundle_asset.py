"""
Tests for src/amplihack/resolve_bundle_asset.py

Covers:
- Module existence and importability
- 4-priority fallback chain
- Path traversal prevention
- AMPLIHACK_HOME validation
- CLI interface (exit codes, output format)
- Directory asset resolution (HOOKS_DIR pattern)
- Regression: resolves correctly when CWD is outside the amplihack repo
"""

import importlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Module loader — cached to avoid re-executing source on every test method.
# ---------------------------------------------------------------------------
_MODULE_CACHE: dict = {}

_SRC_FILE = Path(__file__).parent.parent / "src" / "amplihack" / "resolve_bundle_asset.py"


def _load_module():
    """Import resolve_bundle_asset from source, with caching."""
    if "mod" not in _MODULE_CACHE:
        spec = importlib.util.spec_from_file_location("amplihack.resolve_bundle_asset", _SRC_FILE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULE_CACHE["mod"] = mod
    return _MODULE_CACHE["mod"]


# ---------------------------------------------------------------------------
# Helper: run the module as a CLI subprocess.
# ---------------------------------------------------------------------------
def _run_cli(args, *, env=None, cwd=None):
    """Run python3 -m amplihack.resolve_bundle_asset <args> as a subprocess."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(_SRC_FILE)] + args,
        capture_output=True,
        text=True,
        cwd=cwd or str(Path(__file__).parent.parent),
        env=full_env,
    )


# ---------------------------------------------------------------------------
# 1. Module existence
# ---------------------------------------------------------------------------
class TestModuleExists(unittest.TestCase):
    """resolve_bundle_asset.py must exist and be importable."""

    def test_source_file_exists(self):
        """Module source file is present in the package."""
        self.assertTrue(_SRC_FILE.exists(), f"Module not found: {_SRC_FILE}")

    def test_module_importable(self):
        """Module loads without ImportError."""
        mod = _load_module()
        self.assertIsNotNone(mod)

    def test_resolve_asset_callable(self):
        """Public API resolve_asset is a callable."""
        mod = _load_module()
        self.assertTrue(callable(mod.resolve_asset))


# ---------------------------------------------------------------------------
# 2. AMPLIHACK_HOME resolution (highest priority)
# ---------------------------------------------------------------------------
class TestAmplihackHomeResolution(unittest.TestCase):
    """AMPLIHACK_HOME env var must be tried first in the fallback chain."""

    def setUp(self):
        self.mod = _load_module()
        # The real repo root always contains amplifier-bundle/tools/orch_helper.py.
        self.repo_root = str(Path(__file__).parent.parent)

    def test_amplihack_home_valid_dir_resolves(self):
        """AMPLIHACK_HOME pointing to the repo root resolves orch_helper.py."""
        with patch.dict(os.environ, {"AMPLIHACK_HOME": self.repo_root}):
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        self.assertTrue(resolved.is_file(), f"Not a file: {resolved}")
        self.assertIn("orch_helper.py", resolved.name)

    def test_amplihack_home_invalid_dir_warns_and_falls_back(self):
        """AMPLIHACK_HOME pointing to a non-directory emits warning and falls back."""
        with patch.dict(os.environ, {"AMPLIHACK_HOME": "/nonexistent/path/xyz"}):
            # Should not raise — must fall back to other candidates.
            try:
                resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
                self.assertTrue(resolved.is_file())
            except FileNotFoundError:
                pass  # Acceptable if no fallback candidate exists either.

    def test_amplihack_home_is_file_not_dir_warns_and_falls_back(self):
        """AMPLIHACK_HOME pointing to a file (not a dir) warns and falls back."""
        with tempfile.NamedTemporaryFile() as tmp:
            with patch.dict(os.environ, {"AMPLIHACK_HOME": tmp.name}):
                try:
                    self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
                except FileNotFoundError:
                    pass  # Acceptable if no fallback works either.

    def test_amplihack_home_takes_priority_over_pkg_dir(self):
        """When AMPLIHACK_HOME is valid, it is chosen over pkg_dir candidate."""
        with patch.dict(os.environ, {"AMPLIHACK_HOME": self.repo_root}):
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        expected_prefix = Path(self.repo_root).resolve()
        self.assertTrue(
            str(resolved).startswith(str(expected_prefix)),
            f"Expected path under {expected_prefix}, got {resolved}",
        )

    def test_warning_does_not_leak_amplihack_home_value(self):
        """Warning message must not contain the AMPLIHACK_HOME value."""
        import io

        bad_home = "/some/secret/path/12345"
        buf = io.StringIO()
        with patch.dict(os.environ, {"AMPLIHACK_HOME": bad_home}):
            with patch("sys.stderr", buf):
                try:
                    self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
                except FileNotFoundError:
                    pass
        warning_text = buf.getvalue()
        if warning_text:
            self.assertNotIn(bad_home, warning_text)


# ---------------------------------------------------------------------------
# 3. Fallback chain — pkg_dir and editable install
# ---------------------------------------------------------------------------
class TestPackageInstallResolution(unittest.TestCase):
    """Fallback via pkg_dir (installed) or pkg_dir.parent.parent (editable)."""

    def setUp(self):
        self.mod = _load_module()

    def test_resolves_without_amplihack_home(self):
        """resolve_asset works even when AMPLIHACK_HOME is not set."""
        env = dict(os.environ)
        env.pop("AMPLIHACK_HOME", None)
        with patch.dict(os.environ, env, clear=True):
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        self.assertTrue(resolved.is_file())

    def test_returns_absolute_path(self):
        """Returned path is always absolute."""
        resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        self.assertTrue(resolved.is_absolute(), f"Expected absolute path, got: {resolved}")

    def test_editable_install_candidate(self):
        """pkg_dir.parent.parent/amplifier-bundle/ is tried as editable-install candidate."""
        mod = self.mod
        pkg_dir = mod._PKG_DIR
        editable_candidate = pkg_dir.parent.parent / "amplifier-bundle" / "tools" / "orch_helper.py"
        # In the dev/test environment, this should exist (repo root).
        if editable_candidate.exists():
            resolved = mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            self.assertTrue(resolved.is_file())

    def test_running_inside_repo_prefers_cwd_checkout_over_home_install(self):
        """A local checkout should beat ~/.amplihack even if Python imported an installed package."""
        mod = self.mod

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo_root = tmp / "repo"
            helper = repo_root / "amplifier-bundle" / "tools" / "orch_helper.py"
            helper.parent.mkdir(parents=True)
            helper.write_text("# local checkout helper\n")

            fake_pkg_dir = tmp / "site-packages" / "amplihack"
            fake_pkg_dir.mkdir(parents=True)

            fake_home = tmp / "home-amplihack"
            home_helper = fake_home / "amplifier-bundle" / "tools" / "orch_helper.py"
            home_helper.parent.mkdir(parents=True)
            home_helper.write_text("# home install helper\n")

            old_pkg_dir = mod._PKG_DIR
            old_home = mod._HOME_AMPLIHACK
            old_cwd = Path.cwd()
            try:
                mod._PKG_DIR = fake_pkg_dir
                mod._HOME_AMPLIHACK = fake_home
                os.chdir(repo_root)
                with patch.dict(os.environ, {}, clear=True):
                    resolved = mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            finally:
                mod._PKG_DIR = old_pkg_dir
                mod._HOME_AMPLIHACK = old_home
                os.chdir(old_cwd)

        self.assertEqual(resolved, helper.resolve())


# ---------------------------------------------------------------------------
# 4. Regression: resolves correctly from outside the repo (issue #3092)
# ---------------------------------------------------------------------------
class TestRegressionOutsideRepo(unittest.TestCase):
    """Core regression: must succeed when CWD is outside the amplihack repo."""

    def setUp(self):
        self.mod = _load_module()

    def test_resolves_from_tmp_directory(self):
        """`resolve_asset` succeeds when called from /tmp (not inside amplihack)."""
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            self.assertTrue(resolved.is_file(), f"Not a file: {resolved}")
        finally:
            os.chdir(original_cwd)

    def test_cli_resolves_from_tmp_directory(self):
        """CLI invocation from /tmp returns exit 0 and a valid path."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"], cwd="/tmp")
        self.assertEqual(result.returncode, 0, f"CLI failed:\n{result.stderr}")
        resolved = Path(result.stdout.strip())
        self.assertTrue(resolved.is_file(), f"Resolved path is not a file: {resolved}")

    def test_no_git_rev_parse_dependency(self):
        """Resolution must not invoke git rev-parse (pure pathlib only)."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = AssertionError("subprocess.run must not be called")
            with patch("subprocess.check_output") as mock_co:
                mock_co.side_effect = AssertionError("subprocess.check_output must not be called")
                # Should resolve without calling any subprocess.
                try:
                    self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
                except FileNotFoundError:
                    pass  # Not finding it is fine; calling subprocess is not.


# ---------------------------------------------------------------------------
# 5. Path traversal prevention
# ---------------------------------------------------------------------------
class TestPathTraversalPrevention(unittest.TestCase):
    """_validate_relative_path must reject dangerous inputs."""

    def setUp(self):
        self.validate = _load_module()._validate_relative_path

    def test_rejects_dotdot_component(self):
        """Path containing '..' is rejected."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/../../../etc/passwd")

    def test_rejects_absolute_path(self):
        """Absolute path starting with '/' is rejected."""
        with self.assertRaises(ValueError):
            self.validate("/etc/passwd")

    def test_rejects_home_path(self):
        """Path starting with '~' is rejected."""
        with self.assertRaises(ValueError):
            self.validate("~/secret")

    def test_rejects_missing_prefix(self):
        """Path without 'amplifier-bundle/' prefix is rejected."""
        with self.assertRaises(ValueError):
            self.validate("tools/orch_helper.py")

    def test_rejects_empty_path(self):
        """Empty string is rejected."""
        with self.assertRaises(ValueError):
            self.validate("")

    def test_rejects_null_byte(self):
        """Path containing null byte is rejected (unsafe character)."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/tools/\x00orch_helper.py")

    def test_rejects_shell_metachar(self):
        """Path containing ';' (shell metacharacter) is rejected."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/tools/orch_helper.py;rm -rf /")

    def test_accepts_valid_path(self):
        """A well-formed path passes validation without raising."""
        # Should not raise.
        self.validate("amplifier-bundle/tools/orch_helper.py")


# ---------------------------------------------------------------------------
# 6. No valid path found → exit 1 with actionable message
# ---------------------------------------------------------------------------
class TestNoValidPathFound(unittest.TestCase):
    """When no candidate exists, raise FileNotFoundError with guidance."""

    def setUp(self):
        self.mod = _load_module()

    def test_raises_file_not_found_when_no_candidate(self):
        """FileNotFoundError raised if asset doesn't exist in any location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                with patch.object(self.mod, "_PKG_DIR", Path("/nonexistent/pkg")):
                    with patch.object(self.mod, "_HOME_AMPLIHACK", Path("/nonexistent/home")):
                        env = dict(os.environ)
                        env.pop("AMPLIHACK_HOME", None)
                        with patch.dict(os.environ, env, clear=True):
                            with self.assertRaises(FileNotFoundError) as ctx:
                                self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            finally:
                os.chdir(old_cwd)
        self.assertIn("AMPLIHACK_HOME", str(ctx.exception))

    def test_api_error_message_mentions_amplihack_home(self):
        """FileNotFoundError message mentions AMPLIHACK_HOME so the user knows how to fix."""
        mod = _load_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                with patch.object(mod, "_PKG_DIR", Path("/nonexistent/pkg")):
                    with patch.object(mod, "_HOME_AMPLIHACK", Path("/nonexistent/home")):
                        env = dict(os.environ)
                        env.pop("AMPLIHACK_HOME", None)
                        with patch.dict(os.environ, env, clear=True):
                            with self.assertRaises(FileNotFoundError) as ctx:
                                mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            finally:
                os.chdir(old_cwd)
        self.assertIn(
            "AMPLIHACK_HOME",
            str(ctx.exception),
            "Error message must mention AMPLIHACK_HOME so the user knows how to fix the issue",
        )


# ---------------------------------------------------------------------------
# 7. Output safety
# ---------------------------------------------------------------------------
class TestOutputSafety(unittest.TestCase):
    """CLI stdout must be a single absolute path, safe for unquoted shell use."""

    def test_output_is_single_line(self):
        """stdout contains exactly one non-empty line."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"])
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, f"Expected 1 line, got: {result.stdout!r}")

    def test_output_is_absolute_path(self):
        """stdout is an absolute path."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"])
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved = Path(result.stdout.strip())
        self.assertTrue(resolved.is_absolute())

    def test_output_contains_no_shell_metacharacters(self):
        """stdout path contains only safe characters (no spaces, ;, $, etc.)."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"])
        self.assertEqual(result.returncode, 0, result.stderr)
        path_str = result.stdout.strip()
        # Allow: alphanumeric, hyphen, underscore, dot, forward-slash.
        self.assertRegex(path_str, r"^[A-Za-z0-9_\-./]+$")


# ---------------------------------------------------------------------------
# 8. CLI interface
# ---------------------------------------------------------------------------
class TestCLIInterface(unittest.TestCase):
    """python3 -m amplihack.resolve_bundle_asset CLI contract."""

    def test_exit_0_on_valid_asset(self):
        """Valid asset path → exit 0."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exit_2_on_no_arguments(self):
        """No arguments → exit 2 (usage error)."""
        result = _run_cli([])
        self.assertEqual(result.returncode, 2, f"Expected exit 2, got {result.returncode}")

    def test_exit_2_on_path_traversal(self):
        """Path traversal attempt → exit 2."""
        result = _run_cli(["amplifier-bundle/../../../etc/passwd"])
        self.assertEqual(result.returncode, 2)

    def test_exit_2_on_missing_prefix(self):
        """Path without required prefix → exit 2."""
        result = _run_cli(["tools/orch_helper.py"])
        self.assertEqual(result.returncode, 2)


# ---------------------------------------------------------------------------
# 9. Directory asset resolution (HOOKS_DIR pattern)
# ---------------------------------------------------------------------------
class TestDirectoryAssetResolution(unittest.TestCase):
    """resolve_asset must work for directory assets, not just files."""

    def setUp(self):
        self.mod = _load_module()

    def test_resolves_directory_asset(self):
        """amplifier-bundle/tools/ directory resolves to an existing directory."""
        try:
            resolved = self.mod.resolve_asset("amplifier-bundle/tools")
        except FileNotFoundError:
            self.skipTest("amplifier-bundle/tools not found in any candidate")
        self.assertTrue(resolved.exists())

    def test_hooks_dir_pattern_soft_fail(self):
        """HOOKS_DIR soft-fail pattern: missing hooks dir returns empty, no exit 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _run_cli(
                ["amplifier-bundle/tools/amplihack/hooks"],
                env={"AMPLIHACK_HOME": tmpdir},
                cwd=tmpdir,
            )
        # Exit 1 = not found (acceptable for soft-fail scenarios in YAML).
        self.assertIn(result.returncode, (0, 1))


# ---------------------------------------------------------------------------
# 10. Fallback chain order
# ---------------------------------------------------------------------------
class TestFallbackChainOrder(unittest.TestCase):
    """AMPLIHACK_HOME must take priority; pkg_dir used when not set."""

    def setUp(self):
        self.mod = _load_module()
        self.repo_root = str(Path(__file__).parent.parent)

    def test_amplihack_home_beats_pkg_dir(self):
        """When both AMPLIHACK_HOME and pkg_dir have the asset, AMPLIHACK_HOME wins."""
        with patch.dict(os.environ, {"AMPLIHACK_HOME": self.repo_root}):
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        expected = (
            Path(self.repo_root) / "amplifier-bundle" / "tools" / "orch_helper.py"
        ).resolve()
        self.assertEqual(resolved, expected)

    def test_pkg_dir_used_when_no_env_var(self):
        """pkg_dir fallback is tried when AMPLIHACK_HOME is absent."""
        env = dict(os.environ)
        env.pop("AMPLIHACK_HOME", None)
        with patch.dict(os.environ, env, clear=True):
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        self.assertTrue(resolved.is_file())


# ---------------------------------------------------------------------------
# 11. orch_helper importability regression
# ---------------------------------------------------------------------------
class TestOrchHelperImportRegression(unittest.TestCase):
    """Resolved path for orch_helper.py must be importable as the orch_helper module."""

    def setUp(self):
        self.mod = _load_module()

    def test_resolved_path_is_importable_as_orch_helper(self):
        """The resolved orch_helper.py can be loaded via importlib (recipe pattern)."""
        resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        spec = importlib.util.spec_from_file_location("orch_helper", str(resolved))
        self.assertIsNotNone(spec, "spec_from_file_location returned None")
        orch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orch)
        self.assertTrue(callable(getattr(orch, "extract_json", None)))

    def test_issue_3092_skwaqr_scenario(self):
        """Simulate running from a non-amplihack directory (the exact bug scenario)."""
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
            self.assertTrue(
                resolved.is_file(),
                "orch_helper.py not found when running from /tmp — issue #3092 regression",
            )
        finally:
            os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# 12. Security hardening — SR-001 through SR-004 (TDD: tests written first)
#
# These tests define the security contract that the implementation MUST satisfy
# after applying the hardening described in the design specification.
#
# Expected status before hardening:
#   - test_rejects_single_dot_path_component   → FAIL (dot segment passes regex)
#   - test_null_byte_caught_before_prefix       → FAIL (wrong error ordering)
#   - test_safe_join_function_exists            → FAIL (_safe_join not defined)
#   - test_safe_join_prevents_symlink_escape    → FAIL (no containment check)
#
# Expected status after hardening:
#   - All four tests pass; all pre-existing tests still pass (no regressions)
# ---------------------------------------------------------------------------
class TestSecurityHardeningSR001SingleDot(unittest.TestCase):
    """SR-001: Segment-level dotdot validation must also reject single-dot segments."""

    def setUp(self):
        self.validate = _load_module()._validate_relative_path

    def test_rejects_single_dot_path_component(self):
        """SR-001: A lone '.' segment is a no-op traversal and must be rejected.

        Path.resolve() on 'amplifier-bundle/./tools/orch_helper.py' collapses the
        dot, which is safe, but allowing '.' blurs the boundary check implemented
        by segment-level validation.  The spec requires rejecting any segment that
        is exactly '.' (in addition to '..').

        EXPECTED TO FAIL until SR-001 hardening is applied.
        """
        with self.assertRaises(ValueError, msg="Single '.' path segment must be rejected"):
            self.validate("amplifier-bundle/./tools/orch_helper.py")

    def test_rejects_dotdot_inside_longer_segment_name_allowed(self):
        """SR-001 boundary: '..hidden' is a filename, not a traversal — must be allowed.

        Filenames that merely *start* with '..' (e.g. '..hidden') are not traversal
        segments and must not be rejected by the segment-level check.
        """
        # Should NOT raise — '..hidden' is a valid filename component.
        self.validate("amplifier-bundle/tools/..hidden")

    def test_rejects_double_dot_as_standalone_final_segment(self):
        """SR-001: '..' as the final path segment is rejected (existing + new test)."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/tools/..")

    def test_rejects_double_dot_surrounded_by_valid_segments(self):
        """SR-001: '..' buried between valid segments is caught by segment scan."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/tools/../tools/orch_helper.py")


class TestSecurityHardeningSR003NullByteOrdering(unittest.TestCase):
    """SR-003: Null byte must be caught as the FIRST validation step.

    Ordering matters: if null byte snuck through before the prefix check it could
    cause silent misbehaviour in downstream shell usage.  The implementation must
    short-circuit on null byte *before* inspecting any other path property.
    """

    def setUp(self):
        self.validate = _load_module()._validate_relative_path

    def test_null_byte_caught_before_prefix_check(self):
        r"""SR-003: '\x00amplifier-bundle/...' is rejected for null byte, not missing prefix.

        Currently the code checks the 'amplifier-bundle/' prefix before the regex
        allowlist, so '\x00amplifier-bundle/...' is rejected with a *prefix* error
        rather than a null-byte error.  After hardening, the null byte is detected
        first; the error message must NOT mention 'prefix' or 'amplifier-bundle'.

        EXPECTED TO FAIL until SR-003 null-byte-first ordering is applied.
        """
        null_prefixed = "\x00amplifier-bundle/tools/orch_helper.py"
        with self.assertRaises(ValueError) as ctx:
            self.validate(null_prefixed)
        error_msg = str(ctx.exception).lower()
        self.assertNotIn(
            "prefix",
            error_msg,
            "Null byte must be caught before the prefix check — "
            "error message must not mention 'prefix'",
        )
        self.assertNotIn(
            "amplifier-bundle",
            error_msg,
            "Null byte must be caught before the prefix check — "
            "error message must not mention 'amplifier-bundle'",
        )

    def test_null_byte_mid_path_still_rejected(self):
        r"""SR-003: Null byte in the middle of a valid-prefix path is also caught."""
        with self.assertRaises(ValueError):
            self.validate("amplifier-bundle/tools/\x00orch_helper.py")

    def test_null_byte_rejected_via_python_api(self):
        r"""SR-003: Python API rejects null byte in path with exit code 2 semantics.

        Note: null bytes cannot be passed via OS argv (the kernel treats \x00 as
        an argument terminator and subprocess.run raises ValueError).  This test
        validates the Python API path, which is the attack surface that matters
        for programmatic callers.
        """
        validate = _load_module()._validate_relative_path
        with self.assertRaises(ValueError):
            validate("amplifier-bundle/tools/\x00orch_helper.py")


class TestSecurityHardeningSR004SafeJoin(unittest.TestCase):
    """SR-004: _safe_join() containment check prevents symlink escape from base dir.

    resolve_asset currently computes candidates with plain path arithmetic
    (base / relative_path) and then calls candidate.exists().  If a symlink inside
    the bundle directory points outside the base directory, candidate.resolve()
    would silently escape the containment boundary.

    The fix requires a _safe_join(base, relative) helper that:
      1. Computes candidate = (base / relative).resolve()
      2. Checks candidate.relative_to(base.resolve()) — raises ValueError on escape
      3. Returns None if the path escapes, rather than raising

    EXPECTED TO FAIL until SR-004 is implemented.
    """

    def setUp(self):
        self.mod = _load_module()

    def test_safe_join_function_exists(self):
        """SR-004: _safe_join must be defined in the module (not yet present).

        EXPECTED TO FAIL until the function is added.
        """
        self.assertTrue(
            hasattr(self.mod, "_safe_join"),
            "_safe_join function must exist in resolve_bundle_asset module (SR-004).\n"
            "Add: def _safe_join(base: Path, relative: str) -> Path | None",
        )

    def test_safe_join_returns_path_for_legitimate_asset(self):
        """SR-004: _safe_join must return a Path for a normal, non-escaping asset."""
        mod = self.mod
        if not hasattr(mod, "_safe_join"):
            self.skipTest("_safe_join not implemented yet (SR-004)")
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "amplifier-bundle" / "tools").mkdir(parents=True)
            (base / "amplifier-bundle" / "tools" / "orch_helper.py").write_text("# stub")
            result = mod._safe_join(base, "amplifier-bundle/tools/orch_helper.py")
            self.assertIsNotNone(result, "_safe_join must return a Path for a legitimate asset")
            self.assertIsInstance(result, Path)

    def test_safe_join_returns_none_for_symlink_escape(self):
        """SR-004: _safe_join must return None when a symlink points outside base.

        Setup: base/amplifier-bundle/tools/escape -> /etc (outside base)
        Expected: _safe_join(base, 'amplifier-bundle/tools/escape') returns None

        EXPECTED TO FAIL until SR-004 containment check is added.
        """
        mod = self.mod
        if not hasattr(mod, "_safe_join"):
            self.skipTest("_safe_join not implemented yet (SR-004)")
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "amplifier-bundle" / "tools").mkdir(parents=True)
            # Symlink points outside the base directory.
            escape_link = base / "amplifier-bundle" / "tools" / "escape"
            escape_link.symlink_to("/etc")
            result = mod._safe_join(base, "amplifier-bundle/tools/escape")
            self.assertIsNone(
                result,
                "SR-004: _safe_join must return None when symlink escapes base dir, "
                f"but returned {result!r}",
            )

    def test_safe_join_returns_none_for_double_dot_component(self):
        """SR-004: _safe_join must return None when resolved path escapes via '..'."""
        mod = self.mod
        if not hasattr(mod, "_safe_join"):
            self.skipTest("_safe_join not implemented yet (SR-004)")
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Even without a symlink, a path with '..' can theoretically escape.
            # _safe_join must catch this via relative_to() containment.
            result = mod._safe_join(base, "amplifier-bundle/../../../etc/passwd")
            self.assertIsNone(
                result,
                "SR-004: _safe_join must return None when resolved path escapes base dir",
            )


class TestSecurityHardeningSR002StdoutCleanliness(unittest.TestCase):
    """SR-002: Searched filesystem paths must never appear on stdout.

    stdout is the machine-readable channel.  Diagnostic information (candidate
    search paths, AMPLIHACK_HOME warnings) must go to stderr only.
    """

    def test_stdout_empty_when_asset_not_found(self):
        """SR-002: stdout is empty (exit 1) when asset does not exist anywhere."""
        result = _run_cli(
            ["amplifier-bundle/does-not-exist-xyz.py"],
            env={"AMPLIHACK_HOME": "/nonexistent/path"},
        )
        self.assertEqual(result.returncode, 1, f"Expected exit 1, got {result.returncode}")
        self.assertEqual(
            result.stdout.strip(),
            "",
            f"stdout must be empty on not-found, got: {result.stdout!r}",
        )

    def test_error_details_on_stderr_not_stdout(self):
        """SR-002: Error details appear on stderr, not stdout."""
        result = _run_cli(
            ["amplifier-bundle/does-not-exist-xyz.py"],
            env={"AMPLIHACK_HOME": "/nonexistent/path"},
        )
        # stderr must contain something actionable.
        self.assertGreater(
            len(result.stderr.strip()),
            0,
            "stderr must contain error guidance when asset is not found",
        )

    def test_warning_for_invalid_amplihack_home_on_stderr_only(self):
        """SR-002: Invalid AMPLIHACK_HOME warning goes to stderr, never stdout."""
        result = _run_cli(
            ["amplifier-bundle/tools/orch_helper.py"],
            env={"AMPLIHACK_HOME": "/nonexistent/path/for/sr002/test"},
        )
        # The single stdout line must be ONLY the resolved path (or empty on not-found).
        stdout_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        if stdout_lines:
            # If found, the only stdout content must be the path.
            self.assertEqual(
                len(stdout_lines), 1, f"stdout must be one line, got: {result.stdout!r}"
            )
            resolved = Path(stdout_lines[0])
            self.assertTrue(
                resolved.is_absolute(), f"stdout must be an absolute path: {stdout_lines[0]!r}"
            )

    def test_amplihack_home_value_not_leaked_in_warning(self):
        """SR-005/SR-002: The AMPLIHACK_HOME value must not appear in warning text."""
        secret_path = "/very/secret/install/path/12345"
        result = _run_cli(
            ["amplifier-bundle/tools/orch_helper.py"],
            env={"AMPLIHACK_HOME": secret_path},
        )
        self.assertNotIn(
            secret_path,
            result.stderr,
            f"AMPLIHACK_HOME value {secret_path!r} must not be leaked in stderr output",
        )
        self.assertNotIn(
            secret_path,
            result.stdout,
            f"AMPLIHACK_HOME value {secret_path!r} must not appear in stdout",
        )


class TestSecurityHardeningIntegration(unittest.TestCase):
    """Integration tests confirming security hardening does not break functionality."""

    def setUp(self):
        self.mod = _load_module()
        self.repo_root = str(Path(__file__).parent.parent)

    def test_hardened_module_still_resolves_orch_helper(self):
        """After hardening: orch_helper.py must still resolve correctly."""
        resolved = self.mod.resolve_asset("amplifier-bundle/tools/orch_helper.py")
        self.assertTrue(resolved.is_file(), f"orch_helper.py not found: {resolved}")

    def test_hardened_module_valid_path_accepted(self):
        """After hardening: deeply nested valid path is still accepted."""
        # Should not raise for a well-formed path.
        self.mod._validate_relative_path("amplifier-bundle/tools/amplihack/hooks/post-commit")

    def test_hardened_module_exit_0_for_valid_asset(self):
        """After hardening: CLI still exits 0 for known-good asset."""
        result = _run_cli(["amplifier-bundle/tools/orch_helper.py"])
        self.assertEqual(result.returncode, 0, f"Unexpected failure:\n{result.stderr}")

    def test_all_sr001_sr004_exit_code_2_via_cli(self):
        """SR-001/SR-004: Injection attempts that can reach the CLI produce exit code 2.

        Note: null bytes (\x00) cannot be passed via OS argv — the kernel terminates
        arguments at the first null byte, so subprocess.run raises ValueError before
        the process starts.  Null-byte rejection is validated via the Python API in
        TestSecurityHardeningSR003NullByteOrdering instead.
        """
        bad_paths = [
            "amplifier-bundle/./tools/orch_helper.py",  # SR-001: dot segment
        ]
        for path in bad_paths:
            with self.subTest(path=repr(path)):
                result = _run_cli([path])
                self.assertEqual(
                    result.returncode,
                    2,
                    f"Expected exit 2 for {path!r}, got {result.returncode}.\n"
                    f"stderr: {result.stderr!r}",
                )


if __name__ == "__main__":
    unittest.main()
