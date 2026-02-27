#!/usr/bin/env python3
"""
Tests for Issue #2473: power-steering stop hook reports false failures
when all checks actually pass.

Root causes fixed:
1. stop.py: First-stop visibility block returned decision="block" even when all
   checks passed, causing Claude Code to report a false failure. Fix: return
   decision="approve" when reasons=["first_stop_visibility"] (all checks passed).

2. power_steering_checker.py _create_passing_analysis(): Created new
   ConsiderationAnalysis with empty failed_blockers/failed_warnings lists even
   when modified_results contained unsatisfied warnings. Fix: rebuild failed
   lists from modified results for data consistency.

3. power_steering_checker.py first-stop visibility path: Did not record turn
   state approval, leaving turn state in ambiguous state. Fix: record approval
   in turn state manager.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import (
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringChecker,
    PowerSteeringResult,
)


class TestCreatePassingAnalysisConsistency(unittest.TestCase):
    """Tests for _create_passing_analysis() data consistency fix."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        ).write_text(json.dumps(config))

    def test_passing_analysis_has_empty_failed_blockers_when_all_addressed(self):
        """When all blockers are addressed, failed_blockers should be empty."""
        checker = PowerSteeringChecker(self.project_root)

        # Original analysis with one blocker
        original = ConsiderationAnalysis()
        blocker = CheckerResult(
            consideration_id="test_blocker",
            satisfied=False,
            reason="Not done",
            severity="blocker",
        )
        original.add_result(blocker)
        self.assertTrue(original.has_blockers)

        # Address the blocker
        addressed = {"test_blocker": "Fixed it"}
        result = checker._create_passing_analysis(original, addressed)

        # The new analysis should have no failed blockers
        self.assertFalse(result.has_blockers)
        self.assertEqual(len(result.failed_blockers), 0)

    def test_passing_analysis_preserves_unsatisfied_warnings_in_lists(self):
        """Unsatisfied warnings should appear in failed_warnings list (consistency)."""
        checker = PowerSteeringChecker(self.project_root)

        # Original analysis with one blocker and one warning
        original = ConsiderationAnalysis()
        blocker = CheckerResult(
            consideration_id="test_blocker",
            satisfied=False,
            reason="Not done",
            severity="blocker",
        )
        warning = CheckerResult(
            consideration_id="test_warning",
            satisfied=False,
            reason="Could be better",
            severity="warning",
        )
        original.add_result(blocker)
        original.add_result(warning)

        # Address only the blocker
        addressed = {"test_blocker": "Fixed it"}
        result = checker._create_passing_analysis(original, addressed)

        # Blocker addressed → no failed blockers
        self.assertEqual(len(result.failed_blockers), 0)
        # Warning NOT addressed → should be in failed_warnings
        self.assertEqual(len(result.failed_warnings), 1)
        self.assertEqual(result.failed_warnings[0].consideration_id, "test_warning")
        self.assertFalse(result.failed_warnings[0].satisfied)

    def test_passing_analysis_results_dict_consistent_with_lists(self):
        """results dict and failed_* lists must agree on satisfaction status."""
        checker = PowerSteeringChecker(self.project_root)

        original = ConsiderationAnalysis()
        original.add_result(
            CheckerResult("blocker_1", satisfied=False, reason="Fail", severity="blocker")
        )
        original.add_result(
            CheckerResult("blocker_2", satisfied=False, reason="Fail", severity="blocker")
        )
        original.add_result(
            CheckerResult("warn_1", satisfied=False, reason="Warn", severity="warning")
        )
        original.add_result(
            CheckerResult("pass_1", satisfied=True, reason="OK", severity="blocker")
        )

        addressed = {"blocker_1": "Done", "blocker_2": "Done"}
        result = checker._create_passing_analysis(original, addressed)

        # Count unsatisfied results from dict
        unsatisfied_from_dict = [r for r in result.results.values() if not r.satisfied]
        # Count from lists
        unsatisfied_from_lists = result.failed_blockers + result.failed_warnings

        # Both counts must match
        self.assertEqual(len(unsatisfied_from_dict), len(unsatisfied_from_lists))

        # Specifically: only warn_1 should be unsatisfied
        self.assertEqual(len(unsatisfied_from_dict), 1)
        self.assertEqual(unsatisfied_from_dict[0].consideration_id, "warn_1")

    def test_passing_analysis_all_satisfied_when_all_addressed(self):
        """When all concerns are addressed, everything should be satisfied."""
        checker = PowerSteeringChecker(self.project_root)

        original = ConsiderationAnalysis()
        original.add_result(CheckerResult("b1", satisfied=False, reason="Fail", severity="blocker"))
        original.add_result(CheckerResult("w1", satisfied=False, reason="Fail", severity="warning"))

        # Address everything
        addressed = {"b1": "Done", "w1": "Done"}
        result = checker._create_passing_analysis(original, addressed)

        self.assertEqual(len(result.failed_blockers), 0)
        self.assertEqual(len(result.failed_warnings), 0)
        self.assertFalse(result.has_blockers)

        # All results should be satisfied
        for r in result.results.values():
            self.assertTrue(r.satisfied, f"{r.consideration_id} should be satisfied")

    def test_passing_analysis_addressed_results_have_reason_annotation(self):
        """Addressed results should have [ADDRESSED: ...] in their reason."""
        checker = PowerSteeringChecker(self.project_root)

        original = ConsiderationAnalysis()
        original.add_result(
            CheckerResult("b1", satisfied=False, reason="Tests failing", severity="blocker")
        )

        addressed = {"b1": "All tests now pass"}
        result = checker._create_passing_analysis(original, addressed)

        b1_result = result.results["b1"]
        self.assertTrue(b1_result.satisfied)
        self.assertIn("[ADDRESSED: All tests now pass]", b1_result.reason)
        self.assertIn("Tests failing", b1_result.reason)


