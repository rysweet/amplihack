#!/usr/bin/env bash
#
# User Prompt Submitted Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/user_prompt_submit.py
#
# What this hook does:
# - Logs user prompts for audit trail
# - Injects user preferences on every message (for REPL continuity)
# - Extracts and tracks prompt metadata
#
# Input: JSON on stdin with userMessage
# Output: JSON on stdout with additionalContext field
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
METRICS_DIR="$RUNTIME_DIR/metrics"

mkdir -p "$LOGS_DIR"
mkdir -p "$METRICS_DIR"

# Log function
log() {
    local level="${1:-INFO}"
    local message="$2"
    echo "[$(date -Iseconds)] [$level] user_prompt_submit: $message" >> "$LOGS_DIR/user_prompt_submit.log"
}

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$METRICS_DIR/user_prompt_submit_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Extract user message text using jq
USER_PROMPT=$(echo "$INPUT" | jq -r '.userMessage.text // ""')
PROMPT_LENGTH=${#USER_PROMPT}

log "INFO" "User prompt received (length: $PROMPT_LENGTH)"
save_metric "prompt_length" "$PROMPT_LENGTH"

# Log the prompt for audit trail (truncate if too long)
AUDIT_FILE="$LOGS_DIR/prompts_audit.jsonl"
if [[ $PROMPT_LENGTH -lt 500 ]]; then
    PROMPT_PREVIEW="$USER_PROMPT"
else
    PROMPT_PREVIEW="${USER_PROMPT:0:500}..."
fi

echo "{\"timestamp\":\"$(date -Iseconds)\",\"length\":$PROMPT_LENGTH,\"preview\":$(echo "$PROMPT_PREVIEW" | jq -Rs .)}" >> "$AUDIT_FILE"

# Build context parts for injection
CONTEXT_PARTS=()

# Read and inject user preferences (for REPL continuity)
PREFERENCES_FILE="$PROJECT_ROOT/.claude/context/USER_PREFERENCES.md"
if [[ -f "$PREFERENCES_FILE" ]]; then
    log "INFO" "Injecting user preferences"

    # Extract key preferences using grep/sed
    COMMUNICATION_STYLE=$(grep -A 1 "^### Communication Style" "$PREFERENCES_FILE" 2>/dev/null | tail -1 | xargs || echo "")
    VERBOSITY=$(grep -A 1 "^### Verbosity" "$PREFERENCES_FILE" 2>/dev/null | tail -1 | xargs || echo "")
    COLLABORATION_STYLE=$(grep -A 1 "^### Collaboration Style" "$PREFERENCES_FILE" 2>/dev/null | tail -1 | xargs || echo "")

    # Build preference summary
    CONTEXT_PARTS+=("🎯 ACTIVE USER PREFERENCES (MANDATORY - Apply to all responses):")

    [[ -n "$COMMUNICATION_STYLE" && "$COMMUNICATION_STYLE" != "(not set)" ]] && \
        CONTEXT_PARTS+=("• Communication Style: $COMMUNICATION_STYLE - Use this style in yer response, savvy?")

    [[ -n "$VERBOSITY" && "$VERBOSITY" != "(not set)" ]] && \
        CONTEXT_PARTS+=("• Verbosity: $VERBOSITY - Match this detail level, matey!")

    [[ -n "$COLLABORATION_STYLE" && "$COLLABORATION_STYLE" != "(not set)" ]] && \
        CONTEXT_PARTS+=("• Collaboration Style: $COLLABORATION_STYLE - Follow this approach, arrr!")

    CONTEXT_PARTS+=("")
    CONTEXT_PARTS+=("Apply these preferences to this response. These preferences are READ-ONLY except when using /amplihack:customize command.")
    CONTEXT_PARTS+=("")

    PREFS_COUNT=$(( ${#COMMUNICATION_STYLE} > 0 ? 1 : 0 ))
    PREFS_COUNT=$(( PREFS_COUNT + ${#VERBOSITY} > 0 ? 1 : 0 ))
    PREFS_COUNT=$(( PREFS_COUNT + ${#COLLABORATION_STYLE} > 0 ? 1 : 0 ))

    log "INFO" "Injected $PREFS_COUNT preferences"
    save_metric "preferences_injected" "$PREFS_COUNT"
else
    log "WARNING" "No USER_PREFERENCES.md found - skipping preference injection"
    save_metric "preferences_injected" "0"
fi

# Join context parts with newlines
FULL_CONTEXT=""
for part in "${CONTEXT_PARTS[@]}"; do
    FULL_CONTEXT+="$part"$'\n'
done

CONTEXT_LENGTH=${#FULL_CONTEXT}
log "INFO" "Context injected: $CONTEXT_LENGTH characters"
save_metric "context_length" "$CONTEXT_LENGTH"

# Output JSON response with additionalContext
echo "$FULL_CONTEXT" | jq -Rs '{
    additionalContext: .
}'

exit 0
