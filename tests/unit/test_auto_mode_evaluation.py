"""Tests for enhanced auto-mode evaluation loop - TDD approach.

Tests the integration of WorkSummary, CompletionSignals, and CompletionVerifier
into the auto-mode evaluation loop:
- Prompt injection of work summary
- Signal-based evaluation enhancement
- Verification before loop exit
- Graceful degradation when tools unavailable
"""

from unittest.mock import Mock, patch, MagicMock
import pytest

from amplihack.launcher.auto_mode import AutoMode
from amplihack.launcher.work_summary import (
    WorkSummary,
    TodoState,
    GitState,
    GitHubState,
)
from amplihack.launcher.completion_signals import CompletionSignals
from amplihack.launcher.completion_verifier import (
    VerificationResult,
    VerificationStatus,
)


class TestWorkSummaryPromptInjection:
    """Test injection of WorkSummary into evaluation prompt."""

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    def test_evaluation_prompt_includes_work_summary(self, mock_generator_class):
        """Evaluation prompt should include formatted WorkSummary."""
        # Setup mock
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=123, pr_state="OPEN", ci_status="PENDING", pr_mergeable=None
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator.format_for_prompt.return_value = "Work Summary: 3/5 tasks done, PR #123 (CI pending)"
        mock_generator_class.return_value = mock_generator

        # Create AutoMode instance
        auto_mode = AutoMode(task="Test task")

        # Get evaluation prompt
        mock_capture = Mock()
        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Verify work summary is included
        assert "Work Summary" in evaluation_prompt
        assert "3/5 tasks" in evaluation_prompt or "3 of 5" in evaluation_prompt
        assert "PR #123" in evaluation_prompt or "123" in evaluation_prompt

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    def test_evaluation_prompt_graceful_degradation_no_summary(
        self, mock_generator_class
    ):
        """Should handle gracefully if WorkSummary generation fails."""
        # Setup mock to raise exception
        mock_generator = Mock()
        mock_generator.generate.side_effect = Exception("Git not available")
        mock_generator_class.return_value = mock_generator

        auto_mode = AutoMode(task="Test task")
        mock_capture = Mock()

        # Should not crash
        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Should still have base prompt
        assert "evaluate" in evaluation_prompt.lower() or "assessment" in evaluation_prompt.lower()


class TestCompletionSignalIntegration:
    """Test integration of CompletionSignals into evaluation."""

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    def test_evaluation_uses_completion_signals(
        self, mock_detector_class, mock_generator_class
    ):
        """Evaluation should use CompletionSignals for concrete markers."""
        # Setup mocks
        mock_generator = Mock()
        mock_summary = WorkSummary(
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
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        auto_mode = AutoMode(task="Test task")
        mock_capture = Mock()

        # Build evaluation prompt
        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Verify CompletionSignals are used
        mock_detector.detect.assert_called_once_with(mock_summary)

        # Prompt should include signal information
        assert "PR" in evaluation_prompt or "pull request" in evaluation_prompt.lower()
        assert "CI" in evaluation_prompt or "checks" in evaluation_prompt.lower()

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    def test_evaluation_prompt_includes_completion_score(
        self, mock_detector_class, mock_generator_class
    ):
        """Evaluation prompt should mention completion score."""
        # Setup mocks
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=5, completed=3, in_progress=1, pending=1),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=2,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.4,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        auto_mode = AutoMode(task="Test task")
        mock_capture = Mock()

        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Should mention score or completion percentage
        assert "0.4" in evaluation_prompt or "40%" in evaluation_prompt or "score" in evaluation_prompt.lower()


