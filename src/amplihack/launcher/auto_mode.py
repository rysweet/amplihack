"""Auto mode - agentic loop orchestrator."""

import subprocess
import sys
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
        """Run SDK command with prompt.

        Returns:
            (exit_code, output)
        """
        if self.sdk == "copilot":
            cmd = ["copilot", "--allow-all-tools", "-p", prompt]
        else:
            cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]

        self.log(f'Running: {cmd[0]} -p "..."')
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            cwd=self.working_dir,
        )
        return result.returncode, result.stdout

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
            # Provide empty JSON input via stdin (hooks expect JSON from stdin)
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                timeout=120,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                input="{}",  # Provide empty JSON object as input
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
