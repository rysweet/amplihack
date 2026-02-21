"""Progressive test suite for agent learning evaluation.

Runs 12 levels of increasing difficulty:
- L1: Single source direct recall (baseline)
- L2: Multi-source synthesis
- L3: Temporal reasoning
- L4: Procedural learning
- L5: Contradiction handling
- L6: Incremental learning
- L7: Teacher-student knowledge transfer
- L8: Metacognition
- L9: Causal reasoning
- L10: Counterfactual reasoning
- L11: Novel skill acquisition
- L12: Far transfer

Philosophy: Comprehensive evaluation from simple to complex,
measuring learning capability across multiple dimensions.
"""

import json
import statistics
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from .grader import grade_answer
from .metacognition_grader import grade_metacognition
from .test_levels import ADVANCED_LEVELS, ALL_LEVELS, TestLevel


@dataclass
class ProgressiveConfig:
    """Configuration for progressive test suite."""

    output_dir: str
    agent_name: str
    levels_to_run: list[str] | None = None  # None = run all
    memory_backend: str = "amplihack-memory-lib"
    sdk: str = "mini"  # SDK type: mini, claude, copilot, microsoft
    grader_votes: int = 1  # Number of grading votes per question (1=single, 3=majority)


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


def run_learning_subprocess(articles: list, agent_name: str, sdk: str = "mini") -> tuple[bool, str]:
    """Run learning phase as subprocess.

    Args:
        articles: List of article dicts to learn from
        agent_name: Agent identifier
        sdk: SDK type to pass to agent subprocess

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

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack.eval.agent_subprocess",
                "--phase",
                "learning",
                "--agent-name",
                agent_name,
                "--sdk",
                sdk,
            ],
            input=json.dumps(learning_input),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Learning phase timed out after 600 seconds"

    if result.returncode != 0:
        return False, result.stderr

    return True, _extract_json_line(result.stdout)


def run_testing_subprocess(questions: list, agent_name: str, sdk: str = "mini") -> tuple[bool, str]:
    """Run testing phase as subprocess.

    Args:
        questions: List of question dicts to answer
        agent_name: Agent identifier
        sdk: SDK type to pass to agent subprocess

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

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack.eval.agent_subprocess",
                "--phase",
                "testing",
                "--agent-name",
                agent_name,
                "--sdk",
                sdk,
            ],
            input=json.dumps(testing_input),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Testing phase timed out after 600 seconds"

    if result.returncode != 0:
        return False, result.stderr

    return True, _extract_json_line(result.stdout)


def _isolate_memory_for_level(agent_name: str, level_id: str) -> str:
    """Create an isolated agent name for each level to avoid cross-level interference.

    Each level gets a unique agent name which maps to a separate memory database.
    This prevents facts from L1 leaking into L2, etc.

    Args:
        agent_name: Base agent name
        level_id: Level identifier (L1, L2, etc.)

    Returns:
        Isolated agent name string
    """
    return f"{agent_name}_{level_id}_{int(time.time())}"


def run_l7_teaching_eval(
    level: TestLevel, config: ProgressiveConfig, level_dir: Path
) -> LevelResult:
    """Run L7 teaching evaluation using the TeachingSession framework.

    L7 is special: it uses a teacher-student multi-turn dialogue rather than
    single-pass learning+testing. The teacher learns the articles, then teaches
    a student agent through multiple turns. The student is then tested.

    Args:
        level: L7 test level definition
        config: Progressive configuration
        level_dir: Output directory for L7

    Returns:
        LevelResult with scores and status
    """
    level_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Phase 1: Learn articles (same as other levels)
        agent_name = _isolate_memory_for_level(config.agent_name, "L7")
        success, data = run_learning_subprocess(level.articles, agent_name, sdk=config.sdk)
        if not success:
            return LevelResult(
                level_id=level.level_id,
                level_name=level.level_name,
                success=False,
                error_message=f"L7 learning phase failed: {data}",
            )

        learning_data = json.loads(data)
        with open(level_dir / "learning_phase.log", "w") as f:
            json.dump(learning_data, f, indent=2)

        # Phase 2: Run teaching session (teacher teaches student)
        # Build knowledge base from the articles for the teacher
        knowledge_base = []
        for article in level.articles:
            knowledge_base.append(f"Title: {article.title}")
            knowledge_base.append(article.content)

        # Run teaching session as subprocess to isolate state
        teaching_result = _run_teaching_subprocess(knowledge_base, agent_name)
        with open(level_dir / "teaching_session.log", "w") as f:
            json.dump(teaching_result, f, indent=2)

        # Phase 3: Test the student (same agent, already has knowledge from teaching)
        success, data = run_testing_subprocess(level.questions, agent_name, sdk=config.sdk)
        if not success:
            return LevelResult(
                level_id=level.level_id,
                level_name=level.level_name,
                success=False,
                error_message=f"L7 testing phase failed: {data}",
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
                num_votes=config.grader_votes,
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
                    "metacognition": None,
                }
            )

        if all_grades:
            avg_score = sum(g["score"] for g in all_grades) / len(all_grades)
            scores = {
                "average": avg_score,
                "count": len(all_grades),
                "details": all_grades,
                "metacognition": None,
                "teaching_session": teaching_result,
            }
        else:
            scores = {"average": 0.0, "count": 0, "details": [], "metacognition": None}

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


