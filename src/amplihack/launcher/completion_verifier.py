"""CompletionVerifier - Verify completion claims against signals.

Cross-checks evaluation result text against CompletionSignals:
- Detects false completion claims
- Identifies discrepancies between claim and reality
- Provides verification reports

Philosophy:
- Trust but verify
- Concrete signals beat text claims
- Clear explanations for discrepancies
"""

from dataclasses import dataclass
from enum import Enum
from typing import List

from amplihack.launcher.completion_signals import CompletionSignals


class VerificationStatus(Enum):
    """Verification status enum."""

    VERIFIED = "verified"
    DISPUTED = "disputed"
    INCOMPLETE = "incomplete"
    AMBIGUOUS = "ambiguous"


@dataclass
class VerificationResult:
    """Result of verification."""

    status: VerificationStatus
    verified: bool
    explanation: str
    discrepancies: List[str]


class CompletionVerifier:
    """Verify completion claims against concrete signals."""

    def __init__(self, completion_threshold: float = 0.8):
        """Initialize verifier.

        Args:
            completion_threshold: Score threshold for completion
        """
        self.completion_threshold = completion_threshold

    def verify(
        self, evaluation_result: str, signals: CompletionSignals
    ) -> VerificationResult:
        """Verify evaluation result against signals.

        Args:
            evaluation_result: Evaluation text from LLM
            signals: CompletionSignals detected from WorkSummary

        Returns:
            VerificationResult with status and discrepancies
        """
        # Parse completion claim from evaluation
        claimed_complete = self._parse_completion_claim(evaluation_result)

        # Check if signals support the claim
        signals_complete = signals.completion_score >= self.completion_threshold

        # Detect discrepancies
        discrepancies = self._detect_discrepancies(
            evaluation_result, signals, claimed_complete
        )

        # Determine verification status
        if claimed_complete and signals_complete and not discrepancies:
            # Claim is verified
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                verified=True,
                explanation="Work is complete - evaluation verified by concrete signals",
                discrepancies=[],
            )
        elif claimed_complete and not signals_complete:
            # False completion claim - but check if evaluation acknowledges CI pending
            ci_pending = any("CI not passing" in d for d in discrepancies)
            score_close = signals.completion_score >= 0.7  # Within 10% of threshold
            eval_acknowledges_ci = "waiting" in evaluation_result.lower() or "pending" in evaluation_result.lower()

            if ci_pending and score_close and signals.pr_created and signals.all_steps_complete and eval_acknowledges_ci:
                # Work is essentially complete, evaluation acknowledges CI is pending
                return VerificationResult(
                    status=VerificationStatus.INCOMPLETE,
                    verified=False,
                    explanation="Work mostly complete but CI checks still running",
                    discrepancies=discrepancies,
                )
            else:
                # False completion claim
                explanation_parts = [
                    f"Evaluation claims complete but score is {signals.completion_score:.1%} (threshold {self.completion_threshold:.1%})"
                ]
                if discrepancies:
                    explanation_parts.append(f"Issues: {', '.join(discrepancies[:2])}")
                explanation = ". ".join(explanation_parts)

                return VerificationResult(
                    status=VerificationStatus.DISPUTED,
                    verified=False,
                    explanation=explanation,
                    discrepancies=discrepancies,
                )
        elif not claimed_complete and not signals_complete:
            # Both agree incomplete - but check for discrepancies in details
            if discrepancies:
                # Incomplete but with wrong details
                return VerificationResult(
                    status=VerificationStatus.DISPUTED,
                    verified=False,
                    explanation=f"Evaluation and signals both show incomplete, but details conflict: {', '.join(discrepancies[:2])}",
                    discrepancies=discrepancies,
                )
            else:
                # Accurate incomplete claim
                return VerificationResult(
                    status=VerificationStatus.VERIFIED,
                    verified=True,
                    explanation="Evaluation correctly identifies work as incomplete",
                    discrepancies=[],
                )
        elif not claimed_complete and signals_complete:
            # Overly conservative claim
            return VerificationResult(
                status=VerificationStatus.DISPUTED,
                verified=False,
                explanation=f"Evaluation claims incomplete but score is {signals.completion_score:.1%}",
                discrepancies=discrepancies,
            )
        else:
            # Ambiguous case
            return VerificationResult(
                status=VerificationStatus.AMBIGUOUS,
                verified=False,
                explanation="Cannot determine verification status",
                discrepancies=discrepancies,
            )

    def _parse_completion_claim(self, evaluation_result: str) -> bool:
        """Parse completion claim from evaluation text.

        Args:
            evaluation_result: Evaluation text

        Returns:
            True if claims complete, False if claims incomplete
        """
        if not evaluation_result:
            return False

        text_lower = evaluation_result.lower()

        # Explicit markers
        if "evaluation: complete" in text_lower:
            return True
        if "evaluation: incomplete" in text_lower:
            return False

        # Implicit completion language
        completion_phrases = [
            "finished",
            "done",
            "ready to merge",
            "all tasks completed",
            "work is complete",
            "completed successfully",
        ]

        incomplete_phrases = [
            "still working",
            "in progress",
            "pending",
            "need to",
            "not done",
            "incomplete",
        ]

        # Check for completion phrases
        for phrase in completion_phrases:
            if phrase in text_lower:
                return True

        # Check for incomplete phrases
        for phrase in incomplete_phrases:
            if phrase in text_lower:
                return False

        # Default to incomplete if ambiguous
        return False

    def _detect_discrepancies(
        self, evaluation_result: str, signals: CompletionSignals, claimed_complete: bool
    ) -> List[str]:
        """Detect discrepancies between claim and signals.

        Args:
            evaluation_result: Evaluation text
            signals: CompletionSignals
            claimed_complete: Whether evaluation claims complete

        Returns:
            List of discrepancy descriptions
        """
        discrepancies = []
        text_lower = evaluation_result.lower()

        # Check PR claim vs reality
        if "pr" in text_lower or "pull request" in text_lower:
            pr_mentioned = True
            # Check if PR number mentioned
            if signals.pr_number and str(signals.pr_number) in evaluation_result:
                pr_mentioned = True
        else:
            pr_mentioned = False

        if pr_mentioned and not signals.pr_created:
            discrepancies.append("Evaluation mentions PR but no PR exists")
        elif claimed_complete and not signals.pr_created:
            discrepancies.append("Claims complete but no PR created")

        # Check CI status claim vs reality
        ci_mentioned = "ci" in text_lower or "checks" in text_lower or "passing" in text_lower

        if ci_mentioned and "passing" in text_lower and not signals.ci_passing:
            discrepancies.append("Claims CI passing but CI status is not SUCCESS")
        elif ci_mentioned and "failing" in text_lower and signals.ci_passing:
            discrepancies.append("Claims CI failing but CI status is SUCCESS")
        elif claimed_complete and signals.pr_created and not signals.ci_passing:
            discrepancies.append("Claims complete but CI not passing")

        # Check tasks complete claim vs reality
        if ("all tasks" in text_lower or "tasks completed" in text_lower) and not signals.all_steps_complete:
            discrepancies.append("Claims all tasks complete but TodoWrite shows pending tasks")
        elif claimed_complete and not signals.all_steps_complete:
            discrepancies.append("Claims complete but not all TodoWrite tasks finished")

        # Check uncommitted changes
        if ("committed" in text_lower or "pushed" in text_lower) and not signals.no_uncommitted_changes:
            discrepancies.append("Claims changes committed but uncommitted changes exist")

        # Check mergeable status
        if ("ready to merge" in text_lower or "mergeable" in text_lower) and not signals.pr_mergeable:
            discrepancies.append("Claims ready to merge but PR has conflicts or is not mergeable")

        return discrepancies

    def format_report(self, result: VerificationResult) -> str:
        """Format verification result as human-readable report.

        Args:
            result: VerificationResult to format

        Returns:
            Report text
        """
        lines = [f"Verification: {result.status.value.upper()}"]

        if result.verified:
            lines.append(f"✓ {result.explanation}")
        else:
            lines.append(f"✗ {result.explanation}")

        if result.discrepancies:
            lines.append("\nDiscrepancies found:")
            for discrepancy in result.discrepancies:
                lines.append(f"  - {discrepancy}")

        return "\n".join(lines)
