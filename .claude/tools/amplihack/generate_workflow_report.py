#!/usr/bin/env python3
"""
Workflow Adherence Report Generator

Analyzes workflow execution logs and generates markdown dashboard.
Philosophy-aligned: Simple, file-based, no heavy frameworks.

Usage:
    python generate_workflow_report.py [--limit 100] [--output report.md]

Output:
    Markdown report with workflow statistics, completion rates, and insights.
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

WORKFLOW_LOG_FILE = Path(".claude/runtime/logs/workflow_adherence/workflow_execution.jsonl")
DEFAULT_OUTPUT = Path(".claude/runtime/logs/workflow_adherence/WORKFLOW_ADHERENCE_REPORT.md")


def read_log_entries(limit: int = None) -> list[dict[str, Any]]:
    """Read and parse JSONL log file."""
    if not WORKFLOW_LOG_FILE.exists():
        return []

    entries = []
    with open(WORKFLOW_LOG_FILE) as f:
        lines = f.readlines()
        if limit:
            lines = lines[-limit:]

        for line in lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return entries


def analyze_workflows(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze workflow execution patterns."""
    workflows = []
    current_workflow = None
    step_execution_data = defaultdict(lambda: {"executed": 0, "skipped": 0})
    agent_usage = defaultdict(int)
    violations = []
    skip_reasons = defaultdict(int)

    for entry in entries:
        event = entry.get("event")

        if event == "workflow_start":
            current_workflow = {
                "start": entry,
                "steps": [],
                "agents": [],
                "violations": [],
            }

        elif event == "step_executed" and current_workflow is not None:
            step_key = f"Step {entry['step']}: {entry['name']}"
            step_execution_data[step_key]["executed"] += 1

            if entry.get("agent"):
                agent_usage[entry["agent"]] += 1
                current_workflow["agents"].append(entry["agent"])

            current_workflow["steps"].append(entry)

        elif event == "step_skipped" and current_workflow is not None:
            step_key = f"Step {entry['step']}: {entry['name']}"
            step_execution_data[step_key]["skipped"] += 1
            skip_reasons[entry.get("reason", "Unknown")] += 1

        elif event == "agent_invoked":
            agent_usage[entry["agent"]] += 1

        elif event == "workflow_violation":
            violations.append(entry)
            if current_workflow is not None:
                current_workflow["violations"].append(entry)

        elif event == "workflow_end" and current_workflow is not None:
            current_workflow["end"] = entry
            workflows.append(current_workflow)
            current_workflow = None

    return {
        "workflows": workflows,
        "step_data": dict(step_execution_data),
        "agent_usage": dict(agent_usage),
        "violations": violations,
        "skip_reasons": dict(skip_reasons),
    }


def calculate_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    """Calculate key metrics from analysis."""
    workflows = analysis["workflows"]

    if not workflows:
        return {
            "total_workflows": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0,
            "avg_completion_rate": 0,
            "avg_steps_executed": 0,
            "avg_steps_skipped": 0,
            "avg_agents_used": 0,
            "total_violations": 0,
        }

    completed_workflows = [w for w in workflows if "end" in w]
    successful = sum(1 for w in completed_workflows if w["end"].get("success", False))

    completion_rates = [w["end"]["completion_rate"] for w in completed_workflows]
    steps_executed = [
        w["end"]["total_steps"] - w["end"]["skipped_steps"] for w in completed_workflows
    ]
    steps_skipped = [w["end"]["skipped_steps"] for w in completed_workflows]
    agents_used = [len(set(w["agents"])) for w in workflows]

    return {
        "total_workflows": len(workflows),
        "successful": successful,
        "failed": len(completed_workflows) - successful,
        "success_rate": round(successful / len(completed_workflows) * 100, 1)
        if completed_workflows
        else 0,
        "avg_completion_rate": round(sum(completion_rates) / len(completion_rates), 1)
        if completion_rates
        else 0,
        "avg_steps_executed": round(sum(steps_executed) / len(steps_executed), 1)
        if steps_executed
        else 0,
        "avg_steps_skipped": round(sum(steps_skipped) / len(steps_skipped), 1)
        if steps_skipped
        else 0,
        "avg_agents_used": round(sum(agents_used) / len(agents_used), 1) if agents_used else 0,
        "total_violations": len(analysis["violations"]),
    }


