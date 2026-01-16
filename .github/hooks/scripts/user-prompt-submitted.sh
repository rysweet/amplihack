#!/usr/bin/env bash
# User Prompt Submitted Hook - Simple logging wrapper
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
INPUT=$(cat)
mkdir -p "$PROJECT_ROOT/.claude/runtime/logs"
echo "$INPUT" >> "$PROJECT_ROOT/.claude/runtime/logs/user-prompts.jsonl"
