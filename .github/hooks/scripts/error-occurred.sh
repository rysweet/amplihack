#!/usr/bin/env bash
# Wrapper: Minimal error logging
set -euo pipefail

# Read input for potential logging
INPUT=$(cat)

# For now, just pass through (can add Python hook later if needed)
# Future: Call .claude/tools/amplihack/hooks/error_handler.py when implemented
exit 0
