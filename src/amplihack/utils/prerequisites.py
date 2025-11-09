"""Prerequisite checking and installation guidance.

This module provides comprehensive prerequisite checking for all required tools
(Node.js, npm, uv, git, claude) with platform-specific installation guidance.

Philosophy:
- Check prerequisites early and fail fast with helpful guidance
- Provide platform-specific installation commands
- Never auto-install (user control and security)
- Standard library only (no dependencies)
- Safe subprocess error handling throughout

Public API:
    PrerequisiteChecker: Main class for checking prerequisites
    safe_subprocess_call: Safe wrapper for all subprocess operations
    Platform: Enum of supported platforms
    PrerequisiteResult: Results of prerequisite checking
    ToolCheckResult: Results of individual tool checking
"""

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Lazy import to avoid circular dependencies
# claude_cli imports prerequisites, so we import it only when needed
try:
    from .claude_cli import get_claude_cli_path
except ImportError:
    # Fallback if import fails
    def get_claude_cli_path(auto_install: bool = True) -> Optional[str]:
        return None


class Platform(Enum):
    """Supported platforms for prerequisite checking."""

    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


@dataclass
class ToolCheckResult:
    """Result of checking a single tool prerequisite."""

    tool: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PrerequisiteResult:
    """Result of checking all prerequisites."""

    all_available: bool
    missing_tools: List[ToolCheckResult] = field(default_factory=list)
    available_tools: List[ToolCheckResult] = field(default_factory=list)


def safe_subprocess_call(
    cmd: List[str],
    context: str,
    timeout: Optional[int] = 30,
) -> Tuple[int, str, str]:
    """Safely execute subprocess with comprehensive error handling.

    This wrapper ensures all subprocess calls have consistent error handling
    and provide helpful context to users when commands fail.

    Args:
        cmd: Command and arguments to execute
        context: Human-readable context for what this command does
        timeout: Timeout in seconds (default 30)

    Returns:
        Tuple of (returncode, stdout, stderr)
        On error, returncode is non-zero and stderr contains helpful message

    Example:
        >>> returncode, out, err = safe_subprocess_call(
        ...     ["git", "--version"],
        ...     context="checking git version"
        ... )
        >>> if returncode != 0:
        ...     print(f"Error: {err}")
    """
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    except FileNotFoundError:
        # Command not found - most common error
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command not found: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please ensure the tool is installed and in your PATH."
        return 127, "", error_msg

    except PermissionError:
        # Permission denied
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Permission denied: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please check file permissions or run with appropriate privileges."
        return 126, "", error_msg

    except subprocess.TimeoutExpired:
        # Command timed out
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command timed out after {timeout}s: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "The operation took too long to complete."
        return 124, "", error_msg

    except OSError as e:
        # Generic OS error
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"OS error running {cmd_name}: {e!s}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg

    except Exception as e:
        # Catch-all for unexpected errors
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Unexpected error running {cmd_name}: {e!s}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg


