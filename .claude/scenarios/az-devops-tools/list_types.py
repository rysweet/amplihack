#!/usr/bin/env python3
"""List work item types and fields in Azure DevOps.

This tool helps discover:
- Available work item types (User Story, Bug, Task, etc.)
- Field schemas for each type
- Custom work item types
- Required vs optional fields

Philosophy:
- Single responsibility: type/field discovery
- Help with work item creation
- Support custom types
- Clear field documentation

Public API:
    list_types: Get all work item types
    get_type_fields: Get fields for a specific type
"""

import argparse
import json
import sys

from .common import (
    AzCliWrapper,
    ExitCode,
    format_table,
    handle_error,
    load_config,
)


def list_types(org: str, project: str) -> list[dict]:
    """List all work item types in project.

    Args:
        org: Organization URL
        project: Project name

    Returns:
        List of work item type dictionaries

    Raises:
        RuntimeError: If listing fails
    """
    wrapper = AzCliWrapper(org=org, project=project)
    result = wrapper.devops_command(
        ["work-item", "type", "list"],
        timeout=15,
    )

    if not result.success:
        raise RuntimeError(f"Failed to list work item types: {result.stderr}")

    data = result.json_output
    if not data:
        return []

    return data.get("value", [])


def get_type_fields(work_item_type: str, org: str, project: str) -> dict | None:
    """Get field schema for a specific work item type.

    Args:
        work_item_type: Type name (e.g., "User Story")
        org: Organization URL
        project: Project name

    Returns:
        Dictionary with field information, or None if type not found

    Raises:
        RuntimeError: If query fails
    """
    wrapper = AzCliWrapper(org=org, project=project)
    result = wrapper.devops_command(
        ["work-item", "type", "show", "--name", work_item_type],
        timeout=15,
    )

    if not result.success:
        return None

    return result.json_output


def format_types_list(types: list[dict], output_format: str = "table") -> str:
    """Format work item types for output.

    Args:
        types: List of type dictionaries
        output_format: Output format (table, json, list)

    Returns:
        Formatted output string
    """
    if not types:
        return "No work item types found."

    if output_format == "json":
        return json.dumps(types, indent=2)

    if output_format == "list":
        names = [t.get("name", "") for t in types]
        return "\n".join(names)

    # table format
    rows = []
    for t in types:
        rows.append(
            [
                t.get("name", ""),
                t.get("description", "")[:60] + "..."
                if len(t.get("description", "")) > 60
                else t.get("description", ""),
            ]
        )

    headers = ["Type Name", "Description"]
    return format_table(headers, rows)


def format_fields_list(fields: dict, output_format: str = "table", show_all: bool = False) -> str:
    """Format work item type fields for output.

    Args:
        fields: Field schema dictionary
        output_format: Output format (table, json)
        show_all: Show all fields (including system fields)

    Returns:
        Formatted output string
    """
    if not fields:
        return "No field information available."

    if output_format == "json":
        return json.dumps(fields, indent=2)

    # Extract field definitions
    field_defs = fields.get("fields", [])
    if not field_defs:
        return "No fields found."

    # Filter fields
    if not show_all:
        # Show only commonly used fields
        common_prefixes = [
            "System.Title",
            "System.Description",
            "System.State",
            "System.AssignedTo",
            "System.AreaPath",
            "System.IterationPath",
            "System.Tags",
            "Microsoft.VSTS",
        ]
        field_defs = [
            f
            for f in field_defs
            if any(f.get("referenceName", "").startswith(prefix) for prefix in common_prefixes)
        ]

    # Format as table
    rows = []
    for field in field_defs:
        ref_name = field.get("referenceName", "")
        name = field.get("name", "")
        required = "Yes" if field.get("alwaysRequired", False) else "No"
        field_type = field.get("type", "")

        rows.append([ref_name, name, required, field_type])

    headers = ["Reference Name", "Display Name", "Required", "Type"]
    return format_table(headers, rows)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="List Azure DevOps work item types and fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all work item types
  python -m .claude.scenarios.az-devops-tools.list_types

  # Show fields for specific type
  python -m .claude.scenarios.az-devops-tools.list_types \\
    --type "User Story"

  # Show all fields (including system fields)
  python -m .claude.scenarios.az-devops-tools.list_types \\
    --type "Bug" \\
    --all-fields

  # Output as JSON
  python -m .claude.scenarios.az-devops-tools.list_types \\
    --format json

  # Get just type names
  python -m .claude.scenarios.az-devops-tools.list_types \\
    --format list

Common work item types:
  - User Story
  - Bug
  - Task
  - Feature
  - Epic
  - Test Case

Common fields:
  - System.Title (required)
  - System.Description
  - System.State
  - System.AssignedTo
  - System.AreaPath
  - System.IterationPath
  - System.Tags

Learn more:
  https://learn.microsoft.com/en-us/azure/devops/boards/work-items/about-work-items
        """,
    )

    # Optional arguments
    parser.add_argument(
        "--type",
        help="Show fields for specific work item type",
    )
    parser.add_argument(
        "--all-fields",
        action="store_true",
        help="Show all fields including system fields (only with --type)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "list"],
        default="table",
        help="Output format (default: table)",
    )

    # Common arguments
    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    org = args.org or config.get("org")
    project = args.project or config.get("project")

    # Validate required config
    if not org or not project:
        handle_error(
            "Organization and project are required",
            ExitCode.CONFIG_ERROR,
            "Set via --org/--project, environment variables, or az devops configure",
        )

    try:
        # Show specific type fields
        if args.type:
            fields = get_type_fields(args.type, org, project)
            if not fields:
                handle_error(
                    f"Work item type '{args.type}' not found",
                    ExitCode.VALIDATION_ERROR,
                    "Use list_types without --type to see available types",
                )

            output = format_fields_list(
                fields,
                output_format=args.format,
                show_all=args.all_fields,
            )
            print(output)

        # List all types
        else:
            types = list_types(org, project)
            output = format_types_list(types, output_format=args.format)
            print(output)

        sys.exit(ExitCode.SUCCESS)

    except RuntimeError as e:
        handle_error(str(e), ExitCode.COMMAND_ERROR)
    except Exception as e:
        handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["list_types", "get_type_fields", "format_types_list", "format_fields_list", "main"]
