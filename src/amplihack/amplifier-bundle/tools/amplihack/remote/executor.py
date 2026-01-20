"""Remote command execution via azlin.

This module handles transferring context to VMs and executing
amplihack commands remotely.
"""

import base64
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

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
        self.remote_workspace = "~/workspace"

    @staticmethod
    def _encode_b64(text: str) -> str:
        """Encode text as base64 for safe shell transmission.

        Prevents shell escaping issues and visibility in process listings.

        Args:
            text: Text to encode

        Returns:
            Base64-encoded string
        """
        return base64.b64encode(text.encode()).decode()

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

        # Transfer with retry
        # Note: azlin cp requires relative paths, so we need to run from archive directory
        archive_dir = archive_path.parent
        archive_name = archive_path.name

        max_retries = 2
        for attempt in range(max_retries):
            try:
                start_time = time.time()

                subprocess.run(
                    ["azlin", "cp", archive_name, remote_path],
                    cwd=str(archive_dir),  # Run from archive directory
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

        # Should never reach here, but satisfy linter
        raise TransferError("Transfer failed after all retries", context={"vm_name": self.vm.name})

    def execute_remote(
        self, command: str, prompt: str, max_turns: int = 10, api_key: str | None = None
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

        # Encode sensitive data as base64 for safe shell transmission
        # Prevents shell escaping issues and hides from process listings
        encoded_prompt = self._encode_b64(prompt)
        encoded_api_key = self._encode_b64(api_key) if api_key else ""

        # Build remote command
        # First extract and setup context, then run amplihack
        # Note: azlin cp puts files in ~/, so extract from there
        setup_and_run = f"""
set -e
cd ~
tar xzf context.tar.gz

# Setup workspace (clean first for idempotency)
rm -rf {self.remote_workspace}
mkdir -p {self.remote_workspace}
cd {self.remote_workspace}

# Restore git repository
git clone ~/repo.bundle .
# Copy .claude from archive (remove existing first to avoid conflicts)
rm -rf .claude && cp -r ~/.claude .

# Install Python 3.11 (required for blarify dependency)
# Use deadsnakes PPA for Ubuntu
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
fi

# Create venv with Python 3.11 (remove old one first for fresh install)
echo "Creating Python 3.11 virtual environment..."
rm -rf ~/.amplihack-venv
python3.11 -m venv ~/.amplihack-venv
source ~/.amplihack-venv/bin/activate

# Upgrade pip and install amplihack from local bundle
pip install --upgrade pip --quiet
pip install . --quiet
export PATH="$HOME/.amplihack-venv/bin:$PATH"

# Decode API key from base64 (not visible in ps aux)
if [ -n '{encoded_api_key}' ]; then
    export ANTHROPIC_API_KEY=$(echo '{encoded_api_key}' | base64 -d)
# Fallback to .claude.json if no key provided (NFS shared home)
elif [ -f ~/.claude.json ]; then
    API_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.claude.json')).get('anthropicApiKey',''))" 2>/dev/null)
    if [ -n "$API_KEY" ]; then
        export ANTHROPIC_API_KEY="$API_KEY"
        echo "Using API key from ~/.claude.json"
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: No API key found. Set ANTHROPIC_API_KEY or ensure ~/.claude.json exists"
    exit 1
fi

# Decode prompt from base64
PROMPT=$(echo '{encoded_prompt}' | base64 -d)

# Run amplihack command
amplihack claude --{command} --max-turns {max_turns} -- -p "$PROMPT"
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
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # Non-fatal: process may already be terminated or VM unreachable
                pass

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
        # Try workspace first, then venv location (for pip install -e .)
        create_archive = f"""
# Try workspace location first
if [ -d {self.remote_workspace}/.claude/runtime/logs ]; then
    cd {self.remote_workspace}
    tar czf ~/logs.tar.gz .claude/runtime/logs/
    echo "Logs archived from workspace"
# Fall back to venv location
elif [ -d ~/.amplihack-venv/lib/python*/site-packages/amplihack/.claude/runtime/logs ]; then
    cd ~/.amplihack-venv/lib/python*/site-packages/amplihack
    tar czf ~/logs.tar.gz .claude/runtime/logs/
    echo "Logs archived from venv"
else
    echo "No logs directory found in workspace or venv"
    exit 1
fi
"""

        try:
            # Create archive
            subprocess.run(
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
            subprocess.run(
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

    def execute_remote_tmux(
        self,
        session_id: str,
        command: str,
        prompt: str,
        max_turns: int = 10,
        api_key: str | None = None,
    ) -> bool:
        """Execute amplihack command inside tmux session.

        Creates detached tmux session and launches amplihack.
        Returns immediately after starting the session.

        Args:
            session_id: Unique tmux session identifier
            command: Amplihack command (auto, ultrathink, etc.)
            prompt: Task prompt
            max_turns: Maximum turns for auto mode
            api_key: Optional API key (uses environment if not provided)

        Returns:
            True if tmux session started successfully

        Raises:
            ExecutionError: If tmux session creation fails
        """
        # Validate session_id (alphanumeric and dashes only)
        if not session_id or not all(c.isalnum() or c == "-" for c in session_id):
            raise ExecutionError(
                f"Invalid session_id: {session_id}. Must be alphanumeric with dashes only.",
                context={"session_id": session_id},
            )

        # Get API key
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ExecutionError(
                    "ANTHROPIC_API_KEY not found in environment",
                    context={"required": "ANTHROPIC_API_KEY"},
                )

        print(f"Starting tmux session: {session_id}")
        print(f"Command: amplihack {command}")
        print(f"Prompt: {prompt[:100]}..." if len(prompt) > 100 else f"Prompt: {prompt}")

        # Encode sensitive data as base64 for safe shell transmission
        # Prevents shell escaping issues and hides from process listings
        encoded_prompt = self._encode_b64(prompt)
        encoded_api_key = self._encode_b64(api_key) if api_key else ""

        # Defense-in-depth: Quote session_id for shell safety
        safe_session_id = shlex.quote(session_id)
        safe_workspace = shlex.quote(self.remote_workspace)

        # Build setup script (reuse logic from execute_remote)
        setup_and_run = f"""
set -e
cd ~
tar xzf context.tar.gz

# Setup workspace (clean first for idempotency)
rm -rf {self.remote_workspace}
mkdir -p {self.remote_workspace}
cd {self.remote_workspace}

# Restore git repository
git clone ~/repo.bundle .
# Copy .claude from archive (remove existing first to avoid conflicts)
rm -rf .claude && cp -r ~/.claude .

# Install Python 3.11 (required for blarify dependency)
# Use deadsnakes PPA for Ubuntu
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
fi

# Install tmux if not available
if ! command -v tmux &> /dev/null; then
    echo "Installing tmux..."
    sudo apt-get install -y -qq tmux
fi

# Create venv with Python 3.11 (remove old one first for fresh install)
echo "Creating Python 3.11 virtual environment..."
rm -rf ~/.amplihack-venv
python3.11 -m venv ~/.amplihack-venv
source ~/.amplihack-venv/bin/activate

# Upgrade pip and install amplihack from local bundle
pip install --upgrade pip --quiet
pip install . --quiet
export PATH="$HOME/.amplihack-venv/bin:$PATH"

# Decode API key from base64 (not visible in ps aux)
if [ -n '{encoded_api_key}' ]; then
    export ANTHROPIC_API_KEY=$(echo '{encoded_api_key}' | base64 -d)
# Fallback to .claude.json if no key provided (NFS shared home)
elif [ -f ~/.claude.json ]; then
    API_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.claude.json')).get('anthropicApiKey',''))" 2>/dev/null)
    if [ -n "$API_KEY" ]; then
        export ANTHROPIC_API_KEY="$API_KEY"
        echo "Using API key from ~/.claude.json"
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: No API key found. Set ANTHROPIC_API_KEY or ensure ~/.claude.json exists"
    exit 1
fi

# Decode prompt from base64
PROMPT=$(echo '{encoded_prompt}' | base64 -d)

# Create tmux session and run amplihack inside it
tmux new-session -d -s {safe_session_id} -c {safe_workspace}
tmux send-keys -t {safe_session_id} "source ~/.amplihack-venv/bin/activate" C-m
tmux send-keys -t {safe_session_id} "export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY'" C-m
tmux send-keys -t {safe_session_id} "export NODE_OPTIONS='--max-old-space-size=32768'" C-m
tmux send-keys -t {safe_session_id} "amplihack claude --{command} --max-turns {max_turns} -- -p \\"$PROMPT\\"" C-m

echo "Tmux session {safe_session_id} started successfully"
"""

        try:
            result = subprocess.run(
                ["azlin", "connect", self.vm.name, setup_and_run],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for setup
                check=False,
            )

            if result.returncode != 0:
                raise ExecutionError(
                    f"Failed to start tmux session: {result.stderr}",
                    context={"session_id": session_id, "stderr": result.stderr},
                )

            print(f"Tmux session '{session_id}' started successfully on {self.vm.name}")
            return True

        except subprocess.TimeoutExpired:
            raise ExecutionError(
                "Tmux session setup timed out",
                context={"session_id": session_id, "vm_name": self.vm.name},
            )
        except subprocess.CalledProcessError as e:
            raise ExecutionError(
                f"Failed to execute tmux setup: {e.stderr}",
                context={"session_id": session_id, "error": e.stderr},
            )

    def check_tmux_status(self, session_id: str) -> str:
        """Check if tmux session is still running.

        Args:
            session_id: Tmux session identifier

        Returns:
            "running" if session exists, "completed" otherwise

        Raises:
            ExecutionError: If status check fails (not session-related)
        """
        # Validate session_id
        if not session_id or not all(c.isalnum() or c == "-" for c in session_id):
            raise ExecutionError(
                f"Invalid session_id: {session_id}. Must be alphanumeric with dashes only.",
                context={"session_id": session_id},
            )

        check_command = (
            f"tmux has-session -t {session_id} 2>/dev/null && echo running || echo completed"
        )

        try:
            result = subprocess.run(
                ["azlin", "connect", self.vm.name, check_command],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            # Parse output
            status = result.stdout.strip()
            if status in ("running", "completed"):
                return status

            # Unexpected output - treat as completed
            return "completed"

        except subprocess.TimeoutExpired:
            raise ExecutionError(
                "Tmux status check timed out",
                context={"session_id": session_id, "vm_name": self.vm.name},
            )
        except Exception as e:
            raise ExecutionError(
                f"Failed to check tmux status: {e!s}",
                context={"session_id": session_id, "error": str(e)},
            )
