#!/usr/bin/env python3
"""
Tool: create_pr.py

Purpose: Create pull request in Azure DevOps repository

Usage:
    python create_pr.py --source <branch> --target <branch> --title <title> [options]

Examples:
    # Create PR from current branch to main
    python create_pr.py --source feature/auth --target main --title "Add authentication"

    # Create PR with description from file
    python create_pr.py --source feature/auth --target main --title "Add auth" --description @pr_desc.md

    # Create PR with reviewers and work items
    python create_pr.py --source feature/bug-fix --target main --title "Fix bug" --reviewers "user1@domain.com,user2@domain.com" --work-items "12345,12346"

    # Create draft PR
    python create_pr.py --source feature/wip --target main --title "WIP: New feature" --draft

Philosophy:
- Standard library + azure CLI wrapper
- Clear error messages with actionable guidance
- Fail-fast validation
- Self-contained and regeneratable
"""

import argparse
import json
from pathlib import Path

from common import AzCliWrapper, ExitCode, handle_error, load_config


def validate_branch_exists(wrapper: AzCliWrapper, repository: str, branch: str) -> bool:
    """Check if branch exists in repository.

    Args:
        wrapper: AzCliWrapper instance
        repository: Repository name
        branch: Branch name

    Returns:
        True if branch exists, False otherwise
    """
    result = wrapper.devops_command(
        [
            "repos",
            "ref",
            "list",
            "--repository",
            repository,
            "--filter",
            f"heads/{branch}",
            "--output",
            "json",
        ],
        timeout=30,
    )

    if result.success:
        try:
            refs = json.loads(result.stdout)
            return len(refs) > 0
        except json.JSONDecodeError:
            pass

    return False


def create_pull_request(
    wrapper: AzCliWrapper,
    repository: str,
    source_branch: str,
    target_branch: str,
    title: str,
    description: str | None = None,
    reviewers: list[str] | None = None,
    work_items: list[str] | None = None,
    draft: bool = False,
    auto_complete: bool = False,
    delete_source_branch: bool = False,
) -> dict:
    """Create pull request in Azure DevOps.

    Args:
        wrapper: AzCliWrapper instance
        repository: Repository name
        source_branch: Source branch name
        target_branch: Target branch name
        title: PR title
        description: PR description (markdown)
        reviewers: List of reviewer emails
        work_items: List of work item IDs to link
        draft: Create as draft PR
        auto_complete: Enable auto-complete
        delete_source_branch: Delete source branch after merge

    Returns:
        Pull request data

    Raises:
        SystemExit: If operation fails
    """
    # Build command
    cmd = [
        "repos",
        "pr",
        "create",
        "--repository",
        repository,
        "--source-branch",
        source_branch,
        "--target-branch",
        target_branch,
        "--title",
        title,
    ]

    if description:
        cmd.extend(["--description", description])

    if reviewers:
        cmd.extend(["--reviewers"] + reviewers)

    if work_items:
        cmd.extend(["--work-items"] + work_items)

    if draft:
        cmd.append("--draft")

    if auto_complete:
        cmd.append("--auto-complete")

    if delete_source_branch:
        cmd.append("--delete-source-branch")

    cmd.extend(["--output", "json"])

    result = wrapper.devops_command(cmd, timeout=60)

    if not result.success:
        # Check for common errors
        if "does not exist" in result.stderr.lower():
            handle_error(
                "Branch does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr
                + "\n\nVerify that source and target branches exist in the repository",
            )
        elif "already exists" in result.stderr.lower():
            handle_error(
                "Pull request already exists for these branches",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=result.stderr,
            )
        elif "permission" in result.stderr.lower():
            handle_error(
                "Permission denied",
                exit_code=ExitCode.AUTH_ERROR,
                details=result.stderr
                + "\n\nYou may not have permission to create pull requests in this repository",
            )
        else:
            handle_error(
                "Failed to create pull request",
                exit_code=ExitCode.COMMAND_ERROR,
                details=result.stderr,
            )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        handle_error(
            "Failed to parse pull request response",
            exit_code=ExitCode.COMMAND_ERROR,
            details=str(e),
        )
        return {}  # Never reached


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create Azure DevOps pull request",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create PR from current branch to main
  %(prog)s --source feature/auth --target main --title "Add authentication"

  # Create PR with description from file
  %(prog)s --source feature/auth --target main --title "Add auth" --description @pr_desc.md

  # Create PR with reviewers and work items
  %(prog)s --source feature/bug --target main --title "Fix bug" --reviewers "user1@domain.com,user2@domain.com" --work-items "12345,12346"

  # Create draft PR
  %(prog)s --source feature/wip --target main --title "WIP: New feature" --draft

  # Create PR with auto-complete
  %(prog)s --source feature/done --target main --title "Complete feature" --auto-complete --delete-source-branch

