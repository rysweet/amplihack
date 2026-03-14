"""Platform compatibility checking for amplihack.

Detects native Windows (not WSL) and provides helpful guidance.

Philosophy:
- Ruthless simplicity: Direct sys.platform check
- Zero-BS: Real working detection, no stubs
- Clear error messages: Actionable guidance for users

Public API (the "studs"):
    check_platform_compatibility: Main entry point
    is_native_windows: Platform detection function
    PlatformCheckResult: Result data class
"""

import platform
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlatformCheckResult:
    """Result of platform compatibility check.

    Attributes:
        compatible: True if platform is supported
        platform_name: Human-readable platform name
        is_wsl: True if running in WSL
        message: Guidance message (empty if compatible)
    """

    compatible: bool
    platform_name: str
    is_wsl: bool
    message: str = ""


def is_native_windows() -> bool:
    """Detect if running on native Windows (not WSL).

    Returns:
        True if native Windows, False otherwise

    Example:
        >>> if is_native_windows():
        ...     print("Running on native Windows (partial support)")
    """
    # sys.platform is authoritative for the Python interpreter's platform.
    # On WSL, sys.platform == "linux" even though /proc/version contains
    # "microsoft". On native Windows Python, sys.platform == "win32" — even
    # when the host has WSL installed (which makes /proc/version readable
    # via Plan 9 filesystem interop).
    if sys.platform == "win32":
        return True

    # Not Windows at all (Linux, macOS, etc.)
    return False


def check_platform_compatibility() -> PlatformCheckResult:
    """Check if current platform is compatible with amplihack.

    Returns:
        PlatformCheckResult with compatibility status and guidance

    Example:
        >>> result = check_platform_compatibility()
        >>> if not result.compatible:
        ...     print(result.message)
        ...     sys.exit(1)
    """
    system = platform.system()

    # Detect WSL
    is_wsl = False
    if system == "Linux":
        proc_version = Path("/proc/version")
        if proc_version.exists():
            try:
                content = proc_version.read_text().lower()
                if "microsoft" in content or "wsl" in content:
                    is_wsl = True
            except (OSError, PermissionError):
                pass

    # Native Windows — partial support (PR #3127+)
    # Core CLI works; fleet requires tmux/SSH. Memory/kuzu works on x86_64 Python.
    if is_native_windows():
        message = (
            "⚠️  Native Windows detected — running with partial support.\n"
            "   Unavailable features: fleet (requires tmux/SSH).\n"
            "   On ARM64 Windows, use x86_64 Python for memory features (kuzu).\n"
            "   For full support, use WSL: "
            "https://learn.microsoft.com/en-us/windows/wsl/install"
        )

        return PlatformCheckResult(
            compatible=True,
            platform_name="Windows (native, partial)",
            is_wsl=False,
            message=message,
        )

    # macOS, Linux, WSL are all compatible
    platform_names = {
        "Darwin": "macOS",
        "Linux": "Linux (WSL)" if is_wsl else "Linux",
    }

    return PlatformCheckResult(
        compatible=True,
        platform_name=platform_names.get(system, system),
        is_wsl=is_wsl,
        message="",
    )


__all__ = [
    "check_platform_compatibility",
    "is_native_windows",
    "PlatformCheckResult",
]
