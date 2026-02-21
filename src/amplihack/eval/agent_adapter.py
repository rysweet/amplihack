"""Adapters connecting amplihack agents to the eval harness.

Provides AgentAdapter implementations for:
- LearningAgent (mini-framework, synchronous)
- MultiAgentLearningAgent (multi-agent retrieval, synchronous)
- GoalSeekingAgent via SDK factory (Claude/Copilot/Microsoft, async->sync bridge)

Usage:
    from amplihack.eval.agent_adapter import AmplihackLearningAgentAdapter

    adapter = AmplihackLearningAgentAdapter("test-agent")
    adapter.learn("The sky is blue.")
    response = adapter.answer("What color is the sky?")
    adapter.close()
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from amplihack_eval.adapters.base import AgentAdapter, AgentResponse

logger = logging.getLogger(__name__)


class AmplihackLearningAgentAdapter(AgentAdapter):
    """Wraps amplihack's LearningAgent for evaluation.

    The LearningAgent uses synchronous learn_from_content() and
    answer_question() methods, so no async bridging is needed.
    """

    def __init__(
        self,
        agent_name: str = "eval-learning-agent",
        model: str = "",
        storage_path: Path | None = None,
        use_hierarchical: bool = False,
        **kwargs: Any,
    ):
        from amplihack.agents.goal_seeking.learning_agent import LearningAgent

        init_kwargs: dict[str, Any] = {
            "agent_name": agent_name,
            "use_hierarchical": use_hierarchical,
        }
        if model:
            init_kwargs["model"] = model
        if storage_path:
            init_kwargs["storage_path"] = storage_path

        self._agent_name = agent_name
        self._init_kwargs = init_kwargs
        self._extra_kwargs = kwargs
        self._agent = LearningAgent(**init_kwargs)

    def learn(self, content: str) -> None:
        """Feed content to the LearningAgent."""
        self._agent.learn_from_content(content)

    def answer(self, question: str) -> AgentResponse:
        """Ask the LearningAgent a question."""
        result = self._agent.answer_question(question)
        # answer_question may return (answer, trace) tuple or just a string
        if isinstance(result, tuple):
            answer_text, trace = result
        else:
            answer_text = result
            trace = None

        return AgentResponse(
            answer=str(answer_text),
            reasoning_trace=str(trace) if trace else "",
        )

    def reset(self) -> None:
        """Reset agent by closing and re-creating."""
        self._agent.close()
        from amplihack.agents.goal_seeking.learning_agent import LearningAgent

        self._agent = LearningAgent(**self._init_kwargs)

    def close(self) -> None:
        """Release agent resources."""
        self._agent.close()

    @property
    def name(self) -> str:
        return f"AmplihackLearning({self._agent_name})"


class AmplihackMultiAgentAdapter(AgentAdapter):
    """Wraps amplihack's MultiAgentLearningAgent for evaluation.

    Same synchronous interface as LearningAgent, but with multi-agent
    retrieval internally.
    """

    def __init__(
        self,
        agent_name: str = "eval-multi-agent",
        model: str = "",
        storage_path: Path | None = None,
        enable_spawning: bool = False,
        **kwargs: Any,
    ):
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import MultiAgentLearningAgent

        init_kwargs: dict[str, Any] = {
            "agent_name": agent_name,
            "use_hierarchical": True,  # Required for multi-agent benefits
            "enable_spawning": enable_spawning,
        }
        if model:
            init_kwargs["model"] = model
        if storage_path:
            init_kwargs["storage_path"] = storage_path

        self._agent_name = agent_name
        self._init_kwargs = init_kwargs
        self._agent = MultiAgentLearningAgent(**init_kwargs)

    def learn(self, content: str) -> None:
        """Feed content to the MultiAgentLearningAgent."""
        self._agent.learn_from_content(content)

    def answer(self, question: str) -> AgentResponse:
        """Ask the MultiAgentLearningAgent a question."""
        result = self._agent.answer_question(question)
        if isinstance(result, tuple):
            answer_text, trace = result
        else:
            answer_text = result
            trace = None

        return AgentResponse(
            answer=str(answer_text),
            reasoning_trace=str(trace) if trace else "",
        )

    def reset(self) -> None:
        """Reset agent by closing and re-creating."""
        self._agent.close()
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import MultiAgentLearningAgent

        self._agent = MultiAgentLearningAgent(**self._init_kwargs)

    def close(self) -> None:
        """Release agent resources."""
        self._agent.close()

    @property
    def name(self) -> str:
        return f"AmplihackMultiAgent({self._agent_name})"

    @property
    def capabilities(self) -> set[str]:
        return {"memory", "multi_agent"}


class AmplihackSDKAgentAdapter(AgentAdapter):
    """Wraps any SDK-backed GoalSeekingAgent for evaluation.

    SDK agents use async run(), so this adapter bridges async->sync
    using asyncio.run() or an existing event loop.
    """

    def __init__(
        self,
        agent_name: str = "eval-sdk-agent",
        sdk: str = "mini",
        model: str = "",
        storage_path: Path | None = None,
        **kwargs: Any,
    ):
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        create_kwargs: dict[str, Any] = {
            "name": agent_name,
            "sdk": sdk,
        }
        if model:
            create_kwargs["model"] = model
        if storage_path:
            create_kwargs["storage_path"] = storage_path
        create_kwargs.update(kwargs)

        self._agent_name = agent_name
        self._sdk = sdk
        self._create_kwargs = create_kwargs
        self._agent = create_agent(**create_kwargs)
        self._learned_content: list[str] = []

    def _run_async(self, coro: Any) -> Any:
        """Bridge async to sync, handling nested event loops."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Nested event loop -- create a new thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=300)
        else:
            return asyncio.run(coro)

    def learn(self, content: str) -> None:
        """Feed content to the SDK agent via its run() method."""
        self._learned_content.append(content)
        # SDK agents use run() for all interactions
        task = f"Learn and remember the following information:\n\n{content}"
        self._run_async(self._agent.run(task))

    def answer(self, question: str) -> AgentResponse:
        """Ask the SDK agent a question via its run() method."""
        result = self._run_async(self._agent.run(question))
        return AgentResponse(
            answer=str(result.response) if result else "",
            metadata={"sdk": self._sdk, "goal_achieved": result.goal_achieved if result else False},
        )

    def reset(self) -> None:
        """Reset by closing and re-creating the SDK agent."""
        self._agent.close()
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        self._agent = create_agent(**self._create_kwargs)
        self._learned_content.clear()

    def close(self) -> None:
        """Release SDK agent resources."""
        self._agent.close()

    @property
    def name(self) -> str:
        return f"AmplihackSDK({self._sdk}/{self._agent_name})"

    @property
    def capabilities(self) -> set[str]:
        caps = {"memory"}
        if self._sdk != "mini":
            caps.add("tool_use")
        return caps


__all__ = [
    "AmplihackLearningAgentAdapter",
    "AmplihackMultiAgentAdapter",
    "AmplihackSDKAgentAdapter",
]
