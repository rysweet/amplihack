"""Cross-platform process management utilities."""

import os
import signal
import subprocess
import sys
from typing import Dict, List, Optional


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
    def create_process_group(popen_args: Dict) -> Dict:
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
        """Check if a command exists in system PATH.

        Args:
            command: Command name to check (e.g., 'git', 'python')

        Returns:
            True if command exists and is executable, False otherwise.
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
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a command with cross-platform compatibility.

        Args:
            command: Command and arguments as list.
            cwd: Working directory.
            env: Environment variables.
            capture_output: Whether to capture output.

        Returns:
            CompletedProcess instance.
        """
        kwargs = {"cwd": cwd, "env": env, "capture_output": capture_output, "text": True}

        # Add shell=True for Windows if needed
        if ProcessManager.is_windows() and command[0] in ["npm", "npx", "node"]:
            # These commands often need shell on Windows
            kwargs["shell"] = True

        return subprocess.run(command, **kwargs)
