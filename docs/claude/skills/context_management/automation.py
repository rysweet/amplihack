"""Automation module for context-management skill.

This module provides fully automatic context management via PostToolUse hook integration.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

try:
    from context_management import (
        ContextExtractor,
        ContextRehydrator,
        TokenMonitor,
        check_status,
    )
except ImportError:
    # Fallback for when running from hooks
    from .context_extractor import ContextExtractor
    from .context_rehydrator import ContextRehydrator
    from .token_monitor import TokenMonitor


# Automation state tracking
STATE_FILE = Path(".claude/runtime/context-automation-state.json")


class ContextAutomation:
    """Handles automatic context management.

    This class integrates with PostToolUse hook to provide:
    - Automatic token monitoring
    - Automatic snapshot creation at thresholds
    - Automatic compaction detection
    - Automatic context rehydration
    """

    def __init__(self):
        """Initialize automation with state tracking."""
        self.monitor = TokenMonitor()
        self.extractor = ContextExtractor()
        self.rehydrator = ContextRehydrator()
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load automation state from disk."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Default state
        return {
            "last_snapshot_threshold": None,
            "last_token_count": 0,
            "snapshots_created": [],
            "last_rehydration": None,
            "compaction_detected": False,
            "tool_use_count": 0,
            "last_transcript_size": 0,
            "cached_token_count": 0,
        }

    def _save_state(self) -> None:
        """Save automation state to disk."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def process_post_tool_use(
        self, current_tokens: int, conversation_data: Optional[list] = None
    ) -> Dict[str, Any]:
        """Process after tool use for automatic context management.

        Uses adaptive frequency to minimize overhead:
        - 0-40% usage: Check every 50th tool use
        - 40-55% usage: Check every 10th tool use
        - 55-70% usage: Check every 3rd tool use
        - 70%+ usage: Check every tool use

        Args:
            current_tokens: Current token count
            conversation_data: Optional conversation history

        Returns:
            Dict with actions taken and recommendations
        """
        result = {
            "status": "ok",
            "actions_taken": [],
            "warnings": [],
            "recommendations": [],
            "skipped": False,
        }

        # Increment tool use counter
        self.state["tool_use_count"] = self.state.get("tool_use_count", 0) + 1
        tool_count = self.state["tool_use_count"]

        # Calculate current percentage (use cached if available)
        percentage = (current_tokens / self.monitor.max_tokens) * 100

        # Adaptive frequency: skip if not time to check
        if percentage < 40:
            check_every = 50  # Very safe - minimal checks
        elif percentage < 55:
            check_every = 10  # Warming up - occasional checks
        elif percentage < 70:
            check_every = 3   # Close to threshold - frequent checks
        else:
            check_every = 1   # Critical zone - check every time

        # Skip if not time to check yet
        if tool_count % check_every != 0:
            result["skipped"] = True
            result["next_check_in"] = check_every - (tool_count % check_every)
            self._save_state()  # Save updated counter
            return result

        # Check usage
        usage = self.monitor.check_usage(current_tokens)
        threshold_status = usage.threshold_status

        # Detect compaction (token count dropped significantly)
        if self._detect_compaction(current_tokens):
            result["actions_taken"].append("compaction_detected")
            self._handle_compaction(result)

        # Auto-snapshot at thresholds (if we have conversation data)
        if conversation_data and threshold_status != "ok":
            snapshot_created = self._auto_snapshot(
                threshold_status, conversation_data, current_tokens
            )
            if snapshot_created:
                result["actions_taken"].append(f"auto_snapshot_at_{threshold_status}")
                result["warnings"].append(
                    f"⚠️  Auto-snapshot created at {usage.percentage:.1f}% usage"
                )

        # Add recommendations based on usage
        if usage.percentage > 70:
            result["recommendations"].append(usage.recommendation)

        # Update state
        self.state["last_token_count"] = current_tokens
        self._save_state()

        return result

    def _detect_compaction(self, current_tokens: int) -> bool:
        """Detect if context was compacted.

        Compaction detected if token count dropped by more than 30%.
        """
        last_count = self.state.get("last_token_count", 0)

        if last_count == 0:
            return False

        # If tokens dropped by more than 30%, likely compacted
        drop_percentage = (last_count - current_tokens) / last_count
        if drop_percentage > 0.3 and current_tokens < last_count:
            return True

        return False

    def _auto_snapshot(self, threshold: str, conversation_data: list, current_tokens: int) -> bool:
        """Create automatic snapshot at threshold.

        Args:
            threshold: Threshold level ('consider', 'recommended', 'urgent')
            conversation_data: Conversation history
            current_tokens: Current token count

        Returns:
            True if snapshot was created, False if already exists for this threshold
        """
        # Don't create duplicate snapshots at same threshold
        if self.state.get("last_snapshot_threshold") == threshold:
            return False

        # Create snapshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"auto_{threshold}_{timestamp}"

        try:
            context = self.extractor.extract_from_conversation(conversation_data)
            snapshot_path = self.extractor.create_snapshot(context, snapshot_name)

            # Update state
            self.state["last_snapshot_threshold"] = threshold
            self.state["snapshots_created"].append(
                {
                    "timestamp": timestamp,
                    "threshold": threshold,
                    "tokens": current_tokens,
                    "path": str(snapshot_path),
                }
            )
            self._save_state()

            return True

        except Exception:
            # Silently fail - don't interrupt user workflow
            return False

    def _handle_compaction(self, result: Dict[str, Any]) -> None:
        """Handle detected compaction by auto-rehydrating.

        Uses smart level selection based on last known usage.
        """
        # Find most recent snapshot
        snapshots = self.state.get("snapshots_created", [])
        if not snapshots:
            result["warnings"].append("⚠️  Compaction detected but no snapshots available")
            return

        # Get most recent snapshot
        recent_snapshot = snapshots[-1]
        snapshot_path = Path(recent_snapshot["path"])

        if not snapshot_path.exists():
            result["warnings"].append("⚠️  Snapshot file not found")
            return

        # Smart level selection based on usage before compaction
        last_tokens = recent_snapshot["tokens"]
        max_tokens = self.monitor.max_tokens
        percentage = (last_tokens / max_tokens) * 100

        if percentage < 55:
            level = "essential"
        elif percentage < 70:
            level = "standard"
        else:
            level = "comprehensive"

        try:
            # Rehydrate context
            rehydrated = self.rehydrator.rehydrate(snapshot_path, level)

            result["actions_taken"].append(f"auto_rehydrated_at_{level}_level")
            result["warnings"].append(
                f"✅ Context restored automatically ({level} level) from {recent_snapshot['timestamp']}"
            )

            # Mark that we've rehydrated
            self.state["last_rehydration"] = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "snapshot": recent_snapshot["timestamp"],
            }
            self.state["compaction_detected"] = True
            self._save_state()

        except Exception as e:
            result["warnings"].append(f"⚠️  Auto-rehydration failed: {e}")


def run_automation(current_tokens: int, conversation_data: Optional[list] = None):
    """Run context automation (called from PostToolUse hook).

    Args:
        current_tokens: Current token count
        conversation_data: Optional conversation history
    """
    automation = ContextAutomation()
    return automation.process_post_tool_use(current_tokens, conversation_data)


if __name__ == "__main__":
    # Test automation
    print("Testing context automation...")

    # Simulate usage at different levels
    automation = ContextAutomation()

    # Test at 60% usage
    result = automation.process_post_tool_use(600000, [])
    print(f"60% usage: {result}")

    # Test at 75% usage
    result = automation.process_post_tool_use(750000, [])
    print(f"75% usage: {result}")

    # Test compaction detection (simulate drop)
    result = automation.process_post_tool_use(300000, [])
    print(f"After compaction: {result}")
