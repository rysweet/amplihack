"""Factory for creating goal-seeking agents with the chosen SDK.

Usage:
    agent = create_agent(
        name="my_agent",
        sdk="copilot",  # or "claude", "microsoft", "mini"
        instructions="You are a helpful learning agent.",
    )
    result = await agent.run("Learn about quantum computing")

Philosophy: One function, any SDK. The user chooses the runtime,
the interface stays the same.
"""

from __future__ import annotations

from pathlib import Path

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType


def create_agent(
    name: str,
    sdk: str | SDKType = SDKType.COPILOT,
    instructions: str = "",
    model: str | None = None,
    storage_path: Path | None = None,
    enable_memory: bool = True,
    enable_eval: bool = False,
    **kwargs,
) -> GoalSeekingAgent:
    """Create a goal-seeking agent with the specified SDK.

    Args:
        name: Agent identifier
        sdk: SDK to use ("copilot", "claude", "microsoft", "mini")
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
        ValueError: If sdk is not recognized
    """
    if isinstance(sdk, str):
        sdk = SDKType(sdk.lower())

    if sdk == SDKType.CLAUDE:
        from .claude_sdk import ClaudeGoalSeekingAgent

        return ClaudeGoalSeekingAgent(
            name=name,
            instructions=instructions,
            model=model or "claude-sonnet-4-5-20250929",
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if sdk == SDKType.COPILOT:
        from .copilot_sdk import CopilotGoalSeekingAgent

        return CopilotGoalSeekingAgent(
            name=name,
            instructions=instructions,
            model=model or "gpt-4.1",
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if sdk == SDKType.MICROSOFT:
        from .microsoft_sdk import MicrosoftGoalSeekingAgent

        return MicrosoftGoalSeekingAgent(
            name=name,
            instructions=instructions,
            model=model or "gpt-4",
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if sdk == SDKType.MINI:
        # Fallback to current LearningAgent mini-framework

        return _MiniFrameworkAdapter(
            name=name,
            instructions=instructions,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
        )

    raise ValueError(f"Unknown SDK: {sdk}. Choose from: copilot, claude, microsoft, mini")


class _MiniFrameworkAdapter(GoalSeekingAgent):
    """Adapter wrapping the current LearningAgent as a GoalSeekingAgent.

    This allows the existing mini-framework to participate in
    benchmarks alongside the SDK implementations.
    """

    def __init__(self, name, instructions, model, storage_path, enable_memory):
        self._mini_model = model
        self._mini_instructions = instructions
        super().__init__(
            name=name,
            instructions=instructions or "",
            sdk_type=SDKType.MINI,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize mini-framework LearningAgent."""
        from ..learning_agent import LearningAgent

        self._learning_agent = LearningAgent(
            agent_name=self.name,
            model=self._mini_model,
            storage_path=self.storage_path,
            use_hierarchical=True,
        )
        # Share the memory reference
        self.memory = self._learning_agent.memory

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Run through mini-framework."""
        answer = self._learning_agent.answer_question(task, question_level="L2")
        if isinstance(answer, tuple):
            answer = answer[0]
        return AgentResult(
            response=str(answer),
            goal_achieved=True,
            metadata={"sdk": "mini"},
        )

    def _get_native_tools(self) -> list[str]:
        return ["read_content", "search_memory", "synthesize_answer", "calculate"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        pass  # Mini-framework has fixed tool set


__all__ = ["create_agent"]
