#!/usr/bin/env bash
#
# Session End Hook Wrapper for GitHub Copilot CLI
#
# Thin wrapper calling: .claude/tools/amplihack/hooks/stop.py
#

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PYTHON_HOOK="$PROJECT_ROOT/.claude/tools/amplihack/hooks/stop.py"

if [ ! -f "$PYTHON_HOOK" ]; then
    echo "ERROR: Python hook not found at $PYTHON_HOOK" >&2
    exit 1
fi

python3 "$PYTHON_HOOK"
