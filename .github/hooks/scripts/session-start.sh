#!/usr/bin/env bash
#
# Session Start Hook for GitHub Copilot CLI
# 
# WRAPPER: Calls the Python hook to maintain single source of truth
#

set -euo pipefail

# Find project root
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Call Python hook with JSON input
python "$PROJECT_ROOT/.claude/tools/amplihack/hooks/session_start.py"
