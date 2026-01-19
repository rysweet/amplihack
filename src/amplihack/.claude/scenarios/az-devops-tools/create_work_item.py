#!/usr/bin/env python3
"""Create Azure DevOps work items with formatted descriptions.

This tool creates work items with:
- Auto-formatted markdown descriptions (converted to HTML)
- Support for all work item types (User Story, Bug, Task, etc.)
- Optional parent linking
- Custom field values
- Comprehensive validation

Philosophy:
- Single responsibility: work item creation
- Auto-format descriptions for better readability
- Clear validation with actionable errors
- Composable with other tools (format_html, link_parent)

Public API:
    create_work_item: Create work item with all parameters
    validate_work_item_type: Validate work item type exists
"""

import argparse
import sys

from .common import (
    AzCliWrapper,
    ExitCode,
    handle_error,
    load_config,
)
from .format_html import markdown_to_html


def validate_work_item_type(work_item_type: str, org: str, project: str) -> bool:
    """Validate that work item type exists in project.

    Args:
        work_item_type: Type to validate (e.g., "User Story", "Bug")
        org: Organization URL
        project: Project name

    Returns:
        True if type exists, False otherwise
    """
    try:
        wrapper = AzCliWrapper(org=org, project=project)
        result = wrapper.devops_command(
            ["work-item", "type", "list"],
            timeout=15,
        )

        if not result.success:
            return False

        # Parse JSON output
        data = result.json_output
        if not data:
            return False

        # Check if type exists in list
        types = [t.get("name", "").lower() for t in data.get("value", [])]
        return work_item_type.lower() in types

    except Exception:
        return False


