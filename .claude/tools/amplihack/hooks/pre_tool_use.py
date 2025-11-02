#!/usr/bin/env python3
"""
Claude Code hook for pre tool use events.
Detects and logs agent invocations for subagent tracking.

This hook intercepts tool calls BEFORE they execute, allowing us to:
1. Detect when agents are being invoked
2. Log subagent start events with context
3. Track agent delegation patterns
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PreToolUseHook(HookProcessor):
    """Hook processor for pre tool use events with agent detection."""

    # Known agent patterns for detection
    AGENT_DIRECTORIES = [
        ".claude/agents/amplihack/core",
        ".claude/agents/amplihack/specialized",
        ".claude/agents/amplihack/workflows",
        ".claude/agents",
    ]

    # Common agent names for validation
    KNOWN_AGENTS = [
        "architect",
        "builder",
        "reviewer",
        "tester",
        "optimizer",
        "api-designer",
        "database",
        "security",
        "integration",
        "analyzer",
        "cleanup",
        "patterns",
        "ambiguity",
        "fix-agent",
        "ci-diagnostic-workflow",
        "pre-commit-diagnostic",
        "prompt-writer",
        "knowledge-archaeologist",
        "memory-manager",
        "worktree-manager",
        "xpia-defense",
        "zen-architect",
        "multi-agent-debate",
        "n-version-validator",
        "fallback-cascade",
    ]

    def __init__(self):
        super().__init__("pre_tool_use")
        self.subagent_log = self.metrics_dir / "subagent_start.jsonl"

    def extract_agent_from_path(self, path: str) -> Optional[str]:
        """Extract agent name from file path.

        Args:
            path: File path potentially containing agent reference

        Returns:
            Agent name if found, None otherwise
        """
        # Normalize path separators
        normalized = path.replace("\\", "/")

        # Check if path contains agent directory
        for agent_dir in self.AGENT_DIRECTORIES:
            if agent_dir in normalized:
                # Extract filename without extension
                parts = normalized.split("/")
                for part in reversed(parts):
                    if part.endswith(".md"):
                        agent_name = part[:-3]  # Remove .md extension
                        # Validate it's a known agent
                        if agent_name in self.KNOWN_AGENTS or self._is_valid_agent_name(
                            agent_name
                        ):
                            return agent_name
        return None

    def _is_valid_agent_name(self, name: str) -> bool:
        """Check if name follows agent naming conventions.

        Args:
            name: Potential agent name

        Returns:
            True if name looks like an agent
        """
        # Agent names are typically lowercase with hyphens
        # and contain common suffixes like -agent, -workflow, -diagnostic
        if not name:
            return False

        # Must be ASCII lowercase with hyphens only (no unicode)
        if not re.match(r"^[a-z]+(-[a-z]+)*$", name):
            return False

        # Check for common agent patterns
        agent_suffixes = ["-agent", "-workflow", "-diagnostic", "-architect", "-expert"]
        if any(name.endswith(suffix) for suffix in agent_suffixes):
            return True

        # Check for core agent names
        core_names = [
            "architect",
            "builder",
            "reviewer",
            "tester",
            "optimizer",
            "analyzer",
        ]
        if name in core_names:
            return True

        # If it matches the pattern and is in an agent directory, likely an agent
        return True

    def detect_task_tool_agent(self, tool_use: Dict[str, Any]) -> Optional[str]:
        """Detect agent invocation from Task tool parameters.

        The Task tool is used for agent delegation. It typically has:
        - name: "Task"
        - input: {"task": "agent prompt or file reference"}

        Args:
            tool_use: Tool use data from Claude Code

        Returns:
            Agent name if detected, None otherwise
        """
        if tool_use.get("name") != "Task":
            return None

        # Check input parameters
        input_params = tool_use.get("input", {})

        # Look for agent references in task parameter
        task_text = input_params.get("task", "")
        if not task_text:
            return None

        # Pattern 1: Direct file reference to agent
        # Example: "@.claude/agents/amplihack/core/architect.md"
        agent_name = self.extract_agent_from_path(task_text)
        if agent_name:
            return agent_name

        # Pattern 2: Agent name in task text
        # Example: "Use architect agent to design..."
        # Look for known agent names in the text
        task_lower = task_text.lower()
        for agent in self.KNOWN_AGENTS:
            # Look for agent name as whole word
            pattern = r"\b" + re.escape(agent) + r"\b"
            if re.search(pattern, task_lower):
                return agent

        return None

    def detect_agent_from_tool_parameters(
        self, tool_use: Dict[str, Any]
    ) -> Optional[str]:
        """Detect agent reference in any tool parameter.

        Some tools like Read might be used to load agent files.

        Args:
            tool_use: Tool use data from Claude Code

        Returns:
            Agent name if detected, None otherwise
        """
        tool_name = tool_use.get("name", "")
        input_params = tool_use.get("input", {})

        # Check Read tool file_path parameter
        if tool_name == "Read":
            file_path = input_params.get("file_path", "")
            if file_path:
                agent_name = self.extract_agent_from_path(file_path)
                if agent_name:
                    return agent_name

        # Check SlashCommand for agent invocations
        if tool_name == "SlashCommand":
            command = input_params.get("command", "")
            # Look for agent references in command text or paths
            agent_name = self.extract_agent_from_path(command)
            if agent_name:
                return agent_name

            # Also check for agent names in command text
            command_lower = command.lower()
            for agent in self.KNOWN_AGENTS:
                # Look for agent name as whole word
                pattern = r"\b" + re.escape(agent) + r"\b"
                if re.search(pattern, command_lower):
                    return agent

        return None

    def detect_agent_invocation(self, input_data: Dict[str, Any]) -> Optional[str]:
        """Main agent detection logic.

        Tries multiple detection strategies in order:
        1. Task tool with agent reference
        2. Tool parameters containing agent file paths
        3. Context analysis for agent delegation

        Args:
            input_data: Input from Claude Code

        Returns:
            Agent name if detected, None otherwise
        """
        tool_use = input_data.get("toolUse", {})

        # Strategy 1: Check Task tool
        agent_name = self.detect_task_tool_agent(tool_use)
        if agent_name:
            self.log(f"Agent detected via Task tool: {agent_name}")
            return agent_name

        # Strategy 2: Check tool parameters
        agent_name = self.detect_agent_from_tool_parameters(tool_use)
        if agent_name:
            self.log(f"Agent detected via tool parameters: {agent_name}")
            return agent_name

        return None

    def truncate_text(self, text: str, max_length: int = 500) -> str:
        """Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def log_subagent_start(
        self, agent_name: str, tool_use: Dict[str, Any], context: Dict[str, Any]
    ):
        """Log subagent start event to JSONL file.

        Args:
            agent_name: Name of the agent being invoked
            tool_use: Tool use data
            context: Additional context about the invocation
        """
        # Extract prompt from tool input
        input_params = tool_use.get("input", {})
        prompt = input_params.get("task", "")
        if not prompt and "file_path" in input_params:
            prompt = f"Reading agent file: {input_params['file_path']}"

        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.get_session_id(),
            "agent_type": agent_name,
            "tool_name": tool_use.get("name", "unknown"),
            "prompt": self.truncate_text(prompt, max_length=500),
            "context": {
                "tool_id": tool_use.get("id"),
                "input_keys": list(input_params.keys()),
                **context,
            },
        }

        try:
            # Append to JSONL file
            with open(self.subagent_log, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

            self.log(f"Logged subagent start: {agent_name}")

        except Exception as e:
            self.log(f"Failed to log subagent start: {e}", "ERROR")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process pre tool use event.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict (allow tool execution) or permission decision
        """
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")

        self.log(f"Pre-tool use: {tool_name}")

        # Detect agent invocation
        agent_name = self.detect_agent_invocation(input_data)

        if agent_name:
            # Log the subagent start event
            context = {
                "hook_event": "PreToolUse",
                "detected_via": tool_name,
            }
            self.log_subagent_start(agent_name, tool_use, context)

            # Track metrics
            self.save_metric("subagent_invocation", agent_name)

        # Always allow tool execution (return empty dict)
        # PreToolUse hooks can return permission decisions, but we're just logging
        return {}


def main():
    """Entry point for the pre tool use hook."""
    hook = PreToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
