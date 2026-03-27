#!/usr/bin/env python3
"""Generic self-improving parity audit cycle.

Runs all parity scenarios, categorizes failures, generates fix
specifications, and supports iterative re-validation until 100%.

Usage:
    # Full audit
    python parity_audit_cycle.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenarios-dir ./tests/parity/scenarios/

    # Validate only (no fix specs)
    python parity_audit_cycle.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenarios-dir ./tests/parity/scenarios/ \\
        --validate-only

    # Generate fix workstream specs
    python parity_audit_cycle.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenarios-dir ./tests/parity/scenarios/ \\
        --generate-fix-specs

    # Run specific scenario files
    python parity_audit_cycle.py \\
        --legacy "python -m myapp.cli" \\
        --candidate "./target/debug/myapp" \\
        --scenario tests/smoke.yaml tests/install.yaml

The audit cycle pattern:
    1. IDENTIFY — Run all scenarios, collect divergences
    2. CATEGORIZE — Group failures by area (install, launch, etc.)
    3. SPECIFY — Generate fix workstream specifications
    4. (Human/agent fixes the code)
    5. RE-VALIDATE — Run again to check progress
    6. REPEAT until 100%
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import the harness (same directory)
sys.path.insert(0, str(Path(__file__).parent))
from shadow_parity_harness import (
    HarnessConfig,
    load_scenarios,
    parse_command,
    run_harness,
)


# ---------------------------------------------------------------------------
# Audit types
# ---------------------------------------------------------------------------

def categorize_failures(summary: dict[str, Any]) -> dict[str, list[str]]:
    """Categorize divergences into fix workstream buckets."""
    categories: dict[str, list[str]] = {}
    for detail in summary.get("divergence_details", []):
        case = detail["case"]
        # Use the category from the scenario, or infer from name
        cat = _infer_category(case)
        categories.setdefault(cat, []).append(case)
    return {k: v for k, v in categories.items() if v}


def _infer_category(case_name: str) -> str:
    """Infer category from case name using keyword matching."""
    keywords = {
        "install": ["install", "uninstall", "manifest"],
        "launch": ["launch", "launcher", "sigint", "claude"],
        "recipe": ["recipe", "validate", "live-recipe"],
        "plugin": ["plugin"],
        "memory": ["memory", "tree", "export", "import"],
        "settings": ["settings", "config"],
        "hooks": ["hook"],
        "environment": ["env", "runtime", "session"],
    }
    lower = case_name.lower()
    for cat, kws in keywords.items():
        if any(kw in lower for kw in kws):
            return cat
    return "other"


def generate_fix_specs(
    categories: dict[str, list[str]],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate actionable fix workstream specifications."""
    specs = []
    for cat, cases in sorted(categories.items()):
        priority = "critical" if len(cases) >= 5 else "high" if len(cases) >= 3 else "medium" if len(cases) >= 1 else "low"
        specs.append({
            "workstream_id": f"fix-{cat}",
            "category": cat,
            "failing_cases": cases,
            "case_count": len(cases),
            "priority": priority,
            "description": f"Fix {cat} parity: {len(cases)} cases diverge between legacy and candidate",
            "validation_command": f"python {__file__} --scenario <files> --case " + " --case ".join(cases[:5]),
        })
    specs.sort(key=lambda s: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(s["priority"], 99))
    return specs


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    cycle_id: str,
    summary: dict[str, Any],
    categories: dict[str, list[str]],
    fix_specs: list[dict[str, Any]],
) -> None:
    """Print human-readable audit report."""
    total = summary["total"]
    matched = summary["matched"]
    diverged = summary["diverged"]

    print(f"\n{'='*70}")
    print(f"PARITY AUDIT CYCLE: {cycle_id}")
    print(f"{'='*70}")
    print(f"Total: {total}  Passed: {matched}  Failed: {diverged}  Rate: {summary['parity_rate']}")

    if categories:
        print(f"\n--- Gap Categories ---")
        for cat, cases in sorted(categories.items()):
            print(f"  {cat}: {len(cases)} failures")
            for c in cases[:3]:
                print(f"    - {c}")
            if len(cases) > 3:
                print(f"    ... and {len(cases) - 3} more")

    if fix_specs:
        print(f"\n--- Fix Workstream Specs ---")
        for spec in fix_specs:
            print(f"\n  [{spec['priority'].upper()}] {spec['workstream_id']}")
            print(f"    Cases: {spec['case_count']}")
            print(f"    {spec['description']}")

    print(f"\n{'='*70}")
    if diverged == 0:
        print("ALL TESTS PASS — 100% PARITY ACHIEVED")
    else:
        print(f"GAPS REMAIN: {diverged} failures across {len(categories)} categories")
    print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Self-improving parity audit cycle")
    parser.add_argument("--legacy", required=True, help="Legacy command")
    parser.add_argument("--candidate", required=True, help="Candidate command")
    parser.add_argument("--scenarios-dir", type=Path, help="Directory of scenario YAML files")
    parser.add_argument("--scenario", nargs="*", type=Path, help="Specific scenario file(s)")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--generate-fix-specs", action="store_true")
    parser.add_argument("--log-dir", type=Path, default=Path("/tmp/parity-audit"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--case", action="append", help="Run only named case(s)")
    parser.add_argument("--output", type=Path, help="Write JSON audit result to file")
    args = parser.parse_args()

    cycle_id = f"audit-{int(time.time())}"
    args.log_dir.mkdir(parents=True, exist_ok=True)

    # Collect scenario files
    scenario_files: list[Path] = []
    if args.scenarios_dir:
        scenario_files.extend(sorted(args.scenarios_dir.glob("*.yaml")))
    if args.scenario:
        scenario_files.extend(args.scenario)
    if not scenario_files:
        print("ERROR: Provide --scenarios-dir or --scenario.", file=sys.stderr)
        return 1

    cases = load_scenarios(scenario_files)
    if args.case:
        requested = set(args.case)
        cases = [c for c in cases if c["name"] in requested]

    config = HarnessConfig(
        legacy_command=parse_command(args.legacy),
        candidate_command=parse_command(args.candidate),
        log_dir=args.log_dir / cycle_id,
        default_timeout=args.timeout,
    )

    print(f"Parity Audit: {cycle_id}")
    print(f"Legacy: {args.legacy}")
    print(f"Candidate: {args.candidate}")
    print(f"Scenarios: {len(scenario_files)} files, {len(cases)} cases")

    summary = run_harness(config, cases)

    categories = categorize_failures(summary)
    fix_specs = [] if args.validate_only else generate_fix_specs(categories, summary)

    print_report(cycle_id, summary, categories, fix_specs)

    output_path = args.output or (args.log_dir / f"{cycle_id}.json")
    output_path.write_text(json.dumps({
        "cycle_id": cycle_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **summary,
        "gap_categories": categories,
        "fix_specs": fix_specs,
    }, indent=2), encoding="utf-8")
    print(f"\nResult: {output_path}")

    return 0 if summary["diverged"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
