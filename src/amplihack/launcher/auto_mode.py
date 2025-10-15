"""Auto mode - agentic loop orchestrator."""

import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple


class AutoMode:
    """Simple agentic loop orchestrator for Claude or Copilot."""

    def __init__(self, sdk: str, prompt: str, max_turns: int = 10):
        """Initialize auto mode.

        Args:
            sdk: "claude" or "copilot"
            prompt: User's initial prompt
            max_turns: Max iterations (default 10)
        """
        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0
        self.log_dir = (
            Path.cwd() / ".claude" / "runtime" / "logs" / f"auto_{sdk}_{int(time.time())}"
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout

    def run_hook(self, hook: str):
        """Run hook for copilot (Claude does it automatically)."""
        if self.sdk != "copilot":
            return

        hook_path = Path.cwd() / ".claude" / "tools" / "amplihack" / "hooks" / f"{hook}.py"
        if hook_path.exists():
            subprocess.run([sys.executable, str(hook_path)], check=False, timeout=30)

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
                return 1

            # Turn 2: Create plan
            self.turn = 2
            self.log(f"\n--- TURN {self.turn}: Create Plan ---")
            code, plan = self.run_sdk(
                f"Create execution plan for:\n{objective}\n\nIdentify parallel opportunities."
            )
            if code != 0:
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                self.log(f"\n--- TURN {self.turn}: Execute & Evaluate ---")

                # Execute
                code, _ = self.run_sdk(
                    f"Execute next part of plan:\n{plan}\n\nObjective:\n{objective}"
                )

                # Evaluate
                code, eval_result = self.run_sdk(
                    f"Evaluate if objective achieved:\n{objective}\n\nCurrent turn: {turn}/{self.max_turns}"
                )

                # Check completion
                if "COMPLETE" in eval_result or "achieved" in eval_result.lower():
                    self.log("✓ Objective achieved!")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    break

            # Summary
            self.log("\n--- Summary ---")
            self.run_sdk(
                f"Summarize auto mode session:\nTurns: {self.turn}\nObjective: {objective}"
            )

        finally:
            self.run_hook("stop")

        return 0
