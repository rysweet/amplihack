"""Tests for CompletionVerifier - TDD approach.

Tests the verification of completion claims against concrete signals:
- Cross-checking evaluation result text vs CompletionSignals
- Detecting false completion claims
- Providing verification reports
- Handling ambiguous cases
"""

from amplihack.launcher.completion_signals import CompletionSignals
from amplihack.launcher.completion_verifier import (
    CompletionVerifier,
    VerificationResult,
    VerificationStatus,
)
from amplihack.launcher.work_summary import (
    GitHubState,
    GitState,
    TodoState,
    WorkSummary,
)


class TestVerificationResultDataStructure:
    """Test VerificationResult dataclass structure."""

    def test_verification_result_has_required_fields(self):
        """VerificationResult must have status, verified, and explanation."""
        result = VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified=True,
            explanation="All signals indicate completion",
            discrepancies=[],
        )

        assert result.status == VerificationStatus.VERIFIED
        assert result.verified is True
        assert result.explanation is not None
        assert result.discrepancies == []

    def test_verification_status_enum_values(self):
        """VerificationStatus should have clear states."""
        assert hasattr(VerificationStatus, "VERIFIED")
        assert hasattr(VerificationStatus, "DISPUTED")
        assert hasattr(VerificationStatus, "INCOMPLETE")
        assert hasattr(VerificationStatus, "AMBIGUOUS")


class TestVerificationLogic:
    """Test core verification logic against signals."""

    def test_verify_true_completion_claim(self):
        """Should verify when evaluation says complete AND signals confirm."""
        evaluation_result = (
            "EVALUATION: COMPLETE\n\nAll tasks finished, PR #123 created and passing CI."
        )

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is True
        assert result.status == VerificationStatus.VERIFIED
        assert len(result.discrepancies) == 0

    def test_verify_false_completion_claim_no_pr(self):
        """Should dispute when evaluation claims complete but no PR exists."""
        evaluation_result = "EVALUATION: COMPLETE\n\nAll work is done, ready to merge."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=False,  # No PR created
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.5,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is False
        assert result.status == VerificationStatus.DISPUTED
        assert "PR" in result.explanation or "pull request" in result.explanation.lower()
        assert len(result.discrepancies) > 0

    def test_verify_false_completion_claim_ci_failing(self):
        """Should dispute when evaluation claims complete but CI is failing."""
        evaluation_result = "EVALUATION: COMPLETE\n\nPR #456 is ready to merge."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=False,  # CI failing
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.7,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is False
        assert result.status == VerificationStatus.DISPUTED
        assert "CI" in result.explanation or "failing" in result.explanation.lower()

    def test_verify_accurate_incomplete_claim(self):
        """Should verify when evaluation correctly says incomplete."""
        evaluation_result = "EVALUATION: INCOMPLETE\n\nStill working on tests, 2 tasks pending."

        signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=False,
            completion_score=0.3,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        # Should verify the INCOMPLETE claim is accurate
        assert result.verified is True
        assert result.status == VerificationStatus.VERIFIED
        assert "incomplete" in result.explanation.lower() or "correct" in result.explanation.lower()

    def test_verify_false_incomplete_claim(self):
        """Should dispute when evaluation says incomplete but signals show complete."""
        evaluation_result = "EVALUATION: INCOMPLETE\n\nStill need to create PR."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is False
        assert result.status == VerificationStatus.DISPUTED


