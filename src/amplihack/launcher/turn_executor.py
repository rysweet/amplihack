"""Turn execution logic for auto mode."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

from amplihack.launcher.pty_manager import PTYManager

# Try to import Claude SDK, fall back gracefully
try:
    from claude_agent_sdk import ClaudeAgentOptions, query  # type: ignore

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False


class TurnExecutor:
    """Handles turn execution for different SDK types."""

    def __init__(
        self,
        sdk: str,
        working_dir: Path,
        log_func: Callable[[str, str], None],
        message_capture: Any,
        todo_handler: Callable[[list], None],
    ):
        """Initialize turn executor.

        Args:
            sdk: SDK type ("claude", "copilot", "codex")
            working_dir: Working directory for execution
            log_func: Logging function(message, level)
            message_capture: MessageCapture instance
            todo_handler: TodoWrite handler function
        """
        self.sdk = sdk
        self.working_dir = working_dir
        self.log = log_func
        self.message_capture = message_capture
        self.todo_handler = todo_handler

        # Security: Session-level limits
        self.total_api_calls = 0
        self.max_total_api_calls = 50
        self.session_output_size = 0
        self.max_session_output = 50 * 1024 * 1024  # 50MB
        self.start_time = 0.0

    def set_session_limits(self, start_time: float, max_duration: int) -> None:
        """Set session timing limits.

        Args:
            start_time: Session start timestamp
            max_duration: Maximum session duration in seconds
        """
        self.start_time = start_time
        self.max_session_duration = max_duration

    async def run_turn_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> Tuple[int, str]:
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
            self.log(f"Session limit reached ({self.max_total_api_calls} API calls)", "ERROR")
            return (1, "Session limit exceeded - too many API calls")

        elapsed = time.time() - self.start_time
        if elapsed > self.max_session_duration:
            self.log(f"Session duration limit reached ({elapsed:.0f}s)", "ERROR")
            return (1, "Session timeout - maximum duration exceeded")

        for attempt in range(max_retries + 1):
            self.total_api_calls += 1  # Track API call count

            if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
                code, output = await self._run_turn_with_sdk(prompt)
            else:
                code, output = self._run_sdk_subprocess(prompt)

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

    def run_sdk_sync(self, prompt: str) -> Tuple[int, str]:
        """Run SDK command synchronously (for subprocess-based execution).

        Args:
            prompt: The prompt for this turn

        Returns:
            (exit_code, output)
        """
        if self.sdk == "claude" and CLAUDE_SDK_AVAILABLE:
            self.log("ERROR: Claude SDK should use async path, not run_sdk_sync()", "ERROR")
            return (1, "Internal error: Claude SDK requires async session mode")

        return self._run_sdk_subprocess(prompt)

    def _run_sdk_subprocess(self, prompt: str) -> Tuple[int, str]:
        """Run SDK command via subprocess (legacy/copilot mode).

        Args:
            prompt: The prompt for this turn

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

        # Create a pseudo-terminal for stdin
        master_fd, slave_fd = PTYManager.create_pty()

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
        import os

        os.close(slave_fd)

        # Start PTY threads
        stdout_lines, stderr_lines, stdout_thread, stderr_thread, stdin_thread = (
            PTYManager.start_pty_threads(
                process,
                master_fd,
                log_func=self.log,
            )
        )

        # Wait for completion
        PTYManager.wait_for_completion(process, stdout_thread, stderr_thread)

        # Combine captured output
        stdout_output = "".join(stdout_lines)
        stderr_output = "".join(stderr_lines)

        # Log output if present (FULL output per user requirement)
        if stdout_output:
            self.log(f"stdout ({len(stdout_output)} chars): {stdout_output}")

        if stderr_output:
            self.log(f"stderr ({len(stderr_output)} chars): {stderr_output}")

        return process.returncode, stdout_output

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
            )

            # Stream response - messages are typed objects, not dicts
            print("\n[DEBUG] 🔄 Starting async for message loop", flush=True)
            async for message in query(prompt=prompt, options=options):
                print("\n[DEBUG] 💬 Got a message from query()", flush=True)
                # Handle different message types
                if hasattr(message, "__class__"):
                    msg_type = message.__class__.__name__
                    print(f"\n[DEBUG] 📨 Message type: {msg_type}", flush=True)
                    self.log(f"📨 Received message type: {msg_type}", "INFO")

                    if msg_type == "AssistantMessage":
                        # Capture assistant message for transcript
                        self.message_capture.capture_assistant_message(message)

                        # Process content blocks
                        for block in getattr(message, "content", []):
                            block_type = getattr(block, "type", "unknown")
                            self.log(f"  📦 Block type: {block_type}", "INFO")

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
                                        "ERROR",
                                    )
                                    return (1, "Turn output too large")

                                if self.session_output_size > self.max_session_output:
                                    self.log(
                                        f"Session output limit exceeded ({self.session_output_size} bytes)",
                                        "ERROR",
                                    )
                                    return (1, "Session output too large")

                                print(text, end="", flush=True)
                                output_lines.append(text)

                            # Handle tool_use blocks (TodoWrite)
                            elif hasattr(block, "type") and block.type == "tool_use":
                                tool_name = getattr(block, "name", None)
                                self.log(f"🔍 Detected tool_use block: {tool_name}", "INFO")

                                if tool_name == "TodoWrite":
                                    self.log("🎯 TodoWrite tool detected!", "INFO")
                                    # Extract todos from input object
                                    if hasattr(block, "input"):
                                        tool_input = block.input
                                        self.log(
                                            f"✓ Block has input attribute, type: {type(tool_input)}",
                                            "INFO",
                                        )

                                        # Check if input has todos attribute
                                        if hasattr(tool_input, "todos"):
                                            todos = tool_input.todos
                                            self.log(
                                                f"✓ Input has todos attribute with {len(todos)} items",
                                                "INFO",
                                            )
                                            self.todo_handler(todos)
                                        # Fallback: try dict-style access
                                        elif isinstance(tool_input, dict) and "todos" in tool_input:
                                            todos = tool_input["todos"]
                                            self.log(
                                                f"✓ Input is dict with todos key ({len(todos)} items)",
                                                "INFO",
                                            )
                                            self.todo_handler(todos)
                                        else:
                                            self.log(
                                                f"⚠️  Input has no todos attribute or key. Attributes: {dir(tool_input)}",
                                                "WARNING",
                                            )
                                    else:
                                        self.log("⚠️  Block has no input attribute", "WARNING")

                    elif msg_type == "ResultMessage":
                        # Check if there was an error
                        if getattr(message, "is_error", False):
                            error_result = getattr(message, "result", "Unknown error")
                            self.log(f"SDK error: {error_result}", "ERROR")
                            return (1, "".join(output_lines))

                    # SystemMessage and other types are informational - skip

            # Success
            full_output = "".join(output_lines)

            # Log output if present
            if full_output:
                self.log(f"stdout ({len(full_output)} chars): {full_output}")

            return (0, full_output)

        except GeneratorExit:
            # Graceful generator cleanup
            self.log("Async generator cleanup (normal)", "DEBUG")
            return (0, "".join(output_lines) if output_lines else "")
        except RuntimeError as e:
            # Catch cancel scope errors - expected during cleanup
            if "cancel scope" in str(e).lower():
                self.log("Async cleanup complete (task coordination)", "DEBUG")
                return (0, "".join(output_lines) if output_lines else "")
            raise
        except Exception as e:
            self.log(f"SDK execution failed: {e}", "ERROR")
            import traceback

            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
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
