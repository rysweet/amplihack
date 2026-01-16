#!/usr/bin/env bash
#
# Post-Tool Use Hook for GitHub Copilot CLI
#
# Logs tool execution metrics
#

set -euo pipefail

INPUT=$(cat)
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"

METRICS_DIR="$PROJECT_ROOT/.claude/runtime/metrics"
mkdir -p "$METRICS_DIR"

# Log tool execution (JSON lines format)
echo "$INPUT" >> "$METRICS_DIR/tool_executions.jsonl"

# No output needed
