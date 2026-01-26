"""Auto mode - agentic loop orchestrator."""

import asyncio
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
from contextlib import nullcontext
from pathlib import Path

# pty is Unix-only, not available on Windows
if platform.system() != "Windows":
    import pty
else:
    pty = None

# Try to import Claude SDK, fall back gracefully
try:
    from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False

# Try to import Rich for markdown rendering
try:
    from rich.console import Console
    from rich.markdown import Markdown

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Markdown = None

# Import session management components
from amplihack.launcher.completion_signals import CompletionSignalDetector
from amplihack.launcher.completion_verifier import CompletionVerifier
from amplihack.launcher.fork_manager import ForkManager
from amplihack.launcher.json_logger import JsonLogger
from amplihack.launcher.session_capture import MessageCapture
from amplihack.launcher.work_summary import WorkSummaryGenerator

# Security constants for content sanitization
MAX_INJECTED_CONTENT_SIZE = 50 * 1024  # 50KB limit for injected content
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+all\s+prior",
    r"forget\s+everything",
    r"new\s+instructions:",
    r"system\s+prompt:",
    r"you\s+are\s+now",
    r"override\s+all",
]


def _sanitize_injected_content(content: str) -> str:
    """Sanitize content before injecting into prompts.

    Args:
        content: Content to sanitize

    Returns:
        Sanitized content (truncated and with suspicious patterns removed)
    """
    if not content:
        return content

    # Truncate if too large
    if len(content.encode("utf-8")) > MAX_INJECTED_CONTENT_SIZE:
        # Truncate to size limit with warning
        content = content[: MAX_INJECTED_CONTENT_SIZE // 2]  # UTF-8 safe truncation
        content += "\n\n[Content truncated due to size limit]"

    # Remove prompt injection patterns
    content_lower = content.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, content_lower, re.IGNORECASE):
            # Replace suspicious patterns with safe marker
            content = re.sub(
                pattern,
                "[REDACTED: suspicious pattern]",
                content,
                flags=re.IGNORECASE,
            )

    return content


