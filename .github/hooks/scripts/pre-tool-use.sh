#!/usr/bin/env bash
# Wrapper: Calls Python power steering hook
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# For pre-tool-use, we use the power steering hook if available
PYTHON_HOOK="$PROJECT_ROOT/.claude/tools/amplihack/hooks/power_steering.py"

if [[ -f "$PYTHON_HOOK" ]]; then
    python3 "$PYTHON_HOOK" "$@"
else
    # Fallback: allow all tools (no blocking)
    echo '{"permissionDecision":"allow"}'
fi
