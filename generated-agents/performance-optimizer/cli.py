"""
Command-line interface for the Performance Optimizer agent.
"""

import argparse
import sys
from pathlib import Path

from .agent import PerformanceOptimizer
from .metrics import calculate_metrics_from_stats, format_metrics_report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Performance Optimizer Learning Agent")
    parser.add_argument(
        "command", choices=["analyze", "stats", "patterns"], help="Command to execute"
    )
    parser.add_argument("file", nargs="?", help="Python file to analyze (for analyze command)")
    parser.add_argument("--memory-path", help="Path to memory storage (default: use agent default)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Create optimizer
    _ = Path(args.memory_path) if args.memory_path else None
    optimizer = PerformanceOptimizer()

    if args.command == "analyze":
        if not args.file:
            print("Error: analyze command requires a file argument")
            sys.exit(1)

        # Read and analyze file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)

        code = file_path.read_text()
        analysis = optimizer.optimize_code(code, str(file_path))

        # Display results
        print(f"\n=== Performance Analysis: {file_path} ===\n")
        print(f"Total lines: {analysis.total_lines}")
        print(f"Complexity score: {analysis.complexity_score:.1f}")
        print(f"Estimated speedup: {analysis.estimated_total_speedup:.2f}x")
        print(f"Estimated memory saved: {analysis.estimated_total_memory_saved} bytes\n")

        print(f"Found {len(analysis.optimizations)} optimization opportunities:\n")

        for opt in analysis.optimizations:
            status = "✓ APPLIED" if opt.applied else "○ SUGGESTED"
            print(f"{status} {opt.technique}")
            print(f"  Confidence: {opt.confidence:.2%}")
            print(f"  Speedup: {opt.estimated_speedup:.2f}x")
            print(f"  Reason: {opt.reason}")
            if args.verbose:
                print(f"  Before: {opt.original_code[:80]}...")
                print(f"  After:  {opt.optimized_code[:80]}...")
            print()

        if analysis.learned_insights:
            print("Insights:")
            for insight in analysis.learned_insights:
                print(f"  • {insight}")
            print()

    elif args.command == "stats":
        stats = optimizer.get_learning_stats()
        metrics = calculate_metrics_from_stats(stats)
        report = format_metrics_report(metrics)
        print(report)

    elif args.command == "patterns":
        from .optimization_patterns import OPTIMIZATION_PATTERNS, format_pattern_info

        print("\n=== Optimization Patterns Library ===\n")
        print(f"Total patterns: {len(OPTIMIZATION_PATTERNS)}\n")

        for pattern in OPTIMIZATION_PATTERNS.values():
            if args.verbose:
                print(format_pattern_info(pattern))
                print("\n" + "=" * 60 + "\n")
            else:
                print(
                    f"{pattern.name:40s} {pattern.category:15s} {pattern.estimated_speedup_min:.1f}x-{pattern.estimated_speedup_max:.1f}x"
                )


if __name__ == "__main__":
    main()
