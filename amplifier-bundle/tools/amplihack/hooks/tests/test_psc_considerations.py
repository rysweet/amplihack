# File: amplifier-bundle/tools/amplihack/hooks/tests/test_psc_considerations.py
"""Tests for power_steering_checker.considerations module.

Tests all four dataclasses: CheckerResult, ConsiderationAnalysis,
PowerSteeringResult, PowerSteeringRedirect.
"""

import sys
from pathlib import Path

# Allow importing from hooks directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker.considerations import (
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringRedirect,
    PowerSteeringResult,
)


class TestCheckerResult:
    """Tests for CheckerResult dataclass."""

    def test_basic_creation(self):
        result = CheckerResult(
            consideration_id="test_check",
            satisfied=True,
            reason="All good",
            severity="blocker",
        )
        assert result.consideration_id == "test_check"
        assert result.satisfied is True
        assert result.reason == "All good"
        assert result.severity == "blocker"

    def test_default_fields(self):
        result = CheckerResult(
            consideration_id="test",
            satisfied=False,
            reason="Failed",
            severity="warning",
        )
        assert result.recovery_steps == []
        assert result.executed is True

    def test_id_alias(self):
        """id property is alias for consideration_id."""
        result = CheckerResult(
            consideration_id="my_check",
            satisfied=True,
            reason="OK",
            severity="blocker",
        )
        assert result.id == "my_check"

    def test_severity_blocker(self):
        result = CheckerResult(
            consideration_id="c", satisfied=False, reason="r", severity="blocker"
        )
        assert result.severity == "blocker"

    def test_severity_warning(self):
        result = CheckerResult(
            consideration_id="c", satisfied=False, reason="r", severity="warning"
        )
        assert result.severity == "warning"

    def test_recovery_steps_populated(self):
        result = CheckerResult(
            consideration_id="c",
            satisfied=False,
            reason="r",
            severity="blocker",
            recovery_steps=["step1", "step2"],
        )
        assert result.recovery_steps == ["step1", "step2"]

    def test_executed_false(self):
        result = CheckerResult(
            consideration_id="c",
            satisfied=True,
            reason="skipped",
            severity="warning",
            executed=False,
        )
        assert result.executed is False


class TestConsiderationAnalysis:
    """Tests for ConsiderationAnalysis dataclass."""

    def test_default_creation(self):
        analysis = ConsiderationAnalysis()
        assert analysis.results == {}
        assert analysis.failed_blockers == []
        assert analysis.failed_warnings == []

    def test_has_blockers_empty(self):
        analysis = ConsiderationAnalysis()
        assert analysis.has_blockers is False

    def test_add_passed_result(self):
        analysis = ConsiderationAnalysis()
        result = CheckerResult(
            consideration_id="c1", satisfied=True, reason="OK", severity="blocker"
        )
        analysis.add_result(result)
        assert "c1" in analysis.results
        assert analysis.failed_blockers == []

    def test_add_failed_blocker(self):
        analysis = ConsiderationAnalysis()
        result = CheckerResult(
            consideration_id="c1", satisfied=False, reason="Failed", severity="blocker"
        )
        analysis.add_result(result)
        assert analysis.has_blockers is True
        assert len(analysis.failed_blockers) == 1

    def test_add_failed_warning(self):
        analysis = ConsiderationAnalysis()
        result = CheckerResult(
            consideration_id="c1", satisfied=False, reason="Warn", severity="warning"
        )
        analysis.add_result(result)
        assert not analysis.has_blockers
        assert len(analysis.failed_warnings) == 1

    def test_multiple_results(self):
        analysis = ConsiderationAnalysis()
        for i in range(3):
            analysis.add_result(
                CheckerResult(
                    consideration_id=f"c{i}",
                    satisfied=i % 2 == 0,
                    reason="r",
                    severity="blocker",
                )
            )
        assert len(analysis.results) == 3

    def test_group_by_category(self):
        analysis = ConsiderationAnalysis()
        analysis.add_result(
            CheckerResult(
                consideration_id="workflow_check",
                satisfied=False,
                reason="r",
                severity="blocker",
            )
        )
        grouped = analysis.group_by_category()
        assert len(grouped) > 0


class TestPowerSteeringResult:
    """Tests for PowerSteeringResult dataclass."""

    def test_basic_approve(self):
        result = PowerSteeringResult(decision="approve", reasons=["done"])
        assert result.decision == "approve"
        assert result.reasons == ["done"]

    def test_basic_block(self):
        result = PowerSteeringResult(decision="block", reasons=["incomplete"])
        assert result.decision == "block"

    def test_default_fields(self):
        result = PowerSteeringResult(decision="approve", reasons=[])
        assert result.continuation_prompt is None
        assert result.summary is None
        assert result.analysis is None
        assert result.is_first_stop is False
        assert result.evidence_results == []
        assert result.compaction_context is None
        assert result.considerations == []

    def test_with_continuation_prompt(self):
        result = PowerSteeringResult(
            decision="block",
            reasons=["incomplete"],
            continuation_prompt="Please fix X",
        )
        assert result.continuation_prompt == "Please fix X"

    def test_with_analysis(self):
        analysis = ConsiderationAnalysis()
        result = PowerSteeringResult(decision="approve", reasons=[], analysis=analysis)
        assert result.analysis is analysis


class TestPowerSteeringRedirect:
    """Tests for PowerSteeringRedirect dataclass."""

    def test_basic_creation(self):
        redirect = PowerSteeringRedirect(
            redirect_number=1,
            timestamp="2024-01-01T00:00:00",
            failed_considerations=["c1"],
            continuation_prompt="Fix this",
        )
        assert redirect.redirect_number == 1
        assert redirect.timestamp == "2024-01-01T00:00:00"
        assert redirect.failed_considerations == ["c1"]
        assert redirect.continuation_prompt == "Fix this"

    def test_default_work_summary(self):
        redirect = PowerSteeringRedirect(
            redirect_number=1,
            timestamp="2024-01-01T00:00:00",
            failed_considerations=[],
            continuation_prompt="fix",
        )
        assert redirect.work_summary is None

    def test_with_work_summary(self):
        redirect = PowerSteeringRedirect(
            redirect_number=2,
            timestamp="2024-01-01T00:00:00",
            failed_considerations=["c1", "c2"],
            continuation_prompt="Fix both",
            work_summary="Did some work",
        )
        assert redirect.work_summary == "Did some work"

    def test_multiple_failed_considerations(self):
        redirect = PowerSteeringRedirect(
            redirect_number=1,
            timestamp="now",
            failed_considerations=["a", "b", "c"],
            continuation_prompt="fix",
        )
        assert len(redirect.failed_considerations) == 3
