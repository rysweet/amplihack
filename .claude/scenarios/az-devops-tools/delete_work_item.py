#!/usr/bin/env python3
"""
Tool: delete_work_item.py

Purpose: Delete work item with confirmation

Usage:
    python delete_work_item.py --id <work_item_id> [options]

Examples:
    # Delete work item (with confirmation prompt)
    python delete_work_item.py --id 12345

    # Delete without confirmation prompt
    python delete_work_item.py --id 12345 --yes

    # Permanently destroy (cannot be recovered)
    python delete_work_item.py --id 12345 --permanent --yes

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


def get_work_item_info(wrapper: AzCliWrapper, work_item_id: int) -> dict | None:
    """Get basic work item info for confirmation display.

    Args:
        wrapper: AzCliWrapper instance
        work_item_id: Work item ID

    Returns:
        Work item data or None if not found
    """
    result = wrapper.devops_command(
        ["boards", "work-item", "show", "--id", str(work_item_id), "--output", "json"],
        timeout=30,
    )

    if result.success:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass

    return None


def delete_work_item(
    wrapper: AzCliWrapper, work_item_id: int, permanent: bool = False
) -> bool:
    """Delete work item.

    Args:
        wrapper: AzCliWrapper instance
        work_item_id: Work item ID
        permanent: If True, permanently destroy (cannot be recovered)

    Returns:
        True if successful

    Raises:
        SystemExit: If operation fails
    """
    cmd = ["boards", "work-item", "delete", "--id", str(work_item_id)]

    if permanent:
        cmd.append("--destroy")

    cmd.append("--yes")  # Skip az CLI confirmation

    result = wrapper.devops_command(cmd, timeout=30)

    if not result.success:
        if "does not exist" in result.stderr.lower():
            handle_error(
                f"Work item {work_item_id} does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr,
            )
        elif "permission" in result.stderr.lower():
            handle_error(
                f"Permission denied: Cannot delete work item {work_item_id}",
                exit_code=ExitCode.AUTH_ERROR,
                details=result.stderr + "\n\nYou may not have permission to delete work items in this project",
            )
        else:
            handle_error(
                f"Failed to delete work item {work_item_id}",
                exit_code=ExitCode.COMMAND_ERROR,
                details=result.stderr,
            )

    return True


def confirm_deletion(work_item: dict | None, permanent: bool) -> bool:
    """Prompt user to confirm deletion.

    Args:
        work_item: Work item data (None if not found)
        permanent: Whether this is a permanent deletion

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "=" * 60)
    print("DELETION CONFIRMATION")
    print("=" * 60)

    if work_item:
        fields = work_item.get("fields", {})
        print(f"Work Item ID:   {work_item.get('id')}")
        print(f"Type:           {fields.get('System.WorkItemType', 'Unknown')}")
        print(f"Title:          {fields.get('System.Title', 'No title')}")
        print(f"State:          {fields.get('System.State', 'Unknown')}")

        # Check for relations
        relations = work_item.get("relations", [])
        if relations:
            print(f"\nWARNING: This work item has {len(relations)} relation(s)")
            print("Deleting may affect linked work items")
    else:
        print("WARNING: Could not retrieve work item details")

    print("\nDeletion Type: " + ("PERMANENT (cannot be recovered)" if permanent else "Soft delete (can be recovered)"))
    print("=" * 60)

    response = input("\nAre you sure you want to delete this work item? (yes/no): ")
    return response.lower() in ("yes", "y")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Delete Azure DevOps work item",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete work item (with confirmation)
  %(prog)s --id 12345

  # Delete without confirmation prompt
  %(prog)s --id 12345 --yes

  # Permanently destroy (cannot be recovered)
  %(prog)s --id 12345 --permanent --yes

Note:
  By default, work items are soft-deleted and can be recovered.
  Use --permanent to destroy permanently (cannot be undone).
""",
    )

    parser.add_argument("--id", required=True, help="Work item ID to delete")
    parser.add_argument(
        "--permanent",
        action="store_true",
        help="Permanently destroy work item (cannot be recovered)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
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

    # Create wrapper
    wrapper = AzCliWrapper(org=org, project=project)

    try:
        # Get work item info for confirmation
        work_item = None
        if not args.yes:
            work_item = get_work_item_info(wrapper, work_item_id)

            # Confirm deletion
            if not confirm_deletion(work_item, args.permanent):
                print("\nDeletion cancelled.")
                sys.exit(0)

        # Delete work item
        delete_work_item(wrapper, work_item_id, args.permanent)

        print(f"\nSuccessfully deleted work item #{work_item_id}")
        if not args.permanent:
            print("Note: This was a soft delete. The work item can be recovered if needed.")

    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
