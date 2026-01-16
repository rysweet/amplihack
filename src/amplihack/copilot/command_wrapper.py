"""Command invocation wrapper for Copilot CLI.

Philosophy:
- Ruthless simplicity - single function to invoke commands
- Zero-BS - working subprocess calls or doesn't exist
- Fail-fast - clear error messages for missing tools

Public API (the "studs"):
    invoke_copilot_command: Invoke a Copilot CLI command
    CommandResult: Result of command invocation
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class CommandResult:
    """Result of command invocation.

    Attributes:
        success: Whether command succeeded
        returncode: Process return code
        stdout: Standard output
        stderr: Standard error
        command_name: Name of command invoked
    """
    success: bool
    returncode: int
    stdout: str
    stderr: str
    command_name: str


def invoke_copilot_command(
    command_name: str,
    args: Optional[List[str]] = None,
    timeout: int = 300
) -> CommandResult:
    """Invoke a Copilot CLI command.

    Pattern: copilot --allow-all-tools -p "@.github/commands/<cmd>.md <args>"

    Args:
        command_name: Name of command (e.g., "amplihack/ultrathink")
        args: Optional command arguments
        timeout: Command timeout in seconds (default 300)

    Returns:
        CommandResult with execution results

    Raises:
        FileNotFoundError: If copilot CLI not found
        FileNotFoundError: If command file doesn't exist

    Example:
        >>> result = invoke_copilot_command("amplihack/ultrathink", ["analyze this"])
        >>> result.success
        True
    """
    # Validate command exists
    command_path = Path(f".github/commands/{command_name}.md")
    if not command_path.exists():
        raise FileNotFoundError(
            f"Command not found: {command_path}\n"
            f"Fix: Run 'amplihack sync-commands' to convert commands\n"
            f"     Or check command name is correct"
        )

    # Build copilot command
    args_str = " ".join(args) if args else ""
    prompt = f"@.github/commands/{command_name}.md {args_str}".strip()

    cmd = ["copilot", "--allow-all-tools", "-p", prompt]

    try:
        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path.cwd()
        )

        return CommandResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command_name=command_name
        )

    except FileNotFoundError:
        raise FileNotFoundError(
            "Copilot CLI not found\n"
            "Fix: Install GitHub Copilot CLI\n"
            "     npm install -g @githubnext/github-copilot-cli"
        )

    except subprocess.TimeoutExpired:
        return CommandResult(
            success=False,
            returncode=124,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
            command_name=command_name
        )

    except Exception as e:
        return CommandResult(
            success=False,
            returncode=1,
            stdout="",
            stderr=f"Unexpected error: {str(e)}",
            command_name=command_name
        )


def list_available_commands() -> List[str]:
    """List all available Copilot commands.

    Returns:
        List of command names (e.g., ["amplihack/ultrathink", "ddd/1-plan"])

    Example:
        >>> commands = list_available_commands()
        >>> "amplihack/ultrathink" in commands
        True
    """
    commands_dir = Path(".github/commands")

    if not commands_dir.exists():
        return []

    command_files = commands_dir.rglob("*.md")
    commands = []

    for cmd_path in command_files:
        # Get relative path from commands directory
        try:
            relative_path = cmd_path.relative_to(commands_dir)
            # Remove .md extension and convert to command name
            command_name = str(relative_path.with_suffix(''))
            commands.append(command_name)
        except ValueError:
            continue

    return sorted(commands)


__all__ = [
    "invoke_copilot_command",
    "list_available_commands",
    "CommandResult",
]
