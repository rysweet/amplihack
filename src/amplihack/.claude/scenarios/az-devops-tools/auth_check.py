#!/usr/bin/env python3
"""Check Azure DevOps authentication and configuration.

This tool verifies:
- Azure CLI is installed
- User is logged in with az login
- Azure DevOps extension is installed
- Organization and project are configured
- User has access to specified org/project

Philosophy:
- Single responsibility: authentication checking only
- Clear error messages with fix guidance
- Auto-fix capability for common issues
- No swallowed exceptions

Public API:
    check_auth: Main authentication check function
    auto_fix: Attempt to fix authentication issues
"""

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass

from .common import AzCliWrapper, ExitCode, load_config


@dataclass
class AuthStatus:
    """Authentication status result."""

    az_cli_installed: bool = False
    logged_in: bool = False
    devops_extension_installed: bool = False
    org_configured: bool = False
    project_configured: bool = False
    org_accessible: bool = False
    project_accessible: bool = False
    errors: list[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        """Initialize lists if None."""
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    @property
    def is_ready(self) -> bool:
        """Check if authentication is fully ready."""
        return (
            self.az_cli_installed
            and self.logged_in
            and self.devops_extension_installed
            and self.org_configured
            and self.project_configured
            and self.org_accessible
            and self.project_accessible
        )


def check_az_cli_installed() -> tuple[bool, str | None]:
    """Check if Azure CLI is installed.

    Returns:
        Tuple of (installed, error_message)
    """
    if not shutil.which("az"):
        return False, (
            "Azure CLI (az) not found. Install from: "
            "https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"
        )
    return True, None


def check_logged_in() -> tuple[bool, str | None]:
    """Check if user is logged in to Azure CLI.

    Returns:
        Tuple of (logged_in, error_message)
    """
    try:
        result = subprocess.run(
            ["az", "account", "show"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, None
        return False, "Not logged in to Azure CLI. Run: az login"
    except subprocess.TimeoutExpired:
        return False, "Timeout checking login status"
    except Exception as e:
        return False, f"Error checking login status: {e}"


def check_devops_extension() -> tuple[bool, str | None]:
    """Check if Azure DevOps extension is installed.

    Returns:
        Tuple of (installed, error_message)
    """
    try:
        result = subprocess.run(
            ["az", "extension", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "azure-devops" in result.stdout:
            return True, None
        return False, (
            "Azure DevOps extension not installed. Run: az extension add --name azure-devops"
        )
    except subprocess.TimeoutExpired:
        return False, "Timeout checking extension status"
    except Exception as e:
        return False, f"Error checking extension: {e}"


def check_org_project_config(
    org: str | None = None, project: str | None = None
) -> tuple[bool, bool, str | None]:
    """Check if organization and project are configured.

    Args:
        org: Organization URL (optional, will check config if not provided)
        project: Project name (optional, will check config if not provided)

    Returns:
        Tuple of (org_configured, project_configured, error_message)
    """
    config = load_config()

    org_configured = bool(org or config.get("org"))
    project_configured = bool(project or config.get("project"))

    error = None
    if not org_configured:
        error = (
            "Organization not configured. Set via:\n"
            "  - Environment variable: AZURE_DEVOPS_ORG_URL\n"
            "  - Command: az devops configure --defaults organization=https://dev.azure.com/YOUR_ORG\n"
            "  - Argument: --org https://dev.azure.com/YOUR_ORG"
        )
    elif not project_configured:
        error = (
            "Project not configured. Set via:\n"
            "  - Environment variable: AZURE_DEVOPS_PROJECT\n"
            "  - Command: az devops configure --defaults project=YOUR_PROJECT\n"
            "  - Argument: --project YOUR_PROJECT"
        )

    return org_configured, project_configured, error


def check_org_access(org: str) -> tuple[bool, str | None]:
    """Check if user has access to organization.

    Args:
        org: Organization URL

    Returns:
        Tuple of (accessible, error_message)
    """
    try:
        wrapper = AzCliWrapper(org=org)
        result = wrapper.devops_command(["project", "list"], timeout=15)

        if result.success:
            return True, None
        if "Authentication" in result.stderr or "401" in result.stderr:
            return False, f"Authentication failed for organization: {org}"
        if "403" in result.stderr or "Forbidden" in result.stderr:
            return False, f"Access denied to organization: {org}"
        return False, f"Cannot access organization {org}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Timeout accessing organization"
    except Exception as e:
        return False, f"Error accessing organization: {e}"


def check_project_access(org: str, project: str) -> tuple[bool, str | None]:
    """Check if user has access to specific project.

    Args:
        org: Organization URL
        project: Project name

    Returns:
        Tuple of (accessible, error_message)
    """
    try:
        wrapper = AzCliWrapper(org=org, project=project)
        result = wrapper.devops_command(
            [
                "work-item",
                "query",
                "--wiql",
                "SELECT [System.Id] FROM workitems WHERE [System.TeamProject] = @project",
            ],
            timeout=15,
        )

        if result.success:
            return True, None
        if "not found" in result.stderr.lower() or "404" in result.stderr:
            return False, f"Project not found: {project}"
        if "Authentication" in result.stderr or "401" in result.stderr:
            return False, f"Authentication failed for project: {project}"
        if "403" in result.stderr or "Forbidden" in result.stderr:
            return False, f"Access denied to project: {project}"
        return False, f"Cannot access project {project}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Timeout accessing project"
    except Exception as e:
        return False, f"Error accessing project: {e}"


def check_auth(org: str | None = None, project: str | None = None) -> AuthStatus:
    """Check all authentication and configuration requirements.

    Args:
        org: Organization URL (optional)
        project: Project name (optional)

    Returns:
        AuthStatus with detailed check results
    """
    status = AuthStatus()

    # Check Azure CLI installation
    installed, error = check_az_cli_installed()
    status.az_cli_installed = installed
    if error:
        status.errors.append(error)
        return status  # Can't proceed without az CLI

    # Check login status
    logged_in, error = check_logged_in()
    status.logged_in = logged_in
    if error:
        status.errors.append(error)
        return status  # Can't proceed without login

    # Check DevOps extension
    ext_installed, error = check_devops_extension()
    status.devops_extension_installed = ext_installed
    if error:
        status.errors.append(error)
        return status  # Can't proceed without extension

    # Check org/project configuration
    org_configured, project_configured, error = check_org_project_config(org, project)
    status.org_configured = org_configured
    status.project_configured = project_configured
    if error:
        status.errors.append(error)
        return status  # Can't proceed without config

    # Load actual org/project values
    config = load_config()
    org = org or config.get("org")
    project = project or config.get("project")

    # Check organization access
    org_accessible, error = check_org_access(org)
    status.org_accessible = org_accessible
    if error:
        status.errors.append(error)

    # Check project access (only if org is accessible)
    if org_accessible:
        project_accessible, error = check_project_access(org, project)
        status.project_accessible = project_accessible
        if error:
            status.errors.append(error)

    return status


def auto_fix(status: AuthStatus) -> AuthStatus:
    """Attempt to automatically fix authentication issues.

    Args:
        status: Current authentication status

    Returns:
        Updated authentication status after fix attempts
    """
    print("Attempting to auto-fix authentication issues...")

    # Fix: Install DevOps extension
    if status.az_cli_installed and status.logged_in and not status.devops_extension_installed:
        print("\n[1/3] Installing Azure DevOps extension...")
        try:
            result = subprocess.run(
                ["az", "extension", "add", "--name", "azure-devops"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("✓ Azure DevOps extension installed successfully")
                status.devops_extension_installed = True
                # Remove error from list
                status.errors = [e for e in status.errors if "extension" not in e.lower()]
            else:
                print(f"✗ Failed to install extension: {result.stderr}")
        except Exception as e:
            print(f"✗ Error installing extension: {e}")

    # Note: Cannot auto-fix login (requires interactive auth)
    if not status.logged_in:
        print("\n[2/3] Login required - please run manually:")
        print("    az login")
        status.warnings.append("Manual action required: Run 'az login'")

    # Note: Cannot auto-fix org/project config without user input
    if not status.org_configured or not status.project_configured:
        print("\n[3/3] Configuration required - please set manually:")
        if not status.org_configured:
            print("    az devops configure --defaults organization=https://dev.azure.com/YOUR_ORG")
        if not status.project_configured:
            print("    az devops configure --defaults project=YOUR_PROJECT")
        status.warnings.append("Manual action required: Configure org/project")

    return status


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check Azure DevOps authentication and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check default configuration
  python -m .claude.scenarios.az-devops-tools.auth_check

  # Check specific org/project
  python -m .claude.scenarios.az-devops-tools.auth_check \\
    --org https://dev.azure.com/myorg \\
    --project MyProject

  # Attempt auto-fix
  python -m .claude.scenarios.az-devops-tools.auth_check --auto-fix

Exit codes:
  0 - Authentication ready
  1 - Authentication issues found
  2 - Configuration issues found
        """,
    )

    parser.add_argument("--org", help="Azure DevOps organization URL")
    parser.add_argument("--project", help="Project name")
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Attempt to automatically fix issues",
    )
    parser.add_argument("--config", help="Config file path")

    args = parser.parse_args()

    # Load config and check auth
    print("Checking Azure DevOps authentication...\n")
    status = check_auth(org=args.org, project=args.project)

    # Print status
    print("Status:")
    print("  ✓ Azure CLI installed" if status.az_cli_installed else "  ✗ Azure CLI NOT installed")
    print("  ✓ Logged in" if status.logged_in else "  ✗ NOT logged in")
    print(
        "  ✓ DevOps extension installed"
        if status.devops_extension_installed
        else "  ✗ DevOps extension NOT installed"
    )
    print(
        "  ✓ Organization configured"
        if status.org_configured
        else "  ✗ Organization NOT configured"
    )
    print("  ✓ Project configured" if status.project_configured else "  ✗ Project NOT configured")
    print(
        "  ✓ Organization accessible"
        if status.org_accessible
        else "  ✗ Organization NOT accessible"
    )
    print("  ✓ Project accessible" if status.project_accessible else "  ✗ Project NOT accessible")

    # Print errors
    if status.errors:
        print("\nErrors:")
        for error in status.errors:
            print(f"  - {error}")

    # Auto-fix if requested
    if args.auto_fix and not status.is_ready:
        print("\n" + "=" * 60)
        status = auto_fix(status)
        print("=" * 60)

        # Re-check after auto-fix
        print("\nRe-checking authentication after auto-fix...\n")
        status = check_auth(org=args.org, project=args.project)

        print("Updated Status:")
        print(
            "  ✓ Azure CLI installed" if status.az_cli_installed else "  ✗ Azure CLI NOT installed"
        )
        print("  ✓ Logged in" if status.logged_in else "  ✗ NOT logged in")
        print(
            "  ✓ DevOps extension installed"
            if status.devops_extension_installed
            else "  ✗ DevOps extension NOT installed"
        )
        print(
            "  ✓ Organization configured"
            if status.org_configured
            else "  ✗ Organization NOT configured"
        )
        print(
            "  ✓ Project configured" if status.project_configured else "  ✗ Project NOT configured"
        )
        print(
            "  ✓ Organization accessible"
            if status.org_accessible
            else "  ✗ Organization NOT accessible"
        )
        print(
            "  ✓ Project accessible" if status.project_accessible else "  ✗ Project NOT accessible"
        )

    # Print warnings
    if status.warnings:
        print("\nWarnings:")
        for warning in status.warnings:
            print(f"  - {warning}")

    # Final result
    if status.is_ready:
        print("\n✓ Authentication is ready!")
        sys.exit(ExitCode.SUCCESS)
    else:
        print("\n✗ Authentication is NOT ready")
        if not args.auto_fix:
            print("\nTip: Run with --auto-fix to attempt automatic fixes")
        sys.exit(ExitCode.AUTH_ERROR if not status.logged_in else ExitCode.CONFIG_ERROR)


if __name__ == "__main__":
    main()


__all__ = ["check_auth", "auto_fix", "AuthStatus", "main"]
