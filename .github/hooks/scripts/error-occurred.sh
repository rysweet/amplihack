#!/usr/bin/env bash
#
# Error Occurred Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/error_protocol.py
#
# What this hook does:
# - Tracks and logs errors for debugging
# - Categorizes error severity
# - Collects error metrics for analysis
# - Provides structured error information
#
# Input: JSON on stdin with error details
# Output: JSON on stdout (typically empty - just logging)
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
ERROR_LOG_DIR="$RUNTIME_DIR/errors"

mkdir -p "$LOGS_DIR"
mkdir -p "$METRICS_DIR"
mkdir -p "$ERROR_LOG_DIR"

# Log function
log() {
    local level="${1:-INFO}"
    local message="$2"
    echo "[$(date -Iseconds)] [$level] error_occurred: $message" >> "$LOGS_DIR/error_occurred.log"
}

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$METRICS_DIR/error_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Extract error information using jq
ERROR_TYPE=$(echo "$INPUT" | jq -r '.error.type // "unknown"')
ERROR_MESSAGE=$(echo "$INPUT" | jq -r '.error.message // "No message provided"')
ERROR_CONTEXT=$(echo "$INPUT" | jq -r '.error.context // "No context provided"')
SEVERITY=$(echo "$INPUT" | jq -r '.error.severity // "error"')

log "ERROR" "Error occurred: $ERROR_TYPE - $ERROR_MESSAGE"

# Save structured error to error log
ERROR_FILE="$ERROR_LOG_DIR/error_$(date +%Y%m%d_%H%M%S).json"
echo "$INPUT" | jq -c '. + {
    timestamp: (now | todate),
    session_id: env.SESSION_ID
}' > "$ERROR_FILE"

log "INFO" "Error details saved to: $ERROR_FILE"

# Save metrics by error type and severity
save_metric "total_errors" "1"
save_metric "error_type_$ERROR_TYPE" "1"
save_metric "error_severity_$SEVERITY" "1"

# Categorize common error patterns
case "$ERROR_MESSAGE" in
    *"timeout"*|*"timed out"*)
        save_metric "timeout_errors" "1"
        log "INFO" "Categorized as: timeout error"
        ;;
    *"permission"*|*"denied"*)
        save_metric "permission_errors" "1"
        log "INFO" "Categorized as: permission error"
        ;;
    *"not found"*|*"missing"*)
        save_metric "not_found_errors" "1"
        log "INFO" "Categorized as: not found error"
        ;;
    *"import"*|*"module"*)
        save_metric "import_errors" "1"
        log "INFO" "Categorized as: import error"
        ;;
    *"syntax"*|*"parse"*)
        save_metric "syntax_errors" "1"
        log "INFO" "Categorized as: syntax error"
        ;;
esac

# Write to stderr for immediate visibility
echo "⚠️  Error logged: $ERROR_TYPE - $ERROR_MESSAGE" >&2

# Output empty object (no action needed)
echo '{}'

exit 0
