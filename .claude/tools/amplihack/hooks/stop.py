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
import subprocess
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

# Default continuation prompt when no custom prompt is provided
DEFAULT_CONTINUATION_PROMPT = (
    "we must keep pursuing the user's objective and must not stop the turn - "
    "look for any additional TODOs, next steps, or unfinished work and pursue it "
    "diligently in as many parallel tasks as you can"
)


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        self.continuation_prompt_file = (
            self.project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"
        )

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.
        Run synchronous reflection analysis if enabled.
        Execute Neo4j cleanup if appropriate.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with decision to block or allow stop
        """
        self.log("=== STOP HOOK STARTED ===")
        self.log(f"Input keys: {list(input_data.keys())}")

        try:
            lock_exists = self.lock_flag.exists()
        except (PermissionError, OSError) as e:
            self.log(f"Cannot access lock file: {e}", "WARNING")
            self.log("=== STOP HOOK ENDED (fail-safe: approve) ===")
            return {"decision": "approve"}

        if lock_exists:
            # Lock is active - block stop and continue working
            self.log("Lock is active - blocking stop to continue working")
            self.save_metric("lock_blocks", 1)

            # Read custom continuation prompt or use default
            continuation_prompt = self.read_continuation_prompt()

            self.log("=== STOP HOOK ENDED (decision: block - lock active) ===")
            return {
                "decision": "block",
                "reason": continuation_prompt,
            }

        # Neo4j cleanup integration (runs before reflection to ensure database state is managed
        # before any potentially long-running reflection analysis that might timeout the user)
        self._handle_neo4j_cleanup()

        # Neo4j learning capture (after cleanup, before reflection)
        # Separated from cleanup for single responsibility and optional nature
        self._handle_neo4j_learning()

        # Power-steering check (before reflection)
        if not lock_exists and self._should_run_power_steering():
            try:
                from power_steering_checker import PowerSteeringChecker

                ps_checker = PowerSteeringChecker(self.project_root)
                transcript_path_str = input_data.get("transcript_path")

                if transcript_path_str:
                    from pathlib import Path

                    transcript_path = Path(transcript_path_str)
                    session_id = self._get_current_session_id()

                    self.log("Running power-steering analysis...")
                    ps_result = ps_checker.check(transcript_path, session_id)

                    if ps_result.decision == "block":
                        self.log("Power-steering blocking stop - work incomplete")
                        self.save_metric("power_steering_blocks", 1)
                        self.log("=== STOP HOOK ENDED (decision: block - power-steering) ===")
                        return {
                            "decision": "block",
                            "reason": ps_result.continuation_prompt or "Session appears incomplete",
                        }
                    self.log(f"Power-steering approved stop: {ps_result.reasons}")
                    self.save_metric("power_steering_approves", 1)

                    # Display summary if available
                    if ps_result.summary:
                        self.log("Power-steering summary generated")
                        # Summary is saved to file by checker

            except Exception as e:
                # Fail-open: Continue to normal flow on any error
                self.log(f"Power-steering error (fail-open): {e}", "WARNING")
                self.save_metric("power_steering_errors", 1)

                # Surface error to user via stderr for visibility
                print("\n⚠️  Power-Steering Warning", file=sys.stderr)
                print(f"Power-steering encountered an error and was skipped: {e}", file=sys.stderr)
                print("Check .claude/runtime/power-steering/power_steering.log for details", file=sys.stderr)

        # Check if reflection should run
        if not self._should_run_reflection():
            self.log("Reflection not enabled or skipped - allowing stop")
            self.log("=== STOP HOOK ENDED (decision: approve - no reflection) ===")
            return {"decision": "approve"}

        session_id = self._get_current_session_id()
        semaphore_file = (
            self.project_root
            / ".claude"
            / "runtime"
            / "reflection"
            / f".reflection_presented_{session_id}"
        )

        if semaphore_file.exists():
            self.log(
                f"Reflection already presented for session {session_id} - removing semaphore and allowing stop"
            )
            try:
                semaphore_file.unlink()
            except OSError:
                pass
            self.log("=== STOP HOOK ENDED (decision: approve - reflection already shown) ===")
            return {"decision": "approve"}

        try:
            self._announce_reflection_start()
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
                pass

            self.log("Reflection complete - blocking with presentation instructions")
            result = self._block_with_findings(filled_template, str(reflection_path))

            try:
                semaphore_file.parent.mkdir(parents=True, exist_ok=True)
                semaphore_file.touch()
                self.log(f"Created reflection semaphore: {semaphore_file}")
            except OSError as e:
                self.log(f"Warning: Could not create semaphore file: {e}", "WARNING")

            self.log("=== STOP HOOK ENDED (decision: block - reflection complete) ===")
            return result

        except Exception as e:
            self.log(f"Reflection error: {e}", "ERROR")
            self.save_metric("reflection_errors", 1)
            self.log("=== STOP HOOK ENDED (decision: approve - error occurred) ===")
            return {"decision": "approve"}

    def _is_neo4j_in_use(self) -> bool:
        """Check if Neo4j service requires cleanup.

        Two-layer detection:
        1. Environment variables - Are credentials configured?
        2. Docker container status - Is container actually running?

        Returns:
            bool: True if Neo4j container is running, False otherwise.
                  Returns False on any errors (fail-safe).
        """
        # Layer 1: Check environment variables (instant)
        if not os.getenv("NEO4J_USERNAME") or not os.getenv("NEO4J_PASSWORD"):
            self.log("Neo4j credentials not configured - skipping cleanup", "DEBUG")
            return False

        # Layer 2: Check Docker container status (authoritative check)
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=neo4j", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=2.0
            )

            if result.returncode != 0:
                return False

            containers = result.stdout.strip().split('\n')
            neo4j_running = any('neo4j' in name.lower() for name in containers if name)

            if neo4j_running:
                self.log("Neo4j container detected - proceeding with cleanup", "DEBUG")
            else:
                self.log("No Neo4j containers running - skipping cleanup", "DEBUG")

            return neo4j_running

        except FileNotFoundError:
            self.log("Docker command not found - skipping Neo4j cleanup", "WARNING")
            return False

        except subprocess.TimeoutExpired:
            self.log("Docker command timed out - skipping Neo4j cleanup", "WARNING")
            return False

        except Exception as e:
            self.log(f"Error checking Docker status: {e} - skipping Neo4j cleanup", "WARNING")
            return False

    def _handle_neo4j_cleanup(self) -> None:
        """Handle Neo4j cleanup on session exit.

        Pre-check gate: Only proceeds if Neo4j is actually in use.
        Prevents unnecessary initialization of Neo4j components when
        the service isn't running, avoiding spurious authentication errors.

        Executes Neo4j shutdown coordination if appropriate.
        Fail-safe: Never raises exceptions.

        Environment Variables Set:
            AMPLIHACK_CLEANUP_MODE: Set to "1" to signal cleanup context.
                Prevents interactive prompts during session exit.
                Checked by container_selection.py to skip container selection dialog.
        """
        # PRE-CHECK GATE: Skip if Neo4j not in use
        if not self._is_neo4j_in_use():
            self.log("Neo4j not in use - skipping cleanup handler", "DEBUG")
            return

        self.log("Neo4j cleanup handler started - service detected as active", "INFO")

        try:
            # Set cleanup mode to prevent interactive prompts during session exit
            # This is checked by container_selection.resolve_container_name()
            os.environ["AMPLIHACK_CLEANUP_MODE"] = "1"

            # Import components
            from amplihack.memory.neo4j.lifecycle import Neo4jContainerManager
            from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
            from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

            # Detect auto mode (standardized format)
            auto_mode = os.getenv("AMPLIHACK_AUTO_MODE", "0") == "1"

            self.log(f"Neo4j cleanup handler started (auto_mode={auto_mode})")

            # Initialize components with credentials from environment
            # Note: Connection tracker will raise ValueError if password not set and  # pragma: allowlist secret
            # NEO4J_ALLOW_DEFAULT_PASSWORD != "true". This is intentional for production security.  # pragma: allowlist secret
            tracker = Neo4jConnectionTracker(
                username=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD")
            )
            manager = Neo4jContainerManager()
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=tracker,
                container_manager=manager,
                auto_mode=auto_mode,
            )

            # Execute cleanup
            coordinator.handle_session_exit()

            self.log("Neo4j cleanup handler completed")

        except Exception as e:
            self.log(f"Neo4j cleanup failed: {e}", "WARNING")

    def _handle_neo4j_learning(self) -> None:
        """Handle Neo4j learning capture on session exit.

        Extracts learning insights from Neo4j knowledge graph if available.
        Fail-safe: Never raises exceptions.

        Design Notes:
            - Called AFTER Neo4j cleanup coordination
            - Separated from cleanup for single responsibility
            - Optional feature: Gracefully skips if not yet implemented
            - Currently planned but not yet implemented (awaiting schema definition)
        """
        try:
            # Import from sibling neo4j module (relative to hooks directory)
            from neo4j.learning_capture import capture_neo4j_learnings

            session_id = self._get_current_session_id()
            self.log(f"Starting Neo4j learning capture for session {session_id}")

            # Attempt learning capture (fail-safe design)
            success = capture_neo4j_learnings(
                project_root=self.project_root,
                session_id=session_id,
                neo4j_connection=None,  # TODO: Pass active connection when available
            )

            if success:
                self.log("Neo4j learning capture completed successfully")
                self.save_metric("neo4j_learning_captures", 1)
            else:
                self.log("Neo4j learning capture skipped (Neo4j not available)")

        except ImportError:
            self.log("Neo4j learning module not available - skipping", "DEBUG")
        except Exception as e:
            self.log(f"Neo4j learning capture failed (non-critical): {e}", "WARNING")

    def read_continuation_prompt(self) -> str:
        """Read custom continuation prompt from file or return default.

        Returns:
            str: Custom prompt content or DEFAULT_CONTINUATION_PROMPT
        """
        # Check if custom prompt file exists
        if not self.continuation_prompt_file.exists():
            self.log("No custom continuation prompt file - using default")
            return DEFAULT_CONTINUATION_PROMPT

        try:
            # Read prompt content
            content = self.continuation_prompt_file.read_text(encoding="utf-8").strip()

            # Check if empty
            if not content:
                self.log("Custom continuation prompt file is empty - using default")
                return DEFAULT_CONTINUATION_PROMPT

            # Check length constraints
            content_len = len(content)

            # Hard limit: 1000 characters
            if content_len > 1000:
                self.log(
                    f"Custom prompt too long ({content_len} chars) - using default",
                    "WARNING",
                )
                return DEFAULT_CONTINUATION_PROMPT

            # Warning for long prompts (500-1000 chars)
            if content_len > 500:
                self.log(
                    f"Custom prompt is long ({content_len} chars) - consider shortening for clarity",
                    "WARNING",
                )

            # Valid custom prompt
            self.log(f"Using custom continuation prompt ({content_len} chars)")
            return content

        except (PermissionError, OSError, UnicodeDecodeError) as e:
            self.log(f"Error reading custom prompt: {e} - using default", "WARNING")
            return DEFAULT_CONTINUATION_PROMPT

    def _should_run_power_steering(self) -> bool:
        """Check if power-steering should run based on config and environment.

        Returns:
            True if power-steering should run, False otherwise
        """
        try:
            # Reuse PowerSteeringChecker's logic instead of duplicating
            from power_steering_checker import PowerSteeringChecker

            checker = PowerSteeringChecker(self.project_root)
            is_disabled = checker._is_disabled()

            if is_disabled:
                self.log("Power-steering is disabled - skipping", "DEBUG")
                return False

            # Check for power-steering lock to prevent concurrent runs
            ps_dir = self.project_root / ".claude" / "runtime" / "power-steering"
            ps_lock = ps_dir / ".power_steering_lock"

            if ps_lock.exists():
                self.log("Power-steering already running - skipping", "DEBUG")
                return False

            return True

        except Exception as e:
            # Fail-open: On any error, skip power-steering
            self.log(f"Error checking power-steering status: {e} - skipping", "WARNING")
            return False

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

        logs_dir = self.project_root / ".claude" / "runtime" / "logs"
        if logs_dir.exists():
            try:
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

        conversation = None
        if transcript_path:
            transcript_file = Path(transcript_path)
            self.log(f"Using transcript from Claude Code: {transcript_file}")

            try:
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
        """Announce that reflection is starting."""
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
            if "## Task Summary" in filled_template:
                summary_section = filled_template.split("## Task Summary")[1].split("\n\n")[1]
                first_sentence = summary_section.split(".")[0][:100]
                import re

                task_slug = re.sub(r"[^a-z0-9]+", "-", first_sentence.lower()).strip("-")
                task_slug = task_slug[:50]
        except Exception:
            task_slug = "session"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"reflection-{task_slug}-{timestamp}.md"

    def _block_with_findings(self, filled_template: str, reflection_file_path: str) -> Dict:
        """Block stop with instructions to read and present reflection.

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


def stop():
    """Entry point for the stop hook (called by Claude Code)."""
    hook = StopHook()
    hook.run()


def main():
    """Legacy entry point for the stop hook."""
    stop()


if __name__ == "__main__":
    main()
