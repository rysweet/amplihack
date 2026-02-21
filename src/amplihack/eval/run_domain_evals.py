"""Run domain agent evaluations across all 5 domain agents.

Produces a summary report with per-agent, per-level scores.

Usage:
    PYTHONPATH=src python -m amplihack.eval.run_domain_evals
    PYTHONPATH=src python -m amplihack.eval.run_domain_evals --agents code_review meeting_synthesizer
    PYTHONPATH=src python -m amplihack.eval.run_domain_evals --output-dir ./eval_results
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from amplihack.agents.domain_agents.code_review import CodeReviewAgent
from amplihack.agents.domain_agents.data_analysis import DataAnalysisAgent
from amplihack.agents.domain_agents.document_creator import DocumentCreatorAgent
from amplihack.agents.domain_agents.meeting_synthesizer import MeetingSynthesizerAgent
from amplihack.agents.domain_agents.project_planning import ProjectPlanningAgent
from amplihack.eval.domain_eval_harness import DomainEvalHarness

AGENT_REGISTRY = {
    "code_review": CodeReviewAgent,
    "meeting_synthesizer": MeetingSynthesizerAgent,
    "document_creator": DocumentCreatorAgent,
    "data_analysis": DataAnalysisAgent,
    "project_planning": ProjectPlanningAgent,
}


def run_all_evals(
    agent_names: list[str] | None = None,
    output_dir: str = "./domain_eval_results",
) -> dict:
    """Run evals for specified (or all) domain agents.

    Args:
        agent_names: List of agent names to eval, or None for all
        output_dir: Directory to save results

    Returns:
        Dict with per-agent results
    """
    if agent_names is None:
        agent_names = list(AGENT_REGISTRY.keys())

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_results = {}

    for name in agent_names:
        if name not in AGENT_REGISTRY:
            print(f"WARNING: Unknown agent '{name}', skipping")
            continue

        print(f"\n{'=' * 60}")
        print(f"EVALUATING: {name}")
        print(f"{'=' * 60}")

        agent_class = AGENT_REGISTRY[name]
        agent = agent_class()
        harness = DomainEvalHarness(agent)

        try:
            report = harness.run()
            all_results[name] = report.to_dict()

            print(f"  Overall Score: {report.overall_score:.2%}")
            print(f"  Overall Passed: {report.overall_passed}")
            for level in report.levels:
                status = "PASS" if level.passed else "FAIL"
                print(
                    f"  {level.level_id} ({level.level_name}): "
                    f"{level.average_score:.2%} [{status}] "
                    f"({len(level.scenarios)} scenarios)"
                )
                for scenario in level.scenarios:
                    s_status = "PASS" if scenario.passed else "FAIL"
                    print(f"    {scenario.scenario_id}: {scenario.score:.2%} [{s_status}] - {scenario.scenario_name}")
                    if not scenario.passed:
                        print(f"      Details: {scenario.grading_details[:100]}")

            # Save individual agent report
            with open(output_path / f"{name}_eval.json", "w") as f:
                json.dump(report.to_dict(), f, indent=2)

        except Exception as e:
            print(f"  ERROR: {e}")
            all_results[name] = {"error": str(e)}

    # Save combined report
    combined_path = output_path / "all_domain_evals.json"
    with open(combined_path, "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for name, result in all_results.items():
        if "error" in result:
            print(f"  {name}: ERROR - {result['error']}")
        else:
            score = result.get("overall_score", 0)
            passed = result.get("overall_passed", False)
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {score:.2%} [{status}]")

    print(f"\nResults saved to: {output_path}")
    return all_results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Domain Agent Evaluations")
    parser.add_argument(
        "--agents", nargs="*", default=None,
        help="Agent names to evaluate (default: all)",
    )
    parser.add_argument(
        "--output-dir", default="./domain_eval_results",
        help="Output directory for results",
    )
    args = parser.parse_args()

    run_all_evals(agent_names=args.agents, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