class PrerequisiteChecker:
    """Check for required prerequisites and provide installation guidance.

    This class detects the platform and checks for all required tools,
    providing platform-specific installation commands when tools are missing.

    Required tools:
        - Node.js (for claude-trace)
        - npm (for installing claude-trace)
        - uv (for Python package management)
        - git (for repository operations)

    Example:
        >>> checker = PrerequisiteChecker()
        >>> result = checker.check_all_prerequisites()
        >>> if not result.all_available:
        ...     print(checker.format_missing_prerequisites(result.missing_tools))
    """

    # Required tools with their version check arguments
    # Note: Claude CLI is checked separately with auto-installation support
    REQUIRED_TOOLS = {
        "node": "--version",
        "npm": "--version",
        "uv": "--version",
        "git": "--version",
    }

    # Installation commands by platform and tool
    INSTALL_COMMANDS = {
        Platform.MACOS: {
            "node": "brew install node",
            "npm": "brew install node  # npm comes with Node.js",
            "uv": "brew install uv",
            "git": "brew install git",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.LINUX: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs\n# Arch:\nsudo pacman -S nodejs",
            "npm": "# Ubuntu/Debian:\nsudo apt install npm\n# Fedora/RHEL:\nsudo dnf install npm\n# Arch:\nsudo pacman -S npm",
            "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "git": "# Ubuntu/Debian:\nsudo apt install git\n# Fedora/RHEL:\nsudo dnf install git\n# Arch:\nsudo pacman -S git",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.WSL: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs",
            "npm": "# Ubuntu/Debian:\nsudo apt install npm\n# Fedora/RHEL:\nsudo dnf install npm",
            "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "git": "sudo apt install git  # or your WSL distro's package manager",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.WINDOWS: {
            "node": "winget install OpenJS.NodeJS\n# Or: choco install nodejs",
            "npm": "winget install OpenJS.NodeJS  # npm comes with Node.js\n# Or: choco install nodejs",
            "uv": 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"',
            "git": "winget install Git.Git\n# Or: choco install git",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.UNKNOWN: {
            "node": "Please install Node.js from https://nodejs.org/",
            "npm": "Please install npm (usually comes with Node.js)",
            "uv": "Please install uv from https://docs.astral.sh/uv/",
            "git": "Please install git from https://git-scm.com/",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
    }

    # Documentation links
    DOCUMENTATION_LINKS = {
        "node": "https://nodejs.org/",
        "npm": "https://www.npmjs.com/",
        "uv": "https://docs.astral.sh/uv/",
        "git": "https://git-scm.com/",
        "claude": "https://docs.claude.com/en/docs/claude-code/setup",
    }

    def __init__(self):
        """Initialize prerequisite checker and detect platform."""
        self.platform = self._detect_platform()

    def _detect_platform(self) -> Platform:
        """Detect the current platform.

        Returns:
            Platform enum value
        """
        system = platform.system()

        if system == "Darwin":
            return Platform.MACOS
        if system == "Linux":
            # Check if running under WSL
            if self._is_wsl():
                return Platform.WSL
            return Platform.LINUX
        if system == "Windows":
            return Platform.WINDOWS
        return Platform.UNKNOWN

    def _is_wsl(self) -> bool:
        """Check if running under Windows Subsystem for Linux.

        Reads /proc/version to detect WSL environment by looking for 'microsoft' string.

        Returns:
            True if running under WSL, False otherwise
        """
        try:
            proc_version = Path("/proc/version")
            if proc_version.exists():
                content = proc_version.read_text().lower()
                return "microsoft" in content
        except (OSError, PermissionError):
            pass
        return False

    def check_tool(self, tool: str, version_arg: Optional[str] = None) -> ToolCheckResult:
        """Check if a single tool is available.

        Args:
            tool: Name of the tool to check
            version_arg: Argument to get version (e.g., "--version")

        Returns:
            ToolCheckResult with availability and details
        """
        # Check if tool exists in PATH
        tool_path = shutil.which(tool)

        if not tool_path:
            return ToolCheckResult(
                tool=tool,
                available=False,
                error=f"{tool} not found in PATH",
            )

        # Tool found - optionally check version
        version = None
        if version_arg:
            returncode, stdout, stderr = safe_subprocess_call(
                [tool, version_arg],
                context=f"checking {tool} version",
                timeout=5,
            )
            if returncode == 0:
                # Extract version from output (usually first line)
                version = stdout.strip().split("\n")[0] if stdout else None

        return ToolCheckResult(
            tool=tool,
            available=True,
            path=tool_path,
            version=version,
        )

    def check_all_prerequisites(self) -> PrerequisiteResult:
        """Check all required prerequisites including Claude CLI with auto-install.

        Returns:
            PrerequisiteResult with complete status
        """
        missing_tools = []
        available_tools = []

        # Check standard required tools
        for tool, version_arg in self.REQUIRED_TOOLS.items():
            result = self.check_tool(tool, version_arg)

            if result.available:
                available_tools.append(result)
            else:
                missing_tools.append(result)

        # Special handling for Claude CLI with auto-installation support
        claude_path = get_claude_cli_path(auto_install=True)

        if claude_path:
            # Claude CLI is available (found or auto-installed)
            # Get version using safe_subprocess_call
            returncode, stdout, stderr = safe_subprocess_call(
                [claude_path, "--version"],
                context="checking claude version",
                timeout=5,
            )
            version = stdout.strip().split("\n")[0] if returncode == 0 and stdout else None

            available_tools.append(
                ToolCheckResult(
                    tool="claude",
                    available=True,
                    path=claude_path,
                    version=version,
                )
            )
        else:
            # Claude CLI not available (detection failed or auto-install failed)
            error_msg = "Not found in common locations and auto-installation failed. Install manually: npm install -g @anthropic-ai/claude-code"

            missing_tools.append(
                ToolCheckResult(
                    tool="claude",
                    available=False,
                    error=error_msg,
                )
            )

        return PrerequisiteResult(
            all_available=len(missing_tools) == 0,
            missing_tools=missing_tools,
            available_tools=available_tools,
        )

    def get_install_command(self, tool: str) -> str:
        """Get platform-specific installation command for a tool.

        Args:
            tool: Name of the tool

        Returns:
            Installation command string
        """
        platform_commands = self.INSTALL_COMMANDS.get(
            self.platform, self.INSTALL_COMMANDS[Platform.UNKNOWN]
        )
        return platform_commands.get(tool, f"Please install {tool} manually")

    def format_missing_prerequisites(self, missing_tools: List[ToolCheckResult]) -> str:
        """Format a user-friendly message for missing prerequisites.

        Args:
            missing_tools: List of missing tool results

        Returns:
            Formatted error message with installation instructions
        """
        if not missing_tools:
            return ""

        lines = []
        lines.append("=" * 70)
        lines.append("MISSING PREREQUISITES")
        lines.append("=" * 70)
        lines.append("")
        lines.append("The following required tools are not installed:")
        lines.append("")

        for result in missing_tools:
            lines.append(f"  ✗ {result.tool}")
            if result.error:
                lines.append(f"    Error: {result.error}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("INSTALLATION INSTRUCTIONS")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Platform detected: {self.platform.value}")
        lines.append("")

        for result in missing_tools:
            tool = result.tool
            lines.append(f"To install {tool}:")
            lines.append("")
            install_cmd = self.get_install_command(tool)
            # Indent multi-line commands
            for cmd_line in install_cmd.split("\n"):
                lines.append(f"  {cmd_line}")
            lines.append("")

            # Add documentation link
            if tool in self.DOCUMENTATION_LINKS:
                lines.append(f"  Documentation: {self.DOCUMENTATION_LINKS[tool]}")
                lines.append("")

        lines.append("=" * 70)
        lines.append("")
        lines.append("After installing the missing tools, please run this command again.")
        lines.append("")

        return "\n".join(lines)

    def check_and_report(self) -> bool:
        """Check prerequisites and print report if any are missing.

        Returns:
            True if all prerequisites available, False otherwise

        Side Effects:
            Prints detailed report to stdout if prerequisites are missing
        """
        result = self.check_all_prerequisites()

        if result.all_available:
            return True

        # Print detailed report
        print(self.format_missing_prerequisites(result.missing_tools))
        return False


# Convenience function for quick prerequisite checking
def check_prerequisites() -> bool:
    """Quick prerequisite check with automatic reporting.

    Returns:
        True if all prerequisites available, False otherwise

    Side Effects:
        Prints detailed report to stdout if prerequisites are missing

    Example:
        >>> if not check_prerequisites():
        ...     sys.exit(1)
    """
    checker = PrerequisiteChecker()
    return checker.check_and_report()


__all__ = [
    "Platform",
    "PrerequisiteChecker",
    "PrerequisiteResult",
    "ToolCheckResult",
    "check_prerequisites",
    "safe_subprocess_call",
]
