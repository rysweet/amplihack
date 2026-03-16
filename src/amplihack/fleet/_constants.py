"""Fleet module constants — centralized configuration values.

All thresholds, timeouts, and capacity values used across the fleet module.
Import from here instead of hardcoding in individual files.

Public API:
    Confidence thresholds, timing constants, capacity defaults, health thresholds,
    default file paths.
"""

from pathlib import Path

# ── File Paths ────────────────────────────────────────────────────────
DEFAULT_FLEET_DIR = Path.home() / ".amplihack" / "fleet"
DEFAULT_PROJECTS_PATH = DEFAULT_FLEET_DIR / "projects.toml"
DEFAULT_LAST_SCOUT_PATH = DEFAULT_FLEET_DIR / "last_scout.json"

# ── Confidence Thresholds ──────────────────────────────────────────────
MIN_CONFIDENCE_SEND = 0.6  # Minimum confidence to inject a send_input action
MIN_CONFIDENCE_RESTART = 0.8  # Minimum confidence to restart a session
CONFIDENCE_COMPLETION = 0.9  # Confidence for completion detection
CONFIDENCE_ERROR = 0.85  # Confidence for error detection
CONFIDENCE_RUNNING = 0.8  # Confidence for running status
CONFIDENCE_IDLE = 0.7  # Confidence for idle status
CONFIDENCE_DEFAULT_RUNNING = 0.5  # Default confidence for unclassified output
CONFIDENCE_UNKNOWN = 0.3  # Confidence when status is unknown
CONFIDENCE_COPILOT_WAIT = 0.95  # Copilot fast-path wait confidence

# ── Time / Duration ────────────────────────────────────────────────────
DEFAULT_STUCK_THRESHOLD_SECONDS = 300.0  # 5 minutes without change = stuck
DEFAULT_POLL_INTERVAL_SECONDS = 60.0  # Fleet admiral poll interval
SUBPROCESS_TIMEOUT_SECONDS = 120  # SSH/subprocess timeout (Bastion tunnels need ~90s)
SUBPROCESS_TIMEOUT_KILL_SECONDS = 30  # Shorter timeout for kill operations
SSH_ACTION_TIMEOUT_SECONDS = 30  # Timeout for send_input/restart SSH actions
AZ_CLI_TIMEOUT_SECONDS = 30  # az vm list is fast (no Bastion tunnel)
CLI_WATCH_TIMEOUT_SECONDS = 60  # fleet watch tmux capture timeout
DEFAULT_TUI_REFRESH_SECONDS = 60  # Simple TUI refresh interval
DEFAULT_DASHBOARD_REFRESH_SECONDS = 30  # Interactive dashboard refresh

# ── Capacity ───────────────────────────────────────────────────────────
DEFAULT_CAPTURE_LINES = 50  # Terminal scrollback for fleet poll (per-VM, runs often)
DEFAULT_DETAIL_CAPTURE_LINES = 500  # Deeper capture for session detail view (on-demand)
MAX_CAPTURE_LINES = 10000  # Upper bound for capture_lines parameter
DEFAULT_RECENT_MESSAGE_COUNT = 500  # Recent transcript entries for rich context
DEFAULT_MAX_AGENTS_PER_VM = 3  # Max concurrent agents per VM
DEFAULT_MAX_TURNS = 20  # Default task max turns

# ── LLM ──────────────────────────────────────────────────────────────
DEFAULT_LLM_MAX_TOKENS = 128000  # Max output tokens for admiral reasoning
TRANSCRIPT_MAX_TOKENS = 128000  # Max input tokens for transcript context (full scrollback)
MIN_SUBSTANTIAL_OUTPUT_LEN = 50  # Chars threshold for "has substantial output"

# ── Health Thresholds ─────────────────────────────────────────────────
MEMORY_HEALTHY_MAX_PCT = 95.0  # Below this = healthy
DISK_HEALTHY_MAX_PCT = 90.0  # Below this = healthy
MEMORY_ATTENTION_THRESHOLD_PCT = 80.0  # Above this = needs attention
DISK_ATTENTION_THRESHOLD_PCT = 80.0  # Above this = needs attention

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
    "SUBPROCESS_TIMEOUT_KILL_SECONDS",
    "DEFAULT_TUI_REFRESH_SECONDS",
    "DEFAULT_DASHBOARD_REFRESH_SECONDS",
    "DEFAULT_CAPTURE_LINES",
    "DEFAULT_DETAIL_CAPTURE_LINES",
    "DEFAULT_RECENT_MESSAGE_COUNT",
    "DEFAULT_MAX_AGENTS_PER_VM",
    "DEFAULT_MAX_TURNS",
    "MEMORY_HEALTHY_MAX_PCT",
    "DISK_HEALTHY_MAX_PCT",
    "MEMORY_ATTENTION_THRESHOLD_PCT",
    "DISK_ATTENTION_THRESHOLD_PCT",
    "DEFAULT_COST_PER_HOUR",
    "SSH_ACTION_TIMEOUT_SECONDS",
    "AZ_CLI_TIMEOUT_SECONDS",
    "CLI_WATCH_TIMEOUT_SECONDS",
    "MAX_CAPTURE_LINES",
    "DEFAULT_LLM_MAX_TOKENS",
    "TRANSCRIPT_MAX_TOKENS",
    "MIN_SUBSTANTIAL_OUTPUT_LEN",
    "DEFAULT_FLEET_DIR",
    "DEFAULT_PROJECTS_PATH",
    "DEFAULT_LAST_SCOUT_PATH",
]
