"""PM Architect - File-based project management for Claude.

Phase 1 (Foundation):
- File-based state (.pm/ directory)
- Single workstream management
- ClaudeProcess delegation
- CLI commands via slash commands

Phase 2 (AI Assistance):
- Smart recommendations
- Rich delegation packages
- Dependency detection
- Complexity estimation

Phase 3 (Coordination):
- Multiple concurrent workstreams (max 5)
- Conflict detection
- Stall monitoring
- Cross-workstream coordination

Phase 4 (Autonomy):
- Autonomous work selection
- Decision transparency
- Learning from outcomes
- Adaptive recommendations

Public API:
    State Management:
        - PMConfig
        - BacklogItem
        - WorkstreamState
        - PMStateManager

    Workstream Management:
        - DelegationPackage
        - WorkstreamManager
        - WorkstreamMonitor
        - CoordinationAnalysis

    Intelligence (Phase 2):
        - RecommendationEngine
        - RichDelegationPackage

    Autonomy (Phase 4):
        - AutopilotEngine
        - AutopilotDecision
        - OutcomeTracker

    CLI Commands:
        - cmd_init
        - cmd_add
        - cmd_start
        - cmd_status
        - cmd_suggest (Phase 2)
        - cmd_prepare (Phase 2)
        - cmd_coordinate (Phase 3)
        - cmd_autopilot (Phase 4)
        - cmd_explain (Phase 4)

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

    # Get AI recommendations (Phase 2)
    from amplihack.pm import cmd_suggest
    cmd_suggest()

    # Run autopilot (Phase 4)
    from amplihack.pm import cmd_autopilot
    cmd_autopilot(mode="dry-run")
"""

from .state import PMConfig, BacklogItem, WorkstreamState, PMStateManager
from .workstream import DelegationPackage, WorkstreamManager, WorkstreamMonitor, CoordinationAnalysis
from .intelligence import RecommendationEngine, RichDelegationPackage
from .autopilot import AutopilotEngine, AutopilotDecision
from .learning import OutcomeTracker
from .cli import (
    cmd_init,
    cmd_add,
    cmd_start,
    cmd_status,
    cmd_suggest,
    cmd_prepare,
    cmd_coordinate,
    cmd_autopilot,
    cmd_explain,
)

__version__ = "4.0.0"  # Phase 4 complete
__all__ = [
    # State
    "PMConfig",
    "BacklogItem",
    "WorkstreamState",
    "PMStateManager",
    # Workstream
    "DelegationPackage",
    "WorkstreamManager",
    "WorkstreamMonitor",
    "CoordinationAnalysis",
    # Intelligence (Phase 2)
    "RecommendationEngine",
    "RichDelegationPackage",
    # Autonomy (Phase 4)
    "AutopilotEngine",
    "AutopilotDecision",
    "OutcomeTracker",
    # CLI
    "cmd_init",
    "cmd_add",
    "cmd_start",
    "cmd_status",
    "cmd_suggest",
    "cmd_prepare",
    "cmd_coordinate",
    "cmd_autopilot",
    "cmd_explain",
]
