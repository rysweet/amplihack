#!/usr/bin/env bash
#Test end-to-end blarify indexing from PR branch

set -e

echo "========================================================================"
echo "End-to-End Blarify Indexing Test"
echo "========================================================================"
echo ""

# Test directory
TEST_DIR="$HOME/.amplihack-e2e-test"
LOG_FILE="/tmp/e2e-blarify-test-$(date +%Y%m%d-%H%M%S).log"

echo "📋 Test Configuration:"
echo "  Branch: feat/issue-2186-fix-blarify-indexing"
echo "  Test dir: $TEST_DIR"
echo "  Log file: $LOG_FILE"
echo ""

# Clean up old test directory
if [ -d "$TEST_DIR" ]; then
    echo "🧹 Cleaning up old test directory..."
    rm -rf "$TEST_DIR"
fi

# Create test directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📦 Installing amplihack from PR branch..."
echo "  Command: uvx --from git+https://github.com/rysweet/amplihack.git@feat/issue-2186-fix-blarify-indexing amplihack"
echo ""

# Install and run amplihack (non-interactive mode with 'Y' for blarify)
echo "Y" | uvx --from "git+https://github.com/rysweet/amplihack.git@feat/issue-2186-fix-blarify-indexing" amplihack install 2>&1 | tee "$LOG_FILE"

echo ""
echo "========================================================================"
echo "Test Complete"
echo "========================================================================"
echo "Log saved to: $LOG_FILE"
echo ""
echo "Checking results..."

# Check for success indicators
if grep -q "✓ Available languages" "$LOG_FILE"; then
    echo "✅ Prerequisite check passed"
else
    echo "❌ Prerequisite check failed"
fi

if grep -q "Starting server" "$LOG_FILE"; then
    echo "✅ Blarify server started"
else
    echo "❌ Blarify server failed to start"
fi

if grep -q "Indexed.*files" "$LOG_FILE"; then
    echo "✅ Files were indexed"
    grep "Indexed.*files" "$LOG_FILE"
else
    echo "❌ No files indexed"
fi

# Check for errors
if grep -q "Blarify execution failed" "$LOG_FILE"; then
    echo "❌ Blarify execution errors detected"
    grep "Blarify execution failed" "$LOG_FILE"
else
    echo "✅ No execution failures detected"
fi

echo ""
echo "Full log available at: $LOG_FILE"
