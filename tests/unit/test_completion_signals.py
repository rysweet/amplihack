"""Tests for CompletionSignalDetector - TDD approach.

Tests the detection and scoring of completion signals from WorkSummary:
- Concrete signal detection (PR created, CI passing, etc.)
- Signal scoring (0.0 to 1.0)
- Threshold-based completion determination
- Edge case handling
"""

import pytest

from amplihack.launcher.completion_signals import (
    CompletionSignals,
    CompletionSignalDetector,
    SignalScore,
)
from amplihack.launcher.work_summary import (
    WorkSummary,
    TodoState,
    GitState,
    GitHubState,
)


class TestCompletionSignalsDataStructure:
    """Test CompletionSignals dataclass structure."""

    def test_completion_signals_has_required_fields(self):
        """CompletionSignals must have all detection fields."""
        signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )

        assert signals.all_steps_complete is True
        assert signals.pr_created is True
        assert signals.ci_passing is True
        assert signals.pr_mergeable is True
        assert signals.completion_score == 1.0

    def test_completion_score_range_validation(self):
        """Completion score must be between 0.0 and 1.0."""
        # Valid scores
        signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=False,
            no_uncommitted_changes=True,
            completion_score=0.5,
        )
        assert 0.0 <= signals.completion_score <= 1.0

        # Invalid scores should raise
        with pytest.raises(ValueError, match="Completion score must be 0.0-1.0"):
            CompletionSignals(
                all_steps_complete=False,
                pr_created=False,
                ci_passing=False,
                pr_mergeable=False,
                has_commits=False,
                no_uncommitted_changes=False,
                completion_score=1.5,
            )

        with pytest.raises(ValueError, match="Completion score must be 0.0-1.0"):
            CompletionSignals(
                all_steps_complete=False,
                pr_created=False,
                ci_passing=False,
                pr_mergeable=False,
                has_commits=False,
                no_uncommitted_changes=False,
                completion_score=-0.1,
            )