def _run_teaching_subprocess(knowledge_base: list[str], agent_name: str) -> dict:
    """Run a teaching session in a subprocess.

    The teaching session creates a teacher-student dialogue where the teacher
    uses the knowledge base to teach the student, who then stores the knowledge
    in memory for later testing.

    Args:
        knowledge_base: List of knowledge strings (article titles and content)
        agent_name: Agent identifier (shared with testing phase)

    Returns:
        Dict with teaching session results
    """
    teaching_input = {
        "knowledge_base": knowledge_base,
        "agent_name": agent_name,
        "max_turns": 4,
    }

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplihack.eval.teaching_subprocess",
                "--agent-name",
                agent_name,
            ],
            input=json.dumps(teaching_input),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "turns": 0, "error": "Teaching session timed out"}

    if result.returncode != 0:
        return {"status": "error", "turns": 0, "error": result.stderr[:500]}

    try:
        output = _extract_json_line(result.stdout)
        return json.loads(output)
    except (json.JSONDecodeError, Exception):
        return {"status": "completed", "turns": 0, "raw_output": result.stdout[:500]}


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

    # Use L7 teaching path for teacher-student levels
    if level.level_id == "L7":
        return run_l7_teaching_eval(level, config, level_dir)

    # Memory isolation: each level gets a unique agent name
    isolated_agent_name = _isolate_memory_for_level(config.agent_name, level.level_id)

    try:
        # Handle incremental learning (Level 6)
        if level.requires_update_handling:
            # Phase 1: Learn from initial articles
            initial_articles = [
                a for a in level.articles if (a.metadata or {}).get("phase") == "initial"
            ]
            success, data = run_learning_subprocess(
                initial_articles, isolated_agent_name, sdk=config.sdk
            )
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
            success, data = run_learning_subprocess(
                update_articles, isolated_agent_name, sdk=config.sdk
            )
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
            success, data = run_learning_subprocess(
                level.articles, isolated_agent_name, sdk=config.sdk
            )
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
        success, data = run_testing_subprocess(level.questions, isolated_agent_name, sdk=config.sdk)
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
                num_votes=config.grader_votes,
            )

            # Grade metacognition if trace available
            metacog = None
            trace = answer_data.get("reasoning_trace")
            if trace:
                metacog_grade = grade_metacognition(
                    trace=trace,
                    answer_score=grade.score,
                    level=question.level,
                )
                metacog = {
                    "effort_calibration": metacog_grade.effort_calibration,
                    "sufficiency_judgment": metacog_grade.sufficiency_judgment,
                    "search_quality": metacog_grade.search_quality,
                    "self_correction": metacog_grade.self_correction,
                    "overall": metacog_grade.overall,
                    "details": metacog_grade.details,
                }

            all_grades.append(
                {
                    "question": question.question,
                    "level": question.level,
                    "reasoning_type": question.reasoning_type,
                    "expected": question.expected_answer,
                    "actual": answer_data["answer"],
                    "score": grade.score,
                    "reasoning": grade.reasoning,
                    "metacognition": metacog,
                }
            )

        # Calculate scores
        if all_grades:
            avg_score = sum(g["score"] for g in all_grades) / len(all_grades)

            # Calculate metacognition averages if available
            metacog_scores = [g["metacognition"] for g in all_grades if g.get("metacognition")]
            metacog_avg = None
            if metacog_scores:
                metacog_avg = {
                    "effort_calibration": sum(m["effort_calibration"] for m in metacog_scores)
                    / len(metacog_scores),
                    "sufficiency_judgment": sum(m["sufficiency_judgment"] for m in metacog_scores)
                    / len(metacog_scores),
                    "search_quality": sum(m["search_quality"] for m in metacog_scores)
                    / len(metacog_scores),
                    "self_correction": sum(m["self_correction"] for m in metacog_scores)
                    / len(metacog_scores),
                    "overall": sum(m["overall"] for m in metacog_scores) / len(metacog_scores),
                }

            scores = {
                "average": avg_score,
                "count": len(all_grades),
                "details": all_grades,
                "metacognition": metacog_avg,
            }
        else:
            scores = {"average": 0.0, "count": 0, "details": [], "metacognition": None}

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
    from .test_levels import NOVEL_SKILL_LEVELS, TEACHER_STUDENT_LEVELS, TRANSFER_LEVELS

    all_available = (
        ALL_LEVELS + TEACHER_STUDENT_LEVELS + ADVANCED_LEVELS + NOVEL_SKILL_LEVELS + TRANSFER_LEVELS
    )
    if config.levels_to_run:
        levels_to_run = [lvl for lvl in all_available if lvl.level_id in config.levels_to_run]
    else:
        levels_to_run = ALL_LEVELS  # Default: L1-L6 only (L8-L10 need --advanced)

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
        "sdk": config.sdk,
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


