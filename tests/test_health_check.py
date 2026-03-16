"""
Unit tests for amplihack.health_check module.

Tests verify the public contract:
  - check_health() -> HealthReport
  - HealthReport fields: status, checks_passed, checks_failed, details
  - Status values: 'healthy' | 'degraded' | 'unhealthy'
  - Function never raises

These tests focus on the contract (observable behaviour), not implementation
internals — in line with the brick philosophy.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is on sys.path for direct test runs
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.health_check import (
    HealthReport,
    _check_dependency,
    _check_path,
    _project_root,
    check_health,
)

# ---------------------------------------------------------------------------
# HealthReport dataclass contract
# ---------------------------------------------------------------------------


class TestHealthReport:
    """HealthReport is an immutable dataclass with required fields."""

    def test_fields_present(self):
        report = HealthReport(
            status="healthy",
            checks_passed=["dep:rich"],
            checks_failed=[],
            details={"dep:rich": "found"},
        )
        assert report.status == "healthy"
        assert report.checks_passed == ["dep:rich"]
        assert report.checks_failed == []
        assert report.details == {"dep:rich": "found"}

    def test_frozen(self):
        """HealthReport must be immutable (frozen=True)."""
        report = HealthReport(
            status="healthy",
            checks_passed=[],
            checks_failed=[],
            details={},
        )
        with pytest.raises((AttributeError, TypeError)):
            report.status = "unhealthy"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# check_health() — public API
# ---------------------------------------------------------------------------


class TestCheckHealth:
    """check_health() public contract."""

    def test_returns_health_report(self):
        report = check_health()
        assert isinstance(report, HealthReport)

    def test_status_is_valid_value(self):
        report = check_health()
        assert report.status in {"healthy", "degraded", "unhealthy"}

    def test_details_has_expected_keys(self):
        """details must contain entries for every dep and path check."""
        report = check_health()
        from amplihack.health_check import _CRITICAL_DEPS, _CRITICAL_PATHS

        expected_keys = {f"dep:{d}" for d in _CRITICAL_DEPS} | {
            f"path:{p}" for p in _CRITICAL_PATHS
        }
        assert expected_keys.issubset(report.details.keys())

    def test_checks_are_disjoint(self):
        """A check name cannot appear in both passed and failed."""
        report = check_health()
        overlap = set(report.checks_passed) & set(report.checks_failed)
        assert overlap == set()

    def test_checks_cover_all_checks(self):
        """Every check name appears in exactly one of passed/failed."""
        report = check_health()
        from amplihack.health_check import _CRITICAL_DEPS, _CRITICAL_PATHS

        expected = {f"dep:{d}" for d in _CRITICAL_DEPS} | {f"path:{p}" for p in _CRITICAL_PATHS}
        union = set(report.checks_passed) | set(report.checks_failed)
        assert expected == union

    def test_never_raises(self):
        """check_health() must not raise under any circumstances."""
        # Patch _project_root to raise to simulate extreme failure
        with patch("amplihack.health_check._project_root", side_effect=RuntimeError("boom")):
            # Should still return a HealthReport without raising
            report = check_health()
            assert isinstance(report, HealthReport)


# ---------------------------------------------------------------------------
# Status classification rules
# ---------------------------------------------------------------------------


class TestStatusClassification:
    """Status reduction rules: unhealthy > degraded > healthy."""

    def test_unhealthy_when_dep_missing(self):
        """If any dep check fails -> status must be 'unhealthy'."""
        with patch("amplihack.health_check._check_dependency", return_value=(False, "not found")):
            report = check_health()
        assert report.status == "unhealthy"

    def test_degraded_when_only_paths_fail(self):
        """Deps all pass, some path missing -> status must be 'degraded'."""
        with (
            patch(
                "amplihack.health_check._check_dependency",
                return_value=(True, "found"),
            ),
            patch(
                "amplihack.health_check._check_path",
                return_value=(False, "not found"),
            ),
        ):
            report = check_health()
        assert report.status == "degraded"

    def test_healthy_when_all_pass(self):
        """All deps and paths pass -> status must be 'healthy'."""
        with (
            patch(
                "amplihack.health_check._check_dependency",
                return_value=(True, "found"),
            ),
            patch(
                "amplihack.health_check._check_path",
                return_value=(True, "ok"),
            ),
        ):
            report = check_health()
        assert report.status == "healthy"


# ---------------------------------------------------------------------------
# _check_dependency — internal helper (tested for robustness)
# ---------------------------------------------------------------------------


class TestCheckDependency:
    """_check_dependency returns (bool, str) and never raises."""

    def test_known_stdlib_module(self):
        """sys is always importable."""
        ok, msg = _check_dependency("sys")
        assert ok is True
        assert msg == "found"

    def test_nonexistent_package(self):
        ok, msg = _check_dependency("_amplihack_does_not_exist_xyz")
        assert ok is False
        assert msg in {"not found", "internal error"}

    def test_returns_tuple_of_two(self):
        result = _check_dependency("os")
        assert len(result) == 2

    def test_message_is_string(self):
        _, msg = _check_dependency("os")
        assert isinstance(msg, str)

    def test_exception_in_find_spec_returns_false(self):
        """Simulate find_spec raising an unexpected exception."""
        import importlib.util as ilu

        with patch.object(ilu, "find_spec", side_effect=Exception("unexpected")):
            ok, msg = _check_dependency("anything")
        assert ok is False
        assert msg == "internal error"


# ---------------------------------------------------------------------------
# _check_path — internal helper
# ---------------------------------------------------------------------------


class TestCheckPath:
    """_check_path(path) -> (bool, str); never raises."""

    def test_existing_path(self, tmp_path):
        ok, msg = _check_path(tmp_path)
        assert ok is True
        assert msg == "ok"

    def test_missing_path(self, tmp_path):
        ok, msg = _check_path(tmp_path / "does_not_exist")
        assert ok is False
        assert msg == "not found"

    def test_never_raises_on_exception(self):
        fake = Path("/proc/invalid_\x00path")  # NUL in path raises on some OS
        ok, msg = _check_path(fake)
        # Should return (False, ...) rather than raising
        assert isinstance(ok, bool)
        assert isinstance(msg, str)


# ---------------------------------------------------------------------------
# _project_root
# ---------------------------------------------------------------------------


class TestProjectRoot:
    """_project_root() returns the repository root directory."""

    def test_returns_path(self):
        root = _project_root()
        assert isinstance(root, Path)

    def test_root_is_absolute(self):
        root = _project_root()
        assert root.is_absolute()
