"""LSPDetector brick for amplihack Claude Code plugin system.

Philosophy:
- Auto-detect project languages
- Generate LSP configurations
- Standard library only

Public API (the "studs"):
    LSPDetector: Main language detection and LSP config generation class
"""

from .detector import LSPDetector

__all__ = ["LSPDetector"]
