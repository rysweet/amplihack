"""CLI subprocess adapter for recipe execution.

Falls back to shelling out to a CLI tool (claude, copilot, rustyclawd) for
agent steps, and uses subprocess for bash steps.

Agent steps run without a hard timeout. Instead, output is streamed and
monitored so callers can observe progress in real time.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path


class CLISubprocessAdapter:
    """Adapter that uses CLI subprocess calls as the execution backend.

    Agent steps run without a hard timeout. A background thread tails the
    output file so callers (or a monitoring loop) can observe progress.
    Bash steps keep a configurable timeout since they should be fast.
    """

    def __init__(self, cli: str = "claude", working_dir: str = ".") -> None:
        self._cli = cli
        self._working_dir = working_dir

    # ------------------------------------------------------------------
    # Agent steps – no hard timeout, stream output
    # ------------------------------------------------------------------

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step by shelling out to the CLI tool.

        The subprocess runs without a hard timeout.  Output is captured
        to a temp file and tailed by a background thread that prints
        progress lines, so an orchestrator watching stdout can tell the
        step is alive.

        Returns:
            The full stdout of the CLI process.

        Raises:
            RuntimeError: If the CLI exits with a non-zero code.
        """
        actual_cwd = working_dir or self._working_dir
        cmd = [self._cli, "-p", prompt]

        # Write output to a temp file so we can tail it
        output_dir = Path(actual_cwd) / ".recipe-output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"agent-step-{int(time.time())}.log"

        # Launch process – no timeout
        # CRITICAL: Remove CLAUDECODE env var so nested claude sessions work
        child_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        with open(output_file, "w") as log_fh:
            proc = subprocess.Popen(
                cmd,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                cwd=actual_cwd,
                env=child_env,
            )

        # Background thread tails the log so callers see progress
        stop_event = threading.Event()
        tail_thread = threading.Thread(
            target=self._tail_output,
            args=(output_file, stop_event),
            daemon=True,
        )
        tail_thread.start()

        try:
            proc.wait()  # Block until process finishes – no timeout
        finally:
            stop_event.set()
            tail_thread.join(timeout=2)

        # Read full output
        stdout = output_file.read_text(errors="replace")

        # Clean up log
        try:
            output_file.unlink(missing_ok=True)
            if not any(output_dir.iterdir()):
                output_dir.rmdir()
        except OSError:
            pass

        if proc.returncode != 0:
            raise RuntimeError(
                f"{self._cli} failed (exit {proc.returncode}): {stdout[-500:].strip()}"
            )
        return stdout.strip()

    # ------------------------------------------------------------------
    # Bash steps – keep a timeout (these should be fast)
    # ------------------------------------------------------------------

    def execute_bash_step(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int = 120,
    ) -> str:
        """Execute a bash command via subprocess.

        Uses explicit bash invocation instead of shell=True to prevent
        injection vulnerabilities (per PR #2010 security fix).
        """
        child_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
            cwd=working_dir or self._working_dir,
            timeout=timeout,
            env=child_env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if the CLI tool is on the PATH."""
        return shutil.which(self._cli) is not None

    @property
    def name(self) -> str:
        return f"cli-subprocess ({self._cli})"

    @staticmethod
    def _tail_output(path: Path, stop: threading.Event) -> None:
        """Tail a file and print new lines until *stop* is set.

        Prints a heartbeat every 60 s if the file hasn't grown, so the
        orchestrator knows the step is still alive.
        """
        last_size = 0
        last_activity = time.time()

        while not stop.is_set():
            try:
                current_size = path.stat().st_size
            except FileNotFoundError:
                stop.wait(1)
                continue

            if current_size > last_size:
                with open(path) as fh:
                    fh.seek(last_size)
                    new_text = fh.read()
                    # Print last meaningful line as progress
                    lines = [ln for ln in new_text.strip().splitlines() if ln.strip()]
                    if lines:
                        print(f"  [agent] {lines[-1][:120]}")
                last_size = current_size
                last_activity = time.time()
            elif time.time() - last_activity > 60:
                print(
                    f"  [agent] ... still running ({int(time.time() - last_activity)}s since last output)"
                )
                last_activity = time.time()

            stop.wait(2)  # Check every 2 seconds
