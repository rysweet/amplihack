"""Claude Agent SDK implementation of GoalSeekingAgent.

Uses the claude-agent-sdk package (Anthropic's official Claude Code SDK)
or the claude-agents package if available.

Provides native tools: bash, read_file, write_file, edit_file, glob, grep.
Custom learning tools registered via the SDK's tool system.
Subagent support for teaching sessions.

Install: pip install claude-agent-sdk
"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# Try importing Claude Agent SDK (try both package names)
HAS_CLAUDE_SDK = False
_CLAUDE_SDK_VARIANT = ""  # "claude_agents" or "claude_agent_sdk"

try:
    from claude_agents import Agent as _ClaudeAgentsAgent  # type: ignore[import-not-found]
    from claude_agents.tools import Tool as _ClaudeAgentsTool  # type: ignore[import-not-found]

    HAS_CLAUDE_SDK = True
    _CLAUDE_SDK_VARIANT = "claude_agents"
except ImportError:
    _ClaudeAgentsAgent = None  # type: ignore[assignment,misc]
    _ClaudeAgentsTool = None  # type: ignore[assignment,misc]
    try:
        from claude_agent_sdk import ClaudeSDKClient  # type: ignore[import-not-found]

        HAS_CLAUDE_SDK = True
        _CLAUDE_SDK_VARIANT = "claude_agent_sdk"
        logger.debug("Using claude-agent-sdk (ClaudeSDKClient)")
    except ImportError:
        ClaudeSDKClient = None  # type: ignore[assignment,misc]
        logger.debug(
            "Neither claude-agents nor claude-agent-sdk installed. "
            "Install with: pip install claude-agent-sdk"
        )


class ClaudeGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the Claude Agent SDK.

    Features:
    - Native tools: bash, read_file, write_file, edit_file, glob, grep
    - Custom learning tools (7 registered via AgentTool -> ClaudeTool)
    - Subagent support for teaching sessions
    - MCP integration for external tool servers
    - Hooks for logging and validation
    - amplihack-memory-lib for persistent knowledge

    Example:
        >>> agent = ClaudeGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent that acquires knowledge.",
        ... )
        >>> result = await agent.run("Learn about the 2026 Winter Olympics")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str = "claude-sonnet-4-5-20250929",
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        allowed_native_tools: list[str] | None = None,
    ):
        if not HAS_CLAUDE_SDK:
            raise ImportError(
                "Claude Agent SDK not installed. Install with: pip install claude-agents"
            )

        self._allowed_native_tools = allowed_native_tools or [
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "glob",
            "grep",
        ]

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.CLAUDE,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Claude Agent SDK agent with tools.

        Supports two SDK variants:
        - claude_agents (original): Agent(model, system, tools, allowed_tools)
        - claude_agent_sdk (current): ClaudeSDKClient-based async API
        """
        system = self._build_system_prompt()

        if _CLAUDE_SDK_VARIANT == "claude_agents":
            # Original claude-agents package API
            claude_tools = []
            for tool_def in self._tools:
                claude_tool = _ClaudeAgentsTool(
                    name=tool_def.name,
                    description=tool_def.description,
                    input_schema=tool_def.parameters,
                    function=tool_def.function,
                )
                claude_tools.append(claude_tool)

            self._sdk_agent = _ClaudeAgentsAgent(
                model=self.model,
                system=system,
                tools=claude_tools,
                allowed_tools=self._allowed_native_tools + [t.name for t in self._tools],
            )
        elif _CLAUDE_SDK_VARIANT == "claude_agent_sdk":
            # claude-agent-sdk: async client that runs Claude Code sessions
            # This SDK runs Claude Code as a subprocess, not a direct LLM call.
            # Tools are provided via MCP servers, not inline functions.
            # We store config for use in _run_sdk_agent.
            self._sdk_agent = {
                "variant": "claude_agent_sdk",
                "model": self.model,
                "system": system,
                "tool_names": [t.name for t in self._tools],
            }
        else:
            self._sdk_agent = None

    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for goal-seeking learning agent."""
        base = (
            "You are a goal-seeking learning agent. Your capabilities:\n\n"
            "GOAL SEEKING:\n"
            "1. Determine the user's intent from their message\n"
            "2. Form a specific, evaluable goal\n"
            "3. Make a plan to achieve the goal\n"
            "4. Execute the plan iteratively, adjusting based on results\n"
            "5. Evaluate whether the goal was achieved\n\n"
            "LEARNING:\n"
            "- Use learn_from_content to extract and store facts from text\n"
            "- Use search_memory to retrieve relevant stored knowledge\n"
            "- Use verify_fact to check claims against your knowledge\n"
            "- Use find_knowledge_gaps to identify what you don't know\n\n"
            "TEACHING:\n"
            "- Use explain_knowledge to generate explanations at varying depth\n"
            "- Adapt your explanations to the learner's level\n"
            "- Ask probing questions to verify understanding\n\n"
            "APPLYING:\n"
            "- Use stored knowledge to solve new problems\n"
            "- Use native tools (bash, file operations) to take real actions\n"
            "- Verify your work using verify_fact and search_memory\n"
        )

        if self.instructions:
            base += f"\nADDITIONAL INSTRUCTIONS:\n{self.instructions}\n"

        return base

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Claude Agent SDK loop.

        Supports two SDK variants:
        - claude_agents: Synchronous Agent.run(task)
        - claude_agent_sdk: Async ClaudeSDKClient session
        """
        try:
            if (
                isinstance(self._sdk_agent, dict)
                and self._sdk_agent.get("variant") == "claude_agent_sdk"
            ):
                # claude-agent-sdk variant: use ClaudeSDKClient
                return await self._run_claude_agent_sdk(task)

            # Original claude-agents variant
            result = self._sdk_agent.run(task)
            return AgentResult(
                response=result.response if hasattr(result, "response") else str(result),
                goal_achieved=True,
                tools_used=[],
                turns=1,
                metadata={"sdk": "claude", "variant": "claude_agents"},
            )
        except Exception as e:
            logger.error("Claude SDK agent run failed: %s", e)
            return AgentResult(
                response=f"Agent execution failed: {e}",
                goal_achieved=False,
                metadata={"sdk": "claude", "error": str(e)},
            )

    async def _run_claude_agent_sdk(self, task: str) -> AgentResult:
        """Execute task through claude-agent-sdk ClaudeSDKClient.

        This SDK runs Claude Code as a subprocess, so it requires the Claude
        Code CLI to be installed and configured.
        """
        try:
            from claude_agent_sdk import ClaudeSDKClient

            client = ClaudeSDKClient()
            messages = []
            async with client.create_session(
                model=self.model,
                system_prompt=self._sdk_agent["system"],
            ) as session:
                async for event in session.send_message(task):
                    if hasattr(event, "content"):
                        messages.append(str(event.content))

            response_text = "\n".join(messages) if messages else "No response"
            return AgentResult(
                response=response_text,
                goal_achieved=bool(messages),
                tools_used=[],
                turns=1,
                metadata={"sdk": "claude", "variant": "claude_agent_sdk"},
            )
        except Exception as e:
            logger.error("claude-agent-sdk run failed: %s", e)
            return AgentResult(
                response=f"Claude Agent SDK execution failed: {e}",
                goal_achieved=False,
                metadata={"sdk": "claude", "variant": "claude_agent_sdk", "error": str(e)},
            )

    def _get_native_tools(self) -> list[str]:
        """Return Claude SDK native tools."""
        return ["bash", "read_file", "write_file", "edit_file", "glob", "grep"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register custom tool with Claude Agent SDK."""
        self._tools.append(tool)
        if self._sdk_agent:
            self._create_sdk_agent()


__all__ = ["ClaudeGoalSeekingAgent", "HAS_CLAUDE_SDK"]
