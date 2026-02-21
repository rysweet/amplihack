"""Self-improvement infrastructure for goal-seeking agents.

Analyzes eval failures, generates hypotheses about root causes,
proposes code/prompt patches, validates via reviewer voting,
and gates promotion through regression checks.

Philosophy:
- Measure -> Analyze -> Hypothesize -> Patch -> Challenge -> Vote -> Validate -> Promote
- Never modify grader, test data, or safety constraints
- All changes go through PR review (never direct to main)
- Focus on prompt templates first (safest), code changes second
- Every patch must survive challenge and 3-reviewer vote
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .error_analyzer import ErrorAnalysis, analyze_eval_results
from .patch_proposer import PatchHistory, PatchProposal, propose_patch
from .reviewer_voting import (
    ChallengeResponse,
    ReviewResult,
    ReviewVote,
    challenge_proposal,
    review_result_to_dict,
    vote_on_proposal,
)

if TYPE_CHECKING:
    from .runner import (
        IterationResult,
        ResearchDecision,
        RunnerConfig,
        RunnerResult,
        run_self_improvement,
    )


def __getattr__(name: str):
    """Lazy imports for runner module to avoid circular import warnings."""
    _runner_names = {
        "IterationResult",
        "ResearchDecision",
        "RunnerConfig",
        "RunnerResult",
        "run_self_improvement",
    }
    if name in _runner_names:
        from . import runner

        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # error_analyzer
    "ErrorAnalysis",
    "analyze_eval_results",
    # patch_proposer
    "PatchProposal",
    "PatchHistory",
    "propose_patch",
    # reviewer_voting
    "ReviewVote",
    "ChallengeResponse",
    "ReviewResult",
    "challenge_proposal",
    "vote_on_proposal",
    "review_result_to_dict",
    # runner (lazy)
    "run_self_improvement",
    "RunnerConfig",
    "RunnerResult",
    "IterationResult",
    "ResearchDecision",
]
