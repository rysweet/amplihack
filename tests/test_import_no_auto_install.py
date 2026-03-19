"""Regression tests for issue #3327: amplihack import must not auto-install packages.

TDD tests — written BEFORE the fix. Expected failures against current code:

  FAIL: test_ensure_memory_lib_raises_import_error_when_absent
        Current code calls subprocess.run() instead of raising ImportError.

  FAIL: test_ensure_memory_lib_no_subprocess_when_absent
        Current code calls subprocess.run(); patched mock will see the call.

  FAIL: test_main_does_not_call_ensure_memory_lib_installed
        Current main() calls ensure_memory_lib_installed(); it should not.

  FAIL: test_memory_lib_is_optional_dependency_in_pyproject
        amplihack-memory-lib is in [project.dependencies]; it must move to
        [project.optional-dependencies] memory = [...].

  PASS: test_import_amplihack_no_subprocess_at_module_level
        Already fixed: eager call moved into main(), so bare import is clean.

  PASS: test_ensure_memory_lib_returns_true_when_lib_present
        Already works: try/except ImportError short-circuit is correct.

Once the fix lands all six tests must pass.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AMPLIHACK_PREFIX = "amplihack"


def _drop_amplihack_from_sys_modules() -> None:
    """Remove every amplihack-prefixed entry from sys.modules.

    # SECURITY: test isolation only — never use sys.modules manipulation
    # in production code.  This is required here to force a fresh import
    # of the package so subprocess-mock assertions start from a clean state.
    """
    to_remove = [k for k in sys.modules if k == _AMPLIHACK_PREFIX or k.startswith(_AMPLIHACK_PREFIX + ".")]
    for key in to_remove:
        del sys.modules[key]


def _make_fake_memory_module() -> types.ModuleType:
    """Return a minimal stub for amplihack_memory to simulate lib presence."""
    mod = types.ModuleType("amplihack_memory")
    mod.__version__ = "0.2.0"
    return mod


# ---------------------------------------------------------------------------
# Test 1 — Bare import must not trigger any subprocess call (module level)
# ---------------------------------------------------------------------------


class TestImportAmplihackNoSubprocess:
    """import amplihack must produce zero subprocess side-effects."""

    def test_import_amplihack_no_subprocess_at_module_level(self) -> None:
        """EXPECTED PASS: eager call already moved into main().

        Verifies that a fresh `import amplihack` (with amplihack_memory absent)
        does not invoke subprocess.run or subprocess.Popen.
        """
        _drop_amplihack_from_sys_modules()

        # Ensure amplihack_memory appears absent so any auto-install would trigger
        sys.modules.pop("amplihack_memory", None)

        with (
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
        ):
            import amplihack  # noqa: F401 — side-effect under test

            mock_run.assert_not_called(), "subprocess.run was called during `import amplihack`"
            mock_popen.assert_not_called(), "subprocess.Popen was called during `import amplihack`"

        _drop_amplihack_from_sys_modules()


# ---------------------------------------------------------------------------
# Test 2 — ensure_memory_lib_installed() must raise ImportError, not subprocess
# ---------------------------------------------------------------------------


class TestEnsureMemoryLibInstalledContract:
    """ensure_memory_lib_installed() must be a pure guard, not an installer."""

    def setup_method(self) -> None:
        """Block amplihack_memory to simulate absence regardless of install state.

        # SECURITY: test isolation only — never use sys.modules manipulation
        # in production code.  Setting sys.modules[name] = None causes
        # `import name` to raise ImportError, which is how CPython implements
        # the "blocked import" pattern for testing absent optional dependencies.
        # sys.modules.pop() alone does NOT prevent re-import when the package
        # is installed on disk; only the None sentinel blocks it.
        """
        # Block amplihack_memory so `import amplihack_memory` raises ImportError
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]
        # Also drop the module under test so patches take effect cleanly
        sys.modules.pop("amplihack.memory_auto_install", None)

    def teardown_method(self) -> None:
        """Restore sys.modules to its pre-test state."""
        # Remove the None sentinel (or real module) to allow subsequent tests
        # to import normally.  Use pop() rather than del to avoid KeyError
        # when a test's own finally block already cleaned up the key.
        sys.modules.pop("amplihack_memory", None)
        sys.modules.pop("amplihack.memory_auto_install", None)

    def _get_ensure_fn(self):
        """Import the function fresh each time."""
        if "amplihack.memory_auto_install" in sys.modules:
            del sys.modules["amplihack.memory_auto_install"]
        from amplihack.memory_auto_install import ensure_memory_lib_installed

        return ensure_memory_lib_installed

    # ------------------------------------------------------------------
    # EXPECTED FAIL: current code calls subprocess instead of raising
    # ------------------------------------------------------------------

    def test_ensure_memory_lib_raises_import_error_when_absent(self) -> None:
        """EXPECTED FAIL before fix.

        When amplihack_memory is not installed, ensure_memory_lib_installed()
        must raise ImportError with an actionable pip install message.
        It must NOT silently return False or call subprocess.
        """
        ensure = self._get_ensure_fn()

        # Ensure amplihack_memory is blocked (setup_method sets None sentinel)
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with pytest.raises(ImportError) as exc_info:
            ensure()

        error_msg = str(exc_info.value)
        assert "amplihack[memory]" in error_msg, (
            f"ImportError must mention 'amplihack[memory]' but got: {error_msg!r}"
        )
        assert "pip install" in error_msg, (
            f"ImportError must include pip install instructions but got: {error_msg!r}"
        )

    def test_ensure_memory_lib_no_subprocess_when_absent(self) -> None:
        """EXPECTED FAIL before fix.

        When amplihack_memory is absent, ensure_memory_lib_installed() must
        not invoke subprocess.run or subprocess.Popen under any code path.
        """
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with (
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
        ):
            # The function should raise ImportError, not call subprocess
            try:
                ensure()
            except ImportError:
                pass  # Expected after fix; swallowed so we can assert below

            mock_run.assert_not_called(), (
                f"subprocess.run called {mock_run.call_count} time(s) — "
                "must not invoke pip from library code"
            )
            mock_popen.assert_not_called(), (
                f"subprocess.Popen called {mock_popen.call_count} time(s) — "
                "must not invoke pip from library code"
            )

    # ------------------------------------------------------------------
    # EXPECTED PASS: short-circuit on successful import already works
    # ------------------------------------------------------------------

    def test_ensure_memory_lib_returns_true_when_lib_present(self) -> None:
        """EXPECTED PASS (both before and after fix).

        When amplihack_memory is importable, ensure_memory_lib_installed()
        must return True without any subprocess calls.
        """
        ensure = self._get_ensure_fn()

        # Inject a fake module so the import succeeds
        fake_mod = _make_fake_memory_module()
        sys.modules["amplihack_memory"] = fake_mod

        try:
            with (
                patch("subprocess.run") as mock_run,
                patch("subprocess.Popen") as mock_popen,
            ):
                result = ensure()

            assert result is True, f"Expected True when lib present, got {result!r}"
            mock_run.assert_not_called()
            mock_popen.assert_not_called()
        finally:
            sys.modules.pop("amplihack_memory", None)

    def test_ensure_memory_lib_error_message_contains_no_dynamic_paths(self) -> None:
        """EXPECTED FAIL before fix (function doesn't raise at all currently).

        SEC-003: The ImportError message must contain only hardcoded install
        instructions — no sys.path, sys.executable, VIRTUAL_ENV, or dynamic
        paths in the user-visible string.
        """
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with pytest.raises(ImportError) as exc_info:
            ensure()

        error_msg = str(exc_info.value)
        # Must not leak interpreter path (e.g. /usr/bin/python3.12)
        assert sys.executable not in error_msg, (
            "ImportError must not expose sys.executable path"
        )
        # Must not leak virtualenv path
        import os
        venv = os.environ.get("VIRTUAL_ENV", "")
        if venv:
            assert venv not in error_msg, (
                "ImportError must not expose VIRTUAL_ENV path"
            )

    def test_ensure_memory_lib_raise_from_none(self) -> None:
        """EXPECTED FAIL before fix.

        SEC-002: `raise ImportError(...) from None` — chained exception must
        be suppressed so internal import machinery paths are not leaked.
        """
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with pytest.raises(ImportError) as exc_info:
            ensure()

        assert exc_info.value.__cause__ is None, (
            "ImportError must use `raise ... from None` to suppress chained traceback"
        )
        assert exc_info.value.__context__ is None or not exc_info.value.__suppress_context__ is False, (
            "ImportError context must be suppressed (raise ... from None)"
        )


# ---------------------------------------------------------------------------
# Test 3 — main() must NOT call ensure_memory_lib_installed()
# ---------------------------------------------------------------------------


class TestMainDoesNotAutoInstall:
    """CLI main() must not invoke ensure_memory_lib_installed()."""

    def test_main_does_not_call_ensure_memory_lib_installed(self) -> None:
        """EXPECTED FAIL before fix.

        main() currently calls ensure_memory_lib_installed() before delegating
        to cli_main(). After the fix it must not call it.

        Strategy: patch ensure_memory_lib_installed and the downstream cli_main,
        call main(), assert the guard was never invoked.
        """
        _drop_amplihack_from_sys_modules()

        # Import fresh __init__ to get main
        import amplihack

        ensure_mock = MagicMock(return_value=True)
        cli_main_mock = MagicMock(return_value=0)

        with (
            patch("amplihack.memory_auto_install.ensure_memory_lib_installed", ensure_mock),
            patch("amplihack.cli.main", cli_main_mock, create=True),
        ):
            try:
                amplihack.main()
            except Exception:
                # CLI internals may fail in test env — we only care about
                # whether ensure_memory_lib_installed was called
                pass

        assert ensure_mock.call_count == 0, (
            f"main() called ensure_memory_lib_installed() {ensure_mock.call_count} time(s); "
            "it must not call it after the fix"
        )

        _drop_amplihack_from_sys_modules()


# ---------------------------------------------------------------------------
# Test 4 — pyproject.toml: memory lib must be optional, not mandatory
# ---------------------------------------------------------------------------


class TestPyprojectTomlMemoryDependency:
    """pyproject.toml must declare amplihack-memory-lib as optional."""

    @pytest.fixture(scope="class")
    def pyproject(self) -> dict:
        """Parse pyproject.toml from repo root."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        repo_root = Path(__file__).parent.parent
        pyproject_path = repo_root / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"
        with pyproject_path.open("rb") as f:
            return tomllib.load(f)

    def test_memory_lib_is_optional_dependency_in_pyproject(self, pyproject: dict) -> None:
        """EXPECTED FAIL before fix.

        amplihack-memory-lib must NOT appear in [project.dependencies].
        It must appear in [project.optional-dependencies] under 'memory'.
        """
        mandatory_deps: list[str] = pyproject.get("project", {}).get("dependencies", [])
        optional_deps: dict[str, list[str]] = pyproject.get("project", {}).get("optional-dependencies", {})

        # It must not be in mandatory dependencies
        memory_in_mandatory = any("amplihack-memory-lib" in dep for dep in mandatory_deps)
        assert not memory_in_mandatory, (
            "amplihack-memory-lib must NOT be in [project.dependencies] — "
            "it must be an optional extra (amplihack[memory])"
        )

        # It must be in optional-dependencies under 'memory'
        memory_optional = optional_deps.get("memory", [])
        memory_in_optional = any("amplihack-memory-lib" in dep for dep in memory_optional)
        assert memory_in_optional, (
            "amplihack-memory-lib must appear in [project.optional-dependencies] "
            "under the 'memory' key so users install it with: pip install amplihack[memory]"
        )

    def test_memory_optional_dep_is_pinned_not_floating(self, pyproject: dict) -> None:
        """EXPECTED FAIL before fix (memory optional group doesn't exist yet).

        SEC-004: The optional memory dep must be pinned to a specific tag or
        SHA — never @main or @master (supply chain risk).
        """
        optional_deps: dict[str, list[str]] = pyproject.get("project", {}).get("optional-dependencies", {})
        memory_deps = optional_deps.get("memory", [])

        for dep in memory_deps:
            if "amplihack-memory-lib" in dep:
                assert "@main" not in dep, (
                    f"SEC-004: memory dep must not use @main branch: {dep!r}"
                )
                assert "@master" not in dep, (
                    f"SEC-004: memory dep must not use @master branch: {dep!r}"
                )
                break
        else:
            pytest.fail(
                "amplihack-memory-lib not found in [project.optional-dependencies].memory — "
                "run the fix first"
            )


# ---------------------------------------------------------------------------
# Test 5 — memory_auto_install.py must have zero subprocess/os.system refs
# ---------------------------------------------------------------------------


class TestMemoryAutoInstallModuleHasNoSubprocess:
    """SEC-005: memory_auto_install.py must not import subprocess after the fix."""

    def _get_source_path(self) -> Path:
        src = Path(__file__).parent.parent / "src" / "amplihack" / "memory_auto_install.py"
        assert src.exists(), f"memory_auto_install.py not found at {src}"
        return src

    def test_memory_auto_install_has_no_subprocess_import(self) -> None:
        """EXPECTED FAIL before fix.

        SEC-005: After the rewrite, memory_auto_install.py must contain zero
        references to subprocess, os.system, sys.executable, or any
        process-spawning mechanism.
        """
        source = self._get_source_path().read_text()

        forbidden = [
            "import subprocess",
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "os.popen",
        ]
        violations = [tok for tok in forbidden if tok in source]
        assert not violations, (
            f"memory_auto_install.py must not reference process-spawning APIs after fix. "
            f"Found: {violations!r}"
        )

    def test_memory_auto_install_has_no_pip_invocation(self) -> None:
        """EXPECTED FAIL before fix.

        Ensure no pip install strings remain in memory_auto_install.py.
        """
        source = self._get_source_path().read_text()

        pip_patterns = [
            "pip install",
            '"-m", "pip"',
            "[sys.executable",
        ]
        violations = [p for p in pip_patterns if p in source]
        assert not violations, (
            f"memory_auto_install.py must not contain pip invocations. Found: {violations!r}"
        )
