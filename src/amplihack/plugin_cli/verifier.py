"""Plugin verification module.

Philosophy:
- Read-only verification (no side effects)
- Three-layer checks: installed, discoverable, hooks loaded
- Clear diagnostics on failure

Public API (the "studs"):
    PluginVerifier: Main verification class
    VerificationResult: Result dataclass
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    """Result of plugin verification."""

    success: bool
    installed: bool
    discoverable: bool
    hooks_loaded: bool
    issues: list[str]


class PluginVerifier:
    """Verify plugin installation and discoverability."""

    def __init__(self, plugin_name: str):
        """Initialize verifier for specific plugin.

        Args:
            plugin_name: Name of plugin to verify
        """
        self.plugin_name = plugin_name
        self.plugin_root = Path.home() / ".amplihack" / ".claude" / "plugins" / plugin_name
        self.settings_path = Path.home() / ".claude" / "settings.json"

    def verify(self) -> VerificationResult:
        """Run all verification checks.

        Returns:
            VerificationResult with status and diagnostics
        """
        issues = []

        # Check 1: Plugin directory exists
        installed = self.check_installed()
        if not installed:
            issues.append(f"Plugin directory not found: {self.plugin_root}")

        # Check 2: Plugin in settings.json
        discoverable = self.check_discoverable()
        if not discoverable:
            issues.append(f"Plugin not found in {self.settings_path}")

        # Check 3: Hooks loaded
        hooks_loaded = self.check_hooks_loaded()
        if not hooks_loaded:
            issues.append("Hooks not registered or hooks.json missing")

        success = installed and discoverable and hooks_loaded

        return VerificationResult(
            success=success,
            installed=installed,
            discoverable=discoverable,
            hooks_loaded=hooks_loaded,
            issues=issues,
        )

    def check_installed(self) -> bool:
        """Check if plugin directory exists with manifest.

        Returns:
            True if plugin directory and manifest exist
        """
        manifest = self.plugin_root / ".claude-plugin" / "plugin.json"
        return self.plugin_root.exists() and manifest.exists()

    def check_discoverable(self) -> bool:
        """Check if plugin is in Claude Code settings.

        Returns:
            True if plugin is in enabledPlugins array
        """
        if not self.settings_path.exists():
            return False

        try:
            settings = json.loads(self.settings_path.read_text())
            enabled_plugins = settings.get("enabledPlugins", [])
            return self.plugin_name in enabled_plugins
        except (json.JSONDecodeError, KeyError):
            return False

    def check_hooks_loaded(self) -> bool:
        """Check if hooks.json exists and is valid.

        Returns:
            True if hooks.json exists with at least one hook
        """
        hooks_json = self.plugin_root / ".claude" / "tools" / "amplihack" / "hooks" / "hooks.json"
        if not hooks_json.exists():
            return False

        try:
            hooks = json.loads(hooks_json.read_text())
            # Verify at least one hook is defined
            return len(hooks) > 0
        except json.JSONDecodeError:
            return False


__all__ = ["PluginVerifier", "VerificationResult"]
