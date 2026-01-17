"""UVX Launcher - Launch amplihack via UVX for integration testing.

Philosophy:
- Single responsibility: Launch amplihack using uvx --from git+...
- Self-contained and regeneratable
- Real UVX execution (no mocking)
- Supports CI and local testing

Public API (the "studs"):
    uvx_launch: Launch amplihack with non-interactive prompt
    uvx_launch_with_test_project: Launch with temporary test project
    UVXLaunchResult: Dataclass holding launch results
"""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, List
import shutil
import time

__all__ = ["uvx_launch", "uvx_launch_with_test_project", "UVXLaunchResult"]


@dataclass
class UVXLaunchResult:
    """Result from UVX launch operation.

    Attributes:
        success: Whether launch succeeded
        exit_code: Process exit code
        stdout: Standard output
        stderr: Standard error
        duration: Execution duration in seconds
        log_files: Paths to generated log files
        command: Full command that was executed
    """
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    log_files: List[Path]
    command: str

    def assert_success(self, message: str = "") -> None:
        """Assert that launch succeeded."""
        if not self.success:
            error_msg = f"UVX launch failed: {message}\n"
            error_msg += f"Command: {self.command}\n"
            error_msg += f"Exit code: {self.exit_code}\n"
            error_msg += f"Stdout: {self.stdout}\n"
            error_msg += f"Stderr: {self.stderr}"
            raise AssertionError(error_msg)

    def assert_in_output(self, text: str, message: str = "") -> None:
        """Assert text appears in stdout or stderr."""
        combined = self.stdout + self.stderr
        if text not in combined:
            error_msg = f"Text not found in output: {text}\n{message}\n"
            error_msg += f"Stdout: {self.stdout}\n"
            error_msg += f"Stderr: {self.stderr}"
            raise AssertionError(error_msg)

    def assert_in_logs(self, text: str, message: str = "") -> None:
        """Assert text appears in any log file."""
        for log_file in self.log_files:
            if log_file.exists():
                content = log_file.read_text()
                if text in content:
                    return

        error_msg = f"Text not found in logs: {text}\n{message}\n"
        error_msg += f"Log files: {self.log_files}"
        raise AssertionError(error_msg)


def uvx_launch(
    git_ref: str = "feat/issue-1948-plugin-architecture",
    prompt: Optional[str] = None,
    cwd: Optional[Path] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
    extra_args: Optional[List[str]] = None,
) -> UVXLaunchResult:
    """Launch amplihack via UVX with non-interactive prompt.

    Args:
        git_ref: Git branch/tag/commit to test
        prompt: Non-interactive prompt to send (-p flag)
        cwd: Working directory (default: temp dir)
        timeout: Timeout in seconds
        env: Environment variables
        extra_args: Additional CLI arguments

    Returns:
        UVXLaunchResult with execution details

    Example:
        >>> result = uvx_launch(
        ...     prompt="List available skills",
        ...     timeout=30
        ... )
        >>> result.assert_success()
        >>> result.assert_in_output("skill")
    """
    start_time = time.time()

    # Use temp dir if no cwd specified
    if cwd is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="uvx_test_"))
        cwd = temp_dir
    else:
        cwd = Path(cwd)
        cwd.mkdir(parents=True, exist_ok=True)

    # Build UVX command
    git_url = f"git+https://github.com/rysweet/amplihack@{git_ref}"
    cmd = ["uvx", "--from", git_url, "amplihack"]

    # Add non-interactive prompt if provided
    if prompt:
        cmd.extend(["-p", prompt])

    # Add extra args
    if extra_args:
        cmd.extend(extra_args)

    # Prepare environment
    launch_env = env.copy() if env else {}
    launch_env.update({
        "AMPLIHACK_CI_MODE": "1",  # Non-interactive mode
        "AMPLIHACK_LOG_LEVEL": "DEBUG",  # Verbose logging
    })

    # Execute command
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**subprocess.os.environ, **launch_env},
        )
        success = result.returncode == 0
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr

    except subprocess.TimeoutExpired as e:
        success = False
        exit_code = 124
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = f"Command timed out after {timeout}s"

    except Exception as e:
        success = False
        exit_code = 1
        stdout = ""
        stderr = f"Unexpected error: {str(e)}"

    duration = time.time() - start_time

    # Collect log files
    log_files = _collect_log_files(cwd)

    return UVXLaunchResult(
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration=duration,
        log_files=log_files,
        command=" ".join(cmd),
    )


