"""Claude CLI installation and detection.

Auto-installs Claude CLI when missing, with smart path resolution and validation.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _find_claude_in_common_locations() -> Optional[str]:
    """Search for claude in common installation locations.

    Returns:
        Path to claude binary if found, None otherwise.
    """
    # Priority order: homebrew → npm global → system paths
    common_paths = [
        "/opt/homebrew/bin/claude",  # macOS Homebrew (Apple Silicon)
        "/usr/local/bin/claude",  # macOS Homebrew (Intel) / Linux
        "/usr/bin/claude",  # System-wide Linux
        str(Path.home() / ".local" / "bin" / "claude"),  # User-local
    ]

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Fall back to PATH search
    return shutil.which("claude")


def _validate_claude_binary(claude_path: str) -> bool:
    """Validate that claude binary works.

    Args:
        claude_path: Path to claude binary to validate.

    Returns:
        True if binary is valid and executable.
    """
    try:
        result = subprocess.run(
            [claude_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return False


def _install_claude_cli() -> bool:
    """Install Claude CLI via npm.

    Returns:
        True if installation succeeded, False otherwise.
    """
    npm_path = shutil.which("npm")
    if not npm_path:
        print("ERROR: npm not found in PATH. Cannot install Claude CLI.")
        print("Please install Node.js and npm first:")
        print("  https://nodejs.org/")
        return False

    print("Installing Claude CLI via npm...")
    print("Running: npm install -g @anthropic-ai/claude-code")

    try:
        result = subprocess.run(
            [npm_path, "install", "-g", "@anthropic-ai/claude-code"],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes for npm install
        )

        if result.returncode == 0:
            print("✅ Claude CLI installed successfully")
            return True
        print("❌ Claude CLI installation failed:")
        print(result.stderr)
        print("\nManual installation:")
        print("  npm install -g @anthropic-ai/claude-code")
        return False

    except subprocess.TimeoutExpired:
        print("❌ Claude CLI installation timed out")
        print("Try manually: npm install -g @anthropic-ai/claude-code")
        return False
    except Exception as e:
        print(f"❌ Unexpected error installing Claude CLI: {e}")
        return False


def get_claude_cli_path(auto_install: bool = True) -> Optional[str]:
    """Get path to Claude CLI binary, optionally installing if missing.

    Args:
        auto_install: If True, attempt to install Claude CLI if not found.

    Returns:
        Path to claude binary if available, None if not found/installed.
    """
    # First, try to find existing installation
    claude_path = _find_claude_in_common_locations()

    if claude_path and _validate_claude_binary(claude_path):
        return claude_path

    # If not found and auto-install is enabled, try to install
    if auto_install:
        if os.getenv("AMPLIHACK_NO_AUTO_INSTALL", "").lower() in ("1", "true", "yes"):
            print("Auto-installation disabled via AMPLIHACK_NO_AUTO_INSTALL")
            return None

        print("Claude CLI not found. Attempting auto-installation...")
        if _install_claude_cli():
            # Search again after installation
            claude_path = _find_claude_in_common_locations()
            if claude_path and _validate_claude_binary(claude_path):
                return claude_path

    # Installation failed or auto-install disabled
    print("\n⚠️  Claude CLI not found")
    print("Please install manually:")
    print("  npm install -g @anthropic-ai/claude-code")
    print("\nOr disable auto-install:")
    print("  export AMPLIHACK_NO_AUTO_INSTALL=1")

    return None


def ensure_claude_cli() -> str:
    """Ensure Claude CLI is available, installing if needed.

    Returns:
        Path to claude binary.

    Raises:
        RuntimeError: If Claude CLI cannot be found or installed.
    """
    claude_path = get_claude_cli_path(auto_install=True)

    if not claude_path:
        raise RuntimeError(
            "Claude CLI not available and auto-installation failed. "
            "Please install manually: npm install -g @anthropic-ai/claude-code"
        )

    return claude_path
