#!/usr/bin/env python3
"""
Turn-aware state management for power-steering with delta analysis.

This module is a backward-compatible re-export facade. The implementation
has been split into focused modules:

- power_steering_constants.py: Shared constants
- power_steering_models.py: Data models (FailureEvidence, BlockSnapshot, etc.)
- power_steering_delta_analyzer.py: DeltaAnalyzer class
- power_steering_state_io.py: File I/O, atomic writes, file locking
- power_steering_state_manager.py: TurnStateManager high-level operations

All public API names are re-exported here for full backward compatibility.

Philosophy:
- Ruthlessly Simple: Thin re-export layer, no logic
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    FailureEvidence: Detailed evidence of why a consideration failed
    BlockSnapshot: Full snapshot of a block event with evidence
    PowerSteeringTurnState: Dataclass holding turn state
    TurnStateManager: Manages loading/saving/incrementing turn state
    DeltaAnalyzer: Analyzes delta transcript since last block
    DeltaAnalysisResult: Result of delta analysis
    LOCKING_AVAILABLE: Whether file locking is available on this platform
"""

# Re-export models
try:
    from .power_steering_models import (
        BlockSnapshot,
        DeltaAnalysisResult,
        FailureEvidence,
        PowerSteeringTurnState,
    )
except ImportError:
    from power_steering_models import (
        BlockSnapshot,
        DeltaAnalysisResult,
        FailureEvidence,
        PowerSteeringTurnState,
    )

# Re-export delta analyzer
try:
    from .power_steering_delta_analyzer import DeltaAnalyzer
except ImportError:
    from power_steering_delta_analyzer import DeltaAnalyzer

# Re-export state manager
try:
    from .power_steering_state_manager import TurnStateManager
except ImportError:
    from power_steering_state_manager import TurnStateManager

# Re-export LOCKING_AVAILABLE from file_lock_utils
try:
    from . import file_lock_utils

    LOCKING_AVAILABLE = file_lock_utils.LOCKING_AVAILABLE
except ImportError:
    import file_lock_utils

    LOCKING_AVAILABLE = file_lock_utils.LOCKING_AVAILABLE

# Re-export get_shared_runtime_dir for backward compatibility with tests
# that patch "power_steering_state.get_shared_runtime_dir"
try:
    from .git_utils import get_shared_runtime_dir
except ImportError:
    try:
        from git_utils import get_shared_runtime_dir
    except ImportError:
        from pathlib import Path

        def get_shared_runtime_dir(project_root):
            """Fallback implementation when git_utils is unavailable."""
            return str(Path(project_root) / ".claude" / "runtime")


__all__ = [
    "FailureEvidence",
    "BlockSnapshot",
    "PowerSteeringTurnState",
    "TurnStateManager",
    "DeltaAnalyzer",
    "DeltaAnalysisResult",
    "LOCKING_AVAILABLE",
]
