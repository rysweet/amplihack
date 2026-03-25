"""Tests for SDK dependency validation (dep_check module).

Verifies that:
1. validate_sdk_deps detects missing packages
2. validate_sdk_deps passes when all deps are present
3. check_sdk_dep returns correct bools
4. ensure_sdk_deps targets the running interpreter
5. SDK adapter imports work end-to-end
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

from amplihack.dep_check import (
    SDK_DEPENDENCIES,
    DepCheckResult,
    check_sdk_dep,
    ensure_sdk_deps,
    validate_sdk_deps,
)

_HAS_AGENT_FRAMEWORK = check_sdk_dep("agent_framework")
_skip_no_af = pytest.mark.skipif(
    not _HAS_AGENT_FRAMEWORK,
    reason="agent-framework-core not installed (optional dependency)",
)


# ===========================================================================
# 1. Real import tests (only when optional dep is installed)
# ===========================================================================
@_skip_no_af
class TestAgentFrameworkInstalled:
    """Verify agent-framework-core is actually importable when installed."""

    def test_agent_framework_importable(self):
        """Core test: import agent_framework must succeed."""
        mod = importlib.import_module("agent_framework")
        assert mod is not None

    def test_agent_framework_has_agent_class(self):
        """Agent class must be importable from agent_framework."""
        from agent_framework import Agent  # noqa: F401

    def test_agent_framework_has_function_tool(self):
        """FunctionTool must be importable from agent_framework."""
        from agent_framework import FunctionTool  # noqa: F401

    def test_agent_framework_openai_client(self):
        """OpenAIChatClient must be importable from agent_framework.openai."""
        from agent_framework.openai import OpenAIChatClient  # noqa: F401


# ===========================================================================
# 2. validate_sdk_deps tests
# ===========================================================================
class TestValidateSdkDeps:
    """Test the validate_sdk_deps function."""

    @_skip_no_af
    def test_passes_when_all_installed(self):
        """Should return all_ok=True when deps are present."""
        result = validate_sdk_deps(raise_on_missing=False)
        assert result.all_ok
        assert "agent_framework" in result.available
        assert result.missing == []

    def test_raises_when_missing(self):
        """Should raise ImportError when a dep is missing."""
        fake_deps = {"nonexistent_package_xyz": "nonexistent-package-xyz"}
        with patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps):
            with pytest.raises(ImportError, match="Required SDK dependencies are missing"):
                validate_sdk_deps(raise_on_missing=True)

    def test_no_raise_when_missing_but_flag_false(self):
        """Should return result without raising when raise_on_missing=False."""
        fake_deps = {"nonexistent_package_xyz": "nonexistent-package-xyz"}
        with patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps):
            result = validate_sdk_deps(raise_on_missing=False)
            assert not result.all_ok
            assert "nonexistent_package_xyz" in result.missing

    def test_error_message_includes_install_command(self):
        """Error message should include pip install instructions."""
        fake_deps = {"fake_pkg": "fake-pkg"}
        with patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps):
            with pytest.raises(ImportError, match="pip install fake-pkg"):
                validate_sdk_deps(raise_on_missing=True)


# ===========================================================================
# 3. check_sdk_dep tests
# ===========================================================================
class TestCheckSdkDep:
    """Test the check_sdk_dep function."""

    @_skip_no_af
    def test_returns_true_for_installed(self):
        assert check_sdk_dep("agent_framework") is True

    def test_returns_true_for_stdlib(self):
        assert check_sdk_dep("json") is True

    def test_returns_false_for_missing(self):
        assert check_sdk_dep("nonexistent_package_xyz_123") is False


# ===========================================================================
# 4. DepCheckResult tests
# ===========================================================================
class TestDepCheckResult:
    """Test the DepCheckResult dataclass."""

    def test_all_ok_when_no_missing(self):
        result = DepCheckResult(available=["a", "b"], missing=[])
        assert result.all_ok is True

    def test_not_ok_when_missing(self):
        result = DepCheckResult(available=["a"], missing=["b"])
        assert result.all_ok is False

    def test_empty_is_ok(self):
        result = DepCheckResult()
        assert result.all_ok is True


# ===========================================================================
# 5. SDK_DEPENDENCIES registry tests
# ===========================================================================
class TestSdkDependenciesRegistry:
    """Test the SDK_DEPENDENCIES dict is correctly configured."""

    def test_agent_framework_in_registry(self):
        assert "agent_framework" in SDK_DEPENDENCIES

    def test_pip_name_correct(self):
        assert SDK_DEPENDENCIES["agent_framework"] == "agent-framework-core"


# ===========================================================================
# 6. ensure_sdk_deps tests
# ===========================================================================
class TestEnsureSdkDeps:
    """Test the ensure_sdk_deps auto-install function."""

    @_skip_no_af
    def test_returns_ok_when_all_installed(self):
        """Should short-circuit when deps already present."""
        result = ensure_sdk_deps()
        assert result.all_ok

    def test_uses_python_flag_with_uv(self):
        """uv pip install must use --python to target the running interpreter."""
        import sys

        fake_deps = {"nonexistent_pkg_test": "nonexistent-pkg-test"}
        with (
            patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps),
            patch("shutil.which", return_value="/usr/bin/uv"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = type("R", (), {"returncode": 1, "stderr": "not found"})()
            with pytest.raises(ImportError):
                ensure_sdk_deps()

            cmd = mock_run.call_args[0][0]
            assert "--python" in cmd, f"--python flag missing from uv command: {cmd}"
            assert sys.executable in cmd, f"sys.executable missing from uv command: {cmd}"

    def test_uses_pre_flag_with_pip(self):
        """pip install must use --pre for pre-release packages."""
        fake_deps = {"nonexistent_pkg_test": "nonexistent-pkg-test"}
        with (
            patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps),
            patch("shutil.which", side_effect=lambda x: None if x == "uv" else "/usr/bin/pip"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = type("R", (), {"returncode": 1, "stderr": "not found"})()
            with pytest.raises(ImportError):
                ensure_sdk_deps()

            cmd = mock_run.call_args[0][0]
            assert "--pre" in cmd, f"--pre flag missing from pip command: {cmd}"

    def test_invalidates_import_caches_after_install(self):
        """Must call importlib.invalidate_caches() after installing."""
        fake_deps = {"nonexistent_pkg_test": "nonexistent-pkg-test"}
        with (
            patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps),
            patch("shutil.which", return_value="/usr/bin/uv"),
            patch("subprocess.run") as mock_run,
            patch("importlib.invalidate_caches") as mock_invalidate,
        ):
            mock_run.return_value = type("R", (), {"returncode": 0, "stderr": "", "stdout": ""})()
            # Install "succeeds" but dep still can't import → raises
            with pytest.raises(ImportError):
                ensure_sdk_deps()
            mock_invalidate.assert_called_once()


# ===========================================================================
# 7. End-to-end SDK adapter import tests
# ===========================================================================
class TestSdkAdapterImports:
    """Verify all SDK adapter modules import without error."""

    def test_microsoft_sdk_module_imports(self):
        mod = importlib.import_module("amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk")
        assert hasattr(mod, "MicrosoftGoalSeekingAgent")

    @_skip_no_af
    def test_microsoft_sdk_has_agent_framework_flag(self):
        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import (
            _HAS_AGENT_FRAMEWORK,
        )

        assert _HAS_AGENT_FRAMEWORK is True, (
            "agent-framework-core not detected by microsoft_sdk module. "
            "Ensure agent-framework-core is installed."
        )

    def test_factory_module_imports(self):
        mod = importlib.import_module("amplihack.agents.goal_seeking.sdk_adapters.factory")
        assert hasattr(mod, "create_agent")

    def test_base_module_imports(self):
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            GoalSeekingAgent,
            SDKType,
        )

        assert SDKType.MICROSOFT is not None
        assert GoalSeekingAgent is not None
