"""RustyClawd detection and integration.

Detects if RustyClawd (Rust implementation of Claude Code) is available
and provides the appropriate binary path.
"""

import shutil
from pathlib import Path


def is_rustyclawd_available() -> bool:
    """Check if RustyClawd binary is available.

    Checks in order:
    1. RUSTYCLAWD_PATH environment variable
    2. rustyclawd in system PATH
    3. claude-code (if it's the Rust version)

    Returns:
        True if rustyclawd or claude-code (Rust version) is in PATH.
    """
    import os

    # Check custom path from environment variable
    custom_path = os.getenv("RUSTYCLAWD_PATH")
    if custom_path:
        path = Path(custom_path)
        if path.exists() and path.is_file():
            return True

    # Check for rustyclawd binary in PATH
    if shutil.which("rustyclawd"):
        return True

    # Check for claude-code in PATH (might be Rust version)
    if shutil.which("claude-code"):
        # Could be Rust version - we'll detect at runtime
        return True

    return False


def get_rustyclawd_path() -> Path | None:
    """Get path to RustyClawd binary.

    Checks in order:
    1. RUSTYCLAWD_PATH environment variable
    2. rustyclawd in system PATH
    3. claude-code in system PATH (if available)

    Returns:
        Path to RustyClawd binary if available, None otherwise.
    """
    import os

    # Check custom path from environment variable
    custom_path = os.getenv("RUSTYCLAWD_PATH")
    if custom_path:
        path = Path(custom_path)
        if path.exists() and path.is_file():
            return path

    # Try rustyclawd in PATH
    path = shutil.which("rustyclawd")
    if path:
        return Path(path)

    # Try claude-code in PATH (might be Rust version)
    path = shutil.which("claude-code")
    if path:
        return Path(path)

    return None


def install_rustyclawd() -> bool:
    """Install or update RustyClawd via cargo.

    Returns:
        True if installation successful.
    """
    import subprocess

    print("Installing/updating RustyClawd...")
    try:
        subprocess.run(
            [
                "cargo",
                "install",
                "--git",
                "https://github.com/rysweet/RustyClawd",
                "--bin",
                "rusty",
                "--force",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✅ RustyClawd installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install RustyClawd: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ Cargo not found - install Rust from https://rustup.rs")
        return False


def should_use_rustyclawd() -> bool:
    """Determine if RustyClawd should be used instead of Claude Code.

    Checks AMPLIHACK_USE_RUSTYCLAWD environment variable and binary availability.
    Auto-installs if enabled but not found.

    Returns:
        True if RustyClawd should be used.
    """
    import os

    # Check environment variable override
    env_val = os.getenv("AMPLIHACK_USE_RUSTYCLAWD", "").lower()
    if env_val in ("1", "true", "yes"):
        # Try to use, install if not available
        if is_rustyclawd_available():
            return True
        print("RustyClawd not found, installing...")
        return install_rustyclawd()
    if env_val in ("0", "false", "no"):
        return False

    # Auto-detect: Use if available (prefer Rust implementation)
    return is_rustyclawd_available()
