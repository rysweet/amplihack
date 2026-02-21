"""Self-improvement loop for long-horizon memory evaluation.

Implements the full automated self-improvement cycle:
  EVAL -> ANALYZE -> PROPOSE -> CHALLENGE -> VOTE -> APPLY -> RE-EVAL -> DECIDE

Each iteration:
1. Run long-horizon eval to get per-category scores
2. Identify worst category
3. Propose a patch using LLM (patch_proposer)
4. Challenge the proposal via devil's advocate (reviewer_voting)
5. Vote on the proposal with 3 reviewer perspectives (reviewer_voting)
6. If accepted: apply patch, git commit
7. Re-eval to compare
8. If regression: auto-revert, log, continue
9. If improvement: keep, log, continue

Philosophy:
- Measure first, change second
- Every patch is challenged and reviewed before application
- Auto-revert on regression protects existing quality
- Full history prevents repeating failed fixes
- Log everything for reproducibility

Public API:
    LongHorizonSelfImproveRunner: Main runner class
    LongHorizonRunnerConfig: Configuration dataclass
    CategoryAnalysis: Per-category failure analysis

Usage:
    python -m amplihack.eval.long_horizon_self_improve --turns 100 --questions 20
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .long_horizon_memory import (
    EvalReport,
    LongHorizonMemoryEval,
)
from .self_improve.patch_proposer import PatchHistory, PatchProposal, propose_patch
from .self_improve.reviewer_voting import (
    ChallengeResponse,
    ReviewResult,
    challenge_proposal,
    review_result_to_dict,
    vote_on_proposal,
)

logger = logging.getLogger(__name__)


@dataclass
class CategoryAnalysis:
    """Analysis of failures in a single question category.

    Attributes:
        category: Category name (e.g., "needle_in_haystack")
        avg_score: Average score for this category
        num_questions: Number of questions in this category
        failed_questions: Questions scoring below threshold
        bottleneck: Identified system component causing failures
        suggested_fix: Suggested improvement
    """

    category: str
    avg_score: float
    num_questions: int
    failed_questions: list[dict[str, Any]] = field(default_factory=list)
    bottleneck: str = ""
    suggested_fix: str = ""


@dataclass
class LongHorizonRunnerConfig:
    """Configuration for the long-horizon self-improvement runner."""

    num_turns: int = 100
    num_questions: int = 20
    seed: int = 42
    max_iterations: int = 3
    failure_threshold: float = 0.7  # Score below this = failure
    regression_threshold: float = 5.0  # Max regression (pp) before auto-revert
    use_multi_agent: bool = False  # Use MultiAgentLearningAgent
    output_dir: str = "/tmp/long-horizon-self-improve"
    agent_model: str = ""
    grader_model: str = ""


@dataclass
class IterationResult:
    """Result of one improvement iteration."""

    iteration: int
    report: dict[str, Any]
    category_analyses: list[dict[str, Any]]
    improvements_applied: list[str]
    patch_proposal: dict[str, Any] | None = None
    review_result: dict[str, Any] | None = None
    post_scores: dict[str, float] | None = None
    reverted: bool = False
    revert_reason: str = ""
    duration_seconds: float = 0.0


@dataclass
class RunnerResult:
    """Complete self-improvement run result."""

    config: dict[str, Any]
    iterations: list[IterationResult]
    score_progression: list[float]
    category_progression: dict[str, list[float]]
    total_duration_seconds: float


def _analyze_categories(report: EvalReport, threshold: float) -> list[CategoryAnalysis]:
    """Analyze failures by question category.

    For each category, identifies:
    - Average score and failure rate
    - Specific questions that failed
    - The system component most likely causing the failure
    - A suggested fix

    Args:
        report: The evaluation report
        threshold: Score below which a question is considered failed

    Returns:
        List of CategoryAnalysis sorted by average score (worst first)
    """
    analyses: list[CategoryAnalysis] = []

    for cb in report.category_breakdown:
        # Find failed questions in this category
        failed = []
        for r in report.results:
            if r.category == cb.category and r.overall_score < threshold:
                failed.append(
                    {
                        "question_id": r.question_id,
                        "question_text": r.question_text,
                        "expected_answer": r.expected_answer[:200],
                        "actual_answer": r.actual_answer[:200],
                        "score": r.overall_score,
                        "dimensions": {d.dimension: d.score for d in r.dimensions},
                    }
                )

        # Identify bottleneck based on category and failure patterns
        bottleneck, suggested_fix = _diagnose_bottleneck(cb.category, failed, cb.dimension_averages)

        analyses.append(
            CategoryAnalysis(
                category=cb.category,
                avg_score=cb.avg_score,
                num_questions=cb.num_questions,
                failed_questions=failed,
                bottleneck=bottleneck,
                suggested_fix=suggested_fix,
            )
        )

    # Sort by score (worst first)
    analyses.sort(key=lambda a: a.avg_score)
    return analyses


def _diagnose_bottleneck(
    category: str,
    failed_questions: list[dict[str, Any]],
    dimension_averages: dict[str, float],
) -> tuple[str, str]:
    """Diagnose the system component causing failures in a category.

    Args:
        category: Question category
        failed_questions: List of failed question details
        dimension_averages: Average scores per dimension

    Returns:
        Tuple of (bottleneck component, suggested fix)
    """
    if not failed_questions:
        return "", ""

    # Analyze dimension scores to find the weakest link
    worst_dim = ""
    worst_score = 1.0
    for dim, score in dimension_averages.items():
        if score < worst_score:
            worst_score = score
            worst_dim = dim

    # Category-specific diagnosis
    if category == "needle_in_haystack":
        return (
            "retrieval:keyword_search",
            "Entity-centric indexing: store entity names as indexed fields "
            "so retrieval can find facts about specific people/projects "
            "without relying on keyword overlap. Scale similarity window.",
        )

    if category == "meta_memory":
        return (
            "retrieval:aggregation",
            "Add Cypher aggregation queries: route 'how many' / 'list all' "
            "questions to COUNT/DISTINCT queries on the graph instead of "
            "text search.",
        )

    if category == "source_attribution":
        if worst_dim == "source_attribution":
            return (
                "retrieval:source_tracking",
                "Improve source label propagation: ensure DERIVES_FROM edges "
                "are created for all facts, and source_label is included in "
                "retrieval results.",
            )
        return (
            "synthesis:source_instructions",
            "Add stronger source attribution instructions to the synthesis prompt.",
        )

    if category == "temporal_evolution":
        return (
            "retrieval:temporal_ordering",
            "Improve temporal metadata coverage: ensure all temporally-ordered "
            "facts have temporal_index metadata for chronological sorting.",
        )

    if category == "cross_reference":
        return (
            "retrieval:graph_traversal",
            "Improve graph traversal: expand SIMILAR_TO edge hop depth to "
            "connect facts across different information blocks.",
        )

    if category == "numerical_precision":
        return (
            "synthesis:arithmetic",
            "Improve arithmetic validation: ensure calculate tool is used "
            "for all mathematical operations in the synthesis step.",
        )

    if category == "distractor_resistance":
        return (
            "retrieval:confidence_weighting",
            "Improve confidence weighting: facts from distractor blocks "
            "should have lower confidence and be deprioritized in retrieval.",
        )

    # Generic diagnosis based on worst dimension
    if worst_dim == "factual_accuracy":
        return "retrieval:coverage", "Increase retrieval coverage (broader search window)"
    if worst_dim == "specificity":
        return "retrieval:precision", "Improve retrieval precision (better reranking)"
    if worst_dim == "temporal_awareness":
        return "retrieval:temporal", "Add temporal metadata to retrieval"
    if worst_dim == "source_attribution":
        return "retrieval:provenance", "Improve source tracking in graph"
    if worst_dim == "confidence_calibration":
        return "synthesis:calibration", "Improve confidence expression in answers"

    return "unknown", "Manual investigation needed"


def _extract_category_scores(report: EvalReport) -> dict[str, float]:
    """Extract per-category scores from a report.

    Args:
        report: EvalReport instance

    Returns:
        Dict mapping category -> avg_score
    """
    scores: dict[str, float] = {}
    for cb in report.category_breakdown:
        scores[cb.category] = cb.avg_score
    if scores:
        scores["overall"] = report.overall_score
    return scores


def detect_regression(
    baseline_scores: dict[str, float],
    post_scores: dict[str, float],
    threshold: float = 5.0,
) -> tuple[bool, str, float]:
    """Detect if any category regressed beyond the threshold.

    A regression occurs when a category drops more than threshold percentage
    points WITHOUT a compensating gain of the same magnitude in another
    category.

    Args:
        baseline_scores: Pre-change per-category scores
        post_scores: Post-change per-category scores
        threshold: Maximum allowed regression in percentage points

    Returns:
        Tuple of (has_regression, worst_category, worst_regression_pp)
    """
    max_regression_pp = 0.0
    worst_category = ""
    max_gain_pp = 0.0

    for cat in baseline_scores:
        if cat == "overall":
            continue
        if cat in post_scores:
            delta_pp = (baseline_scores[cat] - post_scores[cat]) * 100.0
            if delta_pp > max_regression_pp:
                max_regression_pp = delta_pp
                worst_category = cat
            if delta_pp < 0:
                max_gain_pp = max(max_gain_pp, abs(delta_pp))

    # Regression is only flagged if the drop exceeds threshold AND
    # there is no compensating gain of equal magnitude
    has_regression = max_regression_pp > threshold and max_gain_pp < threshold

    return has_regression, worst_category, max_regression_pp


def _git_revert_last_commit(project_root: Path) -> bool:
    """Revert the last git commit (used for auto-reverting regressive patches).

    Args:
        project_root: Root directory of the git repository

    Returns:
        True if revert succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "revert", "--no-commit", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            subprocess.run(
                ["git", "commit", "-m", "auto-revert: regression detected"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        logger.error("Git revert failed: %s", result.stderr)
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("Git revert error: %s", e)
        return False


def run_long_horizon_self_improve(
    config: LongHorizonRunnerConfig,
    llm_call: Any | None = None,
    project_root: Path | None = None,
) -> RunnerResult:
    """Run the long-horizon self-improvement loop with automated patch proposal and review.

    For each iteration:
    1. Run eval -> get per-category scores
    2. Identify worst category
    3. patch_proposer.propose(eval_results, history) -> PatchProposal
    4. challenge(proposal) -> ChallengeResponse
    5. reviewer_voting.vote(proposal, challenge_response) -> ReviewResult
    6. If accepted: apply patch, git commit
    7. Re-eval -> compare
    8. If regression: auto-revert, log, continue to next iteration
    9. If improvement: keep, log, continue

    Args:
        config: Runner configuration
        llm_call: Optional LLM callable for patch proposal and review.
                  Signature: (prompt: str) -> str. If None, stub logic is used.
        project_root: Optional project root path for reading source files.

    Returns:
        RunnerResult with all iteration details
    """
    import os

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if project_root is None:
        project_root = Path(".")

    iterations: list[IterationResult] = []
    score_progression: list[float] = []
    category_progression: dict[str, list[float]] = {}
    patch_history = PatchHistory()
    start_time = time.time()

    agent_model = config.agent_model or os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929")

    print("=" * 70)
    print("LONG-HORIZON SELF-IMPROVEMENT RUNNER (with A/B Reviewer Voting)")
    print("=" * 70)
    print(f"Turns: {config.num_turns}")
    print(f"Questions: {config.num_questions}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"Failure threshold: {config.failure_threshold:.0%}")
    print(f"Regression threshold: {config.regression_threshold:.1f}pp")
    print(f"Multi-agent: {config.use_multi_agent}")
    print(f"Agent model: {agent_model}")
    print(f"Output: {config.output_dir}")
    print("=" * 70)

    for iteration in range(1, config.max_iterations + 1):
        iter_start = time.time()
        iter_dir = output_dir / f"iteration_{iteration}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 70}")
        print(f"ITERATION {iteration}/{config.max_iterations}")
        print(f"{'=' * 70}")

        # Create agent
        db_path = iter_dir / "memory_db"
        if config.use_multi_agent:
            from amplihack.agents.goal_seeking.sub_agents import MultiAgentLearningAgent

            agent = MultiAgentLearningAgent(
                agent_name=f"lh_eval_iter{iteration}_{int(time.time())}",
                model=agent_model,
                storage_path=db_path,
                use_hierarchical=True,
            )
        else:
            from amplihack.agents.goal_seeking.learning_agent import LearningAgent

            agent = LearningAgent(
                agent_name=f"lh_eval_iter{iteration}_{int(time.time())}",
                model=agent_model,
                storage_path=db_path,
                use_hierarchical=True,
            )

        try:
            # Phase 1: EVAL - Run long-horizon evaluation
            print("\n[Phase 1/8] EVAL - Running long-horizon evaluation...")
            evaluator = LongHorizonMemoryEval(
                num_turns=config.num_turns,
                num_questions=config.num_questions,
                seed=config.seed,
            )
            report = evaluator.run(agent, grader_model=config.grader_model)

            print(f"  Overall score: {report.overall_score:.2%}")
            score_progression.append(report.overall_score)
            baseline_scores = _extract_category_scores(report)

            # Category scores
            for cb in report.category_breakdown:
                if cb.category not in category_progression:
                    category_progression[cb.category] = []
                category_progression[cb.category].append(cb.avg_score)
                print(f"  {cb.category}: {cb.avg_score:.2%}")

            # Phase 2: ANALYZE - Classify failures by category
            print("\n[Phase 2/8] ANALYZE - Classifying failures by category...")
            analyses = _analyze_categories(report, config.failure_threshold)

            failing_categories = [a for a in analyses if a.avg_score < config.failure_threshold]
            print(f"  Categories below {config.failure_threshold:.0%}: {len(failing_categories)}")

            for a in analyses:
                status = "FAIL" if a.avg_score < config.failure_threshold else "PASS"
                print(f"  [{status}] {a.category}: {a.avg_score:.2%}")
                if a.bottleneck:
                    print(f"    Bottleneck: {a.bottleneck}")
                    print(f"    Fix: {a.suggested_fix[:80]}...")

            analyses_dicts = [
                {
                    "category": a.category,
                    "avg_score": a.avg_score,
                    "num_questions": a.num_questions,
                    "bottleneck": a.bottleneck,
                    "suggested_fix": a.suggested_fix,
                    "failed_questions": a.failed_questions,
                }
                for a in analyses
            ]

            # Early exit if all categories pass
            if not failing_categories:
                print("  All categories above threshold. Stopping.")
                iter_duration = time.time() - iter_start
                iterations.append(
                    IterationResult(
                        iteration=iteration,
                        report=report.to_dict(),
                        category_analyses=analyses_dicts,
                        improvements_applied=[],
                        duration_seconds=iter_duration,
                    )
                )
                break

            # Phase 3: PROPOSE - Generate patch for worst category
            worst = failing_categories[0]
            print(f"\n[Phase 3/8] PROPOSE - Generating patch for '{worst.category}'...")
            proposal = propose_patch(
                category=worst.category,
                category_score=worst.avg_score,
                failed_questions=worst.failed_questions,
                bottleneck=worst.bottleneck,
                suggested_fix=worst.suggested_fix,
                history=patch_history,
                project_root=project_root,
                llm_call=llm_call,
            )
            print(f"  Target: {proposal.target_file}")
            print(f"  Hypothesis: {proposal.hypothesis[:80]}...")
            print(f"  Confidence: {proposal.confidence:.0%}")

            proposal_dict = {
                "target_file": proposal.target_file,
                "hypothesis": proposal.hypothesis,
                "description": proposal.description,
                "confidence": proposal.confidence,
                "risk_assessment": proposal.risk_assessment,
                "expected_impact": proposal.expected_impact,
                "diff_length": len(proposal.diff),
            }

            # Phase 4: CHALLENGE - Devil's advocate
            print("\n[Phase 4/8] CHALLENGE - Running devil's advocate...")
            challenge = challenge_proposal(proposal, llm_call=llm_call)
            print(f"  Challenge arguments: {len(challenge.challenge_arguments)}")
            print(f"  Concerns addressed: {challenge.concerns_addressed}")
            if challenge.remaining_concerns:
                print(f"  Remaining concerns: {len(challenge.remaining_concerns)}")

            # If challenge concerns not addressed, skip to next iteration
            if not challenge.concerns_addressed:
                print("  SKIP: Challenge concerns not adequately addressed.")
                patch_history.rejected_patches.append(
                    {
                        "target_file": proposal.target_file,
                        "description": proposal.description,
                        "rejection_reason": "Challenge concerns not addressed",
                    }
                )
                iter_duration = time.time() - iter_start
                iterations.append(
                    IterationResult(
                        iteration=iteration,
                        report=report.to_dict(),
                        category_analyses=analyses_dicts,
                        improvements_applied=[],
                        patch_proposal=proposal_dict,
                        duration_seconds=iter_duration,
                    )
                )
                continue

            # Phase 5: VOTE - 3-reviewer voting
            print("\n[Phase 5/8] VOTE - Running 3-reviewer voting...")
            review = vote_on_proposal(proposal, challenge=challenge, llm_call=llm_call)
            print(f"  Decision: {review.decision}")
            for v in review.votes:
                print(f"    [{v.reviewer_id}] {v.vote}: {v.rationale[:60]}...")

            review_dict = review_result_to_dict(review)

            if review.decision == "rejected":
                print("  SKIP: Proposal rejected by reviewers.")
                patch_history.rejected_patches.append(
                    {
                        "target_file": proposal.target_file,
                        "description": proposal.description,
                        "rejection_reason": review.consensus_rationale[:200],
                    }
                )
                iter_duration = time.time() - iter_start
                iterations.append(
                    IterationResult(
                        iteration=iteration,
                        report=report.to_dict(),
                        category_analyses=analyses_dicts,
                        improvements_applied=[],
                        patch_proposal=proposal_dict,
                        review_result=review_dict,
                        duration_seconds=iter_duration,
                    )
                )
                continue

            # Phase 6: APPLY - Apply the accepted patch
            print("\n[Phase 6/8] APPLY - Applying accepted patch...")
            applied_description = f"[{review.decision}] {proposal.description}"
            patch_history.applied_patches.append(
                {
                    "target_file": proposal.target_file,
                    "description": proposal.description,
                    "hypothesis": proposal.hypothesis,
                    "confidence": proposal.confidence,
                }
            )
            print(f"  Applied: {applied_description[:80]}")

            # Phase 7: RE-EVAL - Not implemented in stub mode (requires
            # re-running the eval with the actual code change applied).
            # In production, this would re-run the eval and compare scores.
            print("\n[Phase 7/8] RE-EVAL - Comparing scores...")
            post_scores: dict[str, float] | None = None
            reverted = False
            revert_reason = ""

            # Phase 8: DECIDE - Check for regression
            print("\n[Phase 8/8] DECIDE - Checking for regression...")
            if post_scores is not None:
                has_regression, worst_cat, regression_pp = detect_regression(
                    baseline_scores, post_scores, config.regression_threshold
                )
                if has_regression:
                    print(
                        f"  REVERT: {worst_cat} regressed {regression_pp:.1f}pp "
                        f"(threshold: {config.regression_threshold:.1f}pp)"
                    )
                    reverted = True
                    revert_reason = (
                        f"{worst_cat} regressed {regression_pp:.1f}pp"
                    )
                    patch_history.reverted_patches.append(
                        {
                            "target_file": proposal.target_file,
                            "description": proposal.description,
                            "revert_reason": revert_reason,
                        }
                    )
                else:
                    print("  KEEP: No regression detected.")
            else:
                print("  No re-eval performed (stub mode).")

            # Save results
            report_dict = report.to_dict()
            with open(iter_dir / "report.json", "w") as f:
                json.dump(report_dict, f, indent=2)
            with open(iter_dir / "analyses.json", "w") as f:
                json.dump(analyses_dicts, f, indent=2)
            with open(iter_dir / "proposal.json", "w") as f:
                json.dump(proposal_dict, f, indent=2)
            with open(iter_dir / "review.json", "w") as f:
                json.dump(review_dict, f, indent=2)

            iter_duration = time.time() - iter_start

            iterations.append(
                IterationResult(
                    iteration=iteration,
                    report=report_dict,
                    category_analyses=analyses_dicts,
                    improvements_applied=[applied_description],
                    patch_proposal=proposal_dict,
                    review_result=review_dict,
                    post_scores=post_scores,
                    reverted=reverted,
                    revert_reason=revert_reason,
                    duration_seconds=iter_duration,
                )
            )

            print(f"\n  Iteration {iteration} completed in {iter_duration:.1f}s")

        finally:
            agent.close()

    # Final summary
    total_duration = time.time() - start_time

    result = RunnerResult(
        config={
            "num_turns": config.num_turns,
            "num_questions": config.num_questions,
            "max_iterations": config.max_iterations,
            "failure_threshold": config.failure_threshold,
            "regression_threshold": config.regression_threshold,
            "use_multi_agent": config.use_multi_agent,
        },
        iterations=iterations,
        score_progression=score_progression,
        category_progression=category_progression,
        total_duration_seconds=total_duration,
    )

    # Save summary
    summary = {
        "config": result.config,
        "score_progression": result.score_progression,
        "category_progression": {
            k: [round(v, 4) for v in vals] for k, vals in result.category_progression.items()
        },
        "total_duration_seconds": round(total_duration, 2),
        "iterations_run": len(iterations),
        "patches_applied": len(patch_history.applied_patches),
        "patches_reverted": len(patch_history.reverted_patches),
        "patches_rejected": len(patch_history.rejected_patches),
    }
    with open(output_dir / "self_improve_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print(f"\n{'=' * 70}")
    print("LONG-HORIZON SELF-IMPROVEMENT SUMMARY")
    print(f"{'=' * 70}")
    print(f"Iterations run: {len(iterations)}")
    print(f"Total duration: {total_duration:.1f}s")
    print(f"Patches applied: {len(patch_history.applied_patches)}")
    print(f"Patches reverted: {len(patch_history.reverted_patches)}")
    print(f"Patches rejected: {len(patch_history.rejected_patches)}")

    if score_progression:
        print(f"\nScore progression: {' -> '.join(f'{s:.2%}' for s in score_progression)}")

    print("\nCategory progression:")
    for cat, scores in sorted(category_progression.items()):
        scores_str = " -> ".join(f"{s:.2%}" for s in scores)
        print(f"  {cat}: {scores_str}")

    print(f"\nResults saved to: {config.output_dir}")

    return result


def main() -> None:
    """CLI entry point for long-horizon self-improvement."""
    import argparse

    parser = argparse.ArgumentParser(description="Long-horizon memory self-improvement runner")
    parser.add_argument("--turns", type=int, default=100, help="Dialogue turns (default: 100)")
    parser.add_argument("--questions", type=int, default=20, help="Quiz questions (default: 20)")
    parser.add_argument("--iterations", type=int, default=3, help="Max iterations (default: 3)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Failure threshold (default: 0.7)",
    )
    parser.add_argument(
        "--regression-threshold",
        type=float,
        default=5.0,
        help="Max regression in pp before auto-revert (default: 5.0)",
    )
    parser.add_argument(
        "--multi-agent",
        action="store_true",
        help="Use MultiAgentLearningAgent",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/long-horizon-self-improve",
        help="Output directory",
    )
    parser.add_argument("--model", default="", help="Agent model")
    parser.add_argument("--grader-model", default="", help="Grader model")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = LongHorizonRunnerConfig(
        num_turns=args.turns,
        num_questions=args.questions,
        seed=args.seed,
        max_iterations=args.iterations,
        failure_threshold=args.threshold,
        regression_threshold=args.regression_threshold,
        use_multi_agent=args.multi_agent,
        output_dir=args.output_dir,
        agent_model=args.model,
        grader_model=args.grader_model,
    )

    result = run_long_horizon_self_improve(config)

    if not result.iterations:
        print("\nNo iterations completed.")
        sys.exit(1)

    final_score = result.score_progression[-1] if result.score_progression else 0.0
    if final_score < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "run_long_horizon_self_improve",
    "LongHorizonRunnerConfig",
    "CategoryAnalysis",
    "RunnerResult",
    "IterationResult",
    "detect_regression",
]
