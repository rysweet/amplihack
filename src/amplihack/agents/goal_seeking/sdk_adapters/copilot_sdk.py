"""GitHub Copilot SDK implementation of GoalSeekingAgent.

Uses the github-copilot-sdk package (CopilotClient + CopilotSession) for
real agent execution via JSON-RPC over stdio.

Provides native tools: file_system, git, web_requests (via Copilot CLI).
Custom learning tools registered as copilot.types.Tool with async handlers.
Event-based response tracking and tool usage monitoring.

Install: pip install github-copilot-sdk
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import types
from pathlib import Path
from typing import Any, Self

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = float(os.environ.get("COPILOT_AGENT_TIMEOUT", "300"))
_MAX_TIMEOUT = 600.0

# Try importing GitHub Copilot SDK
try:
    from copilot import CopilotClient
    from copilot.types import (
        SessionConfig,
        SystemMessageAppendConfig,
        ToolInvocation,
        ToolResult,
    )
    from copilot.types import Tool as CopilotTool

    HAS_COPILOT_SDK = True
except ImportError:
    HAS_COPILOT_SDK = False
    logger.debug("github-copilot-sdk not installed. Install with: pip install github-copilot-sdk")


def _make_tool_handler(agent_tool: AgentTool):
    """Create an async Copilot tool handler from an AgentTool.

    The handler receives a ToolInvocation and returns a ToolResult.
    Wraps the AgentTool.function, converting arguments and results
    to the Copilot SDK wire format.
    """

    async def handler(invocation: ToolInvocation) -> ToolResult:
        try:
            args = invocation.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {"input": args}

            result = (
                agent_tool.function(**args) if isinstance(args, dict) else agent_tool.function(args)
            )

            # Handle async functions
            if asyncio.iscoroutine(result):
                result = await result

            text = json.dumps(result) if not isinstance(result, str) else result
            return ToolResult(
                textResultForLlm=text,
                resultType="success",
            )
        except Exception as exc:
            logger.warning("Tool '%s' failed: %s", agent_tool.name, exc)
            return ToolResult(
                textResultForLlm="Tool invocation failed.",
                resultType="failure",
                error=str(exc),
            )

    return handler


def _agent_tool_to_copilot_tool(agent_tool: AgentTool) -> CopilotTool:
    """Convert an AgentTool to a Copilot SDK Tool."""
    return CopilotTool(
        name=agent_tool.name,
        description=agent_tool.description,
        handler=_make_tool_handler(agent_tool),
        parameters=agent_tool.parameters,
    )


class CopilotGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the GitHub Copilot SDK.

    Features:
    - Real SDK integration via CopilotClient (JSON-RPC over stdio)
    - Session management with lazy initialization
    - Tool mapping: AgentTool -> copilot.types.Tool with async handlers
    - 7 learning tools (learn, search, explain, verify, find_gaps, store, summary)
    - Configurable model (COPILOT_MODEL env) and timeout (max 600s)
    - Event-based tool usage tracking via SessionEventType
    - Generic error messages (no internal details exposed)
    - Security: no eval(), bounded timeouts, input validation
    - Async context manager support

    Example:
        >>> async with CopilotGoalSeekingAgent(name="learner") as agent:
        ...     result = await agent.run("Learn about quantum computing")
        ...     print(result.response)
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        streaming: bool = False,
        timeout: float | None = None,
        cli_path: str | None = None,
        **kwargs: Any,
    ):
        if not HAS_COPILOT_SDK:
            raise ImportError(
                "github-copilot-sdk not installed. Install with: pip install github-copilot-sdk"
            )

        # Resolve model from env or default
        self._model = model or os.environ.get("COPILOT_MODEL", "gpt-4.1")
        self._streaming = streaming
        self._cli_path = cli_path

        # Clamp timeout to [1, 600]
        raw_timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
        self._timeout = max(1.0, min(float(raw_timeout), _MAX_TIMEOUT))

        # Lazy-initialized client and session
        self._client: CopilotClient | None = None
        self._session: Any = None  # CopilotSession
        self._copilot_tools: list[CopilotTool] = []
        self._session_config: SessionConfig | None = None

        # For RUF006 compliance: track background cleanup tasks
        self._cleanup_task: asyncio.Task[Any] | None = None

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.COPILOT,
            model=self._model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Build SessionConfig and convert tools to Copilot format.

        Does NOT start the client - that happens lazily in _ensure_client().
        """
        # Convert all registered AgentTools to Copilot tools
        self._copilot_tools = [_agent_tool_to_copilot_tool(t) for t in self._tools]

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Build session config
        self._session_config = SessionConfig(
            model=self._model,
            tools=self._copilot_tools,
            system_message=SystemMessageAppendConfig(
                mode="append",
                content=system_prompt,
            ),
            streaming=self._streaming,
        )

    def _build_system_prompt(self) -> str:
        """Build goal-seeking system prompt with tool descriptions."""
        tool_list = "\n".join(f"- {t.name}: {t.description}" for t in self._tools)

        base = (
            "You are a goal-seeking learning agent. Your capabilities:\n\n"
            "GOAL SEEKING:\n"
            "1. Determine the user's intent from their message\n"
            "2. Form a specific, evaluable goal\n"
            "3. Make a plan to achieve the goal\n"
            "4. Execute the plan iteratively, adjusting based on results\n"
            "5. Evaluate whether the goal was achieved\n\n"
            "AVAILABLE LEARNING TOOLS:\n"
            f"{tool_list}\n\n"
            "LEARNING:\n"
            "- Use learn_from_content to extract and store facts from text\n"
            "- Use search_memory to retrieve relevant stored knowledge\n"
            "- Use verify_fact to check claims against your knowledge\n"
            "- Use find_knowledge_gaps to identify what you don't know\n\n"
            "TEACHING:\n"
            "- Use explain_knowledge to generate explanations at varying depth\n"
            "- Adapt your explanations to the learner's level\n\n"
            "APPLYING:\n"
            "- Use stored knowledge to solve new problems\n"
            "- Verify your work using verify_fact and search_memory\n"
        )

        if self.instructions:
            base += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return base

    async def _ensure_client(self) -> None:
        """Lazily initialize CopilotClient and create a session.

        Idempotent: does nothing if already connected.
        """
        if self._session is not None:
            return

        client_opts = {}
        if self._cli_path:
            client_opts["cli_path"] = self._cli_path

        self._client = CopilotClient(client_opts or None)
        await self._client.start()

        if self._session_config is None:
            self._create_sdk_agent()

        self._session = await self._client.create_session(self._session_config)

        # Track tool usage via events
        self._tools_used: list[str] = []

        def _track_tools(event: Any) -> None:
            try:
                if hasattr(event, "type") and "tool" in str(event.type).lower():
                    tool_name = getattr(getattr(event, "data", None), "tool_name", None)
                    if tool_name:
                        self._tools_used.append(str(tool_name))
            except Exception:
                pass  # Event tracking is best-effort

        self._session.on(_track_tools)

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Copilot SDK send_and_wait loop.

        Args:
            task: The prompt/task to execute
            max_turns: Maximum conversation turns (currently single-turn)

        Returns:
            AgentResult with response, tools used, and metadata
        """
        try:
            await self._ensure_client()
            self._tools_used = []

            response = await self._session.send_and_wait(
                {"prompt": task},
                timeout=self._timeout,
            )

            content = self._extract_response_content(response)

            return AgentResult(
                response=content,
                goal_achieved=bool(content and len(content) > 0),
                tools_used=list(self._tools_used),
                turns=1,
                metadata={
                    "sdk": "copilot",
                    "model": self._model,
                    "timeout": self._timeout,
                },
            )

        except TimeoutError:
            logger.warning("Copilot SDK timed out after %.1fs", self._timeout)
            return AgentResult(
                response="Agent execution timed out.",
                goal_achieved=False,
                metadata={"sdk": "copilot", "error": "timeout"},
            )
        except Exception as exc:
            logger.error("Copilot SDK agent run failed: %s", exc)
            return AgentResult(
                response="Agent execution encountered an error.",
                goal_achieved=False,
                metadata={"sdk": "copilot", "error": str(type(exc).__name__)},
            )

    @staticmethod
    def _extract_response_content(response: Any) -> str:
        """Extract text content from a Copilot SessionEvent response.

        The send_and_wait method returns the last assistant message event.
        Content is in event.data.content.
        """
        if response is None:
            return ""

        # Direct content attribute path: event.data.content
        data = getattr(response, "data", None)
        if data is not None:
            content = getattr(data, "content", None)
            if content is not None:
                return str(content)

        # Fallback: dict-like access
        if isinstance(response, dict):
            data_dict = response.get("data", {})
            if isinstance(data_dict, dict):
                return str(data_dict.get("content", ""))

        # Last resort: string representation
        return str(response) if response else ""

    def _get_native_tools(self) -> list[str]:
        """Return Copilot CLI native tools."""
        return ["file_system", "git", "web_requests"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register a new tool and invalidate the current session.

        The session must be recreated for the new tool to take effect.
        """
        self._tools.append(tool)
        self._copilot_tools.append(_agent_tool_to_copilot_tool(tool))
        # Invalidate session config so it's rebuilt with new tools
        self._session_config = None
        # Invalidate session so next _ensure_client() creates a new one
        self._session = None

    async def _destroy_session(self) -> None:
        """Destroy the current Copilot session."""
        if self._session is not None:
            try:
                await self._session.destroy()
            except Exception as exc:
                logger.debug("Session destroy error (ignored): %s", exc)
            finally:
                self._session = None

    async def _stop_client(self) -> None:
        """Stop the CopilotClient, destroying session first."""
        await self._destroy_session()
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception:
                try:
                    await self._client.force_stop()
                except Exception as exc:
                    logger.debug("Force stop error (ignored): %s", exc)
            finally:
                self._client = None

    def close(self) -> None:
        """Release all resources (sync wrapper for async cleanup)."""
        super().close()
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._stop_client())
        except RuntimeError:
            # No running loop - use asyncio.run for sync context
            try:
                asyncio.run(self._stop_client())
            except Exception as exc:
                logger.debug("Sync close error (ignored): %s", exc)

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit - clean up resources."""
        await self._stop_client()


__all__ = ["CopilotGoalSeekingAgent", "HAS_COPILOT_SDK"]
