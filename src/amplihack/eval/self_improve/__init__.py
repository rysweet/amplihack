"""Self-improvement infrastructure for goal-seeking agents.

Analyzes eval failures, generates hypotheses about root causes,
proposes code/prompt patches, validates in sandboxed environments,
and gates promotion through regression checks.

Philosophy:
- Measure → Analyze → Hypothesize → Patch → Validate → Promote
- Never modify grader, test data, or safety constraints
- All changes go through PR review (never direct to main)
- Focus on prompt templates first (safest), code changes second
"""

from .error_analyzer import ErrorAnalysis, analyze_eval_results

__all__ = ["ErrorAnalysis", "analyze_eval_results"]
