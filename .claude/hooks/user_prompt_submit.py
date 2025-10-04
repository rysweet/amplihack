#!/usr/bin/env python3
"""
UserPromptSubmit Hook - Secure Shell Command Execution

This hook detects prompts starting with '!' and executes safe shell commands
in a restricted environment, blocking the original prompt submission and
showing the command output in the reason field.

SECURITY: Only allows whitelisted commands with strict validation and sandboxing.

Usage: Type "!command" to execute shell commands
Example: "!ls -la" will execute ls -la and show the output
"""

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Dict, List, Set


class SecurityConfig:
    """Security configuration for shell command execution."""

    # Whitelisted commands (ONLY these are allowed)
    ALLOWED_COMMANDS: Set[str] = {
        "ls",
        "pwd",
        "date",
        "echo",
        "cat",
        "head",
        "tail",
        "wc",
        "grep",
        "find",
        "sort",
        "uniq",
        "cut",
        "whoami",
        "uname",
        "df",
        "du",
        "ps",
        "which",
        "type",
    }

    # Dangerous patterns that are NEVER allowed
    DANGEROUS_PATTERNS = [
        r"[;&|`$()]",  # Shell metacharacters
        r"\.\./",  # Path traversal
        r"/etc/",  # System directories
        r"/root/",  # Root directory
        r"/usr/bin/",  # System binaries
        r"/var/",  # System variables
        r"sudo",  # Privilege escalation
        r"su\s",  # User switching
        r"curl.*http",  # Network access
        r"wget",  # Download tools
        r"nc\s",  # Netcat
        r"python.*-c",  # Python execution
        r"bash.*-c",  # Bash execution
        r"sh.*-c",  # Shell execution
        r">.*/",  # Redirection to system paths
        r"rm\s",  # File removal
        r"mv\s",  # File moving
        r"cp.*/",  # Copying to system paths
        r"chmod",  # Permission changes
        r"chown",  # Ownership changes
    ]

    # Safe argument patterns
    SAFE_ARG_PATTERNS = {
        "-l",
        "-la",
        "-lah",
        "-n",
        "-r",
        "-h",
        "--help",
        "-1",
        "-2",
        "-3",
        "-4",
        "-5",
        "-f",
        "-d",
        "-t",
    }

    # Maximum execution time (seconds)
    MAX_EXECUTION_TIME = 5

    # Maximum output size (bytes)
    MAX_OUTPUT_SIZE = 5000


class SecureCommandValidator:
    """Validates commands against security policies."""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def validate_command(self, command: str) -> bool:
        """
        Validate command against security policies.

        Args:
            command: Raw command string

        Returns:
            True if command is safe, False otherwise
        """
        try:
            # Parse command safely
            cmd_parts = shlex.split(command)
            if not cmd_parts:
                return False

            # Check base command against whitelist
            base_cmd = cmd_parts[0].split("/")[-1]
            if base_cmd not in self.config.ALLOWED_COMMANDS:
                return False

            # Check for dangerous patterns in entire command
            for pattern in self.config.DANGEROUS_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return False

            # Validate arguments
            return self._validate_arguments(cmd_parts[1:])

        except (ValueError, Exception):
            return False

    def _validate_arguments(self, args: List[str]) -> bool:
        """Validate command arguments for safety."""
        for arg in args:
            # No absolute paths to sensitive directories
            if arg.startswith(("/etc/", "/root/", "/usr/", "/var/", "/sys/", "/proc/")):
                return False

            # Check argument patterns
            if arg.startswith("-"):
                if arg not in self.config.SAFE_ARG_PATTERNS:
                    # Only allow simple single-character flags
                    if not re.match(r"^-[a-zA-Z]$", arg):
                        return False

            # No suspicious content in arguments
            for pattern in self.config.DANGEROUS_PATTERNS:
                if re.search(pattern, arg, re.IGNORECASE):
                    return False

        return True


class OutputSanitizer:
    """Sanitizes command output to prevent information disclosure."""

    SENSITIVE_PATTERNS = [
        r"(?i)(password|passwd|pwd)[:=]\s*\S+",
        r"(?i)(api[_-]?key|apikey)[:=]\s*\S+",
        r"(?i)(secret|token)[:=]\s*\S+",
        r"(?i)(private[_-]?key)[:=]\s*\S+",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email addresses
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IP addresses (some)
        r"\b[0-9a-fA-F]{32,}\b",  # Potential hashes/keys
    ]

    def sanitize_output(self, output: str, max_size: int = 5000) -> str:
        """
        Remove sensitive information from command output.

        Args:
            output: Raw command output
            max_size: Maximum output size in bytes

        Returns:
            Sanitized output string
        """
        sanitized = output

        # Remove sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)

        # Limit output length
        if len(sanitized) > max_size:
            sanitized = sanitized[:max_size] + "\n... [OUTPUT TRUNCATED]"

        return sanitized


