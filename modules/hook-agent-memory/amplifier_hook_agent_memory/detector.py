"""
Agent reference detection in prompts.

Detects agent references like @agents/*.md and /slash-commands.
"""

import re

# Agent reference patterns
AGENT_REFERENCE_PATTERNS = [
    r"@\.?agents?/([^/\s]+)\.md",  # @agents/architect.md or @.agents/architect.md
    r"@[a-z-]+:agents?/([^/\s]+)",  # @bundle:agents/architect
    r"Include\s+@[^/]+/agents?/([^/\s]+)\.md",  # Include @bundle/agents/architect.md
    r"Use\s+([a-z-]+)\s+agent",  # Use architect agent
    r"/([a-z-]+)\s",  # Slash commands like /ultrathink, /fix
]

# Map slash commands to agent types
SLASH_COMMAND_AGENTS = {
    "ultrathink": "orchestrator",
    "fix": "fix-agent",
    "analyze": "analyzer",
    "improve": "reviewer",
    "socratic": "ambiguity",
    "debate": "multi-agent-debate",
    "reflect": "reflection",
    "explore": "explorer",
    "architect": "architect",
    "build": "builder",
    "test": "tester",
    "review": "reviewer",
}


def detect_agent_references(prompt: str) -> list[str]:
    """Detect agent references in a prompt.

    Args:
        prompt: The user prompt to analyze

    Returns:
        List of agent type names detected (e.g., ["architect", "builder"])
    """
    agents = set()

    for pattern in AGENT_REFERENCE_PATTERNS:
        matches = re.finditer(pattern, prompt, re.IGNORECASE)
        for match in matches:
            agent_name = match.group(1).lower()
            # Normalize agent names
            agent_name = agent_name.replace("_", "-")
            agents.add(agent_name)

    return list(agents)


def detect_slash_command_agent(prompt: str) -> str | None:
    """Detect if prompt starts with a slash command that invokes an agent.

    Args:
        prompt: The user prompt to analyze

    Returns:
        Agent type name if slash command detected, None otherwise
    """
    prompt_clean = prompt.strip()
    if not prompt_clean.startswith("/"):
        return None

    match = re.match(r"^/([a-z-]+)", prompt_clean)
    if not match:
        return None

    command = match.group(1)
    return SLASH_COMMAND_AGENTS.get(command)


def get_all_detected_agents(prompt: str) -> list[str]:
    """Get all agents detected from both references and slash commands.

    Args:
        prompt: The user prompt to analyze

    Returns:
        Combined list of agent types detected
    """
    agents = set(detect_agent_references(prompt))

    slash_agent = detect_slash_command_agent(prompt)
    if slash_agent:
        agents.add(slash_agent)

    return list(agents)
