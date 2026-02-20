"""Microsoft Agent Framework implementation of GoalSeekingAgent.

Uses the agent-framework package (Microsoft's unified AI agent platform).
Provides: Thread-based state, @function_tool decorator, GraphWorkflow
for multi-agent orchestration, middleware for logging/auth.

Install: pip install agent-framework --pre
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# Try importing Microsoft Agent Framework
try:
    from agents_framework import Agent as MSAgent
    from agents_framework import ModelClient, Thread

    HAS_MS_FRAMEWORK = True
except ImportError:
    HAS_MS_FRAMEWORK = False
    logger.debug(
        "Microsoft Agent Framework not installed. Install with: pip install agent-framework --pre"
    )


class MicrosoftGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on Microsoft Agent Framework.

    Features:
    - Thread-based multi-turn conversation state
    - @function_tool decorator for tool registration
    - GraphWorkflow for teaching orchestration
    - Middleware for logging, auth, validation
    - Structured output via Pydantic
    - OpenTelemetry integration
    - amplihack-memory-lib for persistent knowledge

    Example:
        >>> agent = MicrosoftGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent.",
        ... )
        >>> result = await agent.run("Learn about React framework releases...")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str = "gpt-4",
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
    ):
        if not HAS_MS_FRAMEWORK:
            raise ImportError(
                "Microsoft Agent Framework not installed. "
                "Install with: pip install agent-framework --pre"
            )

        self._thread: Any = None

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.MICROSOFT,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Microsoft Agent Framework agent."""
        # Convert AgentTools to MS function_tool format
        ms_tools = []
        for tool in self._tools:
            # Create a wrapper function with the right metadata
            fn = tool.function
            fn.__name__ = tool.name
            fn.__doc__ = tool.description
            ms_tools.append(fn)

        # Build system prompt
        system = self._build_system_prompt()

        self._sdk_agent = MSAgent(
            name=self.name,
            model=ModelClient(model=self.model),
            instructions=system,
            tools=ms_tools,
        )

        # Initialize thread for multi-turn state
        self._thread = Thread()

    def _build_system_prompt(self) -> str:
        """Build system prompt for Microsoft Agent Framework agent."""
        base = (
            "You are a goal-seeking learning agent built on Microsoft Agent Framework.\n\n"
            "GOAL-SEEKING BEHAVIOR:\n"
            "1. Analyze the user's request to determine intent\n"
            "2. Form a specific, measurable goal\n"
            "3. Create a step-by-step plan\n"
            "4. Execute each step, using tools as needed\n"
            "5. Evaluate progress and adjust plan\n"
            "6. Report goal achievement status\n\n"
            "LEARNING CAPABILITIES:\n"
            "- learn_from_content: Extract and store facts\n"
            "- search_memory: Query stored knowledge\n"
            "- explain_knowledge: Generate explanations\n"
            "- find_knowledge_gaps: Identify unknowns\n"
            "- verify_fact: Check consistency\n"
            "- store_fact: Persist knowledge\n"
            "- get_memory_summary: Knowledge overview\n\n"
            "Always use your tools to interact with your memory system.\n"
            "Store important facts. Verify claims. Identify gaps.\n"
        )

        if self.instructions:
            base += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return base

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Microsoft Agent Framework loop."""
        try:
            response = await self._sdk_agent.run(
                thread=self._thread,
                message=task,
            )

            content = response.content if hasattr(response, "content") else str(response)

            return AgentResult(
                response=content,
                goal_achieved=bool(content),
                tools_used=[],
                turns=1,
                metadata={"sdk": "microsoft", "model": self.model},
            )
        except Exception as e:
            logger.exception("Microsoft Agent Framework run failed: %s", type(e).__name__)
            return AgentResult(
                response="Agent execution encountered an error.",
                goal_achieved=False,
                metadata={"sdk": "microsoft", "error": type(e).__name__},
            )

    def _get_native_tools(self) -> list[str]:
        """Return MS Agent Framework native tools."""
        return ["model_client"]  # Tools depend on model client configuration

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register custom tool with MS Agent Framework."""
        self._tools.append(tool)
        self._create_sdk_agent()

    def close(self) -> None:
        """Release resources."""
        super().close()
        self._thread = None


__all__ = ["MicrosoftGoalSeekingAgent", "HAS_MS_FRAMEWORK"]
