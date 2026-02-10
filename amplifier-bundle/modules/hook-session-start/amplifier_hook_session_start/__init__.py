"""Session Start Hook - Amplifier wrapper for Claude Code session initialization.

Handles comprehensive session startup including:
- Version mismatch detection and auto-update
- Global hook migration (prevents duplicate execution)
- Original request capture for context preservation
- Neo4j memory system startup (if enabled)
- User preferences injection
- Project context injection
- Agent content loading (workaround for microsoft/amplifier#174)
"""

import logging
import sys
from pathlib import Path
from typing import Any

import yaml
from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_session_start/ -> hook-session-start/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify the import works
    try:
        import session_start  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"SessionStartHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"SessionStartHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


# Inline shared utilities (fallback if delegation fails)
def load_user_preferences() -> str | None:
    """Load user preferences from standard locations."""
    prefs_paths = [
        Path.cwd() / "USER_PREFERENCES.md",
        Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md",
        Path.home() / ".claude" / "USER_PREFERENCES.md",
    ]
    for path in prefs_paths:
        if path.exists():
            try:
                return path.read_text()
            except Exception as e:
                logger.debug(f"Failed to read preferences from {path}: {e}")
    return None


def load_project_context() -> str | None:
    """Load project-specific context files."""
    context_paths = [
        Path.cwd() / ".claude" / "context" / "PHILOSOPHY.md",
        Path.cwd() / ".claude" / "context" / "PATTERNS.md",
        Path.cwd() / "CLAUDE.md",
    ]
    context_parts = []
    for path in context_paths:
        if path.exists():
            try:
                content = path.read_text()
                context_parts.append(f"## {path.name}\n{content}")
            except Exception as e:
                logger.debug(f"Failed to read context from {path}: {e}")
    return "\n\n".join(context_parts) if context_parts else None


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content potentially with YAML frontmatter.

    Returns:
        Tuple of (frontmatter_dict, body_content).
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.split("\n")
    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    frontmatter_str = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :])

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError:
        return {}, content

    return frontmatter, body


def load_agent_content(agent_path: Path) -> dict[str, Any] | None:
    """Load agent content from a .md file.

    WORKAROUND: This function exists because of microsoft/amplifier#174 where
    agent instructions from .md files are never loaded in the spawn pipeline.
    Remove when microsoft/amplifier-foundation#30 is merged.

    Args:
        agent_path: Path to the agent .md file.

    Returns:
        Agent config dict with name, description, and system.instruction,
        or None if file cannot be read.
    """
    try:
        content = agent_path.read_text()
        frontmatter, body = parse_frontmatter(content)

        agent_config: dict[str, Any] = {}

        # Extract from meta section OR top-level frontmatter
        # Supports both structures:
        #   meta: { name: X, description: Y }  (Amplifier convention)
        #   name: X, description: Y             (amplihack convention)
        meta = frontmatter.get("meta", {})
        agent_config["name"] = meta.get("name") or frontmatter.get("name", agent_path.stem)
        agent_config["description"] = (
            meta.get("description") or frontmatter.get("description") or ""
        )

        # Copy other frontmatter fields (exclude already-extracted fields)
        for key, value in frontmatter.items():
            if key not in {"meta", "name", "description"} and key not in agent_config:
                agent_config[key] = value

        # Set body as system instruction
        if body.strip():
            agent_config.setdefault("system", {})["instruction"] = body.strip()

        return agent_config

    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to load agent from {agent_path.name}: {type(e).__name__}")
        return None


