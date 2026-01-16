#!/usr/bin/env bash
# Wrapper: Calls Python hook from .claude/tools/amplihack/hooks/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PYTHON_HOOK="$PROJECT_ROOT/.claude/tools/amplihack/hooks/stop.py"

if [[ ! -f "$PYTHON_HOOK" ]]; then
    echo "Error: Python hook not found: $PYTHON_HOOK" >&2
    exit 1
fi

# Call Python hook, passing stdin through
python3 "$PYTHON_HOOK" "$@"
