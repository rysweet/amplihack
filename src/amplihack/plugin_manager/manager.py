"""Plugin manager implementation."""

import json
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class InstallResult:
    """Result of plugin installation."""
    success: bool
    plugin_name: str
    installed_path: Path
    message: str


@dataclass
class ValidationResult:
    """Result of manifest validation."""
    valid: bool
    errors: list
    warnings: list


class PluginManager:
    """Manages plugin installation, validation, and uninstallation.

    This manager handles:
    - Plugin installation from git URLs or local paths
    - Manifest validation (required fields, version format, name format)
    - Plugin uninstallation
    - Path resolution in manifests
    """

    # Semantic version pattern (major.minor.patch)
    VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')

    # Plugin name pattern (lowercase letters, numbers, hyphens)
    NAME_PATTERN = re.compile(r'^[a-z0-9-]+$')

    REQUIRED_FIELDS = ['name', 'version', 'entry_point']

    # Fields that should be resolved to absolute paths
    PATH_FIELDS = {'entry_point', 'files', 'cwd', 'script', 'path'}

    def __init__(self, plugin_root: Optional[Path] = None):
        """Initialize plugin manager.

        Args:
            plugin_root: Root directory for plugins (defaults to ~/.amplihack/.claude/plugins)
        """
        self.plugin_root = plugin_root or Path.home() / ".amplihack" / ".claude" / "plugins"
        self._lock = threading.Lock()

    def validate_manifest(self, manifest_path: Path) -> ValidationResult:
        """Validate a plugin manifest file.

        Args:
            manifest_path: Path to manifest.json file

        Returns:
            ValidationResult with validation status, errors, and warnings
        """
        errors = []
        warnings = []

        # Check if file exists
        if not manifest_path.exists():
            errors.append(f"Manifest file not found: {manifest_path}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Parse JSON
        try:
            manifest_text = manifest_path.read_text()
            manifest = json.loads(manifest_text)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in manifest: {e}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in manifest:
                errors.append(f"Missing required field: {field}")

        # Validate version format if present
        if 'version' in manifest:
            if not self.VERSION_PATTERN.match(str(manifest['version'])):
                errors.append(f"Invalid version format: {manifest['version']} (expected semver like 1.0.0)")

        # Validate name format if present
        if 'name' in manifest:
            if not self.NAME_PATTERN.match(str(manifest['name'])):
                errors.append(f"Invalid name format: {manifest['name']} (must be lowercase letters, numbers, hyphens only)")

        # Check for optional but recommended fields
        recommended_fields = ['description', 'author']
        for field in recommended_fields:
            if field not in manifest:
                warnings.append(f"Missing recommended field: {field}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def install(self, source: str, force: bool = False) -> InstallResult:
        """Install a plugin from git URL or local path.

        Args:
            source: Git URL or local directory path
            force: If True, overwrite existing plugin

        Returns:
            InstallResult with installation status and details
        """
        with self._lock:
            # Validate source
            if not source:
                return InstallResult(
                    success=False,
                    plugin_name="",
                    installed_path=Path(),
                    message="Empty source provided"
                )

            # Determine if source is git URL or local path
            is_git_url = source.startswith(("http://", "https://", "git@"))

            if is_git_url:
                # Extract plugin name from URL
                plugin_name = source.rstrip('/').split('/')[-1]
                if plugin_name.endswith('.git'):
                    plugin_name = plugin_name[:-4]

                # Create temp directory for cloning
                import tempfile
                temp_dir = Path(tempfile.mkdtemp())

                # Clone repository
                result = subprocess.run(
                    ['git', 'clone', source, str(temp_dir / plugin_name)],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    return InstallResult(
                        success=False,
                        plugin_name=plugin_name,
                        installed_path=Path(),
                        message=f"Git clone failed: {result.stderr}"
                    )

                source_path = temp_dir / plugin_name
            else:
                # Local path
                source_path = Path(source)
                if not source_path.exists():
                    return InstallResult(
                        success=False,
                        plugin_name="",
                        installed_path=Path(),
                        message=f"Source path does not exist: {source}"
                    )

                if not source_path.is_dir():
                    return InstallResult(
                        success=False,
                        plugin_name="",
                        installed_path=Path(),
                        message=f"Source must be a directory: {source}"
                    )

                plugin_name = source_path.name

            # Validate manifest
            manifest_path = source_path / "manifest.json"
            validation = self.validate_manifest(manifest_path)

            if not validation.valid:
                return InstallResult(
                    success=False,
                    plugin_name=plugin_name,
                    installed_path=Path(),
                    message=f"Invalid manifest: {', '.join(validation.errors)}"
                )

            # Check if plugin already exists
            target_path = self.plugin_root / plugin_name
            if target_path.exists() and not force:
                return InstallResult(
                    success=False,
                    plugin_name=plugin_name,
                    installed_path=target_path,
                    message=f"Plugin already installed: {plugin_name} (use force=True to overwrite)"
                )

            # Remove existing if force
            if target_path.exists() and force:
                shutil.rmtree(target_path)

            # Create plugin directory
            self.plugin_root.mkdir(parents=True, exist_ok=True)

            # Copy plugin files
            shutil.copytree(source_path, target_path)

            # Register plugin in Claude Code settings
            if not self._register_plugin(plugin_name, target_path):
                return InstallResult(
                    success=False,
                    plugin_name=plugin_name,
                    installed_path=target_path,
                    message=f"Plugin copied but registration failed: {plugin_name}"
                )

            return InstallResult(
                success=True,
                plugin_name=plugin_name,
                installed_path=target_path,
                message=f"Plugin installed successfully: {plugin_name}"
            )

    def uninstall(self, plugin_name: str) -> bool:
        """Uninstall a plugin.

        Args:
            plugin_name: Name of plugin to uninstall

        Returns:
            True if successful, False otherwise
        """
        plugin_path = self.plugin_root / plugin_name

        if not plugin_path.exists():
            return False

        try:
            shutil.rmtree(plugin_path)
            return True
        except (PermissionError, OSError):
            return False

    def resolve_paths(self, manifest: dict, plugin_path: Optional[Path] = None) -> dict:
        """Resolve relative paths in manifest to absolute paths.

        Args:
            manifest: Plugin manifest dictionary
            plugin_path: Base path for resolving relative paths (defaults to plugin_root)

        Returns:
            Manifest with resolved paths
        """
        base_path = plugin_path or self.plugin_root
        resolved = {}

        for key, value in manifest.items():
            if key in self.PATH_FIELDS and isinstance(value, str):
                # Resolve path
                path = Path(value)
                if not path.is_absolute():
                    resolved[key] = str(base_path / path)
                else:
                    resolved[key] = value
            elif key in self.PATH_FIELDS and isinstance(value, list):
                # Resolve list of paths
                resolved[key] = [
                    str(base_path / Path(p)) if not Path(p).is_absolute() else p
                    for p in value
                ]
            elif isinstance(value, dict):
                # Recursively resolve nested dictionaries
                resolved[key] = self._resolve_nested_paths(value, base_path)
            else:
                resolved[key] = value

        return resolved

    def _resolve_nested_paths(self, data: dict, base_path: Path) -> dict:
        """Recursively resolve paths in nested dictionaries.

        Args:
            data: Nested dictionary
            base_path: Base path for resolution

        Returns:
            Dictionary with resolved paths
        """
        resolved = {}

        for key, value in data.items():
            if key in self.PATH_FIELDS and isinstance(value, str):
                path = Path(value)
                if not path.is_absolute():
                    resolved[key] = str(base_path / path)
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_nested_paths(value, base_path)
            else:
                resolved[key] = value

        return resolved

    def _register_plugin(self, plugin_name: str, plugin_path: Path) -> bool:
        """Register plugin in Claude Code settings.

        Adds plugin to enabledPlugins array in ~/.claude/settings.json
        so it appears in /plugin command.

        Args:
            plugin_name: Name of plugin to register
            plugin_path: Path to installed plugin

        Returns:
            True if successful, False otherwise
        """
        settings_path = Path.home() / ".claude" / "settings.json"

        try:
            # Create .claude directory if it doesn't exist
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing settings or create new
            if settings_path.exists():
                settings = json.loads(settings_path.read_text())
            else:
                settings = {}

            # Add to enabledPlugins array
            if 'enabledPlugins' not in settings:
                settings['enabledPlugins'] = []

            if plugin_name not in settings['enabledPlugins']:
                settings['enabledPlugins'].append(plugin_name)

            # Write updated settings
            settings_path.write_text(json.dumps(settings, indent=2))
            return True

        except (OSError, json.JSONDecodeError, PermissionError):
            return False
