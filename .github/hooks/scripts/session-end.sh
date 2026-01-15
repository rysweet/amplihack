#!/usr/bin/env bash
#
# Session End Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/stop.py
#
# What this hook does:
# - Checks for lock flag to enable continuous work mode
# - Cleans up session resources
# - Persists session state and metrics
# - Optionally blocks session end if work is incomplete
#
# Input: JSON on stdin with session info and transcript
# Output: JSON on stdout with decision (approve/block) and optional reason
#

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract project root from environment or use current directory
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"

# Paths
RUNTIME_DIR="$PROJECT_ROOT/.claude/runtime"
LOGS_DIR="$RUNTIME_DIR/logs/$SESSION_ID"
LOCKS_DIR="$RUNTIME_DIR/locks"
LOCK_FLAG="$LOCKS_DIR/.lock_active"
CONTINUATION_PROMPT_FILE="$LOCKS_DIR/.continuation_prompt"

mkdir -p "$LOGS_DIR"
mkdir -p "$LOCKS_DIR"

# Log function
log() {
    local level="${1:-INFO}"
    local message="$2"
    echo "[$(date -Iseconds)] [$level] stop: $message" >> "$LOGS_DIR/stop.log"
}

log "INFO" "=== STOP HOOK STARTED ==="

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$RUNTIME_DIR/metrics/stop_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Default continuation prompt
DEFAULT_CONTINUATION_PROMPT="we must keep pursuin' the user's objective and must not stop the turn - look fer any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as ye can, arrr!"

# Check if lock flag exists
if [[ -f "$LOCK_FLAG" ]]; then
    log "INFO" "Lock is active - blocking stop to continue working"
    save_metric "lock_blocks" "1"

    # Read custom continuation prompt or use default
    CONTINUATION_PROMPT="$DEFAULT_CONTINUATION_PROMPT"
    if [[ -f "$CONTINUATION_PROMPT_FILE" ]]; then
        CUSTOM_PROMPT=$(cat "$CONTINUATION_PROMPT_FILE")
        if [[ -n "$CUSTOM_PROMPT" ]]; then
            # Check length constraint (1000 chars max)
            if [[ ${#CUSTOM_PROMPT} -le 1000 ]]; then
                CONTINUATION_PROMPT="$CUSTOM_PROMPT"
                log "INFO" "Using custom continuation prompt (${#CUSTOM_PROMPT} chars)"
            else
                log "WARNING" "Custom prompt too long (${#CUSTOM_PROMPT} chars) - using default"
            fi
        fi
    fi

    # Increment lock counter
    LOCK_COUNTER_FILE="$LOCKS_DIR/$SESSION_ID/lock_invocations.txt"
    mkdir -p "$(dirname "$LOCK_COUNTER_FILE")"

    LOCK_COUNT=0
    if [[ -f "$LOCK_COUNTER_FILE" ]]; then
        LOCK_COUNT=$(cat "$LOCK_COUNTER_FILE")
    fi
    LOCK_COUNT=$((LOCK_COUNT + 1))
    echo "$LOCK_COUNT" > "$LOCK_COUNTER_FILE"

    log "INFO" "Lock mode invocation count: $LOCK_COUNT"
    log "INFO" "=== STOP HOOK ENDED (decision: block - lock active) ==="

    # Output block decision with continuation prompt
    jq -n --arg reason "$CONTINUATION_PROMPT" '{
        decision: "block",
        reason: $reason
    }'
    exit 0
fi

# No lock - allow stop
log "INFO" "No lock active - allowing stop"
log "INFO" "=== STOP HOOK ENDED (decision: approve) ==="

# Cleanup: Mark session as completed
COMPLETION_FILE="$LOGS_DIR/session_completed.txt"
date -Iseconds > "$COMPLETION_FILE"

# Save final metrics
save_metric "session_completed" "1"

# Output approve decision
jq -n '{
    decision: "approve"
}'

exit 0
