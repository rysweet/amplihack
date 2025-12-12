#!/usr/bin/env python3
"""
Automated Serena MCP Evaluation using amplihack auto mode.

Runs 3 test scenarios both WITH and WITHOUT Serena MCP enabled,
collecting real metrics for comparison.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict

# Test scenarios
SCENARIOS = [
    {
        "id": "scenario1_navigation",
        "name": "Find Handler Implementations",
        "prompt_file": "/tmp/serena_eval_scenario1_baseline.md",
    },
    {
        "id": "scenario2_analysis",
        "name": "Map DatabaseService Dependencies",
        "prompt_file": "/tmp/serena_eval_scenario2_baseline.md",
    },
    {
        "id": "scenario3_modification",
        "name": "Add Type Hints to UserService",
        "prompt_file": "/tmp/serena_eval_scenario3_baseline.md",
    },
]


def run_amplihack_auto(goal_file: str, enable_serena: bool, output_dir: Path) -> Dict:
    """Run amplihack in auto mode with given goal."""
    print(f"  Running {'WITH' if enable_serena else 'WITHOUT'} Serena...")

    # Prepare settings (with or without Serena)
    settings_file = output_dir / "settings.json"
    with open(settings_file, "w") as f:
        settings = {"enabledMcpjsonServers": []}
        if enable_serena:
            settings["enabledMcpjsonServers"].append(
                {
                    "name": "serena",
                    "command": "uvx",
                    "args": ["--from", "git+https://github.com/oraios/serena", "serena"],
                }
            )
        json.dump(settings, f, indent=2)

    # Run amplihack auto mode with correct syntax
    # Read goal prompt
    with open(goal_file) as f:
        goal_prompt = f.read()

    cmd = [
        "amplihack",
        "claude",
        "--auto",
        "--max-turns",
        "10",
        "--checkout-repo",
        str(output_dir),
        "--",
        "-p",
        goal_prompt,
    ]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    end_time = time.time()

    # Collect metrics
    metrics = {
        "time_seconds": end_time - start_time,
        "exit_code": result.returncode,
        "stdout_length": len(result.stdout),
        "stderr_length": len(result.stderr),
    }

    # Save output
    (output_dir / "stdout.txt").write_text(result.stdout)
    (output_dir / "stderr.txt").write_text(result.stderr)

    print(f"    Time: {metrics['time_seconds']:.1f}s, Exit: {metrics['exit_code']}")

    return metrics


def main():
    """Run complete evaluation."""
    print("=" * 70)
    print("SERENA MCP EVALUATION - Real Testing with Auto Mode")
    print("=" * 70)

    results = []

    for scenario in SCENARIOS:
        print(f"\n[{scenario['id']}] {scenario['name']}")

        # Create output directories
        baseline_dir = Path(f"/tmp/eval_results/{scenario['id']}_baseline")
        serena_dir = Path(f"/tmp/eval_results/{scenario['id']}_serena")
        baseline_dir.mkdir(parents=True, exist_ok=True)
        serena_dir.mkdir(parents=True, exist_ok=True)

        # Run baseline (no Serena)
        baseline_metrics = run_amplihack_auto(
            scenario["prompt_file"], enable_serena=False, output_dir=baseline_dir
        )

        # Run with Serena
        serena_metrics = run_amplihack_auto(
            scenario["prompt_file"], enable_serena=True, output_dir=serena_dir
        )

        # Calculate improvements
        time_delta = (
            (serena_metrics["time_seconds"] - baseline_metrics["time_seconds"])
            / baseline_metrics["time_seconds"]
            * 100
        )

        result = {
            "scenario": scenario["name"],
            "baseline": baseline_metrics,
            "serena": serena_metrics,
            "improvement": {
                "time_percent": time_delta,
            },
        }
        results.append(result)

        print(f"  Baseline: {baseline_metrics['time_seconds']:.1f}s")
        print(f"  Serena:   {serena_metrics['time_seconds']:.1f}s")
        print(f"  Delta:    {time_delta:+.1f}%")

    # Save results
    results_file = Path("/tmp/eval_results/serena_evaluation_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"Results saved to: {results_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
