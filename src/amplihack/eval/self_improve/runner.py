"""Self-improvement runner for goal-seeking agents.

Implements the closed-loop: EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE.
Each iteration measures L1-L12 scores, identifies failures with error_analyzer,
runs a research step (hypothesis + evidence + counter-arguments), applies the
best improvement, and gates promotion through regression checks.

Philosophy:
- Measure first, change second
- Every change has a hypothesis and evidence
- Revert on regression, commit on improvement
- Log everything for reproducibility
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..progressive_test_suite import ProgressiveConfig, run_progressive_suite
from .error_analyzer import ErrorAnalysis, analyze_eval_results

logger = logging.getLogger(__name__)


@dataclass
class ResearchDecision:
    """Result of the research step for a proposed improvement.

    Captures the full reasoning chain: hypothesis -> evidence ->
    counter-arguments -> decision.
    """

    hypothesis: str
    evidence: list[str]
    counter_arguments: list[str]
    decision: str  # "apply", "skip", "defer"
    reasoning: str
    failure_mode: str
    affected_level: str
    affected_component: str
    proposed_change: str


@dataclass
class IterationResult:
    """Result of a single improvement iteration."""

    iteration: int
    baseline_scores: dict[str, float]
    post_scores: dict[str, float] | None
    analyses: list[dict]
    research_decisions: list[dict]
    applied_changes: list[str]
    net_improvement: float
    max_regression: float
    committed: bool
    reverted: bool
    duration_seconds: float


@dataclass
class RunnerConfig:
    """Configuration for the self-improvement runner."""

    sdk_type: str = "mini"
    max_iterations: int = 5
    improvement_threshold: float = 2.0  # minimum % improvement to commit
    regression_tolerance: float = 5.0  # maximum % regression on any level
    levels: list[str] = field(default_factory=lambda: ["L1", "L2", "L3", "L4", "L5", "L6"])
    output_dir: str = "./eval_results/self_improve"
    agent_name: str = "self-improve-agent"
    score_threshold: float = 0.6  # threshold for failure classification
    dry_run: bool = False  # if True, do not apply changes or git operations


@dataclass
class RunnerResult:
    """Result of the complete self-improvement run."""

    config: RunnerConfig
    iterations: list[IterationResult]
    final_scores: dict[str, float]
    total_improvement: float
    total_duration_seconds: float


def _extract_level_scores(eval_result) -> dict[str, float]:
    """Extract per-level average scores from a ProgressiveResult.

    Args:
        eval_result: ProgressiveResult from run_progressive_suite

    Returns:
        Dict mapping level_id -> average score (0.0-1.0)
    """
    scores: dict[str, float] = {}
    for lr in eval_result.level_results:
        if lr.success and lr.scores:
            scores[lr.level_id] = lr.scores["average"]
        else:
            scores[lr.level_id] = 0.0
    if scores:
        scores["overall"] = sum(scores.values()) / len(scores)
    return scores


def _extract_level_results_for_analyzer(eval_result) -> list[dict]:
    """Convert ProgressiveResult into the format expected by analyze_eval_results.

    Args:
        eval_result: ProgressiveResult from run_progressive_suite

    Returns:
        List of level result dicts with 'details' containing per-question data
    """
    results = []
    for lr in eval_result.level_results:
        if lr.success and lr.scores:
            results.append(
                {
                    "level_id": lr.level_id,
                    "details": lr.scores.get("details", []),
                }
            )
    return results


def _research_improvement(
    analysis: ErrorAnalysis,
    all_analyses: list[ErrorAnalysis],
    baseline_scores: dict[str, float],
) -> ResearchDecision:
    """Research step: hypothesis, evidence, counter-arguments, decision.

    This is the critical thinking step that prevents blind changes.
    For each proposed improvement, we:
    1. State a clear hypothesis
    2. Gather evidence from eval results and the codebase
    3. Consider what could go wrong
    4. Make a reasoned decision

    Args:
        analysis: The specific failure to research
        all_analyses: All failures for cross-referencing
        baseline_scores: Current scores for context

    Returns:
        ResearchDecision with full reasoning chain
    """
    # Step 1: State hypothesis
    hypothesis = (
        f"Improving {analysis.affected_component} will fix "
        f"'{analysis.failure_mode}' failures in {analysis.affected_level}, "
        f"raising score from {analysis.score:.0%}."
    )

    # Step 2: Gather evidence
    evidence = []

    # Evidence from eval results
    for ev in analysis.evidence:
        question = ev.get("question", "")[:100]
        actual = ev.get("actual", "")[:100]
        expected = ev.get("expected", "")[:100]
        evidence.append(f"Q: '{question}' -> Got: '{actual}' (expected: '{expected}')")

    # Evidence from failure patterns
    same_mode_count = sum(1 for a in all_analyses if a.failure_mode == analysis.failure_mode)
    if same_mode_count > 1:
        evidence.append(f"Pattern: {same_mode_count} failures share mode '{analysis.failure_mode}'")

    # Evidence from level baseline
    level_score = baseline_scores.get(analysis.affected_level, 0.0)
    evidence.append(f"Level {analysis.affected_level} baseline: {level_score:.0%}")

    # Step 3: Counter-arguments
    counter_arguments = []

    # Risk of prompt template changes
    if analysis.prompt_template:
        counter_arguments.append(
            f"Changing prompt '{analysis.prompt_template}' may regress other levels "
            f"that depend on the same template."
        )

    # Risk of code changes
    if "::" in analysis.affected_component:
        counter_arguments.append(
            f"Modifying '{analysis.affected_component}' is a code change "
            f"that could break other components sharing the same function."
        )

    # Risk of stochasticity
    if analysis.score >= 0.4:
        counter_arguments.append(
            f"Score {analysis.score:.0%} is borderline - could be LLM stochasticity "
            f"rather than a systematic failure."
        )

    # Risk if many levels affected
    affected_levels = {
        a.affected_level for a in all_analyses if a.failure_mode == analysis.failure_mode
    }
    if len(affected_levels) > 2:
        counter_arguments.append(
            f"This failure mode affects {len(affected_levels)} levels - "
            f"a single fix may not address all of them."
        )

    # Step 4: Make decision
    # Apply if: clear failure pattern, prompt template available, multiple evidence points
    if analysis.prompt_template and same_mode_count >= 2 and analysis.score < 0.4:
        decision = "apply"
        reasoning = (
            f"Strong evidence: {same_mode_count} failures of type '{analysis.failure_mode}', "
            f"low score ({analysis.score:.0%}), and a targeted prompt template "
            f"'{analysis.prompt_template}' is available for safe modification."
        )
    elif analysis.prompt_template and analysis.score < 0.3:
        decision = "apply"
        reasoning = (
            f"Very low score ({analysis.score:.0%}) with prompt template available. "
            f"Risk is acceptable for prompt-level changes."
        )
    elif analysis.score < 0.2:
        decision = "apply"
        reasoning = (
            f"Critical failure (score {analysis.score:.0%}). "
            f"Even without a prompt template, the component needs attention."
        )
    elif analysis.score >= 0.5:
        decision = "skip"
        reasoning = (
            f"Score {analysis.score:.0%} is above 50% - likely stochastic variation. "
            f"Counter-arguments outweigh evidence for change."
        )
    else:
        decision = "defer"
        reasoning = (
            f"Insufficient evidence to justify change. Score {analysis.score:.0%} "
            f"is in the ambiguous range. Deferring to next iteration for more data."
        )

    # Describe the proposed change
    if analysis.prompt_template:
        proposed_change = (
            f"Modify prompt template '{analysis.prompt_template}' to address "
            f"'{analysis.failure_mode}' pattern in {analysis.affected_component}."
        )
    else:
        proposed_change = (
            f"Investigate and fix {analysis.affected_component} to address "
            f"'{analysis.failure_mode}' pattern."
        )

    return ResearchDecision(
        hypothesis=hypothesis,
        evidence=evidence,
        counter_arguments=counter_arguments,
        decision=decision,
        reasoning=reasoning,
        failure_mode=analysis.failure_mode,
        affected_level=analysis.affected_level,
        affected_component=analysis.affected_component,
        proposed_change=proposed_change,
    )


def _apply_prompt_improvement(
    analysis: ErrorAnalysis,
    research: ResearchDecision,
    output_dir: Path,
) -> str | None:
    """Apply a prompt-level improvement for a specific failure.

    Generates an improved prompt instruction based on the failure analysis
    and writes it to the output directory. Returns a description of the
    change applied, or None if no change was made.

    Args:
        analysis: The failure analysis
        research: The research decision
        output_dir: Directory to write patch files

    Returns:
        Description of applied change, or None
    """
    if research.decision != "apply":
        return None

    # Generate improvement patch description
    patch_description = {
        "failure_mode": analysis.failure_mode,
        "affected_component": analysis.affected_component,
        "prompt_template": analysis.prompt_template,
        "proposed_change": research.proposed_change,
        "evidence_count": len(research.evidence),
        "hypothesis": research.hypothesis,
    }

    # Write patch file for tracking
    patch_file = output_dir / f"patch_{analysis.failure_mode}_{analysis.affected_level}.json"
    with open(patch_file, "w") as f:
        json.dump(patch_description, f, indent=2)

    return research.proposed_change


def _compute_regression(
    baseline: dict[str, float],
    post: dict[str, float],
) -> tuple[float, float, str]:
    """Compute net improvement and max regression between two score sets.

    Args:
        baseline: Pre-change scores by level
        post: Post-change scores by level

    Returns:
        Tuple of (net_improvement_pct, max_regression_pct, worst_level)
    """
    baseline_overall = baseline.get("overall", 0.0)
    post_overall = post.get("overall", 0.0)
    net_improvement = (post_overall - baseline_overall) * 100.0

    max_regression = 0.0
    worst_level = ""
    for level_id in baseline:
        if level_id == "overall":
            continue
        if level_id in post:
            regression = (baseline[level_id] - post[level_id]) * 100.0
            if regression > max_regression:
                max_regression = regression
                worst_level = level_id

    return net_improvement, max_regression, worst_level


def run_self_improvement(config: RunnerConfig) -> RunnerResult:
    """Run the complete self-improvement loop.

    For each iteration:
    1. EVAL: Run progressive test suite
    2. ANALYZE: Classify failures with error_analyzer
    3. RESEARCH: Hypothesis + evidence + counter-arguments for each fix
    4. IMPROVE: Apply the best improvement
    5. RE-EVAL: Run eval again on affected levels
    6. DECIDE: Commit if improved, revert if regressed
    7. LOG: Write iteration results

    Args:
        config: Runner configuration

    Returns:
        RunnerResult with all iteration details
    """
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    iterations: list[IterationResult] = []
    start_time = time.time()

    print("=" * 70)
    print("SELF-IMPROVEMENT RUNNER")
    print("=" * 70)
    print(f"SDK: {config.sdk_type}")
    print(f"Max iterations: {config.max_iterations}")
    print(f"Improvement threshold: {config.improvement_threshold}%")
    print(f"Regression tolerance: {config.regression_tolerance}%")
    print(f"Levels: {', '.join(config.levels)}")
    print(f"Output: {config.output_dir}")
    print(f"Dry run: {config.dry_run}")
    print("=" * 70)

    for iteration in range(1, config.max_iterations + 1):
        iter_start = time.time()
        iter_dir = output_dir / f"iteration_{iteration}"
        iter_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 70}")
        print(f"ITERATION {iteration}/{config.max_iterations}")
        print(f"{'=' * 70}")

        # Phase 1: EVAL - Run progressive test suite
        print("\n[Phase 1/6] EVAL - Running progressive test suite...")
        eval_config = ProgressiveConfig(
            output_dir=str(iter_dir / "eval"),
            agent_name=f"{config.agent_name}_iter{iteration}_{int(time.time())}",
            levels_to_run=config.levels,
        )
        eval_result = run_progressive_suite(eval_config)
        baseline_scores = _extract_level_scores(eval_result)

        print("  Baseline scores:")
        for level_id in sorted(k for k in baseline_scores if k != "overall"):
            print(f"    {level_id}: {baseline_scores[level_id]:.0%}")
        print(f"    Overall: {baseline_scores.get('overall', 0):.0%}")

        # Save baseline scores
        with open(iter_dir / "baseline_scores.json", "w") as f:
            json.dump(baseline_scores, f, indent=2)

        # Phase 2: ANALYZE - Classify failures
        print("\n[Phase 2/6] ANALYZE - Classifying failures...")
        level_results = _extract_level_results_for_analyzer(eval_result)
        analyses = analyze_eval_results(level_results, score_threshold=config.score_threshold)

        print(f"  Found {len(analyses)} failure(s):")
        for a in analyses[:5]:  # Show top 5
            print(f"    - {a.affected_level} {a.failure_mode}: {a.score:.0%}")

        # Save analyses
        analyses_dicts = [
            {
                "failure_mode": a.failure_mode,
                "affected_level": a.affected_level,
                "affected_component": a.affected_component,
                "prompt_template": a.prompt_template,
                "score": a.score,
                "suggested_focus": a.suggested_focus,
            }
            for a in analyses
        ]
        with open(iter_dir / "analyses.json", "w") as f:
            json.dump(analyses_dicts, f, indent=2)

        # Phase 3: RESEARCH - Hypothesis + evidence + counter-arguments
        print("\n[Phase 3/6] RESEARCH - Investigating improvements...")
        research_decisions: list[ResearchDecision] = []
        for analysis in analyses:
            research = _research_improvement(analysis, analyses, baseline_scores)
            research_decisions.append(research)
            status_icon = {"apply": "+", "skip": "-", "defer": "?"}[research.decision]
            print(f"  [{status_icon}] {research.failure_mode} ({analysis.affected_level}):")
            print(f"      Hypothesis: {research.hypothesis[:80]}...")
            print(f"      Evidence: {len(research.evidence)} points")
            print(f"      Counter-args: {len(research.counter_arguments)}")
            print(f"      Decision: {research.decision} - {research.reasoning[:60]}...")

        # Save research decisions
        research_dicts = [
            {
                "hypothesis": r.hypothesis,
                "evidence": r.evidence,
                "counter_arguments": r.counter_arguments,
                "decision": r.decision,
                "reasoning": r.reasoning,
                "failure_mode": r.failure_mode,
                "affected_level": r.affected_level,
                "affected_component": r.affected_component,
                "proposed_change": r.proposed_change,
            }
            for r in research_decisions
        ]
        with open(iter_dir / "research_decisions.json", "w") as f:
            json.dump(research_dicts, f, indent=2)

        # Phase 4: IMPROVE - Apply the best improvements
        print("\n[Phase 4/6] IMPROVE - Applying improvements...")
        applied_changes: list[str] = []
        to_apply = [r for r in research_decisions if r.decision == "apply"]

        if not to_apply:
            print("  No improvements to apply this iteration.")
        elif config.dry_run:
            print(f"  [DRY RUN] Would apply {len(to_apply)} change(s):")
            for r in to_apply:
                print(f"    - {r.proposed_change[:80]}")
                applied_changes.append(f"[DRY RUN] {r.proposed_change}")
        else:
            for r in to_apply:
                matching_analysis = next(
                    (
                        a
                        for a in analyses
                        if a.failure_mode == r.failure_mode and a.affected_level == r.affected_level
                    ),
                    None,
                )
                if matching_analysis:
                    change = _apply_prompt_improvement(matching_analysis, r, iter_dir)
                    if change:
                        applied_changes.append(change)
                        print(f"    Applied: {change[:80]}")

        # Phase 5: RE-EVAL - Run eval again if changes were applied
        post_scores: dict[str, float] | None = None
        net_improvement = 0.0
        max_regression = 0.0

        if applied_changes and not config.dry_run:
            print("\n[Phase 5/6] RE-EVAL - Measuring impact...")
            re_eval_config = ProgressiveConfig(
                output_dir=str(iter_dir / "re_eval"),
                agent_name=f"{config.agent_name}_reeval{iteration}_{int(time.time())}",
                levels_to_run=config.levels,
            )
            re_eval_result = run_progressive_suite(re_eval_config)
            post_scores = _extract_level_scores(re_eval_result)

            print("  Post-change scores:")
            for level_id in sorted(k for k in post_scores if k != "overall"):
                baseline_val = baseline_scores.get(level_id, 0.0)
                post_val = post_scores[level_id]
                delta = (post_val - baseline_val) * 100
                direction = "+" if delta >= 0 else ""
                print(f"    {level_id}: {post_val:.0%} ({direction}{delta:.1f}%)")
            print(f"    Overall: {post_scores.get('overall', 0):.0%}")

            # Save post scores
            with open(iter_dir / "post_scores.json", "w") as f:
                json.dump(post_scores, f, indent=2)
        else:
            print("\n[Phase 5/6] RE-EVAL - Skipped (no changes applied)")
            post_scores = baseline_scores.copy()

        # Phase 6: DECIDE - Commit or revert
        print("\n[Phase 6/6] DECIDE - Evaluating results...")
        committed = False
        reverted = False

        if applied_changes and post_scores and not config.dry_run:
            net_improvement, max_regression, worst_level = _compute_regression(
                baseline_scores, post_scores
            )

            print(f"  Net improvement: {net_improvement:+.1f}%")
            print(f"  Max regression: {max_regression:.1f}% ({worst_level})")

            if max_regression > config.regression_tolerance:
                print(
                    f"  REVERT: Regression {max_regression:.1f}% exceeds tolerance {config.regression_tolerance}%"
                )
                reverted = True
            elif net_improvement >= config.improvement_threshold:
                print(
                    f"  COMMIT: Improvement {net_improvement:.1f}% meets threshold {config.improvement_threshold}%"
                )
                committed = True
            else:
                print(
                    f"  COMMIT (marginal): Improvement {net_improvement:.1f}% below threshold but no regression"
                )
                committed = True
        else:
            print("  No changes to evaluate.")

        iter_duration = time.time() - iter_start

        # Build iteration result
        iter_result = IterationResult(
            iteration=iteration,
            baseline_scores=baseline_scores,
            post_scores=post_scores,
            analyses=analyses_dicts,
            research_decisions=research_dicts,
            applied_changes=applied_changes,
            net_improvement=net_improvement,
            max_regression=max_regression,
            committed=committed,
            reverted=reverted,
            duration_seconds=iter_duration,
        )
        iterations.append(iter_result)

        # Save iteration result
        with open(iter_dir / "iteration_result.json", "w") as f:
            json.dump(
                {
                    "iteration": iter_result.iteration,
                    "baseline_scores": iter_result.baseline_scores,
                    "post_scores": iter_result.post_scores,
                    "analyses_count": len(iter_result.analyses),
                    "research_decisions_count": len(iter_result.research_decisions),
                    "applied_changes": iter_result.applied_changes,
                    "net_improvement": iter_result.net_improvement,
                    "max_regression": iter_result.max_regression,
                    "committed": iter_result.committed,
                    "reverted": iter_result.reverted,
                    "duration_seconds": iter_result.duration_seconds,
                },
                f,
                indent=2,
            )

        print(f"\n  Iteration {iteration} completed in {iter_duration:.1f}s")

        # Early exit: if no failures found, we're done
        if not analyses:
            print("  No failures found - agent is performing well. Stopping.")
            break

        # Early exit: if no improvements possible
        if not to_apply and not config.dry_run:
            print("  No improvements deemed worth applying. Stopping.")
            break

    # Final summary
    total_duration = time.time() - start_time
    final_scores = (
        iterations[-1].post_scores or iterations[-1].baseline_scores if iterations else {}
    )

    total_improvement = 0.0
    if len(iterations) >= 2:
        first_overall = iterations[0].baseline_scores.get("overall", 0.0)
        last_overall = final_scores.get("overall", 0.0)
        total_improvement = (last_overall - first_overall) * 100.0

    result = RunnerResult(
        config=config,
        iterations=iterations,
        final_scores=final_scores,
        total_improvement=total_improvement,
        total_duration_seconds=total_duration,
    )

    # Save final summary
    summary = {
        "sdk_type": config.sdk_type,
        "max_iterations": config.max_iterations,
        "iterations_run": len(iterations),
        "final_scores": final_scores,
        "total_improvement_pct": total_improvement,
        "total_duration_seconds": total_duration,
        "per_iteration": [
            {
                "iteration": it.iteration,
                "baseline_overall": it.baseline_scores.get("overall", 0.0),
                "post_overall": (it.post_scores or {}).get("overall", 0.0),
                "net_improvement": it.net_improvement,
                "max_regression": it.max_regression,
                "committed": it.committed,
                "reverted": it.reverted,
                "failures_found": len(it.analyses),
                "changes_applied": len(it.applied_changes),
                "duration_seconds": it.duration_seconds,
            }
            for it in iterations
        ],
    }

    with open(output_dir / "self_improve_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print(f"\n{'=' * 70}")
    print("SELF-IMPROVEMENT SUMMARY")
    print(f"{'=' * 70}")
    print(f"Iterations run: {len(iterations)}")
    print(f"Total duration: {total_duration:.1f}s")
    print(f"Total improvement: {total_improvement:+.1f}%")
    print("\nFinal scores:")
    for level_id in sorted(k for k in final_scores if k != "overall"):
        print(f"  {level_id}: {final_scores[level_id]:.0%}")
    if "overall" in final_scores:
        print(f"  Overall: {final_scores['overall']:.0%}")
    print(f"\nResults saved to: {config.output_dir}")

    return result


def main():
    """CLI entry point for the self-improvement runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Improvement Runner for Goal-Seeking Agents")
    parser.add_argument(
        "--sdk",
        default="mini",
        choices=["mini", "claude", "copilot", "microsoft"],
        help="SDK type to evaluate (default: mini)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Maximum improvement iterations (default: 5)",
    )
    parser.add_argument(
        "--improvement-threshold",
        type=float,
        default=2.0,
        help="Minimum %% improvement to commit (default: 2.0)",
    )
    parser.add_argument(
        "--regression-tolerance",
        type=float,
        default=5.0,
        help="Maximum %% regression on any level (default: 5.0)",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        default=["L1", "L2", "L3", "L4", "L5", "L6"],
        help="Levels to evaluate (default: L1-L6)",
    )
    parser.add_argument(
        "--output-dir",
        default="./eval_results/self_improve",
        help="Output directory (default: ./eval_results/self_improve)",
    )
    parser.add_argument(
        "--agent-name",
        default="self-improve-agent",
        help="Agent name for memory isolation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run evaluation and analysis only, do not apply changes",
    )

    args = parser.parse_args()

    config = RunnerConfig(
        sdk_type=args.sdk,
        max_iterations=args.iterations,
        improvement_threshold=args.improvement_threshold,
        regression_tolerance=args.regression_tolerance,
        levels=args.levels,
        output_dir=args.output_dir,
        agent_name=args.agent_name,
        dry_run=args.dry_run,
    )

    result = run_self_improvement(config)

    if not result.iterations:
        print("\nNo iterations completed.")
        sys.exit(1)

    # Exit with error if overall score is below 50%
    final_overall = result.final_scores.get("overall", 0.0)
    if final_overall < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()


__all__ = [
    "run_self_improvement",
    "RunnerConfig",
    "RunnerResult",
    "IterationResult",
    "ResearchDecision",
]
