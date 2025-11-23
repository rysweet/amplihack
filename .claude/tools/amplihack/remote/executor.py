"""Remote command execution via azlin.

This module handles transferring context to VMs and executing
amplihack commands remotely.
"""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .errors import ExecutionError, TransferError
from .orchestrator import VM


@dataclass
class ExecutionResult:
    """Result of remote command execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class Executor:
    """Executes amplihack commands on remote VMs.

    Handles file transfer, remote setup, command execution,
    and output capture.
    """

    def __init__(self, vm: VM, timeout_minutes: int = 120):
        """Initialize executor.

        Args:
            vm: Target VM for execution
            timeout_minutes: Maximum execution time (default: 120)
        """
        self.vm = vm
        self.timeout_seconds = timeout_minutes * 60
        self.remote_workspace = "~/amplihack-workspace"  # Use ~/ for azureuser's home

    def transfer_context(self, archive_path: Path) -> bool:
        """Transfer context archive to remote VM.

        Args:
            archive_path: Local path to context.tar.gz

        Returns:
            True if transfer successful

        Raises:
            TransferError: If transfer fails
        """
        if not archive_path.exists():
            raise TransferError(
                f"Archive file not found: {archive_path}",
                context={"archive_path": str(archive_path)},
            )

        print(f"Transferring context ({archive_path.stat().st_size / 1024 / 1024:.1f} MB)...")

        # Remote destination (azlin uses session:path notation with ~/ for home dir)
        remote_path = f"{self.vm.name}:~/context.tar.gz"

        # azlin cp only accepts relative paths from ~/
        # So copy archive to ~/context.tar.gz first, then transfer
        import shutil
        home_archive = Path.home() / "context.tar.gz"
        shutil.copy2(archive_path, home_archive)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                start_time = time.time()

                subprocess.run(
                    ["azlin", "cp", "context.tar.gz", remote_path],
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minutes for transfer
                    check=True,
                )

                duration = time.time() - start_time
                print(f"Transfer complete ({duration:.1f}s)")
                return True

            except subprocess.TimeoutExpired:
                if attempt < max_retries - 1:
                    print(f"Transfer timeout, retrying ({attempt + 2}/{max_retries})...")
                    continue
                raise TransferError(
                    f"File transfer timed out after {max_retries} attempts",
                    context={"vm_name": self.vm.name, "archive_path": str(archive_path)},
                )

            except subprocess.CalledProcessError as e:
                if attempt < max_retries - 1:
                    print(f"Transfer failed, retrying ({attempt + 2}/{max_retries})...")
                    time.sleep(10)
                    continue
                raise TransferError(
                    f"Failed to transfer file: {e.stderr}",
                    context={"vm_name": self.vm.name, "error": e.stderr},
                )

    def execute_remote(
        self, command: str, prompt: str, max_turns: int = 10, api_key: Optional[str] = None
    ) -> ExecutionResult:
        """Execute amplihack command on remote VM.

        Args:
            command: Amplihack command (auto, ultrathink, etc.)
            prompt: Task prompt
            max_turns: Maximum turns for auto mode
            api_key: Optional API key (uses environment if not provided)

        Returns:
            ExecutionResult with output and metadata

        Raises:
            ExecutionError: If execution setup fails
        """
        # Get API key
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ExecutionError(
                    "ANTHROPIC_API_KEY not found in environment",
                    context={"required": "ANTHROPIC_API_KEY"},
                )

        print(f"Executing remote command: amplihack {command}")
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

        # Escape single quotes in prompt for bash
        escaped_prompt = prompt.replace("'", "'\"'\"'")

        # Build remote command
        # First extract and setup context, then run amplihack
        # Note: azlin cp puts files in ~/, so extract from there
        setup_and_run = f"""
set -e
cd ~
tar xzf context.tar.gz

# Setup workspace
mkdir -p {self.remote_workspace}
cd {self.remote_workspace}

# Restore git repository
git clone ~/repo.bundle .
cp -r ~/.claude .

# Install amplihack if needed
if ! command -v amplihack &> /dev/null; then
    pip install amplihack --quiet
fi

