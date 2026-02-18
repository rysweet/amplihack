"""Progressive test suite for agent learning evaluation.

Runs 6 levels of increasing difficulty:
- L1: Single source direct recall (baseline)
- L2: Multi-source synthesis
- L3: Temporal reasoning
- L4: Procedural learning
- L5: Contradiction handling
- L6: Incremental learning

Philosophy: Comprehensive evaluation from simple to complex,
measuring learning capability across multiple dimensions.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .grader import grade_answer
from .test_levels import ALL_LEVELS, TestLevel


@dataclass
class ProgressiveConfig:
    """Configuration for progressive test suite."""

    output_dir: str
    agent_name: str
    levels_to_run: list[str] | None = None  # None = run all
    memory_backend: str = "amplihack-memory-lib"


@dataclass
class LevelResult:
    """Result for a single level."""

    level_id: str
    level_name: str
    success: bool
    scores: dict | None = None
    error_message: str | None = None


@dataclass
class ProgressiveResult:
    """Result of entire progressive test suite."""

    success: bool
    level_results: list[LevelResult]
    overall_scores: dict | None = None
    error_message: str | None = None


def _extract_json_line(stdout: str) -> str:
    """Extract the JSON object line from subprocess stdout.

    Subprocess stdout may contain litellm warnings, deprecation notices,
    or other non-JSON lines mixed in. This finds the line that is a valid
    JSON object starting with '{'.

    Args:
        stdout: Raw subprocess stdout

    Returns:
        The JSON line, or '{}' if none found
    """
    # Search from last line backward (JSON output is printed last by agent_subprocess)
    for line in reversed(stdout.strip().splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                json.loads(stripped)
                return stripped
            except json.JSONDecodeError:
                continue
    return "{}"


def run_learning_subprocess(articles: list, agent_name: str) -> tuple[bool, str]:
    """Run learning phase as subprocess.

    Args:
        articles: List of article dicts to learn from
        agent_name: Agent identifier

    Returns:
        Tuple of (success, error_message_or_data)
    """
    learning_input = [
        {
            "url": a.url,
            "title": a.title,
            "content": a.content,
            "published": a.published,
            "metadata": a.metadata or {},
        }
        for a in articles
    ]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "amplihack.eval.agent_subprocess",
            "--phase",
            "learning",
            "--agent-name",
            agent_name,
        ],
        input=json.dumps(learning_input),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, result.stderr

    return True, _extract_json_line(result.stdout)


def run_testing_subprocess(questions: list, agent_name: str) -> tuple[bool, str]:
    """Run testing phase as subprocess.

    Args:
        questions: List of question dicts to answer
        agent_name: Agent identifier

    Returns:
        Tuple of (success, error_message_or_data)
    """
    testing_input = [
        {
            "question": q.question,
            "expected_answer": q.expected_answer,
            "level": q.level,
        }
        for q in questions
    ]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "amplihack.eval.agent_subprocess",
            "--phase",
            "testing",
            "--agent-name",
            agent_name,
        ],
        input=json.dumps(testing_input),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return False, result.stderr

    return True, _extract_json_line(result.stdout)


def run_single_level(level: TestLevel, config: ProgressiveConfig, level_dir: Path) -> LevelResult:
    """Run evaluation for a single level.

    Args:
        level: Test level definition
        config: Progressive configuration
        level_dir: Output directory for this level

    Returns:
        LevelResult with scores and status
    """
    level_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Handle incremental learning (Level 6)
        if level.requires_update_handling:
            # Phase 1: Learn from initial articles
            initial_articles = [
                a for a in level.articles if (a.metadata or {}).get("phase") == "initial"
            ]
            success, data = run_learning_subprocess(initial_articles, config.agent_name)
            if not success:
                return LevelResult(
                    level_id=level.level_id,
                    level_name=level.level_name,
                    success=False,
                    error_message=f"Learning phase 1 failed: {data}",
                )

            learning1_data = json.loads(data)
            with open(level_dir / "learning_phase1.log", "w") as f:
                json.dump(learning1_data, f, indent=2)

            # Phase 2: Learn from update articles
            update_articles = [
                a for a in level.articles if (a.metadata or {}).get("phase") == "update"
            ]
            success, data = run_learning_subprocess(update_articles, config.agent_name)
            if not success:
                return LevelResult(
                    level_id=level.level_id,
                    level_name=level.level_name,
                    success=False,
                    error_message=f"Learning phase 2 failed: {data}",
                )

            learning2_data = json.loads(data)
            with open(level_dir / "learning_phase2.log", "w") as f:
                json.dump(learning2_data, f, indent=2)

        else:
            # Standard learning: all articles at once
            success, data = run_learning_subprocess(level.articles, config.agent_name)
            if not success:
                return LevelResult(
                    level_id=level.level_id,
                    level_name=level.level_name,
                    success=False,
                    error_message=f"Learning phase failed: {data}",
                )

            learning_data = json.loads(data)
            with open(level_dir / "learning_phase.log", "w") as f:
                json.dump(learning_data, f, indent=2)

        # Testing phase
        success, data = run_testing_subprocess(level.questions, config.agent_name)
        if not success:
            return LevelResult(
                level_id=level.level_id,
                level_name=level.level_name,
                success=False,
                error_message=f"Testing phase failed: {data}",
            )

        testing_data = json.loads(data)
        with open(level_dir / "testing_phase.log", "w") as f:
            json.dump(testing_data, f, indent=2)

        # Grade answers
        all_grades = []
        for i, answer_data in enumerate(testing_data["answers"]):
            question = level.questions[i]

            grade = grade_answer(
                question=question.question,
                expected=question.expected_answer,
                actual=answer_data["answer"],
                level=question.level,
            )

            all_grades.append(
                {
                    "question": question.question,
                    "level": question.level,
                    "reasoning_type": question.reasoning_type,
                    "expected": question.expected_answer,
                    "actual": answer_data["answer"],
                    "score": grade.score,
                    "reasoning": grade.reasoning,
                }
            )

        # Calculate scores
        if all_grades:
            avg_score = sum(g["score"] for g in all_grades) / len(all_grades)
            scores = {"average": avg_score, "count": len(all_grades), "details": all_grades}
        else:
            scores = {"average": 0.0, "count": 0, "details": []}

        # Save grading results
        with open(level_dir / "scores.json", "w") as f:
            json.dump(scores, f, indent=2)

        return LevelResult(
            level_id=level.level_id, level_name=level.level_name, success=True, scores=scores
        )

    except Exception as e:
        return LevelResult(
            level_id=level.level_id,
            level_name=level.level_name,
            success=False,
            error_message=str(e),
        )


def run_progressive_suite(config: ProgressiveConfig) -> ProgressiveResult:
    """Run complete progressive test suite.

    Args:
        config: Progressive suite configuration

    Returns:
        ProgressiveResult with all level results and overall scores
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which levels to run
    if config.levels_to_run:
        levels_to_run = [lvl for lvl in ALL_LEVELS if lvl.level_id in config.levels_to_run]
    else:
        levels_to_run = ALL_LEVELS

    # Run each level
    level_results = []
    for level in levels_to_run:
        print(f"\n{'=' * 70}")
        print(f"Running {level.level_id}: {level.level_name}")
        print(f"{'=' * 70}")
        print(f"Description: {level.description}")
        print(f"Articles: {len(level.articles)}, Questions: {len(level.questions)}")

        level_dir = output_dir / level.level_id
        result = run_single_level(level, config, level_dir)
        level_results.append(result)

        if result.success and result.scores:
            print(f"✓ {level.level_id} completed: {result.scores['average']:.2%} average score")
        else:
            print(f"✗ {level.level_id} failed: {result.error_message}")

    # Calculate overall scores
    successful_levels = [r for r in level_results if r.success]

    if successful_levels:
        overall_scores = {}

        # Average score per level
        for result in successful_levels:
            overall_scores[result.level_id] = {
                "average": result.scores["average"],
                "count": result.scores["count"],
            }

        # Overall average across all levels
        all_scores = [r.scores["average"] for r in successful_levels]
        overall_scores["overall"] = sum(all_scores) / len(all_scores)

        # Success rate (levels passed)
        overall_scores["levels_passed"] = len(successful_levels)
        overall_scores["levels_total"] = len(level_results)
        overall_scores["pass_rate"] = len(successful_levels) / len(level_results)

    else:
        overall_scores = None

    # Save summary
    summary = {
        "overall_scores": overall_scores,
        "level_results": [
            {
                "level_id": r.level_id,
                "level_name": r.level_name,
                "success": r.success,
                "average_score": r.scores["average"] if r.success else None,
                "error": r.error_message if not r.success else None,
            }
            for r in level_results
        ],
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Determine overall success
    all_success = all(r.success for r in level_results)

    return ProgressiveResult(
        success=all_success,
        level_results=level_results,
        overall_scores=overall_scores,
        error_message=None if all_success else "Some levels failed",
    )


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Progressive Agent Learning Test Suite (Levels 1-6)"
    )
    parser.add_argument(
        "--output-dir", default="./eval_progressive", help="Output directory for results"
    )
    parser.add_argument(
        "--agent-name", default="progressive-test-agent", help="Agent name for memory isolation"
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=["L1", "L2", "L3", "L4", "L5", "L6"],
        help="Specific levels to run (default: all)",
    )
    parser.add_argument(
        "--memory-backend", default="amplihack-memory-lib", help="Memory backend to use"
    )

    args = parser.parse_args()

    config = ProgressiveConfig(
        output_dir=args.output_dir,
        agent_name=args.agent_name,
        levels_to_run=args.levels,
        memory_backend=args.memory_backend,
    )

    print("=" * 70)
    print("PROGRESSIVE AGENT LEARNING TEST SUITE")
    print("=" * 70)
    print(f"Output directory: {config.output_dir}")
    print(f"Agent name: {config.agent_name}")
    if config.levels_to_run:
        print(f"Levels to run: {', '.join(config.levels_to_run)}")
    else:
        print("Levels to run: All (L1-L6)")
    print("=" * 70)

    result = run_progressive_suite(config)

    # Print summary
    print("\n" + "=" * 70)
    print("PROGRESSIVE TEST SUITE SUMMARY")
    print("=" * 70)

    if result.success:
        print("\n✓ All levels completed successfully\n")
    else:
        print(f"\n✗ Some levels failed: {result.error_message}\n")

    if result.overall_scores:
        print("Scores by Level:")
        for level_result in result.level_results:
            if level_result.success and level_result.scores:
                score = level_result.scores["average"]
                count = level_result.scores["count"]
                print(
                    f"  {level_result.level_id} ({level_result.level_name}): "
                    f"{score:.2%} ({count} questions)"
                )
            else:
                print(f"  {level_result.level_id} ({level_result.level_name}): FAILED")

        print(f"\nOverall Average: {result.overall_scores['overall']:.2%}")
        print(
            f"Levels Passed: {result.overall_scores['levels_passed']}/{result.overall_scores['levels_total']}"
        )
        print(f"Pass Rate: {result.overall_scores['pass_rate']:.2%}")

    print(f"\nDetailed results saved to: {config.output_dir}")

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "run_progressive_suite",
    "run_single_level",
    "ProgressiveConfig",
    "ProgressiveResult",
    "LevelResult",
]
