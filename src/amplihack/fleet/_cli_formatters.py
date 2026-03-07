"""Fleet CLI output formatters.

Extracted from _cli_session_ops.py to separate formatting concerns.

Defines the result dataclasses and formatting functions for fleet reports:
- ScoutResult - data returned by scout agents
- AdvanceResult - data returned by advance agents
- format_scout_report() - format a ScoutResult for CLI output
- format_advance_report() - format an AdvanceResult for CLI output
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import yaml

# Truncation constants
MAX_OUTPUT_LENGTH = 300
MAX_FINDING_LENGTH = 150

_VALID_FORMATS = ("table", "json", "yaml")


@dataclass
class ScoutResult:
    """Result from a scout agent run."""

    session_id: str
    task: str
    success: bool
    agents_used: int = 0
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdvanceResult:
    """Result from an advance agent run."""

    session_id: str
    task: str
    success: bool
    agents_used: int = 0
    steps_completed: int = 0
    steps_total: int = 0
    changes_made: list[str] = field(default_factory=list)
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def format_scout_report(
    result: ScoutResult,
    format: str = "table",
    verbose: bool = False,
) -> str:
    """Format scout agent analysis report.

    Args:
        result: Scout execution result
        format: Output format (table/json/yaml)
        verbose: Include full output without truncation

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format not in _VALID_FORMATS:
        raise ValueError(f"Invalid format: {format}. Must be one of: {', '.join(_VALID_FORMATS)}")
    if format == "json":
        return _format_scout_json(result)
    if format == "yaml":
        return _format_scout_yaml(result)
    return _format_scout_table(result, verbose)


def format_advance_report(
    result: AdvanceResult,
    format: str = "table",
    verbose: bool = False,
) -> str:
    """Format advance agent execution report.

    Args:
        result: Advance execution result
        format: Output format (table/json/yaml)
        verbose: Include full output without truncation

    Returns:
        Formatted string output

    Raises:
        ValueError: If format is invalid
    """
    if format not in _VALID_FORMATS:
        raise ValueError(f"Invalid format: {format}. Must be one of: {', '.join(_VALID_FORMATS)}")
    if format == "json":
        return _format_advance_json(result)
    if format == "yaml":
        return _format_advance_yaml(result)
    return _format_advance_table(result, verbose)


# --- Scout formatters ---


def _format_scout_table(result: ScoutResult, verbose: bool) -> str:
    lines: list[str] = []
    status_icon = "✓" if result.success else "✗"
    lines.append(f"Scout Report [{status_icon}] Session: {result.session_id}")
    lines.append(f"  Task:    {result.task}")
    lines.append(f"  Agents:  {result.agents_used}")
    lines.append(f"  Status:  {_format_agent_status(result.success)}")

    if result.findings:
        lines.append("  Findings:")
        for i, finding in enumerate(result.findings, 1):
            text = finding if verbose else _truncate(finding, MAX_FINDING_LENGTH)
            lines.append(f"    [{i}] {text}")
    else:
        lines.append("  Findings: (none)")

    if result.recommendations:
        lines.append("  Recommendations:")
        for rec in result.recommendations:
            lines.append(f"    - {rec}")

    if result.error and not result.success:
        lines.append(f"  Error: {result.error}")

    return "\n".join(lines)


def _format_scout_json(result: ScoutResult) -> str:
    return json.dumps(_scout_to_dict(result), indent=2)


def _format_scout_yaml(result: ScoutResult) -> str:
    return yaml.dump(_scout_to_dict(result), default_flow_style=False, sort_keys=False)


def _scout_to_dict(result: ScoutResult) -> dict[str, Any]:
    return {
        "session_id": result.session_id,
        "task": result.task,
        "success": result.success,
        "agents_used": result.agents_used,
        "findings": result.findings,
        "recommendations": result.recommendations,
        "error": result.error,
        "metadata": result.metadata,
    }


# --- Advance formatters ---


def _format_advance_table(result: AdvanceResult, verbose: bool) -> str:
    lines: list[str] = []
    status_icon = "✓" if result.success else "✗"
    lines.append(f"Advance Report [{status_icon}] Session: {result.session_id}")
    lines.append(f"  Task:         {result.task}")
    lines.append(f"  Agents:       {result.agents_used}")
    lines.append(f"  Status:       {_format_agent_status(result.success)}")
    lines.append(f"  Steps done:   {result.steps_completed}/{result.steps_total}")

    if result.changes_made:
        lines.append("  Changes made:")
        for change in result.changes_made:
            lines.append(f"    - {change}")
    else:
        lines.append("  Changes made: (none)")

    if result.output:
        output = result.output if verbose else _truncate(result.output, MAX_OUTPUT_LENGTH)
        lines.append(f"  Output: {output}")

    if result.error and not result.success:
        lines.append(f"  Error: {result.error}")

    return "\n".join(lines)


def _format_advance_json(result: AdvanceResult) -> str:
    return json.dumps(_advance_to_dict(result), indent=2)


def _format_advance_yaml(result: AdvanceResult) -> str:
    return yaml.dump(_advance_to_dict(result), default_flow_style=False, sort_keys=False)


def _advance_to_dict(result: AdvanceResult) -> dict[str, Any]:
    return {
        "session_id": result.session_id,
        "task": result.task,
        "success": result.success,
        "agents_used": result.agents_used,
        "steps_completed": result.steps_completed,
        "steps_total": result.steps_total,
        "changes_made": result.changes_made,
        "output": result.output,
        "error": result.error,
        "metadata": result.metadata,
    }


# --- Shared helpers ---


def _format_agent_status(success: bool) -> str:
    return "completed" if success else "failed"


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