Note:
  Branch names should not include 'refs/heads/' prefix.
  Description supports markdown and can be loaded from file using @ prefix.
""",
    )

    parser.add_argument(
        "--repository",
        help="Repository name (defaults to project's default repo if not specified)",
    )
    parser.add_argument("--source", required=True, help="Source branch name")
    parser.add_argument("--target", default="main", help="Target branch name (default: main)")
    parser.add_argument("--title", required=True, help="Pull request title")
    parser.add_argument(
        "--description",
        help="Pull request description (markdown). Use @filename to load from file.",
    )
    parser.add_argument(
        "--reviewers",
        help="Comma-separated list of reviewer emails or display names",
    )
    parser.add_argument(
        "--work-items",
        help="Comma-separated list of work item IDs to link",
    )
    parser.add_argument("--draft", action="store_true", help="Create as draft pull request")
    parser.add_argument(
        "--auto-complete",
        action="store_true",
        help="Enable auto-complete when all policies pass",
    )
    parser.add_argument(
        "--delete-source-branch",
        action="store_true",
        help="Delete source branch after successful merge",
    )

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

    # Handle description from file
    description = args.description
    if description and description.startswith("@"):
        file_path = Path(description[1:])
        if not file_path.exists():
            handle_error(
                f"Description file not found: {file_path}",
                exit_code=ExitCode.VALIDATION_ERROR,
            )
        try:
            description = file_path.read_text()
        except OSError as e:
            handle_error(
                f"Failed to read description file: {e}",
                exit_code=ExitCode.VALIDATION_ERROR,
            )

    # Parse reviewers and work items
    reviewers = args.reviewers.split(",") if args.reviewers else None
    work_items = args.work_items.split(",") if args.work_items else None

    # Get repository name (use project name if not specified)
    repository = args.repository or project

    # Create wrapper
    wrapper = AzCliWrapper(org=org, project=project)

    try:
        # Validate branches exist
        print(f"Validating branches in repository '{repository}'...")
        if not validate_branch_exists(wrapper, repository, args.source):
            handle_error(
                f"Source branch '{args.source}' does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=f"Verify the branch exists in repository '{repository}'",
            )

        if not validate_branch_exists(wrapper, repository, args.target):
            handle_error(
                f"Target branch '{args.target}' does not exist",
                exit_code=ExitCode.VALIDATION_ERROR,
                details=f"Verify the branch exists in repository '{repository}'",
            )

        # Create pull request
        print("Creating pull request...")
        pr = create_pull_request(
            wrapper,
            repository,
            args.source,
            args.target,
            args.title,
            description,
            reviewers,
            work_items,
            args.draft,
            args.auto_complete,
            args.delete_source_branch,
        )

        # Show success message
        print(f"\nSuccessfully created pull request #{pr.get('pullRequestId')}")
        print(f"Title: {pr.get('title')}")
        print(f"Status: {'Draft' if pr.get('isDraft') else 'Active'}")
        print(f"Source: {args.source} → Target: {args.target}")

        if reviewers:
            print(f"Reviewers: {', '.join(reviewers)}")
        if work_items:
            print(f"Linked work items: {', '.join(work_items)}")

        pr_url = (
            pr.get("url", "")
            .replace("_apis/git/repositories", "_git")
            .replace("/pullRequests/", "/pullrequest/")
        )
        print(f"\nView PR at: {pr_url}")

    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