def generate_markdown_report(analysis: dict[str, Any], metrics: dict[str, Any]) -> str:
    """Generate markdown report from analysis and metrics."""
    report_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Most skipped steps
    step_data = analysis["step_data"]
    most_skipped = sorted(
        [(k, v["skipped"], v["executed"]) for k, v in step_data.items()],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    # Most used agents
    most_used_agents = sorted(analysis["agent_usage"].items(), key=lambda x: x[1], reverse=True)[
        :10
    ]

    # Skip reasons
    skip_reasons = sorted(analysis["skip_reasons"].items(), key=lambda x: x[1], reverse=True)[:10]

    # Recent violations
    recent_violations = analysis["violations"][-10:]

    markdown = f"""# Workflow Adherence Report

**Generated**: {report_time}
**Analysis Window**: Last {len(analysis["workflows"])} workflow executions

## Executive Summary

### Overall Metrics

| Metric | Value |
|--------|-------|
| Total Workflows Executed | {metrics["total_workflows"]} |
| Successful Completions | {metrics["successful"]} |
| Failed Workflows | {metrics["failed"]} |
| Success Rate | {metrics["success_rate"]}% |
| Average Completion Rate | {metrics["avg_completion_rate"]}% |
| Average Steps Executed | {metrics["avg_steps_executed"]} |
| Average Steps Skipped | {metrics["avg_steps_skipped"]} |
| Average Agents Used | {metrics["avg_agents_used"]} |
| Total Violations | {metrics["total_violations"]} |

### Interpretation

"""

    # Add interpretation based on metrics
    if metrics["avg_completion_rate"] >= 90:
        markdown += "✓ **EXCELLENT**: Workflow adherence is strong (>90% completion rate).\n\n"
    elif metrics["avg_completion_rate"] >= 75:
        markdown += "⚠ **GOOD**: Workflow adherence is acceptable but has room for improvement.\n\n"
    else:
        markdown += "✗ **POOR**: Workflow adherence needs significant improvement (<75% completion rate).\n\n"

    if metrics["avg_steps_skipped"] > 3:
        markdown += f"⚠ **WARNING**: Average of {metrics['avg_steps_skipped']} steps skipped per workflow. Review skip patterns below.\n\n"

    if metrics["total_violations"] > 0:
        markdown += f"✗ **VIOLATIONS**: {metrics['total_violations']} workflow violations detected. See violations section below.\n\n"

    # Most skipped steps section
    markdown += "## Most Frequently Skipped Steps\n\n"

    if most_skipped:
        markdown += "| Step | Times Skipped | Times Executed | Skip Rate |\n"
        markdown += "|------|---------------|----------------|----------|\n"

        for step_name, skipped, executed in most_skipped:
            total = skipped + executed
            skip_rate = round(skipped / total * 100, 1) if total > 0 else 0
            markdown += f"| {step_name} | {skipped} | {executed} | {skip_rate}% |\n"

        markdown += "\n**Analysis**: Steps with >50% skip rate should be reviewed. Consider:\n"
        markdown += "- Are these steps necessary for all workflows?\n"
        markdown += "- Should workflow variables be adjusted?\n"
        markdown += "- Is step documentation clear?\n\n"
    else:
        markdown += "*No step skip data available.*\n\n"

    # Skip reasons section
    markdown += "## Common Skip Reasons\n\n"

    if skip_reasons:
        markdown += "| Reason | Count |\n"
        markdown += "|--------|-------|\n"

        for reason, count in skip_reasons:
            markdown += f"| {reason} | {count} |\n"

        markdown += "\n"
    else:
        markdown += "*No skip reason data available.*\n\n"

    # Agent usage section
    markdown += "## Agent Usage Statistics\n\n"

    if most_used_agents:
        markdown += "| Agent | Times Used |\n"
        markdown += "|-------|------------|\n"

        for agent, count in most_used_agents:
            markdown += f"| {agent} | {count} |\n"

        markdown += "\n**Analysis**: Verify that all required agents are being used:\n"
        markdown += "- prompt-writer (Step 1)\n"
        markdown += "- architect (Step 4)\n"
        markdown += "- builder (Step 5)\n"
        markdown += "- cleanup (Step 6)\n"
        markdown += "- reviewer (Steps 11, 13)\n\n"
    else:
        markdown += "*No agent usage data available.*\n\n"

    # Violations section
    markdown += "## Recent Workflow Violations\n\n"

    if recent_violations:
        markdown += "| Timestamp | Type | Description |\n"
        markdown += "|-----------|------|-------------|\n"

        for violation in recent_violations:
            timestamp = violation.get("timestamp", "Unknown")
            violation_type = violation.get("type", "Unknown")
            description = violation.get("description", "No description")
            markdown += f"| {timestamp} | {violation_type} | {description} |\n"

        markdown += "\n**Action Items**:\n"
        markdown += "1. Review violations and identify patterns\n"
        markdown += "2. Update workflow documentation if violations indicate confusion\n"
        markdown += "3. Consider adding guardrails for common violation types\n\n"
    else:
        markdown += "*No violations detected. Excellent!*\n\n"

    # Recommendations section
    markdown += "## Recommendations\n\n"

    recommendations = []

    if metrics["avg_steps_skipped"] > 3:
        recommendations.append(
            f"- **Reduce Skip Rate**: Average of {metrics['avg_steps_skipped']} steps skipped. "
            "Review most-skipped steps and clarify when skipping is appropriate."
        )

    if metrics["avg_agents_used"] < 5:
        recommendations.append(
            f"- **Increase Agent Usage**: Average of {metrics['avg_agents_used']} agents per workflow. "
            "Should be using 5+ agents for proper delegation."
        )

    if metrics["avg_completion_rate"] < 80:
        recommendations.append(
            f"- **Improve Completion Rate**: Current rate is {metrics['avg_completion_rate']}%. "
            "Target should be >90%. Review skip patterns and workflow clarity."
        )

    if metrics["total_violations"] > 0:
        recommendations.append(
            f"- **Address Violations**: {metrics['total_violations']} violations detected. "
            "Review violation patterns and update documentation/tooling."
        )

    if not recommendations:
        recommendations.append(
            "- **Keep It Up**: Workflow adherence is excellent. No changes needed."
        )

    for rec in recommendations:
        markdown += f"{rec}\n"

    markdown += "\n## How to Improve Adherence\n\n"
    markdown += (
        "1. **Read Workflow First**: Always read DEFAULT_WORKFLOW.md before starting tasks\n"
    )
    markdown += "2. **Use TodoWrite**: Create todos with 'Step N: [Step Name]' format\n"
    markdown += "3. **Delegate to Agents**: Use specialized agents at every applicable step\n"
    markdown += "4. **Track Execution**: Use workflow_tracker.py to log steps\n"
    markdown += "5. **Review This Report**: Check this dashboard regularly for patterns\n\n"

    markdown += "---\n\n"
    markdown += "*Report generated by generate_workflow_report.py*\n"

    return markdown


def main():
    parser = argparse.ArgumentParser(description="Generate workflow adherence report")
    parser.add_argument("--limit", type=int, help="Limit number of log entries to analyze")
    parser.add_argument("--output", type=str, help=f"Output file path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT

    print(f"Reading log entries from {WORKFLOW_LOG_FILE}...")
    entries = read_log_entries(limit=args.limit)

    if not entries:
        print("No log entries found. Workflow tracker may not have been used yet.")
        print(f"Log file location: {WORKFLOW_LOG_FILE}")
        return

    print(f"Analyzing {len(entries)} log entries...")
    analysis = analyze_workflows(entries)

    print("Calculating metrics...")
    metrics = calculate_metrics(analysis)

    print("Generating markdown report...")
    report = generate_markdown_report(analysis, metrics)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(report)

    print(f"\n✓ Report generated: {output_path}")
    print("\n--- Executive Summary ---")
    print(f"Total Workflows: {metrics['total_workflows']}")
    print(f"Success Rate: {metrics['success_rate']}%")
    print(f"Avg Completion Rate: {metrics['avg_completion_rate']}%")
    print(f"Avg Steps Skipped: {metrics['avg_steps_skipped']}")
    print(f"Total Violations: {metrics['total_violations']}")


if __name__ == "__main__":
    main()
