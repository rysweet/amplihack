"""CompletionSignalDetector - Detect concrete completion signals.

Detects completion signals from WorkSummary:
- All TodoWrite steps complete
- PR created on GitHub
- CI checks passing
- PR mergeable
- Has commits
- No uncommitted changes

Philosophy:
- Concrete markers only (no LLM interpretation)
- Scoring: 0.0 (nothing done) to 1.0 (perfect completion)
- Threshold-based completion (default 0.8)
"""

from dataclasses import dataclass

from amplihack.launcher.work_summary import WorkSummary


@dataclass
class SignalScore:
    """Individual signal weight for scoring."""

    name: str
    weight: float
    detected: bool


@dataclass
class CompletionSignals:
    """Concrete completion signals detected from WorkSummary."""

    all_steps_complete: bool
    pr_created: bool
    ci_passing: bool
    pr_mergeable: bool
    has_commits: bool
    no_uncommitted_changes: bool
    completion_score: float
    pr_number: int | None = None

    def __post_init__(self):
        """Validate completion score range."""
        if not 0.0 <= self.completion_score <= 1.0:
            raise ValueError(f"Completion score must be 0.0-1.0, got {self.completion_score}")


class CompletionSignalDetector:
    """Detect completion signals from WorkSummary."""

    # Signal weights (must sum to 1.0)
    WEIGHTS = {
        "all_steps_complete": 0.30,  # TodoWrite complete
        "pr_created": 0.25,  # PR exists
        "ci_passing": 0.20,  # CI checks pass
        "pr_mergeable": 0.15,  # No conflicts
        "has_commits": 0.05,  # Work committed
        "no_uncommitted_changes": 0.05,  # Clean tree
    }

    def __init__(self, completion_threshold: float = 0.8):
        """Initialize detector.

        Args:
            completion_threshold: Score >= this value indicates completion (default 0.8)
        """
        self.completion_threshold = completion_threshold

    def detect(self, summary: WorkSummary) -> CompletionSignals:
        """Detect all completion signals from WorkSummary.

        Args:
            summary: WorkSummary to analyze

        Returns:
            CompletionSignals with detection results and score
        """
        # Detect individual signals
        all_steps_complete = self._detect_all_steps_complete(summary)
        pr_created = self._detect_pr_created(summary)
        ci_passing = self._detect_ci_passing(summary)
        pr_mergeable = self._detect_pr_mergeable(summary)
        has_commits = self._detect_has_commits(summary)
        no_uncommitted_changes = self._detect_no_uncommitted_changes(summary)

        # Calculate weighted score with partial credit for task completion
        score = 0.0

        # Task completion - give partial credit based on completion ratio
        # (Never give full credit separately to avoid double-counting)
        todo = summary.todo_state
        if todo.total > 0:
            completion_ratio = todo.completed / todo.total
            score += self.WEIGHTS["all_steps_complete"] * completion_ratio

        # Add other signal weights (not partial credit, just binary)
        if pr_created:
            score += self.WEIGHTS["pr_created"]
        if ci_passing:
            score += self.WEIGHTS["ci_passing"]
        if pr_mergeable:
            score += self.WEIGHTS["pr_mergeable"]
        if has_commits:
            score += self.WEIGHTS["has_commits"]
        if no_uncommitted_changes:
            score += self.WEIGHTS["no_uncommitted_changes"]

        return CompletionSignals(
            all_steps_complete=all_steps_complete,
            pr_created=pr_created,
            ci_passing=ci_passing,
            pr_mergeable=pr_mergeable,
            has_commits=has_commits,
            no_uncommitted_changes=no_uncommitted_changes,
            completion_score=score,
            pr_number=summary.github_state.pr_number,
        )

    def _detect_all_steps_complete(self, summary: WorkSummary) -> bool:
        """Detect if all TodoWrite tasks are completed.

        Args:
            summary: WorkSummary to check

        Returns:
            True if all tasks completed
        """
        todo = summary.todo_state
        if todo.total == 0:
            return False
        return todo.completed == todo.total

    def _detect_pr_created(self, summary: WorkSummary) -> bool:
        """Detect if PR exists on GitHub.

        Args:
            summary: WorkSummary to check

        Returns:
            True if PR exists
        """
        return summary.github_state.pr_number is not None

    def _detect_ci_passing(self, summary: WorkSummary) -> bool:
        """Detect if CI checks are passing.

        Args:
            summary: WorkSummary to check

        Returns:
            True if CI status is SUCCESS
        """
        return summary.github_state.ci_status == "SUCCESS"

    def _detect_pr_mergeable(self, summary: WorkSummary) -> bool:
        """Detect if PR is in mergeable state.

        Args:
            summary: WorkSummary to check

        Returns:
            True if PR is mergeable
        """
        return summary.github_state.pr_mergeable is True

    def _detect_has_commits(self, summary: WorkSummary) -> bool:
        """Detect if branch has commits ahead of main.

        Args:
            summary: WorkSummary to check

        Returns:
            True if commits ahead > 0
        """
        commits_ahead = summary.git_state.commits_ahead
        return commits_ahead is not None and commits_ahead > 0

    def _detect_no_uncommitted_changes(self, summary: WorkSummary) -> bool:
        """Detect if working tree is clean.

        Args:
            summary: WorkSummary to check

        Returns:
            True if no uncommitted changes
        """
        return not summary.git_state.has_uncommitted_changes

    def is_complete(self, signals: CompletionSignals) -> bool:
        """Check if signals indicate completion.

        Args:
            signals: CompletionSignals to check

        Returns:
            True if completion_score >= threshold
        """
        return signals.completion_score >= self.completion_threshold

    def explain(self, signals: CompletionSignals) -> str:
        """Generate human-readable explanation of signals.

        Args:
            signals: CompletionSignals to explain

        Returns:
            Explanation text
        """
        if self.is_complete(signals):
            return self._explain_complete(signals)
        return self._explain_incomplete(signals)

    def _explain_complete(self, signals: CompletionSignals) -> str:
        """Explain why signals indicate completion.

        Args:
            signals: CompletionSignals (complete)

        Returns:
            Explanation text
        """
        lines = ["Work appears complete:"]

        if signals.all_steps_complete:
            lines.append("✓ All tasks completed")
        if signals.pr_created:
            pr_text = f"PR #{signals.pr_number}" if signals.pr_number else "PR"
            lines.append(f"✓ {pr_text} created")
        if signals.ci_passing:
            lines.append("✓ CI checks passing")
        if signals.pr_mergeable:
            lines.append("✓ PR is mergeable")
        if signals.has_commits:
            lines.append("✓ Work committed")
        if signals.no_uncommitted_changes:
            lines.append("✓ Clean working tree")

        lines.append(f"\nCompletion score: {signals.completion_score:.1%}")
        return "\n".join(lines)

    def _explain_incomplete(self, signals: CompletionSignals) -> str:
        """Explain what's missing for completion.

        Args:
            signals: CompletionSignals (incomplete)

        Returns:
            Explanation text
        """
        lines = ["Work incomplete:"]

        missing = []
        if not signals.all_steps_complete:
            missing.append("Tasks pending")
        if not signals.pr_created:
            missing.append("No PR created")
        if not signals.ci_passing:
            if signals.pr_created:
                missing.append("CI not passing")
        if not signals.pr_mergeable:
            if signals.pr_created:
                missing.append("PR has conflicts")
        if not signals.has_commits:
            missing.append("No commits")
        if not signals.no_uncommitted_changes:
            missing.append("Uncommitted changes exist")

        for item in missing:
            lines.append(f"✗ {item}")

        lines.append(f"\nCompletion score: {signals.completion_score:.1%}")
        lines.append(f"(Threshold: {self.completion_threshold:.1%})")
        return "\n".join(lines)
