#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.

Stop Hook Protocol (https://docs.claude.com/en/docs/claude-code/hooks):
- Return {"decision": "approve"} to allow normal stop
- Return {"decision": "block", "reason": "..."} to prevent stop and continue working
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class StopHook(HookProcessor):
    """Hook processor for stop events with lock support."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.
        Also trigger reflection analysis and memory extraction if enabled.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with decision to block or allow stop
        """
        try:
            lock_exists = self.lock_flag.exists()
        except (PermissionError, OSError) as e:
            self.log(f"Cannot access lock file: {e}", "WARNING")
            # Fail-safe: allow stop if we can't read lock
            return {"decision": "approve"}

        if lock_exists:
            # Lock is active - block stop and continue working
            self.log("Lock is active - blocking stop to continue working")
            self.save_metric("lock_blocks", 1)
            return {
                "decision": "block",
                "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can",
            }

        # Not locked - extract learnings from session before stopping
        self._extract_agent_learnings(input_data)

        # Check if reflection should be triggered
        self._trigger_reflection_if_enabled()

        # Allow stop - explicitly approve to proceed
        self.log("No lock active - allowing stop")
        return {"decision": "approve"}

    def _extract_agent_learnings(self, input_data: Dict[str, Any]):
        """Extract learnings from session for memory storage.

        Args:
            input_data: Input from Claude Code Stop hook
        """
        # Memory extraction temporarily disabled - requires agent_memory_hook module
        # TODO: Re-enable in future PR when module is properly implemented
        return

            # Read conversation from session file if available
            session_id = self.get_session_id()

            # Try to find recent session files
            session_dirs = sorted(self.log_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

            conversation_text = ""
            agent_types = []

            # Look for DECISIONS.md or agent-specific logs in recent session
            for session_dir in session_dirs[:3]:  # Check last 3 sessions
                if not session_dir.is_dir():
                    continue

                # Check for DECISIONS.md
                decisions_file = session_dir / "DECISIONS.md"
                if decisions_file.exists():
                    try:
                        with open(decisions_file, "r") as f:
                            conversation_text += f"\n\n## Session Decisions\n{f.read()}"
                    except Exception as e:
                        self.log(f"Failed to read decisions: {e}", "DEBUG")

                # Check metrics for agent usage
                metrics_files = list(self.metrics_dir.glob("user_prompt_submit_metrics.jsonl"))
                if metrics_files:
                    try:
                        import json
                        with open(metrics_files[0], "r") as f:
                            for line in f:
                                metric = json.loads(line)
                                if metric.get("metric") == "agents_detected" and metric.get("metadata"):
                                    detected = metric["metadata"].get("agent_types", [])
                                    agent_types.extend(detected)
                    except Exception as e:
                        self.log(f"Failed to read metrics: {e}", "DEBUG")

            # If we have agent types and some conversation text, extract learnings
            if agent_types and conversation_text:
                self.log(f"Extracting learnings for agents: {agent_types}")

                metadata = extract_learnings_from_conversation(
                    conversation_text=conversation_text,
                    agent_types=list(set(agent_types)),  # Deduplicate
                    session_id=session_id,
                )

                # Log results
                notice = format_learning_extraction_notice(metadata)
                if notice:
                    self.log(notice)
                    self.save_metric("agent_learnings_stored", metadata.get("learnings_stored", 0))
            else:
                self.log("No agent activity detected in session - skipping learning extraction", "DEBUG")

        except ImportError as e:
            self.log(f"Memory integration not available: {e}", "DEBUG")
        except Exception as e:
            # Never block on learning extraction - just log and continue
            self.log(f"Non-critical: Failed to extract learnings: {e}", "WARNING")

    def _trigger_reflection_if_enabled(self):
        """Trigger reflection analysis if enabled and not already running."""
        try:
            # Load reflection config
            config_path = (
                self.project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
            )
            if not config_path.exists():
                self.log("Reflection config not found - skipping reflection", "DEBUG")
                return

            import json

            with open(config_path) as f:
                config = json.load(f)

            # Check if enabled
            if not config.get("enabled", False):
                self.log("Reflection is disabled - skipping", "DEBUG")
                return

            # Check for reflection lock to prevent concurrent runs
            reflection_dir = self.project_root / ".claude" / "runtime" / "reflection"
            reflection_lock = reflection_dir / ".reflection_lock"

            if reflection_lock.exists():
                self.log("Reflection already running - skipping", "DEBUG")
                return

            # Create pending marker (non-blocking)
            reflection_dir.mkdir(parents=True, exist_ok=True)
            pending_marker = reflection_dir / ".reflection_pending"
            pending_marker.touch()

            self.log("Reflection pending marker created")
            self.save_metric("reflection_triggered", 1)

        except Exception as e:
            # Never block on reflection - just log and continue
            self.log(f"Non-critical: Failed to trigger reflection: {e}", "WARNING")


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
