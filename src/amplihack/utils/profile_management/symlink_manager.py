"""Platform-aware symlink and junction manager.

Handles creation of symlinks on Unix and junctions on Windows for
building profile-filtered component views.
"""

import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List
import os


class SymlinkManager:
    """Platform-aware symlink/junction operations.

    Creates symlink structures that enable zero-overhead profile filtering.
    Handles platform differences between Unix symlinks and Windows junctions.

    Attributes:
        platform: Current platform name (Linux, Darwin, Windows)

    Example:
        >>> manager = SymlinkManager()
        >>> components = {"commands": [Path("cmd1.md"), Path("cmd2.md")]}
        >>> manager.create_component_view(
        ...     all_dir=Path(".claude/_all"),
        ...     active_dir=Path(".claude/_active"),
        ...     components=components,
        ...     category="commands"
        ... )
    """

    def __init__(self):
        """Initialize with current platform detection."""
        self.platform = platform.system()

    def create_component_view(
        self,
        all_dir: Path,
        active_dir: Path,
        components: Dict[str, List[Path]],
        category: str
    ) -> None:
        """Create symlink structure for a component category.

        Builds a filtered view of components by creating symlinks from
        active directory to all directory based on profile selection.

        Args:
            all_dir: Source directory (.claude/_all/)
            active_dir: Target directory (.claude/_active/)
            components: Resolved components to link by category
            category: Component category (commands, agents, or skills)

        Raises:
            OSError: If symlink creation fails
            subprocess.CalledProcessError: If Windows junction creation fails

        Example:
            >>> manager = SymlinkManager()
            >>> components = {
            ...     "commands": [
            ...         Path(".claude/_all/commands/amplihack/ultrathink.md")
            ...     ]
            ... }
            >>> manager.create_component_view(
            ...     all_dir=Path(".claude/_all"),
            ...     active_dir=Path(".claude/_active"),
            ...     components=components,
            ...     category="commands"
            ... )
        """
        source_dir = all_dir / category
        target_dir = active_dir / category

        # Create target root directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Get components for this category
        category_components = components.get(category, [])

        # Create symlinks for each component
        for component_path in category_components:
            # Get relative path from source_dir
            try:
                rel_path = component_path.relative_to(source_dir)
            except ValueError:
                # Component is not under source_dir, skip it
                continue

            # Create parent directories in target
            link_path = target_dir / rel_path
            link_path.parent.mkdir(parents=True, exist_ok=True)

            # Create symlink
            self._create_link(component_path, link_path)

    def _create_link(self, source: Path, target: Path) -> None:
        """Create platform-appropriate link.

        Args:
            source: Source file or directory path
            target: Target link path

        Raises:
            OSError: If link creation fails
            subprocess.CalledProcessError: If Windows junction fails
        """
        # Remove existing link if present
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            elif target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)

        # Create link based on platform
        if self.platform == "Windows":
            self._create_windows_link(source, target)
        else:
            self._create_unix_link(source, target)

    def _create_windows_link(self, source: Path, target: Path) -> None:
        """Create Windows junction or symlink.

        Uses directory junctions for directories and symlinks for files.
        Falls back to file copy if symlink creation fails.

        Args:
            source: Source path
            target: Target link path

        Raises:
            subprocess.CalledProcessError: If junction creation fails
            OSError: If symlink and copy both fail
        """
        if source.is_dir():
            # Use directory junction for directories
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise OSError(
                    f"Failed to create Windows junction: {e.stderr}"
                )
        else:
            # For files, use symlink or copy as fallback
            try:
                target.symlink_to(source)
            except OSError:
                # If symlink fails (no admin rights), copy file
                shutil.copy2(source, target)

    def _create_unix_link(self, source: Path, target: Path) -> None:
        """Create Unix symlink.

        Args:
            source: Source path
            target: Target link path

        Raises:
            OSError: If symlink creation fails
        """
        try:
            target.symlink_to(source)
        except OSError as e:
            raise OSError(
                f"Failed to create symlink from {target} to {source}: {e}"
            )

    def remove_link_tree(self, root: Path) -> None:
        """Remove a directory tree of symlinks.

        Safely removes symlinks and empty directories without following
        symlink targets.

        Args:
            root: Root directory to remove

        Example:
            >>> manager = SymlinkManager()
            >>> manager.remove_link_tree(Path(".claude/_active"))
        """
        if not root.exists():
            return

        # Walk directory tree bottom-up
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_symlink():
                # Remove symlink without following it
                path.unlink()
            elif path.is_file():
                # Remove regular file
                path.unlink()
            elif path.is_dir() and not any(path.iterdir()):
                # Remove empty directory
                path.rmdir()

        # Remove root if empty
        if root.exists() and not any(root.iterdir()):
            root.rmdir()

    def verify_link(self, link_path: Path, expected_target: Path) -> bool:
        """Verify that a symlink points to expected target.

        Args:
            link_path: Path to symlink
            expected_target: Expected target path

        Returns:
            True if link exists and points to expected target

        Example:
            >>> manager = SymlinkManager()
            >>> is_valid = manager.verify_link(
            ...     Path(".claude/commands"),
            ...     Path(".claude/_active/commands")
            ... )
        """
        if not link_path.is_symlink():
            return False

        try:
            actual_target = link_path.resolve()
            return actual_target == expected_target.resolve()
        except (OSError, RuntimeError):
            return False

    def create_directory_symlink(self, source: Path, target: Path) -> None:
        """Create a symlink to a directory.

        Used for top-level category symlinks like .claude/commands -> .claude/_active/commands

        Args:
            source: Source directory path
            target: Target symlink path

        Raises:
            OSError: If symlink creation fails
            subprocess.CalledProcessError: If Windows junction fails

        Example:
            >>> manager = SymlinkManager()
            >>> manager.create_directory_symlink(
            ...     source=Path(".claude/_active/commands"),
            ...     target=Path(".claude/commands")
            ... )
        """
        # Remove existing target if present
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        # Create directory symlink
        if self.platform == "Windows":
            # Use junction for directory on Windows
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                raise OSError(
                    f"Failed to create Windows junction: {e.stderr}"
                )
        else:
            # Unix symlink
            try:
                target.symlink_to(source)
            except OSError as e:
                raise OSError(
                    f"Failed to create symlink from {target} to {source}: {e}"
                )
