"""Teaching evaluation layer for domain agents.

Bridges domain agents with the TeachingSession framework to evaluate
how well agents can teach their domain skills to students.

Two evaluation paths:
1. Domain agent's own teach() method - grades structured output
2. Full TeachingSession with LLM student - grades multi-turn dialogue

Philosophy: Teaching ability measures depth of understanding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, TeachingResult


@dataclass
class TeachingDimensionScore:
    """Score for a single teaching dimension.

    Attributes:
        dimension: Name of the dimension
        score: Grade from 0.0 to 1.0
        weight: Weight in composite score
        details: How the grade was determined
    """

    dimension: str
    score: float
    weight: float
    details: str


@dataclass
class DomainTeachingEvalResult:
    """Complete teaching evaluation result for a domain agent.

    Attributes:
        agent_name: Agent being evaluated
        domain: Domain name
        topic: What was taught
        student_level: Student level used
        dimension_scores: Per-dimension scores
        composite_score: Weighted overall score
        teaching_result: Raw teaching result from agent
    """

    agent_name: str
    domain: str
    topic: str
    student_level: str
    dimension_scores: list[TeachingDimensionScore]
    composite_score: float
    teaching_result: TeachingResult
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "topic": self.topic,
            "student_level": self.student_level,
            "composite_score": round(self.composite_score, 3),
            "dimensions": [
                {
                    "dimension": d.dimension,
                    "score": round(d.score, 3),
                    "weight": d.weight,
                    "details": d.details,
                }
                for d in self.dimension_scores
            ],
        }


class DomainTeachingEvaluator:
    """Evaluates a domain agent's teaching ability.

    Uses the agent's teach() method and grades the output across
    4 dimensions: clarity, completeness, student performance, adaptivity.

    Example:
        >>> agent = CodeReviewAgent("reviewer")
        >>> evaluator = DomainTeachingEvaluator(agent)
        >>> result = evaluator.evaluate("security review")
        >>> print(f"Teaching: {result.composite_score:.0%}")
    """

    # Dimension weights
    WEIGHTS = {
        "clarity": 0.25,
        "completeness": 0.25,
        "student_performance": 0.30,
        "adaptivity": 0.20,
    }

    def __init__(self, agent: DomainAgent):
        """Initialize evaluator.

        Args:
            agent: Domain agent to evaluate
        """
        self.agent = agent

    def evaluate(
        self,
        topic: str,
        student_level: str = "beginner",
    ) -> DomainTeachingEvalResult:
        """Run teaching evaluation.

        Args:
            topic: Topic for the agent to teach
            student_level: Student level

        Returns:
            DomainTeachingEvalResult with scores
        """
        # Run the agent's teach method
        teaching_result = self.agent.teach(topic=topic, student_level=student_level)

        # Grade each dimension
        dimension_scores = [
            self._grade_clarity(teaching_result),
            self._grade_completeness(teaching_result),
            self._grade_student_performance(teaching_result),
            self._grade_adaptivity(teaching_result),
        ]

        # Calculate composite
        composite = sum(d.score * d.weight for d in dimension_scores)

        return DomainTeachingEvalResult(
            agent_name=self.agent.agent_name,
            domain=self.agent.domain,
            topic=topic,
            student_level=student_level,
            dimension_scores=dimension_scores,
            composite_score=composite,
            teaching_result=teaching_result,
        )

    def _grade_clarity(self, result: TeachingResult) -> TeachingDimensionScore:
        """Grade clarity of instruction."""
        instruction = result.instruction
        score = 0.0
        details_parts = []

        if not instruction or not instruction.strip():
            return TeachingDimensionScore(
                dimension="clarity",
                score=0.0,
                weight=self.WEIGHTS["clarity"],
                details="No instruction provided",
            )

        # Length check
        words = instruction.split()
        if len(words) >= 50:
            score += 0.25
            details_parts.append(f"Sufficient length ({len(words)} words)")
        elif len(words) >= 20:
            score += 0.15
            details_parts.append(f"Moderate length ({len(words)} words)")
        else:
            details_parts.append(f"Too short ({len(words)} words)")

        # Structure check
        has_structure = any(m in instruction for m in ["1.", "2.", "- ", "**"])
        if has_structure:
            score += 0.25
            details_parts.append("Has structure")

        # Example check
        has_examples = any(
            m in instruction.lower() for m in ["example", "for instance", "bad:", "good:", "e.g."]
        )
        if has_examples:
            score += 0.25
            details_parts.append("Includes examples")

        # Domain terms check
        domain_terms = _get_domain_terms(self.agent.domain)
        terms_found = sum(1 for t in domain_terms if t.lower() in instruction.lower())
        if terms_found >= 3:
            score += 0.25
            details_parts.append(f"Uses {terms_found} domain terms")
        elif terms_found >= 1:
            score += 0.15
            details_parts.append(f"Uses {terms_found} domain terms")

        return TeachingDimensionScore(
            dimension="clarity",
            score=min(1.0, score),
            weight=self.WEIGHTS["clarity"],
            details=" | ".join(details_parts),
        )

    def _grade_completeness(self, result: TeachingResult) -> TeachingDimensionScore:
        """Grade completeness of teaching."""
        score = 0.0
        details_parts = []

        # Lesson plan
        if result.lesson_plan and len(result.lesson_plan.strip()) > 20:
            plan_items = [ln for ln in result.lesson_plan.split("\n") if ln.strip()]
            if len(plan_items) >= 4:
                score += 0.3
                details_parts.append(f"Lesson plan: {len(plan_items)} items")
            elif len(plan_items) >= 2:
                score += 0.2
                details_parts.append(f"Lesson plan: {len(plan_items)} items")
        else:
            details_parts.append("Weak lesson plan")

        # Multi-section instruction
        if result.instruction:
            sections = result.instruction.count("\n\n")
            if sections >= 3:
                score += 0.25
                details_parts.append(f"{sections + 1} instruction sections")
            elif sections >= 1:
                score += 0.15

        # Answers provided
        if result.agent_answers:
            substantive = sum(1 for a in result.agent_answers if len(a) > 20)
            if substantive >= 2:
                score += 0.25
                details_parts.append(f"{substantive} substantive answers")
            elif substantive >= 1:
                score += 0.15

        # Practice material
        if result.student_attempt and len(result.student_attempt.strip()) > 20:
            score += 0.2
            details_parts.append("Practice material present")

        return TeachingDimensionScore(
            dimension="completeness",
            score=min(1.0, score),
            weight=self.WEIGHTS["completeness"],
            details=" | ".join(details_parts),
        )

    def _grade_student_performance(self, result: TeachingResult) -> TeachingDimensionScore:
        """Grade student performance on practice."""
        attempt = result.student_attempt
        score = 0.0
        details_parts = []

        if not attempt or not attempt.strip():
            return TeachingDimensionScore(
                dimension="student_performance",
                score=0.0,
                weight=self.WEIGHTS["student_performance"],
                details="No student attempt",
            )

        words = attempt.split()
        if len(words) >= 30:
            score += 0.3
            details_parts.append(f"Substantive attempt ({len(words)} words)")
        elif len(words) >= 15:
            score += 0.2

        # Finding indicators
        finding_markers = ["found", "identified", "detected", "issue", "finding", "action"]
        has_findings = any(m in attempt.lower() for m in finding_markers)
        if has_findings:
            score += 0.35
            details_parts.append("Shows findings")

        # Structure indicators
        structure_markers = ["- ", "* ", "1.", ":", "Summary", "Action"]
        has_structure = any(m in attempt for m in structure_markers)
        if has_structure:
            score += 0.35
            details_parts.append("Structured output")

        return TeachingDimensionScore(
            dimension="student_performance",
            score=min(1.0, score),
            weight=self.WEIGHTS["student_performance"],
            details=" | ".join(details_parts),
        )

    def _grade_adaptivity(self, result: TeachingResult) -> TeachingDimensionScore:
        """Grade agent's adaptivity to student needs."""
        score = 0.0
        details_parts = []

        # Different answers to different questions
        if len(result.agent_answers) >= 2:
            if result.agent_answers[0] != result.agent_answers[1]:
                score += 0.35
                details_parts.append("Varied responses")

        # Answer quality
        if result.agent_answers:
            avg_len = sum(len(a) for a in result.agent_answers) / len(result.agent_answers)
            if avg_len > 100:
                score += 0.3
                details_parts.append(f"Detailed answers (avg {avg_len:.0f} chars)")
            elif avg_len > 50:
                score += 0.2

        # Level awareness
        if result.lesson_plan and any(
            lvl in result.lesson_plan.lower()
            for lvl in ["beginner", "intermediate", "advanced", "student level"]
        ):
            score += 0.35
            details_parts.append("Level-aware")

        return TeachingDimensionScore(
            dimension="adaptivity",
            score=min(1.0, score),
            weight=self.WEIGHTS["adaptivity"],
            details=" | ".join(details_parts),
        )


