#!/usr/bin/env bash
# Wrapper: Calls Python stop hook
set -euo pipefail

# Get absolute path to project root
# This script is in .github/hooks/scripts/, so go up 3 levels
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Try multiple possible hook locations (handles different installation scenarios)
HOOK_LOCATIONS=(
    "$PROJECT_ROOT/.claude/tools/amplihack/hooks/stop.py"
    "$PROJECT_ROOT/.claude/tools/amplihack/hooks/session_stop.py"
    "$(dirname "$SCRIPT_DIR")/../.claude/tools/amplihack/hooks/stop.py"
)

PYTHON_HOOK=""
for location in "${HOOK_LOCATIONS[@]}"; do
    if [[ -f "$location" ]]; then
        PYTHON_HOOK="$location"
        break
    fi
done

if [[ -z "$PYTHON_HOOK" ]]; then
    echo "Error: Stop hook not found. Tried:" >&2
    for loc in "${HOOK_LOCATIONS[@]}"; do
        echo "  - $loc" >&2
    done
    echo "  Project root: $PROJECT_ROOT" >&2
    echo "  Script dir: $SCRIPT_DIR" >&2
    # Don't block - just log error and allow stop
    echo '{"decision":"approve"}'
    exit 0
fi

# Call Python hook, passing stdin through
python3 "$PYTHON_HOOK" "$@"
