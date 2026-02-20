"""SDK evaluation improvement loop.

Runs N iterations of eval-analyze-tune-reeval per SDK, tracking score
progression. Each loop:
1. Runs L1-L6 eval for the SDK
2. Analyzes failures to identify weak levels
3. Generates prompt tuning recommendations
4. Re-evaluates to measure improvement

Usage:
    python -m amplihack.eval.sdk_eval_loop --sdks mini claude --loops 5
    python -m amplihack.eval.sdk_eval_loop --all-sdks --loops 3 --levels L1 L2 L3

Philosophy: Data-driven SDK comparison via iterative improvement.
Each iteration produces actionable tuning recommendations.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .progressive_test_suite import (
    ProgressiveConfig,
    ProgressiveResult,
    run_progressive_suite,
)


@dataclass
class LoopIteration:
    """Result of a single improvement loop iteration."""

    iteration: int
    sdk: str
    scores: dict[str, float]
    overall: float
    failures: list[dict]
    recommendations: list[str]
    duration_seconds: float


@dataclass
class SDKEvalReport:
    """Complete eval report for one SDK across all iterations."""

    sdk: str
    iterations: list[LoopIteration]
    final_scores: dict[str, float]
    final_overall: float
    score_progression: list[float]
    best_iteration: int
    best_overall: float


@dataclass
class MultiSDKReport:
    """Comparative report across all SDKs."""

    sdk_reports: dict[str, SDKEvalReport]
    ranking: list[tuple[str, float]]  # (sdk, best_overall) sorted descending
    timestamp: str


def _analyze_failures(result: ProgressiveResult) -> list[dict]:
    """Extract failure details from eval results.

    Args:
        result: Progressive test suite result

    Returns:
        List of failure dicts with level, question, score, and reason
    """
    failures = []
    for lr in result.level_results:
        if not lr.success:
            failures.append(
                {
                    "level": lr.level_id,
                    "type": "level_failure",
                    "error": lr.error_message or "Unknown error",
                    "score": 0.0,
                }
            )
            continue

        if lr.scores and lr.scores.get("details"):
            for detail in lr.scores["details"]:
                if detail.get("score", 1.0) < 0.7:
                    failures.append(
                        {
                            "level": detail.get("level", lr.level_id),
                            "type": detail.get("reasoning_type", "unknown"),
                            "question": detail.get("question", "")[:100],
                            "expected": detail.get("expected", "")[:100],
                            "actual": detail.get("actual", "")[:100],
                            "score": detail.get("score", 0.0),
                        }
                    )

    return failures


def _generate_recommendations(failures: list[dict], sdk: str) -> list[str]:
    """Generate SDK-specific prompt tuning recommendations.

    Args:
        failures: List of failure details
        sdk: SDK type

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Group failures by level
    level_failures: dict[str, list[dict]] = {}
    for f in failures:
        level_failures.setdefault(f["level"], []).append(f)

    # Analyze patterns
    for level_id, lf in sorted(level_failures.items()):
        level_score = sum(f.get("score", 0.0) for f in lf) / max(len(lf), 1)
        reasoning_types = {f.get("type", "unknown") for f in lf}

        if level_id == "L3" and level_score < 0.7:
            recommendations.append(
                f"[{sdk}] L3 temporal reasoning weak ({level_score:.0%}). "
                "Add explicit temporal comparison instructions to SDK prompt."
            )
        elif level_id == "L5" and level_score < 0.7:
            recommendations.append(
                f"[{sdk}] L5 contradiction handling weak ({level_score:.0%}). "
                "Add contradiction awareness instructions."
            )
        elif level_id == "L2" and level_score < 0.8:
            recommendations.append(
                f"[{sdk}] L2 multi-source synthesis needs improvement ({level_score:.0%}). "
                "Add cross-source comparison instructions."
            )
        elif level_id == "L4" and "procedural_sequence" in reasoning_types:
            recommendations.append(
                f"[{sdk}] L4 procedural sequencing issues. "
                "Add step-numbering instructions to prompt."
            )
        elif level_id == "L6" and level_score < 0.8:
            recommendations.append(
                f"[{sdk}] L6 incremental update handling weak ({level_score:.0%}). "
                "Add instructions to prefer latest information."
            )

    if not recommendations:
        recommendations.append(f"[{sdk}] All levels performing adequately. No tuning needed.")

    return recommendations


