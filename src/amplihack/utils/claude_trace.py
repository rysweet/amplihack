"""Claude-trace integration - ruthlessly simple implementation."""

import os
import shutil
import subprocess
from pathlib import Path


def should_use_trace() -> bool:
    """Check if claude-trace should be used instead of claude.

    Default behavior: Always prefer claude-trace unless explicitly disabled.
    """
    # Check if explicitly disabled
    use_trace_env = os.getenv("AMPLIHACK_USE_TRACE", "").lower()
    if use_trace_env in ("0", "false", "no"):
        return False

    # Default to using claude-trace
    return True


def get_claude_command() -> str:
    """Get the appropriate claude command (claude, claude-trace, or rustyclawd).

    Uses smart binary detection to avoid shell script wrappers and
    prefer reliable binaries. Checks for RustyClawd first (Rust implementation).

    Returns:
        Command name/path to use ('rustyclawd', 'claude-trace', or 'claude')

    Side Effects:
        May attempt to install claude-trace via npm if not found
    """
    # Check for RustyClawd (Rust implementation) first
    from .rustyclawd_detect import get_rustyclawd_path, should_use_rustyclawd

    if should_use_rustyclawd():
        rustyclawd = get_rustyclawd_path()
        if rustyclawd:
            print(f"Using RustyClawd (Rust implementation): {rustyclawd}")
            return str(rustyclawd)

    if not should_use_trace():
        print("Claude-trace explicitly disabled via AMPLIHACK_USE_TRACE=0")
        return "claude"

    # Smart detection of valid claude-trace binary
    claude_trace_path = _find_valid_claude_trace()
    if claude_trace_path:
        print(f"Using claude-trace for enhanced debugging: {claude_trace_path}")
        return "claude-trace"

    # Try to install claude-trace
    print("Claude-trace not found, attempting to install...")
    if _install_claude_trace():
        # Verify installation worked
        claude_trace_path = _find_valid_claude_trace()
        if claude_trace_path:
            print(f"Claude-trace installed successfully: {claude_trace_path}")
            return "claude-trace"
        print("Claude-trace installation completed but binary validation failed")

    # Fall back to claude
    print("Could not install claude-trace, falling back to standard claude")
    return "claude"


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


def _find_valid_claude_trace() -> str | None:
    """Find a valid claude-trace binary using smart detection.

    Searches for claude-trace binaries in order of preference:
    1. User-local npm installations (highest priority)
    2. Homebrew installations (most reliable)
    3. Global npm installations
    4. Other PATH locations

    Validates each candidate to ensure it's Node.js compatible.

    Returns:
        Path to valid claude-trace binary, or None if not found
    """
    # Define search paths in preference order
    user_npm_bin = Path.home() / ".npm-global" / "bin" / "claude-trace"

    search_paths = [
        # User-local npm (highest priority)
        str(user_npm_bin),
        str(Path.home() / ".local" / "bin" / "claude-trace"),
        # Homebrew locations (most reliable)
        "/opt/homebrew/bin/claude-trace",
        "/usr/local/bin/claude-trace",
        # Then use shutil.which for PATH search
        None,  # Placeholder for shutil.which result
    ]

    # Add shutil.which result to search list
    which_result = shutil.which("claude-trace")
    if which_result:
        # Insert after homebrew paths but before fallbacks
        search_paths[4] = which_result
    else:
        search_paths.pop()  # Remove placeholder

    # Test each candidate
    for path in search_paths:
        if path and _is_valid_claude_trace_binary(path):
            return path

    return None


def _is_valid_claude_trace_binary(path: str) -> bool:
    """Check if a path points to a valid claude-trace binary.

    Args:
        path: File path to check

    Returns:
        True if the binary is valid and Node.js compatible
    """
    try:
        # Check if file exists and is executable
        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_file():
            return False

        # Check basic executability
        if not os.access(path, os.X_OK):
            return False

        # Test execution to ensure it's not a broken wrapper
        return _test_claude_trace_execution(path)

    except (OSError, PermissionError):
        return False


def _test_claude_trace_execution(path: str) -> bool:
    """Test if a claude-trace binary actually executes correctly.

    Args:
        path: Path to claude-trace binary to test

    Returns:
        True if binary executes without syntax errors and appears to be claude-trace
    """
    try:
        # Run with --help flag to test basic functionality
        # Use a short timeout to avoid hanging
        # NOTE: We always test execution now, even for homebrew paths,
        # to catch bugs where claude-trace tries to require() the claude
        # binary instead of spawn()ing it (which causes SyntaxError on ELF)
        result = subprocess.run(
            [path, "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )

        # Consider success if:
        # 1. Process exits cleanly (returncode 0)
        # 2. Output is non-empty
        # 3. Output contains "claude" (case-insensitive)
        # 4. Output contains either "trace" or "usage" (case-insensitive)
        if result.returncode == 0:
            stdout_lower = (result.stdout or "").lower()

            # Must have non-empty output
            if not stdout_lower.strip():
                return False

            # Must mention "claude"
            if "claude" not in stdout_lower:
                return False

            # Must mention either "trace" or "usage"
            if "trace" not in stdout_lower and "usage" not in stdout_lower:
                return False

            # All checks passed
            return True

        return False

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        # Any execution failure means invalid binary
        # This includes exec format errors from shell scripts, etc.
        return False


def _install_claude_trace() -> bool:
    """Attempt to install claude-trace via npm using user-local installation.

    Returns:
        True if installation succeeded, False otherwise

    Side Effects:
        Prints helpful installation guidance if npm is not available
    """
    try:
        # Check if npm is available
        if not shutil.which("npm"):
            print("\nNPM not found - required to install claude-trace")
            print("\nTo install npm:")
            print("  macOS:    brew install node")
            print("  Linux:    sudo apt install npm  # or your package manager")
            print("  Windows:  winget install OpenJS.NodeJS")
            print("\nFor more information, see docs/PREREQUISITES.md")
            return False

        # Configure user-local npm environment
        env = _configure_user_local_npm()
        user_npm_bin = Path.home() / ".npm-global" / "bin"

        print("Installing claude-trace via npm (user-local)...")
        print(f"Target directory: {user_npm_bin}")
        print("Running: npm install -g @mariozechner/claude-trace --ignore-scripts")

        # Install claude-trace with user-local npm and --ignore-scripts for security
        result = subprocess.run(
            ["npm", "install", "-g", "@mariozechner/claude-trace", "--ignore-scripts"],
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"\nFailed to install claude-trace: {result.stderr}")
            print("\nYou can try installing manually:")
            print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
            print("  npm install -g @mariozechner/claude-trace --ignore-scripts")
            print('  export PATH="$HOME/.npm-global/bin:$PATH"')
            return False

        # Check if user needs to add to PATH
        print("✅ Claude-trace installed successfully")
        if not shutil.which("claude-trace"):
            print("\n⚠️  Add to your shell profile for future sessions:")
            print('  export PATH="$HOME/.npm-global/bin:$PATH"')

        return True

    except subprocess.TimeoutExpired:
        print("\nInstallation timed out. You can try installing manually:")
        print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
        print("  npm install -g @mariozechner/claude-trace --ignore-scripts")
        print('  export PATH="$HOME/.npm-global/bin:$PATH"')
        return False
    except subprocess.SubprocessError as e:
        print(f"\nError installing claude-trace: {e!s}")
        print("\nYou can try installing manually:")
        print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
        print("  npm install -g @mariozechner/claude-trace --ignore-scripts")
        print('  export PATH="$HOME/.npm-global/bin:$PATH"')
        return False
