"""Patch proposer for self-improvement automation.

Uses LLM to analyze eval failures, generate hypotheses about root causes,
and propose specific code changes as unified diffs.

Philosophy:
- Failures drive hypotheses, not guesses
- Every patch has a clear rationale and expected impact
- Previous iteration outcomes prevent repeating failed fixes
- Confidence scores enable informed decision-making
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PatchProposal:
    """A proposed code change to fix an eval failure category.

    Attributes:
        target_file: Path to the file to modify
        hypothesis: Why the category is failing
        description: What the patch does
        diff: Unified diff format of the change
        expected_impact: Mapping of category -> expected score delta (pp)
        risk_assessment: What could go wrong if this patch is applied
        confidence: Confidence in the fix (0.0-1.0)
    """

    target_file: str
    hypothesis: str
    description: str
    diff: str
    expected_impact: dict[str, float] = field(default_factory=dict)
    risk_assessment: str = ""
    confidence: float = 0.0


@dataclass
class PatchHistory:
    """Tracks previously proposed patches and their outcomes.

    Used to avoid re-proposing patches that were reverted or rejected.
    """

    applied_patches: list[dict[str, Any]] = field(default_factory=list)
    reverted_patches: list[dict[str, Any]] = field(default_factory=list)
    rejected_patches: list[dict[str, Any]] = field(default_factory=list)


def _build_proposal_prompt(
    category: str,
    category_score: float,
    failed_questions: list[dict[str, Any]],
    bottleneck: str,
    suggested_fix: str,
    relevant_code: str,
    history: PatchHistory,
) -> str:
    """Build the LLM prompt for generating a patch proposal.

    Args:
        category: The failing category name
        category_score: Current average score for this category
        failed_questions: List of failed question details
        bottleneck: Identified bottleneck component
        suggested_fix: Suggested fix from diagnosis
        relevant_code: Current code of the target file
        history: Previous patch attempts and outcomes

    Returns:
        Prompt string for the LLM
    """
    # Format failed questions
    questions_text = ""
    for i, fq in enumerate(failed_questions[:5], 1):
        questions_text += (
            f"\n  {i}. Question: {fq.get('question_text', '')[:120]}\n"
            f"     Expected: {fq.get('expected_answer', '')[:120]}\n"
            f"     Actual: {fq.get('actual_answer', '')[:120]}\n"
            f"     Score: {fq.get('score', 0):.2%}\n"
        )
        dims = fq.get("dimensions", {})
        if dims:
            dim_strs = [f"{d}: {s:.2%}" for d, s in dims.items()]
            questions_text += f"     Dimensions: {', '.join(dim_strs)}\n"

    # Format history of failed attempts
    history_text = ""
    if history.reverted_patches:
        history_text += "\nPreviously reverted patches (DO NOT repeat these):\n"
        for p in history.reverted_patches[-5:]:
            history_text += (
                f"  - Target: {p.get('target_file', '?')}\n"
                f"    Description: {p.get('description', '?')[:100]}\n"
                f"    Reason for revert: {p.get('revert_reason', 'regression')}\n"
            )

    if history.rejected_patches:
        history_text += "\nPreviously rejected patches (different approach needed):\n"
        for p in history.rejected_patches[-5:]:
            history_text += (
                f"  - Target: {p.get('target_file', '?')}\n"
                f"    Description: {p.get('description', '?')[:100]}\n"
                f"    Rejection reason: {p.get('rejection_reason', 'unknown')}\n"
            )

    return f"""You are an expert code improvement agent. Analyze the failing eval category
and propose a specific code change to fix it.

## Failing Category
- Category: {category}
- Current Score: {category_score:.2%}
- Bottleneck Component: {bottleneck}
- Suggested Fix Direction: {suggested_fix}

## Failed Questions{questions_text}
{history_text}
## Current Code (target file)
```python
{relevant_code[:3000]}
```

## Your Task

Analyze WHY this category is failing and propose a SPECIFIC code change.

Respond with a JSON object:
{{
  "hypothesis": "Clear explanation of why this category fails",
  "description": "What the patch does in 1-2 sentences",
  "diff": "Unified diff of the change (--- a/file\\n+++ b/file\\n@@ ... @@\\n...)",
  "expected_impact": {{"category_name": expected_score_delta_in_percentage_points}},
  "risk_assessment": "What could go wrong",
  "confidence": 0.0 to 1.0
}}

