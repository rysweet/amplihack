#!/usr/bin/env bash
#
# Error Occurred Hook for GitHub Copilot CLI
#
# Logs errors for debugging
#

set -euo pipefail

INPUT=$(cat)
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"

LOGS_DIR="$PROJECT_ROOT/.claude/runtime/logs/$SESSION_ID"
mkdir -p "$LOGS_DIR"

# Log error (JSON lines format)
echo "$INPUT" >> "$LOGS_DIR/errors.jsonl"

# Extract error message for console log
ERROR_MSG=$(echo "$INPUT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('error', {}).get('message', 'Unknown error'))" 2>/dev/null || echo "Unknown error")

echo "[$(date -Iseconds)] ERROR: $ERROR_MSG" >> "$LOGS_DIR/errors.log"

# No output needed