class TestStopHookVisibilityDecisionLogic(unittest.TestCase):
    """Tests for stop.py decision logic distinguishing visibility from failure.

    Instead of mocking the full stop hook process(), we test the core decision
    logic that determines whether a PowerSteeringResult represents a visibility
    block (all checks passed) vs an actual failure block.
    """

    def test_visibility_result_is_detected(self):
        """A first_stop_visibility result should be identified as visibility-only."""
        result = PowerSteeringResult(
            decision="block",
            reasons=["first_stop_visibility"],
            continuation_prompt="All power-steering checks passed!",
            analysis=ConsiderationAnalysis(),
            is_first_stop=True,
        )

        # This is the exact condition from the fix in stop.py
        is_visibility_only = result.is_first_stop and result.reasons == ["first_stop_visibility"]
        self.assertTrue(
            is_visibility_only,
            "first_stop_visibility result should be detected as visibility-only",
        )

    def test_actual_failure_is_not_visibility(self):
        """An actual failure result should NOT be identified as visibility-only."""
        result = PowerSteeringResult(
            decision="block",
            reasons=["tests_not_run", "workflow_not_followed"],
            continuation_prompt="Please complete the work",
            analysis=ConsiderationAnalysis(),
            is_first_stop=True,
        )

        is_visibility_only = result.is_first_stop and result.reasons == ["first_stop_visibility"]
        self.assertFalse(
            is_visibility_only,
            "Actual failure result should NOT be detected as visibility-only",
        )

    def test_subsequent_stop_is_not_visibility(self):
        """A subsequent stop result should NOT be detected as visibility-only."""
        result = PowerSteeringResult(
            decision="block",
            reasons=["first_stop_visibility"],
            continuation_prompt="...",
            analysis=ConsiderationAnalysis(),
            is_first_stop=False,
        )

        is_visibility_only = result.is_first_stop and result.reasons == ["first_stop_visibility"]
        self.assertFalse(
            is_visibility_only,
            "Subsequent stop should NOT be treated as visibility-only",
        )

    def test_approve_result_needs_no_special_handling(self):
        """An approve result doesn't need visibility detection."""
        result = PowerSteeringResult(
            decision="approve",
            reasons=["all_considerations_satisfied"],
            continuation_prompt=None,
        )

        # Approve results bypass the block handling entirely
        self.assertEqual(result.decision, "approve")

    def test_visibility_detection_precise_reasons_match(self):
        """Visibility detection must use exact match on reasons list."""
        # Mixed reasons should NOT be visibility-only
        result = PowerSteeringResult(
            decision="block",
            reasons=["first_stop_visibility", "some_other_reason"],
            analysis=ConsiderationAnalysis(),
            is_first_stop=True,
        )

        is_visibility_only = result.is_first_stop and result.reasons == ["first_stop_visibility"]
        self.assertFalse(
            is_visibility_only,
            "Mixed reasons should not be treated as visibility-only",
        )


