"""Agent invocation wrapper for Copilot CLI.

Philosophy:
- Zero-BS implementation - all functions work
- Clear public API for agent discovery and invocation
- Self-contained module with standard library only

Public API:
    invoke_copilot_agent: Invoke a Copilot agent with a task
    discover_agents: Discover available agents from REGISTRY.json
    list_agents: List all available agents
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .errors import InvocationError, InstallationError


@dataclass
class AgentInfo:
    """Agent metadata from REGISTRY.json.

    Attributes:
        name: Agent name (e.g., "architect")
        path: Relative path to agent file
        description: Agent description
        tags: Agent tags
        invocable_by: What can invoke this agent
    """

    name: str
    path: str
    description: str
    tags: List[str]
    invocable_by: List[str]


@dataclass
class AgentInvocationResult:
    """Result from agent invocation.

    Attributes:
        success: Whether invocation succeeded
        agent_name: Name of invoked agent
        output: Agent output (stdout)
        error: Error output (stderr)
        exit_code: Command exit code
    """

    success: bool
    agent_name: str
    output: str
    error: str
    exit_code: int


def check_copilot() -> bool:
    """Check if Copilot CLI is installed.

    Returns:
        True if copilot command is available

    Example:
        >>> if check_copilot():
        ...     print("Copilot CLI is installed")
    """
    try:
        subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def discover_agents(
    registry_path: Path = Path(".github/agents/REGISTRY.json"),
) -> Dict[str, AgentInfo]:
    """Discover available agents from REGISTRY.json.

    Args:
        registry_path: Path to REGISTRY.json file

    Returns:
        Dictionary mapping agent name to AgentInfo

    Raises:
        FileNotFoundError: If REGISTRY.json doesn't exist
        ValueError: If REGISTRY.json is invalid

    Example:
        >>> agents = discover_agents()
        >>> agents["architect"].description
        'General architecture and design agent...'
    """
    if not registry_path.exists():
        raise FileNotFoundError(
            f"Agent registry not found: {registry_path}\n"
            f"Run 'amplihack sync-agents' to create it"
        )

    try:
        with open(registry_path, "r") as f:
            registry = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid REGISTRY.json: {str(e)}") from e

    agents = {}
    for agent_key, agent_data in registry.get("agents", {}).items():
        # Skip non-invocable entries (like README)
        if agent_key == "README" or not agent_data.get("path"):
            continue

        # Extract agent name from path or key
        name = agent_data.get("name", agent_key)

        agents[name] = AgentInfo(
            name=name,
            path=agent_data["path"],
            description=agent_data.get("description", ""),
            tags=agent_data.get("tags", []),
            invocable_by=agent_data.get("invocable_by", []),
        )

    return agents


def list_agents(registry_path: Path = Path(".github/agents/REGISTRY.json")) -> List[AgentInfo]:
    """List all available agents.

    Args:
        registry_path: Path to REGISTRY.json file

    Returns:
        List of AgentInfo objects sorted by name

    Example:
        >>> agents = list_agents()
        >>> for agent in agents:
        ...     print(f"{agent.name}: {agent.description}")
    """
    agents_dict = discover_agents(registry_path)
    return sorted(agents_dict.values(), key=lambda a: a.name)


def invoke_copilot_agent(
    agent_name: str,
    task: str,
    registry_path: Path = Path(".github/agents/REGISTRY.json"),
    additional_files: Optional[List[str]] = None,
    allow_all_tools: bool = True,
    verbose: bool = False,
) -> AgentInvocationResult:
    """Invoke a Copilot agent with a task.

    Pattern: copilot --allow-all-tools -p "task" -f @.github/agents/<path>/<agent>.md

    Args:
        agent_name: Name of agent to invoke (e.g., "architect")
        task: Task description for the agent
        registry_path: Path to REGISTRY.json
        additional_files: Additional files to include with -f flag
        allow_all_tools: Allow all tools (default True)
        verbose: Show detailed output (default False)

    Returns:
        AgentInvocationResult with invocation details

    Raises:
        InstallationError: If Copilot CLI not installed
        InvocationError: If agent not found or invocation fails

    Example:
        >>> result = invoke_copilot_agent(
        ...     "architect",
        ...     "Design authentication system"
        ... )
        >>> if result.success:
        ...     print(result.output)
    """
    # Check if Copilot CLI is installed
    if not check_copilot():
        raise InstallationError(
            "Copilot CLI not installed. Install with:\n"
            "  npm install -g @github/copilot"
        )

    # Discover agents
    try:
        agents = discover_agents(registry_path)
    except (FileNotFoundError, ValueError) as e:
        raise InvocationError(str(e)) from e

    # Find agent
    if agent_name not in agents:
        available = ", ".join(sorted(agents.keys()))
        raise InvocationError(
            f"Agent '{agent_name}' not found.\n"
            f"Available agents: {available}"
        )

    agent = agents[agent_name]

    # Build command
    cmd = ["copilot"]

    # Add tool permissions
    if allow_all_tools:
        cmd.append("--allow-all-tools")

    # Add agent file
    agent_path = Path(".github/agents") / agent.path
    if not agent_path.exists():
        raise InvocationError(
            f"Agent file not found: {agent_path}\n"
            f"Run 'amplihack sync-agents' to create it"
        )

    cmd.extend(["-f", f"@{agent_path}"])

    # Add additional files
    if additional_files:
        for file in additional_files:
            cmd.extend(["-f", f"@{file}"])

    # Add task prompt
    cmd.extend(["-p", task])

    if verbose:
        print(f"Executing: {' '.join(cmd)}")

    # Execute command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        return AgentInvocationResult(
            success=result.returncode == 0,
            agent_name=agent_name,
            output=result.stdout,
            error=result.stderr,
            exit_code=result.returncode,
        )

    except Exception as e:
        raise InvocationError(f"Failed to invoke agent: {str(e)}") from e


__all__ = [
    "AgentInfo",
    "AgentInvocationResult",
    "invoke_copilot_agent",
    "discover_agents",
    "list_agents",
    "check_copilot",
]