class TestDiscrepancyDetection:
    """Test detection of specific discrepancies."""

    def test_detect_pr_claim_discrepancy(self):
        """Should detect when evaluation claims PR exists but signals say no."""
        evaluation_result = "PR #789 created and ready for review."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.5,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        # Should identify PR discrepancy
        assert len(result.discrepancies) > 0
        pr_discrepancy = [
            d for d in result.discrepancies if "PR" in d or "pull request" in d.lower()
        ]
        assert len(pr_discrepancy) > 0

    def test_detect_ci_status_discrepancy(self):
        """Should detect when evaluation claims CI passing but signals say failing."""
        evaluation_result = "All CI checks are passing, ready to merge."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=False,  # Actually failing
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.7,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert len(result.discrepancies) > 0
        ci_discrepancy = [d for d in result.discrepancies if "CI" in d or "check" in d.lower()]
        assert len(ci_discrepancy) > 0

    def test_detect_tasks_complete_discrepancy(self):
        """Should detect when evaluation claims all tasks done but signals show pending."""
        evaluation_result = "All tasks completed successfully."

        signals = CompletionSignals(
            all_steps_complete=False,  # Actually incomplete
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.8,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert len(result.discrepancies) > 0
        task_discrepancy = [
            d for d in result.discrepancies if "task" in d.lower() or "step" in d.lower()
        ]
        assert len(task_discrepancy) > 0

    def test_detect_uncommitted_changes_discrepancy(self):
        """Should detect when evaluation claims clean state but uncommitted changes exist."""
        evaluation_result = "All changes committed and pushed."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=False,  # Has uncommitted changes
            completion_score=0.9,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert len(result.discrepancies) > 0
        uncommitted_discrepancy = [
            d for d in result.discrepancies if "uncommitted" in d.lower() or "changes" in d.lower()
        ]
        assert len(uncommitted_discrepancy) > 0


class TestEvaluationParsing:
    """Test parsing of evaluation result text."""

    def test_parse_explicit_complete_marker(self):
        """Should detect 'EVALUATION: COMPLETE' marker."""
        evaluation_result = "EVALUATION: COMPLETE\n\nWork is done."

        verifier = CompletionVerifier()
        is_claimed_complete = verifier._parse_completion_claim(evaluation_result)

        assert is_claimed_complete is True

    def test_parse_explicit_incomplete_marker(self):
        """Should detect 'EVALUATION: INCOMPLETE' marker."""
        evaluation_result = "EVALUATION: INCOMPLETE\n\nStill working on it."

        verifier = CompletionVerifier()
        is_claimed_complete = verifier._parse_completion_claim(evaluation_result)

        assert is_claimed_complete is False

    def test_parse_implicit_completion_language(self):
        """Should detect implicit completion language."""
        evaluation_result = "The task is finished. PR is ready to merge."

        verifier = CompletionVerifier()
        is_claimed_complete = verifier._parse_completion_claim(evaluation_result)

        assert is_claimed_complete is True

    def test_parse_implicit_incomplete_language(self):
        """Should detect implicit incomplete language."""
        evaluation_result = "Still working on the implementation. Need to add tests."

        verifier = CompletionVerifier()
        is_claimed_complete = verifier._parse_completion_claim(evaluation_result)

        assert is_claimed_complete is False

    def test_parse_ambiguous_language(self):
        """Should handle ambiguous evaluation text."""
        evaluation_result = "Some progress made. More work needed in some areas."

        verifier = CompletionVerifier()
        is_claimed_complete = verifier._parse_completion_claim(evaluation_result)

        # Should either detect as incomplete or mark as ambiguous
        # Implementation can choose conservative interpretation
        assert is_claimed_complete is not None


class TestThresholdBasedVerification:
    """Test verification using completion score threshold."""

    def test_verify_with_score_above_threshold(self):
        """Should verify completion when score >= 0.8 regardless of claim."""
        evaluation_result = "Work is nearly done."  # Ambiguous claim

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.9,  # Above threshold
        )

        verifier = CompletionVerifier(completion_threshold=0.8)
        result = verifier.verify(evaluation_result, signals)

        # Should consider complete based on score
        assert result.verified is True or result.status == VerificationStatus.VERIFIED

    def test_verify_with_score_below_threshold(self):
        """Should not verify completion when score < 0.8 even if claimed."""
        evaluation_result = "EVALUATION: COMPLETE\n\nAll done!"

        signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.3,  # Well below threshold
        )

        verifier = CompletionVerifier(completion_threshold=0.8)
        result = verifier.verify(evaluation_result, signals)

        # Should dispute based on low score
        assert result.verified is False
        assert result.status == VerificationStatus.DISPUTED


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_verify_with_empty_evaluation(self):
        """Should handle empty evaluation text."""
        evaluation_result = ""

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        # Should not crash, should have some status
        assert result.status in VerificationStatus.__members__.values()

    def test_verify_with_missing_github_info(self):
        """Should handle gracefully when GitHub info unavailable."""
        evaluation_result = "EVALUATION: COMPLETE\n\nAll tasks done, PR created."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=False,  # GitHub CLI unavailable
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.6,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        # Should mark as ambiguous or incomplete, not crash
        assert result.status in [
            VerificationStatus.AMBIGUOUS,
            VerificationStatus.INCOMPLETE,
            VerificationStatus.DISPUTED,
        ]

    def test_verify_with_ci_pending(self):
        """Should handle CI still running (PENDING status)."""
        evaluation_result = "EVALUATION: COMPLETE\n\nPR created, waiting for CI."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=False,  # Still pending
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.75,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        # Should mark as incomplete or ambiguous (CI not done)
        assert result.status in [
            VerificationStatus.INCOMPLETE,
            VerificationStatus.AMBIGUOUS,
        ]
        assert result.verified is False


