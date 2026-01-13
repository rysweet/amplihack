"""
Power Steering Hook for Amplifier.

Autonomous session completion verification that prevents sessions from ending
prematurely by analyzing work against configurable considerations.

Philosophy:
- Fail-Open: Never block users due to bugs
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with clear API
"""

from .checker import ConsiderationResult, PowerSteeringChecker, PowerSteeringResult
from .heuristics import HEURISTIC_PATTERNS, AddressedChecker
from .hook import PowerSteeringHook
from .state import PowerSteeringState, StateManager

__all__ = [
    "PowerSteeringHook",
    "PowerSteeringChecker",
    "PowerSteeringResult",
    "ConsiderationResult",
    "PowerSteeringState",
    "StateManager",
    "AddressedChecker",
    "HEURISTIC_PATTERNS",
]
