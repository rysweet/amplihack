"""Permission-flag helpers for knowledge builder agent commands."""


def permission_flag_for_agent_cmd(agent_cmd: str) -> str:
    """Return the CLI permission flag for the configured agent binary."""
    normalized_cmd = agent_cmd.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if "copilot" in normalized_cmd or "codex" in normalized_cmd:
        return "--allow-all-tools"
    return "--dangerously-skip-permissions"
