#!/usr/bin/env bash
#
# Post Tool Use Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/post_tool_use.py
#
# What this hook does:
# - Logs tool execution results
# - Collects tool usage metrics
# - Categorizes tool types for analytics
# - Tracks execution duration if available
#
# Input: JSON on stdin with toolUse and result
# Output: JSON on stdout with optional metadata
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
    echo "[$(date -Iseconds)] [$level] post_tool_use: $message" >> "$LOGS_DIR/post_tool_use.log"
}

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$METRICS_DIR/post_tool_use_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Extract tool information using jq
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolUse.name // "unknown"')
RESULT=$(echo "$INPUT" | jq -c '.result // {}')
DURATION_MS=$(echo "$RESULT" | jq -r '.duration_ms // "null"')

log "INFO" "Tool used: $TOOL_NAME"

# Save tool usage metric with duration if available
if [[ "$DURATION_MS" != "null" ]]; then
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"tool_usage\",\"tool\":\"$TOOL_NAME\",\"duration_ms\":$DURATION_MS}" >> "$METRICS_DIR/post_tool_use_metrics.jsonl"
else
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"tool_usage\",\"tool\":\"$TOOL_NAME\"}" >> "$METRICS_DIR/post_tool_use_metrics.jsonl"
fi

# Check for errors in tool result
ERROR_MSG=$(echo "$RESULT" | jq -r '.error // ""')
if [[ -n "$ERROR_MSG" ]]; then
    log "WARNING" "Tool $TOOL_NAME reported error: $ERROR_MSG"
    save_metric "tool_errors" "1"
fi

# Track high-level metrics by tool category
case "$TOOL_NAME" in
    Bash)
        save_metric "bash_commands" "1"
        ;;
    Read|Write|Edit|MultiEdit)
        save_metric "file_operations" "1"
        ;;
    Grep|Glob)
        save_metric "search_operations" "1"
        ;;
    Task)
        save_metric "agent_invocations" "1"
        ;;
esac

# Output metadata (empty if no errors)
if [[ -n "$ERROR_MSG" ]]; then
    jq -n --arg tool "$TOOL_NAME" --arg err "$ERROR_MSG" '{
        metadata: {
            warning: ("Tool " + $tool + " encountered an error"),
            tool: $tool,
            error: $err
        }
    }'
else
    echo '{}'
fi

exit 0