def _extract_level_scores(result: ProgressiveResult) -> dict[str, float]:
    """Extract per-level average scores from result.

    Args:
        result: Progressive test suite result

    Returns:
        Dict mapping level_id to average score
    """
    scores = {}
    for lr in result.level_results:
        if lr.success and lr.scores:
            scores[lr.level_id] = lr.scores["average"]
        else:
            scores[lr.level_id] = 0.0
    return scores


def run_sdk_eval_loop(
    sdk: str,
    num_loops: int = 5,
    levels: list[str] | None = None,
    base_output_dir: str = "./eval_sdk_loop",
) -> SDKEvalReport:
    """Run improvement loop for a single SDK.

    Args:
        sdk: SDK type (mini, claude, copilot, microsoft)
        num_loops: Number of improvement iterations
        levels: Levels to evaluate (default: L1-L6)
        base_output_dir: Base directory for results

    Returns:
        SDKEvalReport with all iteration results
    """
    output_dir = Path(base_output_dir) / sdk
    output_dir.mkdir(parents=True, exist_ok=True)

    iterations: list[LoopIteration] = []
    score_progression: list[float] = []
    best_overall = 0.0
    best_iteration = 0

    for loop_idx in range(num_loops):
        print(f"\n{'#' * 70}")
        print(f"SDK: {sdk} | Loop {loop_idx + 1}/{num_loops}")
        print(f"{'#' * 70}")

        start_time = time.time()

        # Create unique agent name for this iteration
        agent_name = f"sdk_{sdk}_loop{loop_idx}_{int(time.time())}"
        iter_dir = str(output_dir / f"loop_{loop_idx}")

        config = ProgressiveConfig(
            output_dir=iter_dir,
            agent_name=agent_name,
            levels_to_run=levels,
            sdk=sdk,
        )

        # Step 1: Run eval
        result = run_progressive_suite(config)

        duration = time.time() - start_time

        # Step 2: Extract scores
        level_scores = _extract_level_scores(result)
        overall = result.overall_scores.get("overall", 0.0) if result.overall_scores else 0.0

        # Step 3: Analyze failures
        failures = _analyze_failures(result)

        # Step 4: Generate recommendations
        recommendations = _generate_recommendations(failures, sdk)

        iteration = LoopIteration(
            iteration=loop_idx,
            sdk=sdk,
            scores=level_scores,
            overall=overall,
            failures=failures,
            recommendations=recommendations,
            duration_seconds=round(duration, 1),
        )
        iterations.append(iteration)
        score_progression.append(overall)

        if overall > best_overall:
            best_overall = overall
            best_iteration = loop_idx

        # Print iteration summary
        print(f"\n  Loop {loop_idx + 1} Results ({sdk}):")
        for level_id, score in sorted(level_scores.items()):
            print(f"    {level_id}: {score:.2%}")
        print(f"    Overall: {overall:.2%} ({duration:.1f}s)")

        if failures:
            print(f"    Failures: {len(failures)}")
            for f in failures[:3]:
                print(f"      - {f['level']} [{f['type']}]: score={f.get('score', 0):.2%}")

        if recommendations:
            print("    Recommendations:")
            for rec in recommendations[:3]:
                print(f"      - {rec}")

        # Save iteration results
        iter_path = output_dir / f"loop_{loop_idx}" / "iteration.json"
        iter_path.parent.mkdir(parents=True, exist_ok=True)
        with open(iter_path, "w") as f:
            json.dump(
                {
                    "iteration": loop_idx,
                    "sdk": sdk,
                    "scores": level_scores,
                    "overall": overall,
                    "failures_count": len(failures),
                    "recommendations": recommendations,
                    "duration_seconds": round(duration, 1),
                },
                f,
                indent=2,
            )

    # Build final report
    final_scores = iterations[-1].scores if iterations else {}
    final_overall = iterations[-1].overall if iterations else 0.0

    report = SDKEvalReport(
        sdk=sdk,
        iterations=iterations,
        final_scores=final_scores,
        final_overall=final_overall,
        score_progression=score_progression,
        best_iteration=best_iteration,
        best_overall=best_overall,
    )

    # Save SDK report
    with open(output_dir / "sdk_report.json", "w") as f:
        json.dump(
            {
                "sdk": sdk,
                "final_scores": final_scores,
                "final_overall": final_overall,
                "score_progression": [round(s, 4) for s in score_progression],
                "best_iteration": best_iteration,
                "best_overall": round(best_overall, 4),
                "total_iterations": len(iterations),
            },
            f,
            indent=2,
        )

    return report


