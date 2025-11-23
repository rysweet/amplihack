"""Profile-based file staging for amplihack install/launch.

This module provides functionality to create staging manifests that determine
which files should be copied during amplihack installation based on the active
profile configuration.
"""

from pathlib import Path
from typing import Callable, List, Optional
from dataclasses import dataclass

from .config import ConfigManager
from .loader import ProfileLoader
from .parser import ProfileParser
from .filter import ComponentFilter
from .discovery import ComponentDiscovery


@dataclass
class StagingManifest:
    """Result of applying profile to installation manifest.

    Attributes:
        dirs_to_stage: List of directories that should be copied
        file_filter: Optional per-file filter function (None = copy all files)
        profile_name: Name of the profile that was used
    """
    dirs_to_stage: List[str]
    file_filter: Optional[Callable[[Path], bool]]
    profile_name: str


def create_staging_manifest(
    base_dirs: List[str],
    profile_uri: Optional[str] = None
) -> StagingManifest:
    """
    Create filtered staging manifest based on active profile.

    This function determines which directories and files should be staged
    during amplihack installation by applying the active profile's filtering
    rules. It follows a fail-open design: if any error occurs during profile
    loading or parsing, it falls back to staging all files.

    Args:
        base_dirs: List of essential directories from ESSENTIAL_DIRS
        profile_uri: Optional profile URI override (None = use configured profile)

    Returns:
        StagingManifest with filtered directories and optional file filter

    Examples:
        >>> # Use configured profile
        >>> manifest = create_staging_manifest([".claude/context", ".claude/commands"])
        >>> print(manifest.profile_name)
        coding

        >>> # Override with specific profile
        >>> manifest = create_staging_manifest(
        ...     [".claude/context"],
        ...     profile_uri="amplihack://profiles/minimal"
        ... )
    """
    try:
        # Get profile URI (from argument, config, or default)
        if profile_uri is None:
            config = ConfigManager()
            profile_uri = config.get_current_profile()

        # Load and parse profile
        loader = ProfileLoader()
        parser = ProfileParser()

        yaml_content = loader.load(profile_uri)
        profile = parser.parse(yaml_content)

        # If "all" profile, return full manifest (no filtering)
        if profile.name == "all":
            return StagingManifest(
                dirs_to_stage=base_dirs,
                file_filter=None,
                profile_name="all"
            )

        # Discover available components
        discovery = ComponentDiscovery()
        inventory = discovery.discover_all()

        # Apply profile filters
        component_filter = ComponentFilter()
        filtered = component_filter.filter(profile, inventory)

        # Create file filter function based on filtered components
        def should_copy_file(file_path: Path) -> bool:
            """Determine if a file should be copied based on profile filters.

            Trusts that file_path is valid (internal function, caller responsibility).

            Args:
                file_path: Path to file being considered for staging

            Returns:
                True if file should be copied, False otherwise
            """
            # Get the relative path within .claude directory
            if ".claude" in file_path.parts:
                claude_idx = file_path.parts.index(".claude")
                rel_path = Path(*file_path.parts[claude_idx:])
            else:
                rel_path = file_path

            # File matching: Compare relative paths (rel_path vs filtered paths)
            # filtered.agents etc. contain paths like ".claude/agents/amplihack/core/architect.md"
            # rel_path is like ".claude/agents/amplihack/core/architect.md" (after normalization above)

            rel_path_str = str(rel_path)

            # Commands
            if "commands" in rel_path.parts:
                return any(rel_path_str.endswith(Path(cmd_path).name) or
                         str(cmd_path).endswith(rel_path_str) or
                         rel_path_str in str(cmd_path) or
                         str(cmd_path) in rel_path_str
                         for cmd_path in filtered.commands)

            # Context
            if "context" in rel_path.parts:
                return any(rel_path_str.endswith(Path(ctx_path).name) or
                         str(ctx_path).endswith(rel_path_str) or
                         rel_path_str in str(ctx_path) or
                         str(ctx_path) in rel_path_str
                         for ctx_path in filtered.context)

            # Agents
            if "agents" in rel_path.parts:
                return any(rel_path_str.endswith(Path(agent_path).name) or
                         str(agent_path).endswith(rel_path_str) or
                         rel_path_str in str(agent_path) or
                         str(agent_path) in rel_path_str
                         for agent_path in filtered.agents)

            # Skills
            if "skills" in rel_path.parts:
                return any(rel_path_str.endswith(Path(skill_path).name) or
                         str(skill_path).endswith(rel_path_str) or
                         rel_path_str in str(skill_path) or
                         str(skill_path) in rel_path_str
                         for skill_path in filtered.skills)

            # For other files (tools, workflow, etc.), include by default
            return True

        return StagingManifest(
            dirs_to_stage=base_dirs,
            file_filter=should_copy_file,
            profile_name=profile.name
        )

    except Exception as e:
        # Fail-open: Return full manifest on any errors
        print(f"Warning: Profile loading failed ({e}), using 'all' profile")
        return StagingManifest(
            dirs_to_stage=base_dirs,
            file_filter=None,
            profile_name="all (fallback)"
        )