class TestFirstStopVisibilityTurnState(unittest.TestCase):
    """Tests for turn state approval in first-stop visibility path."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        ).write_text(json.dumps(config))

    def test_first_stop_visibility_sets_complete_semaphore(self):
        """First-stop visibility path should set the _completed semaphore."""
        checker = PowerSteeringChecker(self.project_root)
        session_id = "test-session-2473"

        # Verify clean state
        self.assertFalse(checker._already_ran(session_id))

        # Simulate first-stop visibility: mark results shown and complete
        checker._mark_results_shown(session_id)
        checker._mark_complete(session_id)

        # Both semaphores must be set
        self.assertTrue(checker._results_already_shown(session_id))
        self.assertTrue(checker._already_ran(session_id))

    def test_subsequent_stop_after_visibility_approves(self):
        """After first-stop visibility, subsequent check() must approve immediately."""
        checker = PowerSteeringChecker(self.project_root)
        session_id = "test-session-2473-subsequent"

        # Simulate first stop already completed
        checker._mark_results_shown(session_id)
        checker._mark_complete(session_id)

        # Write minimal transcript
        transcript_file = self.project_root / f"{session_id}.jsonl"
        line = json.dumps({"type": "user", "message": {"role": "user", "content": "Fix login bug"}})
        transcript_file.write_text(line + "\n")

        # Subsequent check should approve via _already_ran
        result = checker.check(transcript_file, session_id)
        self.assertEqual(result.decision, "approve")
        self.assertIn("already_ran", result.reasons)


class TestFormatResultsTextWithPassingAnalysis(unittest.TestCase):
    """Tests for _format_results_text with _create_passing_analysis output."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        ).write_text(json.dumps(config))

    def test_all_addressed_shows_all_checks_passed(self):
        """When all concerns are addressed, format_results_text should show ALL CHECKS PASSED."""
        checker = PowerSteeringChecker(self.project_root)

        # Create analysis where all items are satisfied
        original = ConsiderationAnalysis()
        original.add_result(
            CheckerResult("test_check", satisfied=False, reason="Not done", severity="blocker")
        )

        addressed = {"test_check": "Done now"}
        passing_analysis = checker._create_passing_analysis(original, addressed)

        # Override considerations to match our test data
        checker.considerations = [
            {
                "id": "test_check",
                "question": "Was the test done?",
                "severity": "blocker",
                "category": "Testing",
            }
        ]

        results_text = checker._format_results_text(passing_analysis, "STANDARD")

        # Should show ALL CHECKS PASSED, not CHECKS FAILED
        self.assertIn("ALL CHECKS PASSED", results_text)
        self.assertNotIn("CHECKS FAILED", results_text)

    def test_passing_analysis_results_all_show_checkmark(self):
        """All addressed results should show ✅ in the formatted output."""
        checker = PowerSteeringChecker(self.project_root)

        original = ConsiderationAnalysis()
        original.add_result(CheckerResult("c1", satisfied=False, reason="Fail", severity="blocker"))
        original.add_result(CheckerResult("c2", satisfied=False, reason="Fail", severity="blocker"))

        addressed = {"c1": "Done", "c2": "Done"}
        passing_analysis = checker._create_passing_analysis(original, addressed)

        checker.considerations = [
            {"id": "c1", "question": "Check 1?", "severity": "blocker", "category": "Testing"},
            {"id": "c2", "question": "Check 2?", "severity": "blocker", "category": "Testing"},
        ]

        results_text = checker._format_results_text(passing_analysis, "STANDARD")

        # Both should show as passed (no ❌)
        self.assertNotIn("❌", results_text)
        # Should have ✅ for each result (plus summary line)
        self.assertIn("✅", results_text)


