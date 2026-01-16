#!/usr/bin/env bash
# Post-Tool Use Hook - Metrics logging
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT=$(cat)
mkdir -p "$PROJECT_ROOT/.claude/runtime/metrics"
echo "$INPUT" >> "$PROJECT_ROOT/.claude/runtime/metrics/tool-usage.jsonl"
