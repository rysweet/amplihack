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

import os
import sys

# Ensure hooks directory is importable for both package and standalone execution
_hooks_dir = os.path.dirname(os.path.abspath(__file__))
if _hooks_dir not in sys.path:
    sys.path.insert(0, _hooks_dir)

# Re-export models
# Re-export LOCKING_AVAILABLE from file_lock_utils
import file_lock_utils

# Re-export delta analyzer
from power_steering_delta_analyzer import DeltaAnalyzer
from power_steering_models import (
    BlockSnapshot,
    DeltaAnalysisResult,
    FailureEvidence,
    PowerSteeringTurnState,
)

# Re-export state manager
from power_steering_state_manager import TurnStateManager

LOCKING_AVAILABLE = file_lock_utils.LOCKING_AVAILABLE

# Re-export get_shared_runtime_dir for backward compatibility with tests
# that patch "power_steering_state.get_shared_runtime_dir"
try:
    from git_utils import get_shared_runtime_dir
except ImportError as e:
    print(f"FATAL: Required dependency missing: {e}", file=sys.stderr)
    raise


__all__ = [
    "FailureEvidence",
    "BlockSnapshot",
    "PowerSteeringTurnState",
    "TurnStateManager",
    "DeltaAnalyzer",
    "DeltaAnalysisResult",
    "LOCKING_AVAILABLE",
]
