"""Semantic grader for quiz answers.

Uses LLM to semantically evaluate agent answers against expected answers.
Supports multi-vote grading (majority vote across N calls) to reduce noise.
Philosophy: Single responsibility - just grading, no other logic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import statistics
from dataclasses import dataclass

import anthropic  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class GradeResult:
    """Result of grading an answer."""

    score: float  # 0.0 to 1.0
    reasoning: str
    vote_scores: list[float] | None = None  # Individual vote scores when multi-vote


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM response text.

    Handles common LLM response patterns:
    - Raw JSON: {"score": 0.85, ...}
    - Markdown fenced: ```json\\n{...}\\n```
    - Markdown fenced without language tag: ```\\n{...}\\n```

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dict

    Raises:
        json.JSONDecodeError: If no valid JSON object can be extracted
    """
    stripped = text.strip()

    # Try direct parse first
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences: ```json ... ``` or ``` ... ```
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find first { ... } block as last resort
    brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError(
        f"No valid JSON found in response: {stripped[:200]}",
        stripped,
        0,
    )


def _build_grading_prompt(question: str, expected: str, actual: str, level: str) -> str:
    """Build the grading prompt for LLM evaluation.

    Args:
        question: The quiz question
        expected: Expected answer
        actual: Agent's actual answer
        level: Cognitive level

    Returns:
        Formatted prompt string
    """
    # Level-specific grading criteria
    level_criteria = ""
    if level == "L3":
        level_criteria = (
            "\n\nL3 TEMPORAL REASONING grading criteria:\n"
            "- The NUMERICAL values (differences, totals) are the PRIMARY grading dimension.\n"
            "  If the agent computes the correct numbers, award at least 0.7.\n"
            "- TREND DIRECTION is secondary. Accept any of these as describing a decrease:\n"
            "  'deceleration', 'slowing', 'slowed', 'decreased rate', 'less in later period'\n"
            "  These all mean the SAME THING as the expected answer's trend description.\n"
            "- Award 0.9-1.0 if the agent gets BOTH correct numbers AND correct trend direction.\n"
        )
    elif level == "L5":
        level_criteria = (
            "\n\nL5 EXPLICIT GRADING CRITERIA for contradiction acknowledgment:\n"
            "Award 0.9-1.0 if the agent:\n"
            "  - Names BOTH conflicting values/claims with their sources\n"
            "  - Uses language like 'conflicting', 'disagree', 'different reports'\n"
            "Award 0.6-0.8 if the agent:\n"
            "  - Mentions both values but does not explicitly flag the conflict\n"
            "  - Or flags the conflict but misattributes a source\n"
            "Award 0.3-0.5 if the agent:\n"
            "  - Only presents one value but hints at uncertainty\n"
            "Award 0.0-0.2 if the agent:\n"
            "  - Presents only one value with no mention of disagreement\n"
        )

    return f"""You are grading an AI agent's answer to a quiz question.

Cognitive Level: {level}
- L1 (Recall): Direct facts, must be factually accurate
- L2 (Multi-Source Synthesis): Combining information from multiple sources
- L3 (Temporal Reasoning): Understanding changes over time, computing differences
- L4 (Procedural Learning): Learning and applying step-by-step procedures
- L5 (Contradiction Handling): Detecting and reasoning about conflicting information
- L6 (Incremental Learning): Updating knowledge when new information arrives

Question: {question}

Expected Answer: {expected}

Agent's Answer: {actual}

Grade the agent's answer on a scale of 0.0 to 1.0:
- 1.0: Perfect match or semantically equivalent
- 0.8-0.9: Correct main points, minor differences
- 0.6-0.7: Partially correct, missing some details
- 0.4-0.5: Some relevant content, significant gaps
- 0.0-0.3: Incorrect or unrelated

Special considerations:
- L5 (Contradictions): Award full points if agent acknowledges the contradiction, even if they don't resolve it
- L6 (Updates): Agent must use the MOST RECENT information, not outdated data
- L7 (Teaching): Grade based on factual accuracy of the answer, regardless of how it was learned
- L9 (Causal): When asking about "most important single factor" or "root cause", accept
  EITHER "program restructuring after 2018" OR "winning the hosting bid" as valid root causes.
  Both are defensible interpretations. Score 0.8+ if the agent picks either and provides
  sound causal reasoning explaining why that factor is the root cause.
- L11 (Novel Skill): For workflow/config generation, grade on correctness of REQUIRED fields.
  Do NOT penalize for including extra optional fields if the required ones are correct.
- L12 (Far Transfer): When computing ratios and trends, the DIRECTION of the trend
  (improving vs worsening) is critical. Correct ratio computation with wrong trend
  direction should score 0.5-0.6, not 0.8+.
- IMPORTANT: If the agent shows work/reasoning, look at the FINAL CONCLUSION,
  not just the opening line. Agents may self-correct during reasoning.
  The final answer at the end of the response is what matters.
{level_criteria}
Return ONLY a JSON object with this structure:
{{"score": 0.85, "reasoning": "Brief explanation of grade"}}"""