@dataclass
class ParallelResult:
    """Result of a parallel eval run (multiple runs aggregated)."""

    num_runs: int
    median_scores: dict[str, float]
    all_run_results: list[ProgressiveResult]
    per_run_scores: dict[str, list[float]] = field(default_factory=dict)


def _run_single_suite(args: tuple) -> ProgressiveResult:
    """Run a single suite invocation (used as ProcessPoolExecutor target).

    Args:
        args: Tuple of (run_id, base_output_dir, levels_to_run, memory_backend, sdk, grader_votes)

    Returns:
        ProgressiveResult for this run
    """
    run_id, base_output_dir, levels_to_run, memory_backend, sdk, grader_votes = args
    agent_name = f"agent_{run_id}_{int(time.time())}"
    output_dir = str(Path(base_output_dir) / f"run_{run_id}")

    config = ProgressiveConfig(
        output_dir=output_dir,
        agent_name=agent_name,
        levels_to_run=levels_to_run,
        memory_backend=memory_backend,
        sdk=sdk,
        grader_votes=grader_votes,
    )

    return run_progressive_suite(config)


def run_parallel_suite(
    num_runs: int,
    base_output_dir: str,
    levels_to_run: list[str] | None = None,
    memory_backend: str = "amplihack-memory-lib",
    max_workers: int = 4,
    sdk: str = "mini",
    grader_votes: int = 1,
) -> ParallelResult:
    """Run the progressive suite multiple times in parallel and report medians.

    Args:
        num_runs: Number of parallel runs
        base_output_dir: Base output directory (each run gets a subdirectory)
        levels_to_run: Optional list of level IDs to run
        memory_backend: Memory backend to use
        max_workers: Maximum concurrent processes (capped at 4)
        sdk: SDK type to use
        grader_votes: Number of grading votes per question

    Returns:
        ParallelResult with median scores across all runs
    """
    max_workers = min(max_workers, 4)  # Cap at 4 to avoid API overload
    workers = min(max_workers, num_runs)

    print(f"Starting {num_runs} parallel runs (max {workers} concurrent)...")

    run_args = [
        (i, base_output_dir, levels_to_run, memory_backend, sdk, grader_votes)
        for i in range(num_runs)
    ]

    all_results: list[ProgressiveResult] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_run_single_suite, args): args[0] for args in run_args}
        for future in as_completed(futures):
            run_id = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                print(f"  Run {run_id} completed (success={result.success})")
            except Exception as e:
                print(f"  Run {run_id} failed with exception: {e}")
                all_results.append(
                    ProgressiveResult(
                        success=False,
                        level_results=[],
                        overall_scores=None,
                        error_message=str(e),
                    )
                )

    # Collect per-level scores across all runs
    per_run_scores: dict[str, list[float]] = {}
    for result in all_results:
        if not result.level_results:
            continue
        for lr in result.level_results:
            if lr.success and lr.scores:
                per_run_scores.setdefault(lr.level_id, []).append(lr.scores["average"])

    # Compute median per level
    median_scores: dict[str, float] = {}
    for level_id, scores in sorted(per_run_scores.items()):
        median_scores[level_id] = statistics.median(scores)

    # Overall median
    if median_scores:
        median_scores["overall"] = statistics.median(median_scores[k] for k in median_scores)

    return ParallelResult(
        num_runs=num_runs,
        median_scores=median_scores,
        all_run_results=all_results,
        per_run_scores=per_run_scores,
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
        choices=["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "L12"],
        help="Specific levels to run (default: L1-L6, use --advanced for L8-L12)",
    )
    parser.add_argument(
        "--advanced",
        action="store_true",
        help="Include advanced levels (L8-L10: metacognition, causal, counterfactual)",
    )
    parser.add_argument(
        "--memory-backend", default="amplihack-memory-lib", help="Memory backend to use"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=0,
        metavar="N",
        help="Run suite N times in parallel and report median scores (max 4 concurrent)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=0,
        metavar="N",
        help="Alias for --parallel. Run suite N times and report median scores. "
        "Recommended: --runs 3 for stable results on high-variance levels (L2, L5, L9, L10, L11).",
    )
    parser.add_argument(
        "--sdk",
        default="mini",
        choices=["mini", "claude", "copilot", "microsoft"],
        help="SDK type to evaluate (default: mini). All SDKs use the same LearningAgent "
        "for learning/answering but validate SDK agent creation.",
    )
    parser.add_argument(
        "--grader-votes",
        type=int,
        default=1,
        metavar="N",
        help="Number of grading votes per question (default: 1). "
        "Use 3 for majority-vote grading to reduce noise on ambiguous answers.",
    )

    args = parser.parse_args()

    # --runs is an alias for --parallel; prefer --runs if both given
    if args.runs > 0:
        args.parallel = args.runs

    # If --advanced is set, include L8-L10 in levels to run
    if args.advanced and not args.levels:
        args.levels = ["L1", "L2", "L3", "L4", "L5", "L6", "L8", "L9", "L10"]
    elif args.advanced and args.levels:
        # Add advanced levels to explicit selection
        for lvl in ["L8", "L9", "L10"]:
            if lvl not in args.levels:
                args.levels.append(lvl)

    # Parallel mode
    if args.parallel > 0:
        print("=" * 70)
        print("PROGRESSIVE AGENT LEARNING TEST SUITE - PARALLEL MODE")
        print("=" * 70)
        print(f"Number of runs: {args.parallel}")
        print(f"Output directory: {args.output_dir}")
        if args.levels:
            print(f"Levels to run: {', '.join(args.levels)}")
        else:
            print("Levels to run: All (L1-L6)")
        print("=" * 70)

        par_result = run_parallel_suite(
            num_runs=args.parallel,
            base_output_dir=args.output_dir,
            levels_to_run=args.levels,
            memory_backend=args.memory_backend,
            sdk=args.sdk,
            grader_votes=args.grader_votes,
        )

        # Print parallel summary
        print("\n" + "=" * 70)
        print("PARALLEL TEST SUITE SUMMARY")
        print("=" * 70)
        print(f"Completed {par_result.num_runs} runs\n")

        print("Median Scores by Level:")
        for level_id in sorted(k for k in par_result.median_scores if k != "overall"):
            scores = par_result.per_run_scores.get(level_id, [])
            median = par_result.median_scores[level_id]
            scores_str = ", ".join(f"{s:.2%}" for s in scores)
            print(f"  {level_id}: {median:.2%}  (runs: {scores_str})")

        if "overall" in par_result.median_scores:
            print(f"\nOverall Median: {par_result.median_scores['overall']:.2%}")

        print(f"\nDetailed results saved to: {args.output_dir}")

        # Save parallel summary
        summary_path = Path(args.output_dir) / "parallel_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump(
                {
                    "num_runs": par_result.num_runs,
                    "median_scores": par_result.median_scores,
                    "per_run_scores": {
                        k: [round(s, 4) for s in v] for k, v in par_result.per_run_scores.items()
                    },
                },
                f,
                indent=2,
            )

        return

    # Single run mode
    config = ProgressiveConfig(
        output_dir=args.output_dir,
        agent_name=args.agent_name,
        levels_to_run=args.levels,
        memory_backend=args.memory_backend,
        sdk=args.sdk,
        grader_votes=args.grader_votes,
    )

    print("=" * 70)
    print("PROGRESSIVE AGENT LEARNING TEST SUITE")
    print("=" * 70)
    print(f"Output directory: {config.output_dir}")
    print(f"Agent name: {config.agent_name}")
    print(f"SDK: {config.sdk}")
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
    "run_parallel_suite",
    "run_single_level",
    "ProgressiveConfig",
    "ProgressiveResult",
    "ParallelResult",
    "LevelResult",
]
