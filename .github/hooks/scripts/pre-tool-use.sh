#!/usr/bin/env bash
#
# Pre-Tool Use Hook for GitHub Copilot CLI
#
# Security validation - blocks dangerous operations
# This is Copilot-specific (permission control via permissionDecision)
#

set -euo pipefail

INPUT=$(cat)

# Extract tool name and command using Python for reliable JSON parsing
TOOL_INFO=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tool_name = data.get('toolName', '')
tool_args = json.loads(data.get('toolArgs', '{}'))
command = tool_args.get('command', '')
print(f'{tool_name}|{command}')
")

TOOL_NAME="${TOOL_INFO%%|*}"
COMMAND="${TOOL_INFO#*|}"

# Block dangerous --no-verify flag
if [[ "$COMMAND" == *"--no-verify"* ]] && [[ "$COMMAND" == *"git commit"* ]]; then
    echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"BLOCKED: --no-verify bypasses critical pre-commit security checks. Remove --no-verify flag.\"}"
    exit 0
fi

# Allow by default (no output = allow)