class TestVerificationReports:
    """Test human-readable verification reports."""

    def test_report_verified_completion(self):
        """Should provide clear report for verified completion."""
        evaluation_result = "EVALUATION: COMPLETE\n\nAll work done."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)
        report = verifier.format_report(result)

        assert "verified" in report.lower() or "confirmed" in report.lower()
        assert "complete" in report.lower()

    def test_report_disputed_completion(self):
        """Should provide actionable report for disputed completion."""
        evaluation_result = "EVALUATION: COMPLETE\n\nReady to merge."

        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.5,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)
        report = verifier.format_report(result)

        # Should mention what's missing
        assert "dispute" in report.lower() or "mismatch" in report.lower()
        assert len(result.discrepancies) > 0
        # Report should include discrepancies
        for discrepancy in result.discrepancies:
            assert discrepancy in report

    def test_report_includes_score(self):
        """Should include completion score in report."""
        evaluation_result = "Some work done."

        signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.4,
        )

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)
        report = verifier.format_report(result)

        # Should mention score or percentage
        assert "0.4" in report or "40%" in report or "score" in report.lower()


class TestVerificationIntegrationWithWorkSummary:
    """Test verification using real WorkSummary scenarios."""

    def test_verify_realistic_complete_scenario(self):
        """End-to-end test: steps complete, PR created, CI passing."""
        evaluation_result = (
            "EVALUATION: COMPLETE\n\nAll 5 tasks completed. PR #200 created and CI passing."
        )

        # Create realistic complete scenario
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/issue-123",
                has_uncommitted_changes=False,
                commits_ahead=4,
            ),
            github_state=GitHubState(
                pr_number=200, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        # Generate signals from summary (would use CompletionSignalDetector)
        from amplihack.launcher.completion_signals import CompletionSignalDetector

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        # Verify
        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is True
        assert result.status == VerificationStatus.VERIFIED
        assert len(result.discrepancies) == 0

    def test_verify_realistic_incomplete_scenario(self):
        """End-to-end test: steps incomplete, no PR."""
        evaluation_result = (
            "EVALUATION: INCOMPLETE\n\n3 of 5 tasks done, still working on implementation."
        )

        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/issue-456",
                has_uncommitted_changes=True,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        from amplihack.launcher.completion_signals import CompletionSignalDetector

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is True  # Correctly identified as incomplete
        assert result.status == VerificationStatus.VERIFIED

    def test_verify_realistic_false_claim_scenario(self):
        """End-to-end test: claims complete but CI failing."""
        evaluation_result = "EVALUATION: COMPLETE\n\nAll work finished, PR ready."

        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/issue-789",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=300, pr_state="OPEN", ci_status="FAILURE", pr_mergeable=False
            ),
        )

        from amplihack.launcher.completion_signals import CompletionSignalDetector

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        verifier = CompletionVerifier()
        result = verifier.verify(evaluation_result, signals)

        assert result.verified is False
        assert result.status == VerificationStatus.DISPUTED
        assert any("CI" in d or "failing" in d.lower() for d in result.discrepancies)
