"""Semantic grader for quiz answers.

Uses LLM to semantically evaluate agent answers against expected answers.
Philosophy: Single responsibility - just grading, no other logic.
"""

import json
import os
import re
from dataclasses import dataclass

import anthropic  # type: ignore[import-untyped]


@dataclass
class GradeResult:
    """Result of grading an answer."""

    score: float  # 0.0 to 1.0
    reasoning: str


def _extract_json(text: str) -> dict:
    """Extract a JSON object from LLM response text.

    Handles common LLM response patterns:
    - Raw JSON: {"score": 0.85, ...}
    - Markdown fenced: ```json\n{...}\n```
    - Markdown fenced without language tag: ```\n{...}\n```

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


def grade_answer(question: str, expected: str, actual: str, level: str) -> GradeResult:
    """Grade an answer using semantic comparison.

    Args:
        question: The quiz question
        expected: Expected answer
        actual: Agent's actual answer
        level: Cognitive level (L1, L2, L3, L4, L5, L6)

    Returns:
        GradeResult with score and reasoning
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise OSError("ANTHROPIC_API_KEY environment variable is required for grading")
    client = anthropic.Anthropic(api_key=api_key)

    grader_model = os.environ.get("GRADER_MODEL", "claude-sonnet-4-5-20250929")

    prompt = f"""You are grading an AI agent's answer to a quiz question.

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
- IMPORTANT: If the agent shows work/reasoning, look at the FINAL CONCLUSION,
  not just the opening line. Agents may self-correct during reasoning.
  The final answer at the end of the response is what matters.

Return ONLY a JSON object with this structure:
{{"score": 0.85, "reasoning": "Brief explanation of grade"}}"""

    message = client.messages.create(
        model=grader_model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract JSON from response, handling markdown fences
    response_text = message.content[0].text
    result_json = _extract_json(response_text)

    return GradeResult(score=result_json["score"], reasoning=result_json["reasoning"])


__all__ = ["grade_answer", "GradeResult"]
