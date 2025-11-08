#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.

Stop Hook Protocol (https://docs.claude.com/en/docs/claude-code/hooks):
- Return {"decision": "approve"} to allow normal stop
- Return {"decision": "block", "reason": "..."} to prevent stop and continue working
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Import HookProcessor - wrap in try/except for robustness
try:
    from hook_processor import HookProcessor  # type: ignore[import]
except ImportError as e:
    # If import fails, provide helpful error message
    print(f"Failed to import hook_processor: {e}", file=sys.stderr)
    print("Make sure hook_processor.py exists in the same directory", file=sys.stderr)
    sys.exit(1)


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.
        Run synchronous reflection analysis if enabled.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with decision to block or allow stop
        """
        # LOG START - Always log entry for debugging
        self.log("=== STOP HOOK STARTED ===")
        self.log(f"Input keys: {list(input_data.keys())}")

        try:
            lock_exists = self.lock_flag.exists()
        except (PermissionError, OSError) as e:
            self.log(f"Cannot access lock file: {e}", "WARNING")
            self.log("=== STOP HOOK ENDED (fail-safe: approve) ===")
            # Fail-safe: allow stop if we can't read lock
            return {"decision": "approve"}

        if lock_exists:
            # Lock is active - block stop and continue working
            self.log("Lock is active - blocking stop to continue working")
            self.save_metric("lock_blocks", 1)
            self.log("=== STOP HOOK ENDED (decision: block - lock active) ===")
            return {
                "decision": "block",
                "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can",
            }

        # Check if reflection should run
        if not self._should_run_reflection():
            self.log("Reflection not enabled or skipped - allowing stop")
            self.log("=== STOP HOOK ENDED (decision: approve - no reflection) ===")
            return {"decision": "approve"}

        # FIX #2: Check for reflection semaphore (prevents infinite loop)
        session_id = self._get_current_session_id()
        semaphore_file = (
            self.project_root
            / ".claude"
            / "runtime"
            / "reflection"
            / f".reflection_presented_{session_id}"
        )

        if semaphore_file.exists():
            # Reflection already presented - remove semaphore and allow stop
            self.log(
                f"Reflection already presented for session {session_id} - removing semaphore and allowing stop"
            )
            try:
                semaphore_file.unlink()
            except OSError:
                pass
            self.log("=== STOP HOOK ENDED (decision: approve - reflection already shown) ===")
            return {"decision": "approve"}

        # RUN REFLECTION SYNCHRONOUSLY (blocks here)
        try:
            # FIX #4: Announce reflection start (STAGE 1)
            self._announce_reflection_start()

            # FIX #6: Pass transcript_path from input_data
            transcript_path = input_data.get("transcript_path")
            filled_template = self._run_reflection_sync(transcript_path)

            # If reflection failed or returned nothing, allow stop
            if not filled_template or not filled_template.strip():
                self.log("No reflection result - allowing stop")
                self.log("=== STOP HOOK ENDED (decision: approve - no reflection) ===")
                return {"decision": "approve"}

            # Generate unique filename for this reflection
            reflection_filename = self._generate_reflection_filename(filled_template)
            reflection_path = (
                self.project_root / ".claude" / "runtime" / "reflection" / reflection_filename
            )

            # Save reflection to uniquely named file
            try:
                reflection_path.parent.mkdir(parents=True, exist_ok=True)
                reflection_path.write_text(filled_template)
                self.log(f"Reflection saved to: {reflection_path}")
            except Exception as e:
                self.log(f"Warning: Could not save reflection file: {e}", "WARNING")

            # Also save to current_findings.md for backward compatibility
            try:
                current_findings = (
                    self.project_root / ".claude" / "runtime" / "reflection" / "current_findings.md"
                )
                current_findings.write_text(filled_template)
            except Exception:
                pass  # Non-critical

            # FIX #5: Block with instructions to read and present (STAGE 2)
            self.log("Reflection complete - blocking with presentation instructions")
            result = self._block_with_findings(filled_template, str(reflection_path))

            # FIX #7: Create semaphore after presenting
            try:
                semaphore_file.parent.mkdir(parents=True, exist_ok=True)
                semaphore_file.touch()
                self.log(f"Created reflection semaphore: {semaphore_file}")
            except OSError as e:
                self.log(f"Warning: Could not create semaphore file: {e}", "WARNING")

            self.log("=== STOP HOOK ENDED (decision: block - reflection complete) ===")
            return result

        except Exception as e:
            # FAIL-SAFE: Always allow stop on errors
            self.log(f"Reflection error: {e}", "ERROR")
            self.save_metric("reflection_errors", 1)
            self.log("=== STOP HOOK ENDED (decision: approve - error occurred) ===")
            return {"decision": "approve"}

    def _should_run_reflection(self) -> bool:
        """Check if reflection should run based on config and environment.

        Returns:
            True if reflection should run, False otherwise
        """
        # Check environment variable skip flag
        if os.environ.get("AMPLIHACK_SKIP_REFLECTION"):
            self.log("AMPLIHACK_SKIP_REFLECTION is set - skipping reflection", "DEBUG")
            return False

        # Load reflection config
        config_path = self.project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
        if not config_path.exists():
            self.log("Reflection config not found - skipping reflection", "DEBUG")
            return False

        try:
            with open(config_path) as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.log(f"Cannot read reflection config: {e}", "WARNING")
            return False

        # Check if enabled
        if not config.get("enabled", False):
            self.log("Reflection is disabled - skipping", "DEBUG")
            return False

        # Check for reflection lock to prevent concurrent runs
        reflection_dir = self.project_root / ".claude" / "runtime" / "reflection"
        reflection_lock = reflection_dir / ".reflection_lock"

        if reflection_lock.exists():
            self.log("Reflection already running - skipping", "DEBUG")
            return False

        return True

    def _get_current_session_id(self) -> str:
        """Detect current session ID from environment or logs.

        Priority:
        1. CLAUDE_SESSION_ID env var (if set by tooling)
        2. Most recent session directory
        3. Generate timestamp-based ID

        Returns:
            Session ID string
        """
        # Try environment variable
        session_id = os.environ.get("CLAUDE_SESSION_ID")
        if session_id:
            return session_id

        # FIX #1: Try finding most recent session directory (not files!)
        logs_dir = self.project_root / ".claude" / "runtime" / "logs"
        if logs_dir.exists():
            try:
                # Filter to directories only - don't pick up log files like "stop.log"
                sessions = [p for p in logs_dir.iterdir() if p.is_dir()]
                sessions = sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)
                if sessions:
                    return sessions[0].name
            except (OSError, PermissionError) as e:
                self.log(f"Cannot access logs directory: {e}", "WARNING")

        # Generate timestamp-based ID
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _run_reflection_sync(self, transcript_path: Optional[str] = None) -> Optional[str]:
        """Run Claude SDK-based reflection synchronously.

        Args:
            transcript_path: Optional path to JSONL transcript file from Claude Code

        Returns:
            Filled FEEDBACK_SUMMARY template as string, or None if failed
        """
        try:
            from claude_reflection import run_claude_reflection
        except ImportError:
            self.log("Cannot import claude_reflection - skipping reflection", "WARNING")
            return None

        # Get session ID
        session_id = self._get_current_session_id()
        self.log(f"Running Claude-powered reflection for session: {session_id}")

        # FIX #3: Load JSONL transcript if provided by Claude Code
        conversation = None
        if transcript_path:
            transcript_file = Path(transcript_path)
            self.log(f"Using transcript from Claude Code: {transcript_file}")

            try:
                # Load JSONL format (one JSON per line)
                conversation = []
                with open(transcript_file) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        entry = json.loads(line)
                        if entry.get("type") in ["user", "assistant"] and "message" in entry:
                            msg = entry["message"]
                            content = msg.get("content", "")
                            if isinstance(content, list):
                                text_parts = []
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_parts.append(block.get("text", ""))
                                content = "\n".join(text_parts)

                            conversation.append(
                                {
                                    "role": msg.get("role", entry.get("type", "user")),
                                    "content": content,
                                }
                            )
                self.log(f"Loaded {len(conversation)} conversation turns from transcript")
            except Exception as e:
                self.log(f"Failed to load transcript: {e}", "WARNING")
                conversation = None

        # Find session directory
        session_dir = self.project_root / ".claude" / "runtime" / "logs" / session_id

        if not session_dir.exists():
            self.log(f"Session directory not found: {session_dir}", "WARNING")
            return None

        # Run Claude reflection (uses SDK)
        try:
            filled_template = run_claude_reflection(session_dir, self.project_root, conversation)

            if not filled_template:
                self.log("Claude reflection returned empty result", "WARNING")
                return None

            # Save the filled template
            output_path = session_dir / "FEEDBACK_SUMMARY.md"
            output_path.write_text(filled_template)
            self.log(f"Feedback summary saved to: {output_path}")

            # Also save to current_findings for backward compatibility
            findings_path = (
                self.project_root / ".claude" / "runtime" / "reflection" / "current_findings.md"
            )
            findings_path.parent.mkdir(parents=True, exist_ok=True)
            findings_path.write_text(filled_template)

            # Save metrics
            self.save_metric("reflection_success", 1)

            return filled_template

        except Exception as e:
            self.log(f"Claude reflection failed: {e}", "ERROR")
            return None

    def _announce_reflection_start(self) -> None:
        """Announce that reflection is starting (STAGE 1 - FIX #4)."""
        print(f"\n{'=' * 70}", file=sys.stderr)
        print("🔍 BEGINNING SELF-REFLECTION ON SESSION", file=sys.stderr)
        print(f"{'=' * 70}\n", file=sys.stderr)
        print("Analyzing the conversation using Claude SDK...", file=sys.stderr)
        print("This will take 10-60 seconds.", file=sys.stderr)
        print("\nWhat reflection analyzes:", file=sys.stderr)
        print("  • Task complexity and workflow adherence", file=sys.stderr)
        print("  • User interactions and satisfaction", file=sys.stderr)
        print("  • Subagent usage and efficiency", file=sys.stderr)
        print("  • Learning opportunities and improvements", file=sys.stderr)
        print(f"\n{'=' * 70}\n", file=sys.stderr)

    def _generate_reflection_filename(self, filled_template: str) -> str:
        """Generate descriptive filename for this session's reflection.

        Args:
            filled_template: The reflection content (used to extract task summary)

        Returns:
            Filename like: reflection-system-investigation-20251104_165432.md
        """
        # Extract task summary from template if possible
        task_slug = "session"
        try:
            # Try to extract from "## Task Summary" section
            if "## Task Summary" in filled_template:
                summary_section = filled_template.split("## Task Summary")[1].split("\n\n")[1]
                # Get first sentence, clean it up
                first_sentence = summary_section.split(".")[0][:100]
                # Convert to slug
                import re

                task_slug = re.sub(r"[^a-z0-9]+", "-", first_sentence.lower()).strip("-")
                # Limit length
                task_slug = task_slug[:50]
        except Exception:
            # Fallback to generic
            task_slug = "session"

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"reflection-{task_slug}-{timestamp}.md"

    def _block_with_findings(self, filled_template: str, reflection_file_path: str) -> Dict:
        """Block stop with instructions to read and present reflection (STAGE 2 - FIX #5).

        Args:
            filled_template: Filled FEEDBACK_SUMMARY template from Claude
            reflection_file_path: Path where reflection was saved

        Returns:
            Block decision dict with presentation instructions
        """
        reason = f"""📋 SESSION REFLECTION COMPLETE

The reflection system has analyzed this session and saved the findings to:

**{reflection_file_path}**

**YOUR TASK:**

1. Read the reflection file using the Read tool
2. Parse the findings and present them to the user following this structure:

   a) **Executive Summary** (2-3 sentences)
      - What was accomplished
      - Key insight from reflection

   b) **Key Findings** (Be verbose!)
      - What Worked Well: Highlight 2-3 top successes with specific examples
      - Areas for Improvement: Highlight 2-3 main issues with context

   c) **Top Recommendations** (Be verbose!)
      - Present 3-5 recommendations in priority order
      - For each: Problem → Solution → Impact → Why it matters

   d) **Action Options** - Give the user these choices:
      • Create GitHub Issues (work on NOW or save for LATER)
      • Start Auto Mode (if concrete improvements can be implemented)
      • Discuss Specific Improvements (explore recommendations in detail)
      • Just Stop (next stop will succeed - semaphore prevents re-run)

After presenting the findings and getting the user's decision, you may proceed accordingly."""

        self.save_metric("reflection_blocked", 1)

        return {"decision": "block", "reason": reason}


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
