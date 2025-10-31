#!/bin/bash
# Manual integration test for TodoWrite tracking in auto mode
#
# This script runs a simple auto mode task that should generate todos
# and verifies they appear in the output.

set -e

echo "🏴‍☠️ Testing TodoWrite tracking in auto mode..."
echo ""

# Create temporary test directory
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

echo "📂 Test directory: $TEST_DIR"
echo ""

# Run auto mode with a simple task that should use TodoWrite
echo "⚓ Running auto mode with task that uses TodoWrite..."
echo ""

# Use a task that will definitely use TodoWrite (multi-step task)
TASK="Create a simple Python hello world script. Use TodoWrite to track your progress."

# Run auto mode (without --ui for easier testing)
timeout 120 amplihack auto --sdk claude --max-turns 3 "$TASK" > /tmp/auto_mode_output.log 2>&1 || true

echo ""
echo "📋 Checking for TodoWrite in output..."
echo ""

# Check if todos appeared in the output
if grep -q "📋 Todo List:" /tmp/auto_mode_output.log; then
    echo "✅ SUCCESS: TodoWrite output detected!"
    echo ""
    echo "Sample todos from output:"
    grep -A 10 "📋 Todo List:" /tmp/auto_mode_output.log | head -15
    exit 0
else
    echo "❌ FAILURE: No TodoWrite output found"
    echo ""
    echo "Output preview:"
    head -50 /tmp/auto_mode_output.log
    echo ""
    echo "Full output saved to: /tmp/auto_mode_output.log"
    exit 1
fi

# Cleanup
rm -rf "$TEST_DIR"
