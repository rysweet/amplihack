"""Claude Agent SDK implementation of GoalSeekingAgent.

Uses the claude-agents package (Anthropic's official agent framework).
Provides native tools: bash, read_file, write_file, edit_file, glob, grep.
Custom learning tools registered via Tool(name, schema, function).
Subagent support for teaching sessions.
MCP integration for external tool servers.

Install: pip install claude-agents
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# Try importing Claude Agent SDK
try:
    from claude_agents import Agent as ClaudeAgent
    from claude_agents.tools import Tool as ClaudeTool

    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False
    logger.debug("claude-agents not installed. Install with: pip install claude-agents")


class ClaudeGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the Claude Agent SDK.

    Features:
    - Native tools: bash, read_file, write_file, edit_file, glob, grep
    - Custom learning tools (7 registered via AgentTool -> ClaudeTool)
    - Subagent support for teaching sessions
    - MCP integration for external tool servers
    - Hooks for logging and validation
    - amplihack-memory-lib for persistent knowledge

    Example:
        >>> agent = ClaudeGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent that acquires knowledge from content.",
        ... )
        >>> result = await agent.run("Learn about the 2026 Winter Olympics from this article...")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str = "claude-sonnet-4-5-20250929",
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        allowed_native_tools: list[str] | None = None,
        mcp_clients: list[Any] | None = None,
    ):
        if not HAS_CLAUDE_SDK:
            raise ImportError(
                "Claude Agent SDK not installed. Install with: pip install claude-agents"
            )

        self._allowed_native_tools = allowed_native_tools or [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "grep",
        ]
        self._mcp_clients = mcp_clients or []

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.CLAUDE,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Claude Agent SDK agent with tools."""
        # Convert AgentTools to Claude Tool format
        claude_tools = []
        for tool in self._tools:
            claude_tool = ClaudeTool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.parameters,
                function=tool.function,
            )
            claude_tools.append(claude_tool)

        # Build system prompt with goal-seeking + learning instructions
        system = self._build_system_prompt()

        agent_kwargs: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "tools": claude_tools,
            "allowed_tools": self._allowed_native_tools + [t.name for t in self._tools],
        }

        # MCP integration
        if self._mcp_clients:
            agent_kwargs["mcp_clients"] = self._mcp_clients

        self._sdk_agent = ClaudeAgent(**agent_kwargs)

    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for goal-seeking learning agent."""
        base = (
            "You are a goal-seeking learning agent. Your capabilities:\n\n"
            "GOAL SEEKING:\n"
            "1. Determine the user's intent from their message\n"
            "2. Form a specific, evaluable goal\n"
            "3. Make a plan to achieve the goal\n"
            "4. Execute the plan iteratively, adjusting based on results\n"
            "5. Evaluate whether the goal was achieved\n\n"
            "LEARNING:\n"
            "- Use learn_from_content to extract and store facts from text\n"
            "- Use search_memory to retrieve relevant stored knowledge\n"
            "- Use verify_fact to check claims against your knowledge\n"
            "- Use find_knowledge_gaps to identify what you don't know\n\n"
            "TEACHING:\n"
            "- Use explain_knowledge to generate explanations at varying depth\n"
            "- Adapt your explanations to the learner's level\n"
            "- Ask probing questions to verify understanding\n\n"
            "APPLYING:\n"
            "- Use stored knowledge to solve new problems\n"
            "- Use native tools (bash, file operations) to take real actions\n"
            "- Verify your work using verify_fact and search_memory\n"
        )

        if self.instructions:
            base += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return base

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Claude Agent SDK loop."""
        try:
            result = self._sdk_agent.run(task, max_turns=max_turns)

            # Extract metadata from result
            tools_used = []
            turns = 1
            if hasattr(result, "tools_used"):
                tools_used = result.tools_used
            if hasattr(result, "turns"):
                turns = result.turns

            return AgentResult(
                response=result.response if hasattr(result, "response") else str(result),
                goal_achieved=True,
                tools_used=tools_used,
                turns=turns,
                metadata={"sdk": "claude", "max_turns": max_turns},
            )
        except Exception as e:
            logger.error("Claude SDK agent run failed: %s", e)
            return AgentResult(
                response=f"Agent execution failed: {e}",
                goal_achieved=False,
                metadata={"sdk": "claude", "error": str(e)},
            )

    def _get_native_tools(self) -> list[str]:
        """Return Claude SDK native tools."""
        return ["bash", "read_file", "write_file", "edit_file", "glob", "grep"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register custom tool with Claude Agent SDK."""
        if self._sdk_agent:
            # Re-create agent with updated tools (Claude SDK is immutable)
            self._tools.append(tool)
            self._create_sdk_agent()

    def create_teaching_subagent(
        self, topic: str, student_level: str = "intermediate"
    ) -> Any:
        """Create a subagent specialized for teaching a topic.

        Uses Claude SDK's subagent() context manager for isolated context.

        Args:
            topic: Topic to teach
            student_level: beginner, intermediate, or advanced

        Returns:
            Subagent context manager (use with 'with' statement)
        """
        if not self._sdk_agent:
            raise RuntimeError("SDK agent not initialized")

        teaching_system = (
            f"You are a teaching agent specialized in explaining '{topic}' "
            f"to {student_level} students.\n\n"
            "Teaching approach:\n"
            "1. Start with the big picture\n"
            "2. Break down into manageable concepts\n"
            "3. Use analogies and examples\n"
            "4. Check understanding with questions\n"
            "5. Adapt depth based on student responses\n\n"
            "Use search_memory to retrieve relevant knowledge.\n"
            "Use explain_knowledge for structured explanations.\n"
        )

        # Return subagent context manager
        return self._sdk_agent.subagent(
            system=teaching_system,
            tools=[
                ClaudeTool(
                    name=t.name,
                    description=t.description,
                    input_schema=t.parameters,
                    function=t.function,
                )
                for t in self._tools
                if t.category in ("memory", "teaching")
            ],
        )


__all__ = ["ClaudeGoalSeekingAgent", "HAS_CLAUDE_SDK"]
