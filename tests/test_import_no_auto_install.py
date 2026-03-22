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

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_AMPLIHACK_PREFIX = "amplihack"


def _drop_amplihack_from_sys_modules() -> None:
    """Remove every amplihack-prefixed entry from sys.modules."""
    to_remove = [
        k for k in sys.modules if k == _AMPLIHACK_PREFIX or k.startswith(_AMPLIHACK_PREFIX + ".")
    ]
    for key in to_remove:
        del sys.modules[key]


def _make_fake_memory_module() -> types.ModuleType:
    """Return a minimal stub for amplihack_memory to simulate lib presence."""
    mod = types.ModuleType("amplihack_memory")
    mod.__version__ = "0.2.0"
    return mod


class TestImportAmplihackNoSubprocess:
    """import amplihack must produce zero subprocess side-effects."""

    def test_import_amplihack_no_subprocess_at_module_level(self) -> None:
        """A fresh package import must not spawn installers."""
        _drop_amplihack_from_sys_modules()
        sys.modules.pop("amplihack_memory", None)

        with (
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
        ):
            import amplihack  # noqa: F401

            mock_run.assert_not_called()
            mock_popen.assert_not_called()

        _drop_amplihack_from_sys_modules()


class TestEnsureMemoryLibInstalledContract:
    """ensure_memory_lib_installed() must be a pure guard, not an installer."""

    def setup_method(self) -> None:
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]
        sys.modules.pop("amplihack.memory_auto_install", None)

    def teardown_method(self) -> None:
        sys.modules.pop("amplihack_memory", None)
        sys.modules.pop("amplihack.memory_auto_install", None)

    def _get_ensure_fn(self):
        if "amplihack.memory_auto_install" in sys.modules:
            del sys.modules["amplihack.memory_auto_install"]
        from amplihack.memory_auto_install import ensure_memory_lib_installed

        return ensure_memory_lib_installed

    def test_ensure_memory_lib_raises_import_error_when_absent(self) -> None:
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with pytest.raises(ImportError) as exc_info:
            ensure()

        error_msg = str(exc_info.value)
        assert "amplihack[memory]" in error_msg
        assert "pip install" in error_msg

    def test_ensure_memory_lib_no_subprocess_when_absent(self) -> None:
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with (
            patch("subprocess.run") as mock_run,
            patch("subprocess.Popen") as mock_popen,
        ):
            try:
                ensure()
            except ImportError:
                pass

            mock_run.assert_not_called()
            mock_popen.assert_not_called()

    def test_ensure_memory_lib_returns_true_when_lib_present(self) -> None:
        ensure = self._get_ensure_fn()
        fake_mod = _make_fake_memory_module()
        sys.modules["amplihack_memory"] = fake_mod

        try:
            with (
                patch("subprocess.run") as mock_run,
                patch("subprocess.Popen") as mock_popen,
            ):
                result = ensure()

            assert result is True
            mock_run.assert_not_called()
            mock_popen.assert_not_called()
        finally:
            sys.modules.pop("amplihack_memory", None)

    def test_ensure_memory_lib_raise_from_none(self) -> None:
        ensure = self._get_ensure_fn()
        sys.modules["amplihack_memory"] = None  # type: ignore[assignment]

        with pytest.raises(ImportError) as exc_info:
            ensure()

        assert exc_info.value.__cause__ is None
        assert (
            exc_info.value.__context__ is None or exc_info.value.__suppress_context__ is not False
        )


class TestMainDoesNotAutoInstall:
    """CLI main() must not invoke ensure_memory_lib_installed()."""

    def test_main_does_not_call_ensure_memory_lib_installed(self) -> None:
        _drop_amplihack_from_sys_modules()

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
                pass

        assert ensure_mock.call_count == 0
        _drop_amplihack_from_sys_modules()


class TestPyprojectTomlMemoryDependency:
    """pyproject.toml must declare amplihack-memory-lib as optional."""

    @pytest.fixture(scope="class")
    def pyproject(self) -> dict:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        repo_root = Path(__file__).parent.parent
        pyproject_path = repo_root / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            return tomllib.load(f)

    def test_memory_lib_is_optional_dependency_in_pyproject(self, pyproject: dict) -> None:
        mandatory_deps: list[str] = pyproject.get("project", {}).get("dependencies", [])
        optional_deps: dict[str, list[str]] = pyproject.get("project", {}).get(
            "optional-dependencies", {}
        )

        assert not any("amplihack-memory-lib" in dep for dep in mandatory_deps)
        memory_optional = optional_deps.get("memory", [])
        assert any("amplihack-memory-lib" in dep for dep in memory_optional)

    def test_memory_optional_dep_is_pinned_not_floating(self, pyproject: dict) -> None:
        optional_deps: dict[str, list[str]] = pyproject.get("project", {}).get(
            "optional-dependencies", {}
        )
        memory_deps = optional_deps.get("memory", [])

        for dep in memory_deps:
            if "amplihack-memory-lib" in dep:
                assert "@main" not in dep
                assert "@master" not in dep
                break
        else:
            pytest.fail("amplihack-memory-lib not found in [project.optional-dependencies].memory")


class TestMemoryAutoInstallModuleHasNoSubprocess:
    """SEC-005: memory_auto_install.py must not import subprocess after the fix."""

    def _get_source_path(self) -> Path:
        src = Path(__file__).parent.parent / "src" / "amplihack" / "memory_auto_install.py"
        assert src.exists()
        return src

    def test_memory_auto_install_has_no_subprocess_import(self) -> None:
        source = self._get_source_path().read_text()
        assert "import subprocess" not in source

    def test_memory_auto_install_has_no_pip_invocation(self) -> None:
        source = self._get_source_path().read_text()

        pip_patterns = [
            '"-m", "pip"',
            "[sys.executable",
        ]
        violations = [p for p in pip_patterns if p in source]
        assert not violations