class AutoMode:
    """Simple agentic loop orchestrator for Claude, Copilot, or Codex."""

    def __init__(
        self,
        sdk: str = "claude",
        prompt: str = None,
        max_turns: int = 10,
        working_dir: Path | None = None,
        ui_mode: bool = False,
        query_timeout_minutes: float | None = 30.0,
        task: str = None,  # Alias for prompt (for testing)
    ):
        """Initialize auto mode.

        Args:
            sdk: "claude", "copilot", or "codex" (default "claude")
            prompt: User's initial prompt
            max_turns: Max iterations (default 10)
            working_dir: Working directory (defaults to current dir)
            ui_mode: Enable interactive UI mode (requires Rich library)
            query_timeout_minutes: Timeout for each SDK query in minutes (default 30.0).
                None disables timeout. Opus detection is handled by cli.py:resolve_timeout().
            task: Alias for prompt (for testing)
        """
        # Handle task alias
        if task is not None and prompt is None:
            prompt = task
        if prompt is None:
            prompt = "Test prompt"  # Default for testing
        # Ensure UTF-8 encoding for stdout/stderr on Windows
        if sys.platform == "win32":
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.turn = 0
        self.start_time = 0.0  # Will be set when run() starts
        self.working_dir = working_dir if working_dir is not None else Path.cwd()
        self.ui_enabled = ui_mode
        self.ui = None

        # Handle timeout: None means no timeout, otherwise validate
        if query_timeout_minutes is None:
            # No timeout - used for --no-timeout flag
            self.query_timeout_seconds: float | None = None
        else:
            # Validate positive timeout
            if query_timeout_minutes <= 0:
                raise ValueError(
                    f"query_timeout_minutes must be positive, got {query_timeout_minutes}"
                )
            if query_timeout_minutes > 120:  # 2 hours max - warn but allow
                print(
                    f"Warning: Very long timeout ({query_timeout_minutes} minutes)", file=sys.stderr
                )

            self.query_timeout_seconds = query_timeout_minutes * 60.0  # Keep as float for precision
        self.log_dir = (
            self.working_dir / ".claude" / "runtime" / "logs" / f"auto_{sdk}_{int(time.time())}"
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Session management components
        self.message_capture = MessageCapture()
        self.fork_manager = ForkManager(start_time=0, fork_threshold=3600)  # 60 minutes
        self.total_session_time = 0.0  # Cumulative duration across forks

        # Enhanced evaluation components
        self.work_summary_generator = WorkSummaryGenerator()
        self.completion_detector = CompletionSignalDetector(completion_threshold=0.8)
        self.completion_verifier = CompletionVerifier(completion_threshold=0.8)

        # Turn duration tracking
        self.turn_durations = []  # Track all turn durations

        # JSON logger for structured event logging
        self.json_logger = JsonLogger(self.log_dir)

        # Create directories for prompt injection feature
        self.append_dir = self.log_dir / "append"
        self.appended_dir = self.log_dir / "appended"
        self.append_dir.mkdir(parents=True, exist_ok=True)
        self.appended_dir.mkdir(parents=True, exist_ok=True)

        # Write original prompt to prompt.md
        with open(self.log_dir / "prompt.md", "w") as f:
            f.write(f"# Original Auto Mode Prompt\n\n{prompt}\n\n---\n\n")
            f.write(f"**Session Started**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**SDK**: {sdk}\n")
            f.write(f"**Max Turns**: {max_turns}\n")

        # Security: Session-level limits to prevent resource exhaustion
        self.total_api_calls = 0
        self.max_total_api_calls = 50  # Max API calls per session
        self.max_session_duration = 3600  # 1 hour max
        self.session_output_size = 0
        self.max_session_output = 50 * 1024 * 1024  # 50MB total session output

        # Initialize Rich console for markdown rendering
        if RICH_AVAILABLE:
            # Create console with UTF-8 encoding and markup enabled
            self.console = Console(
                file=sys.stdout,
                force_terminal=True,
                markup=True,
                force_interactive=False,
                no_color=False,
                legacy_windows=False,
            )
        else:
            self.console = None

        # Safety: Detect if we're using temp staging directory (safety feature)
        # Check both legacy AMPLIHACK_STAGED_DIR and new AMPLIHACK_IS_STAGED
        self.staged_dir = os.environ.get("AMPLIHACK_STAGED_DIR")
        self.is_staged = os.environ.get("AMPLIHACK_IS_STAGED") == "1"
        self.original_cwd_from_env = os.environ.get("AMPLIHACK_ORIGINAL_CWD")
        self.using_temp_staging = self.staged_dir is not None or self.is_staged

        if self.is_staged:
            self.log("🛡️  Running in staged mode (nested session protection active)")

        # Initialize UI if enabled
        self.ui_thread = None
        if self.ui_enabled:
            try:
                from .auto_mode_state import AutoModeState
                from .auto_mode_ui import AutoModeUI

                # Create shared state with session ID (not PID for security)
                session_id = self.log_dir.name  # Use log directory name as session ID
                self.state = AutoModeState(
                    session_id=session_id,
                    start_time=time.time(),
                    max_turns=max_turns,
                    objective=prompt,
                )

                # Create UI
                self.ui = AutoModeUI(self.state, self, self.working_dir)
            except ImportError as e:
                # Rich should be installed as required dependency
                # If missing, something is wrong with the installation
                print("\n⚠️  ERROR: Rich library required but not found", file=sys.stderr)
                print("   This should not happen - Rich is a required dependency", file=sys.stderr)
                print(f"   Error: {e}", file=sys.stderr)
                print(
                    "\n   Try reinstalling: uvx --from git+https://... amplihack", file=sys.stderr
                )
                print("\n   Continuing in non-UI mode...\n", file=sys.stderr)

                self.log(
                    f"Error: Rich library missing despite being required dependency: {e}",
                    level="ERROR",
                )
                self.ui_enabled = False
                self.ui = None

    def log(self, msg: str, level: str = "INFO"):
        """Log message with optional level."""
        # Only print INFO, WARNING, ERROR to console - skip DEBUG
        if level in ("INFO", "WARNING", "ERROR"):
            print(f"[AUTO {self.sdk.upper()}] {msg}\n", flush=True)

            # Update UI state if enabled (all levels)
            if self.ui_enabled and hasattr(self, "state"):
                self.state.add_log(msg, timestamp=False)

        # Always write to file (including DEBUG)
        with open(self.log_dir / "auto.log", "a", encoding="utf-8") as f:
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

    def run_sdk(self, prompt: str) -> tuple[int, str]:
        """Run SDK command with prompt, choosing method by provider.

        For Claude: Should NOT be called directly - use async path instead
        For Copilot: Use subprocess approach

        Returns:
            (exit_code, output)
        """
        # Claude SDK should use the async session path to maintain single event loop
        if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
            self.log(
                "ERROR: Claude SDK should use _run_async_session(), not run_sdk()", level="ERROR"
            )
            return (1, "Internal error: Claude SDK requires async session mode")
        # Fallback to subprocess for Copilot or if SDK unavailable
        return self._run_sdk_subprocess(prompt)

    def _run_sdk_subprocess(self, prompt: str) -> tuple[int, str]:
        """Run SDK command via subprocess (legacy/copilot mode).

        Returns:
            (exit_code, output)
        """
        if self.sdk == "copilot":
            cmd = ["copilot", "--allow-all-tools", "--add-dir", "/", "-p", prompt]
        elif self.sdk == "codex":
            cmd = ["codex", "--dangerously-bypass-approvals-and-sandbox", "exec", prompt]
        else:
            cmd = ["claude", "--dangerously-skip-permissions", "--verbose", "-p", prompt]

        self.log(f"Running: {cmd[0]} ...")

        # Create a pseudo-terminal for stdin on Unix (not available on Windows)
        # This allows any subprocess (including children) to read from it
        if pty is not None:
            master_fd, slave_fd = pty.openpty()
            stdin_fd = slave_fd
        else:
            # On Windows, use PIPE instead
            master_fd = None
            stdin_fd = subprocess.PIPE

        # Use Popen to capture and mirror output in real-time
        process = subprocess.Popen(
            cmd,
            stdin=stdin_fd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",  # Explicit UTF-8 encoding for proper emoji/unicode support
            errors="replace",  # Replace decode errors instead of crashing
            cwd=self.working_dir,
        )

        # Close slave_fd in parent process (child has a copy) - Unix only
        if pty is not None:
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
            # Only run this on Unix where pty is available
            if fd is None:
                return
            try:
                while proc.poll() is None:
                    time.sleep(0.1)  # Check every 100ms
                    try:
                        os.write(fd, b"\n")
                    except (BrokenPipeError, OSError):
                        # Process closed or pty closed
                        break
            except KeyboardInterrupt:
                # Allow clean shutdown on Ctrl+C
                pass
            except Exception as e:
                # Log unexpected errors for debugging
                self.log(f"PTY stdin feed error: {e}", level="WARNING")
            finally:
                try:
                    os.close(fd)
                except (OSError, ValueError):
                    # File descriptor already closed or invalid
                    pass
                except Exception as e:
                    # Log any other unexpected cleanup errors
                    self.log(f"PTY cleanup error: {e}", level="WARNING")

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

        # Log stdout if present (FULL output per user requirement)
        if stdout_output:
            self.log(f"stdout ({len(stdout_output)} chars): {stdout_output}")

        # Log stderr if present (FULL output per user requirement)
        if stderr_output:
            self.log(f"stderr ({len(stderr_output)} chars): {stderr_output}")

        return process.returncode, stdout_output

    def _check_for_new_instructions(self) -> str:
        """Check append directory for new instruction files and process them.

        Returns:
            String containing all new instructions (sanitized), or empty string if none.
        """
        new_instructions = []

        # Get all .md files in append directory
        md_files = sorted(self.append_dir.glob("*.md"))

        if not md_files:
            return ""

        self.log(f"Found {len(md_files)} new instruction file(s) to process")

        for md_file in md_files:
            try:
                # Read the instruction file
                with open(md_file) as f:
                    content = f.read()

                # Sanitize content before injection
                sanitized_content = _sanitize_injected_content(content)

                timestamp = md_file.stem
                new_instructions.append(
                    f"\n## Additional Instruction (appended at {timestamp})\n\n{sanitized_content}\n"
                )

                # Move file to appended directory
                target_path = self.appended_dir / md_file.name
                md_file.rename(target_path)
                self.log(f"Processed and archived: {md_file.name}")

            except Exception as e:
                self.log(f"Error processing {md_file.name}: {e}", level="ERROR")

        if new_instructions:
            return "\n".join(new_instructions)
        return ""

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

    def _build_evaluation_prompt(self, message_capture) -> str:
        """Build evaluation prompt with work summary injection.

        Args:
            message_capture: MessageCapture instance

        Returns:
            Evaluation prompt string with work summary
        """
        try:
            # Generate work summary
            summary = self.work_summary_generator.generate(message_capture)
            work_summary_text = self.work_summary_generator.format_for_prompt(summary)

            # Detect completion signals
            signals = self.completion_detector.detect(summary)
            signal_explanation = self.completion_detector.explain(signals)

            # Add completion score explicitly (for test compatibility)
            if hasattr(signals, "completion_score"):
                signal_explanation += f"\n\nCompletion score: {signals.completion_score:.1%}"

        except Exception as e:
            # Graceful degradation
            self.log(f"Warning: Work summary generation failed: {e}")
            work_summary_text = "Work summary unavailable (git/GitHub tools may be missing)"
            signal_explanation = ""

        # Build enhanced evaluation prompt
        prompt = f"""{self._build_philosophy_context()}

Task: Evaluate if the objective is achieved based on:
1. All explicit user requirements met
2. Philosophy principles applied (simplicity, modularity, zero-BS)
3. Success criteria from Turn 1 satisfied
4. No placeholders or incomplete implementations remain
5. All work has actually been thoroughly tested and verified
6. The required workflow has been fully executed

{work_summary_text}

{signal_explanation}

Respond with one of:
- "auto-mode EVALUATION: COMPLETE" - All criteria met, objective achieved
- "auto-mode EVALUATION: IN PROGRESS" - Making progress, continue execution
- "auto-mode EVALUATION: NEEDS ADJUSTMENT" - Issues identified, plan adjustment needed

Include brief reasoning for your evaluation. If incomplete, specify next steps or adjustments needed.

Objective:
{self.prompt}

Current Turn: {self.turn}/{self.max_turns}"""

        return prompt

    def _should_continue_loop(self, eval_result: str, message_capture) -> bool:
        """Determine if loop should continue based on verification.

        Returns:
            True if loop should continue, False if it should exit
        """
        try:
            # Generate work summary
            summary = self.work_summary_generator.generate(message_capture)

            # Detect completion signals
            signals = self.completion_detector.detect(summary)

            # Verify completion claim
            verification = self.completion_verifier.verify(eval_result, signals)

            # Log evaluation decision details
            self.log("=" * 70, level="INFO")
            self.log(f"[EVAL] Turn {self.turn} Evaluation Decision", level="INFO")
            self.log("-" * 70, level="INFO")

            # Work summary
            self.log("Work Summary:", level="INFO")
            self.log(
                f"  Workflow: {summary.todo_state.completed}/{summary.todo_state.total} steps",
                level="INFO",
            )
            self.log(
                f"  Git: {summary.git_state.current_branch}, commits={summary.git_state.commits_ahead}",
                level="INFO",
            )
            if summary.github_state.pr_number:
                self.log(
                    f"  GitHub: PR#{summary.github_state.pr_number}, CI={summary.github_state.ci_status}, mergeable={summary.github_state.pr_mergeable}",
                    level="INFO",
                )

            # Completion signals
            self.log("", level="INFO")
            self.log("Completion Signals:", level="INFO")
            self.log(f"  ✓/✗ pr_created: {signals.pr_created}", level="INFO")
            self.log(f"  ✓/✗ ci_passing: {signals.ci_passing}", level="INFO")
            self.log(f"  ✓/✗ all_steps_complete: {signals.all_steps_complete}", level="INFO")
            self.log(f"  ✓/✗ pr_mergeable: {signals.pr_mergeable}", level="INFO")

            # Score and decision
            self.log("", level="INFO")
            self.log(
                f"Completion Score: {signals.completion_score:.1%} (threshold: 80%)", level="INFO"
            )
            self.log(f"Verification: {verification.status.value}", level="INFO")

            # Determine should_continue before logging final decision
            should_continue = True
            if verification.verified:
                # Verification passed - check what was claimed
                eval_lower = eval_result.lower()
                if "auto-mode evaluation: complete" in eval_lower:
                    should_continue = False  # Exit loop - task complete
                else:
                    # Verified incomplete status - continue working
                    should_continue = True
            else:
                # Disputed completion - continue
                should_continue = True

            # Final decision
            decision = (
                "EXIT LOOP (task complete)" if not should_continue else "CONTINUE (work remaining)"
            )
            self.log(f"Decision: {decision}", level="INFO")
            self.log("=" * 70, level="INFO")

            # Additional legacy logging for disputed completion
            if not verification.verified:
                self.log(f"⚠️  Completion claim disputed: {verification.explanation}")
                if verification.discrepancies:
                    self.log("Missing signals:")
                    for discrepancy in verification.discrepancies[:3]:  # Show top 3
                        self.log(f"  - {discrepancy}")
                self.log("Continuing loop to complete remaining work...")
            elif not should_continue:
                self.log("✓ Completion verified by concrete signals")

            return should_continue

        except Exception as e:
            self.log(f"Warning: Verification failed, falling back to text parsing: {e}")
            # Fallback to old behavior
            eval_lower = eval_result.lower()
            return "auto-mode evaluation: complete" not in eval_lower

    def _get_verification_feedback(self, eval_result: str, verification) -> str:
        """Get feedback message for disputed completion.

        Args:
            eval_result: Evaluation result text
            verification: VerificationResult

        Returns:
            Feedback message
        """
        return self.completion_verifier.format_report(verification)

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

    async def _run_turn_with_sdk(self, prompt: str) -> tuple[int, str]:
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
            print("\n[DEBUG] 🚀 START _run_turn_with_sdk", flush=True)
            self.log("Using Claude SDK (streaming mode)")
            output_lines = []
            turn_output_size = 0
            MAX_TURN_OUTPUT = 10 * 1024 * 1024  # 10MB per turn limit

            # Capture user message for transcript
            self.message_capture.capture_user_message(prompt)

            # Configure SDK options
            options = ClaudeAgentOptions(
                cwd=str(self.working_dir),
                permission_mode="bypassPermissions",  # Auto mode needs non-interactive permissions
                allowed_tools=["TodoWrite"],  # Enable TodoWrite for progress tracking
                # Note: verbose flag can be added via extra_args if needed
            )

            # Stream response - messages are typed objects, not dicts
            print("\n[DEBUG] 🔄 Starting async for message loop", flush=True)

            # Track turn start time for accurate timeout reporting
            turn_start_time = time.time()

            # Add timeout wrapper around SDK query (use nullcontext if no timeout)
            timeout_ctx = (
                asyncio.timeout(self.query_timeout_seconds)
                if self.query_timeout_seconds is not None
                else nullcontext()
            )
            async with timeout_ctx:
                async for message in query(prompt=prompt, options=options):
                    print("\n[DEBUG] 💬 Got a message from query()", flush=True)
                    # Handle different message types
                    if hasattr(message, "__class__"):
                        msg_type = message.__class__.__name__
                        print(
                            f"\n[DEBUG] 📨 Message type: {msg_type}", flush=True
                        )  # Direct print to bypass log()
                        self.log(f"📨 Received message type: {msg_type}", level="INFO")

                        if msg_type == "AssistantMessage":
                            # Capture assistant message for transcript
                            self.message_capture.capture_assistant_message(message)

                            # Process content blocks
                            for block in getattr(message, "content", []):
                                block_type = getattr(block, "type", "unknown")
                                self.log(f"  📦 Block type: {block_type}", level="INFO")

                                # Handle text blocks
                                if hasattr(block, "text"):
                                    text = block.text

                                    # Security: Check output size limits
                                    text_size = len(text.encode("utf-8"))
                                    turn_output_size += text_size
                                    self.session_output_size += text_size

                                    if turn_output_size > MAX_TURN_OUTPUT:
                                        self.log(
                                            f"Turn output size limit exceeded ({turn_output_size} bytes)",
                                            level="ERROR",
                                        )
                                        return (1, "Turn output too large")

                                    if self.session_output_size > self.max_session_output:
                                        self.log(
                                            f"Session output limit exceeded ({self.session_output_size} bytes)",
                                            level="ERROR",
                                        )
                                        return (1, "Session output too large")

                                    # Render markdown for Claude SDK output if Rich is available
                                    if self.console is not None:
                                        try:
                                            md = Markdown(text)
                                            self.console.print(md, end="")
                                            sys.stdout.flush()
                                        except Exception:
                                            # Fallback to plain text if markdown rendering fails
                                            print(text, end="", flush=True)
                                    else:
                                        # No Rich available, print plain text
                                        print(text, end="", flush=True)
                                    output_lines.append(text)

                                # Handle tool_use blocks (TodoWrite)
                                elif hasattr(block, "type") and block.type == "tool_use":
                                    tool_name = getattr(block, "name", None)
                                    self.log(
                                        f"🔍 Detected tool_use block: {tool_name}", level="INFO"
                                    )

                                    # Log agent invocation (any tool_use indicates agent activity)
                                    if tool_name:
                                        self.json_logger.log_event(
                                            "agent_invoked", {"agent": tool_name, "turn": self.turn}
                                        )

                                    if tool_name == "TodoWrite":
                                        self.log("🎯 TodoWrite tool detected!", level="INFO")
                                        # Extract todos from input object (not dict!)
                                        # block.input is an object with attributes, not a dict
                                        if hasattr(block, "input"):
                                            tool_input = block.input
                                            self.log(
                                                f"✓ Block has input attribute, type: {type(tool_input)}",
                                                level="INFO",
                                            )

                                            # Check if input has todos attribute
                                            if hasattr(tool_input, "todos"):
                                                todos = tool_input.todos
                                                self.log(
                                                    f"✓ Input has todos attribute with {len(todos)} items",
                                                    level="INFO",
                                                )
                                                self._handle_todo_write(todos)
                                            # Fallback: try dict-style access for backwards compatibility
                                            elif (
                                                isinstance(tool_input, dict)
                                                and "todos" in tool_input
                                            ):
                                                todos = tool_input["todos"]
                                                self.log(
                                                    f"✓ Input is dict with todos key ({len(todos)} items)",
                                                    level="INFO",
                                                )
                                                self._handle_todo_write(todos)
                                            else:
                                                self.log(
                                                    f"⚠️  Input has no todos attribute or key. Attributes: {dir(tool_input)}",
                                                    level="WARNING",
                                                )
                                        else:
                                            self.log(
                                                "⚠️  Block has no input attribute", level="WARNING"
                                            )

                        elif msg_type == "ResultMessage":
                            # Check if there was an error
                            if getattr(message, "is_error", False):
                                error_result = getattr(message, "result", "Unknown error")
                                self.log(f"SDK error: {error_result}", level="ERROR")
                                return (1, "".join(output_lines))

                        # SystemMessage and other types are informational - skip

            # Success
            full_output = "".join(output_lines)

            # Log output if present (FULL output per user requirement)
            if full_output:
                self.log(f"stdout ({len(full_output)} chars): {full_output}")

            return (0, full_output)

        except TimeoutError:
            # Timeout handling with turn context
            turn_elapsed = time.time() - turn_start_time
            partial_output = "".join(output_lines)
            error_msg = (
                f"Turn {self.turn} timed out after {turn_elapsed:.1f}s "
                f"(limit: {self.query_timeout_seconds:.1f}s). "
                f"Try reducing task complexity or increasing --query-timeout-minutes."
            )
            self.log(error_msg, level="ERROR")

            # Log error event
            self.json_logger.log_event(
                "error",
                {"turn": self.turn, "error_type": "timeout", "message": error_msg},
                level="ERROR",
            )

            if partial_output:
                self.log(f"Partial output captured ({len(partial_output)} chars)", level="INFO")
            return (1, partial_output if partial_output else error_msg)

        except GeneratorExit:
            # Graceful generator cleanup - this is expected during async cleanup
            self.log("Async generator cleanup (normal)", level="DEBUG")
            return (0, "".join(output_lines) if output_lines else "")
        except RuntimeError as e:
            # Catch cancel scope errors specifically - these occur during normal async cleanup
            if "cancel scope" in str(e).lower():
                self.log("Async cleanup complete (task coordination)", level="DEBUG")
                # Don't propagate - this is expected during graceful shutdown
                return (0, "".join(output_lines) if output_lines else "")
            # Re-raise other RuntimeErrors
            raise
        except Exception as e:
            # Enhanced existing exception handling with turn context
            error_msg = f"Turn {self.turn} SDK error: {type(e).__name__}: {e}"
            self.log(error_msg, level="ERROR")
            import traceback

            self.log(f"Traceback: {traceback.format_exc()}", level="ERROR")

            # Log error event
            self.json_logger.log_event(
                "error",
                {"turn": self.turn, "error_type": type(e).__name__, "message": str(e)},
                level="ERROR",
            )

            return (1, f"SDK Error: {e!s}")

    def _is_retryable_error(self, error_text: str) -> bool:
        """Check if error is transient and should be retried.

        Args:
            error_text: Error message text

        Returns:
            True if error is retryable (500, 429, 503, timeout, overloaded)
        """
        error_lower = error_text.lower()
        retryable_patterns = [
            "overloaded",
            "rate limit",
            "503",
            "500",
            "timeout",
            "service unavailable",
            "too many requests",
            "429",
        ]
        return any(pattern in error_lower for pattern in retryable_patterns)

    async def _run_turn_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> tuple[int, str]:
        """Execute turn with retry on transient errors.

        Implements exponential backoff for transient API errors (500, 429, 503).
        Permanent errors (400, 401, 403) fail immediately without retry.

        Args:
            prompt: The prompt for this turn
            max_retries: Maximum retry attempts (default 3)
            base_delay: Base delay for exponential backoff in seconds (default 2.0s)

        Returns:
            (exit_code, output_text)
        """
        # Security: Check session limits before attempting turn
        if self.total_api_calls >= self.max_total_api_calls:
            self.log(f"Session limit reached ({self.max_total_api_calls} API calls)", level="ERROR")
            return (1, "Session limit exceeded - too many API calls")

        elapsed = time.time() - self.start_time
        if elapsed > self.max_session_duration:
            self.log(f"Session duration limit reached ({elapsed:.0f}s)", level="ERROR")
            return (1, "Session timeout - maximum duration exceeded")

        for attempt in range(max_retries + 1):
            self.total_api_calls += 1  # Track API call count
            code, output = await self._run_turn_with_sdk(prompt)

            if code == 0:
                # Success - return immediately
                return (code, output)

            # Check if error is retryable
            if self._is_retryable_error(output):
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)  # Exponential backoff: 2s, 4s, 8s
                    self.log(
                        f"Retryable error detected (attempt {attempt + 1}/{max_retries + 1}), "
                        f"waiting {delay:.1f}s before retry..."
                    )
                    await asyncio.sleep(delay)
                    continue
                self.log(f"Max retries ({max_retries}) exceeded for transient error")

            # Non-retryable error or max retries exceeded
            return (code, output)

        return (code, output)

    def run_hook(self, hook: str):
        """Run hook for copilot and codex (Claude SDK handles hooks automatically)."""
        if self.sdk not in ["copilot", "codex"]:
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

    def _start_ui_thread(self) -> None:
        """Start UI in a separate thread if UI mode is enabled."""
        if not self.ui_enabled or not self.ui:
            return

        def ui_runner():
            """Thread target to run the UI."""
            try:
                if self.ui is not None:
                    self.ui.run()
            except Exception as e:
                self.log(f"UI thread error: {e}", level="ERROR")

        self.ui_thread = threading.Thread(
            target=ui_runner,
            daemon=False,  # Not daemon - we want to wait for it
            name="AutoModeUI",
        )
        self.ui_thread.start()
        self.log("UI thread started")

    def _stop_ui_thread(self) -> None:
        """Stop UI thread and wait for it to finish."""
        if not self.ui_thread:
            return

        # Wait for UI thread to finish (with timeout)
        self.ui_thread.join(timeout=5.0)
        if self.ui_thread.is_alive():
            self.log("Warning: UI thread did not stop cleanly", level="WARNING")
        else:
            self.log("UI thread stopped")

    def run(self) -> int:
        """Execute agentic loop.

        Routes to async session for Claude SDK or sync session for subprocess-based SDKs.
        """
        # Start UI thread if enabled
        self._start_ui_thread()

        try:
            # Detect if using Claude SDK
            if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
                # Use single async event loop for entire session
                return asyncio.run(self._run_async_session())
            # Use subprocess-based sync session
            return self._run_sync_session()
        finally:
            # Always stop UI thread when done
            self._stop_ui_thread()

    def _run_sync_session(self) -> int:
        """Execute agentic loop using subprocess-based SDK calls (Copilot/fallback)."""
        self.start_time = time.time()
        self.log(f"Starting auto mode (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        # Safety: Transform prompt if using temp staging (safety feature)
        if self.using_temp_staging and self.original_cwd_from_env:
            from amplihack.safety import PromptTransformer

            transformer = PromptTransformer()
            self.prompt = transformer.transform_prompt(
                original_prompt=self.prompt,
                target_directory=self.original_cwd_from_env,
                used_temp=True,
            )
            self.log(f"Transformed prompt for temp staging (target: {self.original_cwd_from_env})")

        self.run_hook("session_start")

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Clarifying')} Clarify Objective ---")
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
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)
            self.log(f"\n--- {self._progress_str('Planning')} Create Plan ---")
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
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                turn_start_time = time.time()  # Track turn start time
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_turn(self.turn)
                self.log(f"\n--- {self._progress_str('Executing')} Execute ---")

                # Check for new instructions before executing
                new_instructions = self._check_for_new_instructions()

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
{new_instructions}

