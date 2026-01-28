"""
Plugin Manager for Claude Code LSP plugins.

Philosophy:
- Wraps npx cclsp commands for plugin management
- User-guided installation (never auto-installs system binaries)
- Retry logic with exponential backoff
- Clear, actionable error messages

Public API:
    PluginManager: Manages Claude Code LSP plugin lifecycle
    install_plugin: Install a plugin via npx cclsp
    uninstall_plugin: Remove a plugin
    is_plugin_installed: Check if plugin is installed
    list_installed_plugins: Get all installed plugins
"""

import re
import subprocess
import time
from dataclasses import dataclass

__all__ = ["PluginManager", "PluginInstallResult"]


@dataclass
class PluginInstallResult:
    """Result of plugin installation operation."""

    success: bool
    plugin_name: str
    error: str | None = None
    output: str | None = None


class PluginManager:
    """Manages Claude Code LSP plugin installation and lifecycle."""

    def __init__(self, max_retries: int = 3, timeout: int = 120):
        """
        Initialize plugin manager.

        Args:
            max_retries: Maximum retry attempts for failed operations
            timeout: Timeout in seconds for subprocess calls
        """
        self.max_retries = max_retries
        self.timeout = timeout

    def _validate_plugin_name(self, plugin_name: str) -> None:
        """
        Validate plugin name contains only safe characters.

        Args:
            plugin_name: Name to validate

        Raises:
            ValueError: If plugin name contains unsafe characters
        """
        if not re.match(r"^[a-zA-Z0-9_-]+$", plugin_name):
            raise ValueError(f"Invalid plugin name: {plugin_name}")

    def check_npx_available(self) -> bool:
        """
        Check if npx is available on the system.

        Returns:
            True if npx is available, False otherwise
        """
        try:
            result = subprocess.run(["npx", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def is_plugin_installed(self, plugin_name: str) -> bool:
        """
        Check if a plugin is installed.

        Args:
            plugin_name: Name of the plugin (e.g., "python", "typescript")

        Returns:
            True if plugin is installed, False otherwise
        """
        self._validate_plugin_name(plugin_name)
        installed = self.list_installed_plugins()
        return plugin_name in installed

    def list_installed_plugins(self) -> list[str]:
        """
        List all installed Claude Code LSP plugins.

        Returns:
            List of installed plugin names
        """
        if not self.check_npx_available():
            return []

        try:
            result = subprocess.run(
                ["npx", "cclsp", "list"], capture_output=True, text=True, timeout=self.timeout
            )

            if result.returncode == 0:
                # Parse plugin list from stdout (one per line)
                plugins = [
                    line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                ]
                return plugins
            return []
        except (subprocess.TimeoutExpired, Exception):
            return []

    def install_plugin(self, plugin_name: str, dry_run: bool = False) -> bool:
        """
        Install a Claude Code LSP plugin via npx cclsp.

        Args:
            plugin_name: Name of plugin to install (e.g., "python")
            dry_run: If True, don't actually install, just check

        Returns:
            True if installation successful, False otherwise
        """
        self._validate_plugin_name(plugin_name)

        if not self.check_npx_available():
            return False

        if dry_run:
            # Just check if plugin is already installed (validation happens in is_plugin_installed)
            return not self.is_plugin_installed(plugin_name)

        # Check if already installed
        if self.is_plugin_installed(plugin_name):
            return True

        # Install with retry logic
        for attempt in range(self.max_retries):
            try:
                result = subprocess.run(
                    ["npx", "cclsp", "install", plugin_name],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )

                if result.returncode == 0:
                    return True

                # Retry on failure (except last attempt)
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

            except subprocess.TimeoutExpired:
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                    continue
                return False

        return False

    def install_multiple_plugins(
        self, plugin_names: list[str], dry_run: bool = False
    ) -> tuple[list[str], list[str]]:
        """
        Install multiple plugins.

        Args:
            plugin_names: List of plugin names to install
            dry_run: If True, don't actually install

        Returns:
            Tuple of (successful_plugins, failed_plugins)
        """
        successful = []
        failed = []

        for plugin in plugin_names:
            if self.install_plugin(plugin, dry_run=dry_run):
                successful.append(plugin)
            else:
                failed.append(plugin)

        return successful, failed

    def uninstall_plugin(self, plugin_name: str) -> bool:
        """
        Uninstall a Claude Code LSP plugin.

        Args:
            plugin_name: Name of plugin to uninstall

        Returns:
            True if uninstallation successful, False otherwise
        """
        self._validate_plugin_name(plugin_name)

        if not self.check_npx_available():
            return False

        # Check if plugin is installed (validation happens in is_plugin_installed)
        if not self.is_plugin_installed(plugin_name):
            return True  # Already uninstalled

        try:
            result = subprocess.run(
                ["npx", "cclsp", "uninstall", plugin_name],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False

    def get_plugin_info(self, plugin_name: str) -> dict | None:
        """
        Get information about a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Dict with plugin info, or None if not found
        """
        if not self.is_plugin_installed(plugin_name):
            return None

        return {"name": plugin_name, "installed": True, "source": "npx cclsp"}

    def update_plugin(self, plugin_name: str) -> bool:
        """
        Update a plugin to latest version.

        Args:
            plugin_name: Name of plugin to update

        Returns:
            True if update successful, False otherwise
        """
        # Uninstall then reinstall to get latest version
        if self.uninstall_plugin(plugin_name):
            return self.install_plugin(plugin_name)
        return False
