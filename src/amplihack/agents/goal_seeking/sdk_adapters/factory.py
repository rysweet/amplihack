"""Factory for creating goal-seeking agents with the chosen SDK."""

from __future__ import annotations

from pathlib import Path

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType


def create_agent(
    name: str,
    sdk: str | SDKType = SDKType.MICROSOFT,
    instructions: str = "",
    model: str | None = None,
    storage_path: Path | None = None,
    enable_memory: bool = True,
    enable_eval: bool = False,
    **kwargs: object,
) -> GoalSeekingAgent:
    """Create a goal-seeking agent with the specified SDK."""
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
            model=model or "gpt-4o",
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if sdk == SDKType.MINI:
        return _MiniFrameworkAdapter(
            name=name,
            instructions=instructions,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
        )

    raise ValueError(f"Unknown SDK: {sdk}. Choose from: claude, copilot, microsoft, mini")


class _MiniFrameworkAdapter(GoalSeekingAgent):
    """Adapter wrapping the current WikipediaLearningAgent."""

    def __init__(
        self,
        name: str,
        instructions: str,
        model: str | None,
        storage_path: Path | None,
        enable_memory: bool,
    ):
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
        try:
            from ..wikipedia_learning_agent import WikipediaLearningAgent

            self._learning_agent = WikipediaLearningAgent(
                agent_name=self.name,
                model=self._mini_model,
                storage_path=self.storage_path,
            )
        except ImportError:
            self._learning_agent = None

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        if not self._learning_agent:
            return AgentResult(
                response="Mini-framework not available",
                goal_achieved=False,
                metadata={"sdk": "mini"},
            )
        answer = self._learning_agent.answer_question(task)
        if isinstance(answer, tuple):
            answer = answer[0]
        return AgentResult(response=str(answer), goal_achieved=True, metadata={"sdk": "mini"})

    def _get_native_tools(self) -> list[str]:
        return ["read_content", "search_memory", "synthesize_answer", "calculate"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        pass


__all__ = ["create_agent"]
