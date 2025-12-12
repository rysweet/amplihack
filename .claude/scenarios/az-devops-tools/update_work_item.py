#!/usr/bin/env python3
"""
Tool: update_work_item.py

Purpose: Update work item fields, state, and assignments

Usage:
    python update_work_item.py --id <work_item_id> [options]

Examples:
    # Update state
    python update_work_item.py --id 12345 --state "Active"

    # Reassign work item
    python update_work_item.py --id 12345 --assign-to "user@domain.com"

    # Update multiple fields
    python update_work_item.py --id 12345 --state "Resolved" --assign-to "user@domain.com" --comment "Fixed issue"

    # Update custom field
    python update_work_item.py --id 12345 --field "Custom.Priority=High"

Philosophy:
- Standard library + azure CLI wrapper
- Clear error messages with actionable guidance
- Fail-fast validation
- Self-contained and regeneratable
"""

import argparse
import json
import sys

from common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
    validate_work_item_id,
)


def update_work_item(
    wrapper: AzCliWrapper,
    work_item_id: int,
    state: str | None = None,
    assigned_to: str | None = None,
    title: str | None = None,
    description: str | None = None,
    fields: dict[str, str] | None = None,
    comment: str | None = None,
) -> dict:
    """Update work item fields.

    Args:
        wrapper: AzCliWrapper instance
        work_item_id: Work item ID
        state: New state
        assigned_to: New assignee
        title: New title
        description: New description
        fields: Additional fields to update
        comment: Comment explaining changes

    Returns:
        Updated work item data

    Raises:
        SystemExit: If operation fails
    """
    # Build field updates
    field_updates = []

    if state:
        field_updates.append(f"System.State={state}")
    if assigned_to:
        field_updates.append(f"System.AssignedTo={assigned_to}")
    if title:
        field_updates.append(f"System.Title={title}")
    if description:
        field_updates.append(f"System.Description={description}")

    # Add custom fields
    if fields:
        for key, value in fields.items():
            field_updates.append(f"{key}={value}")

    if not field_updates and not comment:
        handle_error(
            "No updates specified",
            exit_code=ExitCode.VALIDATION_ERROR,
            details="Specify at least one field to update or a comment to add",
        )

    # Update work item
    cmd = ["boards", "work-item", "update", "--id", str(work_item_id)]

    if field_updates:
        # Join fields with space for CLI
        fields_arg = " ".join(field_updates)
        cmd.extend(["--fields", fields_arg])

    if comment:
        cmd.extend(["--discussion", comment])

    cmd.append("--output")
    cmd.append("json")

    result = wrapper.devops_command(cmd, timeout=30)

    if not result.success:
        # Check for common errors
        if "does not exist" in result.stderr.lower():
            handle_error(
                f"Work item {work_item_id} does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr,
            )
        elif "invalid state" in result.stderr.lower():
            handle_error(
                f"Invalid state transition",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr + "\n\nUse list_types.py to see valid states for this work item type",
            )
        elif "field" in result.stderr.lower() and "does not exist" in result.stderr.lower():
            handle_error(
                "Invalid field name",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr + "\n\nUse list_types.py --type <type> --fields to see valid fields",
            )
        else:
            handle_error(
                f"Failed to update work item {work_item_id}",
                exit_code=ExitCode.COMMAND_ERROR,
                details=result.stderr,
            )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        handle_error(
            "Failed to parse update response",
            exit_code=ExitCode.COMMAND_ERROR,
            details=str(e),
        )
        return {}  # Never reached


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update Azure DevOps work item",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update state
  %(prog)s --id 12345 --state "Active"

  # Reassign work item
  %(prog)s --id 12345 --assign-to "user@domain.com"

  # Update multiple fields with comment
  %(prog)s --id 12345 --state "Resolved" --comment "Fixed issue"

  # Update custom field
  %(prog)s --id 12345 --field "Custom.Priority=High"

  # Multiple custom fields
  %(prog)s --id 12345 --field "Custom.Priority=High" --field "Custom.Severity=Critical"
""",
    )

    parser.add_argument("--id", required=True, help="Work item ID")
    parser.add_argument("--state", help="New state")
    parser.add_argument("--assign-to", help="New assignee email or display name")
    parser.add_argument("--title", help="New title")
    parser.add_argument("--description", help="New description (HTML supported)")
    parser.add_argument(
        "--field",
        action="append",
        help="Custom field update (format: FieldName=Value). Can specify multiple times.",
    )
    parser.add_argument(
        "--comment", help="Add comment explaining changes"
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
        return

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

    # Parse custom fields
    custom_fields = {}
    if args.field:
        for field_spec in args.field:
            if "=" not in field_spec:
                handle_error(
                    f"Invalid field format: {field_spec}",
                    exit_code=ExitCode.VALIDATION_ERROR,
                    details="Use format: FieldName=Value",
                )
            key, value = field_spec.split("=", 1)
            custom_fields[key.strip()] = value.strip()

    # Create wrapper and update work item
    wrapper = AzCliWrapper(org=org, project=project)

    try:
        updated_item = update_work_item(
            wrapper,
            work_item_id,
            state=args.state,
            assigned_to=args.assign_to,
            title=args.title,
            description=args.description,
            fields=custom_fields if custom_fields else None,
            comment=args.comment,
        )

        # Show success message
        fields = updated_item.get("fields", {})
        print(f"Successfully updated work item #{work_item_id}")
        print(f"Title: {fields.get('System.Title', 'N/A')}")
        print(f"State: {fields.get('System.State', 'N/A')}")
        print(f"Assigned To: {fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned')}")
        print(f"\nView at: {updated_item.get('_links', {}).get('html', {}).get('href', 'N/A')}")

    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
