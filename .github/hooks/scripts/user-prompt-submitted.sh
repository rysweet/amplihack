#!/usr/bin/env bash
#
# User Prompt Submitted Hook Wrapper for GitHub Copilot CLI
#
# Copilot CLI specific - logs user prompts for audit trail
# Single source of truth approach: minimal bash implementation
#

set -euo pipefail

INPUT=$(cat)
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"

# Create logs directory
LOGS_DIR="$PROJECT_ROOT/.claude/runtime/logs/$SESSION_ID"
mkdir -p "$LOGS_DIR"

# Extract prompt from JSON (using python for reliable JSON parsing)
PROMPT=$(echo "$INPUT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('prompt', ''))")

# Log the prompt
echo "[$(date -Iseconds)] USER_PROMPT: $PROMPT" >> "$LOGS_DIR/prompts.log"

# No output needed (ignored by Copilot CLI)
