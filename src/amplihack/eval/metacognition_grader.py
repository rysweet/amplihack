"""Metacognition grader with 4-dimension scoring.

Evaluates student learning across four metacognitive dimensions:
1. Factual Accuracy - Are the facts correct?
2. Self-Awareness - Does the student know what it knows/doesn't know?
3. Knowledge Boundaries - Can the student identify gaps?
4. Explanation Quality - Are self-explanations coherent and insightful?

Philosophy:
- Single responsibility: Grade metacognition only
- LLM-powered evaluation via litellm
- Structured JSON output for reliable parsing
- Graceful degradation on errors
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import litellm  # type: ignore[import-unresolved]

logger = logging.getLogger(__name__)

DIMENSION_NAMES = [
    "factual_accuracy",
    "self_awareness",
    "knowledge_boundaries",
    "explanation_quality",
]


@dataclass
class Dimension:
    """A single scoring dimension.

    Attributes:
        name: Dimension identifier
        score: Score from 0.0 to 1.0
        reasoning: LLM's reasoning for the score
    """

    name: str
    score: float
    reasoning: str


@dataclass
class MetacognitionScore:
    """Complete metacognition evaluation result.

    Attributes:
        dimensions: List of 4 dimension scores
        overall_score: Mean of all dimension scores
        summary: Human-readable summary
    """

    dimensions: list[Dimension]
    overall_score: float
    summary: str


class MetacognitionGrader:
    """Grades student metacognition across 4 dimensions.

    Uses LLM to evaluate how well a student understands what they know
    and what they do not know, beyond just factual correctness.

    Args:
        model: LLM model identifier (litellm format)

    Example:
        >>> grader = MetacognitionGrader()
        >>> score = grader.grade(
        ...     question="What does L1 evaluate?",
        ...     expected_answer="L1 evaluates direct recall.",
        ...     student_answer="L1 tests recall of facts.",
        ...     self_explanation="I know this because recall means remembering.",
        ... )
        >>> print(score.overall_score)  # 0.8125
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929") -> None:
        self.model = model

    def grade(
        self,
        question: str,
        expected_answer: str,
        student_answer: str,
        self_explanation: str,
    ) -> MetacognitionScore:
        """Grade a single question-answer pair on 4 metacognition dimensions.

        Args:
            question: The quiz question
            expected_answer: Correct answer
            student_answer: Student's answer
            self_explanation: Student's self-explanation

        Returns:
            MetacognitionScore with 4 dimensions and overall score
        """
        try:
            return self._grade_with_llm(question, expected_answer, student_answer, self_explanation)
        except Exception as e:
            logger.warning("Grading failed: %s", e)
            return self._zero_score(f"Grading failed: {e}")

    def batch_grade(self, items: list[dict[str, str]]) -> list[MetacognitionScore]:
        """Grade multiple question-answer pairs.

        Args:
            items: List of dicts with keys:
                question, expected, actual, explanation

        Returns:
            List of MetacognitionScore objects
        """
        return [
            self.grade(
                question=item["question"],
                expected_answer=item["expected"],
                student_answer=item["actual"],
                self_explanation=item.get("explanation", ""),
            )
            for item in items
        ]

    def _grade_with_llm(
        self,
        question: str,
        expected_answer: str,
        student_answer: str,
        self_explanation: str,
    ) -> MetacognitionScore:
        """Use LLM to evaluate metacognition."""
        prompt = f"""Evaluate the student's metacognition across 4 dimensions.

Question: {question}
Expected Answer: {expected_answer}
Student's Answer: {student_answer}
Student's Self-Explanation: {self_explanation or "(none provided)"}

Score each dimension from 0.0 to 1.0:

1. **factual_accuracy**: Are the student's stated facts correct?
   - 1.0: All facts correct
   - 0.5: Mix of correct and incorrect
   - 0.0: Mostly incorrect

2. **self_awareness**: Does the student accurately assess their own knowledge?
   - 1.0: Knows what they know and what they do not know
   - 0.5: Some awareness of knowledge gaps
   - 0.0: Overconfident or completely unaware

3. **knowledge_boundaries**: Can the student identify the limits of their knowledge?
   - 1.0: Clearly identifies what is known vs. unknown
   - 0.5: Vague boundaries
   - 0.0: Cannot distinguish known from unknown

4. **explanation_quality**: Are the self-explanations coherent and insightful?
   - 1.0: Clear, logical reasoning that demonstrates understanding
   - 0.5: Some reasoning but shallow
   - 0.0: No meaningful explanation

Return ONLY a JSON object with this structure:
{{"factual_accuracy": {{"score": 0.9, "reasoning": "brief explanation"}},
"self_awareness": {{"score": 0.8, "reasoning": "brief explanation"}},
"knowledge_boundaries": {{"score": 0.7, "reasoning": "brief explanation"}},
"explanation_quality": {{"score": 0.85, "reasoning": "brief explanation"}}}}"""

        response = litellm.completion(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a metacognition evaluation expert. Return only valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        response_text = response.choices[0].message.content.strip()
        return self._parse_grading_response(response_text)

    def _parse_grading_response(self, response_text: str) -> MetacognitionScore:
        """Parse LLM grading response into MetacognitionScore."""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try markdown code block extraction
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                data = json.loads(json_str)
            else:
                raise

        dimensions = []
        for name in DIMENSION_NAMES:
            dim_data = data.get(name, {"score": 0.0, "reasoning": "Not evaluated"})
            score = float(dim_data.get("score", 0.0))
            # Clamp to valid range
            score = max(0.0, min(1.0, score))
            dimensions.append(
                Dimension(
                    name=name,
                    score=score,
                    reasoning=dim_data.get("reasoning", ""),
                )
            )

        overall = sum(d.score for d in dimensions) / len(dimensions) if dimensions else 0.0

        return MetacognitionScore(
            dimensions=dimensions,
            overall_score=overall,
            summary=self._generate_summary(dimensions, overall),
        )

    def _generate_summary(self, dimensions: list[Dimension], overall: float) -> str:
        """Generate human-readable summary from dimension scores."""
        if overall >= 0.8:
            level = "strong metacognition"
        elif overall >= 0.6:
            level = "moderate metacognition"
        elif overall >= 0.4:
            level = "limited metacognition"
        else:
            level = "weak metacognition"

        strongest = max(dimensions, key=lambda d: d.score)
        weakest = min(dimensions, key=lambda d: d.score)

        return (
            f"Student demonstrated {level} (overall: {overall:.2f}). "
            f"Strongest: {strongest.name} ({strongest.score:.2f}). "
            f"Weakest: {weakest.name} ({weakest.score:.2f})."
        )

    def _zero_score(self, reason: str) -> MetacognitionScore:
        """Return a zero score for error cases."""
        dimensions = [Dimension(name=name, score=0.0, reasoning=reason) for name in DIMENSION_NAMES]
        return MetacognitionScore(
            dimensions=dimensions,
            overall_score=0.0,
            summary=f"Grading failed: {reason}",
        )


@dataclass
class ReasoningTraceScore:
    """Score from reasoning trace analysis (progressive test suite interface).

    Maps metacognition dimensions to the trace-based naming convention:
    - effort_calibration: How well the agent calibrated reasoning effort
    - sufficiency_judgment: Whether the agent knew when it had enough info
    - search_quality: Quality of memory search and retrieval
    - self_correction: Ability to detect and correct errors
    - overall: Mean of all dimensions
    - details: Raw dimension data
    """

    effort_calibration: float
    sufficiency_judgment: float
    search_quality: float
    self_correction: float
    overall: float
    details: dict


def grade_metacognition(
    trace: dict | str,
    answer_score: float,
    level: str,
    model: str = "claude-sonnet-4-5-20250929",
) -> ReasoningTraceScore:
    """Grade metacognition from a reasoning trace (convenience function).

    Bridges the progressive_test_suite interface to MetacognitionGrader.

    Args:
        trace: Reasoning trace (dict or string) from agent execution
        answer_score: Score the answer received (0-1)
        level: Test level (L1-L6)
        model: LLM model for grading

    Returns:
        ReasoningTraceScore with dimension scores
    """
    if isinstance(trace, str):
        trace_text = trace
    else:
        trace_text = json.dumps(trace)

    grader = MetacognitionGrader(model=model)
    try:
        result = grader.grade(
            question=f"[{level}] Reasoning trace evaluation",
            expected_answer=f"Score: {answer_score:.2f}",
            student_answer=trace_text[:2000],
            self_explanation=trace_text[:2000],
        )

        # Map 4 dimensions to trace-based naming
        dim_map = {d.name: d.score for d in result.dimensions}
        return ReasoningTraceScore(
            effort_calibration=dim_map.get("self_awareness", 0.0),
            sufficiency_judgment=dim_map.get("knowledge_boundaries", 0.0),
            search_quality=dim_map.get("factual_accuracy", 0.0),
            self_correction=dim_map.get("explanation_quality", 0.0),
            overall=result.overall_score,
            details={
                "dimensions": {
                    d.name: {"score": d.score, "reasoning": d.reasoning} for d in result.dimensions
                },
                "summary": result.summary,
            },
        )
    except Exception as e:
        logger.warning("Metacognition grading failed: %s", e)
        return ReasoningTraceScore(
            effort_calibration=0.0,
            sufficiency_judgment=0.0,
            search_quality=0.0,
            self_correction=0.0,
            overall=0.0,
            details={"error": str(e)},
        )


__all__ = [
    "MetacognitionGrader",
    "MetacognitionScore",
    "Dimension",
    "grade_metacognition",
    "ReasoningTraceScore",
]
