"""Microsoft Agent Framework implementation of GoalSeekingAgent.

Uses the agent-framework package (Microsoft's unified AI agent platform).
Real API surface:
- agent_framework.Agent: Full agent with middleware, telemetry, tool invocation
- agent_framework.FunctionTool / tool(): Tool registration
- agent_framework.AgentSession: Multi-turn state management
- agent_framework.openai.OpenAIChatClient: OpenAI model client
- agent_framework.azure.AzureOpenAIChatClient: Azure OpenAI model client

Install: pip install agent-framework

When agent-framework is not importable (e.g., binary incompatibility),
falls back to mock execution for testing and development.
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
# Optional import of Microsoft Agent Framework
# ---------------------------------------------------------------------------
_HAS_AGENT_FRAMEWORK = False
AFAgent = None  # type: ignore[assignment]
af_tool = None  # type: ignore[assignment]
OpenAIChatClient = None  # type: ignore[assignment]

try:
    # agent-framework >= 1.0.0b260212 uses ChatAgent instead of Agent
    from agent_framework import (
        ChatAgent as AFAgent,  # type: ignore[no-redef,assignment,import-not-found]
    )
    from agent_framework import (
        ai_function as af_tool,  # type: ignore[no-redef,assignment,import-not-found]
    )
    from agent_framework.openai import (
        OpenAIChatClient,  # type: ignore[no-redef,assignment,import-not-found]
    )

    _HAS_AGENT_FRAMEWORK = True
    logger.debug("agent-framework available (ChatAgent API)")
except ImportError:
    try:
        # Older API
        from agent_framework import (
            Agent as AFAgent,  # type: ignore[no-redef,assignment,import-not-found]
        )
        from agent_framework import (
            tool as af_tool,  # type: ignore[no-redef,assignment,import-not-found]
        )
        from agent_framework.openai import (
            OpenAIChatClient,  # type: ignore[no-redef,assignment,import-not-found]
        )

        _HAS_AGENT_FRAMEWORK = True
        logger.debug("agent-framework available (legacy Agent API)")
    except Exception:
        logger.debug(
            "agent-framework not importable. "
            "MicrosoftGoalSeekingAgent will use mock execution mode. "
            "Install with: pip install agent-framework"
        )


# ---------------------------------------------------------------------------
# Prompt template loading
# ---------------------------------------------------------------------------
_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts" / "sdk"


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/sdk/ directory.

    Falls back to empty string if file not found (never crashes).
    """
    path = _PROMPT_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    logger.debug("Prompt template not found: %s", path)
    return ""


# ---------------------------------------------------------------------------
# Tool wrapping helpers
# ---------------------------------------------------------------------------


def _build_learning_tools(agent_ref: GoalSeekingAgent) -> list[Any]:
    """Wrap AgentTools as FunctionTool objects for the real SDK.

    Each base-class AgentTool is converted into a FunctionTool via the
    @tool decorator so the Agent Framework can auto-invoke them.

    Args:
        agent_ref: The agent whose _tools to wrap.

    Returns:
        List of FunctionTool instances, or list of plain functions
        if agent_framework is not importable.
    """
    wrapped: list[Any] = []
    for tool_def in agent_ref._tools:
        fn = _wrap_tool(tool_def, agent_ref)
        wrapped.append(fn)
    return wrapped


def _wrap_tool(tool_def: AgentTool, agent_ref: GoalSeekingAgent) -> Any:
    """Wrap a single AgentTool into a FunctionTool (or plain callable).

    When agent-framework is available, uses the @tool() decorator.
    Otherwise, returns a plain wrapper function.
    """
    original_fn = tool_def.function
    name = tool_def.name
    description = tool_def.description

    # Build a wrapper that accepts kwargs matching the JSON schema
    def wrapper(**kwargs: Any) -> str:
        result = original_fn(**kwargs)
        if isinstance(result, (dict, list)):
            return json.dumps(result)
        return str(result)

    wrapper.__name__ = name
    wrapper.__qualname__ = name
    wrapper.__doc__ = description

    if _HAS_AGENT_FRAMEWORK:
        return af_tool(wrapper, name=name, description=description)
    return wrapper


