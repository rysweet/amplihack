"""Long-horizon memory stress test for goal-seeking agents.

Philosophy:
- 1000-turn dialogue tests memory at scale (not just short-horizon recall)
- Deterministic data generation, reproducible results
- LLM-graded scoring on 5 dimensions per question
- Agent-agnostic: works with any LearningAgent-compatible interface

Public API:
    LongHorizonMemoryEval: Main evaluation class
    EvalResult: Per-question result with scores
    EvalReport: Aggregate report with breakdown by category

Usage:
    python -m amplihack.eval.long_horizon_memory --turns 100 --questions 20
    python -m amplihack.eval.long_horizon_memory --turns 1000 --questions 100
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .long_horizon_data import (
    GroundTruth,
    Question,
    generate_dialogue,
    generate_questions,
)

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """Score on a single dimension for a single question."""

    dimension: str
    score: float  # 0.0 to 1.0
    reasoning: str = ""


@dataclass
class EvalResult:
    """Result for a single question."""

    question_id: str
    question_text: str
    category: str
    expected_answer: str
    actual_answer: str
    dimensions: list[DimensionScore]
    overall_score: float  # Average of dimension scores
    grading_time_s: float = 0.0


@dataclass
class CategoryBreakdown:
    """Aggregate scores for a question category."""

    category: str
    num_questions: int
    avg_score: float
    min_score: float
    max_score: float
    dimension_averages: dict[str, float] = field(default_factory=dict)


@dataclass
class EvalReport:
    """Complete evaluation report."""

    num_turns: int
    num_questions: int
    total_facts_delivered: int
    learning_time_s: float
    questioning_time_s: float
    grading_time_s: float
    overall_score: float
    category_breakdown: list[CategoryBreakdown]
    results: list[EvalResult]
    memory_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "num_turns": self.num_turns,
            "num_questions": self.num_questions,
            "total_facts_delivered": self.total_facts_delivered,
            "learning_time_s": round(self.learning_time_s, 2),
            "questioning_time_s": round(self.questioning_time_s, 2),
            "grading_time_s": round(self.grading_time_s, 2),
            "overall_score": round(self.overall_score, 4),
            "category_breakdown": [
                {
                    "category": cb.category,
                    "num_questions": cb.num_questions,
                    "avg_score": round(cb.avg_score, 4),
                    "min_score": round(cb.min_score, 4),
                    "max_score": round(cb.max_score, 4),
                    "dimension_averages": {
                        k: round(v, 4) for k, v in cb.dimension_averages.items()
                    },
                }
                for cb in self.category_breakdown
            ],
            "results": [
                {
                    "question_id": r.question_id,
                    "question_text": r.question_text,
                    "category": r.category,
                    "expected_answer": r.expected_answer,
                    "actual_answer": r.actual_answer[:500],
                    "overall_score": round(r.overall_score, 4),
                    "dimensions": [
                        {
                            "dimension": d.dimension,
                            "score": round(d.score, 4),
                            "reasoning": d.reasoning[:200],
                        }
                        for d in r.dimensions
                    ],
                }
                for r in self.results
            ],
            "memory_stats": self.memory_stats,
        }


# Scoring dimensions
ALL_DIMENSIONS = [
    "factual_accuracy",
    "specificity",
    "temporal_awareness",
    "source_attribution",
    "confidence_calibration",
]


def _grade_with_llm(
    question: Question,
    actual_answer: str,
    dimensions: list[str],
    grader_model: str = "",
) -> list[DimensionScore]:
    """Grade an answer on multiple dimensions using LLM.

    Args:
        question: The question with expected answer
        actual_answer: Agent's actual answer
        dimensions: Which dimensions to score
        grader_model: Model to use for grading

    Returns:
        List of DimensionScore for each requested dimension
    """
    import anthropic  # type: ignore[import-untyped]

    if not grader_model:
        grader_model = os.environ.get("GRADER_MODEL", "claude-sonnet-4-5-20250929")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Return zero scores if no API key
        return [DimensionScore(dimension=d, score=0.0, reasoning="No API key") for d in dimensions]

    client = anthropic.Anthropic(api_key=api_key)

    dimension_descriptions = {
        "factual_accuracy": "Is the answer factually correct? Does it match the expected answer on key facts?",
        "specificity": "Does the answer include specific details (names, numbers, dates)?",
        "temporal_awareness": "Does the answer correctly distinguish current vs historical values?",
        "source_attribution": "Does the answer correctly attribute information to its source?",
        "confidence_calibration": "Does the answer express appropriate confidence/uncertainty?",
    }

    dims_text = "\n".join(
        f"- {d}: {dimension_descriptions.get(d, 'General quality')}" for d in dimensions
    )

    prompt = f"""Grade this answer on the following dimensions (0.0 to 1.0 each):

