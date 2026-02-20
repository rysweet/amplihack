"""Self-improvement infrastructure for goal-seeking agents.

Analyzes eval failures, generates hypotheses about root causes,
proposes code/prompt patches, validates in sandboxed environments,
and gates promotion through regression checks.

Philosophy:
- Measure -> Analyze -> Hypothesize -> Patch -> Validate -> Promote
- Never modify grader, test data, or safety constraints
- All changes go through PR review (never direct to main)
- Focus on prompt templates first (safest), code changes second
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .error_analyzer import ErrorAnalysis, analyze_eval_results

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
    "ErrorAnalysis",
    "analyze_eval_results",
    "run_self_improvement",
    "RunnerConfig",
    "RunnerResult",
    "IterationResult",
    "ResearchDecision",
]
