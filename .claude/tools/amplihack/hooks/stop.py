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
        try:
            # Try to import Neo4j memory system
            import sys

            # Add src to path if exists
            if self.project_root and (self.project_root / "src").exists():
                sys.path.insert(0, str(self.project_root / "src"))

            from amplihack.memory.neo4j import lifecycle
            from amplihack.memory.neo4j.agent_integration import extract_and_store_learnings

            # Check if Neo4j is running
            if not lifecycle.is_neo4j_running():
                self.log("Neo4j not running, skipping memory extraction", "DEBUG")
                return

            # Extract conversation from input
            conversation = input_data.get("conversation", "")
            if not conversation:
                self.log("No conversation data in stop hook input", "DEBUG")
                return

            # Try to detect agent type from metrics
            agent_type = "general"  # Default

            # Store learnings in Neo4j
            memory_ids = extract_and_store_learnings(
                agent_type=agent_type,
                output=conversation,
                task="session_work",
                success=True,
                project_id=str(self.project_root.name) if self.project_root else "unknown"
            )

            if memory_ids:
                self.log(f"Stored {len(memory_ids)} learnings in Neo4j memory", "INFO")
                self.save_metric("neo4j_learnings_stored", len(memory_ids))

        except ImportError as e:
            self.log(f"Neo4j modules not available: {e}", "DEBUG")
        except Exception as e:
            # Don't crash stop hook - just log
            self.log(f"Memory extraction failed (non-critical): {e}", "WARNING")

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
