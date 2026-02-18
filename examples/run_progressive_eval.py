#!/usr/bin/env python
"""Example script to run the progressive test suite.

This demonstrates how to use the progressive evaluation framework
to test an agent across 6 levels of increasing cognitive complexity.

Usage:
    python examples/run_progressive_eval.py
    python examples/run_progressive_eval.py --levels L1 L2 L3
    python examples/run_progressive_eval.py --output-dir ./my_eval_results
"""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.eval.progressive_test_suite import (
    ProgressiveConfig,
    run_progressive_suite,
)


def main():
    """Run progressive test suite example."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Progressive Agent Learning Test Suite Example"
    )
    parser.add_argument(
        "--output-dir",
        default="./eval_progressive_example",
        help="Output directory for results"
    )
    parser.add_argument(
        "--agent-name",
        default="example-agent",
        help="Agent name for memory isolation"
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=["L1", "L2", "L3", "L4", "L5", "L6"],
        help="Specific levels to run (default: all)"
    )

    args = parser.parse_args()

    config = ProgressiveConfig(
        output_dir=args.output_dir,
        agent_name=args.agent_name,
        levels_to_run=args.levels
    )

    print("=" * 70)
    print("PROGRESSIVE AGENT LEARNING TEST SUITE - EXAMPLE")
    print("=" * 70)
    print(f"Output directory: {config.output_dir}")
    print(f"Agent name: {config.agent_name}")
    if config.levels_to_run:
        print(f"Levels to run: {', '.join(config.levels_to_run)}")
    else:
        print("Levels to run: All (L1-L6)")
    print("=" * 70)
    print()
    print("This example demonstrates the progressive test suite structure.")
    print("For actual evaluation, the agent subprocess needs to be implemented.")
    print()

    result = run_progressive_suite(config)

    # Print summary
    print("\n" + "=" * 70)
    print("EXAMPLE RUN SUMMARY")
    print("=" * 70)

    if result.success:
        print("\n✓ All levels completed successfully\n")
    else:
        print(f"\n✗ Some levels failed: {result.error_message}\n")

    if result.overall_scores:
        print("Scores by Level:")
        for level_result in result.level_results:
            if level_result.success:
                score = level_result.scores["average"]
                count = level_result.scores["count"]
                print(f"  {level_result.level_id} ({level_result.level_name}): "
                      f"{score:.2%} ({count} questions)")
            else:
                print(f"  {level_result.level_id} ({level_result.level_name}): FAILED - {level_result.error_message}")

        print(f"\nOverall Average: {result.overall_scores['overall']:.2%}")
        print(f"Levels Passed: {result.overall_scores['levels_passed']}/{result.overall_scores['levels_total']}")

    print(f"\nDetailed results saved to: {config.output_dir}")

    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
