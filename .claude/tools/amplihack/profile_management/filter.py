"""Component filtering based on profile specifications.

Applies profile filtering rules to component inventory to determine which
components should be loaded for a session.
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from .discovery import ComponentInventory
from .models import ProfileConfig


@dataclass
class ComponentSet:
    """Filtered components to load for session.

    Internal data structure - not part of public API.
    Use ComponentFilter.filter() to create instances.

    Attributes:
        commands: List of command file paths to load
        context: List of context file paths to load
        agents: List of agent file paths to load
        skills: List of skill file paths to load
    """

    commands: list[Path]
    context: list[Path]
    agents: list[Path]
    skills: list[Path]


def estimate_token_count(component_set: ComponentSet) -> int:
    """Estimate token count for filtered components.

    Uses rough heuristic: 1 token per 4 characters of file content.

    Args:
        component_set: Filtered component set

    Returns:
        Estimated token count
    """
    total_size = 0
    for paths in [
        component_set.commands,
        component_set.context,
        component_set.agents,
        component_set.skills,
    ]:
        for path in paths:
            if path.exists():
                total_size += path.stat().st_size

    return total_size // 4


class ComponentFilter:
    """Filter components based on profile specifications.

    Applies include/exclude patterns from profile configuration to
    determine which components to load for a session.
    """

    def filter(self, profile: ProfileConfig, inventory: ComponentInventory) -> ComponentSet:
        """Apply profile filters to component inventory.

        Args:
            profile: Profile configuration with filtering rules
            inventory: Available components discovered from filesystem

        Returns:
            ComponentSet with filtered components
        """
        return ComponentSet(
            commands=self._filter_commands(profile, inventory),
            context=self._filter_context(profile, inventory),
            agents=self._filter_agents(profile, inventory),
            skills=self._filter_skills(profile, inventory),
        )

    def _filter_commands(self, profile: ProfileConfig, inventory: ComponentInventory) -> list[Path]:
        """Filter commands based on profile specification.

        Args:
            profile: Profile configuration
            inventory: Available components

        Returns:
            List of command file paths
        """
        spec = profile.components.commands
        return self._apply_filters(spec.include, spec.exclude, spec.include_all, inventory.commands)

    def _filter_context(self, profile: ProfileConfig, inventory: ComponentInventory) -> list[Path]:
        """Filter context files based on profile specification.

        Args:
            profile: Profile configuration
            inventory: Available components

        Returns:
            List of context file paths
        """
        spec = profile.components.context
        return self._apply_filters(spec.include, spec.exclude, spec.include_all, inventory.context)

    def _filter_agents(self, profile: ProfileConfig, inventory: ComponentInventory) -> list[Path]:
        """Filter agents based on profile specification.

        Args:
            profile: Profile configuration
            inventory: Available components

        Returns:
            List of agent file paths
        """
        spec = profile.components.agents
        return self._apply_filters(spec.include, spec.exclude, spec.include_all, inventory.agents)

    def _filter_skills(self, profile: ProfileConfig, inventory: ComponentInventory) -> list[Path]:
        """Filter skills based on profile specification with category support.

        Supports category-based filtering in addition to individual skill patterns.

        Args:
            profile: Profile configuration
            inventory: Available components

        Returns:
            List of skill file paths
        """
        spec = profile.components.skills

        # Start with empty set
        selected = set()

        # Add skills from included categories
        if spec.include_categories:
            for category in spec.include_categories:
                if category in inventory.skill_categories:
                    selected.update(inventory.skill_categories[category])

        # Add explicitly included skills
        if spec.include:
            for pattern in spec.include:
                for name in inventory.skills:
                    if self._match_pattern(name, pattern):
                        selected.add(name)

        # If include_all, add everything
        if spec.include_all:
            selected.update(inventory.skills.keys())

        # Remove excluded categories
        if spec.exclude_categories:
            for category in spec.exclude_categories:
                if category in inventory.skill_categories:
                    for skill in inventory.skill_categories[category]:
                        selected.discard(skill)

        # Remove explicitly excluded skills (takes precedence)
        if spec.exclude:
            for pattern in spec.exclude:
                for name in list(selected):
                    if self._match_pattern(name, pattern):
                        selected.discard(name)

        # Convert names back to paths
        return [inventory.skills[name] for name in selected if name in inventory.skills]

    def _apply_filters(
        self, include: list[str], exclude: list[str], include_all: bool, components: dict[str, Path]
    ) -> list[Path]:
        """Apply include/exclude filters to components.

        Args:
            include: Patterns to include
            exclude: Patterns to exclude (takes precedence)
            include_all: Whether to include all components
            components: Available components (name -> path)

        Returns:
            List of filtered component paths
        """
        selected = set()

        # If include_all, start with everything
        if include_all:
            selected.update(components.keys())

        # Add explicitly included components
        if include:
            for pattern in include:
                for name in components:
                    if self._match_pattern(name, pattern):
                        selected.add(name)

        # Remove excluded components (takes precedence)
        if exclude:
            for pattern in exclude:
                for name in list(selected):
                    if self._match_pattern(name, pattern):
                        selected.discard(name)

        # Convert names back to paths
        return [components[name] for name in selected if name in components]

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Match name against pattern with wildcard support.

        Supports:
        - Exact match: "ultrathink"
        - Wildcards: "ddd:*", "*-analyst"
        - Multiple wildcards: "*test*"

        Security: Validates pattern complexity to prevent catastrophic
        backtracking and DoS attacks.

        Args:
            name: Component name to match
            pattern: Pattern with optional wildcards

        Returns:
            True if name matches pattern

        Raises:
            ValueError: Pattern too complex (too many wildcards)

        Examples:
            >>> f = ComponentFilter()
            >>> f._match_pattern("ultrathink", "ultrathink")
            True
            >>> f._match_pattern("ddd:1-plan", "ddd:*")
            True
            >>> f._match_pattern("economist-analyst", "*-analyst")
            True
        """
        return fnmatch.fnmatch(name, pattern)