{dims_text}

Question: {question.text}
Category: {question.category}

Expected Answer: {question.expected_answer}

Actual Answer: {actual_answer}

Return ONLY a JSON object mapping each dimension to a score and reasoning:
{{
  "scores": {{
    "factual_accuracy": {{"score": 0.85, "reasoning": "..."}},
    ...
  }}
}}

Scoring guide:
- 1.0: Perfect or semantically equivalent
- 0.8-0.9: Correct main points, minor differences
- 0.5-0.7: Partially correct, missing key details
- 0.2-0.4: Some relevant content, significant gaps
- 0.0-0.1: Incorrect or irrelevant
"""

    try:
        message = client.messages.create(
            model=grader_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        # Parse JSON from response
        result = _extract_json(response_text)
        scores_dict = result.get("scores", result)

        dimension_scores = []
        for dim in dimensions:
            if dim in scores_dict:
                entry = scores_dict[dim]
                if isinstance(entry, dict):
                    dimension_scores.append(
                        DimensionScore(
                            dimension=dim,
                            score=float(entry.get("score", 0.0)),
                            reasoning=str(entry.get("reasoning", "")),
                        )
                    )
                elif isinstance(entry, (int, float)):
                    dimension_scores.append(
                        DimensionScore(
                            dimension=dim,
                            score=float(entry),
                            reasoning="",
                        )
                    )
                else:
                    dimension_scores.append(
                        DimensionScore(
                            dimension=dim,
                            score=0.0,
                            reasoning="Parse error",
                        )
                    )
            else:
                dimension_scores.append(
                    DimensionScore(
                        dimension=dim,
                        score=0.0,
                        reasoning="Not graded",
                    )
                )

        return dimension_scores

    except Exception as e:
        logger.warning("Grading failed for %s: %s", question.question_id, e)
        return [DimensionScore(dimension=d, score=0.0, reasoning=f"Error: {e}") for d in dimensions]


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response text."""
    import re

    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