# ---------------------------------------------------------------------------
# MicrosoftGoalSeekingAgent
# ---------------------------------------------------------------------------


class MicrosoftGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on Microsoft Agent Framework.

    Features:
    - Real agent-framework.Agent with middleware and telemetry
    - FunctionTool / @tool() decorator for learning tool registration
    - AgentSession for multi-turn conversation state
    - OpenAIChatClient for OpenAI models (GPT-4o, etc.)
    - AzureOpenAIChatClient for Azure deployments
    - Mock execution fallback when SDK not importable
    - Prompt templates loaded from markdown files
    - amplihack-memory-lib (MemoryRetriever) for persistent knowledge

    Example:
        >>> agent = MicrosoftGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent.",
        ... )
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
        # Resolve model: env var > explicit > default
        resolved_model = model or os.environ.get("MICROSOFT_AGENT_MODEL", "gpt-4o")

        self._session: Any = None
        self._session_id: str = ""
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

    # ------------------------------------------------------------------
    # SDK-specific initialization
    # ------------------------------------------------------------------

    def _create_sdk_agent(self) -> None:
        """Initialize Microsoft Agent Framework agent.

        Creates:
        - OpenAIChatClient (or mock) as the model backend
        - FunctionTool wrappers for all 7 learning tools
        - Agent instance with tools and system prompt
        - AgentSession for multi-turn state
        """
        system_prompt = self._build_system_prompt()
        tools = _build_learning_tools(self)

        if _HAS_AGENT_FRAMEWORK:
            # Build real SDK agent (requires OPENAI_API_KEY)
            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                logger.info(
                    "OPENAI_API_KEY not set. Agent '%s' initialized in mock mode.",
                    self.name,
                )
                self._sdk_agent = None
                self._session = None
                self._session_id = "mock-session-no-key"
                return

            try:
                client = OpenAIChatClient(model_id=self.model, api_key=api_key)
                self._sdk_agent = AFAgent(
                    client=client,
                    instructions=system_prompt,
                    name=self.name,
                    tools=tools,
                )
                self._session = self._sdk_agent.create_session()
                self._session_id = getattr(self._session, "id", "default")
            except Exception as e:
                logger.warning("Failed to initialize real SDK agent: %s. Using mock mode.", e)
                self._sdk_agent = None
                self._session = None
                self._session_id = "mock-session-error"
        else:
            # Mock mode: store config for mock execution
            self._sdk_agent = None
            self._session = None
            self._session_id = "mock-session"
            logger.info(
                "Microsoft Agent Framework not available. Agent '%s' initialized in mock mode.",
                self.name,
            )

    def _build_system_prompt(self) -> str:
        """Build system prompt from template + custom instructions.

        Loads the prompt from prompts/sdk/microsoft_system.md if available,
        otherwise uses a sensible default.
        """
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

    # ------------------------------------------------------------------
    # Agent execution
    # ------------------------------------------------------------------

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Microsoft Agent Framework loop.

        When agent-framework is available, calls agent.run() with the
        session for multi-turn state. Otherwise, falls back to mock
        execution that routes by keyword.

        Args:
            task: The task/prompt to execute.
            max_turns: Maximum agent loop iterations.

        Returns:
            AgentResult with response, tools used, and metadata.
        """
        if not _HAS_AGENT_FRAMEWORK or self._sdk_agent is None:
            return await self._run_mock(task, max_turns)

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
                    # Track tool usage
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
                metadata={
                    "sdk": "microsoft",
                    "model": self.model,
                    "session_id": self._session_id,
                    "mock": False,
                },
            )
        except Exception as e:
            logger.error("Microsoft Agent Framework run failed: %s", e)
            return AgentResult(
                response="Agent execution failed due to an internal error.",
                goal_achieved=False,
                metadata={"sdk": "microsoft", "error_type": type(e).__name__, "mock": False},
            )

    async def _run_mock(self, task: str, max_turns: int = 10) -> AgentResult:
        """Mock execution when agent-framework is not importable.

        Routes by keyword to exercise the tool implementations,
        providing useful behavior for tests and development.
        """
        task_lower = task.lower()
        tools_used: list[str] = []
        response_parts: list[str] = []

        # Route by keyword (priority order matters: more specific first)
        if "gap" in task_lower:
            result = self._tool_find_gaps(topic=task)
            tools_used.append("find_knowledge_gaps")
            response_parts.append(json.dumps(result))

        elif "verify" in task_lower or "check" in task_lower:
            result = self._tool_verify(fact=task)
            tools_used.append("verify_fact")
            response_parts.append(json.dumps(result))

        elif "explain" in task_lower:
            result = self._tool_explain(topic=task)
            tools_used.append("explain_knowledge")
            response_parts.append(str(result))

        elif "summary" in task_lower or "overview" in task_lower:
            result = self._tool_summary()
            tools_used.append("get_memory_summary")
            response_parts.append(json.dumps(result))

        elif "store" in task_lower or "remember" in task_lower:
            result = self._tool_store(context="stored_task", fact=task, confidence=0.8)
            tools_used.append("store_fact")
            response_parts.append(json.dumps(result))

        elif "search" in task_lower or "what" in task_lower or "find" in task_lower:
            result = self._tool_search(query=task, limit=10)
            tools_used.append("search_memory")
            response_parts.append(json.dumps(result))

        elif "learn" in task_lower:
            result = self._tool_learn(content=task)
            tools_used.append("learn_from_content")
            response_parts.append(json.dumps(result))

        else:
            # Default: learn then search
            learn_result = self._tool_learn(content=task)
            tools_used.append("learn_from_content")
            search_result = self._tool_search(query=task, limit=5)
            tools_used.append("search_memory")
            response_parts.append(
                f"Learned and searched. Learn: {json.dumps(learn_result)}, "
                f"Search: {json.dumps(search_result)}"
            )

        response = "\n".join(response_parts)
        return AgentResult(
            response=response,
            goal_achieved=True,
            tools_used=tools_used,
            turns=1,
            metadata={
                "sdk": "microsoft",
                "model": self.model,
                "session_id": self._session_id,
                "mock": True,
            },
        )

    # ------------------------------------------------------------------
    # Native tools
    # ------------------------------------------------------------------

    def _get_native_tools(self) -> list[str]:
        """Return MS Agent Framework native tool names.

        In the real SDK, the available tools depend on the model client
        and any MCP servers connected. Here we list the learning tools
        that we register.
        """
        return [t.name for t in self._tools]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register an additional custom tool with the SDK.

        Adds the tool to our registry, then recreates the SDK agent
        so the new tool is included in the next run.
        """
        self._tools.append(tool)
        self._create_sdk_agent()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def get_session_id(self) -> str:
        """Return the current session ID."""
        return self._session_id

    def reset_session(self) -> None:
        """Create a new session, discarding conversation history."""
        if _HAS_AGENT_FRAMEWORK and self._sdk_agent is not None:
            self._session = self._sdk_agent.create_session()
            self._session_id = getattr(self._session, "id", "reset")
        else:
            self._session_id = "mock-session-reset"
        logger.info("Session reset for agent '%s'", self.name)

    def close(self) -> None:
        """Release resources."""
        super().close()
        self._session = None
        self._session_id = ""

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def is_mock_mode(self) -> bool:
        """Whether the agent is running in mock mode."""
        return not _HAS_AGENT_FRAMEWORK or self._sdk_agent is None

    def __repr__(self) -> str:
        mode = "mock" if self.is_mock_mode else "real"
        return f"MicrosoftGoalSeekingAgent(name={self.name!r}, model={self.model!r}, mode={mode!r})"


__all__ = ["MicrosoftGoalSeekingAgent", "_HAS_AGENT_FRAMEWORK"]
