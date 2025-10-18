"""Auto mode - agentic loop orchestrator."""

import asyncio
import json
import os
import pty
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

# Try to import Claude SDK, fall back gracefully
try:
    from claude_agent_sdk import query, ClaudeAgentOptions  # type: ignore

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


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

    def log(self, msg: str, level: str = "INFO"):
        """Log message with optional level."""
        print(f"[AUTO {self.sdk.upper()}] {msg}")
        with open(self.log_dir / "auto.log", "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}\n")

    def run_sdk(self, prompt: str) -> Tuple[int, str]:
        """Run SDK command with prompt, choosing method by provider.

        For Claude: Use Python SDK with streaming (if available)
        For Copilot: Use subprocess approach

        Returns:
            (exit_code, output)
        """
        # Use SDK for Claude if available, subprocess otherwise
        if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
            # Run async function in sync context
            return asyncio.run(self._run_turn_with_sdk(prompt))
        # Fallback to subprocess for Copilot or if SDK unavailable
        return self._run_sdk_subprocess(prompt)

    def _run_sdk_subprocess(self, prompt: str) -> Tuple[int, str]:
        """Run SDK command via subprocess (legacy/copilot mode).

        Returns:
            (exit_code, output)
        """
        if self.sdk == "copilot":
            cmd = ["copilot", "--allow-all-tools", "--add-dir", "/", "-p", prompt]
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

    def _build_philosophy_context(self) -> str:
        """Build comprehensive philosophy and decision-making context.

        Returns context string that instructs Claude on autonomous decision-making
        using project philosophy files.
        """
        return """AUTONOMOUS MODE: You are in auto mode. Do NOT ask questions. Make decisions using:
1. Explicit user requirements (HIGHEST PRIORITY - cannot be overridden)
2. @.claude/context/USER_PREFERENCES.md guidance (MANDATORY - must follow)
3. @.claude/context/PHILOSOPHY.md principles (ruthless simplicity, zero-BS, modular design)
4. @.claude/workflow/DEFAULT_WORKFLOW.md patterns
5. @.claude/context/USER_REQUIREMENT_PRIORITY.md for resolving conflicts

Decision Authority:
- YOU DECIDE: How to implement, what patterns to use, technical details, architecture
- YOU PRESERVE: Explicit user requirements, user preferences, "must have" constraints
- WHEN AMBIGUOUS: Apply philosophy principles to make the simplest, most modular choice

Document your decisions and reasoning in comments/logs."""

    async def _run_turn_with_sdk(self, prompt: str) -> Tuple[int, str]:
        """Execute one turn using Claude Python SDK with streaming.

        Args:
            prompt: The prompt for this turn

        Returns:
            (exit_code, output_text)
        """
        if not CLAUDE_SDK_AVAILABLE:
            self.log("ERROR: Claude SDK not available, falling back to subprocess")
            return self._run_sdk_subprocess(prompt)

        try:
            self.log("Using Claude SDK (streaming mode)")
            output_lines = []

            # Configure SDK options
            options = ClaudeAgentOptions(
                working_directory=str(self.working_dir),
                dangerously_skip_permissions=True,
            )

            # Stream response
            async for message in query(prompt, options=options):
                # message is a dict with 'type' and 'content'
                if message.get("type") == "text":
                    content = message.get("content", "")
                    # Print to console in real-time
                    print(content, end="", flush=True)
                    output_lines.append(content)
                elif message.get("type") == "error":
                    error_msg = message.get("content", "Unknown error")
                    self.log(f"SDK error: {error_msg}", level="ERROR")
                    return (1, "\n".join(output_lines))

            # Success
            full_output = "".join(output_lines)
            return (0, full_output)

        except Exception as e:
            self.log(f"SDK execution failed: {e}", level="ERROR")
            import traceback

            self.log(f"Traceback: {traceback.format_exc()}", level="ERROR")
            return (1, f"SDK Error: {e!s}")

    def run_hook(self, hook: str):
        """Run hook for copilot (Claude SDK handles hooks automatically)."""
        if self.sdk != "copilot":
            # Claude SDK runs hooks automatically
            self.log("Skipping manual hook execution for Claude SDK (hooks run automatically)")
            return

        hook_path = self.working_dir / ".claude" / "tools" / "amplihack" / "hooks" / f"{hook}.py"
        if not hook_path.exists():
            self.log(f"Hook {hook} not found at {hook_path}")
            return

        self.log(f"Running hook: {hook}")
        start_time = time.time()

        try:
            # Prepare hook input matching Claude Code's format
            session_id = self.log_dir.name
            hook_input = {
                "prompt": self.prompt if hook == "session_start" else "",
                "workingDirectory": str(self.working_dir),
                "sessionId": session_id,
            }

            # Provide JSON input via stdin
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
        except Exception as e:
            self.log(f"✗ Hook {hook} failed: {e}")

    def run(self) -> int:
        """Execute agentic loop."""
        self.log(f"Starting auto mode (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        self.run_hook("session_start")

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            self.log(f"\n--- TURN {self.turn}: Clarify Objective ---")
            turn1_prompt = f"""{self._build_philosophy_context()}

Task: Analyze this user request and clarify the objective with evaluation criteria.

1. IDENTIFY EXPLICIT REQUIREMENTS: Extract any "must have", "all", "include everything", quoted specifications
2. IDENTIFY IMPLICIT PREFERENCES: What user likely wants based on @.claude/context/USER_PREFERENCES.md
3. APPLY PHILOSOPHY: Ruthless simplicity from @.claude/context/PHILOSOPHY.md, modular design, zero-BS implementation
4. DEFINE SUCCESS CRITERIA: Clear, measurable, aligned with philosophy

User Request:
{self.prompt}"""

            code, objective = self.run_sdk(turn1_prompt)
            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            self.log(f"\n--- TURN {self.turn}: Create Plan ---")
            turn2_prompt = f"""{self._build_philosophy_context()}

Reference:
- @.claude/context/PHILOSOPHY.md for design principles
- @.claude/workflow/DEFAULT_WORKFLOW.md for standard workflow steps
- @.claude/context/USER_PREFERENCES.md for user-specific preferences

Task: Create an execution plan that:
1. PRESERVES all explicit user requirements from objective
2. APPLIES ruthless simplicity and modular design principles
3. IDENTIFIES parallel execution opportunities (agents, tasks, operations)
4. FOLLOWS the brick philosophy (self-contained modules with clear contracts)
5. IMPLEMENTS zero-BS approach (no stubs, no TODOs, no placeholders)

Plan Structure:
- List explicit requirements that CANNOT be changed
- Break work into self-contained modules (bricks)
- Identify what can execute in parallel
- Define clear contracts between components
- Specify success criteria for each step

Objective:
{objective}"""

            code, plan = self.run_sdk(turn2_prompt)
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                self.log(f"\n--- TURN {self.turn}: Execute & Evaluate ---")

                # Execute
                execute_prompt = f"""{self._build_philosophy_context()}

Task: Execute the next part of the plan using specialized agents where possible.

Execution Guidelines:
- Use PARALLEL EXECUTION by default (multiple agents, multiple tasks)
- Apply @.claude/context/PHILOSOPHY.md principles throughout
- Delegate to specialized agents from .claude/agents/* when appropriate
- Implement COMPLETE features (no stubs, no TODOs, no placeholders)
- Make ALL implementation decisions autonomously
- Log your decisions and reasoning

Current Plan:
{plan}

Original Objective:
{objective}

Current Turn: {turn}/{self.max_turns}"""

                code, execution_output = self.run_sdk(execute_prompt)
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                eval_prompt = f"""{self._build_philosophy_context()}

Task: Evaluate if the objective is achieved based on:
1. All explicit user requirements met
2. Philosophy principles applied (simplicity, modularity, zero-BS)
3. Success criteria from Turn 1 satisfied
4. No placeholders or incomplete implementations remain

Respond with one of:
- "EVALUATION: COMPLETE" - All criteria met, objective achieved
- "EVALUATION: IN PROGRESS" - Making progress, continue execution
- "EVALUATION: NEEDS ADJUSTMENT" - Issues identified, plan adjustment needed

Include brief reasoning for your evaluation.

Objective:
{objective}

Current Turn: {turn}/{self.max_turns}"""

                code, eval_result = self.run_sdk(eval_prompt)

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
