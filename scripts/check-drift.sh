#!/usr/bin/env bash
# check-drift.sh — Detect drift between the three sync locations for skills and agents.
#
# Skills must stay in sync across:
#   .claude/skills/            (source of truth)
#   amplifier-bundle/skills/
#   docs/claude/skills/
#
# Agents must stay in sync across:
#   .claude/agents/            (source of truth)
#   amplifier-bundle/agents/
#   docs/claude/agents/
#
# Exits 0 if no drift, non-zero if any drift detected.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DRIFT_FOUND=0

# Compare two directories, excluding __pycache__. Reports differences.
# Usage: compare_dirs <label> <dir_a> <dir_b>
compare_dirs() {
    local label="$1"
    local dir_a="$2"
    local dir_b="$3"

    echo "Checking: $label"
    echo "  A: $dir_a"
    echo "  B: $dir_b"

    # Check for missing directories
    if [ ! -d "$dir_a" ] && [ ! -d "$dir_b" ]; then
        echo "  DRIFT: Both directories are missing"
        DRIFT_FOUND=1
        return
    fi

    if [ ! -d "$dir_a" ]; then
        echo "  DRIFT: Missing directory: $dir_a"
        DRIFT_FOUND=1
        return
    fi

    if [ ! -d "$dir_b" ]; then
        echo "  DRIFT: Missing directory: $dir_b"
        DRIFT_FOUND=1
        return
    fi

    # Run recursive diff, excluding __pycache__
    local diff_output
    if diff_output=$(diff -r \
        --exclude=__pycache__ \
        --exclude="*.pyc" \
        "$dir_a" "$dir_b" 2>&1); then
        echo "  OK: No drift detected"
    else
        echo "  DRIFT detected:"
        echo "$diff_output" | sed 's/^/    /'
        DRIFT_FOUND=1
    fi

    echo ""
}

echo "========================================"
echo " Drift Detection Check"
echo "========================================"
echo ""

compare_dirs \
    ".claude/skills vs amplifier-bundle/skills" \
    ".claude/skills" \
    "amplifier-bundle/skills"

compare_dirs \
    ".claude/skills vs docs/claude/skills" \
    ".claude/skills" \
    "docs/claude/skills"

compare_dirs \
    ".claude/agents vs amplifier-bundle/agents" \
    ".claude/agents" \
    "amplifier-bundle/agents"

compare_dirs \
    ".claude/agents vs docs/claude/agents" \
    ".claude/agents" \
    "docs/claude/agents"

echo "========================================"
if [ "$DRIFT_FOUND" -eq 0 ]; then
    echo " Result: PASS — all locations in sync"
    echo "========================================"
    exit 0
else
    echo " Result: FAIL — drift detected (see above)"
    echo " Fix: update all three locations to match"
    echo "========================================"
    exit 1
fi
