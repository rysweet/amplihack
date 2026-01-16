#!/usr/bin/env bash
# Wrapper: Calls Python pre_tool_use hook
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Try multiple possible hook locations
HOOK_LOCATIONS=(
    "$PROJECT_ROOT/.claude/tools/amplihack/hooks/pre_tool_use.py"
    "$PROJECT_ROOT/.claude/tools/amplihack/hooks/power_steering.py"
)

PYTHON_HOOK=""
for location in "${HOOK_LOCATIONS[@]}"; do
    if [[ -f "$location" ]]; then
        PYTHON_HOOK="$location"
        break
    fi
done

if [[ -z "$PYTHON_HOOK" ]]; then
    # Fallback: allow all tools (no blocking)
    echo '{"permissionDecision":"allow"}'
    exit 0
fi

# Call Python hook, passing stdin through
python3 "$PYTHON_HOOK" "$@"
