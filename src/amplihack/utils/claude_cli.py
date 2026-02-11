"""Claude CLI installation and detection.

Auto-installs Claude CLI when missing, with smart path resolution and validation.

Philosophy:
- Auto-installation enabled by default (can be disabled with AMPLIHACK_AUTO_INSTALL=0)
- User-local npm installation to avoid permission issues
- Platform-aware path detection (user-local npm paths, homebrew, npm global, system paths)
- Validate binary execution before use
- Auto-recovery from validation failures (corrupted/non-executable binaries)
- Single retry on failure before requiring manual intervention
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


def _is_uvx_mode() -> bool:
    """Check if running in UVX mode.

    Returns:
        True if running via UVX deployment (detected by UVX detection module).
    """
    try:
        from .uvx_detection import is_uvx_deployment

        return is_uvx_deployment()
    except ImportError:
        # Fallback to environment variable check if uvx_detection not available
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
        # Update current process PATH so subsequent shutil.which() calls find the binary
        os.environ["PATH"] = env["PATH"]

    return env


def _update_shell_profile_path() -> bool:
    """Append npm-global bin to shell profile so PATH persists across sessions.

    Detects the user's shell from $SHELL and updates the appropriate profile
    file (~/.zshrc for zsh, ~/.bashrc otherwise). Idempotent -- does nothing
    if the export line is already present.

    Returns:
        True if the profile already contains the line or was updated successfully.
        False if the profile could not be written.
    """
    shell = os.environ.get("SHELL", "")
    if shell.endswith("/zsh") or shell.endswith("/zsh5"):
        profile_path = Path.home() / ".zshrc"
    else:
        profile_path = Path.home() / ".bashrc"

    export_line = 'export PATH="$HOME/.npm-global/bin:$PATH"'

    # Check if already present
    try:
        if profile_path.exists():
            content = profile_path.read_text()
            if export_line in content:
                return True
        # Append the export line
        with open(profile_path, "a") as f:
            f.write(f"\n# Added by amplihack\n{export_line}\n")
        return True
    except (OSError, PermissionError):
        return False


def _find_claude_in_common_locations() -> str | None:
    """Search for claude in PATH, falling back to known install location.

    First checks PATH via shutil.which(). If not found, checks the known
    npm-global install location directly. When the fallback location exists,
    adds its directory to os.environ["PATH"] so subsequent calls succeed.

    Returns:
        Path to claude binary if found, None otherwise.
    """
    # Use shutil.which() to search PATH - this respects the user's environment
    found = shutil.which("claude")
    if found:
        return found

    # Fallback: check the known user-local npm install location directly
    npm_claude = Path.home() / ".npm-global" / "bin" / "claude"
    if npm_claude.exists():
        npm_bin = str(npm_claude.parent)
        current_path = os.environ.get("PATH", "")
        if npm_bin not in current_path:
            os.environ["PATH"] = f"{npm_bin}:{current_path}"
        return str(npm_claude)

    return None


def _print_manual_install_instructions():
    """Print manual installation instructions for Claude CLI."""
    print('  export NPM_CONFIG_PREFIX="$HOME/.npm-global"')
    print("  npm install -g @anthropic-ai/claude-code --ignore-scripts")
    print('  export PATH="$HOME/.npm-global/bin:$PATH"')


def _validate_claude_binary(claude_path: str) -> bool:
    """Validate that claude binary works.

    Args:
        claude_path: Path to claude binary to validate.

    Returns:
        True if binary is valid and executable.
    """
    # Import here to avoid circular dependency
    from .prerequisites import safe_subprocess_call

    returncode, stdout, stderr = safe_subprocess_call(
        [claude_path, "--version"],
        context="validating Claude CLI binary",
        timeout=5,
    )
    return returncode == 0


def _remove_failed_binary(binary_path: Path) -> None:
    """Remove a failed Claude binary.

    Args:
        binary_path: Path to the binary to remove

    Note: Uses missing_ok=True for idempotency.
    """
    try:
        binary_path.unlink(missing_ok=True)
        print(f"   Removed failed binary: {binary_path}")
    except OSError as e:
        print(f"   Warning: Could not remove binary: {e}")


def _retry_claude_installation(npm_path: str, user_npm_dir: Path, expected_binary: Path) -> bool:
    """Retry Claude CLI installation after validation failure.

    Handles both permission issues and corrupted binaries by doing a clean reinstall.
    Only retries ONCE - no loops.

    Args:
        npm_path: Path to npm executable
        user_npm_dir: User's npm global directory
        expected_binary: Expected location of claude binary

    Returns:
        True if retry succeeded and validation passed, False otherwise
    """
    # Import here to avoid circular dependency
    from .prerequisites import safe_subprocess_call

    print("   Binary validation failed - attempting recovery...")

    # Remove the failed binary (clean slate)
    _remove_failed_binary(expected_binary)

    # Retry installation
    print("   Reinstalling Claude CLI...")
    returncode, stdout, stderr = safe_subprocess_call(
        [
            npm_path,
            "install",
            "-g",
            "--prefix",
            str(user_npm_dir),
            "@anthropic-ai/claude-code",
            "--ignore-scripts",
        ],
        context="reinstalling Claude CLI after validation failure",
        timeout=120,
    )

    if returncode != 0:
        print(f"   Reinstallation failed: {stderr}")
        return False

    # Check if binary was created
    if not expected_binary.exists():
        print(f"   Binary not created after reinstall: {expected_binary}")
        return False

    # Validate the reinstalled binary
    if _validate_claude_binary(str(expected_binary)):
        print("   ✓ Recovery successful - binary validated")
        return True
    print("   Recovery failed - binary still invalid after reinstall")
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
    _configure_user_local_npm()
    user_npm_bin = Path.home() / ".npm-global" / "bin"

    print("Installing Claude CLI via npm (user-local)...")
    print(f"Target directory: {user_npm_bin}")
    print("Running: npm install -g @anthropic-ai/claude-code --ignore-scripts")

    # Import here to avoid circular dependency
    from .prerequisites import safe_subprocess_call

    try:
        # Use --ignore-scripts for supply chain security
        # Install to user-local directory using --prefix flag (overrides any npm config)
        user_npm_dir = Path.home() / ".npm-global"
        returncode, stdout, stderr = safe_subprocess_call(
            [
                npm_path,
                "install",
                "-g",
                "--prefix",
                str(user_npm_dir),
                "@anthropic-ai/claude-code",
                "--ignore-scripts",
            ],
            context="installing Claude CLI via npm",
            timeout=120,  # 2 minutes for npm install
        )

        if returncode == 0:
            # Verify binary is at expected location (where we told npm to install it)
            expected_binary = user_npm_bin / "claude"

            if not expected_binary.exists():
                # Binary not where expected - check actual npm prefix
                print(f"❌ Binary not found at expected location: {expected_binary}")
                try:
                    prefix_returncode, prefix_stdout, prefix_stderr = safe_subprocess_call(
                        [npm_path, "config", "get", "prefix"],
                        context="checking npm prefix configuration",
                        timeout=5,
                    )
                    if prefix_returncode == 0:
                        actual_prefix = prefix_stdout.strip()
                        print(f"Actual npm prefix: {actual_prefix}")
                        print(f"Expected: {user_npm_dir}")
                    else:
                        print(f"Could not determine npm prefix: {prefix_stderr}")
                except Exception as e:
                    print(f"Could not determine actual npm prefix: {type(e).__name__}: {e!s}")

                print("\nManual installation:")
                _print_manual_install_instructions()
                return False

            # Validate the binary (ensures it actually works)
            # Recovery: Single retry if validation fails (handles both permissions and corruption)
            if not _validate_claude_binary(str(expected_binary)):
                if _retry_claude_installation(npm_path, user_npm_dir, expected_binary):
                    pass  # Continue to success message below
                else:
                    # Recovery failed - provide manual instructions
                    print("\n⚠️  Automatic recovery failed. Please install manually:")
                    print("   npm install -g @anthropics/claude-code")
                    print("   Or download from: https://github.com/anthropics/claude-code")
                    return False

            print("✅ Claude CLI installed and validated successfully")
            print(f"Binary location: {expected_binary}")

            # Auto-update shell profile so PATH persists across sessions
            if _update_shell_profile_path():
                print("\n✅ Shell profile updated. Restart your shell or run:")
                print('  source ~/.bashrc  # or source ~/.zshrc')
            else:
                # Fallback to manual instructions if auto-update fails
                print("\n💡 Add to your shell profile for future sessions:")
                print('  export PATH="$HOME/.npm-global/bin:$PATH"')

            return True

        # Sanitized error - details logged, not exposed to user
        print("❌ Claude CLI installation failed")
        print("Check npm configuration and permissions")
        if stderr:
            print(f"Error details: {stderr}")
        print("\nManual installation:")
        _print_manual_install_instructions()
        return False

    except subprocess.TimeoutExpired as e:
        print("❌ Claude CLI installation timed out after 120 seconds")
        print(f"Command: {' '.join(e.cmd) if hasattr(e, 'cmd') else 'npm install'}")
        print("Try manually:")
        _print_manual_install_instructions()
        return False
    except Exception as e:
        print(f"❌ Unexpected error installing Claude CLI: {type(e).__name__}")
        print(f"Error: {e!s}")
        print("Try manually:")
        _print_manual_install_instructions()
        return False


def get_claude_cli_path(auto_install: bool = True) -> str | None:
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
        # Auto-install is enabled by default
        # Can be explicitly disabled with AMPLIHACK_AUTO_INSTALL=0
        auto_install_disabled = os.getenv("AMPLIHACK_AUTO_INSTALL", "").lower() in (
            "0",
            "false",
            "no",
        )

        if auto_install_disabled:
            print("\n⚠️  Claude CLI not found")
            print("Auto-installation disabled via AMPLIHACK_AUTO_INSTALL=0")
            print("\nTo install manually:")
            _print_manual_install_instructions()
            return None

        print("Claude CLI not found. Auto-installing...")
        if _install_claude_cli():
            # Installation succeeded - return the expected binary path
            # We already validated it in _install_claude_cli(), so no need to check again
            user_npm_bin = Path.home() / ".npm-global" / "bin"
            expected_binary = user_npm_bin / "claude"
            return str(expected_binary)

    # Installation failed or auto-install disabled - print manual instructions only once
    print("\n⚠️  Claude CLI installation failed or not found")
    print("Please install manually:")
    _print_manual_install_instructions()

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
