#!/usr/bin/env python3
"""
Claude Code hook for subagent stop events.
Tracks subagent termination metrics for analysis and monitoring.

This hook detects when a subagent session ends and logs metrics without
interfering with the stop behavior.

Stop Hook Protocol (https://docs.claude.com/en/docs/claude-code/hooks):
- Return {} to allow normal stop (no intervention)
- This hook is purely observational - it never blocks stops
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class SubagentStopHook(HookProcessor):
    """Hook processor for subagent stop events with metric tracking."""

    def __init__(self):
        super().__init__("subagent_stop")

    def _detect_subagent_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if we're running in a subagent context.

        Subagent context can be detected from:
        1. CLAUDE_AGENT environment variable (set by parent when launching subagent)
        2. session_id containing 'agent-' or 'subagent-' prefix
        3. Input data containing agent_name or subagent metadata

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with subagent detection results:
            {
                "is_subagent": bool,
                "agent_name": str or None,
                "detection_method": str (env|session|metadata|none)
            }
        """
        # Check environment variable
        agent_name = os.environ.get("CLAUDE_AGENT")
        if agent_name:
            return {
                "is_subagent": True,
                "agent_name": agent_name,
                "detection_method": "env",
            }

        # Check session_id for agent prefix
        session_id = input_data.get("session_id", "")
        if isinstance(session_id, str) and ("agent-" in session_id or "subagent-" in session_id):
            return {
                "is_subagent": True,
                "agent_name": session_id,
                "detection_method": "session",
            }

        # Check input data metadata
        if "agent_name" in input_data:
            return {
                "is_subagent": True,
                "agent_name": input_data["agent_name"],
                "detection_method": "metadata",
            }

        # Check for subagent marker in input data
        if input_data.get("is_subagent") or input_data.get("subagent"):
            return {
                "is_subagent": True,
                "agent_name": input_data.get("agent_name", "unknown"),
                "detection_method": "metadata",
            }

        return {
            "is_subagent": False,
            "agent_name": None,
            "detection_method": "none",
        }

    def _extract_session_metrics(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant session metrics from input data.

        Args:
            input_data: Input from Claude Code

        Returns:
            Dict with session metrics
        """
        return {
            "session_id": input_data.get("session_id"),
            "turn_count": input_data.get("turn_count", 0),
            "tool_use_count": input_data.get("tool_use_count", 0),
            "error_count": input_data.get("error_count", 0),
            "duration_seconds": input_data.get("duration_seconds"),
        }

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect subagent context and log termination metrics.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict to allow normal stop behavior
        """
        # Detect subagent context
        detection = self._detect_subagent_context(input_data)

        if detection["is_subagent"]:
            self.log(
                f"Subagent stop detected: {detection['agent_name']} "
                f"(method: {detection['detection_method']})"
            )

            # Extract session metrics
            metrics = self._extract_session_metrics(input_data)

            # Log termination metrics to JSONL
            self.save_metric(
                "subagent_termination",
                {
                    "agent_name": detection["agent_name"],
                    "detection_method": detection["detection_method"],
                    **metrics,
                },
            )

            # Also track count for quick analysis
            self.save_metric("subagent_stops", 1, {"agent_name": detection["agent_name"]})

        else:
            self.log("No subagent context detected - skipping metrics")

        # Always return empty dict - never interfere with stop behavior
        return {}


def main():
    """Entry point for the subagent_stop hook."""
    hook = SubagentStopHook()
    hook.run()


if __name__ == "__main__":
    main()
