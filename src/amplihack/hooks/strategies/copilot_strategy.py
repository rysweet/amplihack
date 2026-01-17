"""GitHub Copilot Strategy for Adaptive Hooks.

Philosophy:
- File-based context injection via .github/agents/AGENTS.md
- Power steering via subprocess with --continue flag
- Fail-safe: Graceful handling of missing copilot CLI

This strategy implements GitHub Copilot's mechanisms for context
injection and autonomous power steering.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from .base import HookStrategy


class CopilotStrategy(HookStrategy):
    """Hook strategy for GitHub Copilot launcher.

    GitHub Copilot uses file-based context injection and subprocess-based
    power steering:
    - Context injection: Write to .github/agents/AGENTS.md with @include
    - Power steering: Spawn `gh copilot --continue <session> -p <prompt>`

    See GitHub Copilot CLI documentation for details.
    """

    CONTEXT_DIR = Path(".claude/runtime/copilot")
    DYNAMIC_CONTEXT_FILE = CONTEXT_DIR / "dynamic_context.md"
    AGENTS_FILE = Path(".github/agents/AGENTS.md")

    def inject_context(self, context: str) -> Dict[str, Any]:
        """Inject context into Copilot session via file.

        GitHub Copilot reads context from .github/agents/AGENTS.md.
        We write dynamic context to a separate file and reference it
        via @include directive.

        Args:
            context: Context string (markdown or plain text)

        Returns:
            Empty dict (context injected via file, not hook output)

        Side effects:
            - Writes to .claude/runtime/copilot/dynamic_context.md
            - Updates .github/agents/AGENTS.md with @include directive
        """
        # Ensure directories exist
        self.CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        self.AGENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Write dynamic context
        self._write_with_retry(self.DYNAMIC_CONTEXT_FILE, context)

        # Update AGENTS.md with @include directive
        self._update_agents_file()

        # No hook output needed - context loaded from file
        return {}

    def power_steer(self, prompt: str, session_id: Optional[str] = None) -> bool:
        """Execute power steering via Copilot CLI subprocess.

        Spawns a subprocess to continue the Copilot session with a new prompt:
        `gh copilot --continue <session> -p <prompt>`

        Args:
            prompt: The prompt to execute
            session_id: Copilot session ID (required for Copilot)

        Returns:
            True if subprocess spawned successfully, False otherwise

        Note:
            This spawns a detached subprocess and returns immediately.
            The subprocess runs independently of the hook.
        """
        # Check if gh copilot is available
        if not shutil.which("gh"):
            print("Warning: gh CLI not found - power steering unavailable")
            return False

        # Build command
        cmd = ["gh", "copilot"]

        if session_id:
            cmd.extend(["--continue", session_id])

        cmd.extend(["-p", prompt])

        # Spawn detached subprocess
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent
            )
            return True
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Warning: Failed to spawn copilot subprocess: {e}")
            return False

    def _update_agents_file(self) -> None:
        """Update .github/agents/AGENTS.md with @include directive.

        Creates or updates the AGENTS.md file to include our dynamic context.
        Uses @include syntax supported by GitHub Copilot.
        """
        include_line = (
            f"@include {self.DYNAMIC_CONTEXT_FILE.relative_to(Path.cwd())}\n"
        )

        # Read existing content if file exists
        existing_content = ""
        if self.AGENTS_FILE.exists():
            existing_content = self.AGENTS_FILE.read_text()

        # Check if include already present
        if include_line.strip() in existing_content:
            return  # Already included

        # Prepare new content
        if existing_content:
            # Append to existing content
            new_content = existing_content.rstrip() + "\n\n" + include_line
        else:
            # Create new file with header
            new_content = (
                "# GitHub Copilot Agents Context\n\n"
                "This file is automatically managed by amplihack hooks.\n\n"
                f"{include_line}"
            )

        # Write with retry
        self._write_with_retry(self.AGENTS_FILE, new_content)

    def _write_with_retry(
        self,
        filepath: Path,
        content: str,
        max_retries: int = 3
    ) -> None:
        """Write file with retry for cloud sync resilience.

        Args:
            filepath: Path to write to
            content: Content string to write
            max_retries: Maximum retry attempts

        Raises:
            OSError: If all retries fail
        """
        import time

        retry_delay = 0.1
        last_error = None

        for attempt in range(max_retries):
            try:
                filepath.write_text(content)
                return
            except OSError as e:
                last_error = e
                if e.errno == 5 and attempt < max_retries - 1:  # I/O error
                    if attempt == 0:
                        print(
                            f"File I/O error writing {filepath} - retrying. "
                            "May be cloud sync issue."
                        )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        # All retries failed
        if last_error:
            raise last_error


__all__ = ["CopilotStrategy"]
