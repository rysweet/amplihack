#!/usr/bin/env python3
"""
Claude Code hook for session stop events.
Uses unified HookProcessor for common functionality.
"""

import json

# Import the base processor
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class StopHook(HookProcessor):
    """Hook processor for session stop events."""

    def __init__(self):
        super().__init__("stop")

    def extract_learnings(self, messages: List[Dict]) -> List[Dict]:
        """Extract learnings using the reflection module.

        Args:
            messages: List of conversation messages

        Returns:
            List of potential learnings with improvement suggestions
        """
        try:
            # Import reflection module
            from reflection import SessionReflector, save_reflection_summary

            # Create reflector and analyze session
            reflector = SessionReflector()
            analysis = reflector.analyze_session(messages)

            # Save detailed analysis if not skipped
            if not analysis.get("skipped"):
                summary_file = save_reflection_summary(analysis, self.analysis_dir)
                if summary_file:
                    self.log(f"Reflection analysis saved to {summary_file}")

                # Return patterns found as learnings
                learnings = []
                for pattern in analysis.get("patterns", []):
                    learnings.append(
                        {
                            "type": pattern["type"],
                            "suggestion": pattern.get("suggestion", ""),
                            "priority": "high"
                            if pattern["type"] == "user_frustration"
                            else "normal",
                        }
                    )
                return learnings
            else:
                self.log("Reflection skipped (loop prevention active)")
                return []

        except ImportError as e:
            self.log(f"Could not import reflection module: {e}", "WARNING")
            # Fall back to simple keyword extraction
            return self.extract_learnings_simple(messages)
        except Exception as e:
            self.log(f"Error in reflection analysis: {e}", "ERROR")
            return []

    def extract_learnings_simple(self, messages: List[Dict]) -> List[Dict]:
        """Simple fallback learning extraction.

        Args:
            messages: List of conversation messages

        Returns:
            List of simple keyword-based learnings
        """
        learnings = []
        keywords = ["discovered", "learned", "found that", "issue was", "solution was"]

        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        learnings.append({"keyword": keyword, "preview": content[:200]})
                        break
        return learnings

    def save_session_analysis(self, messages: List[Dict]):
        """Save session analysis for later review.

        Args:
            messages: List of conversation messages
        """
        # Generate analysis filename
        analysis_file = (
            self.analysis_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        # Extract stats
        stats = {
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "tool_uses": 0,
            "errors": 0,
        }

        # Count tool uses and errors
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "tool_use" in str(content):
                    stats["tool_uses"] += 1
                if "error" in str(content).lower():
                    stats["errors"] += 1

        # Extract learnings
        learnings = self.extract_learnings(messages)
        if learnings:
            stats["potential_learnings"] = len(learnings)

        # Save analysis
        analysis = {"stats": stats, "learnings": learnings}

        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)

        self.log(f"Saved session analysis to {analysis_file.name}")

        # Also save metrics
        self.save_metric("message_count", stats["message_count"])
        self.save_metric("tool_uses", stats["tool_uses"])
        self.save_metric("errors", stats["errors"])
        if learnings:
            self.save_metric("potential_learnings", len(learnings))

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stop event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Metadata about the session
        """
        # Extract messages
        messages = input_data.get("messages", [])
        self.log(f"Processing {len(messages)} messages")

        # Save session analysis
        if messages:
            self.save_session_analysis(messages)

        # Check for learnings
        learnings = self.extract_learnings(messages)

        # Build response
        output = {}
        if learnings:
            # Check for high priority learnings
            priority_learnings = [
                learning for learning in learnings if learning.get("priority") == "high"
            ]

            output = {
                "metadata": {
                    "learningsFound": len(learnings),
                    "highPriority": len(priority_learnings),
                    "source": "reflection_analysis",
                    "analysisPath": ".claude/runtime/analysis/",
                    "summary": f"Found {len(learnings)} improvement opportunities",
                }
            }

            # Add specific suggestions to output if high priority
            if priority_learnings:
                output["metadata"]["urgentSuggestion"] = priority_learnings[0].get("suggestion", "")

            self.log(
                f"Found {len(learnings)} potential improvements ({len(priority_learnings)} high priority)"
            )

        return output


def main():
    """Entry point for the stop hook."""
    hook = StopHook()
    hook.run()


if __name__ == "__main__":
    main()
