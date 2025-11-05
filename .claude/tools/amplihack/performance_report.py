#!/usr/bin/env python3
"""
Performance report generator for Ultra-Think sessions.
Analyzes TodoWrite metrics to provide insights into session efficiency.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PerformanceReporter:
    """Generate performance reports from TodoWrite metrics."""

    def __init__(self, metrics_dir: Path):
        """Initialize the performance reporter.

        Args:
            metrics_dir: Path to metrics directory
        """
        self.metrics_dir = metrics_dir
        self.baselines_file = metrics_dir / "baselines.json"

    def load_metrics(self, session_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load TodoWrite transition metrics from JSONL files.

        Args:
            session_filter: Optional session timestamp to filter by

        Returns:
            List of metric dictionaries
        """
        metrics = []
        metrics_file = self.metrics_dir / "post_tool_use_metrics.jsonl"

        if not metrics_file.exists():
            return metrics

        with open(metrics_file) as f:
            for line in f:
                try:
                    metric = json.loads(line.strip())
                    if metric.get("metric") == "todo_transition":
                        # Filter by session if specified
                        if session_filter:
                            session_timestamp = metric.get("metadata", {}).get(
                                "session_timestamp", ""
                            )
                            if not session_timestamp.startswith(session_filter):
                                continue
                        metrics.append(metric)
                except json.JSONDecodeError:
                    continue

        return metrics

    def analyze_tasks(self, metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze task transitions to compute durations and message counts.

        Args:
            metrics: List of TodoWrite transition metrics

        Returns:
            List of analyzed task dictionaries
        """
        # Group metrics by task content
        task_events = defaultdict(list)

        for metric in metrics:
            metadata = metric.get("metadata", {})
            task_content = metadata.get("task_content", "Unknown")
            task_events[task_content].append(metric)

        # Analyze each task
        analyzed_tasks = []

        for task_content, events in task_events.items():
            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""))

            # Find in_progress and completed events
            in_progress_event = None
            completed_event = None

            for event in events:
                if event.get("value") == "in_progress" and not in_progress_event:
                    in_progress_event = event
                elif event.get("value") == "completed":
                    completed_event = event

            if in_progress_event:
                metadata_start = in_progress_event.get("metadata", {})
                message_start = metadata_start.get("message_number", 0)
                timestamp_start = datetime.fromisoformat(in_progress_event.get("timestamp", ""))

                message_end = message_start
                duration_minutes = 0

                if completed_event:
                    metadata_end = completed_event.get("metadata", {})
                    message_end = metadata_end.get("message_number", message_start)
                    timestamp_end = datetime.fromisoformat(completed_event.get("timestamp", ""))
                    duration_seconds = (timestamp_end - timestamp_start).total_seconds()
                    duration_minutes = duration_seconds / 60

                messages_used = max(0, message_end - message_start)

                analyzed_tasks.append(
                    {
                        "task": task_content,
                        "messages": messages_used,
                        "duration_minutes": duration_minutes,
                        "status": "completed" if completed_event else "in_progress",
                        "active_form": metadata_start.get("task_active_form", ""),
                    }
                )

        return analyzed_tasks

    def load_baselines(self) -> Dict[str, Dict[str, Any]]:
        """Load baseline metrics from JSON file.

        Returns:
            Dictionary of baselines by task type
        """
        if not self.baselines_file.exists():
            return {}

        try:
            with open(self.baselines_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def categorize_task_type(self, tasks: List[Dict[str, Any]]) -> str:
        """Categorize the task type based on task names.

        Args:
            tasks: List of analyzed tasks

        Returns:
            Task type category (investigation, development, debugging, etc.)
        """
        # Simple heuristic based on task content
        task_content = " ".join([t["task"].lower() for t in tasks])

        if "investigate" in task_content or "analyze" in task_content:
            return "investigation"
        if "debug" in task_content or "fix" in task_content:
            return "debugging"
        if "refactor" in task_content:
            return "refactoring"
        return "development"

    def generate_report(
        self, session_filter: Optional[str] = None, task_type: Optional[str] = None
    ) -> str:
        """Generate performance report.

        Args:
            session_filter: Optional session timestamp to filter by
            task_type: Optional task type for baseline comparison

        Returns:
            Formatted report string
        """
        metrics = self.load_metrics(session_filter)

        if not metrics:
            return "No TodoWrite metrics found for the specified session."

        tasks = self.analyze_tasks(metrics)

        if not tasks:
            return "No completed or in-progress tasks found."

        # Calculate totals
        total_messages = sum(t["messages"] for t in tasks)
        total_duration = sum(t["duration_minutes"] for t in tasks)

        # Build report
        lines = []
        lines.append("")
        lines.append("Ultra-Think Performance Summary:")
        lines.append("━" * 60)

        # Task breakdown
        for task in tasks:
            task_name = task["task"][:50]  # Truncate long names
            messages = task["messages"]
            duration = task["duration_minutes"]
            status_marker = "✓" if task["status"] == "completed" else "⋯"

            lines.append(f"{status_marker} {task_name:<45} {messages:>3} msgs, ~{duration:.1f}min")

        lines.append("━" * 60)
        lines.append(f"{'Total:':<47} {total_messages:>3} msgs, {total_duration:.1f}min")
        lines.append("")

        # Baseline comparison
        baselines = self.load_baselines()

        if not task_type:
            task_type = self.categorize_task_type(tasks)

        if task_type in baselines:
            baseline = baselines[task_type]
            expected_messages = baseline.get("avg_messages", 0)
            expected_duration = baseline.get("avg_duration_minutes", 0)

            if expected_messages > 0 and expected_duration > 0:
                message_diff = ((total_messages - expected_messages) / expected_messages) * 100
                duration_diff = ((total_duration - expected_duration) / expected_duration) * 100

                lines.append(f"Comparison to baseline ({task_type} tasks):")
                lines.append(
                    f"  Messages: {total_messages} vs {expected_messages:.0f} expected ({message_diff:+.0f}%)"
                )
                lines.append(
                    f"  Duration: {total_duration:.1f}min vs {expected_duration:.1f}min expected ({duration_diff:+.0f}%)"
                )
                lines.append("")

        return "\n".join(lines)

    def update_baselines(self, session_filter: Optional[str] = None):
        """Update baseline metrics with data from current session.

        Args:
            session_filter: Optional session timestamp to filter by
        """
        metrics = self.load_metrics(session_filter)

        if not metrics:
            print("No metrics to add to baselines.", file=sys.stderr)
            return

        tasks = self.analyze_tasks(metrics)

        if not tasks:
            print("No completed tasks to add to baselines.", file=sys.stderr)
            return

        # Calculate session totals
        total_messages = sum(t["messages"] for t in tasks)
        total_duration = sum(t["duration_minutes"] for t in tasks)
        task_type = self.categorize_task_type(tasks)

        # Load existing baselines
        baselines = self.load_baselines()

        if task_type not in baselines:
            baselines[task_type] = {
                "avg_messages": total_messages,
                "avg_duration_minutes": total_duration,
                "sample_count": 1,
            }
        else:
            # Update running average
            baseline = baselines[task_type]
            count = baseline["sample_count"]
            new_count = count + 1

            baseline["avg_messages"] = (
                baseline["avg_messages"] * count + total_messages
            ) / new_count
            baseline["avg_duration_minutes"] = (
                baseline["avg_duration_minutes"] * count + total_duration
            ) / new_count
            baseline["sample_count"] = new_count

        # Save updated baselines
        self.baselines_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.baselines_file, "w") as f:
            json.dump(baselines, f, indent=2)

        print(
            f"Updated {task_type} baseline (sample count: {baselines[task_type]['sample_count']})"
        )


def main():
    """CLI entry point for performance reporting."""
    parser = argparse.ArgumentParser(description="Generate Ultra-Think performance reports")
    parser.add_argument(
        "--session",
        help="Session timestamp filter (YYYY-MM-DD or full ISO timestamp)",
        default=None,
    )
    parser.add_argument(
        "--task-type",
        help="Task type for baseline comparison (investigation, development, debugging, refactoring)",
        default=None,
    )
    parser.add_argument(
        "--update-baselines",
        help="Update baseline metrics with current session data",
        action="store_true",
    )
    parser.add_argument(
        "--metrics-dir",
        help="Path to metrics directory (default: .claude/runtime/metrics)",
        default=None,
    )

    args = parser.parse_args()

    # Find metrics directory
    if args.metrics_dir:
        metrics_dir = Path(args.metrics_dir)
    else:
        # Try to find .claude directory
        current = Path.cwd()
        metrics_dir = None

        for _ in range(10):
            if (current / ".claude" / "runtime" / "metrics").exists():
                metrics_dir = current / ".claude" / "runtime" / "metrics"
                break
            if current == current.parent:
                break
            current = current.parent

        if not metrics_dir:
            print("Error: Could not find .claude/runtime/metrics directory", file=sys.stderr)
            sys.exit(1)

    reporter = PerformanceReporter(metrics_dir)

    if args.update_baselines:
        reporter.update_baselines(args.session)
    else:
        report = reporter.generate_report(args.session, args.task_type)
        print(report)


if __name__ == "__main__":
    main()
