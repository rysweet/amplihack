#!/usr/bin/env bash
#
# Session Start Hook Wrapper for GitHub Copilot CLI
#
# This is a thin wrapper that calls the amplihack Python hook.
# Single source of truth: .claude/tools/amplihack/hooks/session_start.py
#

set -euo pipefail

# Locate project root (where .claude/ directory exists)
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Find the Python hook
PYTHON_HOOK="$PROJECT_ROOT/.claude/tools/amplihack/hooks/session_start.py"

if [ ! -f "$PYTHON_HOOK" ]; then
    echo "ERROR: Python hook not found at $PYTHON_HOOK" >&2
    exit 1
fi

# Call the Python hook with stdin/stdout passthrough
python3 "$PYTHON_HOOK"
