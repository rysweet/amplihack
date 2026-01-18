"""Reflection module for the amplihack framework."""

# Export main reflection functions
# NOTE: Only export functions that actually exist in reflection.py
from .lightweight_analyzer import LightweightAnalyzer
from .reflection import analyze_session_patterns, process_reflection_analysis

# Export interactive reflection system components
from .semaphore import LockData, ReflectionLock
from .state_machine import (
    ReflectionState,
    ReflectionStateData,
    ReflectionStateMachine,
)

__all__ = [
    # Existing reflection functions
    "analyze_session_patterns",
    "process_reflection_analysis",
    # Interactive reflection system
    "ReflectionLock",
    "LockData",
    "ReflectionState",
    "ReflectionStateData",
    "ReflectionStateMachine",
    "LightweightAnalyzer",
]
