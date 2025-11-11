"""Session lifecycle management for auto mode."""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional


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


def sanitize_injected_content(content: str) -> str:
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


class SessionManager:
    """Manages session lifecycle, hooks, and instruction injection."""

    def __init__(
        self,
        log_dir: Path,
        working_dir: Path,
        log_func: Callable[[str, str], None],
    ):
        """Initialize session manager.

        Args:
            log_dir: Directory for session logs
            working_dir: Working directory for execution
            log_func: Logging function(message, level)
        """
        self.log_dir = log_dir
        self.working_dir = working_dir
        self.log = log_func

        # Create directories for prompt injection feature
        self.append_dir = self.log_dir / "append"
        self.appended_dir = self.log_dir / "appended"
        self.append_dir.mkdir(parents=True, exist_ok=True)
        self.appended_dir.mkdir(parents=True, exist_ok=True)

    def write_initial_prompt(self, prompt: str, sdk: str, max_turns: int) -> None:
        """Write initial prompt to prompt.md.

        Args:
            prompt: Original user prompt
            sdk: SDK type being used
            max_turns: Maximum number of turns
        """
        with open(self.log_dir / "prompt.md", "w") as f:
            f.write(f"# Original Auto Mode Prompt\n\n{prompt}\n\n---\n\n")
            f.write(f"**Session Started**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**SDK**: {sdk}\n")
            f.write(f"**Max Turns**: {max_turns}\n")

    def check_for_new_instructions(self) -> str:
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
                sanitized_content = sanitize_injected_content(content)

                timestamp = md_file.stem
                new_instructions.append(
                    f"\n## Additional Instruction (appended at {timestamp})\n\n{sanitized_content}\n"
                )

                # Move file to appended directory
                target_path = self.appended_dir / md_file.name
                md_file.rename(target_path)
                self.log(f"Processed and archived: {md_file.name}")

            except Exception as e:
                self.log(f"Error processing {md_file.name}: {e}", "ERROR")

        if new_instructions:
            return "\n".join(new_instructions)
        return ""

    def run_hook(self, hook: str, sdk: str, prompt: str = "") -> None:
        """Run hook for copilot and codex (Claude SDK handles hooks automatically).

        Args:
            hook: Hook name (session_start, stop, etc.)
            sdk: SDK type being used
            prompt: Original prompt (only used for session_start hook)
        """
        if sdk not in ["copilot", "codex"]:
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
                "prompt": prompt if hook == "session_start" else "",
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
                self.log(f"⚠ Hook {hook} returned exit code {result.returncode} after {elapsed:.1f}s")
                if result.stderr:
                    self.log(f"Hook stderr: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self.log(f"✗ Hook {hook} timed out after {elapsed:.1f}s")
        except Exception as e:
            self.log(f"✗ Hook {hook} failed: {e}")


class PromptTransformManager:
    """Manages prompt transformation for safety features."""

    def __init__(self, log_func: Callable[[str, str], None]):
        """Initialize prompt transform manager.

        Args:
            log_func: Logging function(message, level)
        """
        self.log = log_func
        self.using_temp_staging = os.environ.get("AMPLIHACK_STAGED_DIR") is not None
        self.staged_dir = os.environ.get("AMPLIHACK_STAGED_DIR")
        self.original_cwd_from_env = os.environ.get("AMPLIHACK_ORIGINAL_CWD")

    def transform_if_needed(self, prompt: str) -> str:
        """Transform prompt if using temp staging (safety feature).

        Args:
            prompt: Original prompt

        Returns:
            Transformed prompt (or original if not using temp staging)
        """
        if self.using_temp_staging and self.original_cwd_from_env:
            from amplihack.safety import PromptTransformer

            transformer = PromptTransformer()
            transformed = transformer.transform_prompt(
                original_prompt=prompt,
                target_directory=self.original_cwd_from_env,
                used_temp=True,
            )
            self.log(f"Transformed prompt for temp staging (target: {self.original_cwd_from_env})")
            return transformed

        return prompt


class UIManager:
    """Manages UI thread lifecycle."""

    def __init__(self, ui: Optional[object], log_func: Callable[[str, str], None]):
        """Initialize UI manager.

        Args:
            ui: AutoModeUI instance (or None if UI disabled)
            log_func: Logging function(message, level)
        """
        self.ui = ui
        self.log = log_func
        self.ui_thread = None

    def start_ui_thread(self) -> None:
        """Start UI in a separate thread if UI mode is enabled."""
        import threading

        if not self.ui:
            return

        def ui_runner():
            """Thread target to run the UI."""
            try:
                if self.ui is not None:
                    self.ui.run()
            except Exception as e:
                self.log(f"UI thread error: {e}", "ERROR")

        self.ui_thread = threading.Thread(
            target=ui_runner,
            daemon=False,  # Not daemon - we want to wait for it
            name="AutoModeUI",
        )
        self.ui_thread.start()
        self.log("UI thread started")

    def stop_ui_thread(self) -> None:
        """Stop UI thread and wait for it to finish."""
        if not self.ui_thread:
            return

        # Wait for UI thread to finish (with timeout)
        self.ui_thread.join(timeout=5.0)
        if self.ui_thread.is_alive():
            self.log("Warning: UI thread did not stop cleanly", "WARNING")
        else:
            self.log("UI thread stopped")