def _get_domain_terms(domain: str) -> list[str]:
    """Get domain-specific terms for instruction quality checking."""
    terms = {
        "code_review": [
            "bug",
            "security",
            "vulnerability",
            "style",
            "naming",
            "convention",
            "injection",
            "refactor",
            "test",
            "pattern",
        ],
        "meeting_synthesizer": [
            "action item",
            "decision",
            "speaker",
            "transcript",
            "summary",
            "deadline",
            "owner",
            "follow-up",
        ],
        "document_creator": [
            "template",
            "format",
            "section",
            "outline",
            "audience",
        ],
        "data_analysis": [
            "statistics",
            "trend",
            "correlation",
            "dataset",
            "insight",
        ],
        "project_planning": [
            "task",
            "milestone",
            "dependency",
            "risk",
            "timeline",
        ],
    }
    return terms.get(domain, [])


def run_combined_eval(
    agent: DomainAgent,
    teaching_topic: str,
    domain_weight: float = 0.6,
    teaching_weight: float = 0.4,
) -> dict[str, Any]:
    """Run combined domain + teaching evaluation.

    Args:
        agent: Domain agent to evaluate
        teaching_topic: Topic for teaching evaluation
        domain_weight: Weight for domain eval score
        teaching_weight: Weight for teaching eval score

    Returns:
        Dictionary with combined scores
    """
    from amplihack.eval.domain_eval_harness import DomainEvalHarness

    # Run domain evaluation
    domain_harness = DomainEvalHarness(agent)
    domain_report = domain_harness.run()

    # Run teaching evaluation
    teaching_evaluator = DomainTeachingEvaluator(agent)
    teaching_result = teaching_evaluator.evaluate(topic=teaching_topic)

    # Combine scores
    combined_score = (
        domain_report.overall_score * domain_weight
        + teaching_result.composite_score * teaching_weight
    )

    return {
        "agent_name": agent.agent_name,
        "domain": agent.domain,
        "domain_score": round(domain_report.overall_score, 3),
        "teaching_score": round(teaching_result.composite_score, 3),
        "combined_score": round(combined_score, 3),
        "domain_weight": domain_weight,
        "teaching_weight": teaching_weight,
        "domain_details": domain_report.to_dict(),
        "teaching_details": teaching_result.to_dict(),
    }


__all__ = [
    "DomainTeachingEvaluator",
    "DomainTeachingEvalResult",
    "TeachingDimensionScore",
    "run_combined_eval",
]
