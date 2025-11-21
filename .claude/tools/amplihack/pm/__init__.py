"""PM Architect - File-based project management for Claude.

Phase 1 (Foundation):
- Single workstream management
- File-based state (.pm/ directory)
- ClaudeProcess delegation
- CLI commands via slash commands

Public API:
    State Management:
        - PMConfig
        - BacklogItem
        - WorkstreamState
        - PMStateManager

    Workstream Management:
        - DelegationPackage
        - WorkstreamManager

    CLI Commands:
        - cmd_init
        - cmd_add
        - cmd_start
        - cmd_status

Usage:
    # Initialize PM
    from amplihack.pm import cmd_init
    cmd_init()

    # Add backlog item
    from amplihack.pm import cmd_add
    cmd_add("Feature X", priority="HIGH")

    # Start workstream
    from amplihack.pm import cmd_start
    cmd_start("BL-001")
"""

from .state import PMConfig, BacklogItem, WorkstreamState, PMStateManager
from .workstream import DelegationPackage, WorkstreamManager
from .cli import cmd_init, cmd_add, cmd_start, cmd_status

__version__ = "1.0.0"
__all__ = [
    # State
    "PMConfig",
    "BacklogItem",
    "WorkstreamState",
    "PMStateManager",
    # Workstream
    "DelegationPackage",
    "WorkstreamManager",
    # CLI
    "cmd_init",
    "cmd_add",
    "cmd_start",
    "cmd_status",
]
