"""Copilot CLI launcher - simple wrapper around copilot command."""

import json
import os
import platform
import select
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

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


def _compare_versions(current: str, latest: str) -> bool:
    """Compare version strings to determine if update is available.

    Args:
        current: Current version string (e.g., "1.0.0" or "v1.0.0")
        latest: Latest version string (e.g., "1.0.1")

    Returns:
        True if latest > current, False otherwise
    """
    try:
        # Strip 'v' prefix if present
        current_clean = current.lstrip('v')
        latest_clean = latest.lstrip('v')

        # Parse version strings into tuples of integers
        current_parts = tuple(int(x) for x in current_clean.split('.'))
        latest_parts = tuple(int(x) for x in latest_clean.split('.'))

        # Python tuple comparison handles semantic versioning correctly
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        # Invalid version format - return False (no update)
        return False


def check_for_update() -> Optional[str]:
    """Check if a newer version of Copilot CLI is available.

    Returns:
        New version string if update available, None otherwise
    """
    try:
        # Get current version
        current_result = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if current_result.returncode != 0:
            return None

        # Parse version from output: "@github/copilot/1.4.0 linux-x64 node-v20.10.0"
        current_output = current_result.stdout.strip()
        if "/" not in current_output:
            return None

        parts = current_output.split("/")
        if len(parts) < 3:
            return None

        # Extract version from: "1.4.0 linux-x64..." -> "1.4.0"
        current_version = parts[2].split()[0]

        # Get latest version from npm
        latest_result = subprocess.run(
            ["npm", "view", "@github/copilot", "version"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if latest_result.returncode != 0:
            return None

        latest_version = latest_result.stdout.strip()

        if _compare_versions(current_version, latest_version):
            return latest_version

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, IndexError):
        return None


def detect_install_method() -> str:
    """Detect how Copilot CLI was installed.

    Returns:
        'npm' or 'uvx' based on installation method, defaults to 'npm'
    """
    try:
        # Check npm global installation
        npm_result = subprocess.run(
            ["npm", "list", "-g", "@github/copilot"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if npm_result.returncode == 0:
            # If the path contains uv/tools, it's actually uvx
            if "uv/tools" in npm_result.stdout or "uv\\tools" in npm_result.stdout:
                return "uvx"
            return "npm"

        # Check uvx installation if npm check failed
        uvx_result = subprocess.run(
            ["uvx", "list"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if uvx_result.returncode == 0 and "copilot" in uvx_result.stdout:
            return "uvx"

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "npm"


def prompt_user_to_update(new_version: str, install_method: str) -> bool:
    """Prompt user to update Copilot CLI with timeout.

    Args:
        new_version: The new version available
        install_method: Installation method ('npm' or 'uvx')

    Returns:
        True if user wants to update, False otherwise
    """
    print(f"🔄 Copilot CLI update available: v{new_version}")

    if install_method == "uvx":
        print("  Update: uvx --from @github/copilot@latest copilot")
    else:
        # Default to npm (install_method == "npm" or unknown)
        print("  Update: npm install -g @github/copilot")

    # Cross-platform timeout implementation
    timeout_seconds = 5
    user_input = None

    if platform.system() == "Windows":
        # Windows: Use threading-based timeout
        def get_input():
            nonlocal user_input
            try:
                user_input = input("Update now? (y/N): ").strip().lower()
            except EOFError:
                user_input = ""

        input_thread = threading.Thread(target=get_input)
        input_thread.daemon = True
        input_thread.start()
        input_thread.join(timeout=timeout_seconds)

        if input_thread.is_alive():
            # Timeout occurred - default to No
            print("\nTimeout - skipping update")
            return False
    else:
        # Unix: Use signal-based timeout
        def timeout_handler(signum, frame):
            raise TimeoutError("Input timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        try:
            user_input = input("Update now? (y/N): ").strip().lower()
            signal.alarm(0)  # Cancel alarm
        except TimeoutError:
            print("\nTimeout - skipping update")
            signal.signal(signal.SIGALRM, old_handler)
            return False
        except EOFError:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            return False
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    # Handle empty input or 'n' as No, only 'y' as Yes
    return user_input == "y"


def execute_update(install_method: str) -> bool:
    """Execute Copilot CLI update based on installation method.

    Args:
        install_method: Installation method ('npm' or 'uvx')

    Returns:
        True if update succeeded, False otherwise
    """
    print(f"\n📦 Updating Copilot CLI via {install_method}...")

    try:
        # Get current version before update
        try:
            pre_result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            pre_version = None
            if pre_result.returncode == 0:
                output = pre_result.stdout.strip()
                if "/" in output:
                    parts = output.split("/")
                    if len(parts) >= 3:
                        pre_version = parts[2].split()[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pre_version = None

        # Execute update command
        if install_method == "uvx":
            # uvx update: run copilot with latest version
            result = subprocess.run(
                ["uvx", "--from", "@github/copilot@latest", "copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        else:
            # npm update
            result = subprocess.run(
                ["npm", "install", "-g", "@github/copilot"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

        if result.returncode != 0:
            print(f"✗ Update failed: {result.stderr.strip()}")
            return False

        # Verify update by checking version
        try:
            post_result = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if post_result.returncode == 0:
                output = post_result.stdout.strip()
                if "/" in output:
                    parts = output.split("/")
                    if len(parts) >= 3:
                        post_version = parts[2].split()[0]
                        if pre_version and post_version != pre_version:
                            print(f"✓ Updated from {pre_version} to {post_version}")
                            return True
                        elif post_version:
                            print(f"✓ Update complete (version: {post_version})")
                            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
            pass

        # If version check fails but update command succeeded
        print("✓ Update completed")
        return True

    except subprocess.TimeoutExpired:
        print("✗ Update timed out")
        return False
    except FileNotFoundError:
        print(f"✗ Update failed: {install_method} not found")
        return False
    except Exception as e:
        print(f"✗ Update failed: {e}")
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


def get_copilot_directories() -> list[str]:
    """Get list of directories to provide copilot filesystem access.

    Returns:
        List of existing directory paths as strings.
        Non-existent directories are silently skipped.
    """
    directories = []

    # Collect candidate directories
    candidates = [
        Path.home(),
        Path(tempfile.gettempdir()),
        Path(os.getcwd()),
    ]

    # Filter to only existing directories
    for path in candidates:
        try:
            if path.exists() and path.is_dir():
                directories.append(str(path))
        except (OSError, RuntimeError):
            # Skip directories that raise errors (permissions, broken symlinks, etc.)
            continue

    return directories


def launch_copilot(args: list[str] | None = None, interactive: bool = True) -> int:
    """Launch Copilot CLI.

    Args:
        args: Arguments to pass to copilot
        interactive: If True, use subprocess for proper terminal handling on Windows

    Returns:
        Exit code
    """
    # Check for updates (non-blocking)
    try:
        new_version = check_for_update()
        if new_version:
            install_method = detect_install_method()
            if prompt_user_to_update(new_version, install_method):
                # User wants to update
                if execute_update(install_method):
                    print("✓ Copilot CLI updated successfully")
                else:
                    print("⚠ Update failed - continuing with current version")
    except Exception:
        # Silently ignore update check failures
        pass

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

    # Build command with filesystem access to user directories
    # Model can be overridden via COPILOT_MODEL env var (default: Opus 4.5)
    model = os.getenv("COPILOT_MODEL", "claude-opus-4.5")
    cmd = [
        "copilot",
        "--allow-all-tools",
        "--model",
        model,
    ]

    # Add all available directories (home, temp, cwd)
    for directory in get_copilot_directories():
        cmd.extend(["--add-dir", directory])

    # Disable GitHub MCP server to save context tokens
    cmd.extend(["--disable-mcp-server", "github-mcp-server"])

    if args:
        cmd.extend(args)

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False)
    return result.returncode
