"""CLI command handlers for plugin management.

Philosophy:
- Thin wrappers around PluginManager
- Clear user-facing messages
- Standard exit codes (0=success, 1=failure)

Public API (the "studs"):
    plugin_install_command: Install plugin from source
    plugin_uninstall_command: Remove installed plugin
    plugin_verify_command: Verify plugin installation
"""

import argparse
import platform

from ..plugin_manager import PluginManager
from .verifier import PluginVerifier

# Platform-specific emoji support
IS_WINDOWS = platform.system() == "Windows"
SUCCESS = "[OK]" if IS_WINDOWS else "✅"
FAILURE = "[ERROR]" if IS_WINDOWS else "❌"


def plugin_install_command(args: argparse.Namespace) -> int:
    """Install plugin from source.

    Args:
        args: Parsed arguments with 'source' and 'force' attributes

    Returns:
        0 on success, 1 on failure
    """
    manager = PluginManager()
    result = manager.install(args.source, force=getattr(args, "force", False))

    if result.success:
        print(f"{SUCCESS} Plugin installed: {result.plugin_name}")
        print(f"   Location: {result.installed_path}")
        print(f"   {result.message}")
        return 0
    print(f"{FAILURE} Installation failed: {result.message}")
    return 1


def plugin_uninstall_command(args: argparse.Namespace) -> int:
    """Uninstall plugin.

    Args:
        args: Parsed arguments with 'plugin_name' attribute

    Returns:
        0 on success, 1 on failure
    """
    manager = PluginManager()
    success = manager.uninstall(args.plugin_name)

    if success:
        print(f"{SUCCESS} Plugin removed: {args.plugin_name}")
        return 0
    print(f"{FAILURE} Failed to remove plugin: {args.plugin_name}")
    print("   Plugin may not be installed or removal failed")
    return 1


def plugin_verify_command(args: argparse.Namespace) -> int:
    """Verify plugin installation and discoverability.

    Args:
        args: Parsed arguments with 'plugin_name' attribute

    Returns:
        0 if fully verified, 1 if any check fails
    """
    verifier = PluginVerifier(args.plugin_name)
    result = verifier.verify()

    print(f"Plugin: {args.plugin_name}")
    print(f"  Installed: {SUCCESS if result.installed else FAILURE}")
    print(f"  Discoverable: {SUCCESS if result.discoverable else FAILURE}")
    print(f"  Hooks loaded: {SUCCESS if result.hooks_loaded else FAILURE}")

    if not result.success:
        print("\nDiagnostics:")
        for issue in result.issues:
            print(f"  - {issue}")

    return 0 if result.success else 1


__all__ = [
    "plugin_install_command",
    "plugin_uninstall_command",
    "plugin_verify_command",
]
