"""Platform CLI Abstraction Module.

This module provides a unified interface for spawning and managing AI coding assistant
subprocesses across different platforms (Claude Code, GitHub Copilot, Microsoft Amplifier).

Key features:
- Protocol-based abstraction for platform independence
- Subprocess spawning with platform-specific command formatting
- Prompt formatting tailored to persona characteristics
- Platform registration system for extensibility

Philosophy:
- Each platform CLI implementation is self-contained
- Standard library subprocess management (no external dependencies)
- Clear separation between platform concerns and business logic
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Set


# Whitelist of allowed extra_args for security
ALLOWED_EXTRA_ARGS: Set[str] = {
    "--debug",
    "--verbose",
    "-v",
    "--quiet",
    "-q",
    "--help",
    "-h",
    "--version",
    "--no-color",
    "--json",
}


def _validate_working_dir(working_dir: str) -> None:
    """Validate working directory exists and is a directory.

    Args:
        working_dir: Working directory path

    Raises:
        ValueError: If working_dir is invalid or doesn't exist
    """
    if not working_dir:
        raise ValueError("working_dir cannot be empty")

    path = Path(working_dir)

    # Check for path traversal attempts
    if ".." in path.parts:
        raise ValueError(f"Path traversal detected in working_dir: {working_dir}")

    # Verify directory exists
    if not path.exists():
        raise ValueError(f"working_dir does not exist: {working_dir}")

    if not path.is_dir():
        raise ValueError(f"working_dir is not a directory: {working_dir}")


def _validate_extra_args(extra_args: List[str]) -> None:
    """Validate extra arguments against whitelist.

    Args:
        extra_args: List of extra arguments

    Raises:
        ValueError: If any argument is not in the whitelist
    """
    for arg in extra_args:
        if arg not in ALLOWED_EXTRA_ARGS:
            raise ValueError(
                f"Argument '{arg}' is not allowed. "
                f"Allowed arguments: {', '.join(sorted(ALLOWED_EXTRA_ARGS))}"
            )


def _validate_cli_command(command: List[str], timeout: int = 5) -> bool:
    """Validate that a CLI command is available.

    Args:
        command: Command and arguments to check (e.g., ["claude", "--version"])
        timeout: Timeout in seconds for command execution

    Returns:
        True if command is available and runs successfully, False otherwise
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_cli_version(command: List[str], timeout: int = 5) -> str:
    """Get version from CLI command.

    Args:
        command: Command and arguments to get version (e.g., ["claude", "--version"])
        timeout: Timeout in seconds for command execution

    Returns:
        Version string if found, "unknown" otherwise
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            # Parse version from output like "Tool v1.2.3" or "1.2.3"
            match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)
        return "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


class PlatformCLI(Protocol):
    """Protocol defining the interface for platform CLI implementations.

    All platform implementations must provide these methods to ensure
    consistent behavior across different AI coding assistants.
    """

    platform_name: str

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str],
        **kwargs,
    ) -> subprocess.Popen:
        """Spawn subprocess for AI assistant with given parameters.

        Args:
            goal: The task to accomplish
            persona: The persona type (guide, qa_engineer, architect, junior_dev)
            working_dir: Working directory for subprocess
            environment: Environment variables to set
            **kwargs: Platform-specific additional arguments

        Returns:
            subprocess.Popen object for the spawned process
        """
        ...

    def format_prompt(self, goal: str, persona: str, context: str) -> str:
        """Format prompt for the platform based on persona characteristics.

        Args:
            goal: The task goal
            persona: Persona type
            context: Additional context information

        Returns:
            Formatted prompt string
        """
        ...

    def parse_output(self, output: str) -> Dict[str, str]:
        """Parse output from the subprocess.

        Args:
            output: Raw output from subprocess

        Returns:
            Dictionary with parsed output data
        """
        ...

    def validate_installation(self) -> bool:
        """Check if platform CLI is installed and available.

        Returns:
            True if platform is available, False otherwise
        """
        ...

    def get_version(self) -> str:
        """Get version of the installed platform CLI.

        Returns:
            Version string
        """
        ...


class ClaudeCodeCLI:
    """Claude Code platform implementation."""

    platform_name = "claude-code"

    def validate_installation(self) -> bool:
        """Check if claude command is available."""
        return _validate_cli_command(["claude", "--version"])

    def get_version(self) -> str:
        """Get Claude Code version."""
        return _get_cli_version(["claude", "--version"])

    def format_prompt(self, goal: str, persona: str, context: str) -> str:
        """Format prompt for Claude Code with persona-specific styling."""
        persona_styles = {
            "guide": """You are a guide persona helping someone learn and understand.

**Your approach:**
- Teach concepts through explanation and examples
- Ask Socratic questions to deepen understanding
- Provide clear documentation and tutorials
- Break down complex ideas into digestible parts

**Goal:** {goal}

**Context:** {context}

Remember to focus on educational value and ensure the learner understands not just the "how" but the "why".""",
            "qa_engineer": """You are a QA engineer persona focused on comprehensive validation.

**Your approach:**
- Create exhaustive test suites covering all scenarios
- Identify edge cases, error conditions, and security vulnerabilities
- Validate against success criteria with precision
- Document test coverage and results

**Goal:** {goal}

**Context:** {context}

Ensure thorough testing with happy path, error handling, boundary conditions, security, and performance tests.""",
            "architect": """You are an architect persona designing robust systems.

**Your approach:**
- Think holistically about system design and interfaces
- Consider scalability, maintainability, and extensibility
- Create clear architectural documentation and diagrams
- Define module boundaries and contracts

