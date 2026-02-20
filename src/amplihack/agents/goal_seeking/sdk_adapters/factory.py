"""Factory for creating goal-seeking agents with the chosen SDK.

Usage:
    agent = create_agent(
        name="my_agent",
        sdk_type="claude",  # or "copilot", "microsoft", "mini"
        instructions="You are a helpful learning agent.",
    )
    result = await agent.run("Learn about quantum computing")

Philosophy: One function, any SDK. The user chooses the runtime,
the interface stays the same.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType


def create_agent(
    name: str,
    sdk_type: str | SDKType = SDKType.COPILOT,
    instructions: str = "",
    model: str | None = None,
    storage_path: Path | None = None,
    enable_memory: bool = True,
    enable_eval: bool = False,
    **kwargs: Any,
) -> GoalSeekingAgent:
    """Create a goal-seeking agent with the specified SDK.

    Args:
        name: Agent identifier
        sdk_type: SDK to use ("copilot", "claude", "microsoft", "mini")
        instructions: Agent system prompt
        model: LLM model (SDK-specific default if None)
        storage_path: Path for memory database
        enable_memory: Enable amplihack-memory-lib (default True)
        enable_eval: Include eval harness
        **kwargs: SDK-specific options

    Returns:
        GoalSeekingAgent instance ready to use

    Raises:
        ImportError: If the chosen SDK is not installed
        ValueError: If sdk_type is not recognized
        NotImplementedError: If the SDK adapter is not yet implemented
    """
    if isinstance(sdk_type, str):
        try:
            sdk_type = SDKType(sdk_type.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported SDK type: {sdk_type}. Choose from: {[t.value for t in SDKType]}"
            )

    if sdk_type == SDKType.CLAUDE:
        from .claude_sdk import ClaudeGoalSeekingAgent

        return ClaudeGoalSeekingAgent(
            name=name,
            instructions=instructions,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if sdk_type == SDKType.COPILOT:
        raise NotImplementedError("Copilot SDK adapter not yet implemented")

    if sdk_type == SDKType.MICROSOFT:
        raise NotImplementedError("Microsoft Agent Framework adapter not yet implemented")

    if sdk_type == SDKType.MINI:
        return _MiniFrameworkAdapter(
            name=name,
            instructions=instructions,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
        )

    raise ValueError(f"Unsupported SDK type: {sdk_type}. Choose from: {[t.value for t in SDKType]}")


class _MiniFrameworkAdapter(GoalSeekingAgent):
    """Adapter wrapping existing WikipediaLearningAgent as GoalSeekingAgent."""

    def __init__(self, name, instructions, model, storage_path, enable_memory):
        self._mini_model = model
        super().__init__(
            name=name,
            instructions=instructions or "",
            sdk_type=SDKType.MINI,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize mini-framework agent."""
        try:
            from ..learning_agent import WikipediaLearningAgent

            self._learning_agent = WikipediaLearningAgent(
                agent_name=self.name,
                model=self._mini_model,
            )
        except ImportError:
            self._learning_agent = None

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Run through mini-framework."""
        if not self._learning_agent:
            return AgentResult(
                response="Mini framework not available",
                goal_achieved=False,
                metadata={"sdk": "mini"},
            )
        try:
            answer = self._learning_agent.answer_question(task)
            if isinstance(answer, tuple):
                answer = answer[0]
            return AgentResult(
                response=str(answer),
                goal_achieved=True,
                metadata={"sdk": "mini"},
            )
        except Exception as e:
            return AgentResult(
                response=f"Error: {e}",
                goal_achieved=False,
                metadata={"sdk": "mini", "error": str(e)},
            )

    def _get_native_tools(self) -> list[str]:
        return ["read_content", "search_memory", "synthesize_answer"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        pass  # Mini-framework has fixed tool set


__all__ = ["create_agent"]
