#!/usr/bin/env python3
"""Link work items to parent items in Azure DevOps.

This tool creates parent-child relationships between work items.

Philosophy:
- Single responsibility: work item linking only
- Validate both work items exist before linking
- Clear error messages for invalid links
- Support different link types

Public API:
    link_parent: Create parent-child link
    validate_link_compatibility: Check if link is valid
"""

import argparse
import sys

from .common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
    validate_work_item_id,
)


def work_item_exists(work_item_id: int, org: str, project: str) -> bool:
    """Check if work item exists.

    Args:
        work_item_id: Work item ID to check
        org: Organization URL
        project: Project name

    Returns:
        True if work item exists, False otherwise
    """
    try:
        wrapper = AzCliWrapper(org=org, project=project)
        result = wrapper.devops_command(
            ["work-item", "show", "--id", str(work_item_id)],
            timeout=15,
        )
        return result.success
    except Exception:
        return False


def get_work_item_type(work_item_id: int, org: str, project: str) -> str | None:
    """Get work item type.

    Args:
        work_item_id: Work item ID
        org: Organization URL
        project: Project name

    Returns:
        Work item type string, or None if not found
    """
    try:
        wrapper = AzCliWrapper(org=org, project=project)
        result = wrapper.devops_command(
            ["work-item", "show", "--id", str(work_item_id)],
            timeout=15,
        )

        if not result.success:
            return None

        data = result.json_output
        if not data:
            return None

        return data.get("fields", {}).get("System.WorkItemType")

    except Exception:
        return None


def validate_link_compatibility(child_type: str, parent_type: str) -> bool:
    """Validate that child and parent types can be linked.

    Common valid relationships:
    - Task -> User Story
    - Task -> Bug
    - Task -> Feature
    - Bug -> Feature
    - User Story -> Feature
    - Feature -> Epic

    Args:
        child_type: Child work item type
        parent_type: Parent work item type

    Returns:
        True if link is valid, False otherwise
    """
    # Common valid parent-child relationships
    valid_relationships = {
        "Task": ["User Story", "Bug", "Feature", "Epic"],
        "Bug": ["Feature", "Epic"],
        "User Story": ["Feature", "Epic"],
        "Feature": ["Epic"],
    }

    # Check if relationship is valid
    valid_parents = valid_relationships.get(child_type, [])
    return parent_type in valid_parents or parent_type == "Epic"  # Epic can be parent to anything


def link_parent(
    child_id: int,
    parent_id: int,
    org: str,
    project: str,
    link_type: str = "Parent",
) -> bool:
    """Link work item to parent.

    Args:
        child_id: Child work item ID
        parent_id: Parent work item ID
        org: Organization URL
        project: Project name
        link_type: Link type (default: "Parent")

    Returns:
        True if link created successfully

    Raises:
        ValueError: If work items don't exist or link is invalid
        RuntimeError: If link creation fails
    """
    # Validate child exists
    if not work_item_exists(child_id, org, project):
        raise ValueError(f"Child work item {child_id} does not exist")

    # Validate parent exists
    if not work_item_exists(parent_id, org, project):
        raise ValueError(f"Parent work item {parent_id} does not exist")

    # Get work item types
    child_type = get_work_item_type(child_id, org, project)
    parent_type = get_work_item_type(parent_id, org, project)

    # Validate link compatibility (warning only, not blocking)
    if child_type and parent_type:
        if not validate_link_compatibility(child_type, parent_type):
            print(
                f"Warning: Linking {child_type} to {parent_type} may not be a standard relationship",
                file=sys.stderr,
            )

    # Create link
    wrapper = AzCliWrapper(org=org, project=project)
    result = wrapper.devops_command(
        [
            "work-item",
            "relation",
            "add",
            "--id",
            str(child_id),
            "--relation-type",
            link_type,
            "--target-id",
            str(parent_id),
        ],
        timeout=15,
    )

    if not result.success:
        raise RuntimeError(f"Failed to create link: {result.stderr}")

    return True


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Link work item to parent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Link Task to User Story
  python -m .claude.scenarios.az-devops-tools.link_parent \\
    --child 5678 \\
    --parent 1234

  # Link Bug to Feature
  python -m .claude.scenarios.az-devops-tools.link_parent \\
    --child 9999 \\
    --parent 8888

Common relationships:
  - Task -> User Story, Bug, Feature, Epic
  - Bug -> Feature, Epic
  - User Story -> Feature, Epic
  - Feature -> Epic

Link types:
  - Parent (default): Parent-child relationship
  - Related: Related items
  - Duplicate: Duplicate items
        """,
    )

    # Required arguments
    parser.add_argument(
        "--child",
        required=True,
        type=int,
        help="Child work item ID",
    )
    parser.add_argument(
        "--parent",
        required=True,
        type=int,
        help="Parent work item ID",
    )

    # Optional arguments
    parser.add_argument(
        "--link-type",
        default="Parent",
        help="Link type (default: Parent)",
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

    # Validate work item IDs
    try:
        child_id = validate_work_item_id(str(args.child))
        parent_id = validate_work_item_id(str(args.parent))
    except ValueError as e:
        handle_error(str(e), ExitCode.VALIDATION_ERROR)

    # Create link
    try:
        success = link_parent(
            child_id=child_id,
            parent_id=parent_id,
            org=org,
            project=project,
            link_type=args.link_type,
        )

        if success:
            print("✓ Successfully linked work items!")
            print(f"  Child: {child_id}")
            print(f"  Parent: {parent_id}")
            print(f"  Link Type: {args.link_type}")
            sys.exit(ExitCode.SUCCESS)
        else:
            handle_error("Failed to create link", ExitCode.COMMAND_ERROR)

    except ValueError as e:
        handle_error(str(e), ExitCode.VALIDATION_ERROR)
    except RuntimeError as e:
        handle_error(str(e), ExitCode.COMMAND_ERROR)
    except Exception as e:
        handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["link_parent", "validate_link_compatibility", "work_item_exists", "main"]
