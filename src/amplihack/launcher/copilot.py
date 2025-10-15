"""Copilot CLI launcher - simple wrapper around copilot command."""

import os
import subprocess
from typing import List, Optional


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


def launch_copilot(args: Optional[List[str]] = None, interactive: bool = True) -> int:
    """Launch Copilot CLI.

    Args:
        args: Arguments to pass to copilot
        interactive: If True, exec to replace process

    Returns:
        Exit code (only for non-interactive mode)
    """
    # Ensure copilot is installed
    if not check_copilot():
        if not install_copilot() or not check_copilot():
            print("Failed to install Copilot CLI")
            return 1

    # Build command with default --add-dir flag for full filesystem access
    # (safe in VM environment)
    cmd = [
        "copilot",
        "--allow-all-tools",
        "--add-dir",
        "/",
    ]
    if args:
        cmd.extend(args)

    # Launch
    if interactive:
        os.execvp(cmd[0], cmd)  # Replace process - never returns
        # This line is unreachable but helps type checkers
        return 0  # pragma: no cover

    # Non-interactive mode
    result = subprocess.run(cmd, check=False)
    return result.returncode
