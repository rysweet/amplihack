"""GitHub Copilot SDK implementation of GoalSeekingAgent.

Uses the github-copilot-sdk package for agent execution.
Provides native tools via --allow-all mode (file system, git, web).
Custom learning tools registered as session tools.
Session-based state management.

Install: pip install github-copilot-sdk
Requires: GitHub Copilot CLI installed and authenticated
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# Try importing Copilot SDK
try:
    from copilot import CopilotClient

    HAS_COPILOT_SDK = True
except ImportError:
    HAS_COPILOT_SDK = False
    logger.debug("github-copilot-sdk not installed. Install with: pip install github-copilot-sdk")


class CopilotGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the GitHub Copilot SDK.

    Features:
    - Native tools: file system, git, web requests (--allow-all mode)
    - Custom learning tools (7 registered as session tools)
    - Session-based conversation state
    - MCP server integration
    - Custom agent personas
    - Streaming support
    - amplihack-memory-lib for persistent knowledge

    Example:
        >>> agent = CopilotGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent.",
        ... )
        >>> result = await agent.run("Learn about gh-aw from the documentation...")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str = "gpt-4.1",
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        streaming: bool = False,
    ):
        if not HAS_COPILOT_SDK:
            raise ImportError(
                "GitHub Copilot SDK not installed. Install with: pip install github-copilot-sdk\n"
                "Also requires: GitHub Copilot CLI installed and authenticated"
            )

        self._streaming = streaming
        self._client: Any = None
        self._session: Any = None

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.COPILOT,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Copilot SDK client and session."""
        # Convert AgentTools to Copilot tool format
        copilot_tools = []
        for tool in self._tools:
            copilot_tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "_handler": tool.function,
                }
            )

        # Build system prompt
        system = self._build_system_prompt()

        # Store config for lazy initialization (Copilot client requires async start)
        self._session_config = {
            "model": self.model,
            "streaming": self._streaming,
            "tools": copilot_tools,
            "systemMessage": {"content": system},
            "customAgents": [
                {
                    "name": self.name,
                    "displayName": self.name,
                    "description": f"Goal-seeking learning agent: {self.name}",
                    "prompt": self.instructions,
                }
            ],
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt for Copilot-based goal-seeking agent."""
        base = (
            "You are a goal-seeking learning agent powered by GitHub Copilot.\n\n"
            "CAPABILITIES:\n"
            "- Goal formation: Determine intent → form evaluable goal → plan → iterate\n"
            "- Learning: Extract facts from content, store in persistent memory\n"
            "- Remembering: Search stored knowledge, verify facts, find gaps\n"
            "- Teaching: Explain topics, adapt to learner level\n"
            "- Applying: Use knowledge + native tools to solve real problems\n\n"
            "NATIVE TOOLS:\n"
            "- File system operations (read, write, edit files)\n"
            "- Git operations\n"
            "- Web requests\n\n"
            "LEARNING TOOLS:\n"
            "- learn_from_content: Extract and store facts from text\n"
            "- search_memory: Query stored knowledge\n"
            "- explain_knowledge: Generate topic explanations\n"
            "- find_knowledge_gaps: Identify unknowns\n"
            "- verify_fact: Check fact consistency\n"
            "- store_fact: Persist a fact in memory\n"
            "- get_memory_summary: Overview of stored knowledge\n"
        )

        if self.instructions:
            base += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return base

    async def _ensure_client(self) -> None:
        """Ensure Copilot client and session are initialized."""
        if self._client is None:
            self._client = CopilotClient()
            await self._client.start()
            self._session = await self._client.create_session(self._session_config)

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Copilot SDK session."""
        try:
            await self._ensure_client()
            response = await self._session.send_and_wait({"prompt": task})

            content = ""
            if response and hasattr(response, "data"):
                content = (
                    response.data.content
                    if hasattr(response.data, "content")
                    else str(response.data)
                )
            elif response:
                content = str(response)

            return AgentResult(
                response=content,
                goal_achieved=bool(content),
                tools_used=[],
                turns=1,
                metadata={"sdk": "copilot", "model": self.model},
            )
        except Exception as e:
            logger.exception("Copilot SDK agent run failed: %s", e)
            return AgentResult(
                response="Agent execution encountered an error.",
                goal_achieved=False,
                metadata={"sdk": "copilot", "error": type(e).__name__},
            )

    def _get_native_tools(self) -> list[str]:
        """Return Copilot SDK native tools (--allow-all mode)."""
        return ["file_system", "git", "web_requests"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register custom tool with Copilot SDK session."""
        self._tools.append(tool)
        # Rebuild session config
        self._create_sdk_agent()
        # Reset session so it picks up new tools
        self._session = None

    def close(self) -> None:
        """Release Copilot client resources."""
        super().close()
        if self._client:
            asyncio.get_event_loop().run_until_complete(self._client.stop())


__all__ = ["CopilotGoalSeekingAgent", "HAS_COPILOT_SDK"]