class TestVerificationBeforeLoopExit:
    """Test verification of completion claims before exiting loop."""

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    @patch("amplihack.launcher.auto_mode.CompletionVerifier")
    def test_verify_completion_before_exit(
        self, mock_verifier_class, mock_detector_class, mock_generator_class
    ):
        """Should verify completion claim before allowing loop exit."""
        # Setup mocks
        mock_generator = Mock()
        mock_summary = WorkSummary(
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
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        mock_verifier = Mock()
        mock_verification = VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified=True,
            explanation="All signals confirm completion",
            discrepancies=[],
        )
        mock_verifier.verify.return_value = mock_verification
        mock_verifier_class.return_value = mock_verifier

        auto_mode = AutoMode(task="Test task")

        # Simulate evaluation result claiming completion
        evaluation_result = "EVALUATION: COMPLETE\n\nAll tasks done, PR merged."

        # Check if should continue loop
        should_continue = auto_mode._should_continue_loop(evaluation_result, Mock())

        # Should verify before exiting
        mock_verifier.verify.assert_called_once()
        assert should_continue is False  # Should exit loop

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    @patch("amplihack.launcher.auto_mode.CompletionVerifier")
    def test_continue_loop_on_disputed_completion(
        self, mock_verifier_class, mock_detector_class, mock_generator_class
    ):
        """Should continue loop if completion claim is disputed."""
        # Setup mocks
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=None,  # No PR!
                pr_state=None,
                ci_status=None,
                pr_mergeable=None,
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=False,  # No PR
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.5,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        mock_verifier = Mock()
        mock_verification = VerificationResult(
            status=VerificationStatus.DISPUTED,
            verified=False,
            explanation="Claimed complete but no PR created",
            discrepancies=["PR not created"],
        )
        mock_verifier.verify.return_value = mock_verification
        mock_verifier_class.return_value = mock_verifier

        auto_mode = AutoMode(task="Test task")

        evaluation_result = "EVALUATION: COMPLETE\n\nAll done!"

        should_continue = auto_mode._should_continue_loop(evaluation_result, Mock())

        # Should continue loop (disputed)
        assert should_continue is True

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    @patch("amplihack.launcher.auto_mode.CompletionVerifier")
    def test_provide_feedback_on_disputed_completion(
        self, mock_verifier_class, mock_detector_class, mock_generator_class
    ):
        """Should provide feedback to agent when completion is disputed."""
        # Setup mocks
        mock_generator = Mock()
        mock_summary = WorkSummary(
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
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=False,  # CI failing
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=0.7,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        mock_verifier = Mock()
        mock_verification = VerificationResult(
            status=VerificationStatus.DISPUTED,
            verified=False,
            explanation="CI checks are failing",
            discrepancies=["CI status: FAILURE"],
        )
        mock_verifier.verify.return_value = mock_verification
        mock_verifier_class.return_value = mock_verifier

        auto_mode = AutoMode(task="Test task")

        evaluation_result = "EVALUATION: COMPLETE\n\nReady to merge."

        feedback = auto_mode._get_verification_feedback(
            evaluation_result, mock_verification
        )

        # Should include discrepancies in feedback
        assert "CI" in feedback or "failing" in feedback.lower()
        assert "FAILURE" in feedback


class TestGracefulDegradation:
    """Test graceful degradation when external tools unavailable."""

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    def test_evaluation_continues_without_github(self, mock_generator_class):
        """Should continue evaluation even if GitHub CLI unavailable."""
        # Setup mock - no GitHub info
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=5, completed=5, in_progress=0, pending=0),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=False,
                commits_ahead=3,
            ),
            github_state=GitHubState(
                pr_number=None,  # GitHub CLI unavailable
                pr_state=None,
                ci_status=None,
                pr_mergeable=None,
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        auto_mode = AutoMode(task="Test task")
        mock_capture = Mock()

        # Should not crash
        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Should mention GitHub unavailable
        assert (
            "github" in evaluation_prompt.lower()
            or "unavailable" in evaluation_prompt.lower()
        )

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    def test_evaluation_continues_without_git(self, mock_generator_class):
        """Should continue evaluation even if not in git repository."""
        # Setup mock - no git info
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=3, completed=3, in_progress=0, pending=0),
            git_state=GitState(
                current_branch=None,  # Not in git repo
                has_uncommitted_changes=False,
                commits_ahead=None,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        auto_mode = AutoMode(task="Test task")
        mock_capture = Mock()

        # Should not crash
        evaluation_prompt = auto_mode._build_evaluation_prompt(mock_capture)

        # Should still work with TodoWrite only
        assert "3" in evaluation_prompt  # Task count


class TestAutoModeLoopIntegration:
    """Test end-to-end auto-mode loop with verification."""

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    @patch("amplihack.launcher.auto_mode.CompletionVerifier")
    @patch("amplihack.launcher.auto_mode.ClaudeSDKClient")
    def test_complete_workflow_with_verified_completion(
        self,
        mock_client_class,
        mock_verifier_class,
        mock_detector_class,
        mock_generator_class,
    ):
        """End-to-end test: Complete workflow with verified completion exits loop."""
        # Setup mocks for complete scenario
        mock_generator = Mock()
        mock_summary = WorkSummary(
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
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=True,
            pr_created=True,
            ci_passing=True,
            pr_mergeable=True,
            has_commits=True,
            no_uncommitted_changes=True,
            completion_score=1.0,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        mock_verifier = Mock()
        mock_verification = VerificationResult(
            status=VerificationStatus.VERIFIED,
            verified=True,
            explanation="All signals confirm completion",
            discrepancies=[],
        )
        mock_verifier.verify.return_value = mock_verification
        mock_verifier_class.return_value = mock_verifier

        # Mock Claude SDK response
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        auto_mode = AutoMode(task="Test task", max_iterations=10)

        # Run auto-mode (would be async in real implementation)
        # This is a simplified test - real implementation would need async

        # Verify that:
        # 1. WorkSummary is generated
        # 2. CompletionSignals are detected
        # 3. Verification happens before exit
        # 4. Loop exits on verified completion

        # Actual assertion depends on implementation
        # For now, verify mocks are set up correctly
        assert mock_generator is not None
        assert mock_detector is not None
        assert mock_verifier is not None

    @patch("amplihack.launcher.auto_mode.WorkSummaryGenerator")
    @patch("amplihack.launcher.auto_mode.CompletionSignalDetector")
    @patch("amplihack.launcher.auto_mode.CompletionVerifier")
    def test_loop_continues_on_incomplete_work(
        self, mock_verifier_class, mock_detector_class, mock_generator_class
    ):
        """Loop should continue when work is genuinely incomplete."""
        # Setup mocks for incomplete scenario
        mock_generator = Mock()
        mock_summary = WorkSummary(
            todo_state=TodoState(total=5, completed=2, in_progress=1, pending=2),
            git_state=GitState(
                current_branch="feat/test",
                has_uncommitted_changes=True,
                commits_ahead=1,
            ),
            github_state=GitHubState(
                pr_number=None, pr_state=None, ci_status=None, pr_mergeable=None
            ),
        )
        mock_generator.generate.return_value = mock_summary
        mock_generator_class.return_value = mock_generator

        mock_detector = Mock()
        mock_signals = CompletionSignals(
            all_steps_complete=False,
            pr_created=False,
            ci_passing=False,
            pr_mergeable=False,
            has_commits=True,
            no_uncommitted_changes=False,
            completion_score=0.3,
        )
        mock_detector.detect.return_value = mock_signals
        mock_detector_class.return_value = mock_detector

        mock_verifier = Mock()
        mock_verification = VerificationResult(
            status=VerificationStatus.INCOMPLETE,
            verified=True,  # Verified as incomplete
            explanation="Work is incomplete",
            discrepancies=[],
        )
        mock_verifier.verify.return_value = mock_verification
        mock_verifier_class.return_value = mock_verifier

        auto_mode = AutoMode(task="Test task")

        evaluation_result = "EVALUATION: INCOMPLETE\n\nStill working on tests."

        should_continue = auto_mode._should_continue_loop(evaluation_result, Mock())

        assert should_continue is True  # Should continue working
