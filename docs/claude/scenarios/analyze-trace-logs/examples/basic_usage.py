#!/usr/bin/env python3
"""
Basic usage examples for trace log analyzer.

This demonstrates common usage patterns for the analyze-trace-logs tool.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import TraceLogAnalyzer


def example_1_basic_analysis():
    """Example 1: Basic analysis with defaults."""
    print("=" * 80)
    print("Example 1: Basic Analysis")
    print("=" * 80)
    print()

    # Find trace logs in project
    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / ".claude-trace"

    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        print("Creating sample logs for demonstration...")
        log_dir = create_sample_logs()

    # Create analyzer
    analyzer = TraceLogAnalyzer()

    # Run analysis (15 most recent files)
    print(f"Analyzing logs in: {log_dir}")
    analysis = analyzer.analyze(log_dir, sample_size=5)

    # Display summary
    print(f"\nTotal messages analyzed: {analysis['total_messages']}")
    print(f"Files processed: {len(analysis['file_stats'])}")
    print("\nTop categories:")
    for category, count in analysis["categories"].most_common(5):
        print(f"  - {category}: {count}")

    print("\n" + "=" * 80 + "\n")


def example_2_custom_output():
    """Example 2: Custom output location."""
    print("=" * 80)
    print("Example 2: Custom Output Location")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / ".claude-trace"

    if not log_dir.exists():
        print("No trace logs found. Use Example 1 first.")
        return

    analyzer = TraceLogAnalyzer()

    # Analyze with custom output
    output_path = Path.cwd() / "custom_analysis.md"
    print(f"Output will be saved to: {output_path}")

    analysis = analyzer.analyze(log_dir, sample_size=10)
    analyzer.generate_report(analysis, output_path)

    print(f"\nReport generated: {output_path}")
    print(f"File size: {output_path.stat().st_size} bytes")

    print("\n" + "=" * 80 + "\n")


def example_3_large_sample():
    """Example 3: Deep analysis with large sample size."""
    print("=" * 80)
    print("Example 3: Deep Analysis (Large Sample)")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / ".claude-trace"

    if not log_dir.exists():
        print("No trace logs found. Use Example 1 first.")
        return

    analyzer = TraceLogAnalyzer()

    # Analyze 30 files for deeper insights
    print("Analyzing 30 most recent files...")
    analysis = analyzer.analyze(log_dir, sample_size=30)

    print("\nDeep analysis complete:")
    print(f"  Total messages: {analysis['total_messages']}")
    print(f"  Files processed: {len(analysis['file_stats'])}")

    # Show decision patterns
    if analysis["decision_patterns"]:
        print("\nDecision patterns found:")
        for pattern, examples in analysis["decision_patterns"].items():
            if examples:
                print(f"  - {pattern}: {len(examples)} instances")

    print("\n" + "=" * 80 + "\n")


def example_4_programmatic_access():
    """Example 4: Programmatic access to analysis data."""
    print("=" * 80)
    print("Example 4: Programmatic Access")
    print("=" * 80)
    print()

    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / ".claude-trace"

    if not log_dir.exists():
        print("No trace logs found.")
        return

    analyzer = TraceLogAnalyzer()
    analysis = analyzer.analyze(log_dir, sample_size=10)

    # Access specific data programmatically
    print("Programmatic data access:\n")

    # Most common verbs
    print("Top 5 task verbs:")
    for i, (verb, count) in enumerate(analysis["task_verbs"].most_common(5), 1):
        print(f"  {i}. {verb}: {count} occurrences")

    # Slash commands usage
    print(f"\nSlash commands used: {len(analysis['slash_commands'])}")
    for cmd, count in analysis["slash_commands"][:3]:
        print(f"  - {cmd}: {count} times")

    # Decision patterns
    print("\nUser preferences detected:")
    completeness = len(analysis["decision_patterns"].get("completeness_required", []))
    autonomy = len(analysis["decision_patterns"].get("high_autonomy", []))
    print(f"  - Completeness preference: {completeness} instances")
    print(f"  - High autonomy preference: {autonomy} instances")

    print("\n" + "=" * 80 + "\n")


def create_sample_logs():
    """Create sample logs for demonstration."""
    import json
    import tempfile

    temp_dir = Path(tempfile.mkdtemp())
    print(f"Creating sample logs in: {temp_dir}")

    sample_messages = [
        "Fix the authentication bug in user_service.py",
        "Create a new feature for profile management",
        "Analyze the codebase for performance issues",
        "Run tests and fix any failures",
        "/ultrathink implement the payment system",
        "Refactor the database queries for better performance",
        "Add documentation for the API endpoints",
        "Debug the CI pipeline failure",
        "Implement caching for frequently accessed data",
        "Review the security of the authentication flow",
    ]

    # Create 3 sample log files
    for i in range(3):
        log_file = temp_dir / f"sample_{i}.jsonl"
        with open(log_file, "w") as f:
            for j, msg in enumerate(sample_messages[i * 3 : (i + 1) * 3]):
                entry = {"request": {"body": {"messages": [{"role": "user", "content": msg}]}}}
                f.write(json.dumps(entry) + "\n")

    return temp_dir


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Trace Log Analyzer Examples" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    examples = [
        ("Basic Analysis", example_1_basic_analysis),
        ("Custom Output", example_2_custom_output),
        ("Deep Analysis", example_3_large_sample),
        ("Programmatic Access", example_4_programmatic_access),
    ]

    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print()

    choice = input("Select example (1-4) or 'all' to run all: ").strip().lower()

    if choice == "all":
        for name, func in examples:
            func()
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        examples[int(choice) - 1][1]()
    else:
        print("Invalid choice. Running Example 1...")
        example_1_basic_analysis()


if __name__ == "__main__":
    main()