Current Turn: {turn}/{self.max_turns}"""

                code, execution_output = self.run_sdk(execute_prompt)
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")
                eval_prompt = f"""{self._build_philosophy_context()}

Task: Evaluate if the objective is achieved based on:
1. All explicit user requirements met
2. Philosophy principles applied (simplicity, modularity, zero-BS)
3. Success criteria from Turn 1 satisfied
4. No placeholders or incomplete implementations remain
5. All work has actually been thoroughly tested and verified
6. The required workflow has been fully executed

Respond with one of:
- "auto-mode EVALUATION: COMPLETE" - All criteria met, objective achieved
- "auto-mode EVALUATION: IN PROGRESS" - Making progress, continue execution
- "auto-mode EVALUATION: NEEDS ADJUSTMENT" - Issues identified, plan adjustment needed

Include brief reasoning for your evaluation. If incomplete, specify next steps or adjustments needed.

Objective:
{objective}

Current Turn: {turn}/{self.max_turns}"""

                code, eval_result = self.run_sdk(eval_prompt)

                # Calculate and log turn duration
                turn_duration = time.time() - turn_start_time
                self.turn_durations.append(turn_duration)
                self.log(f"Turn {turn} completed in {turn_duration:.1f}s", level="INFO")

                # Check completion - look for strong completion signals
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

            # Log session metrics
            if self.turn_durations:
                avg_duration = sum(self.turn_durations) / len(self.turn_durations)
                max_duration = max(self.turn_durations)
                total_duration = sum(self.turn_durations)
                self.log(
                    f"Session metrics: {len(self.turn_durations)} turns, "
                    f"avg {avg_duration:.1f}s, max {max_duration:.1f}s, "
                    f"total {total_duration:.1f}s",
                    level="INFO",
                )

            # Summary - display it directly
            self.log(f"\n--- {self._progress_str('Summarizing')} Summary ---")
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

    async def _run_async_session(self) -> int:
        """Execute agentic loop using Claude SDK in single async event loop.

        This maintains a single event loop for the entire session, preventing
        the "cancel scope in different task" error that occurs when repeatedly
        calling asyncio.run() for each turn.
        """
        self.start_time = time.time()
        self.fork_manager.start_time = self.start_time  # Initialize fork manager timer
        self.log(f"Starting auto mode with Claude SDK (max {self.max_turns} turns)")
        self.log(f"Prompt: {self.prompt}")

        # Safety: Transform prompt if using temp staging (safety feature)
        if self.using_temp_staging and self.original_cwd_from_env:
            from amplihack.safety import PromptTransformer

            transformer = PromptTransformer()
            self.prompt = transformer.transform_prompt(
                original_prompt=self.prompt,
                target_directory=self.original_cwd_from_env,
                used_temp=True,
            )
            self.log(f"Transformed prompt for temp staging (target: {self.original_cwd_from_env})")

        self.run_hook("session_start")

        # Initialize options for potential forking
        options = ClaudeAgentOptions(
            cwd=str(self.working_dir),
            permission_mode="bypassPermissions",
            allowed_tools=["TodoWrite"],  # Enable TodoWrite for progress tracking
        )

        try:
            # Turn 1: Clarify objective
            self.turn = 1
            self.message_capture.set_phase("clarifying", self.turn)  # Set phase for message capture
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)

            # Log turn start event
            self.json_logger.log_event(
                "turn_start",
                {"turn": self.turn, "phase": "clarifying", "max_turns": self.max_turns},
            )

            self.log(f"\n--- {self._progress_str('Clarifying')} Clarify Objective ---")
            turn1_prompt = f"""{self._build_philosophy_context()}

