"""Profile management data models.

Defines the data structures for amplihack profile system.
Profiles control which components are visible to Claude Code.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ComponentFilter:
    """Component inclusion/exclusion patterns.

    Uses glob patterns to specify which components are enabled.
    Includes are applied first, then excludes are removed.

    Attributes:
        includes: Glob patterns for components to include (default: all)
        excludes: Glob patterns for components to exclude (default: none)

    Example:
        >>> filter = ComponentFilter(
        ...     includes=["amplihack/*", "ddd/*"],
        ...     excludes=["amplihack/experimental/*"]
        ... )
    """
    includes: List[str] = field(default_factory=lambda: ["**/*"])
    excludes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "includes": self.includes,
            "excludes": self.excludes
        }


@dataclass
class Profile:
    """Profile definition for amplihack component visibility.

    A profile defines which commands, agents, and skills are visible
    to Claude Code when it starts.

    Attributes:
        name: Unique profile identifier
        description: Human-readable description
        version: Profile schema version (currently 1.0.0)
        commands: Command component filter
        agents: Agent component filter
        skills: Skill component filter
        metadata: Additional profile metadata

    Example:
        >>> profile = Profile(
        ...     name="coding",
        ...     description="Development-focused profile",
        ...     version="1.0.0",
        ...     commands=ComponentFilter(includes=["amplihack/ultrathink.md"])
        ... )
    """
    name: str
    description: str
    version: str

    commands: ComponentFilter = field(default_factory=ComponentFilter)
    agents: ComponentFilter = field(default_factory=ComponentFilter)
    skills: ComponentFilter = field(default_factory=ComponentFilter)

    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, data: dict) -> 'Profile':
        """Create Profile from parsed YAML data.

        Args:
            data: Parsed YAML dictionary

        Returns:
            Profile instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If data format is invalid

        Example:
            >>> data = {
            ...     "name": "coding",
            ...     "description": "Development profile",
            ...     "version": "1.0.0",
            ...     "includes": {
            ...         "commands": ["amplihack/*"]
            ...     }
            ... }
            >>> profile = Profile.from_yaml(data)
        """
        # Validate required fields
        if "name" not in data:
            raise KeyError("Profile missing required field: name")
        if "description" not in data:
            raise KeyError("Profile missing required field: description")

        # Parse includes/excludes
        includes = data.get('includes', {})
        excludes = data.get('excludes', {})

        return cls(
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0.0'),
            commands=ComponentFilter(
                includes=includes.get('commands', ['**/*']),
                excludes=excludes.get('commands', [])
            ),
            agents=ComponentFilter(
                includes=includes.get('agents', ['**/*']),
                excludes=excludes.get('agents', [])
            ),
            skills=ComponentFilter(
                includes=includes.get('skills', ['**/*']),
                excludes=excludes.get('skills', [])
            ),
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> dict:
        """Convert profile to dictionary representation.

        Returns:
            Dictionary suitable for YAML serialization
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "includes": {
                "commands": self.commands.includes,
                "agents": self.agents.includes,
                "skills": self.skills.includes
            },
            "excludes": {
                "commands": self.commands.excludes,
                "agents": self.agents.excludes,
                "skills": self.skills.excludes
            },
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Profile(name='{self.name}', version='{self.version}')"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Profile(name='{self.name}', description='{self.description}', "
            f"version='{self.version}')"
        )
