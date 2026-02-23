"""Tool Injector: SDK-specific tool injection for spawned agents.

Philosophy:
- Single responsibility: Inject SDK-native tools into agents
- Each SDK has its own set of native tools
- Tools are injected based on the agent's SDK type
- Keeps SDK-specific logic isolated from the spawner

Public API:
    inject_sdk_tools: Inject SDK-specific tools into a GoalSeekingAgent
    get_sdk_tool_names: Get the list of tool names for an SDK type
"""

from __future__ import annotations

import logging
from typing import Any

from ..sdk_adapters.base import AgentTool, SDKType

logger = logging.getLogger(__name__)


# SDK-specific tool definitions
# Each tool has a name, description, parameters schema, and a no-op function
# The actual implementations are provided by the SDK runtime

def _noop(**kwargs: Any) -> dict[str, Any]:
    """No-op placeholder function for SDK-native tools.

    These tools are descriptors; the actual execution happens in the SDK runtime.
    """
    return {"status": "sdk_native_tool", "note": "Executed by SDK runtime"}


# Claude SDK tools
_CLAUDE_TOOLS = [
    AgentTool(
        name="bash",
        description="Execute a bash command in a sandboxed environment",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"},
            },
            "required": ["command"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="read_file",
        description="Read the contents of a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="write_file",
        description="Write content to a file",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="edit_file",
        description="Edit a file with search and replace",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to edit"},
                "old_text": {"type": "string", "description": "Text to find"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
        function=_noop,
        category="sdk_native",
    ),
]

# Copilot SDK tools
_COPILOT_TOOLS = [
    AgentTool(
        name="file_system",
        description="Read, write, or list files and directories",
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "list"],
                    "description": "File system operation",
                },
                "path": {"type": "string", "description": "File or directory path"},
                "content": {"type": "string", "description": "Content for write operations"},
            },
            "required": ["operation", "path"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="git",
        description="Execute git operations",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Git command to execute"},
            },
            "required": ["command"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="web_requests",
        description="Make HTTP requests to external services",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET",
                },
            },
            "required": ["url"],
        },
        function=_noop,
        category="sdk_native",
    ),
]

# Microsoft SDK tools
_MICROSOFT_TOOLS = [
    AgentTool(
        name="agent_execute",
        description="Execute a task through the Microsoft Agent Framework",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task to execute"},
                "context": {"type": "string", "description": "Additional context"},
            },
            "required": ["task"],
        },
        function=_noop,
        category="sdk_native",
    ),
    AgentTool(
        name="agent_query",
        description="Query the agent framework for information",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Query to run"},
            },
            "required": ["query"],
        },
        function=_noop,
        category="sdk_native",
    ),
]

# Tool registry by SDK type
_SDK_TOOLS: dict[str, list[AgentTool]] = {
    SDKType.CLAUDE: _CLAUDE_TOOLS,
    SDKType.COPILOT: _COPILOT_TOOLS,
    SDKType.MICROSOFT: _MICROSOFT_TOOLS,
    SDKType.MINI: [],  # Mini SDK has no native tools
}


def get_sdk_tool_names(sdk_type: str | SDKType) -> list[str]:
    """Get the list of native tool names for an SDK type.

    Args:
        sdk_type: The SDK type (string or SDKType enum)

    Returns:
        List of tool name strings
    """
    sdk_type_str = sdk_type.value if isinstance(sdk_type, SDKType) else sdk_type
    tools = _SDK_TOOLS.get(sdk_type_str, [])
    return [t.name for t in tools]


def get_sdk_tools(sdk_type: str | SDKType) -> list[AgentTool]:
    """Get the native tools for an SDK type.

    Args:
        sdk_type: The SDK type (string or SDKType enum)

    Returns:
        List of AgentTool instances
    """
    sdk_type_str = sdk_type.value if isinstance(sdk_type, SDKType) else sdk_type
    return list(_SDK_TOOLS.get(sdk_type_str, []))


def inject_sdk_tools(agent: Any, sdk_type: str | SDKType) -> int:
    """Inject SDK-specific tools into an agent.

    Adds the SDK-native tools to the agent's tool list. The agent must
    have a _tools attribute (list of AgentTool) or a _register_tool_with_sdk
    method.

    Args:
        agent: A GoalSeekingAgent or compatible agent instance
        sdk_type: The SDK type to inject tools for

    Returns:
        Number of tools injected

    Example:
        >>> from ..sdk_adapters.base import GoalSeekingAgent, SDKType
        >>> # agent = create_agent("test", sdk_type=SDKType.CLAUDE)
        >>> # count = inject_sdk_tools(agent, SDKType.CLAUDE)
        >>> # print(f"Injected {count} tools")
    """
    tools = get_sdk_tools(sdk_type)

    if not tools:
        logger.debug("No native tools for SDK type: %s", sdk_type)
        return 0

    injected = 0

    # Check for existing tool names to avoid duplicates
    existing_names: set[str] = set()
    if hasattr(agent, "_tools"):
        existing_names = {t.name for t in agent._tools}

    for tool in tools:
        if tool.name in existing_names:
            logger.debug("Tool '%s' already registered, skipping", tool.name)
            continue

        if hasattr(agent, "_register_tool_with_sdk"):
            try:
                agent._register_tool_with_sdk(tool)
                injected += 1
            except Exception as e:
                logger.warning("Failed to inject tool '%s': %s", tool.name, e)
        elif hasattr(agent, "_tools"):
            agent._tools.append(tool)
            injected += 1
        else:
            logger.warning("Agent has no _tools or _register_tool_with_sdk method")
            break

    logger.info("Injected %d SDK tools (type=%s) into agent", injected, sdk_type)
    return injected


__all__ = ["inject_sdk_tools", "get_sdk_tools", "get_sdk_tool_names"]