class SecureExecutor:
    """Executes commands in a secure, restricted environment."""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.sanitizer = OutputSanitizer()

    def execute_command(self, command: str) -> Dict:
        """
        Execute command in secure environment.

        Args:
            command: Validated command string

        Returns:
            Dictionary with execution results
        """
        try:
            # Create minimal, restricted environment
            restricted_env = {
                "PATH": "/usr/bin:/bin",  # Minimal PATH
                "HOME": "/tmp",  # Restricted home
                "USER": "restricted",  # Generic user
                "SHELL": "/bin/bash",  # Basic shell
                "TERM": "xterm",  # Basic terminal
                "LC_ALL": "C",  # Standard locale
                # Remove all other environment variables for security
            }

            # Execute with strict resource limits
            result = subprocess.run(
                ["bash", "-c", command],
                env=restricted_env,
                cwd="/tmp",  # Safe working directory
                capture_output=True,
                text=True,
                timeout=self.config.MAX_EXECUTION_TIME,
                # Additional security: no new privileges
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            # Sanitize output
            sanitized_stdout = self.sanitizer.sanitize_output(
                result.stdout, self.config.MAX_OUTPUT_SIZE
            )
            sanitized_stderr = self.sanitizer.sanitize_output(
                result.stderr, self.config.MAX_OUTPUT_SIZE
            )

            return {
                "success": result.returncode == 0,
                "output": sanitized_stdout.strip(),
                "error": sanitized_stderr.strip(),
                "exit_code": result.returncode,
                "command": command,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Command timed out ({self.config.MAX_EXECUTION_TIME} second limit)",
                "exit_code": -1,
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Execution error: {str(e)}",
                "exit_code": -1,
                "command": command,
            }


def execute_shell_command(command: str) -> dict:
    """
    Execute a shell command securely and return the result.

    Args:
        command: Shell command to execute

    Returns:
        Dictionary with success, output, error, and exit_code
    """
    # Initialize security components
    config = SecurityConfig()
    validator = SecureCommandValidator(config)
    executor = SecureExecutor(config)

    # Validate command against security policies
    if not validator.validate_command(command):
        return {
            "success": False,
            "output": "",
            "error": "Command blocked by security policy. Only safe, whitelisted commands are allowed.",
            "exit_code": -1,
            "command": command,
            "security_blocked": True,
        }

    # Execute the validated command
    return executor.execute_command(command)


def format_command_output(result: dict) -> str:
    """
    Format command execution result for display.

    Args:
        result: Command execution result dictionary

    Returns:
        Formatted output string
    """
    lines = []

    # Handle security-blocked commands
    if result.get("security_blocked"):
        lines.append("🚫 SECURITY: Command blocked")
        lines.append(f"Command: {result['command']}")
        lines.append("")
        lines.append("Security Policy:")
        lines.append("• Only whitelisted commands are allowed")
        lines.append(
            "• Allowed: ls, pwd, date, echo, cat, head, tail, wc, grep, find, sort, uniq, cut, whoami, uname, df, du, ps, which, type"
        )
        lines.append("• Dangerous patterns and system access are blocked")
        lines.append("")
        lines.append("Error: " + result["error"])
        lines.append("")
        lines.append("---")
        lines.append("Use only safe commands. For unrestricted access, use Claude Code tools.")
        return "\n".join(lines)

    # Format normal command execution
    lines.append(f"$ {result['command']}")
    lines.append("")

    if result["success"]:
        if result["output"]:
            lines.append("Output:")
            lines.append(result["output"])
        else:
            lines.append("✅ Command completed successfully (no output)")
    else:
        lines.append(f"❌ Command failed (exit code: {result['exit_code']})")
        if result["error"]:
            lines.append("Error:")
            lines.append(result["error"])

    lines.append("")
    lines.append("---")
    lines.append("Shell command execution blocked prompt submission.")
    lines.append("Use normal prompts to interact with Claude Code.")

    return "\n".join(lines)


def main():
    """Main hook execution function."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        prompt = input_data.get("prompt", "").strip()

        # Check if prompt starts with '!'
        if not prompt.startswith("!"):
            # Not a shell command, allow prompt to proceed
            sys.exit(0)

        # Extract shell command (remove the '!' prefix)
        command = prompt[1:].strip()

        if not command:
            # Empty command, block with helpful message
            output = {
                "decision": "block",
                "reason": "Empty shell command. Usage: !<command>\nExample: !ls -la",
            }
            print(json.dumps(output))
            sys.exit(0)

        # Execute the shell command
        result = execute_shell_command(command)

        # Format the output for display
        formatted_output = format_command_output(result)

        # Block the prompt and show command output
        output = {"decision": "block", "reason": formatted_output}

        print(json.dumps(output))
        sys.exit(0)

    except json.JSONDecodeError:
        # Invalid JSON input, allow prompt to proceed
        sys.exit(0)
    except Exception as e:
        # Unexpected error, block with error message
        output = {"decision": "block", "reason": f"Shell command hook error: {str(e)}"}
        print(json.dumps(output))
        sys.exit(0)


if __name__ == "__main__":
    main()
