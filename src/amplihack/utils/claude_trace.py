"""Claude-trace integration - ruthlessly simple implementation."""

import logging
import os
import shutil
import subprocess
from pathlib import Path

__all__ = [
    "should_use_trace",
    "get_claude_command",
    "detect_claude_trace_status",
    "clear_status_cache",
]

# Module-level cache for detection results to avoid repeated checks
_claude_trace_status_cache: dict[str, str] = {}
_fallback_message_shown = False

# Note: This module uses both print() and logging:
# - print() for user-facing messages (installation status, fallback notices)
# - logging (logger.debug) for internal diagnostics and debugging
logger = logging.getLogger(__name__)


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

    Implements fallback logic:
    1. Try RustyClawd (Rust native implementation)
    2. Try claude-trace (if working)
    3. Fall back to claude (if claude-trace broken/missing)

    Returns:
        Command name/path to use ('rustyclawd', 'claude-trace', or 'claude')

    Side Effects:
        - May attempt to install claude-trace via npm if not found
        - Shows informational message once if falling back from broken claude-trace
    """
    global _fallback_message_shown

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
        # Found a working claude-trace
        status = detect_claude_trace_status(claude_trace_path)
        if status == "working":
            print(f"Using claude-trace for enhanced debugging: {claude_trace_path}")
            return "claude-trace"
        elif status == "broken":
            # claude-trace exists but is broken - fall back to claude
            if not _fallback_message_shown:
                print(f"\nℹ️  Found claude-trace at {claude_trace_path} but it failed execution test")
                print("   Falling back to standard 'claude' command")
                print("   Tip: Reinstall claude-trace with: npm install -g @mariozechner/claude-trace\n")
                _fallback_message_shown = True
            return "claude"

    # Try to install claude-trace
    print("Claude-trace not found, attempting to install...")
    if _install_claude_trace():
        # Verify installation worked
        claude_trace_path = _find_valid_claude_trace()
        if claude_trace_path:
            status = detect_claude_trace_status(claude_trace_path)
            if status == "working":
                print(f"Claude-trace installed successfully: {claude_trace_path}")
                return "claude-trace"
            elif status == "broken":
                print("Claude-trace installed but binary validation failed")
                if not _fallback_message_shown:
                    print("Falling back to standard 'claude' command")
                    _fallback_message_shown = True
                return "claude"
        print("Claude-trace installation completed but binary not found")

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
        status = detect_claude_trace_status(path)
        return status == "working"

    except (OSError, PermissionError):
        return False


def detect_claude_trace_status(path: str) -> str:
    """Detect the status of a claude-trace binary.

    Tests whether a claude-trace binary is:
    - "working": Executes successfully with valid output
    - "broken": Exists but fails at runtime (ELF format error, syntax error, etc.)
    - "missing": Does not exist or not executable

    Args:
        path: Path to claude-trace binary to test

    Returns:
        Status string: "working", "broken", or "missing"

    Note:
        Results are cached to avoid repeated checks during the same session.
    """
    # Check cache first
    if path in _claude_trace_status_cache:
        return _claude_trace_status_cache[path]

    # Check if file exists and is executable
    path_obj = Path(path)
    if not path_obj.exists() or not path_obj.is_file():
        _claude_trace_status_cache[path] = "missing"
        return "missing"

    if not os.access(path, os.X_OK):
        _claude_trace_status_cache[path] = "missing"
        return "missing"

    # Test execution
    try:
        result = subprocess.run(
            [path, "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )

        # Check for common error indicators
        if result.returncode != 0:
            stderr_lower = (result.stderr or "").lower()

            # Detect specific error patterns that indicate broken binary
            broken_patterns = [
                "exec format error",
                "cannot execute binary",
                "syntax error",
                "unexpected token",
                "bad interpreter",
            ]

            if any(pattern in stderr_lower for pattern in broken_patterns):
                logger.debug(f"claude-trace at {path} is broken: {result.stderr[:100]}")
                _claude_trace_status_cache[path] = "broken"
                return "broken"

            # Non-zero exit without clear error pattern - treat as broken
            _claude_trace_status_cache[path] = "broken"
            return "broken"

        # Exit code 0 - validate output
        stdout_lower = (result.stdout or "").lower()

        # Must have non-empty output
        if not stdout_lower.strip():
            _claude_trace_status_cache[path] = "broken"
            return "broken"

        # Must mention "claude"
        if "claude" not in stdout_lower:
            _claude_trace_status_cache[path] = "broken"
            return "broken"

        # Must mention either "trace" or "usage"
        if "trace" not in stdout_lower and "usage" not in stdout_lower:
            _claude_trace_status_cache[path] = "broken"
            return "broken"

        # All checks passed
        _claude_trace_status_cache[path] = "working"
        return "working"

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        # Execution failure indicates broken binary
        logger.debug(f"claude-trace at {path} failed to execute: {e}")
        _claude_trace_status_cache[path] = "broken"
        return "broken"


def clear_status_cache() -> None:
    """Clear the cached claude-trace status detection results.

    This is primarily useful for testing, allowing tests to reset detection
    state between test cases. May also be useful for forcing re-detection
    after manual fixes or reinstallation of claude-trace.

    Side Effects:
        - Clears the module-level _claude_trace_status_cache dictionary
        - Resets the _fallback_message_shown flag
    """
    global _fallback_message_shown
    _claude_trace_status_cache.clear()
    _fallback_message_shown = False


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
