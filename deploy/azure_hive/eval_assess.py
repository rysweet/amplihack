#!/usr/bin/env python3
"""Assessment script for distributed eval output files.

Reads one or more eval result JSON files (produced by eval_distributed.py or
eval_distributed_security.py), re-validates scores, computes per-domain and
per-agent aggregate statistics, and writes an enriched assessment JSON.

Can also compare a distributed run against a single-agent baseline to
measure retrieval parity — the primary regression signal.

Usage:
    # Assess a single distributed run
    python deploy/azure_hive/eval_assess.py results.json

    # Compare distributed vs single-agent baseline
    python deploy/azure_hive/eval_assess.py \\
        --distributed results_distributed.json \\
        --baseline results_single_agent.json \\
        --output assessment.json

    # Batch-assess all JSON files in a directory
    python deploy/azure_hive/eval_assess.py --dir /tmp/eval_runs/ --output assessment.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [eval_assess] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_assess")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CategoryStats:
    category: str
    num_questions: int
    avg_score: float
    min_score: float
    max_score: float
    dimension_averages: dict[str, float]


@dataclass
class RunAssessment:
    source_file: str
    eval_type: str  # "distributed" | "single_agent" | "unknown"
    agent_count: int
    num_turns: int
    num_questions: int
    overall_score: float
    overall_score_pct: str
    pass_fail: str  # PASS / FAIL / WARN
    category_stats: list[CategoryStats]
    timing: dict[str, float]
    memory_stats: dict[str, Any]
    weakest_categories: list[str]
    strongest_categories: list[str]
    questions_below_threshold: list[dict[str, Any]]


@dataclass
class ParityReport:
    distributed_file: str
    baseline_file: str
    distributed_score: float
    baseline_score: float
    parity_delta: float  # distributed - baseline (positive = distributed better)
    parity_pct: str
    parity_status: str  # PARITY | DIVERGED | IMPROVED
    per_category_delta: dict[str, float]
    regressions: list[str]  # categories where distributed is worse by >5%
    improvements: list[str]  # categories where distributed is better by >5%


PASS_THRESHOLD = 0.90
WARN_THRESHOLD = 0.80
PARITY_TOLERANCE = 0.05  # 5% tolerance for distributed vs single-agent


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_run(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    if "results" not in data:
        raise ValueError(f"{path}: missing 'results' field — not an eval output file")
    return data


# ---------------------------------------------------------------------------
# Assessor
# ---------------------------------------------------------------------------


def assess_run(data: dict[str, Any], source_file: str) -> RunAssessment:
    overall_score = float(data.get("overall_score", 0.0))
    eval_type = data.get("eval_type", "unknown")
    agent_count = int(data.get("agent_count", data.get("memory_stats", {}).get("agent_count", 1)))
    num_turns = int(data.get("num_turns", 0))
    num_questions = int(data.get("num_questions", 0))

    # Category breakdown
    category_stats: list[CategoryStats] = []
    cat_scores: dict[str, float] = {}
    for cat in data.get("category_breakdown", []):
        cs = CategoryStats(
            category=cat["category"],
            num_questions=cat.get("num_questions", 0),
            avg_score=float(cat.get("avg_score", 0.0)),
            min_score=float(cat.get("min_score", 0.0)),
            max_score=float(cat.get("max_score", 0.0)),
            dimension_averages={k: float(v) for k, v in cat.get("dimension_averages", {}).items()},
        )
        category_stats.append(cs)
        cat_scores[cs.category] = cs.avg_score

    # Weakest / strongest categories (by avg_score)
    sorted_cats = sorted(cat_scores.items(), key=lambda x: x[1])
    weakest = [c for c, _ in sorted_cats[:3] if cat_scores]
    strongest = [c for c, _ in reversed(sorted_cats[-3:]) if cat_scores]

    # Questions below threshold (< 0.8)
    questions_below: list[dict[str, Any]] = []
    for result in data.get("results", []):
        q_score = float(result.get("overall_score", 1.0))
        if q_score < WARN_THRESHOLD:
            questions_below.append(
                {
                    "question_id": result.get("question_id", ""),
                    "category": result.get("category", ""),
                    "score": q_score,
                    "question": result.get("question_text", "")[:80],
                }
            )

    # Pass/fail
    if overall_score >= PASS_THRESHOLD:
        pass_fail = "PASS"
    elif overall_score >= WARN_THRESHOLD:
        pass_fail = "WARN"
    else:
        pass_fail = "FAIL"

    timing = {
        k: float(data.get(k, 0.0))
        for k in ("learning_time_s", "questioning_time_s", "grading_time_s")
    }

    return RunAssessment(
        source_file=source_file,
        eval_type=eval_type,
        agent_count=agent_count,
        num_turns=num_turns,
        num_questions=num_questions,
        overall_score=overall_score,
        overall_score_pct=f"{overall_score * 100:.1f}%",
        pass_fail=pass_fail,
        category_stats=category_stats,
        timing=timing,
        memory_stats=data.get("memory_stats", {}),
        weakest_categories=weakest,
        strongest_categories=strongest,
        questions_below_threshold=questions_below,
    )


# ---------------------------------------------------------------------------
# Parity comparison
# ---------------------------------------------------------------------------


def compare_runs(
    dist_data: dict[str, Any], base_data: dict[str, Any], dist_file: str, base_file: str
) -> ParityReport:
    dist_score = float(dist_data.get("overall_score", 0.0))
    base_score = float(base_data.get("overall_score", 0.0))
    delta = dist_score - base_score

    # Per-category delta
    base_cats: dict[str, float] = {
        c["category"]: float(c.get("avg_score", 0.0))
        for c in base_data.get("category_breakdown", [])
    }
    dist_cats: dict[str, float] = {
        c["category"]: float(c.get("avg_score", 0.0))
        for c in dist_data.get("category_breakdown", [])
    }

    all_cats = set(base_cats) | set(dist_cats)
    per_cat_delta = {
        cat: dist_cats.get(cat, 0.0) - base_cats.get(cat, 0.0) for cat in sorted(all_cats)
    }

    regressions = [cat for cat, d in per_cat_delta.items() if d < -PARITY_TOLERANCE]
    improvements = [cat for cat, d in per_cat_delta.items() if d > PARITY_TOLERANCE]

    if abs(delta) <= PARITY_TOLERANCE and not regressions:
        parity_status = "PARITY"
    elif delta > PARITY_TOLERANCE:
        parity_status = "IMPROVED"
    else:
        parity_status = "DIVERGED"

    return ParityReport(
        distributed_file=dist_file,
        baseline_file=base_file,
        distributed_score=dist_score,
        baseline_score=base_score,
        parity_delta=round(delta, 4),
        parity_pct=f"{delta * 100:+.1f}%",
        parity_status=parity_status,
        per_category_delta={k: round(v, 4) for k, v in per_cat_delta.items()},
        regressions=regressions,
        improvements=improvements,
    )


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def assessment_to_dict(a: RunAssessment) -> dict[str, Any]:
    return {
        "source_file": a.source_file,
        "eval_type": a.eval_type,
        "agent_count": a.agent_count,
        "num_turns": a.num_turns,
        "num_questions": a.num_questions,
        "overall_score": a.overall_score,
        "overall_score_pct": a.overall_score_pct,
        "pass_fail": a.pass_fail,
        "timing": a.timing,
        "memory_stats": a.memory_stats,
        "weakest_categories": a.weakest_categories,
        "strongest_categories": a.strongest_categories,
        "questions_below_threshold": a.questions_below_threshold,
        "category_stats": [
            {
                "category": cs.category,
                "num_questions": cs.num_questions,
                "avg_score": cs.avg_score,
                "min_score": cs.min_score,
                "max_score": cs.max_score,
                "dimension_averages": cs.dimension_averages,
            }
            for cs in a.category_stats
        ],
    }


def parity_to_dict(p: ParityReport) -> dict[str, Any]:
    return {
        "distributed_file": p.distributed_file,
        "baseline_file": p.baseline_file,
        "distributed_score": p.distributed_score,
        "baseline_score": p.baseline_score,
        "parity_delta": p.parity_delta,
        "parity_pct": p.parity_pct,
        "parity_status": p.parity_status,
        "per_category_delta": p.per_category_delta,
        "regressions": p.regressions,
        "improvements": p.improvements,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(
        description="Assess distributed eval output files and compare against baseline"
    )
    p.add_argument("files", nargs="*", help="Eval result JSON files to assess")
    p.add_argument("--distributed", default="", help="Distributed run result JSON")
    p.add_argument(
        "--baseline", default="", help="Single-agent baseline JSON for parity comparison"
    )
    p.add_argument("--dir", default="", help="Directory of eval result JSONs to batch-assess")
    p.add_argument("--output", default="", help="Write assessment JSON to this file")
    p.add_argument(
        "--threshold",
        type=float,
        default=PASS_THRESHOLD,
        help=f"Pass threshold (default: {PASS_THRESHOLD})",
    )
    args = p.parse_args()

    # Collect files
    all_files: list[str] = list(args.files)
    if args.distributed:
        all_files.append(args.distributed)
    if args.dir:
        all_files.extend(str(f) for f in Path(args.dir).glob("*.json"))

    if not all_files and not args.baseline:
        p.print_help()
        return 1

    assessments: list[dict[str, Any]] = []
    overall_ok = True

    for path in all_files:
        if not Path(path).exists():
            logger.error("File not found: %s", path)
            overall_ok = False
            continue
        try:
            data = load_run(path)
            a = assess_run(data, path)
        except Exception as exc:
            logger.error("Failed to assess %s: %s", path, exc)
            overall_ok = False
            continue

        # Print summary
        icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(a.pass_fail, "?")
        print(f"\n{icon} {Path(path).name}")
        print(f"  Type: {a.eval_type} | Agents: {a.agent_count} | Turns: {a.num_turns}")
        print(f"  Score: {a.overall_score_pct} [{a.pass_fail}]")
        if a.weakest_categories:
            print(f"  Weakest: {', '.join(a.weakest_categories)}")
        if a.questions_below_threshold:
            print(
                f"  Questions below {WARN_THRESHOLD * 100:.0f}%: {len(a.questions_below_threshold)}"
            )
            for q in a.questions_below_threshold:
                print(f"    - {q['question_id']} ({q['category']}): {q['score']:.2f}")

        if a.pass_fail == "FAIL":
            overall_ok = False

        assessments.append(assessment_to_dict(a))

    # Parity comparison
    parity: dict[str, Any] | None = None
    if args.distributed and args.baseline:
        try:
            dist_data = load_run(args.distributed)
            base_data = load_run(args.baseline)
            pr = compare_runs(dist_data, base_data, args.distributed, args.baseline)
            parity = parity_to_dict(pr)

            print(f"\n{'=' * 60}")
            print("  Retrieval Parity Analysis")
            print(
                f"  Distributed:  {pr.distributed_score * 100:.1f}% ({Path(args.distributed).name})"
            )
            print(f"  Baseline:     {pr.baseline_score * 100:.1f}% ({Path(args.baseline).name})")
            print(f"  Delta:        {pr.parity_pct} → {pr.parity_status}")
            if pr.regressions:
                print(f"  Regressions:  {', '.join(pr.regressions)}")
            if pr.improvements:
                print(f"  Improvements: {', '.join(pr.improvements)}")
            print(f"{'=' * 60}")

            if pr.parity_status == "DIVERGED":
                overall_ok = False
        except Exception as exc:
            logger.error("Parity comparison failed: %s", exc)

    # Output
    result: dict[str, Any] = {
        "assessments": assessments,
        "pass_threshold": args.threshold,
    }
    if parity:
        result["parity"] = parity

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        logger.info("Assessment written to %s", args.output)
    else:
        print(json.dumps(result, indent=2))

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
