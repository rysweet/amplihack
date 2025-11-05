#!/usr/bin/env python3
"""
Claude Code hook for post tool use events.
Uses unified HookProcessor for common functionality.
"""

# Import the base processor
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import json
import re

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PostToolUseHook(HookProcessor):
    """Hook processor for post tool use events."""

    def __init__(self):
        super().__init__("post_tool_use")
        self.checkpoint_enabled = self._load_checkpoint_config()

    def _load_checkpoint_config(self) -> bool:
        """Load satisfaction checkpoint configuration.

        Returns:
            True if checkpoints are enabled, False otherwise
        """
        config_path = (
            self.project_root
            / ".claude"
            / "tools"
            / "amplihack"
            / ".satisfaction_checkpoint_config"
        )
        if not config_path.exists():
            # Default to enabled
            return True

        try:
            with open(config_path) as f:
                config = json.load(f)
            return config.get("enabled", True)
        except (OSError, json.JSONDecodeError):
            return True

    def _is_investigation_command(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """Detect if this is an investigation command completion.

        Args:
            tool_name: Name of the tool used
            tool_args: Arguments passed to the tool

        Returns:
            True if investigation command, False otherwise
        """
        if tool_name != "SlashCommand" and tool_name != "Skill":
            return False

        # Check for investigation commands
        command = tool_args.get("command", "")
        investigation_commands = [
            "knowledge-builder",
            "analyze",
            "expert-panel",
            "debate",
            "socratic",
        ]

        return any(inv_cmd in command for inv_cmd in investigation_commands)

    def _extract_topics(self, result: Any) -> tuple[str, str]:
        """Extract key topics from investigation result for checkpoint.

        Args:
            result: Tool result data

        Returns:
            Tuple of (topic_1, topic_2) extracted from result
        """
        result_text = str(result)

        # Try to extract topics using patterns
        # Look for headings, key terms, etc.
        topics = []

        # Pattern 1: Markdown headings
        headings = re.findall(r"^#+\s+(.+)$", result_text, re.MULTILINE)
        if headings:
            topics.extend(headings[:2])

        # Pattern 2: Bullet points with key topics
        bullets = re.findall(r"^\s*[-*]\s*\*\*(.+?)\*\*", result_text, re.MULTILINE)
        if bullets:
            topics.extend(bullets[:2])

        # Fallback defaults
        topic_1 = topics[0][:50] if len(topics) > 0 else "this topic"
        topic_2 = topics[1][:50] if len(topics) > 1 else "related areas"

        return (topic_1, topic_2)

    def _show_satisfaction_checkpoint(self, investigation_type: str, result: Any) -> None:
        """Display satisfaction checkpoint to user via stderr.

        Args:
            investigation_type: Type of investigation (knowledge-builder, analyze, etc.)
            result: Investigation result data
        """
        # Load template
        template_path = self.project_root / ".claude" / "templates" / "SATISFACTION_CHECKPOINT.md"
        if not template_path.exists():
            self.log("Satisfaction checkpoint template not found", "WARNING")
            return

        try:
            template = template_path.read_text()
        except OSError as e:
            self.log(f"Cannot read checkpoint template: {e}", "WARNING")
            return

        # Extract topics from result
        topic_1, topic_2 = self._extract_topics(result)

        # Apply user preferences for communication style
        preferences = self._load_user_preferences()
        if preferences:
            template = self._apply_communication_style(template, preferences)

        # Inject topics into template
        checkpoint = template.replace("{topic_1}", topic_1)
        checkpoint = checkpoint.replace("{topic_2}", topic_2)
        checkpoint = checkpoint.replace(
            "{investigation_summary}", f"Investigation type: {investigation_type}"
        )

        # Display to user via stderr (visible in Claude Code UI)
        print("\n" + "=" * 70, file=sys.stderr)
        print(checkpoint, file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)

        # Log satisfaction checkpoint shown
        self.save_metric("satisfaction_checkpoint_shown", investigation_type)
        self.log(f"Satisfaction checkpoint displayed for: {investigation_type}")

    def _load_user_preferences(self) -> Optional[Dict[str, Any]]:
        """Load user preferences for communication style.

        Returns:
            Dict of preferences or None if not found
        """
        prefs_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
        if not prefs_path.exists():
            return None

        try:
            prefs_text = prefs_path.read_text()
            # Simple parsing - look for communication_style
            match = re.search(r"communication_style:\s*(\w+)", prefs_text)
            if match:
                return {"communication_style": match.group(1)}
        except OSError:
            pass

        return None

    def _apply_communication_style(self, template: str, preferences: Dict[str, Any]) -> str:
        """Apply user communication style preferences to template.

        Args:
            template: Original template text
            preferences: User preferences dict

        Returns:
            Template with communication style applied
        """
        style = preferences.get("communication_style", "casual")

        if style == "formal":
            # Replace pirate speak with formal language
            template = template.replace("yer", "your")
            template = template.replace("ye", "you")
            template = template.replace("Would ye like me to:", "Would you like me to:")
            template = template.replace(
                "I've completed the investigation and provided ye with",
                "I have completed the investigation and provided you with",
            )
        elif style == "pirate":
            # Already in pirate mode - no changes needed
            pass
        elif style == "technical":
            # More technical, less conversational
            template = template.replace("Would ye like me to:", "Next actions available:")
            template = template.replace("yer questions", "your requirements")

        return template

    def save_tool_metric(self, tool_name: str, duration_ms: Optional[int] = None):
        """Save tool usage metric with structured data.

        Args:
            tool_name: Name of the tool used
            duration_ms: Duration in milliseconds (if available)
        """
        metadata = {}
        if duration_ms is not None:
            metadata["duration_ms"] = duration_ms

        self.save_metric("tool_usage", tool_name, metadata)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process post tool use event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict or validation messages
        """
        # Extract tool information
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")
        tool_args = tool_use.get("input", {})

        # Extract result if available (not currently used but could be useful)
        result = input_data.get("result", {})

        self.log(f"Tool used: {tool_name}")

        # Check for investigation command completion and show satisfaction checkpoint
        if self.checkpoint_enabled and self._is_investigation_command(tool_name, tool_args):
            command = tool_args.get("command", "")
            self._show_satisfaction_checkpoint(command, result)

        # Save metrics - could extract duration from result if available
        duration_ms = None
        if isinstance(result, dict):
            # Some tools might include timing information
            duration_ms = result.get("duration_ms")

        self.save_tool_metric(tool_name, duration_ms)

        # Check for specific tool types that might need validation
        output = {}
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            # Could add validation or checks here
            # For example, check if edits were successful
            if isinstance(result, dict) and result.get("error"):
                self.log(f"Tool {tool_name} reported error: {result.get('error')}", "WARNING")
                # Could return a suggestion or alert
                output["metadata"] = {
                    "warning": f"Tool {tool_name} encountered an error",
                    "tool": tool_name,
                }

        # Track high-level metrics
        if tool_name == "Bash":
            self.save_metric("bash_commands", 1)
        elif tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
            self.save_metric("file_operations", 1)
        elif tool_name in ["Grep", "Glob"]:
            self.save_metric("search_operations", 1)

        return output


def main():
    """Entry point for the post tool use hook."""
    hook = PostToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
