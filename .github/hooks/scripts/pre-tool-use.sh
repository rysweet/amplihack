#!/usr/bin/env bash
# Pre-Tool Use Hook - Safety validation
set -euo pipefail
INPUT=$(cat)

# Block dangerous operations (requires jq)
if command -v jq >/dev/null 2>&1; then
    TOOL_ARGS=$(echo "$INPUT" | jq -r '.toolArgs // "{}"' 2>/dev/null || echo "{}")
    if echo "$TOOL_ARGS" | grep -qE -- '--no-verify|--force.*push|rm -rf /'; then
        echo '{"permissionDecision":"deny","permissionDecisionReason":"Dangerous operation blocked"}'
        exit 0
    fi
fi
