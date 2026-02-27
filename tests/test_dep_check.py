"""Tests for SDK dependency validation (dep_check module).

Verifies that:
1. agent-framework is importable (the actual fix for #2660)
2. validate_sdk_deps detects missing packages
3. validate_sdk_deps passes when all deps are present
4. check_sdk_dep returns correct bools
5. All SDK adapter imports work end-to-end
"""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

from amplihack.dep_check import (
    SDK_DEPENDENCIES,
    DepCheckResult,
    check_sdk_dep,
    validate_sdk_deps,
)


# ===========================================================================
# 1. Real import tests (the actual #2660 fix verification)
# ===========================================================================
class TestAgentFrameworkInstalled:
    """Verify agent-framework is actually importable after install."""

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
        assert SDK_DEPENDENCIES["agent_framework"] == "agent-framework"


# ===========================================================================
# 6. End-to-end SDK adapter import tests
# ===========================================================================
class TestSdkAdapterImports:
    """Verify all SDK adapter modules import without error."""

    def test_microsoft_sdk_module_imports(self):
        mod = importlib.import_module("amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk")
        assert hasattr(mod, "MicrosoftGoalSeekingAgent")

    def test_microsoft_sdk_has_agent_framework_flag(self):
        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import (
            _HAS_AGENT_FRAMEWORK,
        )

        assert _HAS_AGENT_FRAMEWORK is True, (
            "agent-framework not detected by microsoft_sdk module. "
            "Ensure agent-framework is installed."
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
