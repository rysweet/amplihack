"""Fleet module constants — centralized configuration values.

All thresholds, timeouts, and capacity values used across the fleet module.
Import from here instead of hardcoding in individual files.

Public API:
    Confidence thresholds, timing constants, capacity defaults.
"""

# ── Confidence Thresholds ──────────────────────────────────────────────
MIN_CONFIDENCE_SEND = 0.6        # Minimum confidence to inject a send_input action
MIN_CONFIDENCE_RESTART = 0.8     # Minimum confidence to restart a session
CONFIDENCE_COMPLETION = 0.9      # Confidence for completion detection
CONFIDENCE_ERROR = 0.85          # Confidence for error detection
CONFIDENCE_RUNNING = 0.8         # Confidence for running status
CONFIDENCE_IDLE = 0.7            # Confidence for idle status
CONFIDENCE_DEFAULT_RUNNING = 0.5 # Default confidence for unclassified output
CONFIDENCE_UNKNOWN = 0.3         # Confidence when status is unknown
CONFIDENCE_COPILOT_WAIT = 0.95   # Copilot fast-path wait confidence

# ── Time / Duration ────────────────────────────────────────────────────
DEFAULT_STUCK_THRESHOLD_SECONDS = 300.0  # 5 minutes without change = stuck
DEFAULT_POLL_INTERVAL_SECONDS = 60.0     # Fleet admiral poll interval
SUBPROCESS_TIMEOUT_SECONDS = 60          # SSH/subprocess timeout
DEFAULT_TUI_REFRESH_SECONDS = 60         # Simple TUI refresh interval
DEFAULT_DASHBOARD_REFRESH_SECONDS = 30   # Interactive dashboard refresh

# ── Capacity ───────────────────────────────────────────────────────────
DEFAULT_CAPTURE_LINES = 5000       # Terminal scrollback capture depth
DEFAULT_RECENT_MESSAGE_COUNT = 500 # Recent transcript entries for rich context
DEFAULT_MAX_AGENTS_PER_VM = 3      # Max concurrent agents per VM
DEFAULT_MAX_TURNS = 20             # Default task max turns

# ── Cost ───────────────────────────────────────────────────────────────
DEFAULT_COST_PER_HOUR = 0.576  # Standard_E16as_v5, March 2026

__all__ = [
    "MIN_CONFIDENCE_SEND",
    "MIN_CONFIDENCE_RESTART",
    "CONFIDENCE_COMPLETION",
    "CONFIDENCE_ERROR",
    "CONFIDENCE_RUNNING",
    "CONFIDENCE_IDLE",
    "CONFIDENCE_DEFAULT_RUNNING",
    "CONFIDENCE_UNKNOWN",
    "CONFIDENCE_COPILOT_WAIT",
    "DEFAULT_STUCK_THRESHOLD_SECONDS",
    "DEFAULT_POLL_INTERVAL_SECONDS",
    "SUBPROCESS_TIMEOUT_SECONDS",
    "DEFAULT_TUI_REFRESH_SECONDS",
    "DEFAULT_DASHBOARD_REFRESH_SECONDS",
    "DEFAULT_CAPTURE_LINES",
    "DEFAULT_RECENT_MESSAGE_COUNT",
    "DEFAULT_MAX_AGENTS_PER_VM",
    "DEFAULT_MAX_TURNS",
    "DEFAULT_COST_PER_HOUR",
]
