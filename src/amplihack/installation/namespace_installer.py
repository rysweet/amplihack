"""Install Amplihack configuration files to namespaced directory.

This module handles copying configuration files to .claude/amplihack/ to avoid
conflicts with existing user configuration.
"""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class InstallResult:
    """Result of namespace installation.

    Attributes:
        success: True if installation completed successfully
        installed_path: Path where files were installed (.claude/amplihack/)
        files_installed: List of files that were installed
        errors: List of error messages if any failures occurred
    """

    success: bool
    installed_path: Path
    files_installed: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def install_to_namespace(
    source_dir: Path,
    target_dir: Path,
    force: bool = False,
) -> InstallResult:
    """Install Amplihack files to .claude/amplihack/ namespace.

    Args:
        source_dir: Directory containing Amplihack config files to install
        target_dir: User's .claude/ directory
        force: If True, overwrite existing amplihack installation

    Returns:
        InstallResult with details of what was installed

    Example:
        >>> result = install_to_namespace(Path("config"), Path(".claude"))
        >>> assert result.success
        >>> assert result.installed_path.exists()
    """
    installed_path = target_dir / "amplihack"
    errors = []
    files_installed = []

    # Validate source directory exists
    if not source_dir.exists():
        return InstallResult(
            success=False,
            installed_path=installed_path,
            errors=[f"Source directory not found: {source_dir}"],
        )

    # Check if amplihack namespace already exists
    try:
        path_exists = installed_path.exists()
    except (PermissionError, OSError):
        # If we can't check due to permissions, treat as not existing
        # The mkdir() below will properly fail with permission error if needed
        path_exists = False

    if path_exists and not force:
        return InstallResult(
            success=False,
            installed_path=installed_path,
            errors=[
                f"Amplihack already installed at {installed_path}. Use force=True to overwrite."
            ],
        )

    # Create parent directory if needed
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        return InstallResult(
            success=False,
            installed_path=installed_path,
            errors=[f"Cannot create target directory: {e}"],
        )

    # Remove existing installation if force is enabled
    try:
        force_path_exists = installed_path.exists()
    except (PermissionError, OSError):
        # If we can't check, assume it doesn't exist
        force_path_exists = False

    if force_path_exists and force:
        try:
            shutil.rmtree(installed_path)
        except (PermissionError, OSError) as e:
            return InstallResult(
                success=False,
                installed_path=installed_path,
                errors=[f"Cannot remove existing installation: {e}"],
            )

    # Copy files to namespace
    try:
        shutil.copytree(
            source_dir,
            installed_path,
            dirs_exist_ok=False,  # Should not exist after cleanup above
        )

        # Collect list of installed files
        for item in installed_path.rglob("*"):
            if item.is_file():
                files_installed.append(item.relative_to(target_dir))

    except (PermissionError, OSError) as e:
        return InstallResult(
            success=False,
            installed_path=installed_path,
            errors=[f"Failed to copy files: {e}"],
        )

    # Validate installation by checking for key files
    key_files = ["CLAUDE.md", "agents"]
    missing_files = []

    for key_file in key_files:
        if not (installed_path / key_file).exists():
            missing_files.append(key_file)

    if missing_files:
        errors.append(f"Installation incomplete: missing {', '.join(missing_files)}")
        return InstallResult(
            success=False,
            installed_path=installed_path,
            files_installed=files_installed,
            errors=errors,
        )

    return InstallResult(
        success=True,
        installed_path=installed_path,
        files_installed=files_installed,
    )
