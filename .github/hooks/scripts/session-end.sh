#!/usr/bin/env bash
# Session End Hook - Wrapper for Python hook
set -euo pipefail
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
python "$PROJECT_ROOT/.claude/tools/amplihack/hooks/stop.py"
