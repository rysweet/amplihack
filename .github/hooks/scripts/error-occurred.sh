#!/usr/bin/env bash
# Error Occurred Hook - Error logging
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT=$(cat)
mkdir -p "$PROJECT_ROOT/.claude/runtime/logs"
echo "$INPUT" >> "$PROJECT_ROOT/.claude/runtime/logs/errors.jsonl"
