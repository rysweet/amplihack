"""Metacognition grader for evaluating agent reasoning quality.

Evaluates HOW the agent reasoned, not just WHAT it answered.
Uses ReasoningTrace from the agentic loop to assess:
- Effort calibration (proportional effort to complexity)
- Sufficiency judgment (correctly assessed when enough info collected)
- Search quality (ratio of useful queries)
- Self-correction (refinement and verification behaviors)

Philosophy: Single responsibility - just metacognition grading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetacognitionGrade:
    """Result of metacognition grading.

    Attributes:
        effort_calibration: 0.0-1.0, penalizes over/under-effort
        sufficiency_judgment: 0.0-1.0, correct sufficient/insufficient decisions
        search_quality: 0.0-1.0, ratio of queries that found new facts
        self_correction: 0.0-1.0, refinement and verification behaviors
        overall: Weighted average of all dimensions
        details: Explanations for each score
    """

    effort_calibration: float = 0.0
    sufficiency_judgment: float = 0.0
    search_quality: float = 0.0
    self_correction: float = 0.0
    overall: float = 0.0
    details: dict[str, str] = field(default_factory=dict)


# Complexity levels and their expected effort ranges
_COMPLEXITY_EFFORT = {
    "simple_recall": {"min_queries": 0, "max_queries": 2, "max_iterations": 1},
    "mathematical_computation": {"min_queries": 2, "max_queries": 6, "max_iterations": 3},
    "temporal_comparison": {"min_queries": 2, "max_queries": 8, "max_iterations": 3},
    "multi_source_synthesis": {"min_queries": 3, "max_queries": 8, "max_iterations": 3},
    "contradiction_resolution": {"min_queries": 2, "max_queries": 5, "max_iterations": 2},
}


def grade_metacognition(
    trace: dict[str, Any],
    answer_score: float,
    level: str,
) -> MetacognitionGrade:
    """Grade the reasoning trace for metacognitive quality.

    Args:
        trace: Serialized ReasoningTrace dict with keys:
            - question, intent, steps, total_facts_collected,
              total_queries_executed, iterations, final_confidence,
              used_simple_path
        answer_score: The answer quality score (0.0-1.0) for context
        level: Cognitive level (L1, L2, L3, etc.)

    Returns:
        MetacognitionGrade with dimension scores and explanations
    """
    details = {}

    # Extract trace info
    intent_type = trace.get("intent", {}).get("intent", "simple_recall")
    steps = trace.get("steps", [])
    total_queries = trace.get("total_queries_executed", 0)
    total_facts = trace.get("total_facts_collected", 0)
    iterations = trace.get("iterations", 0)
    final_confidence = trace.get("final_confidence", 0.0)
    used_simple = trace.get("used_simple_path", False)

    # 1. Effort Calibration: Did the agent use proportional effort?
    effort_score = _grade_effort_calibration(
        intent_type, total_queries, iterations, used_simple, level, details
    )

    # 2. Sufficiency Judgment: Did it correctly assess when it had enough?
    sufficiency_score = _grade_sufficiency_judgment(
        steps, final_confidence, answer_score, total_facts, details
    )

    # 3. Search Quality: Were queries productive?
    search_score = _grade_search_quality(steps, total_queries, total_facts, details)

    # 4. Self-Correction: Did it refine and verify?
    correction_score = _grade_self_correction(steps, iterations, details)

    # Weighted overall
    overall = (
        0.25 * effort_score
        + 0.30 * sufficiency_score
        + 0.25 * search_score
        + 0.20 * correction_score
    )

    return MetacognitionGrade(
        effort_calibration=round(effort_score, 3),
        sufficiency_judgment=round(sufficiency_score, 3),
        search_quality=round(search_score, 3),
        self_correction=round(correction_score, 3),
        overall=round(overall, 3),
        details=details,
    )


def _grade_effort_calibration(
    intent_type: str,
    total_queries: int,
    iterations: int,
    used_simple: bool,
    level: str,
    details: dict,
) -> float:
    """Score effort calibration: proportional effort to complexity."""
    expected = _COMPLEXITY_EFFORT.get(intent_type, _COMPLEXITY_EFFORT["simple_recall"])

    # Simple questions should use simple path
    if intent_type == "simple_recall":
        if used_simple:
            details["effort"] = "Correctly used simple retrieval for simple question"
            return 1.0
        details["effort"] = (
            f"Over-effort: used iterative loop ({total_queries} queries) for simple question"
        )
        return max(0.3, 1.0 - 0.15 * total_queries)

    # Complex questions should NOT use simple path
    if used_simple and intent_type != "simple_recall":
        details["effort"] = f"Under-effort: used simple retrieval for {intent_type}"
        return 0.3

    # Check if queries are in expected range
    min_q = expected["min_queries"]
    max_q = expected["max_queries"]

    if min_q <= total_queries <= max_q:
        details["effort"] = f"Good effort calibration: {total_queries} queries for {intent_type}"
        return 1.0
    if total_queries < min_q:
        shortfall = min_q - total_queries
        details["effort"] = f"Under-effort: {total_queries} queries, expected at least {min_q}"
        return max(0.3, 1.0 - 0.2 * shortfall)
    excess = total_queries - max_q
    details["effort"] = f"Over-effort: {total_queries} queries, expected at most {max_q}"
    return max(0.5, 1.0 - 0.1 * excess)


def _grade_sufficiency_judgment(
    steps: list[dict],
    final_confidence: float,
    answer_score: float,
    total_facts: int,
    details: dict,
) -> float:
    """Score sufficiency judgment: correct assessment of information adequacy."""
    # Find evaluation steps
    eval_steps = [s for s in steps if s.get("step_type") == "evaluate"]

    if not eval_steps:
        # No evaluation = no metacognition about sufficiency
        if answer_score >= 0.8:
            details["sufficiency"] = "No explicit evaluation, but answer was good"
            return 0.6
        details["sufficiency"] = "No explicit evaluation, and answer was poor"
        return 0.3

    # Check if final confidence correlates with answer quality
    # High confidence + high score = good calibration
    # High confidence + low score = overconfident
    # Low confidence + high score = underconfident
    # Low confidence + low score = well-calibrated
    confidence_error = abs(final_confidence - answer_score)

    if confidence_error < 0.2:
        details["sufficiency"] = (
            f"Well-calibrated: confidence={final_confidence:.2f}, score={answer_score:.2f}"
        )
        return 1.0
    if confidence_error < 0.4:
        details["sufficiency"] = (
            f"Moderate calibration: confidence={final_confidence:.2f}, score={answer_score:.2f}"
        )
        return 0.7
    direction = "overconfident" if final_confidence > answer_score else "underconfident"
    details["sufficiency"] = (
        f"Poorly calibrated ({direction}): confidence={final_confidence:.2f}, score={answer_score:.2f}"
    )
    return max(0.2, 1.0 - confidence_error)


def _grade_search_quality(
    steps: list[dict],
    total_queries: int,
    total_facts: int,
    details: dict,
) -> float:
    """Score search quality: ratio of productive searches."""
    if total_queries == 0:
        details["search"] = "No queries executed"
        return 0.5  # Neutral - might be simple path

    search_steps = [s for s in steps if s.get("step_type") == "search"]
    productive_queries = sum(1 for s in search_steps if s.get("facts_found", 0) > 0)
    total_search_queries = sum(len(s.get("queries", [])) for s in search_steps)

    if total_search_queries == 0:
        details["search"] = "No search queries found in trace"
        return 0.5

    # Ratio of queries that found at least one fact
    productivity = productive_queries / len(search_steps) if search_steps else 0

    # Facts-per-query ratio (efficiency)
    efficiency = min(
        1.0, total_facts / max(total_queries, 1) / 3
    )  # Normalize: 3 facts/query = perfect

    score = 0.6 * productivity + 0.4 * efficiency
    details["search"] = (
        f"Productivity: {productive_queries}/{len(search_steps)} searches found facts, "
        f"efficiency: {total_facts} facts from {total_queries} queries"
    )
    return min(1.0, score)


def _grade_self_correction(
    steps: list[dict],
    iterations: int,
    details: dict,
) -> float:
    """Score self-correction: refinement and verification behaviors."""
    refine_steps = [s for s in steps if s.get("step_type") == "refine"]
    eval_steps = [s for s in steps if s.get("step_type") == "evaluate"]

    score = 0.5  # Baseline

    # Bonus for having evaluation steps (self-monitoring)
    if eval_steps:
        score += 0.2
        details_parts = ["Has evaluation steps"]
    else:
        details_parts = ["No evaluation steps"]

    # Bonus for refinement (adapting search strategy)
    if refine_steps:
        score += 0.2
        details_parts.append("refined queries after evaluation")

    # Bonus for multiple iterations when needed (persistence)
    if iterations >= 2:
        score += 0.1
        details_parts.append(f"iterated {iterations} times")

    # Check if evaluation led to useful refinement
    for i, step in enumerate(steps):
        if step.get("step_type") == "evaluate" and not step.get("evaluation", {}).get(
            "sufficient", True
        ):
            # Found insufficient eval - check if next step is refine
            if i + 1 < len(steps) and steps[i + 1].get("step_type") in ("refine", "plan"):
                score = min(1.0, score + 0.1)
                details_parts.append("correctly refined after insufficient evaluation")

    details["self_correction"] = "; ".join(details_parts)
    return min(1.0, score)


__all__ = ["grade_metacognition", "MetacognitionGrade"]