class TestSignalDetection:
    """Test individual signal detection from WorkSummary."""

    def test_detect_all_steps_complete(self):
        """Should detect when all TodoWrite tasks are completed."""
        # All complete
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="main", has_uncommitted_changes=False, commits_ahead=0
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_all_steps_complete(summary) is True

        # Some pending
        summary_incomplete = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="main", has_uncommitted_changes=False, commits_ahead=0
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        assert detector._detect_all_steps_complete(summary_incomplete) is False

    def test_detect_pr_created(self):
        """Should detect when PR exists on GitHub."""
        # PR exists
        summary = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_pr_created(summary) is True

        # No PR
        summary_no_pr = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        assert detector._detect_pr_created(summary_no_pr) is False

    def test_detect_ci_passing(self):
        """Should detect when CI checks are passing."""
        # CI passing
        summary_passing = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_ci_passing(summary_passing) is True

        # CI failing
        summary_failing = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="FAILURE", pr_mergeable=False
            ),
        )

        assert detector._detect_ci_passing(summary_failing) is False

        # CI pending
        summary_pending = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="PENDING", pr_mergeable=None
            ),
        )

        assert detector._detect_ci_passing(summary_pending) is False

    def test_detect_pr_mergeable(self):
        """Should detect when PR is in mergeable state."""
        # Mergeable
        summary = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_pr_mergeable(summary) is True

        # Not mergeable
        summary_conflicts = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=False
            ),
        )

        assert detector._detect_pr_mergeable(summary_conflicts) is False

    def test_detect_has_commits(self):
        """Should detect when branch has commits ahead of main."""
        # Has commits
        summary = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_has_commits(summary) is True

        # No commits
        summary_no_commits = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="main", has_uncommitted_changes=False, commits_ahead=0
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        assert detector._detect_has_commits(summary_no_commits) is False

    def test_detect_no_uncommitted_changes(self):
        """Should detect when working tree is clean."""
        # Clean tree
        summary = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        assert detector._detect_no_uncommitted_changes(summary) is True

        # Dirty tree
        summary_dirty = WorkSummary(
            todo_state=TodoState(total=0, completed=0, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=True,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        assert detector._detect_no_uncommitted_changes(summary_dirty) is False


class TestSignalScoring:
    """Test completion score calculation from signals."""

    def test_score_perfect_completion(self):
        """Perfect completion should score 1.0."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        assert signals.completion_score == 1.0

    def test_score_no_completion(self):
        """No progress should score 0.0."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=0, in_progress=1, pending=4),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=True,
                commits_ahead=0,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        assert signals.completion_score == 0.0

    def test_score_partial_completion(self):
        """Partial completion should score between 0.0 and 1.0."""
        # Steps complete, PR created, but CI failing
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="FAILURE", pr_mergeable=False
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        # Should be high (steps + PR) but not perfect (CI failing)
        assert 0.5 < signals.completion_score < 1.0

    def test_score_weights_critical_signals_higher(self):
        """Critical signals (PR mergeable, CI passing) should weight higher."""
        # Scenario 1: All steps complete, but no PR
        summary_no_pr = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        # Scenario 2: PR created and passing, but 1 step pending
        summary_pr_passing = WorkSummary(
            todo_state=TodoState(total=5, completed=4, in_progress=0, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        score1 = detector.detect(summary_no_pr).completion_score
        score2 = detector.detect(summary_pr_passing).completion_score

        # PR passing should score higher than just steps complete
        assert score2 > score1


class TestCompletionThreshold:
    """Test threshold-based completion determination."""

    def test_default_threshold_is_0_8(self):
        """Default completion threshold should be 0.8."""
        detector = CompletionSignalDetector()
        assert detector.completion_threshold == 0.8

    def test_is_complete_above_threshold(self):
        """Score >= 0.8 should be considered complete."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        assert detector.is_complete(signals) is True
        assert signals.completion_score >= 0.8

    def test_is_complete_below_threshold(self):
        """Score < 0.8 should not be considered complete."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=2, in_progress=1, pending=2),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=1,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        assert detector.is_complete(signals) is False
        assert signals.completion_score < 0.8

    def test_custom_threshold(self):
        """Should support custom completion threshold."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=4, in_progress=0, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status=None, pr_mergeable=None
            ),
        )

        # Lower threshold (0.5)
        detector_low = CompletionSignalDetector(completion_threshold=0.5)
        signals = detector_low.detect(summary)

        # Higher threshold (0.95)
        detector_high = CompletionSignalDetector(completion_threshold=0.95)

        # Same signals, different thresholds
        assert detector_low.is_complete(signals) is True  # Score > 0.5
        assert detector_high.is_complete(signals) is False  # Score < 0.95


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_detect_with_no_git_info(self):
        """Should handle missing git information gracefully."""
        summary = WorkSummary(
            todo_state=TodoState(total=3, completed=3, in_progress=0, pending=0),
            git_state=GitState(
                current_branch=None, has_uncommitted_changes=False, commits_ahead=None
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        # Should not crash, should have some score
        assert 0.0 <= signals.completion_score <= 1.0

    def test_detect_with_no_github_info(self):
        """Should handle missing GitHub information (gh CLI unavailable)."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        # Should still detect steps complete and has commits
        assert signals.all_steps_complete is True
        assert signals.has_commits is True
        assert signals.pr_created is False
        # Score should be > 0 but < 1.0 (missing PR signals)
        assert 0.0 < signals.completion_score < 1.0

    def test_detect_with_ci_pending(self):
        """Should handle CI still running (PENDING status)."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="PENDING", pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        assert signals.pr_created is True
        assert signals.ci_passing is False  # Pending = not passing yet
        assert signals.pr_mergeable is False  # Can't merge until CI done
        # Score should be high but not complete
        assert 0.6 < signals.completion_score < 0.8

    def test_detect_with_multiple_prs(self):
        """Should handle case where multiple PRs exist for same branch."""
        # Note: WorkSummary should ideally use latest/most recent PR
        summary = WorkSummary(
            todo_state=TodoState(total=3, completed=3, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=125,  # Latest PR
                pr_state="OPEN",
                ci_status="SUCCESS",
                pr_mergeable=True,
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)

        # Should use the provided PR (WorkSummary handles selection)
        assert signals.pr_created is True
        assert signals.pr_number == 125


class TestSignalExplanations:
    """Test human-readable explanations of signals."""

    def test_explain_signals_complete(self):
        """Should provide explanation when complete."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="SUCCESS", pr_mergeable=True
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)
        explanation = detector.explain(signals)

        assert "complete" in explanation.lower()
        assert "PR #123" in explanation or "123" in explanation
        assert "passing" in explanation.lower() or "success" in explanation.lower()

    def test_explain_signals_incomplete(self):
        """Should explain what's missing when incomplete."""
        summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=True,
                commits_ahead=1,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )

        detector = CompletionSignalDetector()
        signals = detector.detect(summary)
        explanation = detector.explain(signals)

        # Should mention what's missing
        assert "pending" in explanation.lower() or "incomplete" in explanation.lower()
        assert "PR" in explanation or "pull request" in explanation.lower()
        assert "uncommitted" in explanation.lower() or "changes" in explanation.lower()