def create_work_item(
    title: str,
    work_item_type: str,
    org: str,
    project: str,
    description: str | None = None,
    assigned_to: str | None = None,
    area: str | None = None,
    iteration: str | None = None,
    parent_id: int | None = None,
    tags: list[str] | None = None,
    additional_fields: dict[str, str] | None = None,
    auto_format_description: bool = True,
) -> dict:
    """Create work item in Azure DevOps.

    Args:
        title: Work item title
        work_item_type: Type (e.g., "User Story", "Bug", "Task")
        org: Organization URL
        project: Project name
        description: Work item description (markdown if auto_format_description=True)
        assigned_to: User to assign (email or display name)
        area: Area path
        iteration: Iteration path
        parent_id: Parent work item ID (will create link)
        tags: List of tags
        additional_fields: Additional field values as dict
        auto_format_description: Convert description from markdown to HTML

    Returns:
        Dictionary with work item details (id, url, fields)

    Raises:
        ValueError: If validation fails
        RuntimeError: If creation fails
    """
    # Validate work item type
    if not validate_work_item_type(work_item_type, org, project):
        raise ValueError(
            f"Invalid work item type: '{work_item_type}'. Use list_types.py to see available types."
        )

    # Auto-format description if requested
    if description and auto_format_description:
        description = markdown_to_html(description)

    # Build command
    wrapper = AzCliWrapper(org=org, project=project)
    command_args = [
        "--type",
        work_item_type,
        "--title",
        title,
    ]

    # Add optional fields
    if description:
        command_args.extend(["--description", description])
    if assigned_to:
        command_args.extend(["--assigned-to", assigned_to])
    if area:
        command_args.extend(["--area", area])
    if iteration:
        command_args.extend(["--iteration", iteration])
    if tags:
        command_args.extend(["--tags", ",".join(tags)])

    # Add additional fields
    if additional_fields:
        for field, value in additional_fields.items():
            command_args.extend(["--fields", f"{field}={value}"])

    # Execute creation
    result = wrapper.devops_command(
        ["work-item", "create"] + command_args,
        timeout=30,
    )

    if not result.success:
        raise RuntimeError(f"Failed to create work item: {result.stderr}")

    # Parse result
    work_item_data = result.json_output
    if not work_item_data:
        raise RuntimeError("Failed to parse work item creation response")

    work_item_id = work_item_data.get("id")
    if not work_item_id:
        raise RuntimeError("Work item created but no ID returned")

    # Link to parent if specified
    if parent_id:
        try:
            # Use link_parent tool to create link
            from .link_parent import link_parent

            link_parent(
                child_id=work_item_id,
                parent_id=parent_id,
                org=org,
                project=project,
            )
        except Exception as e:
            # Work item created but linking failed - warn but don't fail
            print(
                f"Warning: Work item {work_item_id} created but parent link failed: {e}",
                file=sys.stderr,
            )

    return {
        "id": work_item_id,
        "url": work_item_data.get("url", ""),
        "fields": work_item_data.get("fields", {}),
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create Azure DevOps work item",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create User Story
  python -m .claude.scenarios.az-devops-tools.create_work_item \\
    --type "User Story" \\
    --title "Implement user login" \\
    --description "As a user, I want to log in..."

  # Create Bug with assignment
  python -m .claude.scenarios.az-devops-tools.create_work_item \\
    --type Bug \\
    --title "Login button not working" \\
    --assigned-to user@example.com \\
    --tags "urgent,login"

  # Create Task with parent
  python -m .claude.scenarios.az-devops-tools.create_work_item \\
    --type Task \\
    --title "Write unit tests" \\
    --parent 1234 \\
    --area "MyProject\\Development"

  # Read description from file
  python -m .claude.scenarios.az-devops-tools.create_work_item \\
    --type "User Story" \\
    --title "My Story" \\
    --description "$(cat story.md)"

Field names:
  Use list_types.py to see available fields for each work item type.

Common fields:
  - System.Title (--title)
  - System.Description (--description)
  - System.AssignedTo (--assigned-to)
  - System.AreaPath (--area)
  - System.IterationPath (--iteration)
  - System.Tags (--tags)
        """,
    )

    # Required arguments
    parser.add_argument(
        "--type",
        required=True,
        help='Work item type (e.g., "User Story", "Bug", "Task")',
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Work item title",
    )

    # Optional arguments
    parser.add_argument(
        "--description",
        help="Work item description (markdown format)",
    )
    parser.add_argument(
        "--assigned-to",
        help="User to assign (email or display name)",
    )
    parser.add_argument(
        "--area",
        help="Area path",
    )
    parser.add_argument(
        "--iteration",
        help="Iteration path",
    )
    parser.add_argument(
        "--parent",
        type=int,
        help="Parent work item ID",
    )
    parser.add_argument(
        "--tags",
        help="Comma-separated tags",
    )
    parser.add_argument(
        "--fields",
        action="append",
        help="Additional field (format: Field=Value). Can be specified multiple times.",
    )
    parser.add_argument(
        "--no-format",
        action="store_true",
        help="Don't auto-format description from markdown to HTML",
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

    # Parse tags
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",")]

    # Parse additional fields
    additional_fields = None
    if args.fields:
        additional_fields = {}
        for field_spec in args.fields:
            if "=" not in field_spec:
                handle_error(
                    f"Invalid field specification: {field_spec}",
                    ExitCode.VALIDATION_ERROR,
                    "Use format: Field=Value",
                )
            field, value = field_spec.split("=", 1)
            additional_fields[field.strip()] = value.strip()

    # Create work item
    try:
        work_item = create_work_item(
            title=args.title,
            work_item_type=args.type,
            org=org,
            project=project,
            description=args.description,
            assigned_to=args.assigned_to,
            area=args.area,
            iteration=args.iteration,
            parent_id=args.parent,
            tags=tags,
            additional_fields=additional_fields,
            auto_format_description=not args.no_format,
        )

        # Print success
        print("✓ Work item created successfully!")
        print(f"  ID: {work_item['id']}")
        print(f"  URL: {work_item['url']}")
        print(f"  Type: {args.type}")
        print(f"  Title: {args.title}")

        if args.parent:
            print(f"  Parent: {args.parent}")

        sys.exit(ExitCode.SUCCESS)

    except ValueError as e:
        handle_error(str(e), ExitCode.VALIDATION_ERROR)
    except RuntimeError as e:
        handle_error(str(e), ExitCode.COMMAND_ERROR)
    except Exception as e:
        handle_error(f"Unexpected error: {e}", ExitCode.COMMAND_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["create_work_item", "validate_work_item_type", "main"]
