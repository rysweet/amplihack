"""Claude Agent SDK implementation of GoalSeekingAgent.

Uses the claude-agent-sdk package (Anthropic's official agent framework).
Provides native tools: Bash, Read, Write, Edit, Glob, Grep (PascalCase).
Custom learning tools registered via in-process MCP server.
Subagent support for teaching sessions.

Install: pip install claude-agent-sdk
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

logger = logging.getLogger(__name__)

# Try importing Claude Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        create_sdk_mcp_server,
        query,
        tool,
    )

    HAS_CLAUDE_SDK = True
except ImportError:
    HAS_CLAUDE_SDK = False
    logger.debug("claude-agent-sdk not installed. Install with: pip install claude-agent-sdk")


def _load_prompt_template(template_name: str) -> str:
    """Load a prompt template from prompts/sdk/ directory."""
    template_dir = Path(__file__).parent.parent / "prompts" / "sdk"
    template_path = template_dir / f"{template_name}.md"
    if template_path.exists():
        return template_path.read_text()
    return ""


def _create_learning_mcp_tools(agent: ClaudeGoalSeekingAgent) -> list:
    """Convert agent learning tools to SdkMcpTool instances via @tool decorator."""
    mcp_tools = []

    for agent_tool in agent._tools:
        # Create a closure to capture the current tool
        def make_handler(t):
            async def handler(**kwargs) -> dict[str, Any]:
                try:
                    result = t.function(**kwargs)
                    # Truncate large results
                    if isinstance(result, str) and len(result) > 10000:
                        result = result[:10000] + "... (truncated)"
                    if isinstance(result, dict):
                        return result
                    if isinstance(result, list):
                        return {"results": result}
                    return {"result": str(result)}
                except Exception as e:
                    return {"error": str(e)}

            return handler

        sdk_tool = tool(
            agent_tool.name,
            agent_tool.description,
            agent_tool.parameters,
        )(make_handler(agent_tool))
        mcp_tools.append(sdk_tool)

    return mcp_tools


class ClaudeGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent built on the Claude Agent SDK.

    Features:
    - Native tools: Bash, Read, Write, Edit, Glob, Grep (PascalCase)
    - Custom learning tools (7 registered via MCP server)
    - Subagent support for teaching sessions
    - MCP integration for external tool servers
    - amplihack-memory-lib for persistent knowledge

    Example:
        >>> agent = ClaudeGoalSeekingAgent(
        ...     name="learner",
        ...     instructions="You are a learning agent.",
        ... )
        >>> result = await agent.run("Learn about photosynthesis")
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        allowed_native_tools: list[str] | None = None,
        permission_mode: str | None = None,
        enable_teaching_subagent: bool = False,
        cwd: str | Path | None = None,
    ):
        if not HAS_CLAUDE_SDK:
            raise ImportError(
                "Claude Agent SDK not installed. Install with: pip install claude-agent-sdk"
            )

        self._allowed_native_tools = allowed_native_tools or [
            "Read",
            "Glob",
            "Grep",
        ]
        self._permission_mode = permission_mode or os.environ.get(
            "CLAUDE_SDK_PERMISSION_MODE", "bypassPermissions"
        )
        self._enable_teaching_subagent = enable_teaching_subagent
        self._cwd = cwd or os.getcwd()
        self._mcp_server = None
        self._mcp_server_name = f"learning_{name}"
        self._options = None

        # Override model from env if set
        env_model = os.environ.get("CLAUDE_SDK_MODEL")
        effective_model = env_model or model

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=SDKType.CLAUDE,
            model=effective_model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize Claude Agent SDK agent with MCP tools."""
        # Create MCP tools from learning tools
        mcp_tools = _create_learning_mcp_tools(self)

        # Create in-process MCP server
        self._mcp_server = create_sdk_mcp_server(
            name=self._mcp_server_name,
            tools=mcp_tools,
        )

        # Build allowed tools list
        mcp_tool_names = [f"mcp__{self._mcp_server_name}__{t.name}" for t in self._tools]
        allowed_tools = list(self._allowed_native_tools) + mcp_tool_names

        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Build max_turns from env
        max_turns = None
        env_turns = os.environ.get("CLAUDE_SDK_MAX_TURNS")
        if env_turns:
            try:
                max_turns = int(env_turns)
            except ValueError:
                pass

        # Build agents config for teaching subagent
        agents = None
        if self._enable_teaching_subagent:
            teaching_prompt = _load_prompt_template("teaching_system")
            if teaching_prompt:
                agents = {
                    "teaching_agent": {
                        "system_prompt": teaching_prompt,
                        "allowed_tools": mcp_tool_names,
                    }
                }

        # Build options
        self._options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            mcp_servers={self._mcp_server_name: self._mcp_server},
            permission_mode=self._permission_mode,
            max_turns=max_turns,
            model=self.model,
            cwd=str(self._cwd),
            agents=agents,
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt from template + custom instructions."""
        template = _load_prompt_template("goal_seeking_system")
        if not template:
            template = (
                "You are a goal-seeking learning agent with persistent memory.\n"
                "Use your learning tools to acquire, verify, and apply knowledge.\n"
            )

        if self.instructions:
            template += f"\n## Additional Instructions\n{self.instructions}\n"

        return template

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through Claude Agent SDK query() loop."""
        try:
            response_text = ""
            tools_used = []
            turns = 0
            metadata = {"sdk": "claude"}

            async for message in query(task, self._options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text
                        elif isinstance(block, ToolUseBlock):
                            tools_used.append(block.name)
                elif isinstance(message, ResultMessage):
                    turns = message.num_turns or 0
                    metadata["cost_usd"] = message.total_cost_usd
                    metadata["session_id"] = message.session_id
                    if message.is_error:
                        return AgentResult(
                            response=response_text or str(message.result),
                            goal_achieved=False,
                            tools_used=tools_used,
                            turns=turns,
                            metadata=metadata,
                        )

            return AgentResult(
                response=response_text,
                goal_achieved=True,
                tools_used=tools_used,
                turns=turns,
                metadata=metadata,
            )
        except Exception as e:
            logger.error("Claude SDK agent run failed: %s", e)
            return AgentResult(
                response=f"Agent execution failed: {type(e).__name__}: {e}",
                goal_achieved=False,
                metadata={"sdk": "claude", "error": str(e)},
            )

    def _get_native_tools(self) -> list[str]:
        """Return Claude SDK native tools (PascalCase)."""
        return ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]

    def _register_tool_with_sdk(self, tool_def: AgentTool) -> None:
        """Register a custom tool with the Claude Agent SDK."""
        self._tools.append(tool_def)
        # Recreate MCP server with updated tools
        self._create_sdk_agent()

    def get_options(self) -> ClaudeAgentOptions:
        """Return current agent options (for testing/inspection)."""
        return self._options

    async def run_conversation(self, messages: list[str]) -> list[AgentResult]:
        """Multi-turn conversation using ClaudeSDKClient."""
        from claude_agent_sdk import ClaudeSDKClient

        results = []
        async with ClaudeSDKClient(self._options) as client:
            for msg in messages:
                response_text = ""
                async for message in client.send(msg):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text
                results.append(AgentResult(response=response_text, goal_achieved=True))
        return results


__all__ = [
    "ClaudeGoalSeekingAgent",
    "HAS_CLAUDE_SDK",
    "_create_learning_mcp_tools",
    "_load_prompt_template",
]
