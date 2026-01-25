#!/bin/bash
# End-to-end test for workflow classification reminder hook
# Tests actual hook invocation as Claude Code would call it

set -e

HOOK_SCRIPT=".claude/tools/amplihack/hooks/workflow_classification_reminder.py"
TEST_DIR="/tmp/workflow_hook_e2e_test"

echo "======================================================================"
echo "E2E TEST: Workflow Classification Reminder Hook"
echo "======================================================================"

# Setup test environment
mkdir -p "$TEST_DIR"
cd "$(dirname "$0")/../../.."  # Go to .claude/ directory root

# Test 1: First turn (new topic)
echo ""
echo "[Test 1] First turn - should inject reminder"
echo '{"userMessage": "Implement user authentication", "turnCount": 0}' | \
    "$HOOK_SCRIPT" > "$TEST_DIR/test1_output.json"

if grep -q "NEW TOPIC DETECTED" "$TEST_DIR/test1_output.json"; then
    echo "✓ PASS: Reminder injected on first turn"
else
    echo "✗ FAIL: No reminder on first turn"
    cat "$TEST_DIR/test1_output.json"
    exit 1
fi

if grep -q "OPERATIONS" "$TEST_DIR/test1_output.json"; then
    echo "✓ PASS: Operations category present in reminder"
else
    echo "✗ FAIL: Operations category missing"
    exit 1
fi

# Test 2: Follow-up (same topic)
echo ""
echo "[Test 2] Follow-up - should NOT inject reminder"
echo '{"userMessage": "Also add password reset", "turnCount": 2}' | \
    "$HOOK_SCRIPT" > "$TEST_DIR/test2_output.json"

if ! grep -q "NEW TOPIC DETECTED" "$TEST_DIR/test2_output.json"; then
    echo "✓ PASS: No reminder on follow-up"
else
    echo "✗ FAIL: Unexpected reminder on follow-up"
    cat "$TEST_DIR/test2_output.json"
    exit 1
fi

# Test 3: Explicit transition (new topic)
echo ""
echo "[Test 3] Explicit transition - should inject reminder"
echo '{"userMessage": "Now lets work on caching", "turnCount": 5}' | \
    "$HOOK_SCRIPT" > "$TEST_DIR/test3_output.json"

if grep -q "NEW TOPIC DETECTED" "$TEST_DIR/test3_output.json"; then
    echo "✓ PASS: Reminder injected on explicit transition"
else
    echo "✗ FAIL: No reminder on explicit transition"
    cat "$TEST_DIR/test3_output.json"
    exit 1
fi

# Test 4: Operations task
echo ""
echo "[Test 4] Operations task - should inject reminder with operations category"
echo '{"userMessage": "Clean up old log files", "turnCount": 10}' | \
    "$HOOK_SCRIPT" > "$TEST_DIR/test4_output.json"

if grep -q "NEW TOPIC DETECTED" "$TEST_DIR/test4_output.json" && \
   grep -q "OPERATIONS" "$TEST_DIR/test4_output.json"; then
    echo "✓ PASS: Operations workflow available"
else
    echo "✗ FAIL: Operations handling incorrect"
    cat "$TEST_DIR/test4_output.json"
    exit 1
fi

# Test 5: Hook returns valid JSON
echo ""
echo "[Test 5] JSON validity - hook output must be valid JSON"
if python3 -c "import json; json.load(open('$TEST_DIR/test1_output.json'))" 2>/dev/null; then
    echo "✓ PASS: Hook returns valid JSON"
else
    echo "✗ FAIL: Hook output is not valid JSON"
    cat "$TEST_DIR/test1_output.json"
    exit 1
fi

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "======================================================================"
echo "SUMMARY: All E2E tests PASSED"
echo "======================================================================"
echo ""
echo "The hook is ready for production use:"
echo "  ✓ Loads correctly and executes"
echo "  ✓ Detects topic boundaries accurately"
echo "  ✓ Injects reminders at appropriate times"
echo "  ✓ Includes Operations workflow category"
echo "  ✓ Returns valid JSON for Claude Code"
echo ""
echo "Next step: Merge PR #2075 to activate in production"
