"""
CLI tool for mapping subagent executions.

Provides command-line interface to analyze subagent metrics and generate reports.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .metrics_reader import MetricsReader
from .visualization import ReportGenerator


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: List of arguments. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="amplihack subagent-mapper",
        description="Analyze and visualize subagent execution patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  amplihack subagent-mapper                          # Current session
  amplihack subagent-mapper --session-id ID          # Specific session
  amplihack subagent-mapper --agent architect        # Filter by agent
  amplihack subagent-mapper --output json            # Export JSON
  amplihack subagent-mapper --stats                  # Performance stats
  amplihack subagent-mapper --list-sessions          # Show available sessions
        """
    )

    parser.add_argument(
        "--session-id",
        type=str,
        help="Analyze specific session ID (default: most recent)"
    )

    parser.add_argument(
        "--agent",
        type=str,
        help="Filter by specific agent name"
    )

    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show detailed performance statistics"
    )

    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all available session IDs"
    )

    parser.add_argument(
        "--metrics-dir",
        type=Path,
        help="Path to metrics directory (default: .claude/runtime/metrics/)"
    )

    return parser.parse_args(args)


def list_sessions(reader: MetricsReader) -> int:
    """
    List all available sessions.

    Args:
        reader: MetricsReader instance.

    Returns:
        Exit code (0 for success).
    """
    session_ids = reader.get_session_ids()

    if not session_ids:
        print("No sessions found in metrics.")
        return 0

    print("Available Sessions:")
    print("=" * 64)
    for i, session_id in enumerate(session_ids, 1):
        marker = "(latest)" if i == 1 else ""
        print(f"{i}. {session_id} {marker}")

    return 0


def show_stats(reader: MetricsReader, session_id: Optional[str], agent_filter: Optional[str]) -> int:
    """
    Show detailed performance statistics.

    Args:
        reader: MetricsReader instance.
        session_id: Session ID to analyze.
        agent_filter: Agent name filter.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    # Determine session
    if session_id is None:
        session_id = reader.get_latest_session_id()
        if session_id is None:
            print("Error: No sessions found in metrics.", file=sys.stderr)
            return 1

    # Get stats
    stats = reader.get_agent_stats(session_id=session_id, agent_name=agent_filter)

    print(f"Performance Statistics - Session: {session_id}")
    print("=" * 64)
    print()

    print(f"Total Executions: {stats['total_executions']}")
    print(f"Total Duration: {stats['total_duration_ms']/1000:.2f}s")

    if stats['total_executions'] > 0:
        print(f"Average Duration: {stats['avg_duration_ms']/1000:.2f}s")
        print(f"Min Duration: {stats['min_duration_ms']/1000:.2f}s")
        print(f"Max Duration: {stats['max_duration_ms']/1000:.2f}s")

    print()
    print("Agent Execution Counts:")
    if stats['agents']:
        # Sort by count (descending)
        sorted_agents = sorted(
            stats['agents'].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for agent_name, count in sorted_agents:
            pct = (count / stats['total_executions'] * 100) if stats['total_executions'] > 0 else 0
            bar = "#" * (count * 40 // max(c for _, c in sorted_agents))
            print(f"  {agent_name:20} {count:3} ({pct:5.1f}%) {bar}")
    else:
        print("  No agent data available")

    return 0


def generate_report(
    reader: MetricsReader,
    generator: ReportGenerator,
    session_id: Optional[str],
    agent_filter: Optional[str],
    output_format: str
) -> int:
    """
    Generate and display report.

    Args:
        reader: MetricsReader instance.
        generator: ReportGenerator instance.
        session_id: Session ID to analyze.
        agent_filter: Agent name filter.
        output_format: Output format ("text" or "json").

    Returns:
        Exit code (0 for success, 1 for error).
    """
    if output_format == "json":
        report = generator.generate_json_report(
            session_id=session_id,
            agent_filter=agent_filter
        )

        if "error" in report:
            print(f"Error: {report['error']}", file=sys.stderr)
            return 1

        print(json.dumps(report, indent=2))
    else:
        report = generator.generate_text_report(
            session_id=session_id,
            agent_filter=agent_filter
        )
        print(report)

    return 0


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        args: List of arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parsed_args = parse_args(args)

    # Initialize reader
    reader = MetricsReader(metrics_dir=parsed_args.metrics_dir)

    # Handle --list-sessions
    if parsed_args.list_sessions:
        return list_sessions(reader)

    # Handle --stats
    if parsed_args.stats:
        return show_stats(reader, parsed_args.session_id, parsed_args.agent)

    # Generate report
    generator = ReportGenerator(reader)
    return generate_report(
        reader,
        generator,
        parsed_args.session_id,
        parsed_args.agent,
        parsed_args.output
    )


if __name__ == "__main__":
    sys.exit(main())