**Goal:** {goal}

**Context:** {context}

Focus on strategic design decisions and long-term system health.""",
            "junior_dev": """You are a junior developer persona focused on implementation.

**Your approach:**
- Follow specifications and requirements closely
- Implement features step-by-step
- Write clean, working code
- Ask questions when requirements are unclear

**Goal:** {goal}

**Context:** {context}

Focus on delivering working code that meets the stated requirements.""",
        }

        template = persona_styles.get(
            persona,
            "**Goal:** {goal}\n\n**Context:** {context}",
        )

        return template.format(goal=goal, context=context or "No additional context provided.")

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str],
        **kwargs,
    ) -> subprocess.Popen:
        """Spawn Claude Code subprocess."""
        # Validate inputs
        _validate_working_dir(working_dir)
        extra_args = kwargs.get("extra_args", [])
        _validate_extra_args(extra_args)

        prompt = self.format_prompt(goal, persona, kwargs.get("context", ""))

        # Build command
        command = ["claude"]

        # Add extra arguments if provided
        command.extend(extra_args)

        # Add the prompt as the last argument
        command.append(prompt)

        # Merge environment variables
        env = os.environ.copy()
        env.update(environment)

        # Spawn subprocess
        process = subprocess.Popen(
            command,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process

    def parse_output(self, output: str) -> Dict[str, str]:
        """Parse Claude Code output."""
        return {
            "stdout": output,
        }


class CopilotCLI:
    """GitHub Copilot CLI platform implementation."""

    platform_name = "copilot"

    def validate_installation(self) -> bool:
        """Check if gh copilot is available."""
        return _validate_cli_command(["gh", "copilot", "--version"])

    def get_version(self) -> str:
        """Get GitHub Copilot version."""
        return _get_cli_version(["gh", "copilot", "--version"])

    def format_prompt(self, goal: str, persona: str, context: str) -> str:
        """Format prompt for GitHub Copilot."""
        # Copilot uses similar prompt structure but may have different conventions
        persona_prefix = {
            "guide": "As a teaching guide, ",
            "qa_engineer": "As a QA engineer, ",
            "architect": "As a software architect, ",
            "junior_dev": "As a developer, ",
        }

        prefix = persona_prefix.get(persona, "")
        context_str = f"\n\nContext: {context}" if context else ""

        return f"{prefix}{goal}{context_str}"

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str],
        **kwargs,
    ) -> subprocess.Popen:
        """Spawn GitHub Copilot subprocess."""
        # Validate inputs
        _validate_working_dir(working_dir)
        extra_args = kwargs.get("extra_args", [])
        _validate_extra_args(extra_args)

        prompt = self.format_prompt(goal, persona, kwargs.get("context", ""))

        command = ["gh", "copilot", "suggest"]

        command.extend(extra_args)

        command.append(prompt)

        env = os.environ.copy()
        env.update(environment)

        process = subprocess.Popen(
            command,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process

    def parse_output(self, output: str) -> Dict[str, str]:
        """Parse GitHub Copilot output."""
        return {
            "stdout": output,
        }


class AmplifierCLI:
    """Microsoft Amplifier platform implementation."""

    platform_name = "amplifier"

    def validate_installation(self) -> bool:
        """Check if amplifier command is available."""
        return _validate_cli_command(["amplifier", "--version"])

    def get_version(self) -> str:
        """Get Amplifier version."""
        return _get_cli_version(["amplifier", "--version"])

    def format_prompt(self, goal: str, persona: str, context: str) -> str:
        """Format prompt for Microsoft Amplifier."""
        context_str = f"\nContext: {context}" if context else ""

        return f"Goal: {goal}{context_str}\n\nPersona: {persona}"

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str],
        **kwargs,
    ) -> subprocess.Popen:
        """Spawn Amplifier subprocess."""
        # Validate inputs
        _validate_working_dir(working_dir)
        extra_args = kwargs.get("extra_args", [])
        _validate_extra_args(extra_args)

        prompt = self.format_prompt(goal, persona, kwargs.get("context", ""))

        command = ["amplifier", "run"]

        command.extend(extra_args)

        command.append(prompt)

        env = os.environ.copy()
        env.update(environment)

        process = subprocess.Popen(
            command,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        return process

    def parse_output(self, output: str) -> Dict[str, str]:
        """Parse Amplifier output."""
        return {
            "stdout": output,
        }


# Platform registry
_PLATFORM_REGISTRY: Dict[str, PlatformCLI] = {
    "claude-code": ClaudeCodeCLI(),
    "copilot": CopilotCLI(),
    "amplifier": AmplifierCLI(),
}


def register_platform(name: str, platform: PlatformCLI) -> None:
    """Register a custom platform CLI implementation.

    Args:
        name: Platform name identifier
        platform: Platform CLI implementation
    """
    _PLATFORM_REGISTRY[name] = platform


def get_platform_cli(platform: Optional[str] = None) -> PlatformCLI:
    """Get platform CLI implementation.

    Args:
        platform: Platform name (defaults to "claude-code")

    Returns:
        Platform CLI implementation

    Raises:
        ValueError: If platform is not registered
    """
    platform = platform or "claude-code"

    if platform not in _PLATFORM_REGISTRY:
        raise ValueError(
            f"Unknown platform: {platform}. "
            f"Available platforms: {', '.join(_PLATFORM_REGISTRY.keys())}"
        )

    return _PLATFORM_REGISTRY[platform]
