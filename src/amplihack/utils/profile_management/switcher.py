"""Profile switching with atomic operations and rollback.

Handles safe profile switching with staging, verification, and rollback
to ensure the system is never left in an inconsistent state.
"""

from pathlib import Path
import shutil
from typing import Optional, Dict, List
import fnmatch

from .models import Profile
from .loader import ProfileLoader
from .symlink_manager import SymlinkManager


class ProfileSwitcher:
    """Handle atomic profile switching operations.

    Implements safe profile switching with staging, backup, and rollback.
    Ensures the .claude directory is never left in an inconsistent state.

    Attributes:
        claude_dir: Path to .claude directory
        loader: Profile loader instance
        symlink_mgr: Symlink manager instance
        marker_file: File storing current profile name

    Example:
        >>> switcher = ProfileSwitcher()
        >>> result = switcher.switch_profile("coding")
        >>> print(result["success"])
        True
        >>> print(switcher.get_current_profile())
        coding
    """

    def __init__(self, claude_dir: Optional[Path] = None):
        """Initialize switcher with .claude directory.

        Args:
            claude_dir: Path to .claude directory. If None, uses .claude
        """
        if claude_dir is None:
            claude_dir = Path(".claude")

        self.claude_dir = Path(claude_dir)
        self.loader = ProfileLoader(claude_dir / "profiles")
        self.symlink_mgr = SymlinkManager()
        self.marker_file = claude_dir / ".active-profile"

    def switch_profile(self, profile_name: str) -> dict:
        """Switch to specified profile atomically.

        Performs atomic profile switch with staging and rollback on error.
        The .claude directory is never left in an inconsistent state.

        Args:
            profile_name: Name of profile to switch to

        Returns:
            Dictionary with switch results:
                - success: True if switch succeeded
                - profile: Profile name
                - components: Count of enabled components by category

        Raises:
            FileNotFoundError: If profile doesn't exist
            ValueError: If profile is invalid
            RuntimeError: If switch operation fails

        Example:
            >>> switcher = ProfileSwitcher()
            >>> result = switcher.switch_profile("coding")
            >>> print(f"Enabled {result['components']['commands']} commands")
        """
        # Load and validate profile
        profile = self.loader.load_profile(profile_name)

        # Validate profile
        validation_errors = self.loader.validate_profile(profile)
        if validation_errors:
            raise ValueError(
                f"Invalid profile '{profile_name}': {'; '.join(validation_errors)}"
            )

        # Resolve components
        components = self._resolve_components(profile)

        # Define directory paths
        staging_dir = self.claude_dir / "_staging"
        active_dir = self.claude_dir / "_active"
        backup_dir = self.claude_dir / "_active.backup"
        all_dir = self.claude_dir / "_all"

        try:
            # Clear staging directory
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            staging_dir.mkdir(parents=True)

            # Build symlink structure in staging
            for category in ["commands", "agents", "skills"]:
                self.symlink_mgr.create_component_view(
                    all_dir=all_dir,
                    active_dir=staging_dir,
                    components=components,
                    category=category
                )

            # Backup current active directory
            if active_dir.exists():
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                active_dir.rename(backup_dir)

            # Move staging to active (atomic operation)
            staging_dir.rename(active_dir)

            # Update top-level category symlinks
            self._update_category_symlinks()

            # Update marker file
            self.marker_file.write_text(profile_name)

            # Clean up backup
            if backup_dir.exists():
                shutil.rmtree(backup_dir)

            return {
                "success": True,
                "profile": profile_name,
                "components": {k: len(v) for k, v in components.items()}
            }

        except Exception as e:
            # Rollback on error
            if backup_dir.exists() and not active_dir.exists():
                backup_dir.rename(active_dir)

            # Clean up staging
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

            raise RuntimeError(f"Profile switch failed: {e}") from e

    def _update_category_symlinks(self) -> None:
        """Update top-level category symlinks.

        Creates/updates the symlinks:
            .claude/commands -> .claude/_active/commands
            .claude/agents -> .claude/_active/agents
            .claude/skills -> .claude/_active/skills
        """
        active_dir = self.claude_dir / "_active"

        for category in ["commands", "agents", "skills"]:
            source = active_dir / category
            target = self.claude_dir / category

            # Only create symlink if source exists
            if source.exists():
                self.symlink_mgr.create_directory_symlink(source, target)

    def get_current_profile(self) -> str:
        """Get current profile name.

        Returns:
            Current profile name, or "all" if no profile is active

        Example:
            >>> switcher = ProfileSwitcher()
            >>> current = switcher.get_current_profile()
            >>> print(f"Current profile: {current}")
        """
        if self.marker_file.exists():
            return self.marker_file.read_text().strip()
        return "all"  # Default profile

    def _resolve_components(self, profile: Profile) -> Dict[str, List[Path]]:
        """Resolve which components are enabled by the profile.

        Applies include and exclude glob patterns to determine which
        component files should be visible.

        Args:
            profile: Profile to resolve components for

        Returns:
            Dictionary mapping category to list of component file paths

        Example:
            >>> switcher = ProfileSwitcher()
            >>> profile = switcher.loader.load_profile("coding")
            >>> components = switcher._resolve_components(profile)
            >>> print(f"Commands: {len(components['commands'])}")
        """
        result = {}
        all_dir = self.claude_dir / "_all"

        for category in ["commands", "agents", "skills"]:
            filter_spec = getattr(profile, category)
            category_dir = all_dir / category

            # Skip if category directory doesn't exist
            if not category_dir.exists():
                result[category] = []
                continue

            # Get all component files
            all_components = []
            for item in category_dir.rglob("*"):
                if item.is_file():
                    all_components.append(item)

            # Apply includes (union of all include patterns)
            included = set()
            for pattern in filter_spec.includes:
                for comp in all_components:
                    rel_path = str(comp.relative_to(category_dir))
                    # Normalize path separators for cross-platform matching
                    rel_path_norm = rel_path.replace("\\", "/")
                    pattern_norm = pattern.replace("\\", "/")

                    if fnmatch.fnmatch(rel_path_norm, pattern_norm):
                        included.add(comp)

            # Apply excludes (remove from included set)
            excluded = set()
            for pattern in filter_spec.excludes:
                for comp in included:
                    rel_path = str(comp.relative_to(category_dir))
                    # Normalize path separators
                    rel_path_norm = rel_path.replace("\\", "/")
                    pattern_norm = pattern.replace("\\", "/")

                    if fnmatch.fnmatch(rel_path_norm, pattern_norm):
                        excluded.add(comp)

            # Final component list
            result[category] = sorted(list(included - excluded))

        return result

    def get_profile_info(self, profile_name: Optional[str] = None) -> dict:
        """Get information about a profile.

        Args:
            profile_name: Profile to get info for. If None, uses current profile.

        Returns:
            Dictionary with profile information:
                - name: Profile name
                - description: Profile description
                - version: Profile version
                - is_current: Whether this is the current profile
                - component_counts: Count of components by category

        Example:
            >>> switcher = ProfileSwitcher()
            >>> info = switcher.get_profile_info("coding")
            >>> print(info["description"])
        """
        if profile_name is None:
            profile_name = self.get_current_profile()

        profile = self.loader.load_profile(profile_name)
        components = self._resolve_components(profile)
        current = self.get_current_profile()

        return {
            "name": profile.name,
            "description": profile.description,
            "version": profile.version,
            "is_current": profile_name == current,
            "component_counts": {
                category: len(comps)
                for category, comps in components.items()
            },
            "metadata": profile.metadata
        }

    def verify_profile_integrity(self) -> bool:
        """Verify that the current profile setup is valid.

        Checks that:
        - Active directory exists
        - Marker file exists and is valid
        - Category symlinks are correct

        Returns:
            True if profile setup is valid, False otherwise

        Example:
            >>> switcher = ProfileSwitcher()
            >>> if not switcher.verify_profile_integrity():
            ...     print("Profile setup is corrupted!")
        """
        active_dir = self.claude_dir / "_active"

        # Check active directory exists
        if not active_dir.exists():
            return False

        # Check marker file exists
        if not self.marker_file.exists():
            return False

        # Check current profile is valid
        current = self.get_current_profile()
        if not self.loader.profile_exists(current):
            return False

        # Check category symlinks
        for category in ["commands", "agents", "skills"]:
            symlink_path = self.claude_dir / category
            expected_target = active_dir / category

            # If expected target exists, symlink should point to it
            if expected_target.exists():
                if not self.symlink_mgr.verify_link(symlink_path, expected_target):
                    return False

        return True
