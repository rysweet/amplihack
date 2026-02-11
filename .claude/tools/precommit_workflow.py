#!/usr/bin/env python3
"""Pre-commit workflow tool for handling pre-commit hook failures.

This tool provides functionality to analyze, fix, and verify pre-commit issues.

Usage:
    python -m claude.tools.precommit_workflow analyze
    python -m claude.tools.precommit_workflow auto-fix --tools prettier,black
    python -m claude.tools.precommit_workflow verify-env
    python -m claude.tools.precommit_workflow verify-success
"""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


class PreCommitWorkflow:
    """Handles pre-commit workflow operations."""

    # Mapping of common tools to their auto-fix commands
    AUTO_FIX_COMMANDS = {
        "prettier": "npx prettier --write",
        "black": "black",
        "ruff": "ruff format",
        "ruff-fix": "ruff --fix",
        "isort": "isort",
        "autopep8": "autopep8 -i",
        "eslint": "npx eslint --fix",
        "rustfmt": "rustfmt",
    }

    def __init__(self):
        """Initialize the workflow handler."""
        self.project_root = self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find the project root by looking for .git directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return Path.cwd()

    def _run_command(self, command: list[str], check: bool = False) -> tuple[int, str, str]:
        """Run a command safely without shell interpretation.

        Args:
            command: Command and arguments as list (NOT string)
            check: Whether to raise CalledProcessError on non-zero exit

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Security:
            - NEVER uses shell=True (prevents shell injection CWE-78)
            - Command must be list[str], not string
            - No shell metacharacter interpretation
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                check=check,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout or "", e.stderr or ""

    def analyze_failures(self) -> dict[str, Any]:
        """Analyze pre-commit failures from the most recent run.

        Returns:
            Dictionary with analysis results including:
            - failed_hooks: List of failed hook IDs
            - issues: Detailed issues by hook
            - fixable: List of auto-fixable issues
            - manual_fixes: List of issues requiring manual intervention
        """
        print("Analyzing pre-commit failures...")

        # Try to run pre-commit to get current state
        returncode, stdout, stderr = self._run_command(["pre-commit", "run", "--all-files"])

        result = {
            "success": returncode == 0,
            "failed_hooks": [],
            "issues": {},
            "fixable": [],
            "manual_fixes": [],
        }

        if returncode == 0:
            print("✓ No pre-commit failures detected")
            return result

        # Parse output to identify failed hooks
        lines = (stdout + stderr).split("\n")
        current_hook = None

        for line in lines:
            # Detect hook failures (format: "hook-id.......................Failed")
            if "Failed" in line and "." in line:
                hook_id = line.split(".")[0].strip()
                if hook_id:
                    current_hook = hook_id
                    result["failed_hooks"].append(hook_id)
                    result["issues"][hook_id] = []

            # Collect error messages for current hook
            elif current_hook and line.strip() and not line.startswith("-"):
                result["issues"][current_hook].append(line.strip())

        # Categorize issues
        for hook_id in result["failed_hooks"]:
            # Check if auto-fixable
            if any(tool in hook_id for tool in ["prettier", "black", "ruff", "eslint", "isort"]):
                result["fixable"].append(hook_id)
            else:
                result["manual_fixes"].append(hook_id)

        # Display analysis
        print(f"\n❌ Found {len(result['failed_hooks'])} failed hooks:")
        for hook_id in result["failed_hooks"]:
            print(f"  - {hook_id}")

        if result["fixable"]:
            print(f"\n🔧 Auto-fixable hooks ({len(result['fixable'])}):")
            for hook_id in result["fixable"]:
                print(f"  - {hook_id}")

        if result["manual_fixes"]:
            print(f"\n⚠️  Manual fixes required ({len(result['manual_fixes'])}):")
            for hook_id in result["manual_fixes"]:
                print(f"  - {hook_id}")

        return result

    def auto_fix(self, tools: list[str] | None = None) -> bool:
        """Run auto-fix for specified tools or all known tools.

        Args:
            tools: List of tool names to run auto-fix for. If None, tries all known tools.

        Returns:
            True if all fixes succeeded, False otherwise.
        """
        if tools is None:
            # Try common formatting tools
            tools = ["ruff", "prettier", "black"]

        print(f"Running auto-fix for tools: {', '.join(tools)}")
        all_success = True

        for tool in tools:
            if tool not in self.AUTO_FIX_COMMANDS:
                print(f"⚠️  Unknown tool: {tool}")
                continue

            command_str = self.AUTO_FIX_COMMANDS[tool]

            # Add file patterns based on tool
            if tool in ["prettier"] or tool in ["black", "ruff"]:
                command_str += " ."
            elif tool == "ruff-fix":
                command_str = "ruff --fix ."

            # Convert string command to list for security
            command = shlex.split(command_str)

            print(f"  Running: {' '.join(command)}")
            returncode, stdout, stderr = self._run_command(command)

            if returncode == 0:
                print(f"  ✓ {tool} succeeded")
            else:
                print(f"  ❌ {tool} failed")
                if stderr:
                    print(f"     Error: {stderr[:200]}")
                all_success = False

        return all_success

    def verify_environment(self) -> dict[str, bool]:
        """Verify pre-commit environment is properly set up.

        Returns:
            Dictionary with verification results for each check.
        """
        print("Verifying pre-commit environment...")
        checks = {}

        # Check pre-commit installed
        returncode, stdout, _ = self._run_command(["pre-commit", "--version"])
        checks["pre-commit_installed"] = returncode == 0
        if checks["pre-commit_installed"]:
            print(f"✓ pre-commit installed: {stdout.strip()}")
        else:
            print("❌ pre-commit not installed")

        # Check config file exists
        config_path = self.project_root / ".pre-commit-config.yaml"
        checks["config_exists"] = config_path.exists()
        if checks["config_exists"]:
            print(f"✓ Config file exists: {config_path}")
        else:
            print(f"❌ Config file missing: {config_path}")

        # Check hooks installed
        if checks["pre-commit_installed"] and checks["config_exists"]:
            returncode, _, _ = self._run_command(["pre-commit", "install", "--install-hooks"])
            checks["hooks_installed"] = returncode == 0
            if checks["hooks_installed"]:
                print("✓ Pre-commit hooks installed")
            else:
                print("❌ Failed to install pre-commit hooks")
        else:
            checks["hooks_installed"] = False

        # Check for required tools
        tools_to_check = {
            "ruff": ["ruff", "--version"],
            "prettier": ["npx", "prettier", "--version"],
            "pyright": ["pyright", "--version"],
        }

        for tool, command in tools_to_check.items():
            returncode, stdout, _ = self._run_command(command)
            checks[f"{tool}_available"] = returncode == 0
            if returncode == 0:
                print(f"✓ {tool} available: {stdout.strip()}")
            else:
                print(f"⚠️  {tool} not available (optional)")

        # Overall status
        essential_checks = ["pre-commit_installed", "config_exists", "hooks_installed"]
        all_essential_ok = all(checks.get(check, False) for check in essential_checks)

        if all_essential_ok:
            print("\n✅ Pre-commit environment is properly configured")
        else:
            print("\n❌ Pre-commit environment needs setup")
            print("   Run: pre-commit install --install-hooks")

        return checks

    def verify_success(self) -> bool:
        """Verify all pre-commit checks pass.

        Returns:
            True if all checks pass, False otherwise.
        """
        print("Running pre-commit checks on all files...")

        returncode, stdout, stderr = self._run_command(["pre-commit", "run", "--all-files"])

        if returncode == 0:
            print("✅ All pre-commit checks passed!")
            return True
        print("❌ Pre-commit checks failed")
        print("\nOutput:")
        print(stdout)
        if stderr:
            print("\nErrors:")
            print(stderr)
        print("\nRun 'python -m claude.tools.precommit_workflow analyze' for details")
        return False


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Pre-commit workflow tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m claude.tools.precommit_workflow analyze
  python -m claude.tools.precommit_workflow auto-fix
  python -m claude.tools.precommit_workflow auto-fix --tools prettier,ruff
  python -m claude.tools.precommit_workflow verify-env
  python -m claude.tools.precommit_workflow verify-success
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze command
    subparsers.add_parser("analyze", help="Analyze pre-commit failures")

    # Auto-fix command
    fix_parser = subparsers.add_parser("auto-fix", help="Run auto-fix for formatting issues")
    fix_parser.add_argument(
        "--tools",
        type=str,
        help="Comma-separated list of tools to run (e.g., prettier,black,ruff)",
    )

    # Verify environment command
    subparsers.add_parser("verify-env", help="Verify pre-commit environment setup")

    # Verify success command
    subparsers.add_parser("verify-success", help="Verify all pre-commit checks pass")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    workflow = PreCommitWorkflow()

    if args.command == "analyze":
        result = workflow.analyze_failures()
        return 0 if result["success"] else 1

    if args.command == "auto-fix":
        tools = None
        if args.tools:
            tools = [t.strip() for t in args.tools.split(",")]
        success = workflow.auto_fix(tools)
        return 0 if success else 1

    if args.command == "verify-env":
        checks = workflow.verify_environment()
        essential = ["pre-commit_installed", "config_exists", "hooks_installed"]
        success = all(checks.get(check, False) for check in essential)
        return 0 if success else 1

    if args.command == "verify-success":
        success = workflow.verify_success()
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