def populate_agent_configs(coordinator: Any) -> dict[str, Any]:
    """Populate agent configs from .md files.

    WORKAROUND: This function exists because of microsoft/amplifier#174 where
    agent instructions from .md files are never loaded in the spawn pipeline.
    Remove when microsoft/amplifier-foundation#30 is merged.

    Args:
        coordinator: The session coordinator.

    Returns:
        Metadata about what was populated.
    """
    metadata: dict[str, Any] = {"agents_populated": []}

    # Find the agents directory relative to this module
    # Path: __init__.py -> amplifier_hook_session_start/ -> hook-session-start/ -> modules/ -> amplifier-bundle/
    bundle_root = Path(__file__).parent.parent.parent.parent
    agents_dir = bundle_root / "agents"

    if not agents_dir.exists():
        logger.debug(f"No agents directory found at {agents_dir}")
        return metadata

    # Get current agent configs
    agents = coordinator.config.get("agents", {})

    # Load each agent .md file (recursively including subdirectories)
    for agent_file in agents_dir.rglob("*.md"):
        # Build agent name from path relative to agents_dir
        # e.g., core/architect.md -> architect, specialized/security.md -> security
        agent_name = agent_file.stem

        # Build the full agent key (with bundle namespace)
        # Try both namespaced and simple keys
        possible_keys = [f"amplihack:{agent_name}", agent_name]

        for key in possible_keys:
            if key in agents:
                current = agents[key]
                # Skip if already has instruction content
                if current.get("system", {}).get("instruction"):
                    continue

                # Load content from file
                loaded = load_agent_content(agent_file)
                if loaded:
                    # Merge loaded content with existing config
                    agents[key] = {**current, **loaded}
                    metadata["agents_populated"].append(key)
                    logger.info(f"Populated agent config for: {key}")
                break
        else:
            # Agent not in config - add it with both keys for discoverability
            loaded = load_agent_content(agent_file)
            if loaded:
                # Add with namespaced key
                full_key = f"amplihack:{agent_name}"
                agents[full_key] = loaded
                metadata["agents_populated"].append(full_key)
                logger.info(f"Added new agent config: {full_key}")

    # Update coordinator config
    coordinator.config["agents"] = agents

    return metadata


class SessionStartHook(Hook):
    """Comprehensive session initialization hook."""

    def __init__(self, config: dict[str, Any] | None = None, coordinator: Any = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._session_start_hook = None
        self._delegation_attempted = False
        self._coordinator = coordinator  # Store for agent population workaround

    def _get_session_start_hook(self):
        """Lazy load session start hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from session_start import SessionStartHook as ClaudeSessionStartHook

                    self._session_start_hook = ClaudeSessionStartHook()
                    logger.info("SessionStartHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"SessionStartHook: Claude Code delegation failed: {e}")
                    self._session_start_hook = None
            else:
                logger.info(f"SessionStartHook: Using fallback ({_IMPORT_ERROR})")
        return self._session_start_hook

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:start events for comprehensive initialization."""
        if not self.enabled:
            return None

        if event != "session:start":
            return None

        try:
            injections = []
            metadata = {}

            # WORKAROUND: Populate agent configs from .md files
            # This exists because of microsoft/amplifier#174 where agent instructions
            # from .md files are never loaded in the spawn pipeline.
            # Remove when microsoft/amplifier-foundation#30 is merged.
            if self._coordinator:
                agent_metadata = populate_agent_configs(self._coordinator)
                if agent_metadata.get("agents_populated"):
                    metadata["agents_populated"] = agent_metadata["agents_populated"]
                    logger.info(
                        f"SessionStartHook: Populated {len(agent_metadata['agents_populated'])} agent configs"
                    )

            # Try to use Claude Code session start hook for full functionality
            claude_hook = self._get_session_start_hook()
            if claude_hook:
                try:
                    # Process through Claude Code hook
                    result = claude_hook.process(data)
                    if result and result.get("hookSpecificOutput"):
                        additional_context = result["hookSpecificOutput"].get(
                            "additionalContext", ""
                        )
                        if additional_context:
                            injections.append(additional_context)
                            metadata["claude_hook_processed"] = True
                            metadata["delegation"] = "success"
                            logger.info("SessionStartHook: Delegation successful")
                except Exception as e:
                    logger.warning(f"Claude Code session start hook execution failed: {e}")
                    metadata["delegation"] = "execution_failed"

            # Fallback: inject essentials if Claude Code hook unavailable or failed
            if not injections:
                metadata["delegation"] = metadata.get("delegation", "fallback")
                logger.info("SessionStartHook: Using fallback implementation")

                # Load user preferences
                prefs = load_user_preferences()
                if prefs:
                    injections.append(f"## USER PREFERENCES (MANDATORY)\n\n{prefs}")
                    metadata["preferences_injected"] = True

                # Load project context
                project_context = load_project_context()
                if project_context:
                    injections.append(f"## PROJECT CONTEXT\n\n{project_context}")
                    metadata["project_context_injected"] = True

            if injections:
                return HookResult(
                    modified_data={**data, "injected_context": "\n\n".join(injections)},
                    metadata=metadata,
                )

        except Exception as e:
            # Fail open - log but don't block session start
            logger.warning(f"Session start hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the session start hook."""
    hook = SessionStartHook(config, coordinator=coordinator)
    coordinator.mount("hooks", hook)


__all__ = ["SessionStartHook", "mount"]
