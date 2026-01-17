"""Copilot CLI launcher - simple wrapper around copilot command."""

import os
import shlex
import subprocess
from pathlib import Path

from ..context.adaptive.detector import LauncherDetector


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

    # Write launcher context before launching
    project_root = Path(os.getcwd())
    detector = LauncherDetector(project_root)
    # Sanitize args for safe logging
    safe_args = ' '.join(shlex.quote(arg) for arg in (args or []))
    detector.write_context(
        launcher_type="copilot",
        command=f"amplihack copilot {safe_args}",
        environment={"AMPLIHACK_LAUNCHER": "copilot"}
    )

    # CRITICAL: Create AGENTS.md BEFORE launching Copilot
    # Copilot autodiscovers AGENTS.md at startup, so it must exist first
    try:
        from ..context.adaptive.strategies import CopilotStrategy

        strategy = CopilotStrategy(project_root)

        # Load preferences and inject into AGENTS.md
        prefs_file = project_root / ".claude/context/USER_PREFERENCES.md"
        if prefs_file.exists():
            prefs_content = prefs_file.read_text()
            strategy.inject_context(prefs_content)
    except Exception as e:
        # Fail gracefully - Copilot will work without preferences
        print(f"Warning: Could not create AGENTS.md: {e}")

    # Build command with full filesystem access (safe in VM environment)
    cmd = [
        "copilot",
        "--allow-all-tools",
        "--model", "claude-opus-4.5",  # Use Opus for best performance
        "--add-dir",
        os.getcwd(),  # Add current directory for .github/agents/ access
    ]
    if args:
        cmd.extend(args)

    # Launch using subprocess.run() for proper terminal handling
    # Note: os.execvp() doesn't work properly on Windows - it corrupts stdin/terminal state
    result = subprocess.run(cmd, check=False)
    return result.returncode
