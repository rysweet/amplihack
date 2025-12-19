"""Profile-based file staging for amplihack install/launch.

This module provides functionality to create staging manifests that determine
which files should be copied during amplihack installation based on the active
profile configuration.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigManager
from .loader import ProfileLoader
from .parser import ProfileParser


@dataclass
class StagingManifest:
    """Result of applying profile to installation manifest.

    Attributes:
        dirs_to_stage: List of directories that should be copied
        file_filter: Optional per-file filter function (None = copy all files)
        profile_name: Name of the profile that was used
    """

    dirs_to_stage: list[str]
    file_filter: Callable[[Path], bool] | None
    profile_name: str


def create_staging_manifest(
    base_dirs: list[str], profile_uri: str | None = None
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
            return StagingManifest(dirs_to_stage=base_dirs, file_filter=None, profile_name="all")

        # Create file filter function using profile configuration directly
        # Don't use ComponentDiscovery - it requires .claude to exist already
        def should_copy_file(file_path: Path) -> bool:
            """Determine if a file should be copied based on profile filters.

            Uses profile.components include/exclude lists directly.

            Args:
                file_path: Path to file being considered for staging

            Returns:
                True if file should be copied, False otherwise
            """
            import fnmatch

            filename = file_path.name
            file_path_str = str(file_path).replace(os.sep, "/")

            # Helper to check include/exclude patterns
            def matches_pattern(filename: str, patterns: list[str]) -> bool:
                """Check if filename matches any pattern in list.

                Handles patterns like "architect" matching "architect.md"
                and "*-analyst" matching "economist-analyst.md"
                """
                if not patterns:
                    return False

                # Get stem (without extension) for matching
                stem = Path(filename).stem

                for pattern in patterns:
                    # Extract just the filename part if pattern has path
                    pattern_name = pattern.split("/")[-1]
                    # Try matching against both full filename and stem
                    if fnmatch.fnmatch(filename, pattern_name) or fnmatch.fnmatch(
                        stem, pattern_name
                    ):
                        return True
                return False

            # Agents
            if "/agents/" in file_path_str:
                agents_spec = profile.components.agents
                if agents_spec.include_all:
                    return True
                # Check excludes first
                if agents_spec.exclude and matches_pattern(filename, agents_spec.exclude):
                    return False
                # Then check includes
                if agents_spec.include:
                    return matches_pattern(filename, agents_spec.include)
                return False

            # Commands
            if "/commands/" in file_path_str:
                commands_spec = profile.components.commands
                if commands_spec.include_all:
                    return True
                if commands_spec.exclude and matches_pattern(filename, commands_spec.exclude):
                    return False
                if commands_spec.include:
                    return matches_pattern(filename, commands_spec.include)
                return False

            # Context
            if "/context/" in file_path_str:
                context_spec = profile.components.context
                if context_spec.include_all:
                    return True
                if context_spec.exclude and matches_pattern(filename, context_spec.exclude):
                    return False
                if context_spec.include:
                    return matches_pattern(filename, context_spec.include)
                return False

            # Skills
            if "/skills/" in file_path_str:
                skills_spec = profile.components.skills
                if skills_spec.include_all:
                    return True
                # Skills filtering is more complex (categories), for now include all
                return True

            # For other files (tools, workflow, etc.), include by default
            return True

        return StagingManifest(
            dirs_to_stage=base_dirs, file_filter=should_copy_file, profile_name=profile.name
        )

    except Exception as e:
        # Fail-open: Return full manifest on any errors
        print(f"Warning: Profile loading failed ({e}), using 'all' profile")
        return StagingManifest(
            dirs_to_stage=base_dirs, file_filter=None, profile_name="all (fallback)"
        )