def run_multi_sdk_eval(
    sdks: list[str],
    num_loops: int = 5,
    levels: list[str] | None = None,
    base_output_dir: str = "./eval_sdk_loop",
) -> MultiSDKReport:
    """Run improvement loops for multiple SDKs and compare.

    Args:
        sdks: List of SDK types to evaluate
        num_loops: Number of improvement iterations per SDK
        levels: Levels to evaluate (default: L1-L6)
        base_output_dir: Base directory for results

    Returns:
        MultiSDKReport with comparative results
    """
    sdk_reports: dict[str, SDKEvalReport] = {}

    for sdk in sdks:
        print(f"\n{'=' * 70}")
        print(f"EVALUATING SDK: {sdk}")
        print(f"{'=' * 70}")

        report = run_sdk_eval_loop(
            sdk=sdk,
            num_loops=num_loops,
            levels=levels,
            base_output_dir=base_output_dir,
        )
        sdk_reports[sdk] = report

    # Rank SDKs by best overall score
    ranking = sorted(
        [(sdk, report.best_overall) for sdk, report in sdk_reports.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    multi_report = MultiSDKReport(
        sdk_reports=sdk_reports,
        ranking=ranking,
        timestamp=timestamp,
    )

    # Print comparative summary
    print(f"\n{'=' * 70}")
    print("MULTI-SDK COMPARISON RESULTS")
    print(f"{'=' * 70}")
    print(f"Timestamp: {timestamp}")
    print(f"SDKs evaluated: {', '.join(sdks)}")
    print(f"Loops per SDK: {num_loops}")
    print()

    print("SDK Ranking (by best overall score):")
    for rank, (sdk, score) in enumerate(ranking, 1):
        report = sdk_reports[sdk]
        prog = " -> ".join(f"{s:.0%}" for s in report.score_progression)
        print(f"  {rank}. {sdk}: {score:.2%} (best at loop {report.best_iteration + 1})")
        print(f"     Progression: {prog}")

    print()
    print("Per-Level Comparison (final iteration):")
    all_levels = sorted(
        {level_id for report in sdk_reports.values() for level_id in report.final_scores}
    )
    header = "Level  " + "  ".join(f"{sdk:>10}" for sdk in sdks)
    print(f"  {header}")
    for level_id in all_levels:
        scores_row = "  ".join(
            f"{sdk_reports[sdk].final_scores.get(level_id, 0.0):>10.2%}" for sdk in sdks
        )
        print(f"  {level_id:<7}{scores_row}")

    # Save comparative report
    output_path = Path(base_output_dir) / "multi_sdk_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "sdks": sdks,
                "num_loops": num_loops,
                "ranking": [
                    {"sdk": sdk, "best_overall": round(score, 4)} for sdk, score in ranking
                ],
                "per_sdk": {
                    sdk: {
                        "final_scores": report.final_scores,
                        "final_overall": round(report.final_overall, 4),
                        "score_progression": [round(s, 4) for s in report.score_progression],
                        "best_iteration": report.best_iteration,
                        "best_overall": round(report.best_overall, 4),
                    }
                    for sdk, report in sdk_reports.items()
                },
            },
            f,
            indent=2,
        )

    print(f"\nDetailed results saved to: {base_output_dir}")
    return multi_report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SDK Evaluation Improvement Loop")
    parser.add_argument(
        "--sdks",
        nargs="+",
        choices=["mini", "claude", "copilot", "microsoft"],
        help="SDKs to evaluate",
    )
    parser.add_argument(
        "--all-sdks",
        action="store_true",
        help="Evaluate all 4 SDKs",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=5,
        help="Number of improvement loops per SDK (default: 5)",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=["L1", "L2", "L3", "L4", "L5", "L6"],
        help="Levels to run (default: L1-L6)",
    )
    parser.add_argument(
        "--output-dir",
        default="./eval_sdk_loop",
        help="Output directory for results",
    )
    args = parser.parse_args()

    # Determine SDKs
    if args.all_sdks:
        sdks = ["mini", "claude", "copilot", "microsoft"]
    elif args.sdks:
        sdks = args.sdks
    else:
        sdks = ["mini"]

    run_multi_sdk_eval(
        sdks=sdks,
        num_loops=args.loops,
        levels=args.levels,
        base_output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()


__all__ = [
    "run_sdk_eval_loop",
    "run_multi_sdk_eval",
    "SDKEvalReport",
    "MultiSDKReport",
    "LoopIteration",
]
