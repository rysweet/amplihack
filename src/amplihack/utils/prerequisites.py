"""Prerequisite checking and installation guidance.

This module provides comprehensive prerequisite checking for all required tools
(Node.js, npm, uv, git, claude) with platform-specific installation guidance.

Philosophy:
- Check prerequisites early and fail fast with helpful guidance
- Provide platform-specific installation commands
- Interactive installation with user approval
- Standard library only (no dependencies)
- Safe subprocess error handling throughout
- Security: No shell=True, hardcoded commands only, audit logging

Public API:
    PrerequisiteChecker: Main class for checking prerequisites
    InteractiveInstaller: Class for handling interactive installations
    safe_subprocess_call: Safe wrapper for all subprocess operations
    Platform: Enum of supported platforms
    PrerequisiteResult: Results of prerequisite checking
    ToolCheckResult: Results of individual tool checking
    InstallationResult: Results of installation attempts
    InstallationAuditEntry: Audit log entries for installations
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# Lazy import to avoid circular dependencies
# claude_cli imports prerequisites, so we import it only when needed
try:
    from .claude_cli import get_claude_cli_path
except ImportError:
    # Fallback if import fails
    def get_claude_cli_path(auto_install: bool = True) -> str | None:
        return None


class Platform(Enum):
    """Supported platforms for prerequisite checking."""

    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


@dataclass
class InstallationResult:
    """Result of an installation attempt.

    Attributes:
        tool: Name of the tool being installed
        success: Whether installation succeeded
        command_executed: The command that was executed (as list)
        stdout: Standard output from the command
        stderr: Standard error from the command
        exit_code: Process exit code
        timestamp: ISO 8601 timestamp of installation attempt
        user_approved: Whether user approved the installation
    """

    tool: str
    success: bool
    command_executed: list[str]
    stdout: str
    stderr: str
    exit_code: int
    timestamp: str
    user_approved: bool


@dataclass
class InstallationAuditEntry:
    """Audit log entry for installation attempts.

    Records all installation attempts for security and debugging.
    Logged to .claude/runtime/logs/installation_audit.jsonl
    """

    timestamp: str
    tool: str
    platform: str
    command: list[str]
    user_approved: bool
    success: bool
    exit_code: int
    error_message: str | None = None


@dataclass
class ToolCheckResult:
    """Result of checking a single tool prerequisite."""

    tool: str
    available: bool
    path: str | None = None
    version: str | None = None
    error: str | None = None


@dataclass
class PrerequisiteResult:
    """Result of checking all prerequisites."""

    all_available: bool
    missing_tools: list[ToolCheckResult] = field(default_factory=list)
    available_tools: list[ToolCheckResult] = field(default_factory=list)


@dataclass
class InstallationResult:
    """Result of attempting to install a tool."""

    tool: str
    success: bool
    message: str
    command_used: str | None = None
    verification_result: ToolCheckResult | None = None


def safe_subprocess_call(
    cmd: list[str],
    context: str,
    timeout: int | None = 30,
) -> tuple[int, str, str]:
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


class InteractiveInstaller:
    """Handle interactive installation of missing tools with user approval.

    Security features:
    - No shell=True (prevents shell injection)
    - Hardcoded commands only (from INSTALL_COMMANDS)
    - User approval required for every installation
    - Audit logging of all attempts
    - TTY check for interactive mode

    Example:
        >>> installer = InteractiveInstaller(Platform.MACOS)
        >>> result = installer.install_tool("node")
        >>> if result.success:
        ...     print("Node.js installed successfully")
    """

    def __init__(self, platform: Platform):
        """Initialize interactive installer for a platform.

        Args:
            platform: Target platform for installation
        """
        self.platform = platform
        self.audit_log_path = (
            Path.home() / ".claude" / "runtime" / "logs" / "installation_audit.jsonl"
        )

    def is_interactive_environment(self) -> bool:
        """Check if running in an interactive environment.

        Returns:
            True if interactive (has TTY and not in CI), False otherwise
        """
        # Check if stdin is a TTY
        if not sys.stdin.isatty():
            return False

        # Check common CI environment variables
        ci_vars = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_HOME"]
        if any(os.environ.get(var) for var in ci_vars):
            return False

        return True

    def prompt_for_approval(self, tool: str, command: list[str]) -> bool:
        """Prompt user for approval to install a tool.

        Args:
            tool: Name of the tool to install
            command: Command that will be executed

        Returns:
            True if user approves, False otherwise
        """
        print(f"\n{'=' * 70}")
        print(f"INSTALL {tool.upper()}")
        print(f"{'=' * 70}")
        print(f"\nThe following command will be executed to install {tool}:")
        print(f"\n  {' '.join(command)}")
        print("\nThis command may:")
        print("  - Require sudo password for system-level installation")
        print("  - Install dependencies automatically")
        print("  - Modify system packages or configuration")
        print(f"\n{'=' * 70}\n")

        while True:
            response = (
                input(f"Do you want to proceed with installing {tool}? [y/N]: ").strip().lower()
            )
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no", ""]:
                return False
            print("Please enter 'y' or 'n'")

    def _execute_install_command(self, command: list[str]) -> subprocess.CompletedProcess:
        """Execute installation command with interactive stdin.

        Args:
            command: Command to execute as List[str]

        Returns:
            subprocess.CompletedProcess result

        Security:
            - No shell=True (prevents shell injection)
            - stdin=sys.stdin (allows password prompts)
            - List[str] command (no string interpolation)
        """
        return subprocess.run(
            command,
            stdin=sys.stdin,  # Allow interactive password prompts
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,  # Don't raise exception, handle errors explicitly
        )

    def _log_audit(self, entry: InstallationAuditEntry) -> None:
        """Log installation attempt to audit log.

        Args:
            entry: Audit entry to log

        Note:
            Silently handles I/O errors to avoid breaking installation workflow
        """
        try:
            # Ensure log directory exists
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

            # Append entry as JSONL
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except (OSError, PermissionError):
            # Silently ignore logging errors - don't break installation
            # User can still see installation results in terminal output
            pass

    def install_tool(self, tool: str) -> InstallationResult:
        """Install a tool interactively with user approval.

        Args:
            tool: Name of the tool to install

        Returns:
            InstallationResult with complete installation details

        Workflow:
            1. Check if interactive environment
            2. Get installation command for platform
            3. Prompt user for approval
            4. Execute command with interactive stdin
            5. Log attempt to audit log
            6. Return result
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Check for interactive environment
        if not self.is_interactive_environment():
            return InstallationResult(
                tool=tool,
                success=False,
                command_executed=[],
                stdout="",
                stderr="Non-interactive environment detected. Cannot prompt for installation.",
                exit_code=-1,
                timestamp=timestamp,
                user_approved=False,
            )

        # Get installation command for platform
        platform_commands = PrerequisiteChecker.INSTALL_COMMANDS.get(self.platform, {})
        command = platform_commands.get(tool)

        if not command:
            error_msg = f"No installation command available for {tool} on {self.platform.value}"
            return InstallationResult(
                tool=tool,
                success=False,
                command_executed=[],
                stdout="",
                stderr=error_msg,
                exit_code=-1,
                timestamp=timestamp,
                user_approved=False,
            )

        # Prompt for approval
        user_approved = self.prompt_for_approval(tool, command)

        if not user_approved:
            audit_entry = InstallationAuditEntry(
                timestamp=timestamp,
                tool=tool,
                platform=self.platform.value,
                command=command,
                user_approved=False,
                success=False,
                exit_code=-1,
                error_message="User declined installation",
            )
            self._log_audit(audit_entry)

            return InstallationResult(
                tool=tool,
                success=False,
                command_executed=command,
                stdout="",
                stderr="User declined installation",
                exit_code=-1,
                timestamp=timestamp,
                user_approved=False,
            )

        # Execute installation command
        print(f"\nInstalling {tool}...")
        try:
            result = self._execute_install_command(command)

            success = result.returncode == 0

            # Log audit entry
            audit_entry = InstallationAuditEntry(
                timestamp=timestamp,
                tool=tool,
                platform=self.platform.value,
                command=command,
                user_approved=True,
                success=success,
                exit_code=result.returncode,
                error_message=result.stderr if not success else None,
            )
            self._log_audit(audit_entry)

            return InstallationResult(
                tool=tool,
                success=success,
                command_executed=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                timestamp=timestamp,
                user_approved=True,
            )

        except Exception as e:
            error_msg = f"Unexpected error during installation: {e!s}"

            audit_entry = InstallationAuditEntry(
                timestamp=timestamp,
                tool=tool,
                platform=self.platform.value,
                command=command,
                user_approved=True,
                success=False,
                exit_code=-1,
                error_message=error_msg,
            )
            self._log_audit(audit_entry)

            return InstallationResult(
                tool=tool,
                success=False,
                command_executed=command,
                stdout="",
                stderr=error_msg,
                exit_code=-1,
                timestamp=timestamp,
                user_approved=True,
            )


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
        "rg": "--version",  # ripgrep - required for custom slash commands
    }

    # Installation commands by platform and tool
    # String format for display (may contain multiple options)
    INSTALL_COMMANDS_DISPLAY = {
        Platform.MACOS: {
            "node": "brew install node",
            "npm": "brew install node  # npm comes with Node.js",
            "uv": "brew install uv",
            "git": "brew install git",
            "rg": "brew install ripgrep",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.LINUX: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs\n# Arch:\nsudo pacman -S nodejs",
            "npm": "# Ubuntu/Debian:\nsudo apt install npm\n# Fedora/RHEL:\nsudo dnf install npm\n# Arch:\nsudo pacman -S npm",
            "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "git": "# Ubuntu/Debian:\nsudo apt install git\n# Fedora/RHEL:\nsudo dnf install git\n# Arch:\nsudo pacman -S git",
            "rg": "# Ubuntu/Debian:\nsudo apt install ripgrep\n# Fedora/RHEL:\nsudo dnf install ripgrep\n# Arch:\nsudo pacman -S ripgrep",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.WSL: {
            "node": "# Ubuntu/Debian:\nsudo apt install nodejs\n# Fedora/RHEL:\nsudo dnf install nodejs",
            "npm": "# Ubuntu/Debian:\nsudo apt install npm\n# Fedora/RHEL:\nsudo dnf install npm",
            "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "git": "sudo apt install git  # or your WSL distro's package manager",
            "rg": "sudo apt install ripgrep",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.WINDOWS: {
            "node": "winget install OpenJS.NodeJS\n# Or: choco install nodejs",
            "npm": "winget install OpenJS.NodeJS  # npm comes with Node.js\n# Or: choco install nodejs",
            "uv": 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"',
            "git": "winget install Git.Git\n# Or: choco install git",
            "rg": "winget install BurntSushi.ripgrep.MSVC\n# Or: choco install ripgrep",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
        Platform.UNKNOWN: {
            "node": "Please install Node.js from https://nodejs.org/",
            "npm": "Please install npm (usually comes with Node.js)",
            "uv": "Please install uv from https://docs.astral.sh/uv/",
            "git": "Please install git from https://git-scm.com/",
            "rg": "Please install ripgrep from https://github.com/BurntSushi/ripgrep",
            "claude": "npm install -g @anthropic-ai/claude-code",
        },
    }

    # Actual executable commands (List[str] for security)
    # These are the commands that will be executed interactively
    INSTALL_COMMANDS = {
        Platform.MACOS: {
            "node": ["brew", "install", "node"],
            "npm": ["brew", "install", "node"],  # npm comes with node
            "uv": ["brew", "install", "uv"],
            "git": ["brew", "install", "git"],
            "rg": ["brew", "install", "ripgrep"],
            "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        },
        Platform.LINUX: {
            "node": ["sudo", "apt", "install", "-y", "nodejs"],  # Default to apt
            "npm": ["sudo", "apt", "install", "-y", "npm"],
            "uv": ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "git": ["sudo", "apt", "install", "-y", "git"],
            "rg": ["sudo", "apt", "install", "-y", "ripgrep"],
            "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        },
        Platform.WSL: {
            "node": ["sudo", "apt", "install", "-y", "nodejs"],
            "npm": ["sudo", "apt", "install", "-y", "npm"],
            "uv": ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            "git": ["sudo", "apt", "install", "-y", "git"],
            "rg": ["sudo", "apt", "install", "-y", "ripgrep"],
            "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        },
        Platform.WINDOWS: {
            "node": ["winget", "install", "OpenJS.NodeJS"],
            "npm": ["winget", "install", "OpenJS.NodeJS"],  # npm comes with node
            "uv": ["powershell", "-c", "irm https://astral.sh/uv/install.ps1 | iex"],
            "git": ["winget", "install", "Git.Git"],
            "rg": ["winget", "install", "BurntSushi.ripgrep.MSVC"],
            "claude": ["npm", "install", "-g", "@anthropic-ai/claude-code"],
        },
        Platform.UNKNOWN: {},  # No automatic commands for unknown platforms
    }

    # Documentation links
    DOCUMENTATION_LINKS = {
        "node": "https://nodejs.org/",
        "npm": "https://www.npmjs.com/",
        "uv": "https://docs.astral.sh/uv/",
        "git": "https://git-scm.com/",
        "rg": "https://github.com/BurntSushi/ripgrep",
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

    def check_tool(self, tool: str, version_arg: str | None = None) -> ToolCheckResult:
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
        """Get platform-specific installation command for a tool (display format).

        Args:
            tool: Name of the tool

        Returns:
            Installation command string for display
        """
        platform_commands = self.INSTALL_COMMANDS_DISPLAY.get(
            self.platform, self.INSTALL_COMMANDS_DISPLAY[Platform.UNKNOWN]
        )
        return platform_commands.get(tool, f"Please install {tool} manually")

    def format_missing_prerequisites(self, missing_tools: list[ToolCheckResult]) -> str:
        """Format a user-friendly message for missing prerequisites.

        Args:
            missing_tools: List of missing tool results

        Returns:
            Formatted error message with installation instructions
        """
        if not missing_tools:
            return ""

        lines = []
        lines.append("\nMissing Prerequisites")
        lines.append("-" * 50)
        lines.append(f"\nPlatform: {self.platform.value}")
        lines.append("\nRequired tools not installed:")

        for result in missing_tools:
            lines.append(f"  - {result.tool}")

        lines.append("\nInstallation commands:")

        for result in missing_tools:
            tool = result.tool
            install_cmd = self.get_install_command(tool)
            lines.append(f"\n{tool}:")
            # Indent multi-line commands
            for cmd_line in install_cmd.split("\n"):
                lines.append(f"  {cmd_line}")

            # Add documentation link
            if tool in self.DOCUMENTATION_LINKS:
                lines.append(f"  Docs: {self.DOCUMENTATION_LINKS[tool]}")

        lines.append("\nAfter installing, run this command again.\n")

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

    def check_and_install(self, interactive: bool = True) -> PrerequisiteResult:
        """Check prerequisites and optionally install missing ones interactively.

        This method combines prerequisite checking with interactive installation.
        For each missing tool, it prompts the user for approval before installing.

        Args:
            interactive: If True, prompt user to install missing tools.
                        If False, just return missing tools (same as check_all_prerequisites)

        Returns:
            PrerequisiteResult with current status after any installations

        Side Effects:
            - May install system packages with user approval
            - Logs all installation attempts to audit log
            - Prints status messages during installation

        Example:
            >>> checker = PrerequisiteChecker()
            >>> result = checker.check_and_install(interactive=True)
            >>> if result.all_available:
            ...     print("All prerequisites now available")
        """
        # First check what's missing
        result = self.check_all_prerequisites()

        if result.all_available:
            print("All prerequisites are already available.")
            return result

        if not interactive:
            # Non-interactive mode - just return missing tools
            return result

        # Interactive mode - attempt to install missing tools
        print(f"\n{'=' * 70}")
        print("MISSING PREREQUISITES DETECTED")
        print(f"{'=' * 70}\n")
        print(f"Found {len(result.missing_tools)} missing tool(s):")
        for tool_result in result.missing_tools:
            print(f"  - {tool_result.tool}")
        print(f"\n{'=' * 70}\n")

        # Create installer for this platform
        installer = InteractiveInstaller(self.platform)

        # Check if we're in an interactive environment
        if not installer.is_interactive_environment():
            print("Non-interactive environment detected.")
            print("Cannot prompt for installation. Please install manually:")
            print(self.format_missing_prerequisites(result.missing_tools))
            return result

        # Attempt to install each missing tool
        installation_results: dict[str, InstallationResult] = {}
        for tool_result in result.missing_tools:
            tool = tool_result.tool
            install_result = installer.install_tool(tool)
            installation_results[tool] = install_result

            if install_result.success:
                print(f"\n[SUCCESS] {tool} installed successfully")
            elif not install_result.user_approved:
                print(f"\n[SKIPPED] {tool} installation declined by user")
            else:
                print(f"\n[FAILED] {tool} installation failed")
                if install_result.stderr:
                    print(f"Error: {install_result.stderr}")

        # Re-check prerequisites after installations
        print(f"\n{'=' * 70}")
        print("VERIFYING INSTALLATIONS")
        print(f"{'=' * 70}\n")

        final_result = self.check_all_prerequisites()

        if final_result.all_available:
            print("[SUCCESS] All prerequisites are now available!")
        else:
            print(f"[WARNING] {len(final_result.missing_tools)} tool(s) still missing:")
            for tool_result in final_result.missing_tools:
                print(f"  - {tool_result.tool}")
            print("\nYou may need to:")
            print("  1. Restart your terminal to refresh PATH")
            print("  2. Install manually (see commands above)")
            print("  3. Check installation logs for errors")

        return final_result


# Convenience function for quick prerequisite checking
def check_prerequisites() -> bool:
    """Quick prerequisite check with automatic interactive installation.

    In interactive environments (TTY), prompts user to install missing tools.
    In non-interactive environments (CI), prints manual instructions.

    Returns:
        True if all prerequisites available, False otherwise

    Side Effects:
        - In interactive mode: Prompts for user approval and installs missing tools
        - In non-interactive mode: Prints manual installation instructions
        - All installation attempts are logged to ~/.amplihack/installation_audit.json

    Example:
        >>> if not check_prerequisites():
        ...     sys.exit(1)
    """
    checker = PrerequisiteChecker()
    result = checker.check_and_install(interactive=True)
    return result.all_available


__all__ = [
    "Platform",
    "PrerequisiteChecker",
    "InteractiveInstaller",
    "PrerequisiteResult",
    "ToolCheckResult",
    "InstallationResult",
    "InstallationAuditEntry",
    "check_prerequisites",
    "safe_subprocess_call",
]