class LongHorizonMemoryEval:
    """1000-turn dialogue memory stress test.

    Generates structured dialogue content, feeds it to an agent's learn method,
    then quizzes the agent on details from various points in the conversation.

    Args:
        num_turns: Number of dialogue turns (default 1000)
        num_questions: Number of quiz questions (default 100)
        seed: Random seed for reproducibility (default 42)

    Example:
        >>> from amplihack.agents.goal_seeking.learning_agent import LearningAgent
        >>> agent = LearningAgent("eval_agent", use_hierarchical=True)
        >>> eval_obj = LongHorizonMemoryEval(num_turns=100, num_questions=20)
        >>> report = eval_obj.run(agent)
        >>> print(f"Overall score: {report.overall_score:.2%}")
    """

    def __init__(
        self,
        num_turns: int = 1000,
        num_questions: int = 100,
        seed: int = 42,
    ):
        self.num_turns = num_turns
        self.num_questions = num_questions
        self.seed = seed
        self.ground_truth: GroundTruth | None = None
        self.questions: list[Question] = []

    def generate(self) -> tuple[GroundTruth, list[Question]]:
        """Generate dialogue and questions.

        Returns:
            Tuple of (GroundTruth, list[Question])
        """
        self.ground_truth = generate_dialogue(num_turns=self.num_turns, seed=self.seed)
        self.questions = generate_questions(self.ground_truth, num_questions=self.num_questions)
        return self.ground_truth, self.questions

    def run_dialogue(self, agent: Any, ground_truth: GroundTruth | None = None) -> float:
        """Feed all turns to the agent's learning method.

        Args:
            agent: Agent with learn_from_content(content) method
            ground_truth: Override ground truth (uses self.ground_truth if None)

        Returns:
            Time taken in seconds
        """
        gt = ground_truth or self.ground_truth
        if gt is None:
            raise ValueError("Must call generate() first or pass ground_truth")

        start = time.time()
        total = len(gt.turns)

        for i, turn in enumerate(gt.turns):
            if not turn.content or not turn.content.strip():
                continue

            try:
                agent.learn_from_content(turn.content)
            except Exception as e:
                logger.warning("Failed to learn turn %d: %s", i, e)

            if (i + 1) % 50 == 0 or i == total - 1:
                elapsed = time.time() - start
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                logger.info(
                    "Turn %d/%d (%.1f turns/s) - block: %s",
                    i + 1,
                    total,
                    rate,
                    turn.block_name,
                )

        elapsed = time.time() - start
        logger.info("Dialogue complete: %d turns in %.1fs", total, elapsed)
        return elapsed

    def evaluate(
        self,
        agent: Any,
        questions: list[Question] | None = None,
        grader_model: str = "",
    ) -> EvalReport:
        """Ask questions and grade responses.

        Args:
            agent: Agent with answer_question(question) method
            questions: Override questions (uses self.questions if None)
            grader_model: Model for LLM grading

        Returns:
            EvalReport with all results
        """
        qs = questions or self.questions
        if not qs:
            raise ValueError("Must call generate() first or pass questions")

        results: list[EvalResult] = []
        q_start = time.time()
        grade_total = 0.0

        for i, q in enumerate(qs):
            logger.info("Question %d/%d: %s", i + 1, len(qs), q.text[:60])

            # Get agent's answer
            try:
                answer = agent.answer_question(q.text)
                if isinstance(answer, tuple):
                    answer = answer[0]  # Handle (answer, trace) tuple
            except Exception as e:
                logger.warning("Agent failed to answer: %s", e)
                answer = f"Error: {e}"

            # Grade the answer
            grade_start = time.time()
            dimensions = q.scoring_dimensions or ["factual_accuracy"]
            dim_scores = _grade_with_llm(q, answer, dimensions, grader_model)
            grade_time = time.time() - grade_start
            grade_total += grade_time

            # Compute overall score as average of dimension scores
            overall = sum(d.score for d in dim_scores) / len(dim_scores) if dim_scores else 0.0

            result = EvalResult(
                question_id=q.question_id,
                question_text=q.text,
                category=q.category,
                expected_answer=q.expected_answer,
                actual_answer=answer if isinstance(answer, str) else str(answer),
                dimensions=dim_scores,
                overall_score=overall,
                grading_time_s=grade_time,
            )
            results.append(result)

            logger.info(
                "  Score: %.2f | Answer: %s",
                overall,
                (answer[:80] if isinstance(answer, str) else str(answer)[:80]) + "...",
            )

        q_elapsed = time.time() - q_start

        # Build category breakdown
        categories: dict[str, list[EvalResult]] = {}
        for r in results:
            categories.setdefault(r.category, []).append(r)

        breakdown = []
        for cat, cat_results in sorted(categories.items()):
            scores = [r.overall_score for r in cat_results]
            dim_avgs: dict[str, list[float]] = {}
            for r in cat_results:
                for d in r.dimensions:
                    dim_avgs.setdefault(d.dimension, []).append(d.score)

            breakdown.append(
                CategoryBreakdown(
                    category=cat,
                    num_questions=len(cat_results),
                    avg_score=sum(scores) / len(scores),
                    min_score=min(scores),
                    max_score=max(scores),
                    dimension_averages={k: sum(v) / len(v) for k, v in dim_avgs.items()},
                )
            )

        # Get memory stats
        mem_stats = {}
        try:
            mem_stats = agent.get_memory_stats()
        except Exception:
            pass

        # Count facts delivered
        total_facts = sum(
            len(t.facts) for t in (self.ground_truth.turns if self.ground_truth else [])
        )

        overall_score = sum(r.overall_score for r in results) / len(results) if results else 0.0

        return EvalReport(
            num_turns=self.num_turns,
            num_questions=len(results),
            total_facts_delivered=total_facts,
            learning_time_s=0.0,  # Set by caller
            questioning_time_s=q_elapsed,
            grading_time_s=grade_total,
            overall_score=overall_score,
            category_breakdown=breakdown,
            results=results,
            memory_stats=mem_stats,
        )

    def run(self, agent: Any, grader_model: str = "") -> EvalReport:
        """Run the complete evaluation: generate, learn, quiz, grade.

        Args:
            agent: Agent with learn_from_content and answer_question methods
            grader_model: Model for LLM grading

        Returns:
            Complete EvalReport
        """
        logger.info(
            "Starting long-horizon memory eval: %d turns, %d questions",
            self.num_turns,
            self.num_questions,
        )

        # Step 1: Generate data
        self.generate()
        logger.info(
            "Generated %d turns, %d questions",
            len(self.ground_truth.turns) if self.ground_truth else 0,
            len(self.questions),
        )

        # Step 2: Feed dialogue to agent
        learning_time = self.run_dialogue(agent)

        # Step 3: Quiz and grade
        report = self.evaluate(agent, grader_model=grader_model)
        report.learning_time_s = learning_time

        logger.info(
            "Evaluation complete: overall=%.2f%%, learning=%.1fs, grading=%.1fs",
            report.overall_score * 100,
            report.learning_time_s,
            report.grading_time_s,
        )

        return report