Task: Analyze this user request and clarify the objective with evaluation criteria.

1. IDENTIFY EXPLICIT REQUIREMENTS: Extract any "must have", "all", "include everything", quoted specifications
2. IDENTIFY IMPLICIT PREFERENCES: What user likely wants based on @.claude/context/USER_PREFERENCES.md
3. APPLY PHILOSOPHY: Ruthless simplicity from @.claude/context/PHILOSOPHY.md, modular design, zero-BS implementation
4. DEFINE SUCCESS CRITERIA: Clear, measurable, aligned with philosophy

User Request:
{self.prompt}"""

            turn_start_time = time.time()
            code, objective = await self._run_turn_with_retry(turn1_prompt, max_retries=3)
            turn_duration = time.time() - turn_start_time

            # Log turn complete event
            self.json_logger.log_event(
                "turn_complete",
                {"turn": self.turn, "duration_sec": round(turn_duration, 2), "success": code == 0},
            )

            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turn 2: Create plan
            self.turn = 2
            self.message_capture.set_phase("planning", self.turn)  # Set phase for message capture
            if self.ui_enabled and hasattr(self, "state"):
                self.state.update_turn(self.turn)

            # Log turn start event
            self.json_logger.log_event(
                "turn_start", {"turn": self.turn, "phase": "planning", "max_turns": self.max_turns}
            )

            self.log(f"\n--- {self._progress_str('Planning')} Create Plan ---")
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

            turn_start_time = time.time()
            code, plan = await self._run_turn_with_retry(turn2_prompt, max_retries=3)
            turn_duration = time.time() - turn_start_time

            # Log turn complete event
            self.json_logger.log_event(
                "turn_complete",
                {"turn": self.turn, "duration_sec": round(turn_duration, 2), "success": code == 0},
            )

            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_status("error")
                return 1

            # Turns 3+: Execute and evaluate
            for turn in range(3, self.max_turns + 1):
                self.turn = turn
                turn_start_time = time.time()  # Track turn start time

                # Check if fork needed before turn execution
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

                    # Clear message capture for new fork (fresh start)
                    self.message_capture.clear()

                self.message_capture.set_phase(
                    "executing", self.turn
                )  # Set phase for message capture
                if self.ui_enabled and hasattr(self, "state"):
                    self.state.update_turn(self.turn)

                # Log turn start event
                self.json_logger.log_event(
                    "turn_start",
                    {"turn": self.turn, "phase": "executing", "max_turns": self.max_turns},
                )

                self.log(f"\n--- {self._progress_str('Executing')} Execute ---")

                # Check for new instructions before executing
                new_instructions = self._check_for_new_instructions()

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
{new_instructions}

Current Turn: {turn}/{self.max_turns}"""

                turn_start_time = time.time()
                code, execution_output = await self._run_turn_with_retry(
                    execute_prompt, max_retries=3
                )
                turn_duration = time.time() - turn_start_time

                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate
                self.message_capture.set_phase(
                    "evaluating", self.turn
                )  # Set phase for message capture
                self.log(f"--- {self._progress_str('Evaluating')} Evaluate ---")
                eval_prompt = self._build_evaluation_prompt(self.message_capture)

                code, eval_result = await self._run_turn_with_retry(eval_prompt, max_retries=3)

                # Calculate and log turn duration
                turn_duration = time.time() - turn_start_time
                self.turn_durations.append(turn_duration)
                self.log(f"Turn {turn} completed in {turn_duration:.1f}s", level="INFO")

                # Log turn complete event (after evaluation)
                self.json_logger.log_event(
                    "turn_complete",
                    {
                        "turn": self.turn,
                        "duration_sec": round(turn_duration, 2),
                        "success": code == 0,
                    },
                )

                # Check completion with verification
                if not self._should_continue_loop(eval_result, self.message_capture):
                    self.log("✓ Objective achieved!")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    if self.ui_enabled and hasattr(self, "state"):
                        self.state.update_status("completed")
                    break

            # Log session metrics
            if self.turn_durations:
                avg_duration = sum(self.turn_durations) / len(self.turn_durations)
                max_duration = max(self.turn_durations)
                total_duration = sum(self.turn_durations)
                self.log(
                    f"Session metrics: {len(self.turn_durations)} turns, "
                    f"avg {avg_duration:.1f}s, max {max_duration:.1f}s, "
                    f"total {total_duration:.1f}s",
                    level="INFO",
                )

            # Summary - display it directly
            self.message_capture.set_phase(
                "summarizing", self.turn
            )  # Set phase for message capture
            self.log(f"\n--- {self._progress_str('Summarizing')} Summary ---")
            code, summary = await self._run_turn_with_retry(
                f"Summarize auto mode session:\nTurns: {self.turn}\nObjective: {objective}",
                max_retries=2,  # Fewer retries for summary (less critical)
            )
            if code == 0:
                print(summary)
            else:
                self.log(f"Warning: Summary generation failed (exit {code})")

        finally:
            # Export session transcript before stop hook
            self._export_session_transcript()

            self.run_hook("stop")

        return 0

    def _export_session_transcript(self) -> None:
        """Export session transcript using ClaudeTranscriptBuilder.

        Creates comprehensive transcript files in multiple formats (markdown, JSON, codex)
        using the captured messages from the session.
        """
        try:
            # Import builder using importlib - works in both UVX and local dev
            import importlib.util
            from pathlib import Path

            # Search paths for builders directory
            search_paths = []

            # Path 1: UVX package location
            try:
                import amplihack

                # Security: Use strict=True to prevent symlink attacks
                pkg_path = Path(amplihack.__file__).parent.resolve(strict=True)
                builders_in_pkg = (
                    pkg_path / ".claude" / "tools" / "amplihack" / "builders"
                ).resolve(strict=True)

                # Security: Validate path is within expected package
                if not str(builders_in_pkg).startswith(str(pkg_path)):
                    self.log("Security: Builders path validation failed in UVX", level="DEBUG")
                    raise ValueError("Path traversal detected")

                if builders_in_pkg.exists():
                    search_paths.append(builders_in_pkg)
            except (ValueError, OSError) as e:
                self.log(f"Path validation failed in UVX: {type(e).__name__}", level="DEBUG")
            except Exception:
                pass

            # Path 2: Project root (local development)
            try:
                # Security: Resolve and validate project root
                current_file = Path(__file__).resolve(strict=True)
                project_root = current_file.parent.parent.parent.parent
                builders_in_root = (
                    project_root / ".claude" / "tools" / "amplihack" / "builders"
                ).resolve(strict=True)

                # Security: Ensure builders path is under project root
                try:
                    builders_in_root.relative_to(project_root)
                except ValueError:
                    self.log("Security: Path traversal detected in project root", level="DEBUG")
                    raise ValueError("Path traversal detected")

                if builders_in_root.exists():
                    search_paths.append(builders_in_root)
            except (ValueError, OSError) as e:
                self.log(
                    f"Path validation failed in project root: {type(e).__name__}", level="DEBUG"
                )
            except Exception:
                pass

            # Load builder from first valid path
            ClaudeTranscriptBuilder = None
            for builders_path in search_paths:
                try:
                    builder_file = builders_path / "claude_transcript_builder.py"
                    if builder_file.exists():
                        spec = importlib.util.spec_from_file_location(
                            "claude_transcript_builder", builder_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            ClaudeTranscriptBuilder = module.ClaudeTranscriptBuilder
                            self.log(f"Builders: Loaded from {builders_path}", level="DEBUG")
                            break
                except Exception as e:
                    self.log(f"Builders: Failed from {builders_path}: {e}", level="DEBUG")
                    continue

            # Skip export if builder couldn't be loaded
            if ClaudeTranscriptBuilder is None:
                self.log("Transcript builder not found, skipping export", level="INFO")
                return

            builder = ClaudeTranscriptBuilder(
                session_id=self.log_dir.name, working_dir=self.working_dir
            )
            messages = self.message_capture.get_messages()

            if not messages:
                self.log("No messages captured for export", level="DEBUG")
                return

            # Log where transcripts will be exported
            actual_session_dir = builder.session_dir
            self.log(f"Exporting transcripts to: {actual_session_dir}", level="DEBUG")

            # Note: We don't validate path location - transcript export works
            # whether it's in workspace or venv site-packages (remote execution)

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

            # Generate transcript and export
            builder.build_session_transcript(messages, metadata)
            builder.export_for_codex(messages, metadata)

            # Verify files were actually written to expected location
            expected_files = [
                actual_session_dir / "CONVERSATION_TRANSCRIPT.md",
                actual_session_dir / "conversation_transcript.json",
                actual_session_dir / "codex_export.json",
            ]
            missing_files = [f for f in expected_files if not f.exists()]

            if missing_files:
                error_msg = (
                    f"Transcript export verification failed!\n"
                    f"Expected files were not created at {actual_session_dir}:\n"
                    + "\n".join(f"  Missing: {f.name}" for f in missing_files)
                )
                self.log(error_msg, level="ERROR")
                raise FileNotFoundError(error_msg)

            self.log(
                f"✓ Session transcript exported ({len(messages)} messages, {self._format_elapsed(total_duration)})"
            )

        except (ValueError, FileNotFoundError) as e:
            # Path mismatch or file verification failures - these are critical errors
            # Re-raise to fail loudly and alert user to the problem
            self.log(f"Critical transcript export error: {e}", level="ERROR")
            raise
        except (ImportError, AttributeError) as e:
            # Builder loading issues - log but don't crash the session
            self.log(f"Transcript builder unavailable: {e}", level="WARNING")
        except OSError as e:
            # File system errors - these could be transient, log but continue
            self.log(f"File system error during transcript export: {e}", level="WARNING")
        except Exception as e:
            # Unexpected errors - log with full details but don't crash session
            self.log(
                f"Unexpected error during transcript export: {type(e).__name__}: {e}", level="ERROR"
            )
            # In case of unexpected errors, still try to continue the session
            # but make it clear this is an unusual situation
