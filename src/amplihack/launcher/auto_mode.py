"""Auto mode - agentic loop orchestrator."""

import json
import os
import pty
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple


class AutoMode:
    """Simple agentic loop orchestrator for Claude or Copilot."""

    def __init__(
        self, sdk: str, prompt: str, max_turns: int = 10, working_dir: Optional[Path] = None
    ):
        """Initialize auto mode.

        Args:
            sdk: "claude" or "copilot"
            prompt: User's initial prompt
            max_turns: Max iterations (default 10)
            working_dir: Working directory (defaults to current dir)
        """
        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0
        self.working_dir = working_dir if working_dir is not None else Path.cwd()
        self.log_dir = (
            self.working_dir / ".claude" / "runtime" / "logs" / f"auto_{sdk}_{int(time.time())}"
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str):
        """Log message."""
        print(f"[AUTO {self.sdk.upper()}] {msg}")
        with open(self.log_dir / "auto.log", "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

    def run_sdk(self, prompt: str) -> Tuple[int, str]:
        """Run SDK command with prompt, mirroring output to stdout/stderr.

        Returns:
            (exit_code, output)
        """
        if self.sdk == "copilot":
            cmd = ["copilot", "--allow-all-tools", "-p", prompt]
        else:
            cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]

        self.log(f'Running: {cmd[0]} -p "..."')

        # Create a pseudo-terminal for stdin
        # This allows any subprocess (including children) to read from it
        master_fd, slave_fd = pty.openpty()

        # Use Popen to capture and mirror output in real-time
        process = subprocess.Popen(
            cmd,
            stdin=slave_fd,  # Use slave side of pty as stdin
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.working_dir,
        )

        # Close slave_fd in parent process (child has a copy)
        os.close(slave_fd)

        # Capture output while mirroring to stdout/stderr
        stdout_lines = []
        stderr_lines = []

        def read_stream(stream, output_list, mirror_stream):
            """Read from stream and mirror to output."""
            for line in iter(stream.readline, ""):
                output_list.append(line)
                mirror_stream.write(line)
                mirror_stream.flush()

        def feed_pty_stdin(fd, proc):
            """Auto-feed pty master with newlines to prevent any stdin blocking."""
            try:
                while proc.poll() is None:
                    time.sleep(0.1)  # Check every 100ms
                    try:
                        os.write(fd, b"\n")
                    except (BrokenPipeError, OSError):
                        # Process closed or pty closed
                        break
            except Exception:
                # Silently handle any other exceptions
                pass
            finally:
                try:
                    os.close(fd)
                except Exception:
                    pass

        # Create threads to read stdout and stderr concurrently
        stdout_thread = threading.Thread(
            target=read_stream, args=(process.stdout, stdout_lines, sys.stdout)
        )
        stderr_thread = threading.Thread(
            target=read_stream, args=(process.stderr, stderr_lines, sys.stderr)
        )
        stdin_thread = threading.Thread(
            target=feed_pty_stdin, args=(master_fd, process), daemon=True
        )

        # Start threads
        stdout_thread.start()
        stderr_thread.start()
        stdin_thread.start()

        # Wait for process to complete
        process.wait()

        # Wait for output threads to finish reading
        stdout_thread.join()
        stderr_thread.join()
        # stdin_thread is daemon, will terminate automatically

        # Combine captured output
        stdout_output = "".join(stdout_lines)
        stderr_output = "".join(stderr_lines)

        # Log stderr if present
        if stderr_output:
            self.log(f"stderr: {stderr_output[:200]}...")

        return process.returncode, stdout_output

    def run_hook(self, hook: str):
        """Run hook for copilot (Claude does it automatically)."""
        if self.sdk != "copilot":
            return

        hook_path = self.working_dir / ".claude" / "tools" / "amplihack" / "hooks" / f"{hook}.py"
        if not hook_path.exists():
            self.log(f"Hook {hook} not found at {hook_path}")
            return

        self.log(f"Running hook: {hook}")
        start_time = time.time()

        try:
            # Prepare hook input matching Claude Code's format
            session_id = self.log_dir.name  # Use our auto mode session ID
            hook_input = {
                "prompt": self.prompt if hook == "session_start" else "",
                "workingDirectory": str(self.working_dir),
                "sessionId": session_id,
            }

            # Provide JSON input via stdin (hooks expect JSON from Claude Code)
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                timeout=120,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                input=json.dumps(hook_input),
            )
            elapsed = time.time() - start_time

            if result.returncode == 0:
                self.log(f"✓ Hook {hook} completed in {elapsed:.1f}s")
            else:
                self.log(
                    f"⚠ Hook {hook} returned exit code {result.returncode} after {elapsed:.1f}s"
                )
                if result.stderr:
                    self.log(f"Hook stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self.log(f"✗ Hook {hook} timed out after {elapsed:.1f}s")

        try:
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                timeout=120,  # Increased from 30s to 120s for complex hooks
                cwd=self.working_dir,
                capture_output=True,
                text=True,
            )
            elapsed = time.time() - start_time

            if result.returncode == 0:
                self.log(f"✓ Hook {hook} completed in {elapsed:.1f}s")
            else:
                self.log(
                    f"⚠ Hook {hook} returned exit code {result.returncode} after {elapsed:.1f}s"
                )
                if result.stderr:
                    self.log(f"Hook stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self.log(f"✗ Hook {hook} timed out after {elapsed:.1f}s")

    def run(self) -> int:
        """Execute agentic loop."""
        self.log(f"Starting auto mode (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        self.run_hook("session_start")

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            self.log(f"\n--- TURN {self.turn}: Clarify Objective ---")
            code, objective = self.run_sdk(
                f"Clarify this objective with evaluation criteria:\n{self.prompt}"
            )
            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            self.log(f"\n--- TURN {self.turn}: Create Plan ---")
            code, plan = self.run_sdk(
                f"Create execution plan for:\n{objective}\n\nIdentify parallel opportunities."
            )
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                self.log(f"\n--- TURN {self.turn}: Execute & Evaluate ---")

                # Execute
                code, execution_output = self.run_sdk(
                    f"Execute next part of plan:\n{plan}\n\nObjective:\n{objective}"
                )
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                code, eval_result = self.run_sdk(
                    f"Evaluate if objective achieved:\n{objective}\n\nCurrent turn: {turn}/{self.max_turns}"
                )

                # Check completion - look for strong completion signals
                eval_lower = eval_result.lower()
                if (
                    "evaluation: complete" in eval_lower
                    or "objective achieved" in eval_lower
                    or "all criteria met" in eval_lower
                ):
                    self.log("✓ Objective achieved!")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    break

            # Summary - display it directly
            self.log("\n--- Summary ---")
            code, summary = self.run_sdk(
                f"Summarize auto mode session:\nTurns: {self.turn}\nObjective: {objective}"
            )
            if code == 0:
                print(summary)
            else:
                self.log(f"Warning: Summary generation failed (exit {code})")

        finally:
            self.run_hook("stop")

        return 0
