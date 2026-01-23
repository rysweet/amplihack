"""Copilot CLI launcher - simple wrapper around copilot command."""

import json
import os
import shlex
import subprocess
from pathlib import Path

from ..context.adaptive.detector import LauncherDetector


def get_gh_auth_account() -> str | None:
    """Check if gh CLI is authenticated and return the account name.

    Returns:
        Account name if authenticated, None otherwise.
    """
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            # Parse output - may be in stdout or stderr depending on environment
            output = result.stdout + result.stderr
            # Parse output like "Logged in to github.com account USERNAME"
            for line in output.split("\n"):
                if "Logged in to" in line and "account" in line:
                    parts = line.split("account")
                    if len(parts) > 1:
                        # Extract account name (format: "account USERNAME (path)")
                        account_part = parts[1].strip()
                        account = account_part.split()[0] if account_part else None
                        return account
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def disable_github_mcp_server() -> bool:
    """Disable the GitHub MCP server by staging an MCP config.

    Creates or updates ~/.copilot/github-copilot/mcp.json to disable
    the github-mcp-server, saving context tokens.

    Returns:
        True if config was staged successfully, False otherwise.
    """
    mcp_config_dir = Path.home() / ".copilot" / "github-copilot"
    mcp_config_file = mcp_config_dir / "mcp.json"

    try:
        # Create directory if needed
        mcp_config_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if mcp_config_file.exists():
            config = json.loads(mcp_config_file.read_text())
        else:
            config = {}

        # Ensure mcpServers exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Disable github-mcp-server
        if "github-mcp-server" not in config["mcpServers"]:
            config["mcpServers"]["github-mcp-server"] = {}

        config["mcpServers"]["github-mcp-server"]["disabled"] = True

        # Write config
        mcp_config_file.write_text(json.dumps(config, indent=2) + "\n")
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not disable GitHub MCP server: {e}")
        return False


def check_copilot() -> bool:
    """Check if Copilot CLI is installed."""
    try:
        subprocess.run(["copilot", "--version"], capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_copilot() -> bool:
    """Install GitHub Copilot CLI via npm."""
    print("Installing GitHub Copilot CLI...")
    try:
        result = subprocess.run(["npm", "install", "-g", "@github/copilot"], check=False)
        if result.returncode == 0:
            print("✓ Copilot CLI installed")
            return True
        print("✗ Installation failed")
        return False
    except FileNotFoundError:
        print("Error: npm not found. Install Node.js first.")
        return False


def launch_copilot(args: list[str] | None = None, interactive: bool = True) -> int:
    """Launch Copilot CLI.

    Args:
        args: Arguments to pass to copilot
        interactive: If True, use subprocess for proper terminal handling on Windows

    Returns:
        Exit code
    """
    # Ensure copilot is installed
    if not check_copilot():
        if not install_copilot() or not check_copilot():
            print("Failed to install Copilot CLI")
            return 1

    # Disable GitHub MCP server to save context tokens
    # Users can re-enable by asking "please use the GitHub MCP server"
    if disable_github_mcp_server():
        print("✓ Disabled GitHub MCP server to save context tokens - using gh CLI instead")
        gh_account = get_gh_auth_account()
        if gh_account:
            print(f"  Using gh CLI with account: {gh_account}")
        else:
            print("  ⚠ gh CLI not authenticated - run 'gh auth login' for GitHub access")
        print("  To re-enable GitHub MCP, just ask: 'please use the GitHub MCP server'")

    # Write launcher context before launching
    project_root = Path(os.getcwd())
    detector = LauncherDetector(project_root)
    # Sanitize args for safe logging
    safe_args = " ".join(shlex.quote(arg) for arg in (args or []))
    detector.write_context(
        launcher_type="copilot",
        command=f"amplihack copilot {safe_args}",
        environment={"AMPLIHACK_LAUNCHER": "copilot"},
    )

    # CRITICAL: Create agent files and AGENTS.md BEFORE launching Copilot
    # Copilot autodiscovers these at startup
    try:
        import shutil

        import amplihack

        from ..context.adaptive.strategies import CopilotStrategy

        # Get package directory (where .claude/ is actually staged)
        package_dir = Path(amplihack.__file__).parent

        # User's working directory (where we'll create .github/agents/)
        user_dir = Path(os.getcwd())

        strategy = CopilotStrategy(user_dir)

        # Create individual agent files in user's .github/agents/
        # (Copies instead of symlinks for Windows compatibility)
        agents_dest = user_dir / ".github/agents"
        agents_dest.mkdir(parents=True, exist_ok=True)

        # Copy agents from PACKAGE directory .claude/agents/amplihack/
        # Performance: Only copy if source is newer (skip if up-to-date)
        source_agents = package_dir / ".claude/agents/amplihack"
        if source_agents.exists():
            # Clean stale agents first (removed/renamed agents)
            for old_file in agents_dest.glob("*.md"):
                old_file.unlink()

            copied = 0
            for source_file in source_agents.rglob("*.md"):
                # Flatten structure: core/architect.md → architect.md
                dest_file = agents_dest / source_file.name
                shutil.copy2(source_file, dest_file)
                copied += 1

            if copied > 0:
                print(f"✓ Prepared {copied} amplihack agents")

        # Load preferences - try LOCAL first, fallback to PACKAGE
        # This allows users to customize preferences per-project
        prefs_file = user_dir / ".claude/context/USER_PREFERENCES.md"
        if not prefs_file.exists():
            prefs_file = package_dir / ".claude/context/USER_PREFERENCES.md"

        if prefs_file.exists():
            prefs_content = prefs_file.read_text()
            strategy.inject_context(prefs_content)
    except Exception as e:
        # Fail gracefully - Copilot will work without preferences
        print(f"Warning: Could not prepare Copilot environment: {e}")

    # Build command with full filesystem access (safe in VM environment)
    # Model can be overridden via COPILOT_MODEL env var (default: Opus 4.5)
    model = os.getenv("COPILOT_MODEL", "claude-opus-4.5")
    cmd = [
        "copilot",
        "--allow-all-tools",
        "--model",
        model,
        "--add-dir",
        os.getcwd(),  # Add current directory for .github/agents/ access
    ]
    if args:
        cmd.extend(args)

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False)
    return result.returncode
