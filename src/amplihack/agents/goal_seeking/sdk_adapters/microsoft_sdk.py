"""Microsoft Agent Framework implementation of GoalSeekingAgent.

Uses the agent-framework package (Microsoft's unified AI agent platform).
API: Agent(client, instructions, name=..., tools=[...]) -> agent.run(messages, session=session)

Install: pip install agent-framework
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import Microsoft Agent Framework (required, no fallback)
# ---------------------------------------------------------------------------
_HAS_AGENT_FRAMEWORK = False
AFAgent = None  # type: ignore[assignment]
AFFunctionTool = None  # type: ignore[assignment]
OpenAIChatClient = None  # type: ignore[assignment]

try:
    from agent_framework import (
        Agent as AFAgent,  # type: ignore[no-redef,assignment,import-not-found]
    )
    from agent_framework import (
        FunctionTool as AFFunctionTool,  # type: ignore[no-redef,assignment,import-not-found]
    )
    from agent_framework.openai import (
        OpenAIChatClient,  # type: ignore[no-redef,assignment,import-not-found]
    )

    _HAS_AGENT_FRAMEWORK = True
except ImportError:
    pass  # Checked in MicrosoftGoalSeekingAgent.__init__


# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts" / "sdk"


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/sdk/ directory."""
    path = _PROMPT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Tool wrapping helpers
# ---------------------------------------------------------------------------


def _build_learning_tools(agent_ref: GoalSeekingAgent) -> list[Any]:
    """Wrap AgentTools as FunctionTool objects for the SDK."""
    return [_wrap_tool(tool_def) for tool_def in agent_ref._tools]


def _wrap_tool(tool_def: AgentTool) -> Any:
    """Wrap a single AgentTool into a FunctionTool for the Agent Framework.

    Uses FunctionTool(name=..., description=..., func=...) to create
    a tool that the Agent can invoke.
    """
    original_fn = tool_def.function
    name = tool_def.name
    description = tool_def.description

    def wrapper(**kwargs: Any) -> str:
        result = original_fn(**kwargs)
        if isinstance(result, (dict, list)):
            return json.dumps(result)
        return str(result)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__doc__ = description

    return AFFunctionTool(name=name, description=description, func=wrapper)


# ---------------------------------------------------------------------------
# MicrosoftGoalSeekingAgent
# ---------------------------------------------------------------------------


class MicrosoftGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on Microsoft Agent Framework.

    Uses Agent with OpenAIChatClient. No mock mode.

    Example:
        >>> agent = MicrosoftGoalSeekingAgent(name="learner")
        >>> result = await agent.run("Learn about React framework releases")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        **kwargs: Any,
    ):
        if not _HAS_AGENT_FRAMEWORK:
            raise ImportError(
                "agent-framework not installed. Install with: pip install agent-framework"
            )

        resolved_model = model or os.environ.get("MICROSOFT_AGENT_MODEL", "gpt-4o")

        self._session: Any = None
        self._extra_kwargs = kwargs

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.MICROSOFT,
            model=resolved_model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Microsoft Agent Framework agent with Agent + OpenAIChatClient.

        Defers to lazy initialization if OPENAI_API_KEY is not set, since the
        SDK agent is only needed for _run_sdk_agent (not for eval which uses
        LearningAgent via _SDKAgentWrapper).
        """
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning(
                "OPENAI_API_KEY not set. Microsoft Agent Framework SDK agent "
                "will be created lazily when _run_sdk_agent is called."
            )
            self._sdk_agent = None
            return

        system_prompt = self._build_system_prompt()
        tools = _build_learning_tools(self)

        chat_client = OpenAIChatClient(model_id=self.model, api_key=api_key)
        self._sdk_agent = AFAgent(
            chat_client,
            instructions=system_prompt,
            name=self.name,
            tools=tools,
        )
        self._session = self._sdk_agent.create_session()

    def _build_system_prompt(self) -> str:
        """Build system prompt from template + custom instructions."""
        template = _load_prompt("microsoft_system.md")
        if not template:
            template = (
                "You are a goal-seeking learning agent built on "
                "Microsoft Agent Framework.\n\n"
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
            template += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return template

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Microsoft Agent Framework Agent.run()."""
        try:
            response = await self._sdk_agent.run(
                messages=task,
                session=self._session,
            )

            # Extract text content from AgentResponse
            content = ""
            tools_used: list[str] = []

            if hasattr(response, "messages"):
                for msg in response.messages:
                    if hasattr(msg, "content") and msg.content:
                        content += str(msg.content)
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            name = getattr(tc, "name", None) or getattr(tc, "function", {}).get(
                                "name", ""
                            )
                            if name:
                                tools_used.append(name)

            if not content and hasattr(response, "content"):
                content = str(response.content)

            return AgentResult(
                response=content or str(response),
                goal_achieved=bool(content),
                tools_used=tools_used,
                turns=len(getattr(response, "messages", [])),
                metadata={"sdk": "microsoft", "model": self.model},
            )
        except Exception as e:
            logger.error("Microsoft Agent Framework run failed: %s", e)
            return AgentResult(
                response="Agent execution failed due to an internal error.",
                goal_achieved=False,
                metadata={"sdk": "microsoft", "error_type": type(e).__name__},
            )

    def _get_native_tools(self) -> list[str]:
        """Return registered tool names."""
        return [t.name for t in self._tools]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register a new tool and recreate the SDK agent."""
        self._tools.append(tool)
        self._create_sdk_agent()

    def reset_session(self) -> None:
        """Create a new session, discarding conversation history."""
        self._session = self._sdk_agent.create_session()
        logger.info("Session reset for agent '%s'", self.name)

    def close(self) -> None:
        """Release resources."""
        super().close()
        self._session = None

    def __repr__(self) -> str:
        return f"MicrosoftGoalSeekingAgent(name={self.name!r}, model={self.model!r})"


__all__ = ["MicrosoftGoalSeekingAgent"]
