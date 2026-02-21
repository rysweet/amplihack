"""Backward-compatible imports from amplihack-agent-eval.

This module re-exports key classes from the standalone eval package
so existing code continues to work during the migration period.

When amplihack-agent-eval is installed, all types come from the
standalone package. When it is not installed, this module is a no-op
(no errors raised, but types will not be available).

Usage:
    from amplihack.eval.compat import AgentAdapter, EvalRunner
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from amplihack_eval.adapters.base import AgentAdapter, AgentResponse, ToolCall
    from amplihack_eval.core.grader import GradeResult, grade_answer
    from amplihack_eval.core.runner import EvalRunner, LongHorizonMemoryEval
    from amplihack_eval.data.long_horizon import (
        GradingRubric,
        GroundTruth,
        Question,
        Turn,
        generate_dialogue,
        generate_questions,
    )
    from amplihack_eval.self_improve.patch_proposer import PatchProposal, propose_patch
    from amplihack_eval.self_improve.reviewer_voting import (
        ReviewResult,
        ReviewVote,
        vote_on_proposal,
    )

    __all__ = [
        # Adapters
        "AgentAdapter",
        "AgentResponse",
        "ToolCall",
        # Runner
        "EvalRunner",
        "LongHorizonMemoryEval",
        # Grader
        "grade_answer",
        "GradeResult",
        # Data generation
        "generate_dialogue",
        "generate_questions",
        "Turn",
        "Question",
        "GroundTruth",
        "GradingRubric",
        # Self-improvement
        "PatchProposal",
        "propose_patch",
        "ReviewVote",
        "ReviewResult",
        "vote_on_proposal",
    ]

except ImportError:
    # amplihack-agent-eval not installed -- compat layer is a no-op.
    # Callers should guard with `if hasattr(compat, 'AgentAdapter')` or
    # catch ImportError when importing specific names.
    pass
