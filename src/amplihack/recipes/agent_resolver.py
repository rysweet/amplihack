"""Agent resolver for mapping agent references to system prompt content.

Resolves references like ``amplihack:builder`` to the markdown content of the
corresponding agent definition file.
"""

from __future__ import annotations

import re
from pathlib import Path

# Agent namespace and name must be simple identifiers (alphanumeric, hyphens,
# underscores). This prevents path traversal via ".." or "/" in references.
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class AgentNotFoundError(Exception):
    """Raised when an agent reference cannot be resolved to a file."""

    def __init__(self, agent_ref: str, searched: list[str] | None = None) -> None:
        paths_msg = ""
        if searched:
            paths_msg = f" Searched: {', '.join(searched)}"
        super().__init__(f"Agent '{agent_ref}' not found.{paths_msg}")


_DEFAULT_SEARCH_PATHS = [
    Path.home() / ".amplihack" / ".claude" / "agents",
    Path(".claude") / "agents",
    Path("amplifier-bundle") / "agents",
    Path("src") / "amplihack" / "amplifier-bundle" / "agents",
    Path("src") / "amplihack" / ".claude" / "agents",
]


class AgentResolver:
    """Resolves ``namespace:name`` agent references to their markdown content.

    Searches a configurable list of directories for agent definition files.
    """

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        self._search_paths = search_paths or _DEFAULT_SEARCH_PATHS

    def resolve(self, agent_ref: str) -> str:
        """Resolve an agent reference to its system prompt content.

        Args:
            agent_ref: Reference in ``namespace:name`` format (e.g. ``amplihack:builder``).

        Returns:
            The full text content of the agent's markdown definition file.

        Raises:
            ValueError: If ``agent_ref`` does not contain a colon.
            AgentNotFoundError: If no matching file is found on any search path.
        """
        if ":" not in agent_ref:
            raise ValueError(
                f"Agent reference must be in 'namespace:name' format, got: '{agent_ref}'"
            )

        namespace, name = agent_ref.split(":", 1)

        # Validate that namespace and name are simple identifiers to prevent
        # path traversal attacks (e.g. "../../etc:passwd" or "ns:../../secret").
        if not _SAFE_NAME_RE.match(namespace):
            raise ValueError(
                f"Invalid agent namespace '{namespace}': must contain only "
                "alphanumeric characters, hyphens, and underscores"
            )
        if not _SAFE_NAME_RE.match(name):
            raise ValueError(
                f"Invalid agent name '{name}': must contain only "
                "alphanumeric characters, hyphens, and underscores"
            )

        # Candidate relative paths to try within each search directory
        candidates = [
            Path(namespace) / "core" / f"{name}.md",
            Path(namespace) / "specialized" / f"{name}.md",
            Path("core") / f"{name}.md",
            Path("specialized") / f"{name}.md",
            Path(f"{name}.md"),
        ]

        searched: list[str] = []
        for base in self._search_paths:
            resolved_base = base.resolve()
            for candidate in candidates:
                full = base / candidate
                searched.append(str(full))
                if full.is_file():
                    # Defense in depth: verify the resolved path is actually
                    # inside the search directory to catch any traversal that
                    # might bypass the regex (e.g. via symlinks).
                    resolved_full = full.resolve()
                    if not str(resolved_full).startswith(str(resolved_base)):
                        continue
                    return full.read_text(encoding="utf-8")

        raise AgentNotFoundError(agent_ref, searched)
