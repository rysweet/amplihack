#!/usr/bin/env python3
"""
Tool: list_work_items.py

Purpose: Query and filter work items using WIQL or simple filters

Usage:
    python list_work_items.py [options]

Examples:
    # List my active work items
    python list_work_items.py --state Active --assigned-to @me

    # List all bugs
    python list_work_items.py --type Bug

    # Use predefined query
    python list_work_items.py --query mine

    # Custom WIQL query
    python list_work_items.py --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.State] = 'Active'"

    # Get just IDs for scripting
    python list_work_items.py --format ids

Philosophy:
- Standard library + azure CLI wrapper
- Clear error messages with actionable guidance
- Fail-fast validation
- Self-contained and regeneratable
"""

import argparse
import json
from typing import Any

from common import AzCliWrapper, ExitCode, format_table, handle_error, load_config

# Predefined WIQL queries
PREDEFINED_QUERIES = {
    "mine": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.AssignedTo] = @me ORDER BY [System.ChangedDate] DESC",
    "team": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.State] <> 'Closed' ORDER BY [System.ChangedDate] DESC",
    "unassigned": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.AssignedTo] = '' AND [System.State] <> 'Closed' ORDER BY [System.CreatedDate] DESC",
    "recent": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = @project ORDER BY [System.ChangedDate] DESC",
    "active": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType] FROM WorkItems WHERE [System.TeamProject] = @project AND [System.State] = 'Active' ORDER BY [System.ChangedDate] DESC",
}


def build_wiql_query(
    state: str | None = None,
    work_item_type: str | None = None,
    assigned_to: str | None = None,
) -> str:
    """Build WIQL query from simple filters.

    Args:
        state: Filter by state (e.g., 'Active', 'Closed')
        work_item_type: Filter by type (e.g., 'Bug', 'Task')
        assigned_to: Filter by assignee (use '@me' for current user)

    Returns:
        WIQL query string
    """
    conditions = []

    if state:
        conditions.append(f"[System.State] = '{state}'")
    if work_item_type:
        conditions.append(f"[System.WorkItemType] = '{work_item_type}'")
    if assigned_to:
        if assigned_to == "@me":
            conditions.append("[System.AssignedTo] = @me")
        else:
            conditions.append(f"[System.AssignedTo] = '{assigned_to}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    return f"SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo] FROM WorkItems WHERE {where_clause} ORDER BY [System.ChangedDate] DESC"


def execute_wiql_query(
    wrapper: AzCliWrapper, wiql: str, limit: int | None = None
) -> list[dict[str, Any]]:
    """Execute WIQL query and return results.

    Args:
        wrapper: AzCliWrapper instance
        wiql: WIQL query string
        limit: Maximum number of results to return

    Returns:
        List of work items

    Raises:
        SystemExit: If query fails
    """
    # Execute query
    result = wrapper.devops_command(
        ["boards", "query", "--wiql", wiql, "--output", "json"], timeout=60
    )

    if not result.success:
        handle_error(
            "Failed to execute WIQL query",
            exit_code=ExitCode.COMMAND_ERROR,
            details=result.stderr,
        )

    # Parse JSON output
    try:
        work_items = json.loads(result.stdout)
        if limit:
            work_items = work_items[:limit]
        return work_items
    except (json.JSONDecodeError, KeyError) as e:
        handle_error(
            "Failed to parse query results",
            exit_code=ExitCode.COMMAND_ERROR,
            details=str(e),
        )
        return []  # Never reached due to sys.exit


def format_output(work_items: list[dict[str, Any]], output_format: str) -> str:
    """Format work items according to output format.

    Args:
        work_items: List of work items
        output_format: One of 'table', 'json', 'csv', 'ids-only'

    Returns:
        Formatted string
    """
    if not work_items:
        return "No work items found."

    if output_format == "json":
        return json.dumps(work_items, indent=2)

    if output_format == "ids-only":
        ids = [str(item.get("id", "")) for item in work_items]
        return "\n".join(ids)

    if output_format == "csv":
        # CSV format
        lines = ["ID,Title,State,Type,Assigned To"]
        for item in work_items:
            fields = item.get("fields", {})
            lines.append(
                f"{item.get('id', '')},"
                f'"{fields.get("System.Title", "")}",{fields.get("System.State", "")},'
                f"{fields.get('System.WorkItemType', '')},"
                f'"{fields.get("System.AssignedTo", {}).get("displayName", "")}"'
            )
        return "\n".join(lines)

    # Default: table format
    headers = ["ID", "Title", "State", "Type", "Assigned To"]
    rows = []
    for item in work_items:
        fields = item.get("fields", {})
        rows.append(
            [
                str(item.get("id", "")),
                fields.get("System.Title", "")[:50],  # Truncate long titles
                fields.get("System.State", ""),
                fields.get("System.WorkItemType", ""),
                fields.get("System.AssignedTo", {}).get("displayName", "Unassigned"),
            ]
        )

    return format_table(headers, rows)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List and query Azure DevOps work items",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List my active work items
  %(prog)s --state Active --assigned-to @me

  # List all bugs
  %(prog)s --type Bug

  # Use predefined query
  %(prog)s --query mine

  # Custom WIQL query
  %(prog)s --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'Active'"

  # Get just IDs
  %(prog)s --format ids-only
""",
    )

    # Query options
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument(
        "--query",
        choices=list(PREDEFINED_QUERIES.keys()),
        help="Use predefined query",
    )
    query_group.add_argument("--wiql", help="Custom WIQL query")

    # Simple filters
    parser.add_argument("--state", help="Filter by state (e.g., Active, Closed)")
    parser.add_argument(
        "--type", dest="work_item_type", help="Filter by work item type (e.g., Bug, Task)"
    )
    parser.add_argument("--assigned-to", help="Filter by assignee (use @me for current user)")

    # Output options
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv", "ids-only"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of results to return")

    # Config options
    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")

    args = parser.parse_args()

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

    # Create wrapper
    wrapper = AzCliWrapper(org=org, project=project)

    # Determine WIQL query
    if args.wiql:
        wiql = args.wiql
    elif args.query:
        wiql = PREDEFINED_QUERIES[args.query]
    elif args.state or args.work_item_type or args.assigned_to:
        wiql = build_wiql_query(args.state, args.work_item_type, args.assigned_to)
    else:
        # Default: show recent items
        wiql = PREDEFINED_QUERIES["recent"]

    # Execute query
    try:
        work_items = execute_wiql_query(wrapper, wiql, args.limit)
        output = format_output(work_items, args.format)
        print(output)
    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