def _print_report(report: EvalReport) -> None:
    """Print a human-readable summary of the evaluation report."""
    print("\n" + "=" * 70)
    print("LONG-HORIZON MEMORY EVALUATION REPORT")
    print("=" * 70)
    print(f"Turns: {report.num_turns} | Questions: {report.num_questions}")
    print(f"Facts delivered: {report.total_facts_delivered}")
    print(f"Learning time: {report.learning_time_s:.1f}s")
    print(f"Question+Grading time: {report.questioning_time_s:.1f}s")
    print(f"\nOVERALL SCORE: {report.overall_score:.2%}")
    print()

    print("CATEGORY BREAKDOWN:")
    print("-" * 70)
    print(f"{'Category':<25} {'Avg':>8} {'Min':>8} {'Max':>8} {'Count':>6}")
    print("-" * 70)
    for cb in report.category_breakdown:
        print(
            f"{cb.category:<25} {cb.avg_score:>7.2%} {cb.min_score:>7.2%} "
            f"{cb.max_score:>7.2%} {cb.num_questions:>6}"
        )
    print("-" * 70)

    print("\nDIMENSION AVERAGES BY CATEGORY:")
    for cb in report.category_breakdown:
        if cb.dimension_averages:
            dims = ", ".join(f"{k}: {v:.2%}" for k, v in sorted(cb.dimension_averages.items()))
            print(f"  {cb.category}: {dims}")

    print("\nMEMORY STATS:")
    for k, v in report.memory_stats.items():
        print(f"  {k}: {v}")

    # Show worst-performing questions
    print("\nWORST 5 QUESTIONS:")
    sorted_results = sorted(report.results, key=lambda r: r.overall_score)
    for r in sorted_results[:5]:
        print(f"  [{r.overall_score:.2%}] {r.question_text[:60]}")
        print(f"    Expected: {r.expected_answer[:80]}")
        print(f"    Got: {r.actual_answer[:80]}")
        print()


def main() -> None:
    """CLI entry point for long-horizon memory evaluation."""
    parser = argparse.ArgumentParser(
        description="Long-horizon memory stress test for goal-seeking agents"
    )
    parser.add_argument(
        "--turns", type=int, default=1000, help="Number of dialogue turns (default: 1000)"
    )
    parser.add_argument(
        "--questions", type=int, default=100, help="Number of quiz questions (default: 100)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="/tmp/memory-eval", help="Output directory for results"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="LLM model for the agent (default: env EVAL_MODEL or claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "--grader-model",
        type=str,
        default="",
        help="LLM model for grading (default: env GRADER_MODEL or claude-sonnet-4-5-20250929)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--use-hierarchical",
        action="store_true",
        default=True,
        help="Use hierarchical memory (default: True)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set model if provided
    agent_model = args.model or os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929")

    # Create agent
    logger.info(
        "Creating LearningAgent with model=%s, hierarchical=%s", agent_model, args.use_hierarchical
    )

    from amplihack.agents.goal_seeking.learning_agent import LearningAgent

    db_path = output_dir / "memory_db"
    agent = LearningAgent(
        agent_name="long_horizon_eval",
        model=agent_model,
        storage_path=db_path,
        use_hierarchical=args.use_hierarchical,
    )

    try:
        # Run evaluation
        evaluator = LongHorizonMemoryEval(
            num_turns=args.turns,
            num_questions=args.questions,
            seed=args.seed,
        )

        report = evaluator.run(agent, grader_model=args.grader_model)

        # Print report
        _print_report(report)

        # Save JSON report
        report_path = output_dir / "report.json"
        with open(report_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info("Report saved to %s", report_path)

        # Save ground truth for analysis
        if evaluator.ground_truth:
            gt_path = output_dir / "ground_truth.json"
            gt_data = {
                "num_turns": len(evaluator.ground_truth.turns),
                "turns_with_facts": sum(1 for t in evaluator.ground_truth.turns if t.facts),
                "total_facts": sum(len(t.facts) for t in evaluator.ground_truth.turns),
                "current_values": evaluator.ground_truth.current_values,
                "superseded_count": sum(
                    len(v) for v in evaluator.ground_truth.superseded_values.values()
                ),
                "block_distribution": {},
            }
            for t in evaluator.ground_truth.turns:
                gt_data["block_distribution"][t.block_name] = (
                    gt_data["block_distribution"].get(t.block_name, 0) + 1
                )
            with open(gt_path, "w") as f:
                json.dump(gt_data, f, indent=2)
            logger.info("Ground truth saved to %s", gt_path)

    finally:
        agent.close()


if __name__ == "__main__":
    main()


__all__ = [
    "LongHorizonMemoryEval",
    "EvalResult",
    "EvalReport",
    "CategoryBreakdown",
    "DimensionScore",
]
