#!/usr/bin/env python3
"""Reproducible eval summary report generator.

Reads one or more eval result JSON files and produces a human-readable
Markdown or plain-text report.  Deterministic: same inputs always produce
the same output — suitable for committing to the repo or attaching to PRs.

Usage:
    # Single run
    python deploy/azure_hive/eval_report.py results.json

    # Compare distributed vs baseline (parity report)
    python deploy/azure_hive/eval_report.py \\
        --distributed results_distributed.json \\
        --baseline results_single_agent.json \\
        --output EVAL_REPORT.md

    # Batch report for all runs in a directory
    python deploy/azure_hive/eval_report.py --dir /tmp/eval_runs/

    # JSON assessment input (from eval_assess.py)
    python deploy/azure_hive/eval_report.py --assessment assessment.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_BANNER = "=" * 70


def _fmt_score(score: float) -> str:
    pct = score * 100
    if pct >= 90:
        return f"{pct:.1f}% ✓"
    if pct >= 80:
        return f"{pct:.1f}% ⚠"
    return f"{pct:.1f}% ✗"


def _fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"


# ---------------------------------------------------------------------------
# Single-run report
# ---------------------------------------------------------------------------


def _report_single(data: dict[str, Any], title: str = "") -> str:
    lines: list[str] = []

    eval_type = data.get("eval_type", "unknown")
    agent_count = int(data.get("agent_count", data.get("memory_stats", {}).get("agent_count", 1)))
    num_turns = data.get("num_turns", 0)
    num_questions = data.get("num_questions", 0)
    overall_score = float(data.get("overall_score", 0.0))

    heading = title or f"Eval Report — {eval_type} ({agent_count} agents)"
    lines.append(f"## {heading}")
    lines.append("")
    lines.append("| Field           | Value |")
    lines.append("|-----------------|-------|")
    lines.append(f"| Eval type       | `{eval_type}` |")
    lines.append(f"| Agents          | {agent_count} |")
    lines.append(f"| Turns           | {num_turns:,} |")
    lines.append(f"| Questions       | {num_questions} |")
    lines.append(f"| **Overall score** | **{_fmt_score(overall_score)}** |")

    # Timing
    learning_s = float(data.get("learning_time_s", 0.0))
    questioning_s = float(data.get("questioning_time_s", 0.0))
    grading_s = float(data.get("grading_time_s", 0.0))
    total_s = learning_s + questioning_s + grading_s
    if total_s > 0:
        lines.append(f"| Learning time   | {_fmt_time(learning_s)} |")
        lines.append(f"| Questioning time | {_fmt_time(questioning_s)} |")
        lines.append(f"| Grading time    | {_fmt_time(grading_s)} |")
        lines.append(f"| **Total time**  | **{_fmt_time(total_s)}** |")

    lines.append("")

    # Category breakdown
    cats = data.get("category_breakdown", [])
    if cats:
        lines.append("### Category Breakdown")
        lines.append("")
        lines.append("| Category | Questions | Avg Score |")
        lines.append("|----------|-----------|-----------|")
        for cat in sorted(cats, key=lambda c: c.get("category", "")):
            avg = float(cat.get("avg_score", 0.0))
            lines.append(
                f"| {cat['category']} | {cat.get('num_questions', 0)} | {_fmt_score(avg)} |"
            )
        lines.append("")

    # Question-level results
    results = data.get("results", [])
    low_score_results = [r for r in results if float(r.get("overall_score", 1.0)) < 0.9]
    if low_score_results:
        lines.append("### Questions Below 90%")
        lines.append("")
        for r in sorted(low_score_results, key=lambda x: float(x.get("overall_score", 0.0))):
            score = float(r.get("overall_score", 0.0))
            lines.append(
                f"- **{r.get('question_id', '?')}** ({r.get('category', '?')}): "
                f"{score * 100:.0f}%  \n"
                f"  Q: {r.get('question_text', '')[:80]}  \n"
                f"  Expected: {str(r.get('expected_answer', ''))[:60]}"
            )
        lines.append("")

    # Memory stats
    mem = data.get("memory_stats", {})
    if mem:
        lines.append("### Memory Stats")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(mem, indent=2))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parity section
# ---------------------------------------------------------------------------


def _report_parity(
    dist_data: dict[str, Any],
    base_data: dict[str, Any],
    dist_file: str,
    base_file: str,
) -> str:
    lines: list[str] = []
    lines.append("## Retrieval Parity Analysis")
    lines.append("")

    dist_score = float(dist_data.get("overall_score", 0.0))
    base_score = float(base_data.get("overall_score", 0.0))
    delta = dist_score - base_score
    delta_pct = delta * 100

    if abs(delta) <= 0.05 and delta >= -0.05:
        status = "✓ PARITY"
        status_note = "Distributed is within ±5% of single-agent baseline."
    elif delta > 0.05:
        status = "↑ IMPROVED"
        status_note = f"Distributed outperforms single-agent by {delta_pct:+.1f}%."
    else:
        status = "✗ DIVERGED"
        status_note = (
            f"Distributed underperforms baseline by {delta_pct:.1f}%. Retrieval regression!"
        )

    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Distributed score | {_fmt_score(dist_score)} (`{Path(dist_file).name}`) |")
    lines.append(f"| Baseline score    | {_fmt_score(base_score)} (`{Path(base_file).name}`) |")
    lines.append(f"| Delta             | {delta_pct:+.1f}% |")
    lines.append(f"| **Status**        | **{status}** |")
    lines.append("")
    lines.append(f"_{status_note}_")
    lines.append("")

    # Per-category delta
    base_cats: dict[str, float] = {
        c["category"]: float(c.get("avg_score", 0.0))
        for c in base_data.get("category_breakdown", [])
    }
    dist_cats: dict[str, float] = {
        c["category"]: float(c.get("avg_score", 0.0))
        for c in dist_data.get("category_breakdown", [])
    }
    all_cats = sorted(set(base_cats) | set(dist_cats))

    if all_cats:
        lines.append("### Per-Category Delta (distributed − baseline)")
        lines.append("")
        lines.append("| Category | Baseline | Distributed | Delta |")
        lines.append("|----------|----------|-------------|-------|")
        for cat in all_cats:
            b = base_cats.get(cat, 0.0)
            d = dist_cats.get(cat, 0.0)
            diff = d - b
            flag = " ⚠" if diff < -0.05 else (" ↑" if diff > 0.05 else "")
            lines.append(f"| {cat} | {b * 100:.1f}% | {d * 100:.1f}% | {diff * 100:+.1f}%{flag} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Top-level report builder
# ---------------------------------------------------------------------------


def build_report(
    distributed: str = "",
    baseline: str = "",
    extra_files: list[str] | None = None,
) -> str:
    lines: list[str] = []
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# Distributed Eval Report")
    lines.append("")
    lines.append(f"_Generated: {ts}_")
    lines.append("")

    # Parity comparison (most prominent section)
    if distributed and baseline:
        try:
            dist_data = json.loads(Path(distributed).read_text())
            base_data = json.loads(Path(baseline).read_text())
            lines.append(_report_parity(dist_data, base_data, distributed, baseline))
        except Exception as exc:
            lines.append(f"> ⚠ Parity comparison failed: {exc}\n")

    # Individual run reports
    files_to_report: list[str] = []
    if distributed:
        files_to_report.append(distributed)
    if baseline:
        files_to_report.append(baseline)
    if extra_files:
        files_to_report.extend(extra_files)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique_files: list[str] = []
    for f in files_to_report:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    for path in unique_files:
        if not Path(path).exists():
            lines.append(f"> ⚠ File not found: {path}\n")
            continue
        try:
            data = json.loads(Path(path).read_text())
            lines.append(_report_single(data, title=f"Run: {Path(path).name}"))
        except Exception as exc:
            lines.append(f"> ⚠ Failed to load {path}: {exc}\n")

    lines.append("---")
    lines.append("_Report generated by `deploy/azure_hive/eval_report.py`_")

    return "\n".join(lines)


def build_report_from_assessment(assessment: dict[str, Any]) -> str:
    """Build a report from eval_assess.py output."""
    lines: list[str] = []
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines.append("# Distributed Eval Assessment Report")
    lines.append("")
    lines.append(f"_Generated: {ts}_")
    lines.append("")

    # Parity section
    parity = assessment.get("parity", {})
    if parity:
        status = parity.get("parity_status", "UNKNOWN")
        delta_pct = parity.get("parity_pct", "?")
        lines.append(f"## Retrieval Parity: {status} ({delta_pct})")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Distributed score | {parity['distributed_score'] * 100:.1f}% |")
        lines.append(f"| Baseline score    | {parity['baseline_score'] * 100:.1f}% |")
        lines.append(f"| Delta             | {parity['parity_pct']} |")
        if parity.get("regressions"):
            lines.append(f"| Regressions | {', '.join(parity['regressions'])} |")
        lines.append("")

    # Individual assessments
    for a in assessment.get("assessments", []):
        heading = f"Run: {Path(a.get('source_file', 'unknown')).name}"
        lines.append(f"## {heading}")
        lines.append("")
        lines.append(f"**Score**: {a.get('overall_score_pct', '?')} [{a.get('pass_fail', '?')}]  ")
        lines.append(
            f"**Type**: {a.get('eval_type', '?')} | "
            f"**Agents**: {a.get('agent_count', '?')} | "
            f"**Turns**: {a.get('num_turns', 0):,}"
        )
        lines.append("")

        cats = a.get("category_stats", [])
        if cats:
            lines.append("| Category | Avg Score |")
            lines.append("|----------|-----------|")
            for cs in sorted(cats, key=lambda c: c["category"]):
                lines.append(f"| {cs['category']} | {cs['avg_score'] * 100:.1f}% |")
            lines.append("")

        below = a.get("questions_below_threshold", [])
        if below:
            lines.append(f"⚠ {len(below)} question(s) below threshold:")
            for q in below:
                lines.append(f"- {q['question_id']} ({q['category']}): {q['score'] * 100:.0f}%")
            lines.append("")

    lines.append("---")
    lines.append("_Report generated by `deploy/azure_hive/eval_report.py`_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Generate reproducible eval summary report")
    p.add_argument("files", nargs="*", help="Eval result JSON files")
    p.add_argument("--distributed", default="", help="Distributed run result JSON")
    p.add_argument("--baseline", default="", help="Single-agent baseline JSON")
    p.add_argument("--assessment", default="", help="Assessment JSON (from eval_assess.py)")
    p.add_argument("--dir", default="", help="Directory of eval result JSONs")
    p.add_argument("--output", default="", help="Output file path (default: stdout)")
    args = p.parse_args()

    # Collect extra files
    extra_files: list[str] = list(args.files)
    if args.dir:
        extra_files.extend(str(f) for f in sorted(Path(args.dir).glob("*.json")))
    # Remove duplicates with distributed/baseline
    for f in (args.distributed, args.baseline):
        if f and f in extra_files:
            extra_files.remove(f)

    if args.assessment:
        try:
            assessment = json.loads(Path(args.assessment).read_text())
            report = build_report_from_assessment(assessment)
        except Exception as exc:
            print(f"Error loading assessment: {exc}", file=sys.stderr)
            return 1
    elif args.distributed or args.baseline or extra_files:
        report = build_report(
            distributed=args.distributed,
            baseline=args.baseline,
            extra_files=extra_files or None,
        )
    else:
        p.print_help()
        return 1

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
