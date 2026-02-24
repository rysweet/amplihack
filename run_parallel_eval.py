#!/usr/bin/env python3
"""Run progressive eval N times in parallel with unique agent/DB pairs. Report medians."""
from __future__ import annotations

import json
import subprocess
import sys
import statistics
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_single_eval(run_id: int, levels: list[str]) -> dict:
    """Run one complete eval with a unique agent name."""
    agent_name = f"eval_run_{run_id}_{int(time.time())}"
    output_dir = f"/tmp/parallel_eval/run_{run_id}"

    # Clean previous
    import shutil
    shutil.rmtree(output_dir, ignore_errors=True)
    shutil.rmtree(f"/tmp/amplihack_eval/{agent_name}", ignore_errors=True)

    cmd = [
        sys.executable, "-m", "amplihack.eval.progressive_test_suite",
        "--output-dir", output_dir,
        "--agent-name", agent_name,
    ]
    if levels:
        cmd.extend(["--levels"] + levels)

    env = {**__import__("os").environ, "PYTHONPATH": "src"}
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1800)

    # Parse summary
    summary_path = Path(output_dir) / "summary.json"
    if summary_path.exists():
        return json.loads(summary_path.read_text())
    return {"error": result.stderr[:500], "run_id": run_id}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="Number of parallel runs")
    parser.add_argument("--levels", nargs="+", default=None)
    args = parser.parse_args()

    levels = args.levels or ["L1", "L2", "L3", "L4", "L5", "L6"]
    n_runs = args.runs

    print(f"Running {n_runs} parallel evals for levels: {', '.join(levels)}")
    print(f"Each run gets a unique agent name and Kuzu DB\n")

    # Run in parallel
    results = []
    with ProcessPoolExecutor(max_workers=min(n_runs, 4)) as executor:
        futures = {executor.submit(run_single_eval, i, levels): i for i in range(n_runs)}
        for future in as_completed(futures):
            run_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                if "error" in result:
                    print(f"  Run {run_id}: ERROR - {result['error'][:100]}")
                else:
                    scores = {lr["level_id"]: lr.get("average_score", 0)
                              for lr in result.get("level_results", [])}
                    print(f"  Run {run_id}: {scores}")
            except Exception as e:
                print(f"  Run {run_id}: EXCEPTION - {e}")

    # Compute medians per level
    print(f"\n{'='*70}")
    print(f"MEDIAN SCORES ({n_runs} runs)")
    print(f"{'='*70}\n")

    level_scores: dict[str, list[float]] = {}
    for result in results:
        if "error" in result:
            continue
        for lr in result.get("level_results", []):
            lid = lr["level_id"]
            score = lr.get("average_score", 0)
            level_scores.setdefault(lid, []).append(score)

    for level in sorted(level_scores.keys()):
        scores = level_scores[level]
        median = statistics.median(scores)
        all_scores = [f"{s:.0%}" for s in scores]
        print(f"  {level}: median={median:.0%}  runs={all_scores}")

    if level_scores:
        all_medians = [statistics.median(v) for v in level_scores.values()]
        overall = statistics.median(all_medians)
        print(f"\n  Overall median: {overall:.0%}")


if __name__ == "__main__":
    main()
