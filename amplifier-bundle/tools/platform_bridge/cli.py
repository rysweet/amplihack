"""Unified CLI interface for platform bridge.

Philosophy:
- Simple command structure: platform-bridge <command> [args]
- Auto-detects platform from git remote
- Delegates to appropriate bridge implementation
- Clear error messages with context
"""

import argparse
import json
import sys

from .azdo_bridge import AzureDevOpsBridge
from .detector import Platform, PlatformDetector, detect_platform
from .github_bridge import GitHubBridge


def create_bridge(repo_path: str = "."):
    """Create appropriate bridge based on detected platform.

    Args:
        repo_path: Path to git repository

    Returns:
        Platform bridge instance (GitHubBridge or AzDoBridge)

    Raises:
        RuntimeError: If platform detection fails
        ValueError: If platform is unsupported
    """
    platform = detect_platform(repo_path)

    if platform == Platform.GITHUB:
        return GitHubBridge()
    if platform == Platform.AZDO:
        return AzureDevOpsBridge()
    raise ValueError(f"Unsupported platform: {platform}")


class CLI:
    """Command-line interface for platform bridge operations."""

    def __init__(self, platform: str | None = None):
        """Initialize CLI.

        Args:
            platform: Platform override ("github" or "azdo"). If None, auto-detects.
        """
        if platform:
            # Use specified platform
            if platform.lower() == "github":
                self.platform = Platform.GITHUB
            elif platform.lower() == "azdo":
                self.platform = Platform.AZDO
            else:
                raise ValueError(f"Unsupported platform: {platform}")
        else:
            # Auto-detect platform
            try:
                detector = PlatformDetector()
                self.platform = detector.detect()
            except Exception:
                # If detection fails, set to None and let run() handle it
                self.platform = None

    def _get_bridge(self):
        """Get appropriate bridge for detected platform."""
        if self.platform == Platform.GITHUB:
            return GitHubBridge()
        if self.platform == Platform.AZDO:
            return AzureDevOpsBridge()
        if self.platform == Platform.UNKNOWN or self.platform is None:
            raise RuntimeError("Unknown or unsupported platform detected")
        raise RuntimeError(f"Unsupported platform: {self.platform}")

    def run(self, args: list[str]) -> int:
        """Run CLI command.

        Args:
            args: Command line arguments (without program name)

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parser = argparse.ArgumentParser(
            prog="platform-bridge", description="Unified CLI for GitHub and Azure DevOps operations"
        )

        # Global options
        parser.add_argument(
            "--platform",
            choices=["github", "azdo"],
            help="Platform override (auto-detected if not specified)",
        )

        subparsers = parser.add_subparsers(dest="command", help="Command to execute")

        # create-issue command
        create_issue_parser = subparsers.add_parser("create-issue", help="Create issue")
        create_issue_parser.add_argument("--title", required=True, help="Issue title")
        create_issue_parser.add_argument("--body", required=True, help="Issue description")
        create_issue_parser.add_argument("--labels", nargs="*", help="Issue labels")

        # create-pr command
        create_pr_parser = subparsers.add_parser("create-pr", help="Create pull request")
        create_pr_parser.add_argument("--title", required=True, help="PR title")
        create_pr_parser.add_argument("--body", required=True, help="PR description")
        create_pr_parser.add_argument("--branch", required=True, help="Source branch")
        create_pr_parser.add_argument("--base", help="Target branch (default: main)")

        # mark-pr-ready command
        mark_pr_ready_parser = subparsers.add_parser("mark-pr-ready", help="Mark PR as ready")
        mark_pr_ready_parser.add_argument("pr_number", type=int, help="PR number")

        # add-pr-comment command
        add_pr_comment_parser = subparsers.add_parser("add-pr-comment", help="Add PR comment")
        add_pr_comment_parser.add_argument("pr_number", type=int, help="PR number")
        add_pr_comment_parser.add_argument("--comment", help="Comment text (or read from stdin)")

        # check-ci-status command
        check_ci_parser = subparsers.add_parser("check-ci-status", help="Check CI status")
        check_ci_parser.add_argument("ref", help="Branch or PR number")

        try:
            parsed_args = parser.parse_args(args)

            # Handle --platform override
            if hasattr(parsed_args, "platform") and parsed_args.platform:
                if parsed_args.platform == "github":
                    self.platform = Platform.GITHUB
                elif parsed_args.platform == "azdo":
                    self.platform = Platform.AZDO

            # Validate command is provided
            if not parsed_args.command:
                parser.print_help()
                return 1

            # Get bridge instance
            try:
                bridge = self._get_bridge()
            except RuntimeError as e:
                print(json.dumps({"success": False, "error": str(e)}))
                sys.stderr.write(f"Error: {e}\n")
                return 1

            # Execute command
            if parsed_args.command == "create-issue":
                return self._create_issue(bridge, parsed_args)
            if parsed_args.command == "create-pr":
                return self._create_pr(bridge, parsed_args)
            if parsed_args.command == "mark-pr-ready":
                return self._mark_pr_ready(bridge, parsed_args)
            if parsed_args.command == "add-pr-comment":
                return self._add_pr_comment(bridge, parsed_args)
            if parsed_args.command == "check-ci-status":
                return self._check_ci_status(bridge, parsed_args)
            sys.stderr.write(f"Error: Unknown command: {parsed_args.command}\n")
            return 1

        except SystemExit as e:
            # argparse calls sys.exit() on error
            return e.code if e.code is not None else 1
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            return 1

    def _create_issue(self, bridge, args) -> int:
        """Handle create-issue command."""
        try:
            kwargs = {"title": args.title, "body": args.body}
            if hasattr(args, "labels") and args.labels:
                kwargs["labels"] = args.labels

            result = bridge.create_issue(**kwargs)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
            return 1

    def _create_pr(self, bridge, args) -> int:
        """Handle create-pr command."""
        try:
            kwargs = {"title": args.title, "body": args.body, "branch": args.branch}
            if hasattr(args, "base") and args.base:
                kwargs["base"] = args.base

            result = bridge.create_draft_pr(**kwargs)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
            return 1

    def _mark_pr_ready(self, bridge, args) -> int:
        """Handle mark-pr-ready command."""
        try:
            result = bridge.mark_pr_ready(pr_number=args.pr_number)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
            return 1

    def _add_pr_comment(self, bridge, args) -> int:
        """Handle add-pr-comment command."""
        try:
            # Get comment from args or stdin
            comment = args.comment if args.comment else sys.stdin.read()

            result = bridge.add_pr_comment(pr_number=args.pr_number, comment=comment)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
            return 1

    def _check_ci_status(self, bridge, args) -> int:
        """Handle check-ci-status command."""
        try:
            result = bridge.check_ci_status(ref=args.ref)
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1
        except Exception as e:
            result = {"success": False, "error": str(e)}
            print(json.dumps(result, indent=2))
            return 1


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command line arguments (for testing). If None, uses sys.argv[1:]

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if argv is None:
        argv = sys.argv[1:]

    # Extract --platform if present before creating CLI
    platform = None
    if "--platform" in argv:
        idx = argv.index("--platform")
        if idx + 1 < len(argv):
            platform = argv[idx + 1]

    try:
        cli = CLI(platform=platform)
        return cli.run(argv)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
