"""PathResolver brick for amplihack Claude Code plugin system.

Philosophy:
- Resolve relative to absolute paths
- Handle plugin root detection
- Standard library only

Public API (the "studs"):
    PathResolver: Main path resolution class
"""

from .resolver import PathResolver

__all__ = ["PathResolver"]
