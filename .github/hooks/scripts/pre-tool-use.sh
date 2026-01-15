#!/usr/bin/env bash
#
# Pre Tool Use Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/pre_tool_use.py
#
# What this hook does:
# - Validates tool execution requests
# - Enforces safety policies (e.g., block --no-verify flags)
# - Logs validation attempts
#
# Input: JSON on stdin with toolUse details
# Output: JSON on stdout with optional 'block' and 'message' fields
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
    echo "[$(date -Iseconds)] [$level] pre_tool_use: $message" >> "$LOGS_DIR/pre_tool_use.log"
}

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$METRICS_DIR/pre_tool_use_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Extract tool information using jq
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolUse.name // "unknown"')
TOOL_INPUT=$(echo "$INPUT" | jq -c '.toolUse.input // {}')

log "INFO" "Validating tool use: $TOOL_NAME"

# Check for Bash command with --no-verify flag
if [[ "$TOOL_NAME" == "Bash" ]]; then
    COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // ""')

    # Check for dangerous --no-verify flag
    if [[ "$COMMAND" == *"--no-verify"* ]] && [[ "$COMMAND" == *"git commit"* || "$COMMAND" == *"git push"* ]]; then
        log "ERROR" "BLOCKED: Dangerous operation detected: $COMMAND"
        save_metric "dangerous_operations_blocked" "1"

        # Output block decision with error message
        jq -n '{
            block: true,
            message: "🚫 OPERATION BLOCKED\n\nYe attempted to use --no-verify which bypasses critical quality checks:\n- Code formatting (ruff, prettier)\n- Type checking (pyright)\n- Secret detection\n- Trailing whitespace fixes\n\nThis defeats the purpose of our quality gates, matey!\n\n✅ Instead, fix the underlying issues:\n1. Run: pre-commit run --all-files\n2. Fix the violations\n3. Commit without --no-verify\n\nFor true emergencies, ask a human to override this protection.\n\n🔒 This protection cannot be disabled programmatically."
        }'
        exit 0
    fi
fi

# Allow all other operations
log "INFO" "Tool validation passed: $TOOL_NAME"
save_metric "tools_validated" "1"

# Output empty object (no blocking)
echo '{}'

exit 0
