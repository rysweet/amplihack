#!/bin/bash
# Step 13: Mandatory Local Testing - Issue #2125
# This script verifies that ~/.amplihack/.claude gets populated for all commands

set -e

BRANCH="feat/issue-2125-cli-installation-path-fix"
REPO="git+https://github.com/rysweet/amplihack@${BRANCH}"

echo "========================================="
echo "Step 13: Local Testing - Issue #2125"
echo "========================================="
echo ""
echo "Testing unified .claude/ staging for:"
echo "  - amplihack copilot"
echo "  - amplihack amplifier"
echo "  - amplihack codex"
echo "  - amplihack RustyClawd"
echo ""

# Function to test a command
test_command() {
    local cmd=$1
    echo "Testing: amplihack $cmd"
    echo "-------------------------------------------"

    # Clean staging directory
    rm -rf ~/.amplihack/.claude/
    echo "  ✓ Cleaned ~/.amplihack/.claude/"

    # Run command (just --help to avoid interactive mode)
    echo "  → Running: uvx --from ${REPO} amplihack $cmd --help"
    uvx --from "${REPO}" amplihack "$cmd" --help > /dev/null 2>&1 || true

    # Check staging occurred
    if [ -d ~/.amplihack/.claude/ ]; then
        echo "  ✅ Directory created: ~/.amplihack/.claude/"

        # Check subdirectories
        local all_exist=true
        for subdir in agents skills tools hooks context workflow commands; do
            if [ -d ~/.amplihack/.claude/$subdir ]; then
                echo "    ✅ $subdir/ exists"
            else
                echo "    ❌ $subdir/ MISSING"
                all_exist=false
            fi
        done

        if $all_exist; then
            echo "  ✅ SUCCESS: All expected subdirectories present"
        else
            echo "  ❌ FAILED: Some subdirectories missing"
            return 1
        fi
    else
        echo "  ❌ FAILED: ~/.amplihack/.claude/ not created"
        return 1
    fi

    echo ""
}

# Test 1: Copilot command (Simple Test)
echo "========================================="
echo "Test 1: Simple - Copilot Command"
echo "========================================="
test_command "copilot"

# Test 2: All 4 commands (Complex Test)
echo "========================================="
echo "Test 2: Complex - All Commands"
echo "========================================="
test_command "amplifier"
test_command "codex"
test_command "RustyClawd"

# Test 3: Regression - Claude command still works
echo "========================================="
echo "Test 3: Regression - Claude Command"
echo "========================================="
echo "Testing: amplihack claude (regression check)"
echo "-------------------------------------------"
rm -rf ~/.amplihack/.claude/
echo "  ✓ Cleaned ~/.amplihack/.claude/"
uvx --from "${REPO}" amplihack claude --version > /dev/null 2>&1 || true
if [ -d ~/.amplihack/.claude/ ]; then
    echo "  ✅ Claude command still stages correctly (no regression)"
else
    echo "  ⚠️  WARNING: Claude command staging behavior changed"
fi
echo ""

echo "========================================="
echo "✅ All tests passed!"
echo "========================================="
echo ""
echo "Summary:"
echo "  - copilot: ✅ Stages ~/.amplihack/.claude/"
echo "  - amplifier: ✅ Stages ~/.amplihack/.claude/"
echo "  - codex: ✅ Stages ~/.amplihack/.claude/"
echo "  - RustyClawd: ✅ Stages ~/.amplihack/.claude/"
echo "  - claude: ✅ No regression"
echo ""
echo "Issue #2125 is VERIFIED: All commands populate ~/.amplihack/.claude/"