# Export API key
export ANTHROPIC_API_KEY='{api_key}'

# Run amplihack command
amplihack claude --{command} --max-turns {max_turns} -- -p '{escaped_prompt}'
"""

        # Execute with timeout
        start_time = time.time()

        try:
            result = subprocess.run(
                ["azlin", "connect", self.vm.name, setup_and_run],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,  # Don't raise on non-zero exit
            )

            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                timed_out=False,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time

            # Try to capture partial output
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""

            print(f"Execution timed out after {duration / 60:.1f} minutes")

            # Try to terminate remote process
            try:
                subprocess.run(
                    ["azlin", "connect", self.vm.name, "pkill -TERM -f amplihack"],
                    timeout=30,
                    capture_output=True,
                )
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                # Non-fatal: process may already be terminated or VM unreachable
                print(f"Warning: Could not terminate remote process: {e}")

            return ExecutionResult(
                exit_code=-1,
                stdout=stdout,
                stderr=stderr
                + f"\n\nExecution timed out after {self.timeout_seconds / 60:.1f} minutes",
                duration_seconds=duration,
                timed_out=True,
            )

    def retrieve_logs(self, local_dest: Path) -> bool:
        """Retrieve execution logs from remote VM.

        Args:
            local_dest: Local directory to store logs

        Returns:
            True if retrieval successful

        Raises:
            TransferError: If retrieval fails
        """
        local_dest.mkdir(parents=True, exist_ok=True)

        print("Retrieving execution logs...")

        # Create archive of logs on remote (put in ~/ for azlin cp)
        create_archive = f"""
cd {self.remote_workspace}
if [ -d .claude/runtime/logs ]; then
    tar czf ~/logs.tar.gz .claude/runtime/logs/
    echo "Logs archived"
else
    echo "No logs directory found"
    exit 1
fi
"""

        try:
            # Create archive
            result = subprocess.run(
                ["azlin", "connect", self.vm.name, create_archive],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )

            # Download archive (azlin cp requires relative paths)
            local_archive = local_dest / "logs.tar.gz"
            subprocess.run(
                ["azlin", "cp", f"{self.vm.name}:~/logs.tar.gz", "logs.tar.gz"],
                cwd=str(local_dest),  # Run from destination directory
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            # Extract locally
            import tarfile

            with tarfile.open(local_archive, "r:gz") as tar:
                tar.extractall(local_dest)

            # Cleanup archive
            local_archive.unlink()

            print(f"Logs retrieved to {local_dest}")
            return True

        except subprocess.CalledProcessError as e:
            raise TransferError(
                f"Failed to retrieve logs: {e.stderr}", context={"vm_name": self.vm.name}
            )
        except subprocess.TimeoutExpired:
            raise TransferError("Log retrieval timed out", context={"vm_name": self.vm.name})

    def retrieve_git_state(self, local_dest: Path) -> bool:
        """Retrieve git repository state from remote VM.

        Args:
            local_dest: Local directory to store git state

        Returns:
            True if retrieval successful

        Raises:
            TransferError: If retrieval fails
        """
        local_dest.mkdir(parents=True, exist_ok=True)

        print("Retrieving git state...")

        # Create bundle of all branches on remote (put in ~/ for azlin cp)
        create_bundle = f"""
cd {self.remote_workspace}
git bundle create ~/results.bundle --all
echo "Bundle created"
"""

        try:
            # Create bundle
            result = subprocess.run(
                ["azlin", "connect", self.vm.name, create_bundle],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            # Download bundle (azlin cp requires relative paths)
            local_bundle = local_dest / "results.bundle"
            subprocess.run(
                ["azlin", "cp", f"{self.vm.name}:~/results.bundle", "results.bundle"],
                cwd=str(local_dest),  # Run from destination directory
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )

            print(f"Git state retrieved to {local_bundle}")
            return True

        except subprocess.CalledProcessError as e:
            raise TransferError(
                f"Failed to retrieve git state: {e.stderr}", context={"vm_name": self.vm.name}
            )
        except subprocess.TimeoutExpired:
            raise TransferError("Git state retrieval timed out", context={"vm_name": self.vm.name})
