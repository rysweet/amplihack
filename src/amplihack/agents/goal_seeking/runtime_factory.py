"""Canonical runtime factory for benchmark-compatible goal-seeking agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .goal_seeking_agent import GoalSeekingAgent as OODAGoalSeekingAgent


class GoalAgentRuntime(Protocol):
    """Unified runtime surface shared across eval and Azure entrypoints."""

    def learn_from_content(self, content: str) -> dict[str, Any]: ...

    def answer_question(self, question: str) -> str: ...

    def prepare_fact_batch(self, content: str, include_summary: bool = True) -> dict[str, Any]: ...

    def get_memory_stats(self) -> dict[str, Any]: ...

    def close(self) -> None: ...


class ConfiguredGoalAgentRuntime:
    """Bind answer-mode compatibility around a runtime backend."""

    def __init__(self, runtime: Any, answer_mode: str = "single-shot") -> None:
        self._runtime = runtime
        # Preserve long_horizon_memory snapshot optimization on mini/OODA paths.
        self._agent = getattr(runtime, "_learning_agent", runtime)
        self._answer_mode = answer_mode

    def learn_from_content(self, content: str) -> dict[str, Any]:
        return self._runtime.learn_from_content(content)

    def answer_question(self, question: str) -> str:
        result = self._runtime.answer_question(question, answer_mode=self._answer_mode)
        if isinstance(result, tuple):
            return result[0]
        return result

    def prepare_fact_batch(self, content: str, include_summary: bool = True) -> dict[str, Any]:
        return self._runtime.prepare_fact_batch(content, include_summary=include_summary)

    def store_fact_batch(self, batch: dict[str, Any]) -> dict[str, Any]:
        return self._runtime.store_fact_batch(batch)

    def get_memory_stats(self) -> dict[str, Any]:
        return self._runtime.get_memory_stats()

    def flush_memory(self) -> None:
        if hasattr(self._runtime, "flush_memory"):
            self._runtime.flush_memory()

    def close(self) -> None:
        self._runtime.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runtime, name)


def create_goal_agent_runtime(
    *,
    agent_name: str,
    sdk: str = "mini",
    model: str | None = None,
    storage_path: Path | None = None,
    use_hierarchical: bool = False,
    memory_type: str = "auto",
    answer_mode: str = "single-shot",
    bind_answer_mode: bool = True,
    enable_memory: bool = True,
    enable_eval: bool = False,
    runtime_kind: str | None = None,
    **kwargs: Any,
) -> GoalAgentRuntime | Any:
    """Create the canonical runtime used by eval and Azure surfaces.

    Args:
        agent_name: Agent identifier / memory namespace.
        sdk: Benchmark/runtime variant. ``"mini"`` uses the OODA GoalSeekingAgent
            with LearningAgent internally. Other SDK values use the SDK adapter factory.
        runtime_kind: Optional override. ``"goal"`` forces the OODA GoalSeekingAgent.
        bind_answer_mode: When true, return a wrapper whose ``answer_question()``
            uses the configured ``answer_mode`` while preserving the underlying
            runtime via ``._agent`` for existing eval optimizations.
    """
    runtime: Any

    if runtime_kind == "goal" or sdk == "mini":
        runtime = OODAGoalSeekingAgent(
            agent_name=agent_name,
            model=model,
            storage_path=storage_path,
            use_hierarchical=use_hierarchical and memory_type == "auto",
            memory_type=memory_type,
            **kwargs,
        )
    else:
        from .sdk_adapters.factory import create_agent

        runtime = create_agent(
            name=agent_name,
            sdk=sdk,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
            **kwargs,
        )

    if not bind_answer_mode:
        return runtime
    return ConfiguredGoalAgentRuntime(runtime, answer_mode=answer_mode)


__all__ = [
    "ConfiguredGoalAgentRuntime",
    "GoalAgentRuntime",
    "create_goal_agent_runtime",
]