def uvx_launch_with_test_project(
    project_files: Dict[str, str],
    git_ref: str = "feat/issue-1948-plugin-architecture",
    prompt: Optional[str] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
    extra_args: Optional[List[str]] = None,
) -> UVXLaunchResult:
    """Launch amplihack with a temporary test project.

    Creates a temp project with specified files, launches amplihack via UVX.

    Args:
        project_files: Dict of {relative_path: content}
        git_ref: Git branch/tag/commit to test
        prompt: Non-interactive prompt
        timeout: Timeout in seconds
        env: Environment variables
        extra_args: Additional CLI arguments

    Returns:
        UVXLaunchResult with execution details

    Example:
        >>> result = uvx_launch_with_test_project(
        ...     project_files={
        ...         "main.py": "print('hello')",
        ...         "test.py": "def test_hello(): pass"
        ...     },
        ...     prompt="Detect languages in this project"
        ... )
        >>> result.assert_success()
        >>> result.assert_in_output("Python")
    """
    # Create temp project directory
    project_dir = Path(tempfile.mkdtemp(prefix="uvx_project_"))

    try:
        # Write project files
        for rel_path, content in project_files.items():
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Launch from project directory
        return uvx_launch(
            git_ref=git_ref,
            prompt=prompt,
            cwd=project_dir,
            timeout=timeout,
            env=env,
            extra_args=extra_args,
        )

    finally:
        # Cleanup handled by caller or temp dir auto-cleanup
        pass


def _collect_log_files(directory: Path) -> List[Path]:
    """Collect all log files from directory and subdirectories.

    Args:
        directory: Root directory to search

    Returns:
        List of log file paths
    """
    log_files = []

    # Common log locations
    log_patterns = [
        ".claude/runtime/logs/**/*.log",
        ".claude/runtime/logs/**/*.md",
        "*.log",
        "logs/**/*.log",
    ]

    for pattern in log_patterns:
        log_files.extend(directory.glob(pattern))

    return list(set(log_files))  # Remove duplicates


# Convenience functions for common test scenarios

def launch_and_test_hook(
    hook_name: str,
    git_ref: str = "feat/issue-1948-plugin-architecture",
    timeout: int = 60,
) -> UVXLaunchResult:
    """Launch amplihack and verify hook execution.

    Args:
        hook_name: Hook to test (SessionStart, Stop, etc.)
        git_ref: Git reference
        timeout: Timeout in seconds

    Returns:
        UVXLaunchResult
    """
    prompt = f"Run SessionStart hook and show logs"
    return uvx_launch(
        git_ref=git_ref,
        prompt=prompt,
        timeout=timeout,
    )


def launch_and_test_skill(
    skill_name: str,
    git_ref: str = "feat/issue-1948-plugin-architecture",
    timeout: int = 60,
) -> UVXLaunchResult:
    """Launch amplihack and verify skill invocation.

    Args:
        skill_name: Skill to test
        git_ref: Git reference
        timeout: Timeout in seconds

    Returns:
        UVXLaunchResult
    """
    prompt = f"List all available skills"
    return uvx_launch(
        git_ref=git_ref,
        prompt=prompt,
        timeout=timeout,
    )


def launch_and_test_command(
    command: str,
    git_ref: str = "feat/issue-1948-plugin-architecture",
    timeout: int = 60,
) -> UVXLaunchResult:
    """Launch amplihack and test slash command.

    Args:
        command: Command to test (e.g., "/ultrathink", "/fix")
        git_ref: Git reference
        timeout: Timeout in seconds

    Returns:
        UVXLaunchResult
    """
    # Remove leading slash if present
    if command.startswith("/"):
        command = command[1:]

    prompt = f"Execute /{command} command"
    return uvx_launch(
        git_ref=git_ref,
        prompt=prompt,
        timeout=timeout,
    )


def launch_with_lsp_detection(
    languages: List[str],
    git_ref: str = "feat/issue-1948-plugin-architecture",
    timeout: int = 60,
) -> UVXLaunchResult:
    """Launch amplihack and test LSP detection.

    Args:
        languages: Languages to test (python, typescript, rust)
        git_ref: Git reference
        timeout: Timeout in seconds

    Returns:
        UVXLaunchResult
    """
    # Create project files for each language
    project_files = {}

    if "python" in languages:
        project_files["main.py"] = "print('hello')"
    if "typescript" in languages:
        project_files["index.ts"] = "console.log('hello');"
    if "rust" in languages:
        project_files["main.rs"] = 'fn main() { println!("hello"); }'
    if "javascript" in languages:
        project_files["app.js"] = "console.log('hello');"
    if "go" in languages:
        project_files["main.go"] = 'package main\n\nfunc main() {}'

    prompt = "Detect languages in this project and configure LSP"

    return uvx_launch_with_test_project(
        project_files=project_files,
        git_ref=git_ref,
        prompt=prompt,
        timeout=timeout,
    )
