"""Claude-trace integration - ruthlessly simple implementation."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


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
    """Get the appropriate claude command (claude or claude-trace).

    Uses smart binary detection to avoid shell script wrappers and
    prefer reliable Node.js binaries.

    Returns:
        Command name to use ('claude' or 'claude-trace')

    Side Effects:
        May attempt to install claude-trace via npm if not found
    """
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


def _find_valid_claude_trace() -> Optional[str]:
    """Find a valid claude-trace binary using smart detection.

    Searches for claude-trace binaries in order of preference:
    1. Homebrew installations (most reliable)
    2. Global npm installations
    3. Other PATH locations

    Validates each candidate to ensure it's Node.js compatible.

    Returns:
        Path to valid claude-trace binary, or None if not found
    """
    # Define search paths in preference order
    search_paths = [
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
        search_paths[2] = which_result
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
        # Special handling for known good homebrew installation
        # The homebrew claude-trace is a symlink to a valid Node.js script
        if path in ["/opt/homebrew/bin/claude-trace", "/usr/local/bin/claude-trace"]:
            # Check if it's a symlink to a .js file (valid Node.js script)
            path_obj = Path(path)
            if path_obj.is_symlink():
                target = path_obj.resolve()
                if target.suffix == ".js" and target.exists():
                    # This is a valid homebrew installation
                    # Even if claude-trace fails to find a working claude binary,
                    # the claude-trace binary itself is valid
                    return True

        # Run with --version flag to test basic functionality
        # Use a short timeout to avoid hanging
        result = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Consider success if:
        # 1. Process exits cleanly (returncode 0 or 1 for --version)
        # 2. No JavaScript syntax errors in stderr
        # 3. Output suggests it's actually claude-trace (not just any binary)
        if result.returncode in (0, 1):
            stderr_lower = (result.stderr or "").lower()
            stdout_lower = (result.stdout or "").lower()
            combined_output = (stderr_lower + " " + stdout_lower).strip()

            # Check for common Node.js syntax error indicators
            syntax_errors = [
                "syntaxerror",
                "missing ) after argument list",
                "unexpected token",
                "cannot find module",
            ]

            # Special case: If claude-trace itself runs but the underlying claude has issues,
            # we should still accept claude-trace as valid if it shows claude-trace output
            if (
                "claude trace" in combined_output
                or "starting claude with traffic logging" in combined_output
            ):
                # Even if there are errors downstream, claude-trace itself is valid
                return True

            # If there are syntax errors, definitely not valid
            if any(error in stderr_lower for error in syntax_errors):
                return False

            # For claude-trace, we expect either:
            # 1. Version output mentioning "claude" or "trace"
            # 2. Or help text when --version fails but stderr is clean
            # 3. Exclude obvious non-claude binaries (python, node, etc.)

            # Exclude common binaries that aren't claude-trace
            excluded_patterns = ["python", "node.js", "npm version", "usage: python"]

            if any(pattern in combined_output for pattern in excluded_patterns):
                return False

            # If output mentions claude or trace, likely good
            if "claude" in combined_output or "trace" in combined_output:
                return True

            # If no specific claude/trace mention but clean execution, accept
            # (handles cases where claude-trace --version might not output anything useful)
            return len(combined_output) < 1000  # Avoid huge help texts from wrong binaries

        return False

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        # Any execution failure means invalid binary
        # This includes exec format errors from shell scripts, etc.
        return False


def _install_claude_trace() -> bool:
    """Attempt to install claude-trace via npm.

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

        # Install claude-trace globally
        result = subprocess.run(
            ["npm", "install", "-g", "@mariozechner/claude-trace"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"\nFailed to install claude-trace: {result.stderr}")
            print("\nYou can try installing manually:")
            print("  npm install -g @mariozechner/claude-trace")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("\nInstallation timed out. You can try installing manually:")
        print("  npm install -g @mariozechner/claude-trace")
        return False
    except subprocess.SubprocessError as e:
        print(f"\nError installing claude-trace: {e!s}")
        print("\nYou can try installing manually:")
        print("  npm install -g @mariozechner/claude-trace")
        return False
