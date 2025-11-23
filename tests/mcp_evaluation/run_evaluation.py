#!/usr/bin/env python3
"""Example script for running MCP tool evaluation.

This script demonstrates how to:
1. Load a tool configuration
2. Create the evaluation framework
3. Run all test scenarios
4. Generate and save reports
"""

import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_evaluation.framework import (
    MCPEvaluationFramework,
    ReportGenerator,
)
from tests.mcp_evaluation.scenarios import get_all_scenarios
from tests.mcp_evaluation.tools import load_tool_config


def main():
    """Run MCP tool evaluation."""
    print("=" * 60)
    print("MCP Tool Evaluation Framework")
    print("=" * 60)

    # Configuration
    tool_name = "serena"  # Change this to evaluate different tools
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results" / f"{tool_name}_{timestamp}"

    print(f"\nEvaluating tool: {tool_name}")
    print(f"Results will be saved to: {results_dir}")

    # Load tool configuration
    print("\n[1/5] Loading tool configuration...")
    try:
        config = load_tool_config(tool_name)
        print(f"  ✓ Loaded {config.tool_name} v{config.version}")
        print(f"  ✓ {len(config.capabilities)} capabilities configured")

        # Validate configuration
        errors = config.validate()
        if errors:
            print("  ✗ Configuration validation failed:")
            for error in errors:
                print(f"    - {error}")
            return 1

    except FileNotFoundError as e:
        print(f"  ✗ Configuration not found: {e}")
        print("\n  Available tools:")
        tools_dir = Path(__file__).parent / "tools"
        for config_file in tools_dir.glob("*_config.yaml"):
            tool = config_file.stem.replace("_config", "")
            print(f"    - {tool}")
        return 1
    except Exception as e:
        print(f"  ✗ Failed to load configuration: {e}")
        return 1

    # Create framework
    print("\n[2/5] Creating evaluation framework...")
    try:
        framework = MCPEvaluationFramework(config)
        print("  ✓ Framework initialized")
        print(f"  ✓ Adapter: {config.adapter_class}")

        # Check tool availability
        if config.setup_required:
            print("\n  Tool setup required:")
            print(f"  {config.setup_instructions}")

            if config.health_check_url:
                is_available = framework.adapter.is_available()
                if is_available:
                    print("  ✓ Tool is available and healthy")
                else:
                    print("  ⚠ Tool health check failed (will use fallback behavior)")

    except Exception as e:
        print(f"  ✗ Failed to create framework: {e}")
        return 1

    # Get scenarios
    print("\n[3/5] Loading test scenarios...")
    try:
        scenarios = get_all_scenarios()
        print(f"  ✓ {len(scenarios)} scenarios loaded:")
        for scenario in scenarios:
            print(f"    - [{scenario.category.value}] {scenario.name}")
    except Exception as e:
        print(f"  ✗ Failed to load scenarios: {e}")
        return 1

    # Run evaluation
    print("\n[4/5] Running evaluation...")
    print(f"  This will run {len(scenarios)} scenarios in baseline and enhanced mode")
    print(f"  Total executions: {len(scenarios) * 2}")
    print()

    try:
        report = framework.run_evaluation(scenarios)
        print("\n  ✓ Evaluation complete!")
        print(f"  ✓ {len(report.results)} scenario comparisons")

    except KeyboardInterrupt:
        print("\n  ✗ Evaluation interrupted by user")
        return 1
    except Exception as e:
        print(f"  ✗ Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Save results
    print("\n[5/5] Saving results...")
    try:
        results_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        json_path = results_dir / "report.json"
        report.save_json(json_path)
        print(f"  ✓ JSON report: {json_path}")

        # Save markdown report
        md_path = results_dir / "report.md"
        generator = ReportGenerator(report)
        generator.save(md_path)
        print(f"  ✓ Markdown report: {md_path}")

    except Exception as e:
        print(f"  ✗ Failed to save results: {e}")
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    summary = report.summary
    print(f"\nScenarios: {summary['total_scenarios']}")
    print(f"  - Integrate recommended: {summary['integrate_recommended']}")
    print(f"  - Consider recommended: {summary['consider_recommended']}")

    print("\nPerformance:")
    print(f"  - Average time change: {summary['avg_time_improvement_percent']:+.1f}%")
    print(f"  - Average quality change: {summary['avg_quality_improvement']:+.1%}")

    print("\nRecommendations:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")

    print(f"\nDetailed results: {md_path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
