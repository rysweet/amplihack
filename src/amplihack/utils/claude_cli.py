"""Claude CLI installation and detection.

Auto-installs Claude CLI when missing, with smart path resolution and validation.

Philosophy:
- Opt-in auto-installation for security (requires AMPLIHACK_AUTO_INSTALL=1 or UVX mode)
- User-local npm installation to avoid permission issues
- Platform-aware path detection (user-local, homebrew, npm global, system paths)
- Validate binary execution before use
- Standard library only (no external dependencies)
- Supply chain protection via --ignore-scripts flag

Public API:
    get_claude_cli_path: Get path to Claude CLI, optionally auto-installing
    ensure_claude_cli: Ensure Claude CLI is available, raise on failure
"""

__all__ = [
    "get_claude_cli_path",
    "ensure_claude_cli",
]

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _is_uvx_mode() -> bool:
    """Check if running in UVX mode.

    Returns:
        True if AMPLIHACK_UVX_MODE environment variable is set to a truthy value.
    """
    return os.getenv("AMPLIHACK_UVX_MODE", "").lower() in ("1", "true", "yes")


def _configure_user_local_npm() -> dict[str, str]:
    """Configure npm to use user-local installation paths.

    Sets up environment variables to install npm packages in ~/.npm-global
    instead of requiring sudo/root access.

    Returns:
        Dictionary of environment variables for npm user-local installation.
    """
    user_npm_dir = Path.home() / ".npm-global"
    user_npm_bin = user_npm_dir / "bin"

    # Create directory if it doesn't exist
    user_npm_dir.mkdir(parents=True, exist_ok=True)
    user_npm_bin.mkdir(parents=True, exist_ok=True)

    # Create environment with npm prefix for user-local installation
    env = os.environ.copy()
    env["NPM_CONFIG_PREFIX"] = str(user_npm_dir)

    # Add user npm bin to PATH if not already there
    current_path = env.get("PATH", "")
    user_bin_str = str(user_npm_bin)
    if user_bin_str not in current_path:
        env["PATH"] = f"{user_bin_str}:{current_path}"

    return env


def _find_claude_in_common_locations() -> Optional[str]:
    """Search for claude in common installation locations.

    Returns:
        Path to claude binary if found, None otherwise.
    """
    # Priority order: user-local → homebrew → npm global → system paths
    user_npm_bin = Path.home() / ".npm-global" / "bin" / "claude"

    common_paths = [
        str(user_npm_bin),  # User-local npm (highest priority)
        str(Path.home() / ".local" / "bin" / "claude"),  # User-local alternative
        "/opt/homebrew/bin/claude",  # macOS Homebrew (Apple Silicon)
        "/usr/local/bin/claude",  # macOS Homebrew (Intel) / Linux
        "/usr/bin/claude",  # System-wide Linux
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
    """Install Claude CLI via npm using user-local installation.

    Returns:
        True if installation succeeded, False otherwise.
    """
    npm_path = shutil.which("npm")
    if not npm_path:
        print("ERROR: npm not found in PATH. Cannot install Claude CLI.")
        print("Please install Node.js and npm first:")
        print("  https://nodejs.org/")
        return False

    # Configure user-local npm environment
    env = _configure_user_local_npm()
    user_npm_bin = Path.home() / ".npm-global" / "bin"

    print("Installing Claude CLI via npm (user-local)...")
    print(f"Target directory: {user_npm_bin}")
    print("Running: npm install -g @anthropic-ai/claude-code --ignore-scripts")

    try:
        # Use --ignore-scripts for supply chain security
        # Install to user-local directory via NPM_CONFIG_PREFIX
        result = subprocess.run(
            [npm_path, "install", "-g", "@anthropic-ai/claude-code", "--ignore-scripts"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minutes for npm install
        )

        if result.returncode == 0:
            # Validate the installed binary
            claude_path = _find_claude_in_common_locations()
            if not claude_path or not _validate_claude_binary(claude_path):
                print("❌ Installed binary failed validation")
                print("\nThe binary was installed but may not be in your PATH.")
                print("Add to your shell profile (~/.bashrc, ~/.zshrc, etc.):")
                print('  export PATH="$HOME/.npm-global/bin:$PATH"')
                print("\nThen restart your shell or run:")
                print("  source ~/.bashrc  # or ~/.zshrc")
                return False

            print("✅ Claude CLI installed and validated successfully")
            print(f"Binary location: {claude_path}")

            # Check if user needs to add to PATH
            if not shutil.which("claude"):
                print("\n⚠️  Add to your shell profile for future sessions:")
                print('  export PATH="$HOME/.npm-global/bin:$PATH"')

            return True

        # Sanitized error - details logged, not exposed to user
        print("❌ Claude CLI installation failed")
        print("Check npm configuration and permissions")
        print("\nManual installation:")
        print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
        print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
        print('  export PATH="$HOME/.npm-global/bin:$PATH"')
        return False

    except subprocess.TimeoutExpired:
        print("❌ Claude CLI installation timed out after 120 seconds")
        print("Try manually:")
        print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
        print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
        return False
    except Exception:
        print("❌ Unexpected error installing Claude CLI")
        print("Try manually:")
        print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
        print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
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
        # Auto-enable in UVX mode OR when explicitly enabled
        auto_install_enabled = _is_uvx_mode() or os.getenv(
            "AMPLIHACK_AUTO_INSTALL", ""
        ).lower() in (
            "1",
            "true",
            "yes",
        )

        if not auto_install_enabled:
            print("\n⚠️  Claude CLI not found")
            print("Auto-installation requires explicit consent:")
            print("  export AMPLIHACK_AUTO_INSTALL=1")
            print("\nOr install manually:")
            print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
            print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
            print('  export PATH="$HOME/.npm-global/bin:$PATH"')
            return None

        print("Claude CLI not found. Auto-installation enabled, proceeding...")
        if _install_claude_cli():
            # Search again after installation
            claude_path = _find_claude_in_common_locations()
            if claude_path and _validate_claude_binary(claude_path):
                return claude_path

    # Installation failed or auto-install disabled
    print("\n⚠️  Claude CLI not found")
    print("Please install manually:")
    print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
    print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
    print('  export PATH="$HOME/.npm-global/bin:$PATH"')

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
