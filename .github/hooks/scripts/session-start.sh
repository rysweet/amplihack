#!/usr/bin/env bash
#
# Session Start Hook for GitHub Copilot CLI
#
# Mirrors functionality from .claude/tools/amplihack/hooks/session_start.py
#
# What this hook does:
# - Initializes session state directory
# - Injects user preferences into session context
# - Logs session startup metrics
# - Checks for version mismatches (future enhancement)
#
# Input: JSON on stdin with session context
# Output: JSON on stdout with additionalContext field
#

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract project root from environment or use current directory
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"

# Create runtime directories
RUNTIME_DIR="$PROJECT_ROOT/.claude/runtime"
LOGS_DIR="$RUNTIME_DIR/logs/$SESSION_ID"
METRICS_DIR="$RUNTIME_DIR/metrics"

mkdir -p "$LOGS_DIR"
mkdir -p "$METRICS_DIR"

# Log function
log() {
    local level="${1:-INFO}"
    local message="$2"
    echo "[$(date -Iseconds)] [$level] session_start: $message" >> "$LOGS_DIR/session_start.log"
}

log "INFO" "Session started: $SESSION_ID"

# Save metric function
save_metric() {
    local metric_name="$1"
    local metric_value="$2"
    local metric_file="$METRICS_DIR/session_start_metrics.jsonl"

    echo "{\"timestamp\":\"$(date -Iseconds)\",\"session_id\":\"$SESSION_ID\",\"metric\":\"$metric_name\",\"value\":$metric_value}" >> "$metric_file"
}

# Extract prompt from input using jq
PROMPT=$(echo "$INPUT" | jq -r '.prompt // ""')
PROMPT_LENGTH=${#PROMPT}

log "INFO" "Prompt length: $PROMPT_LENGTH"
save_metric "prompt_length" "$PROMPT_LENGTH"

# Build context parts array
CONTEXT_PARTS=()

# Add project context
CONTEXT_PARTS+=("## Project Context")
CONTEXT_PARTS+=("This is the Microsoft Hackathon 2025 Agentic Coding project.")
CONTEXT_PARTS+=("Focus on building AI-powered development tools.")
CONTEXT_PARTS+=("")

# Check for recent discoveries
DISCOVERIES_FILE="$PROJECT_ROOT/.claude/context/DISCOVERIES.md"
if [[ -f "$DISCOVERIES_FILE" ]]; then
    CONTEXT_PARTS+=("## Recent Learnings")
    CONTEXT_PARTS+=("Check .claude/context/DISCOVERIES.md fer recent insights.")
    CONTEXT_PARTS+=("")
fi

# Read and inject user preferences
PREFERENCES_FILE="$PROJECT_ROOT/.claude/context/USER_PREFERENCES.md"
if [[ -f "$PREFERENCES_FILE" ]]; then
    log "INFO" "Loading user preferences from $PREFERENCES_FILE"

    CONTEXT_PARTS+=("## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)")
    CONTEXT_PARTS+=("")
    CONTEXT_PARTS+=("Apply these preferences to all responses. These preferences are READ-ONLY except when using /amplihack:customize command.")
    CONTEXT_PARTS+=("")
    CONTEXT_PARTS+=("💡 **Preference Management**: Use /amplihack:customize to view or modify preferences.")
    CONTEXT_PARTS+=("")

    # Read full preferences content
    PREFS_CONTENT=$(cat "$PREFERENCES_FILE")
    CONTEXT_PARTS+=("$PREFS_CONTENT")
    CONTEXT_PARTS+=("")

    log "INFO" "Injected full USER_PREFERENCES.md content into session"
    save_metric "preferences_injected" "1"
else
    log "WARNING" "No USER_PREFERENCES.md found - skipping preference injection"
    save_metric "preferences_injected" "0"
fi

# Add workflow information
CONTEXT_PARTS+=("## 📝 Default Workflow")
CONTEXT_PARTS+=("The multi-step workflow is automatically followed by \`/ultrathink\`")
CONTEXT_PARTS+=("• To view the workflow: Read .claude/workflow/DEFAULT_WORKFLOW.md")
CONTEXT_PARTS+=("• To customize: Edit the workflow file directly")
CONTEXT_PARTS+=("• Steps include: Requirements → Issue → Branch → Design → Implement → Review → Merge")
CONTEXT_PARTS+=("")

# Add verbosity instructions
CONTEXT_PARTS+=("## 🎤 Verbosity Mode")
CONTEXT_PARTS+=("• Current setting: balanced")
CONTEXT_PARTS+=("• To enable verbose: Use TodoWrite tool frequently and provide detailed explanations")
CONTEXT_PARTS+=("• Claude will adapt to yer verbosity preference in responses")
CONTEXT_PARTS+=("")

# Join context parts with newlines
FULL_CONTEXT=""
for part in "${CONTEXT_PARTS[@]}"; do
    FULL_CONTEXT+="$part"$'\n'
done

log "INFO" "Session initialized with $(echo -n "$FULL_CONTEXT" | wc -c) characters of context"

# Output JSON response with additionalContext
# Note: Using jq to properly escape and format the JSON output
echo "$FULL_CONTEXT" | jq -Rs '{
    hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: .
    }
}'

log "INFO" "Session start hook completed successfully"
