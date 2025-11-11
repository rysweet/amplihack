"""RustyClawd detection and integration.

Detects if RustyClawd (Rust implementation of Claude Code) is available
and provides the appropriate binary path.
"""

import shutil
from pathlib import Path
from typing import Optional


def is_rustyclawd_available() -> bool:
    """Check if RustyClawd binary is available.
    
    Returns:
        True if rustyclawd or claude-code (Rust version) is in PATH.
    """
    # Check for rustyclawd binary
    if shutil.which("rustyclawd"):
        return True
    
    # Check for claude-code in RustyClawd installation
    rustyclawd_path = Path.home() / "src" / "declawed" / "claude-code-rs" / "target" / "release" / "claude-code"
    if rustyclawd_path.exists() and rustyclawd_path.is_file():
        return True
    
    return False


def get_rustyclawd_path() -> Optional[Path]:
    """Get path to RustyClawd binary.
    
    Returns:
        Path to RustyClawd binary if available, None otherwise.
    """
    # Try rustyclawd in PATH
    path = shutil.which("rustyclawd")
    if path:
        return Path(path)
    
    # Try claude-code in known RustyClawd location
    rustyclawd_path = Path.home() / "src" / "declawed" / "claude-code-rs" / "target" / "release" / "claude-code"
    if rustyclawd_path.exists():
        return rustyclawd_path
    
    return None


def should_use_rustyclawd() -> bool:
    """Determine if RustyClawd should be used instead of Claude Code.
    
    Checks AMPLIHACK_USE_RUSTYCLAWD environment variable and binary availability.
    
    Returns:
        True if RustyClawd should be used.
    """
    import os
    
    # Check environment variable override
    env_val = os.getenv("AMPLIHACK_USE_RUSTYCLAWD", "").lower()
    if env_val in ("1", "true", "yes"):
        return is_rustyclawd_available()
    elif env_val in ("0", "false", "no"):
        return False
    
    # Auto-detect: Use if available (prefer Rust implementation)
    return is_rustyclawd_available()
