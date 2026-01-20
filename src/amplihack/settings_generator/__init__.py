"""SettingsGenerator brick for amplihack Claude Code plugin system.

Philosophy:
- Generate settings from plugin manifests
- Deep merge settings dictionaries
- Write formatted JSON

Public API (the "studs"):
    SettingsGenerator: Main settings generation and merging class
"""

from .generator import SettingsGenerator

__all__ = ["SettingsGenerator"]
