"""Error analyzer for eval failures.

Maps eval scores and reasoning traces to structured failure categories,
identifying which code component is likely responsible for each failure.

Philosophy:
- Failures are categorized, not just scored
- Each category maps to a specific code file/function
- Evidence (traces) are preserved for hypothesis generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Failure taxonomy: maps symptoms to root components
FAILURE_TAXONOMY = {
    "retrieval_insufficient": {
        "description": "Not enough relevant facts were retrieved",
        "component": "agentic_loop.py::_plan_retrieval",
        "prompt_template": "plan_retrieval.md",
        "symptoms": ["facts_collected < expected", "missing key data points"],
    },
    "temporal_ordering_wrong": {
        "description": "Correct facts found but temporal computation failed",
        "component": "learning_agent.py::_synthesize_with_llm (temporal instructions)",
        "prompt_template": "synthesis_instructions.md",
        "symptoms": ["has temporal data but wrong arithmetic"],
    },
    "intent_misclassification": {
        "description": "Question classified as wrong intent type",
        "component": "learning_agent.py::_detect_intent",
        "prompt_template": "intent_classification.md",
        "symptoms": ["wrong retrieval strategy chosen"],
    },
    "fact_extraction_incomplete": {
        "description": "Key facts not extracted during learning",
        "component": "learning_agent.py::_extract_facts_with_llm",
        "prompt_template": "fact_extraction.md",
        "symptoms": ["missing facts in memory despite being in source content"],
    },
    "synthesis_hallucination": {
        "description": "Answer includes information not in the facts",
        "component": "learning_agent.py::_synthesize_with_llm",
        "prompt_template": "synthesis.md",
        "symptoms": ["answer contains data not in retrieved facts"],
    },
    "update_not_applied": {
        "description": "Agent used outdated data instead of updated version",
        "component": "hierarchical_memory.py::_detect_supersedes",
        "prompt_template": None,
        "symptoms": ["old values used when new values available"],
    },
    "contradiction_undetected": {
        "description": "Conflicting sources not identified",
        "component": "learning_agent.py::_detect_intent + synthesis",
        "prompt_template": "synthesis_instructions.md",
        "symptoms": ["presented one source as fact without noting conflict"],
    },
    "procedural_ordering_lost": {
        "description": "Steps mentioned but out of sequence",
        "component": "learning_agent.py::_extract_facts_with_llm",
        "prompt_template": "fact_extraction.md",
        "symptoms": ["procedure steps scrambled or missing"],
    },
    "teaching_coverage_gap": {
        "description": "Student not taught certain key facts",
        "component": "teaching_session.py::_teacher_respond",
        "prompt_template": "teaching_response.md",
        "symptoms": ["student scores low on specific sub-topics"],
    },
    "counterfactual_refusal": {
        "description": "Agent refused to reason hypothetically",
        "component": "learning_agent.py::_synthesize_with_llm",
        "prompt_template": "synthesis_instructions.md",
        "symptoms": ["answer says 'cannot answer' for what-if questions"],
    },
}


@dataclass
class ErrorAnalysis:
    """Structured analysis of an eval failure.

    Attributes:
        failure_mode: Key from FAILURE_TAXONOMY
        affected_level: Which eval level (L1-L12)
        affected_component: File + function responsible
        prompt_template: Which prompt template to improve (if applicable)
        evidence: Failed question details with traces
        score: Score achieved (0.0-1.0)
        suggested_focus: Human-readable description of what to investigate
    """

    failure_mode: str
    affected_level: str
    affected_component: str
    prompt_template: str | None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    suggested_focus: str = ""


def analyze_eval_results(
    level_results: list[dict[str, Any]],
    score_threshold: float = 0.6,
) -> list[ErrorAnalysis]:
    """Analyze eval results and categorize failures.

    Args:
        level_results: List of level result dicts with 'details' containing
            per-question scores, reasoning traces, and metacognition data.
        score_threshold: Questions below this score are considered failures.

    Returns:
        List of ErrorAnalysis objects, one per failure cluster.
    """
    analyses: list[ErrorAnalysis] = []

    for level_result in level_results:
        level_id = level_result.get("level_id", "?")
        details = level_result.get("details", [])

        for question_detail in details:
            score = question_detail.get("score", 1.0)
            if score >= score_threshold:
                continue

            # Classify the failure
            failure_mode = _classify_failure(question_detail, level_id)
            taxonomy_entry = FAILURE_TAXONOMY.get(failure_mode, {})

            analysis = ErrorAnalysis(
                failure_mode=failure_mode,
                affected_level=level_id,
                affected_component=taxonomy_entry.get("component", "unknown"),
                prompt_template=taxonomy_entry.get("prompt_template"),
                evidence=[question_detail],
                score=score,
                suggested_focus=_generate_focus_description(
                    failure_mode, question_detail, taxonomy_entry
                ),
            )
            analyses.append(analysis)

    # Sort by score (worst first)
    analyses.sort(key=lambda a: a.score)
    return analyses


def _classify_failure(detail: dict[str, Any], level_id: str) -> str:
    """Classify a single question failure into a failure mode.

    Uses heuristics based on the question level, reasoning type,
    metacognition trace, and answer content.
    """
    reasoning_type = detail.get("reasoning_type", "")
    actual = detail.get("actual", "").lower()
    metacog = detail.get("metacognition", {})

    # Check for counterfactual refusal
    if any(
        phrase in actual for phrase in ("cannot answer", "not possible", "no facts", "not provided")
    ):
        if (
            "what if" in detail.get("question", "").lower()
            or "without" in detail.get("question", "").lower()
        ):
            return "counterfactual_refusal"

    # Check for update not applied (L6)
    if level_id == "L6" and reasoning_type in (
        "incremental_update",
        "incremental_tracking",
    ):
        return "update_not_applied"

    # Check for contradiction not detected (L5)
    if level_id == "L5":
        return "contradiction_undetected"

    # Check for temporal ordering issues (L3)
    if reasoning_type in ("temporal_comparison", "temporal_difference", "temporal_trend"):
        return "temporal_ordering_wrong"

    # Check for procedural issues (L4)
    if reasoning_type in ("procedural_sequence", "procedural_application"):
        return "procedural_ordering_lost"

    # Check for retrieval issues via metacognition
    if metacog:
        effort_detail = metacog.get("details", {}).get("effort", "")
        if "under-effort" in effort_detail.lower():
            return "intent_misclassification"
        search_detail = metacog.get("details", {}).get("search", "")
        if "0/" in search_detail:  # No productive searches
            return "retrieval_insufficient"

    # Check for synthesis/multi-source issues (L2)
    if reasoning_type == "cross_source_synthesis":
        return "retrieval_insufficient"

    # Default: synthesis hallucination
    return "synthesis_hallucination"


def _generate_focus_description(
    failure_mode: str,
    detail: dict[str, Any],
    taxonomy_entry: dict[str, Any],
) -> str:
    """Generate human-readable description of what to investigate."""
    question = detail.get("question", "")[:80]
    description = taxonomy_entry.get("description", failure_mode)
    component = taxonomy_entry.get("component", "unknown")

    return (
        f"{description}. Question: '{question}...'. "
        f"Investigate: {component}. "
        f"Score: {detail.get('score', 0):.0%}"
    )


__all__ = ["ErrorAnalysis", "analyze_eval_results", "FAILURE_TAXONOMY"]
