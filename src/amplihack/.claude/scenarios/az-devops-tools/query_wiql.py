#!/usr/bin/env python3
"""Execute WIQL queries against Azure DevOps.

WIQL (Work Item Query Language) is used to query work items.
This tool provides both predefined queries and custom WIQL support.

Philosophy:
- Single responsibility: WIQL query execution
- Predefined queries for common cases
- Multiple output formats (table, json, csv, ids-only)
- Result limiting and pagination

Public API:
    execute_wiql: Execute WIQL query
    get_predefined_query: Get predefined query by name
"""

import argparse
import csv
import io
import json
import sys

from .common import (
    AzCliWrapper,
    ExitCode,
    format_table,
    handle_error,
    load_config,
)

# Predefined WIQL queries
PREDEFINED_QUERIES = {
    "my-items": """
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
        FROM workitems
        WHERE [System.AssignedTo] = @Me
        AND [System.State] <> 'Closed'
        ORDER BY [System.ChangedDate] DESC
    """,
    "unassigned": """
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
        FROM workitems
        WHERE [System.AssignedTo] = ''
        AND [System.State] <> 'Closed'
        AND [System.State] <> 'Removed'
        ORDER BY [System.CreatedDate] DESC
    """,
    "recent": """
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.ChangedDate]
        FROM workitems
        WHERE [System.TeamProject] = @project
        ORDER BY [System.ChangedDate] DESC
    """,
    "active-bugs": """
        SELECT [System.Id], [System.Title], [System.State], [System.Priority]
        FROM workitems
        WHERE [System.WorkItemType] = 'Bug'
        AND [System.State] <> 'Closed'
        AND [System.State] <> 'Resolved'
        ORDER BY [System.Priority] ASC, [System.CreatedDate] DESC
    """,
    "active-stories": """
        SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
        FROM workitems
        WHERE [System.WorkItemType] = 'User Story'
        AND [System.State] <> 'Closed'
        AND [System.State] <> 'Removed'
        ORDER BY [System.State] ASC, [System.CreatedDate] DESC
    """,
}


def get_predefined_query(query_name: str) -> str | None:
    """Get predefined WIQL query by name.

    Args:
        query_name: Name of predefined query

    Returns:
        WIQL query string, or None if not found
    """
    return PREDEFINED_QUERIES.get(query_name)


def execute_wiql(
    wiql: str,
    org: str,
    project: str,
    limit: int | None = None,
) -> list[dict]:
    """Execute WIQL query and return results.

    Args:
        wiql: WIQL query string
        org: Organization URL
        project: Project name
        limit: Maximum number of results to return

    Returns:
        List of work item dictionaries

    Raises:
        RuntimeError: If query execution fails
    """
    wrapper = AzCliWrapper(org=org, project=project)

    # Execute query
    result = wrapper.devops_command(
        ["work-item", "query", "--wiql", wiql],
        timeout=30,
    )

    if not result.success:
        raise RuntimeError(f"Failed to execute query: {result.stderr}")

    # Parse results
    data = result.json_output
    if not data:
        return []

    # Get work item IDs from query result
    work_items = data.get("workItems", [])
    if not work_items:
        return []

    # Limit results if requested
    if limit and limit > 0:
        work_items = work_items[:limit]

    # Fetch full work item details
    work_item_details = []
    for item in work_items:
        item_id = item.get("id")
        if not item_id:
            continue

        # Get work item details
        detail_result = wrapper.devops_command(
            ["work-item", "show", "--id", str(item_id)],
            timeout=15,
        )

        if detail_result.success and detail_result.json_output:
            work_item_details.append(detail_result.json_output)

    return work_item_details


def format_work_items(
    work_items: list[dict],
    output_format: str = "table",
) -> str:
    """Format work items for output.

    Args:
        work_items: List of work item dictionaries
        output_format: Output format (table, json, csv, ids-only)

    Returns:
        Formatted output string
    """
    if not work_items:
        return "No work items found."

    if output_format == "json":
        return json.dumps(work_items, indent=2)

    if output_format == "ids-only":
        ids = [str(item.get("id", "")) for item in work_items]
        return "\n".join(ids)

    # Extract common fields for table/csv
    rows = []
    for item in work_items:
        fields = item.get("fields", {})
        rows.append(
            [
                str(item.get("id", "")),
                fields.get("System.WorkItemType", ""),
                fields.get("System.State", ""),
                fields.get("System.Title", ""),
                fields.get("System.AssignedTo", {}).get("displayName", "")
                if isinstance(fields.get("System.AssignedTo"), dict)
                else fields.get("System.AssignedTo", ""),
            ]
        )

    if output_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Type", "State", "Title", "Assigned To"])
        writer.writerows(rows)
        return output.getvalue()

    # table format
    headers = ["ID", "Type", "State", "Title", "Assigned To"]
    return format_table(headers, rows)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Execute WIQL queries against Azure DevOps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use predefined query
  python -m .claude.scenarios.az-devops-tools.query_wiql --query my-items

  # Custom WIQL query
  python -m .claude.scenarios.az-devops-tools.query_wiql \\
    --wiql "SELECT [System.Id] FROM workitems WHERE [System.State] = 'Active'"

  # Output as JSON
  python -m .claude.scenarios.az-devops-tools.query_wiql \\
    --query recent \\
    --format json

  # Limit results
  python -m .claude.scenarios.az-devops-tools.query_wiql \\
    --query my-items \\
    --limit 10

  # Get only IDs
  python -m .claude.scenarios.az-devops-tools.query_wiql \\
    --query my-items \\
    --format ids-only

Predefined queries:
  - my-items: My assigned open work items
  - unassigned: Unassigned open work items
  - recent: Recently changed work items
  - active-bugs: Open bugs
  - active-stories: Open user stories

Output formats:
  - table (default): ASCII table
  - json: JSON array
  - csv: CSV format
  - ids-only: Work item IDs only (one per line)

WIQL syntax:
  SELECT [Field1], [Field2] FROM workitems WHERE [Condition] ORDER BY [Field]

Common fields:
  - [System.Id]
  - [System.Title]
  - [System.State]
  - [System.WorkItemType]
  - [System.AssignedTo]
  - [System.CreatedDate]
  - [System.ChangedDate]

Learn more:
  https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax
        """,
    )

    # Query specification (mutually exclusive)
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument(
        "--query",
        choices=list(PREDEFINED_QUERIES.keys()),
        help="Predefined query name",
    )
    query_group.add_argument(
        "--wiql",
        help="Custom WIQL query string",
    )

    # Output options
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv", "ids-only"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of results to return",
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

    # Get WIQL query
    if args.query:
        wiql = get_predefined_query(args.query)
        if not wiql:
            handle_error(
                f"Unknown predefined query: {args.query}",
                ExitCode.VALIDATION_ERROR,
            )
    else:
        wiql = args.wiql

    # Execute query
    try:
        work_items = execute_wiql(
            wiql=wiql,
            org=org,
            project=project,
            limit=args.limit,
        )

        # Format and print results
        output = format_work_items(work_items, args.format)
        print(output)

        sys.exit(ExitCode.SUCCESS)

    except RuntimeError as e:
        handle_error(str(e), ExitCode.COMMAND_ERROR)
    except Exception as e:
        handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["execute_wiql", "get_predefined_query", "format_work_items", "main"]
