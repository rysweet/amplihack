"""Auto mode - agentic loop orchestrator."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

# Try to import Claude SDK, fall back gracefully
try:
    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

# Import session management components
from amplihack.launcher.fork_manager import ForkManager
from amplihack.launcher.prompt_templates import PromptTemplates
from amplihack.launcher.session import PromptTransformManager, SessionManager, UIManager
from amplihack.launcher.session_capture import MessageCapture
from amplihack.launcher.transcript_exporter import TranscriptExporter
from amplihack.launcher.turn_executor import TurnExecutor


class AutoMode:
    """Simple agentic loop orchestrator for Claude, Copilot, or Codex."""

    def __init__(
        self,
        sdk: str,
        prompt: str,
        max_turns: int = 10,
        working_dir: Optional[Path] = None,
        ui_mode: bool = False,
    ):
        """Initialize auto mode.

        Args:
            sdk: "claude", "copilot", or "codex"
            prompt: User's initial prompt
            max_turns: Max iterations (default 10)
            working_dir: Working directory (defaults to current dir)
            ui_mode: Enable interactive UI mode (requires Rich library)
        """
        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0
        self.start_time = 0.0  # Will be set when run() starts
        self.working_dir = working_dir if working_dir is not None else Path.cwd()
        self.ui_enabled = ui_mode
        self.ui = None
        self.log_dir = (
            self.working_dir / ".claude" / "runtime" / "logs" / f"auto_{sdk}_{int(time.time())}"
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize managers
        self.session_manager = SessionManager(self.log_dir, self.working_dir, self.log)
        self.message_capture = MessageCapture()
        self.fork_manager = ForkManager(start_time=0, fork_threshold=3600)  # 60 minutes
        self.total_session_time = 0.0  # Cumulative duration across forks
        self.prompt_transform = PromptTransformManager(self.log)

        # Initialize turn executor
        self.turn_executor = TurnExecutor(
            sdk=sdk,
            working_dir=self.working_dir,
            log_func=self.log,
            message_capture=self.message_capture,
            todo_handler=self._handle_todo_write,
        )

        # Initialize transcript exporter
        self.transcript_exporter = TranscriptExporter(
            log_dir=self.log_dir,
            log_func=self.log,
            format_elapsed_func=self._format_elapsed,
        )

        # Write original prompt
        self.session_manager.write_initial_prompt(prompt, sdk, max_turns)

        # Initialize UI if enabled
        self.ui_manager = None
        if self.ui_enabled:
            try:
                from .auto_mode_state import AutoModeState
                from .auto_mode_ui import AutoModeUI

                # Create shared state with session ID
                session_id = self.log_dir.name
                self.state = AutoModeState(
                    session_id=session_id,
                    start_time=time.time(),
                    max_turns=max_turns,
                    objective=prompt,
                )

                # Create UI
                self.ui = AutoModeUI(self.state, self, self.working_dir)
                self.ui_manager = UIManager(self.ui, self.log)
            except ImportError as e:
                print("\n⚠️  ERROR: Rich library required but not found", file=sys.stderr)
                print("   This should not happen - Rich is a required dependency", file=sys.stderr)
                print(f"   Error: {e}", file=sys.stderr)
                print("\n   Try reinstalling: uvx --from git+https... amplihack", file=sys.stderr)
                print("\n   Continuing in non-UI mode...\n", file=sys.stderr)

                self.log(
                    f"Error: Rich library missing despite being required dependency: {e}",
                    level="ERROR",
                )
                self.ui_enabled = False
                self.ui = None
                self.ui_manager = None

    def log(self, msg: str, level: str = "INFO"):
        """Log message with optional level."""
        # Only print INFO, WARNING, ERROR to console - skip DEBUG
        if level in ("INFO", "WARNING", "ERROR"):
            print(f"[AUTO {self.sdk.upper()}] {msg}\n", flush=True)

            # Update UI state if enabled (all levels)
            if self.ui_enabled and hasattr(self, "state"):
                self.state.add_log(msg, timestamp=False)

        # Always write to file (including DEBUG)
        with open(self.log_dir / "auto.log", "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}\n")

    def _format_elapsed(self, seconds: float) -> str:
        """Format elapsed time as Xm Ys or Xs.

        Args:
            seconds: Elapsed time in seconds

        Returns:
            Formatted string like "45s" or "1m 23s"
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"

    def _progress_str(self, phase: str) -> str:
        """Build progress indicator string with total duration across forks.

        Args:
            phase: Current phase name (Clarifying, Planning, Executing, Evaluating, Summarizing)

        Returns:
            Progress string like "[Turn 2/10 | Planning | 1m 23s]" or with fork info
        """
        current_fork_time = time.time() - self.start_time
        total_time = self.total_session_time + current_fork_time

        fork_info = ""
        if self.fork_manager and self.fork_manager.get_fork_count() > 0:
            fork_info = f" [Fork {self.fork_manager.get_fork_count() + 1}]"

        return f"[Turn {self.turn}/{self.max_turns} | {phase} | {self._format_elapsed(total_time)}{fork_info}]"

    def _format_todos_for_terminal(self, todos: list) -> str:
        """Format todo list for terminal display with ANSI colors.

        Args:
            todos: List of todo items with status and content

        Returns:
            Formatted string ready for terminal display
        """
        if not todos:
            return ""

        # ANSI color codes
        BOLD = "\033[1m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        RESET = "\033[0m"

        lines = [f"\n{BOLD}📋 Todo List:{RESET}"]

        for i, todo in enumerate(todos, 1):
            status = todo.get("status", "pending")
            content = todo.get("content", "")
            active_form = todo.get("activeForm", content)

            # Choose status indicator and color
            if status == "completed":
                indicator = f"{GREEN}✓{RESET}"
                text = content
            elif status == "in_progress":
                indicator = f"{YELLOW}⟳{RESET}"
                text = active_form
            else:  # pending
                indicator = f"{BLUE}○{RESET}"
                text = content

            lines.append(f"  {indicator} {text}")

        return "\n".join(lines) + "\n"

    def _handle_todo_write(self, todos: list) -> None:
        """Process TodoWrite tool use and update UI state.

        Args:
            todos: List of todo items from TodoWrite tool
        """
        try:
            # LOG ENTRY POINT - Confirm method is called
            self.log(f"🎯 TodoWrite CALLED with {len(todos)} items", level="INFO")

            # Format for terminal display
            formatted = self._format_todos_for_terminal(todos)
            if formatted:
                print(formatted, flush=True)
                self.log("✅ TodoWrite formatted output printed to terminal", level="INFO")
            else:
                self.log("⚠️  TodoWrite formatting returned empty string", level="WARNING")

            # Update message capture state (thread-safe)
            self.message_capture.update_todos(todos)
            self.log("✅ TodoWrite updated message_capture state", level="INFO")

            # Update UI state if enabled (thread-safe)
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_todos(todos)
                self.log("✅ TodoWrite updated UI state", level="INFO")
            else:
                self.log(
                    f"⚠️  TodoWrite UI update skipped (ui_enabled={self.ui_enabled})", level="INFO"
                )

            self.log(f"Updated todo list ({len(todos)} items)", level="DEBUG")

        except Exception as e:
            # Never break conversation flow for todo formatting errors
            self.log(f"Error formatting todos: {e}", level="WARNING")

    def run(self) -> int:
        """Execute agentic loop.

        Routes to async session for Claude SDK or sync session for subprocess-based SDKs.
        """
        # Start UI thread if enabled
        if self.ui_manager:
            self.ui_manager.start_ui_thread()

        try:
            # Detect if using Claude SDK
            if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
                # Use single async event loop for entire session
                return asyncio.run(self._run_async_session())
            # Use subprocess-based sync session
            return self._run_sync_session()
        finally:
            # Always stop UI thread when done
            if self.ui_manager:
                self.ui_manager.stop_ui_thread()

    def _run_sync_session(self) -> int:
        """Execute agentic loop using subprocess-based SDK calls (Copilot/fallback)."""
        self.start_time = time.time()
        self.log(f"Starting auto mode (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        # Transform prompt if needed
        self.prompt = self.prompt_transform.transform_if_needed(self.prompt)

        self.session_manager.run_hook("session_start", self.sdk, self.prompt)

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Clarifying')} Clarify Objective ---")

            philosophy_context = PromptTemplates.build_philosophy_context()
            turn1_prompt = PromptTemplates.build_clarify_prompt(philosophy_context, self.prompt)

            code, objective = self.turn_executor.run_sdk_sync(turn1_prompt)
            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Planning')} Create Plan ---")

            turn2_prompt = PromptTemplates.build_planning_prompt(philosophy_context, objective)

            code, plan = self.turn_executor.run_sdk_sync(turn2_prompt)
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_turn(self.turn)
                self.log(f"\n--- {self._progress_str('Executing')} Execute ---")

                # Check for new instructions
                new_instructions = self.session_manager.check_for_new_instructions()

                # Execute
                execute_prompt = PromptTemplates.build_execution_prompt(
                    philosophy_context, plan, objective, turn, self.max_turns, new_instructions
                )

                code, execution_output = self.turn_executor.run_sdk_sync(execute_prompt)
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")
                eval_prompt = PromptTemplates.build_evaluation_prompt(
                    philosophy_context, objective, turn, self.max_turns
                )

                code, eval_result = self.turn_executor.run_sdk_sync(eval_prompt)

                # Check completion
                eval_lower = eval_result.lower()
                if (
                    "auto-mode evaluation: complete" in eval_lower
                    or "objective achieved" in eval_lower
                    or "all criteria met" in eval_lower
                ):
                    self.log("✓ Objective achieved!")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

            # Summary
            self.log(f"\n--- {self._progress_str('Summarizing')} Summary ---")
            summary_prompt = PromptTemplates.build_summary_prompt(self.turn, objective)

            code, summary = self.turn_executor.run_sdk_sync(summary_prompt)
            if code == 0:
                print(summary)
            else:
                self.log(f"Warning: Summary generation failed (exit {code})")

        finally:
            self.session_manager.run_hook("stop", self.sdk)

        return 0

    async def _run_async_session(self) -> int:
        """Execute agentic loop using Claude SDK in single async event loop."""
        self.start_time = time.time()
        self.fork_manager.start_time = self.start_time
        self.turn_executor.set_session_limits(self.start_time, 3600)  # 1 hour max

        self.log(f"Starting auto mode with Claude SDK (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        # Transform prompt if needed
        self.prompt = self.prompt_transform.transform_if_needed(self.prompt)

        self.session_manager.run_hook("session_start", self.sdk, self.prompt)

        # Initialize options for potential forking
        options = ClaudeAgentOptions(
            cwd=str(self.working_dir),
            permission_mode="bypassPermissions",
            allowed_tools=["TodoWrite"],
        )

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            self.message_capture.set_phase("clarifying", self.turn)
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Clarifying')} Clarify Objective ---")

            philosophy_context = PromptTemplates.build_philosophy_context()
            turn1_prompt = PromptTemplates.build_clarify_prompt(philosophy_context, self.prompt)

            code, objective = await self.turn_executor.run_turn_with_retry(turn1_prompt, max_retries=3)
            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            self.message_capture.set_phase("planning", self.turn)
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Planning')} Create Plan ---")

            turn2_prompt = PromptTemplates.build_planning_prompt(philosophy_context, objective)

            code, plan = await self.turn_executor.run_turn_with_retry(turn2_prompt, max_retries=3)
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn

                # Check if fork needed
                if self.fork_manager.should_fork():
                    elapsed = self.fork_manager.get_elapsed_time()
                    self.log(
                        f"⚠️  Session approaching 60-minute limit ({self._format_elapsed(elapsed)}), forking..."
                    )

                    # Export current session state before fork
                    self._export_session_transcript()

                    # Accumulate session time before fork
                    self.total_session_time += elapsed

                    # Trigger SDK fork and get new options
                    options = self.fork_manager.trigger_fork(options)
                    self.fork_manager.reset()
                    self.log(f"✓ Session forked (Fork {self.fork_manager.get_fork_count()})")

                    # Clear message capture for new fork
                    self.message_capture.clear()

                self.message_capture.set_phase("executing", self.turn)
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_turn(self.turn)
                self.log(f"\n--- {self._progress_str('Executing')} Execute ---")

                # Check for new instructions
                new_instructions = self.session_manager.check_for_new_instructions()

                # Execute
                execute_prompt = PromptTemplates.build_execution_prompt(
                    philosophy_context, plan, objective, turn, self.max_turns, new_instructions
                )

                code, execution_output = await self.turn_executor.run_turn_with_retry(
                    execute_prompt, max_retries=3
                )
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                self.message_capture.set_phase("evaluating", self.turn)
                self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")

                eval_prompt = PromptTemplates.build_evaluation_prompt(
                    philosophy_context, objective, turn, self.max_turns
                )

                code, eval_result = await self.turn_executor.run_turn_with_retry(
                    eval_prompt, max_retries=3
                )

                # Check completion
                eval_lower = eval_result.lower()
                if (
                    "auto-mode evaluation: complete" in eval_lower
                    or "objective achieved" in eval_lower
                    or "all criteria met" in eval_lower
                ):
                    self.log("✓ Objective achieved!")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

            # Summary
            self.message_capture.set_phase("summarizing", self.turn)
            self.log(f"\n--- {self._progress_str('Summarizing')} Summary ---")

            summary_prompt = PromptTemplates.build_summary_prompt(self.turn, objective)

            code, summary = await self.turn_executor.run_turn_with_retry(
                summary_prompt, max_retries=2
            )
            if code == 0:
                print(summary)
            else:
                self.log(f"Warning: Summary generation failed (exit {code})")

        finally:
            # Export session transcript before stop hook
            self._export_session_transcript()
            self.session_manager.run_hook("stop", self.sdk)

        return 0

    def _export_session_transcript(self) -> None:
        """Export session transcript using TranscriptExporter."""
        messages = self.message_capture.get_messages()

        if not messages:
            self.log("No messages captured for export", "DEBUG")
            return

        # Calculate total duration across all forks
        total_duration = self.total_session_time + (time.time() - self.start_time)

        # Build comprehensive metadata
        metadata = {
            "sdk": self.sdk,
            "total_turns": self.turn,
            "fork_count": self.fork_manager.get_fork_count(),
            "total_duration_seconds": total_duration,
            "total_duration_formatted": self._format_elapsed(total_duration),
            "max_turns": self.max_turns,
            "session_id": self.log_dir.name,
        }

        # Export using transcript exporter
        self.transcript_exporter.export_session(messages, metadata)