Rules:
- The diff must be valid unified diff format
- Focus on the SMALLEST change that addresses the root cause
- Do NOT change test infrastructure, graders, or eval harness
- Prefer prompt/instruction changes over algorithmic changes
- Be honest about confidence - lower is better than overconfident
"""


def _read_target_file(bottleneck: str, project_root: Path) -> tuple[str, str]:
    """Read the target file based on the bottleneck component identifier.

    Args:
        bottleneck: Component identifier (e.g., "retrieval:keyword_search")
        project_root: Root directory of the project

    Returns:
        Tuple of (file_path, file_content)
    """
    # Map bottleneck components to likely target files
    component_file_map = {
        "retrieval:": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "synthesis:": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:keyword_search": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:aggregation": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:source_tracking": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:temporal_ordering": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:graph_traversal": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "synthesis:arithmetic": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "retrieval:confidence_weighting": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "synthesis:source_instructions": "src/amplihack/agents/goal_seeking/learning_agent.py",
        "synthesis:calibration": "src/amplihack/agents/goal_seeking/learning_agent.py",
    }

    # Find the best matching file path
    target_rel = "src/amplihack/agents/goal_seeking/learning_agent.py"
    for prefix, filepath in component_file_map.items():
        if bottleneck.startswith(prefix):
            target_rel = filepath
            break

    target_path = project_root / target_rel
    content = ""
    if target_path.exists():
        content = target_path.read_text()[:4000]  # Limit to avoid token overflow

    return target_rel, content


def _parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse LLM response as JSON, handling markdown code blocks.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed JSON dict
    """
    text = response_text.strip()

    # Strip markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    return json.loads(text)


def propose_patch(
    category: str,
    category_score: float,
    failed_questions: list[dict[str, Any]],
    bottleneck: str,
    suggested_fix: str,
    history: PatchHistory | None = None,
    project_root: Path | None = None,
    llm_call: Any | None = None,
) -> PatchProposal:
    """Generate a patch proposal for a failing category using LLM analysis.

    Args:
        category: The failing category name
        category_score: Current average score
        failed_questions: Details of failed questions
        bottleneck: Identified bottleneck component
        suggested_fix: Suggested fix direction
        history: Previous patch attempts (for avoiding repeats)
        project_root: Project root directory for reading source files
        llm_call: Callable for LLM inference. Signature: (prompt: str) -> str.
                  If None, returns a stub proposal.

    Returns:
        PatchProposal with the proposed change
    """
    if history is None:
        history = PatchHistory()

    if project_root is None:
        project_root = Path(".")

    # Read the target file
    target_file, relevant_code = _read_target_file(bottleneck, project_root)

    # Build the prompt
    prompt = _build_proposal_prompt(
        category=category,
        category_score=category_score,
        failed_questions=failed_questions,
        bottleneck=bottleneck,
        suggested_fix=suggested_fix,
        relevant_code=relevant_code,
        history=history,
    )

    # Call LLM or return stub
    if llm_call is None:
        logger.warning("No LLM callable provided; returning stub proposal")
        return PatchProposal(
            target_file=target_file,
            hypothesis=f"Category '{category}' fails due to {bottleneck}",
            description=suggested_fix,
            diff="",
            expected_impact={category: 10.0},
            risk_assessment="No LLM analysis available",
            confidence=0.1,
        )

    try:
        response_text = llm_call(prompt)
        parsed = _parse_llm_response(response_text)

        return PatchProposal(
            target_file=parsed.get("target_file", target_file),
            hypothesis=parsed.get("hypothesis", f"Failing on {category}"),
            description=parsed.get("description", "LLM-proposed change"),
            diff=parsed.get("diff", ""),
            expected_impact=parsed.get("expected_impact", {category: 5.0}),
            risk_assessment=parsed.get("risk_assessment", "Unknown"),
            confidence=float(parsed.get("confidence", 0.5)),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse LLM response for patch proposal: %s", e)
        return PatchProposal(
            target_file=target_file,
            hypothesis=f"Category '{category}' fails due to {bottleneck}",
            description=suggested_fix,
            diff="",
            expected_impact={category: 5.0},
            risk_assessment=f"LLM parse error: {e}",
            confidence=0.1,
        )


def propose_patch_from_analysis(
    category_analysis: dict[str, Any],
    history: PatchHistory | None = None,
    project_root: Path | None = None,
    llm_call: Any | None = None,
) -> PatchProposal:
    """Convenience wrapper to propose a patch from a CategoryAnalysis dict.

    Args:
        category_analysis: Dict form of CategoryAnalysis
        history: Previous patch history
        project_root: Project root directory
        llm_call: LLM callable

    Returns:
        PatchProposal
    """
    return propose_patch(
        category=category_analysis.get("category", "unknown"),
        category_score=category_analysis.get("avg_score", 0.0),
        failed_questions=category_analysis.get("failed_questions", []),
        bottleneck=category_analysis.get("bottleneck", "unknown"),
        suggested_fix=category_analysis.get("suggested_fix", ""),
        history=history,
        project_root=project_root,
        llm_call=llm_call,
    )


__all__ = [
    "PatchProposal",
    "PatchHistory",
    "propose_patch",
    "propose_patch_from_analysis",
]
