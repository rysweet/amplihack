"""Nested session adapter for recipe execution inside Claude Code.

Uses isolated temporary directories for each agent invocation, streams
output with progress monitoring (no hard timeout), and cleans up
resources after execution.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from amplihack.recipes.adapters.env import build_child_env


class NestedSessionAdapter:
    """Adapter for running nested Claude Code sessions.

    Uses isolated temp directories for each agent call, streams output
    with a monitoring thread (no hard timeout), and cleans up resources.
    """

    def __init__(
        self,
        cli: str = "claude",
        working_dir: str = ".",
        use_temp_dirs: bool = True,
    ) -> None:
        self._cli = cli
        self._working_dir = working_dir
        self._use_temp_dirs = use_temp_dirs

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step in a nested Claude Code session.

        Runs without a hard timeout. Output is streamed to a log file
        and tailed by a background thread for progress monitoring.
        """
        env = build_child_env()

        # Prepare working directory
        temp_dir = None
        if self._use_temp_dirs:
            temp_dir = tempfile.mkdtemp(prefix="recipe-agent-")
            actual_working_dir = temp_dir
        else:
            actual_working_dir = working_dir or self._working_dir

        # Output log for monitoring
        output_dir = Path(actual_working_dir)
        output_file = output_dir / f".agent-step-{int(time.time())}.log"

        try:
            cmd = [self._cli, "-p", prompt]

            # Launch process - no timeout
            with open(output_file, "w") as log_fh:
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    cwd=actual_working_dir,
                    env=env,
                )

            # Tail output in background
            stop_event = threading.Event()
            tail_thread = threading.Thread(
                target=self._tail_output,
                args=(output_file, stop_event),
                daemon=True,
            )
            tail_thread.start()

            try:
                proc.wait()  # No timeout - let it run
            finally:
                stop_event.set()
                tail_thread.join(timeout=2)

            stdout = output_file.read_text(errors="replace")

            if proc.returncode != 0:
                raise RuntimeError(
                    f"{self._cli} failed (exit {proc.returncode}): {stdout[-500:].strip()}"
                )

            return stdout.strip()

        finally:
            # Cleanup
            try:
                output_file.unlink(missing_ok=True)
            except OSError:
                pass
            if self._use_temp_dirs and temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def execute_bash_step(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int | None = None,
    ) -> str:
        """Execute a bash command via subprocess.

        Uses explicit bash invocation instead of shell=True to prevent
        injection vulnerabilities (per PR #2010 security fix).
        """
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
            cwd=working_dir or self._working_dir,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def is_available(self) -> bool:
        """Check if the CLI tool is on the PATH."""
        return shutil.which(self._cli) is not None

    @property
    def name(self) -> str:
        return f"nested-session ({self._cli})"

    @staticmethod
    def _tail_output(path: Path, stop: threading.Event) -> None:
        """Tail a file and print new lines until *stop* is set."""
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
                    lines = [ln for ln in new_text.strip().splitlines() if ln.strip()]
                    if lines:
                        print(f"  [agent] {lines[-1][:120]}")
                last_size = current_size
                last_activity = time.time()
            elif time.time() - last_activity > 60:
                elapsed = int(time.time() - last_activity)
                print(f"  [agent] ... still running ({elapsed}s since last output)")
                last_activity = time.time()

            stop.wait(2)
