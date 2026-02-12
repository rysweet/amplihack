#!/bin/bash
# Outside-in tests for Copilot CLI extensibility parity (issue #2241)
# These tests verify that workflows, context, and commands are discoverable
# from a bare repo with NO .claude/ or .github/ directory.
#
# Usage: bash tests/launcher/test_copilot_parity.sh
# Requires: copilot CLI installed, authenticated

set -euo pipefail

PASS=0
FAIL=0
TEST_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

cd "$TEST_DIR"
git init -q

run_test() {
    local name="$1"
    local prompt="$2"
    local expected="$3"

    echo -n "TEST: $name ... "
    output=$(copilot -p "$prompt" --model claude-sonnet-4.5 --add-dir "$HOME" 2>&1) || true

    if echo "$output" | grep -qi "$expected"; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        echo "  Expected to find: $expected"
        echo "  Got: $(echo "$output" | head -5)"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Copilot CLI Extensibility Parity Tests ==="
echo "Test directory: $TEST_DIR (bare repo, no .claude/)"
echo ""

# Test 1: Workflow discovery
run_test "Workflow discovery" \
    "Read the file at ~/.copilot/workflow/DEFAULT_WORKFLOW.md and tell me how many steps it has. Just say the number." \
    "23\|22\|step"

# Test 2: Context/Philosophy discovery
run_test "Philosophy context" \
    "Read the file at ~/.copilot/context/PHILOSOPHY.md and quote the first principle heading exactly." \
    "simplicity\|Simplicity\|SIMPLICITY"

# Test 3: Command discovery
run_test "Command awareness" \
    "Read the file at ~/.copilot/commands/ultrathink.md and tell me in one sentence what it does." \
    "workflow\|orchestrat\|analysis"

# Test 4: Copilot instructions exist
run_test "Global instructions" \
    "Do you have access to amplihack workflows and context? Answer yes or no." \
    "yes\|Yes\|YES"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
