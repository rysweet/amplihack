"""Cross-platform process management utilities."""

import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ProcessManager:
    """Cross-platform process management utilities."""

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows.

        Returns:
            True if Windows, False otherwise.
        """
        return sys.platform == "win32" or os.name == "nt"

    @staticmethod
    def is_unix() -> bool:
        """Check if running on Unix-like system.

        Returns:
            True if Unix-like, False otherwise.
        """
        return not ProcessManager.is_windows()

    @staticmethod
    def create_process_group(popen_args: dict) -> dict:
        """Add process group creation flags to Popen arguments.

        Args:
            popen_args: Dictionary of Popen arguments.

        Returns:
            Modified dictionary with process group flags.
        """
        if ProcessManager.is_windows():
            # CREATE_NEW_PROCESS_GROUP is Windows-specific
            import subprocess

            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                popen_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_args["preexec_fn"] = os.setsid
        return popen_args

    @staticmethod
    def terminate_process_group(process: subprocess.Popen, timeout: int = 5) -> None:
        """Terminate a process and its group.

        Args:
            process: Process to terminate.
            timeout: Timeout in seconds for graceful shutdown.
        """
        if process.poll() is not None:
            return  # Already terminated

        try:
            if ProcessManager.is_windows():
                # Windows: terminate the process
                process.terminate()
            else:
                # Unix: terminate the process group
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if not responding
                if ProcessManager.is_windows():
                    process.kill()
                else:
                    try:
                        os.killpg(pgid, signal.SIGKILL)  # type: ignore
                    except (NameError, UnboundLocalError):
                        process.kill()  # Fallback if pgid not defined
                process.wait()

        except Exception:
            # Try direct kill as fallback
            try:
                process.kill()
                process.wait()
            except Exception:
                pass  # Fallback already attempted

    @staticmethod
    def check_command_exists(command: str) -> bool:
        """Check if a command exists in PATH.

        Args:
            command: Command name to check.

        Returns:
            True if command exists, False otherwise.
        """
        try:
            if ProcessManager.is_windows():
                # Windows: use where command
                result = subprocess.run(
                    ["where", command], capture_output=True, text=True, check=False
                )
            else:
                # Unix: use which command
                result = subprocess.run(
                    ["which", command], capture_output=True, text=True, check=False
                )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def run_command(
        command: list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        capture_output: bool = True,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        """Run a command with cross-platform compatibility.

        Args:
            command: Command and arguments as list.
            cwd: Working directory.
            env: Environment variables.
            capture_output: Whether to capture output.

        Returns:
            CompletedProcess instance.

        Security:
            - NEVER uses shell=True (prevents shell injection)
            - On Windows, resolves full path to .cmd/.bat files using shutil.which()
            - Uses list[str] commands exclusively (no string interpolation)
        """
        kwargs: dict = {
            "cwd": cwd,
            "env": env,
            "capture_output": capture_output,
            "text": True,
            "timeout": timeout,
            "check": False,
        }

        # On Windows, npm/npx/node are typically .cmd batch files
        # Instead of using shell=True (SECURITY RISK), resolve full path
        if ProcessManager.is_windows() and command and command[0] in ["npm", "npx", "node"]:
            # Find the full path to the .cmd file (e.g., npm.cmd)
            resolved_path = shutil.which(command[0])
            if resolved_path:
                # Use the resolved path instead of bare command name
                command = [resolved_path] + command[1:]
            # If not found, let subprocess.run fail with FileNotFoundError
            # which is better than shell injection vulnerability

        return subprocess.run(command, **kwargs)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Structured subprocess result with normalized text output."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def ensure_path_within_root(root: Path, candidate: Path) -> Path:
    """Resolve *candidate* and ensure it remains within *root*."""
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"Path '{resolved_candidate}' escapes allowed root '{resolved_root}'"
        ) from exc
    return resolved_candidate


def run_command_with_timeout(
    command: list[str],
    *,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    timeout: int,
) -> CommandResult:
    """Run a subprocess with an explicit timeout and captured text output."""
    if not command:
        raise ValueError("Command must not be empty")
    if timeout <= 0:
        raise ValueError("Command timeout must be greater than zero")

    completed = ProcessManager.run_command(
        command,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
        capture_output=True,
        timeout=timeout,
    )
    return CommandResult(
        args=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
