#!/usr/bin/env python3
"""
Tool: list_repos.py

Purpose: List repositories in Azure DevOps project or organization

Usage:
    python list_repos.py [options]

Examples:
    # List all repositories in configured project
    python list_repos.py

    # Include repository details (size, branches, etc.)
    python list_repos.py --include-details

    # List repos across all projects
    python list_repos.py --all-projects

    # JSON output
    python list_repos.py --format json

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

from common import AzCliWrapper, ExitCode, format_table, handle_error, load_config


def list_repositories(
    wrapper: AzCliWrapper, include_details: bool = False
) -> list[dict[str, Any]]:
    """List repositories from Azure DevOps.

    Args:
        wrapper: AzCliWrapper instance
        include_details: Include detailed repository information

    Returns:
        List of repository data

    Raises:
        SystemExit: If operation fails
    """
    cmd = ["repos", "list", "--output", "json"]

    result = wrapper.devops_command(cmd, timeout=30)

    if not result.success:
        handle_error(
            "Failed to list repositories",
            exit_code=ExitCode.COMMAND_ERROR,
            details=result.stderr,
        )

    try:
        repos = json.loads(result.stdout)

        # Get additional details if requested
        if include_details and repos:
            for repo in repos:
                repo_name = repo.get("name")
                repo_id = repo.get("id")

                # Get repository stats
                stats_result = wrapper.devops_command(
                    ["repos", "show", "--repository", repo_id, "--output", "json"],
                    timeout=30,
                )
                if stats_result.success:
                    try:
                        repo_details = json.loads(stats_result.stdout)
                        repo["size"] = repo_details.get("size", 0)
                        repo["defaultBranch"] = repo_details.get("defaultBranch", "")
                    except json.JSONDecodeError:
                        pass

        return repos
    except (json.JSONDecodeError, KeyError) as e:
        handle_error(
            "Failed to parse repository data",
            exit_code=ExitCode.COMMAND_ERROR,
            details=str(e),
        )
        return []  # Never reached


def format_output(repos: list[dict[str, Any]], output_format: str, include_details: bool) -> str:
    """Format repositories according to output format.

    Args:
        repos: List of repository data
        output_format: One of 'table', 'json'
        include_details: Whether detailed information was included

    Returns:
        Formatted string
    """
    if not repos:
        return "No repositories found."

    if output_format == "json":
        return json.dumps(repos, indent=2)

    # Table format
    if include_details:
        headers = ["Name", "ID", "Default Branch", "Size (KB)", "Web URL"]
        rows = []
        for repo in repos:
            size_kb = repo.get("size", 0) // 1024 if repo.get("size") else 0
            default_branch = repo.get("defaultBranch", "").split("/")[-1] if repo.get("defaultBranch") else "N/A"
            rows.append(
                [
                    repo.get("name", ""),
                    repo.get("id", "")[:8],  # Truncate ID
                    default_branch,
                    str(size_kb),
                    repo.get("webUrl", "")[:40],  # Truncate URL
                ]
            )
    else:
        headers = ["Name", "ID", "Web URL"]
        rows = []
        for repo in repos:
            rows.append(
                [
                    repo.get("name", ""),
                    repo.get("id", "")[:8],  # Truncate ID
                    repo.get("webUrl", "")[:50],  # Truncate URL
                ]
            )

    return format_table(headers, rows)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="List Azure DevOps repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all repositories in configured project
  %(prog)s

  # Include repository details
  %(prog)s --include-details

  # JSON output
  %(prog)s --format json
""",
    )

    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Include detailed repository information (size, branches, etc.)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # Config options
    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    org = args.org or config.get("org")
    project = args.project or config.get("project")

    if not org:
        handle_error(
            "Organization must be configured",
            exit_code=ExitCode.CONFIG_ERROR,
            details="Use 'az devops configure' or set AZURE_DEVOPS_ORG_URL environment variable",
        )

    # Create wrapper
    wrapper = AzCliWrapper(org=org, project=project)

    try:
        repos = list_repositories(wrapper, args.include_details)
        output = format_output(repos, args.format, args.include_details)
        print(output)

    except Exception as e:
        handle_error(
            f"Unexpected error: {e}",
            exit_code=ExitCode.COMMAND_ERROR,
        )


if __name__ == "__main__":
    main()
