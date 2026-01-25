"""Platform compatibility checking for amplihack.

Detects native Windows (not WSL) and provides helpful guidance.

Philosophy:
- Ruthless simplicity: Direct platform.system() check
- Zero-BS: Real working detection, no stubs
- Clear error messages: Actionable guidance for users

Public API (the "studs"):
    check_platform_compatibility: Main entry point
    is_native_windows: Platform detection function
    PlatformCheckResult: Result data class
"""

import platform
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
        ...     print("Please use WSL")
    """
    # Quick check: not Windows at all
    if platform.system() != "Windows":
        return False

    # If /proc/version exists and contains "microsoft", it's WSL
    proc_version = Path("/proc/version")
    if proc_version.exists():
        try:
            content = proc_version.read_text().lower()
            if "microsoft" in content or "wsl" in content:
                return False  # WSL, not native Windows
        except (OSError, PermissionError):
            pass

    # If we get here, it's native Windows
    return True


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

    # Native Windows detection
    if is_native_windows():
        message = """
╔══════════════════════════════════════════════════════════════════════╗
║                    WINDOWS DETECTED                                  ║
╚══════════════════════════════════════════════════════════════════════╝

amplihack requires a Unix-like environment and does not run natively
on Windows. Please use Windows Subsystem for Linux (WSL).

┌─ Install WSL ────────────────────────────────────────────────────────┐
│                                                                       │
│  1. Open PowerShell or Command Prompt as Administrator               │
│  2. Run: wsl --install                                               │
│  3. Restart your computer                                            │
│  4. Open WSL and install amplihack                                   │
│                                                                       │
│  For detailed instructions:                                          │
│  https://learn.microsoft.com/en-us/windows/wsl/install               │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘

After installing WSL, run amplihack from your WSL terminal.
""".strip()

        return PlatformCheckResult(
            compatible=False,
            platform_name="Windows (native)",
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
