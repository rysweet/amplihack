#!/usr/bin/env python3
"""
Shared constants for the power-steering state management subsystem.

Philosophy:
- Ruthlessly Simple: Single file with all shared constants
- Modular: One responsibility - constant definitions
- Regeneratable: Can be rebuilt from this docstring alone

Public API (the "studs"):
    MAX_CONSECUTIVE_BLOCKS: Maximum blocks before auto-approve
    WARNING_THRESHOLD: Blocks before escalation warning
    LOOP_DETECTION_THRESHOLD: Identical fingerprints to trigger loop detection
    CLAIM_KEYWORDS: Keywords for fallback completion claim detection
    MAX_SAVE_RETRIES: Maximum retries for atomic state writes
    INITIAL_RETRY_DELAY: Starting delay for exponential backoff (seconds)
    LOCK_TIMEOUT_SECONDS: Default timeout for file lock acquisition
    MAX_TURN_COUNT: Upper bound for reasonable turn counts (validation)
"""

__all__ = [
    "MAX_CONSECUTIVE_BLOCKS",
    "WARNING_THRESHOLD",
    "LOOP_DETECTION_THRESHOLD",
    "CLAIM_KEYWORDS",
    "MAX_SAVE_RETRIES",
    "INITIAL_RETRY_DELAY",
    "LOCK_TIMEOUT_SECONDS",
    "MAX_TURN_COUNT",
]

# Auto-approve threshold: after this many consecutive blocks, let the user go
MAX_CONSECUTIVE_BLOCKS: int = 5

# Escalation warning: halfway to max blocks
WARNING_THRESHOLD: int = 2

# Loop detection: number of identical failure fingerprints to trigger
LOOP_DETECTION_THRESHOLD: int = 3

# Fallback claim detection keywords (used when LLM unavailable)
CLAIM_KEYWORDS: list[str] = [
    "completed",
    "finished",
    "all done",
    "tests passing",
    "ci green",
    "pr ready",
    "workflow complete",
]

# Atomic write retry configuration
MAX_SAVE_RETRIES: int = 3
INITIAL_RETRY_DELAY: float = 0.1  # 100ms

# File lock timeout
LOCK_TIMEOUT_SECONDS: float = 2.0

# Validation bounds
MAX_TURN_COUNT: int = 1000
