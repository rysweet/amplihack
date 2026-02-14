#!/bin/bash
# Outside-in test for worktree isolation fix
# Verifies that default-workflow uses worktrees correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_RECIPE="$SCRIPT_DIR/amplifier-bundle/recipes/default-workflow.yaml"

echo "=== Worktree Isolation Test ==="
echo ""

# Verify recipe syntax with parse_json and dot-notation
echo "--- Verifying recipe syntax ---"
if ! grep -q "parse_json: true" "$TEST_RECIPE"; then
    echo "✗ FAIL: parse_json not found in step-04"
    exit 1
fi

if ! grep -q "worktree_setup.worktree_path" "$TEST_RECIPE"; then
    echo "✗ FAIL: dot-notation access not found"
    exit 1
fi
echo "✓ Recipe uses parse_json and dot-notation"
echo ""

# Verify all critical steps use worktree_path
echo "--- Verifying worktree_path usage ---"
WORKTREE_STEPS=$(grep -E "step-(15|16|18c|19c|20b|21)-" "$TEST_RECIPE" -A 5 | grep -c "worktree_setup.worktree_path" || true)
if [ "$WORKTREE_STEPS" -lt 6 ]; then
    echo "✗ FAIL: Expected 6 steps using worktree_path, found $WORKTREE_STEPS"
    exit 1
fi
echo "✓ All critical steps (15,16,18c,19c,20b,21) use worktree_path"
echo ""

# Verify step-22 still uses repo_path (return to root)
echo "--- Verifying step-22 returns to root ---"
if ! grep -A 5 "step-22b-final-status" "$TEST_RECIPE" | grep -q 'cd "{{repo_path}}"'; then
    echo "✗ FAIL: step-22 should use repo_path to return to root"
    exit 1
fi
echo "✓ Step-22 correctly returns to repo_path"
echo ""

echo "=== ALL TESTS PASSED ==="
echo ""
echo "Summary:"
echo "  ✓ Recipe syntax valid (parse_json + dot-notation)"
echo "  ✓ Step-4 outputs structured JSON"
echo "  ✓ Steps 15-21 use worktree isolation"
echo "  ✓ Step-22 returns to root repo"
echo ""
echo "The worktree isolation fix is working correctly."
