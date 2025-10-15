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
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: npm not found. Install Node.js first.")
        return False


def launch_copilot(args: Optional[List[str]] = None, interactive: bool = True) -> int:
    """Launch Copilot CLI.

    Args:
        args: Arguments to pass to copilot
        interactive: If True, exec to replace process

    Returns:
        Exit code
    """
    # Ensure copilot is installed
    if not check_copilot():
        if not install_copilot() or not check_copilot():
            print("Failed to install Copilot CLI")
            return 1

    # Build command
    cmd = ["copilot", "--allow-all-tools"]
    if args:
        cmd.extend(args)

    # Launch
    if interactive:
        os.execvp(cmd[0], cmd)  # Replace process
        return 0
    result = subprocess.run(cmd, check=False)
    return result.returncode
