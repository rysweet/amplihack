#!/usr/bin/env python
"""
Example usage of the Subagent Mapper Tool.

Demonstrates all major features of the analytics module.
"""

import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.amplihack.analytics import (
    MetricsReader,
    ReportGenerator,
    ExecutionTreeBuilder,
    PatternDetector,
    AsciiTreeRenderer,
)


def create_example_metrics(metrics_dir: Path):
    """Create example metrics data."""

    # Example execution sequence:
    # orchestrator → architect → analyzer
    # orchestrator → builder → reviewer
    # orchestrator → builder → tester

    start_events = [
        {
            "event": "start",
            "agent_name": "orchestrator",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:30:00.000Z",
            "parent_agent": None,
            "execution_id": "exec_001"
        },
        {
            "event": "start",
            "agent_name": "architect",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:30:05.000Z",
            "parent_agent": "orchestrator",
            "execution_id": "exec_002"
        },
        {
            "event": "start",
            "agent_name": "analyzer",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:30:50.000Z",
            "parent_agent": "architect",
            "execution_id": "exec_003"
        },
        {
            "event": "start",
            "agent_name": "builder",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:31:05.000Z",
            "parent_agent": "orchestrator",
            "execution_id": "exec_004"
        },
        {
            "event": "start",
            "agent_name": "reviewer",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:33:05.000Z",
            "parent_agent": "builder",
            "execution_id": "exec_005"
        },
        {
            "event": "start",
            "agent_name": "builder",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:33:35.000Z",
            "parent_agent": "orchestrator",
            "execution_id": "exec_006"
        },
        {
            "event": "start",
            "agent_name": "tester",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:35:35.000Z",
            "parent_agent": "builder",
            "execution_id": "exec_007"
        }
    ]

    stop_events = [
        {
            "event": "stop",
            "agent_name": "orchestrator",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:36:00.000Z",
            "execution_id": "exec_001",
            "duration_ms": 360000.0
        },
        {
            "event": "stop",
            "agent_name": "architect",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:31:00.000Z",
            "execution_id": "exec_002",
            "duration_ms": 55000.0
        },
        {
            "event": "stop",
            "agent_name": "analyzer",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:31:02.000Z",
            "execution_id": "exec_003",
            "duration_ms": 12000.0
        },
        {
            "event": "stop",
            "agent_name": "builder",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:33:05.000Z",
            "execution_id": "exec_004",
            "duration_ms": 120000.0
        },
        {
            "event": "stop",
            "agent_name": "reviewer",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:33:35.000Z",
            "execution_id": "exec_005",
            "duration_ms": 30000.0
        },
        {
            "event": "stop",
            "agent_name": "builder",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:35:35.000Z",
            "execution_id": "exec_006",
            "duration_ms": 120000.0
        },
        {
            "event": "stop",
            "agent_name": "tester",
            "session_id": "example_session",
            "timestamp": "2025-11-02T14:36:00.000Z",
            "execution_id": "exec_007",
            "duration_ms": 25000.0
        }
    ]

    # Write files
    with open(metrics_dir / "subagent_start.jsonl", "w") as f:
        for event in start_events:
            f.write(json.dumps(event) + "\n")

    with open(metrics_dir / "subagent_stop.jsonl", "w") as f:
        for event in stop_events:
            f.write(json.dumps(event) + "\n")


def main():
    """Run example usage."""

    print("=" * 64)
    print("Subagent Mapper Tool - Example Usage")
    print("=" * 64)
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir)

        # Create example data
        print("Creating example metrics...")
        create_example_metrics(metrics_dir)
        print("✓ Example metrics created")
        print()

        # Initialize reader
        print("Initializing MetricsReader...")
        reader = MetricsReader(metrics_dir=metrics_dir)
        print("✓ MetricsReader initialized")
        print()

        # Example 1: Read events
        print("Example 1: Reading Events")
        print("-" * 64)
        events = reader.read_events(session_id="example_session")
        print(f"Total events: {len(events)}")

        start_count = sum(1 for e in events if e.event_type == "start")
        stop_count = sum(1 for e in events if e.event_type == "stop")
        print(f"Start events: {start_count}")
        print(f"Stop events: {stop_count}")
        print()

        # Example 2: Build executions
        print("Example 2: Building Executions")
        print("-" * 64)
        executions = reader.build_executions(session_id="example_session")
        print(f"Complete executions: {len(executions)}")
        print()
        print("Execution details:")
        for execution in executions[:3]:  # Show first 3
            print(f"  - {execution.agent_name}: {execution.duration_seconds:.1f}s")
            if execution.parent_agent:
                print(f"    Parent: {execution.parent_agent}")
        print()

        # Example 3: Build execution tree
        print("Example 3: Building Execution Tree")
        print("-" * 64)
        builder = ExecutionTreeBuilder(executions)
        tree = builder.build()
        print(f"Root nodes: {len(tree)}")
        print(f"Root agents: {', '.join(tree.keys())}")
        print()

        # Example 4: Render ASCII tree
        print("Example 4: ASCII Tree Visualization")
        print("-" * 64)
        renderer = AsciiTreeRenderer()
        ascii_tree = renderer.render(tree)
        print(ascii_tree)
        print()

        # Example 5: Detect patterns
        print("Example 5: Pattern Detection")
        print("-" * 64)
        detector = PatternDetector(executions)
        patterns = detector.detect_all()
        print(f"Patterns detected: {len(patterns)}")
        for pattern in patterns:
            print(f"  - {pattern.pattern_type}: {pattern.description}")
        print()

        # Example 6: Get statistics
        print("Example 6: Performance Statistics")
        print("-" * 64)
        stats = reader.get_agent_stats(session_id="example_session")
        print(f"Total executions: {stats['total_executions']}")
        print(f"Total duration: {stats['total_duration_ms'] / 1000:.1f}s")
        print(f"Average duration: {stats['avg_duration_ms'] / 1000:.1f}s")
        print()
        print("Agent execution counts:")
        for agent, count in sorted(stats['agents'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent:15} {count:2} executions")
        print()

        # Example 7: Generate text report
        print("Example 7: Text Report Generation")
        print("-" * 64)
        generator = ReportGenerator(reader)
        report = generator.generate_text_report(session_id="example_session")
        print(report)
        print()

        # Example 8: Generate JSON report
        print("Example 8: JSON Report Generation")
        print("-" * 64)
        json_report = generator.generate_json_report(session_id="example_session")
        print(f"Report keys: {list(json_report.keys())}")
        print(f"Executions in report: {len(json_report['executions'])}")
        print(f"Patterns in report: {len(json_report['patterns'])}")
        print()

        print("=" * 64)
        print("✓ All examples completed successfully!")
        print("=" * 64)


if __name__ == "__main__":
    main()
