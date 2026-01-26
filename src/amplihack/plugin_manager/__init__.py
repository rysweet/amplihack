"""PluginManager brick for amplihack Claude Code plugin system.

Philosophy:
- Self-contained module with single responsibility
- Clear public API via __all__
- Zero-BS implementation - every function works

Public API (the "studs"):
    PluginManager: Main plugin management class
    InstallResult: Result of plugin installation
    ValidationResult: Result of manifest validation
"""

from .manager import InstallResult, PluginManager, ValidationResult

__all__ = ["PluginManager", "InstallResult", "ValidationResult"]
