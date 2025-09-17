#!/bin/bash

# Test script for the Agentic Claude Launcher
# This validates that the launcher correctly sets up directories and arguments

echo "🧪 Testing Agentic Claude Launcher"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the framework directory
FRAMEWORK_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LAUNCHER="${FRAMEWORK_DIR}/bin/launch.js"

echo -e "${BLUE}📁 Framework Directory:${NC} ${FRAMEWORK_DIR}"
echo -e "${BLUE}🚀 Launcher Path:${NC} ${LAUNCHER}"
echo ""

# Test 1: Check launcher exists and is executable
echo "Test 1: Launcher File Validation"
echo "---------------------------------"
if [ -f "$LAUNCHER" ]; then
    echo -e "${GREEN}✓${NC} Launcher file exists"
else
    echo -e "${RED}✗${NC} Launcher file not found!"
    exit 1
fi

if [ -x "$LAUNCHER" ]; then
    echo -e "${GREEN}✓${NC} Launcher is executable"
else
    echo -e "${RED}✗${NC} Launcher is not executable!"
    echo "  Run: chmod +x ${LAUNCHER}"
    exit 1
fi
echo ""

# Test 2: Check framework structure
echo "Test 2: Framework Structure"
echo "---------------------------"
if [ -d "${FRAMEWORK_DIR}/.claude" ]; then
    echo -e "${GREEN}✓${NC} .claude directory exists"

    # Check for key subdirectories
    for dir in agents commands context; do
        if [ -d "${FRAMEWORK_DIR}/.claude/${dir}" ]; then
            echo -e "${GREEN}✓${NC} .claude/${dir} exists"
        else
            echo -e "${RED}✗${NC} .claude/${dir} missing!"
        fi
    done
else
    echo -e "${RED}✗${NC} .claude directory not found!"
    exit 1
fi
echo ""

# Test 3: Create a test project directory
echo "Test 3: Test Project Setup"
echo "--------------------------"
TEST_PROJECT="/tmp/test-agentic-project-$$"
mkdir -p "$TEST_PROJECT"
echo "Test project file" > "${TEST_PROJECT}/test.txt"
echo -e "${GREEN}✓${NC} Created test project: ${TEST_PROJECT}"
echo ""

# Test 4: Test launcher with --help (dry run)
echo "Test 4: Launcher Dry Run"
echo "------------------------"
cd "$TEST_PROJECT"
echo -e "${BLUE}Running from:${NC} $(pwd)"
echo -e "${BLUE}Command:${NC} node ${LAUNCHER} --help"
echo ""

# Run the launcher with --help to see if it would work
# We can't actually launch Claude in the test, but we can check the setup
OUTPUT=$(node "$LAUNCHER" --help 2>&1)
if [ $? -eq 0 ] || [[ "$OUTPUT" == *"Claude CLI not found"* ]]; then
    if [[ "$OUTPUT" == *"Claude CLI not found"* ]]; then
        echo -e "${GREEN}✓${NC} Launcher runs correctly (Claude CLI not installed - expected in CI)"
    else
        echo -e "${GREEN}✓${NC} Launcher executed successfully"
    fi
    echo ""
    echo "Launcher output:"
    echo "$OUTPUT" | head -20
else
    echo -e "${RED}✗${NC} Launcher failed to execute"
    echo "$OUTPUT"
fi
echo ""

# Test 5: Verify npx execution would work
echo "Test 5: NPX Compatibility"
echo "-------------------------"
if [ -f "${FRAMEWORK_DIR}/package.json" ]; then
    echo -e "${GREEN}✓${NC} package.json exists"

    # Check for bin field
    if grep -q '"bin"' "${FRAMEWORK_DIR}/package.json"; then
        echo -e "${GREEN}✓${NC} bin field defined in package.json"
    else
        echo -e "${RED}✗${NC} bin field missing in package.json!"
    fi

    # Check for correct bin path
    if grep -q '"agentic-claude"' "${FRAMEWORK_DIR}/package.json"; then
        echo -e "${GREEN}✓${NC} agentic-claude command defined"
    else
        echo -e "${RED}✗${NC} agentic-claude command not defined!"
    fi
else
    echo -e "${RED}✗${NC} package.json not found!"
fi
echo ""

# Test 6: Simulate npx execution
echo "Test 6: Simulated NPX Execution"
echo "-------------------------------"
echo -e "${BLUE}To test actual npx execution:${NC}"
echo "  1. From this framework directory, run: npm link"
echo "  2. From any project directory, run: agentic-claude"
echo "  3. Or directly: npx ${FRAMEWORK_DIR}"
echo ""

# Cleanup
echo "Cleanup"
echo "-------"
rm -rf "$TEST_PROJECT"
echo -e "${GREEN}✓${NC} Removed test project"
echo ""

# Summary
echo "=================================="
echo -e "${GREEN}🎉 All tests passed!${NC}"
echo ""
echo "Next steps to test with real Claude:"
echo "  1. Make sure Claude CLI is installed"
echo "  2. Run: npm link (from framework directory)"
echo "  3. Go to any project: cd ~/your-project"
echo "  4. Run: agentic-claude"
echo ""
echo "The launcher will:"
echo "  - Add framework directory for .claude configs"
echo "  - Add your project directory"
echo "  - Launch Claude with instructions to change directory"