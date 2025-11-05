#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.
Automatically triggers cleanup agent at task completion.

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
    """Hook processor for stop events with lock support and automatic cleanup."""

    def __init__(self):
        super().__init__("stop")
        self.lock_flag = self.project_root / ".claude" / "runtime" / "locks" / ".lock_active"
        self.cleanup_config_path = self.project_root / ".claude" / "runtime" / ".cleanup_config"
        self.cleanup_marker = self.project_root / ".claude" / "runtime" / ".cleanup_run"

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check lock flag and block stop if active.
        Also trigger reflection analysis and cleanup if enabled.

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

        # Not locked - trigger cleanup before allowing stop
        cleanup_triggered = self._trigger_cleanup_if_enabled()

        # Check if reflection should be triggered
        self._trigger_reflection_if_enabled()

        # Allow stop - explicitly approve to proceed
        self.log("No lock active - allowing stop")

        # If cleanup was triggered, block to run cleanup agent
        if cleanup_triggered:
            return {
                "decision": "block",
                "reason": "Task appears complete - running automatic cleanup to ensure code quality. The cleanup agent will review git status, remove temporary artifacts, and ensure philosophy compliance before allowing stop.",
            }

        return {"decision": "approve"}

    def _trigger_cleanup_if_enabled(self) -> bool:
        """Trigger cleanup agent if task completion is detected and cleanup is enabled.

        Returns:
            True if cleanup was triggered, False otherwise
        """
        try:
            # Check if cleanup has already run this session
            if self.cleanup_marker.exists():
                self.log("Cleanup already ran this session - skipping", "DEBUG")
                return False

            # Load cleanup config
            config = self._load_cleanup_config()

            # Check if automatic cleanup is disabled
            if not config.get("auto_cleanup_enabled", True):
                self.log("Automatic cleanup is disabled - skipping", "DEBUG")
                return False

            # Detect if task appears to be complete
            if not self._detect_task_completion():
                self.log("Task not complete - skipping cleanup", "DEBUG")
                return False

            # Create cleanup marker to prevent duplicate runs
            self.cleanup_marker.parent.mkdir(parents=True, exist_ok=True)
            self.cleanup_marker.touch()

            self.log("Task completion detected - triggering cleanup agent")
            self.save_metric("cleanup_auto_triggered", 1)
            return True

        except Exception as e:
            # Never block on cleanup - just log and continue
            self.log(f"Non-critical: Failed to trigger cleanup: {e}", "WARNING")
            return False

    def _load_cleanup_config(self) -> Dict[str, Any]:
        """Load cleanup configuration with defaults.

        Returns:
            Configuration dictionary
        """
        default_config = {
            "auto_cleanup_enabled": True,
            "cleanup_on_ultrathink": True,
            "cleanup_on_workflow": True,
        }

        if not self.cleanup_config_path.exists():
            return default_config

        try:
            import json

            with open(self.cleanup_config_path) as f:
                user_config = json.load(f)

            # Merge user config with defaults
            default_config.update(user_config)
            return default_config

        except Exception as e:
            self.log(f"Failed to load cleanup config: {e}", "WARNING")
            return default_config

    def _detect_task_completion(self) -> bool:
        """Detect if task appears to be complete.

        Heuristics:
        - TodoWrite todos are all completed
        - Recent git activity suggests work is done
        - No active lock flags

        Returns:
            True if task appears complete, False otherwise
        """
        try:
            # Check for completed todos
            todo_dir = self.project_root / ".claude" / "runtime" / "todos"
            if todo_dir.exists():
                # Look for recent todo files
                todo_files = sorted(
                    todo_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
                )

                if todo_files:
                    import json

                    # Check most recent todo file
                    with open(todo_files[0]) as f:
                        todos = json.load(f)

                    # If all todos are completed, task is likely done
                    if todos and all(todo.get("status") == "completed" for todo in todos):
                        self.log("All todos completed - task appears complete", "DEBUG")
                        return True

                    # If any todos are in_progress or pending, task is not complete
                    if any(todo.get("status") in ("in_progress", "pending") for todo in todos):
                        self.log("Todos still in progress - task not complete", "DEBUG")
                        return False

            # Check for recent git commits (suggesting work is done)
            import subprocess

            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.project_root,
                capture_output=True,
            )

            # If there are staged changes, task might not be complete
            if result.returncode == 1:
                self.log("Staged changes detected - task may not be complete", "DEBUG")
                return False

            # If no todos and no staged changes, assume task is complete
            self.log("No active work detected - task appears complete", "DEBUG")
            return True

        except Exception as e:
            self.log(f"Failed to detect task completion: {e}", "WARNING")
            return False

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