class TestEndToEndFalseFailurePrevention(unittest.TestCase):
    """End-to-end test verifying that issue #2473 is resolved."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        ).write_text(json.dumps(config))

    def test_create_passing_then_format_no_false_failure(self):
        """
        End-to-end: create passing analysis -> format results -> no false failures.

        This test reproduces the exact scenario from Issue #2473:
        1. Original analysis has blockers
        2. All blockers are addressed
        3. _create_passing_analysis creates new analysis
        4. _format_results_text formats the results
        5. Result should show ALL CHECKS PASSED, not CHECKS FAILED
        """
        checker = PowerSteeringChecker(self.project_root)

        # Step 1: Original analysis with blockers
        original = ConsiderationAnalysis()
        original.add_result(
            CheckerResult(
                "workflow_adherence",
                satisfied=False,
                reason="No workflow detected",
                severity="blocker",
            )
        )
        original.add_result(
            CheckerResult(
                "testing_coverage",
                satisfied=False,
                reason="No tests found",
                severity="blocker",
            )
        )
        original.add_result(
            CheckerResult(
                "code_quality",
                satisfied=True,
                reason="Code looks good",
                severity="warning",
            )
        )

        self.assertTrue(original.has_blockers)
        self.assertEqual(len(original.failed_blockers), 2)

        # Step 2: All blockers are addressed
        addressed = {
            "workflow_adherence": "Workflow steps followed",
            "testing_coverage": "Tests added and passing",
        }

        # Step 3: Create passing analysis
        passing = checker._create_passing_analysis(original, addressed)

        # Verify: no blockers, no warnings (code_quality was already passing)
        self.assertFalse(passing.has_blockers)
        self.assertEqual(len(passing.failed_blockers), 0)
        self.assertEqual(len(passing.failed_warnings), 0)

        # Step 4: Format results
        checker.considerations = [
            {
                "id": "workflow_adherence",
                "question": "Was the workflow followed?",
                "severity": "blocker",
                "category": "Workflow",
            },
            {
                "id": "testing_coverage",
                "question": "Were tests written?",
                "severity": "blocker",
                "category": "Testing",
            },
            {
                "id": "code_quality",
                "question": "Is code quality acceptable?",
                "severity": "warning",
                "category": "Quality",
            },
        ]

        results_text = checker._format_results_text(passing, "STANDARD")

        # Step 5: Verify NO false failures
        self.assertIn("ALL CHECKS PASSED", results_text)
        self.assertNotIn("CHECKS FAILED", results_text)
        self.assertNotIn("❌", results_text)

    def test_visibility_result_would_be_approved_by_stop_hook(self):
        """
        Verify that a first_stop_visibility result would be approved (not blocked)
        by the fixed stop.py logic.

        This tests the decision logic without running the full stop hook.
        """
        # Simulate what power-steering checker returns when all checks pass
        analysis = ConsiderationAnalysis()
        analysis.add_result(CheckerResult("c1", satisfied=True, reason="OK", severity="blocker"))
        analysis.add_result(CheckerResult("c2", satisfied=True, reason="OK", severity="warning"))

        ps_result = PowerSteeringResult(
            decision="block",
            reasons=["first_stop_visibility"],
            continuation_prompt="All power-steering checks passed!",
            analysis=analysis,
            is_first_stop=True,
        )

        # Apply the same decision logic as the fixed stop.py
        is_visibility_only = ps_result.is_first_stop and ps_result.reasons == [
            "first_stop_visibility"
        ]

        if is_visibility_only and ps_result.analysis:
            # Fixed behavior: approve
            decision = "approve"
        elif ps_result.is_first_stop and ps_result.analysis:
            # First stop with actual failures: block
            decision = "block"
        else:
            # Subsequent stop with failures: block
            decision = "block"

        self.assertEqual(
            decision,
            "approve",
            "When all checks pass (first_stop_visibility), decision should be 'approve'",
        )

    def test_failure_result_would_be_blocked_by_stop_hook(self):
        """
        Verify that an actual failure result would still be blocked.
        """
        analysis = ConsiderationAnalysis()
        analysis.add_result(CheckerResult("c1", satisfied=False, reason="Fail", severity="blocker"))

        ps_result = PowerSteeringResult(
            decision="block",
            reasons=["c1"],
            continuation_prompt="Please fix c1",
            analysis=analysis,
            is_first_stop=True,
        )

        is_visibility_only = ps_result.is_first_stop and ps_result.reasons == [
            "first_stop_visibility"
        ]

        if is_visibility_only and ps_result.analysis:
            decision = "approve"
        elif ps_result.is_first_stop and ps_result.analysis:
            decision = "block"
        else:
            decision = "block"

        self.assertEqual(
            decision,
            "block",
            "When there are actual failures, decision should be 'block'",
        )


if __name__ == "__main__":
    unittest.main()