def _single_grade_call(client: anthropic.Anthropic, model: str, prompt: str) -> GradeResult:
    """Execute a single grading LLM call.

    Args:
        client: Anthropic client
        model: Model identifier
        prompt: Grading prompt

    Returns:
        GradeResult from this single call
    """
    message = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    result_json = _extract_json(response_text)

    return GradeResult(
        score=float(result_json["score"]),
        reasoning=result_json["reasoning"],
    )


def grade_answer(
    question: str,
    expected: str,
    actual: str,
    level: str,
    num_votes: int = 1,
) -> GradeResult:
    """Grade an answer using semantic comparison with optional multi-vote.

    When num_votes > 1, runs multiple independent grading calls and takes
    the median score as the final grade. This reduces grading noise on
    ambiguous answers.

    Args:
        question: The quiz question
        expected: Expected answer
        actual: Agent's actual answer
        level: Cognitive level (L1, L2, L3, L4, L5, L6, etc.)
        num_votes: Number of grading calls (1 = single, 3 = majority vote)

    Returns:
        GradeResult with score, reasoning, and optional vote_scores
    """
    if not question or not question.strip():
        raise ValueError("Question must be a non-empty string")
    if not expected or not expected.strip():
        raise ValueError("Expected answer must be a non-empty string")
    if not actual or not actual.strip():
        return GradeResult(score=0.0, reasoning="Agent provided no answer")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OSError("ANTHROPIC_API_KEY environment variable is required for grading")
    client = anthropic.Anthropic(api_key=api_key)

    grader_model = os.environ.get("GRADER_MODEL", "claude-sonnet-4-5-20250929")
    prompt = _build_grading_prompt(question, expected, actual, level)

    # Clamp num_votes to valid range
    num_votes = max(1, min(num_votes, 9))

    if num_votes == 1:
        return _single_grade_call(client, grader_model, prompt)

    # Multi-vote: run N grading calls and take median
    vote_results: list[GradeResult] = []
    for vote_idx in range(num_votes):
        try:
            result = _single_grade_call(client, grader_model, prompt)
            vote_results.append(result)
        except Exception as e:
            logger.warning("Grading vote %d failed: %s", vote_idx, e)
            continue

    if not vote_results:
        raise RuntimeError("All grading votes failed")

    vote_scores = [r.score for r in vote_results]
    median_score = statistics.median(vote_scores)

    # Use reasoning from the vote closest to the median
    closest_vote = min(vote_results, key=lambda r: abs(r.score - median_score))

    return GradeResult(
        score=median_score,
        reasoning=f"[{num_votes}-vote median] {closest_vote.reasoning}",
        vote_scores=vote_scores,
    )


__all__ = ["grade_answer", "GradeResult"]
