#!/usr/bin/env python3
"""
Tool: get_work_item.py

Purpose: Get detailed information about a single work item

Usage:
    python get_work_item.py --id <work_item_id> [options]

Examples:
    # Get work item details
    python get_work_item.py --id 12345

    # Include relationships
    python get_work_item.py --id 12345 --relations

    # Get specific fields only
    python get_work_item.py --id 12345 --fields "System.Title,System.State"

    # JSON output
    python get_work_item.py --id 12345 --format json

Philosophy:
- Standard library + azure CLI wrapper
- Clear error messages with actionable guidance
- Fail-fast validation
- Self-contained and regeneratable
"""

import argparse
import json
import sys
from typing import Any

from common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
    validate_work_item_id,
)


def get_work_item_details(
    wrapper: AzCliWrapper,
    work_item_id: int,
    fields: list[str] | None = None,
    include_relations: bool = False,
) -> dict[str, Any]:
    """Get work item details from Azure DevOps.

    Args:
        wrapper: AzCliWrapper instance
        work_item_id: Work item ID
        fields: Specific fields to retrieve (None = all fields)
        include_relations: Include work item relations

    Returns:
        Work item data

    Raises:
        SystemExit: If operation fails
    """
    cmd = ["boards", "work-item", "show", "--id", str(work_item_id), "--output", "json"]

    if fields:
        cmd.extend(["--fields", ",".join(fields)])

    result = wrapper.devops_command(cmd, timeout=30)

    if not result.success:
        if "does not exist" in result.stderr.lower():
            handle_error(
                f"Work item {work_item_id} does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr,
            )
        else:
            handle_error(
                f"Failed to get work item {work_item_id}",
                exit_code=ExitCode.COMMAND_ERROR,
                details=result.stderr,
            )

    try:
        work_item = json.loads(result.stdout)

        # Get relations if requested
        if include_relations:
            relations_result = wrapper.devops_command(
                [
                    "boards",
                    "work-item",
                    "relation",
                    "list-type",
                    "--output",
                    "json",
                ],
                timeout=30,
            )
            if relations_result.success:
                work_item["relations"] = json.loads(relations_result.stdout)

        return work_item
    except (json.JSONDecodeError, KeyError) as e:
        handle_error(
            "Failed to parse work item data",
            exit_code=ExitCode.COMMAND_ERROR,
            details=str(e),
        )
        return {}  # Never reached


def format_summary(work_item: dict[str, Any]) -> str:
    """Format work item as human-readable summary.

    Args:
        work_item: Work item data

    Returns:
        Formatted summary string
    """
    fields = work_item.get("fields", {})
    work_item_id = work_item.get("id", "Unknown")
    work_item_type = fields.get("System.WorkItemType", "Unknown")
    title = fields.get("System.Title", "No title")
    state = fields.get("System.State", "Unknown")
    assigned_to = fields.get("System.AssignedTo", {})
    assigned_name = assigned_to.get("displayName", "Unassigned")
    created_date = fields.get("System.CreatedDate", "Unknown")
    changed_date = fields.get("System.ChangedDate", "Unknown")
    description = fields.get("System.Description", "")

    lines = [
        f"Work Item #{work_item_id}",
        "=" * 60,
        f"Type:        {work_item_type}",
        f"Title:       {title}",
        f"State:       {state}",
        f"Assigned To: {assigned_name}",
        f"Created:     {created_date}",
        f"Changed:     {changed_date}",
        "",
    ]

    if description:
        # Strip HTML tags for readability
        import re

        clean_desc = re.sub("<[^<]+?>", "", description)
        lines.append("Description:")
        lines.append("-" * 60)
        lines.append(clean_desc[:500])  # Truncate long descriptions
        if len(description) > 500:
            lines.append("... (truncated)")
        lines.append("")

    # Show custom fields
    custom_fields = {
        k: v
        for k, v in fields.items()
        if not k.startswith("System.") and not k.startswith("Microsoft.")
    }
    if custom_fields:
        lines.append("Custom Fields:")
        lines.append("-" * 60)
        for key, value in custom_fields.items():
            lines.append(f"{key}: {value}")
        lines.append("")

    # Show relations if available
    if "relations" in work_item and work_item["relations"]:
        lines.append("Relations:")
        lines.append("-" * 60)
        for relation in work_item["relations"]:
            rel_type = relation.get("rel", "Unknown")
            rel_url = relation.get("url", "")
            lines.append(f"  {rel_type}: {rel_url}")
        lines.append("")

    return "\n".join(lines)


def format_detailed(work_item: dict[str, Any]) -> str:
    """Format work item with all fields visible.

    Args:
        work_item: Work item data

    Returns:
        Formatted detailed string
    """
    fields = work_item.get("fields", {})
    work_item_id = work_item.get("id", "Unknown")

    lines = [
        f"Work Item #{work_item_id} - Detailed View",
        "=" * 60,
        "",
        "All Fields:",
        "-" * 60,
    ]

    for key, value in sorted(fields.items()):
        # Handle complex values
        if isinstance(value, dict):
            value_str = value.get("displayName", str(value))
        else:
            value_str = str(value)

        # Truncate very long values
        if len(value_str) > 100:
            value_str = value_str[:100] + "... (truncated)"

        lines.append(f"{key}: {value_str}")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Get Azure DevOps work item details",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get work item details
  %(prog)s --id 12345

  # Include relationships
  %(prog)s --id 12345 --relations

  # Get specific fields
  %(prog)s --id 12345 --fields "System.Title,System.State"

  # JSON output
  %(prog)s --id 12345 --format json
""",
    )

    parser.add_argument("--id", required=True, help="Work item ID")
    parser.add_argument(
        "--fields", help="Comma-separated list of fields to retrieve"
    )
    parser.add_argument(
        "--relations", action="store_true", help="Include work item relations"
    )
    parser.add_argument(
        "--format",
        choices=["summary", "detailed", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Config options
    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")

    args = parser.parse_args()

    # Validate work item ID
    try:
        work_item_id = validate_work_item_id(args.id)
    except ValueError as e:
        handle_error(str(e), exit_code=ExitCode.VALIDATION_ERROR)
        return  # Never reached

    # Load configuration
    config = load_config()
    org = args.org or config.get("org")
    project = args.project or config.get("project")

    if not org or not project:
        handle_error(
            "Organization and project must be configured",
            exit_code=ExitCode.CONFIG_ERROR,
            details="Use 'az devops configure' or set AZURE_DEVOPS_ORG_URL and AZURE_DEVOPS_PROJECT environment variables",
        )

    # Parse fields if provided
    fields = args.fields.split(",") if args.fields else None

    # Create wrapper and get work item
    wrapper = AzCliWrapper(org=org, project=project)

    try:
        work_item = get_work_item_details(
            wrapper, work_item_id, fields, args.relations
        )

        # Format output
        if args.format == "json":
            print(json.dumps(work_item, indent=2))
        elif args.format == "detailed":
            print(format_detailed(work_item))
        else:
            print(format_summary(work_item))

    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
