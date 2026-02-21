"""Claude Agent SDK implementation of GoalSeekingAgent.

Uses the claude-agent-sdk package (Anthropic's official Claude Code SDK).
API: ClaudeSDKClient(options) -> connect() -> query() -> receive_response()

Install: pip install claude-agent-sdk
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

HAS_CLAUDE_SDK = False

try:
    from claude_agent_sdk import (  # type: ignore[import-not-found]
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
    )

    HAS_CLAUDE_SDK = True
except ImportError:
    pass  # Checked in ClaudeGoalSeekingAgent.__init__


class ClaudeGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the Claude Agent SDK.

    Uses ClaudeSDKClient with connect() -> query() -> receive_response() API.

    Example:
        >>> agent = ClaudeGoalSeekingAgent(name="learner")
        >>> result = await agent.run("Learn about the 2026 Winter Olympics")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        allowed_native_tools: list[str] | None = None,
    ):
        if not HAS_CLAUDE_SDK:
            raise ImportError(
                "claude-agent-sdk not installed. Install with: pip install claude-agent-sdk"
            )

        resolved_model = model or os.environ.get("CLAUDE_AGENT_MODEL", "claude-sonnet-4-5-20250929")
        self._allowed_native_tools = allowed_native_tools or [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "grep",
        ]

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.CLAUDE,
            model=resolved_model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Store config for ClaudeSDKClient (created per-run)."""
        self._sdk_agent = {
            "model": self.model,
            "system": self._build_system_prompt(),
        }

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
        """Execute task via ClaudeSDKClient connect/query/receive_response."""
        try:
            options = ClaudeAgentOptions(
                model=self._sdk_agent["model"],
                system_prompt=self._sdk_agent["system"],
                max_turns=max_turns,
                permission_mode="bypassPermissions",
            )
            client = ClaudeSDKClient(options=options)
            text_parts: list[str] = []
            tools_used: list[str] = []

            async with client:
                await client.query(task)
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                text_parts.append(block.text)
                    elif isinstance(msg, ResultMessage):
                        break

            response_text = "\n".join(text_parts) if text_parts else "No response"
            return AgentResult(
                response=response_text,
                goal_achieved=bool(text_parts),
                tools_used=tools_used,
                turns=1,
                metadata={"sdk": "claude", "variant": "claude_agent_sdk"},
            )
        except Exception as e:
            logger.error("Claude SDK agent run failed: %s", e)
            return AgentResult(
                response="Agent execution failed due to an internal error.",
                goal_achieved=False,
                metadata={"sdk": "claude", "error_type": type(e).__name__},
            )

    def _get_native_tools(self) -> list[str]:
        """Return Claude SDK native tools."""
        return ["bash", "read_file", "write_file", "edit_file", "glob", "grep"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register custom tool with Claude Agent SDK."""
        self._tools.append(tool)
        if self._sdk_agent:
            self._create_sdk_agent()


__all__ = ["ClaudeGoalSeekingAgent", "HAS_CLAUDE_SDK"]
