"""Evaluation harness orchestrator.

Coordinates learning → testing workflow with subprocess isolation.
Philosophy: Simple coordinator, delegates actual work to subprocesses.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .grader import grade_answer
from .multi_source_collector import collect_news
from .quiz_generator import generate_quiz


@dataclass
class HarnessConfig:
    """Configuration for harness run."""

    news_file: str
    output_dir: str
    agent_name: str
    memory_backend: str = "amplihack-memory-lib"


@dataclass
class HarnessResult:
    """Result of harness execution."""

    success: bool
    scores: dict | None = None
    error_message: str | None = None


def run_harness(config: HarnessConfig) -> HarnessResult:
    """Run complete evaluation harness.

    Args:
        config: Harness configuration

    Returns:
        HarnessResult with success status and scores
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Collect news
        with open(config.news_file) as f:
            websearch_data = json.load(f)

        articles = collect_news(websearch_data)

        # Step 2: Generate quiz
        quiz = generate_quiz(articles)

        # Save quiz
        quiz_file = output_dir / "quiz.json"
        with open(quiz_file, "w") as f:
            quiz_data = [
                {
                    "question": q.question,
                    "expected_answer": q.expected_answer,
                    "level": q.level,
                    "source_urls": q.source_urls,
                }
                for q in quiz
            ]
            json.dump(quiz_data, f, indent=2)

        # Step 3: Learning phase (subprocess)
        learning_input = [
            {
                "url": a.url,
                "title": a.title,
                "content": a.content,
                "published": a.published,
            }
            for a in articles
        ]

        learning_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack.eval.agent_subprocess",
                "--phase",
                "learning",
                "--agent-name",
                config.agent_name,
            ],
            input=json.dumps(learning_input),
            capture_output=True,
            text=True,
        )

        if learning_result.returncode != 0:
            return HarnessResult(success=False, error_message=learning_result.stderr)

        learning_data = json.loads(learning_result.stdout)

        # Save learning phase log
        with open(output_dir / "learning_phase.log", "w") as f:
            json.dump(learning_data, f, indent=2)

        # Step 4: Testing phase (subprocess)
        testing_input = [
            {
                "question": q.question,
                "expected_answer": q.expected_answer,
                "level": q.level,
            }
            for q in quiz
        ]

        testing_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack.eval.agent_subprocess",
                "--phase",
                "testing",
                "--agent-name",
                config.agent_name,
            ],
            input=json.dumps(testing_input),
            capture_output=True,
            text=True,
        )

        if testing_result.returncode != 0:
            return HarnessResult(success=False, error_message=testing_result.stderr)

        testing_data = json.loads(testing_result.stdout)

        # Save testing phase log
        with open(output_dir / "testing_phase.log", "w") as f:
            json.dump(testing_data, f, indent=2)

        # Step 5: Grade answers
        scores = {}
        all_grades = []

        for i, answer_data in enumerate(testing_data["answers"]):
            question_data = testing_input[i]

            grade = grade_answer(
                question=question_data["question"],
                expected=question_data["expected_answer"],
                actual=answer_data["answer"],
                level=question_data["level"],
            )

            all_grades.append(
                {
                    "question": question_data["question"],
                    "level": question_data["level"],
                    "expected": question_data["expected_answer"],
                    "actual": answer_data["answer"],
                    "score": grade.score,
                    "reasoning": grade.reasoning,
                }
            )

        # Calculate scores by level
        for level in ["L1", "L2", "L3", "L4"]:
            level_grades = [g for g in all_grades if g["level"] == level]
            if level_grades:
                avg_score = sum(g["score"] for g in level_grades) / len(level_grades)
                scores[level] = {"average": avg_score, "count": len(level_grades)}

        # Overall score
        if all_grades:
            overall = sum(g["score"] for g in all_grades) / len(all_grades)
            scores["overall"] = overall

        # Save grading results
        with open(output_dir / "scores.json", "w") as f:
            json.dump({"scores": scores, "details": all_grades}, f, indent=2)

        return HarnessResult(success=True, scores=scores)

    except Exception as e:
        return HarnessResult(success=False, error_message=str(e))


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Learning Evaluation Harness")
    parser.add_argument("--news-file", required=True, help="WebSearch results JSON file")
    parser.add_argument("--output-dir", default="./eval_results", help="Output directory")
    parser.add_argument(
        "--agent-name", default="test-agent", help="Agent name for memory isolation"
    )
    parser.add_argument(
        "--memory-backend", default="amplihack-memory-lib", help="Memory backend to use"
    )

    args = parser.parse_args()

    config = HarnessConfig(
        news_file=args.news_file,
        output_dir=args.output_dir,
        agent_name=args.agent_name,
        memory_backend=args.memory_backend,
    )

    print("=" * 70)
    print("AGENT LEARNING EVALUATION HARNESS")
    print("=" * 70)

    result = run_harness(config)

    if result.success:
        print("\n[SUCCESS] Evaluation completed\n")
        if result.scores:
            print("Scores by Level:")
            for level, data in result.scores.items():
                if level != "overall":
                    print(f"  {level}: {data['average']:.2%} ({data['count']} questions)")
            print(f"\nOverall: {result.scores.get('overall', 0):.2%}")
        print(f"\nResults saved to: {config.output_dir}")
    else:
        print(f"\n[FAILED] {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = ["run_harness", "HarnessConfig", "HarnessResult"]
