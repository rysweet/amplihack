#!/bin/bash
# Setup script for Claude Code plugin testing
# This script prepares the environment for gadugi-agentic-test TUI testing

set -e

PLUGIN_BRANCH="${PLUGIN_BRANCH:-feat/issue-1948-plugin-architecture}"
GITHUB_REPO="${GITHUB_REPO:-git+https://github.com/rysweet/amplihack}"

echo "🏴‍☠️ Setting up Claude Code plugin test environment..."

# Step 1: Clean any existing installation
echo "🧹 Cleaning previous amplihack installation..."
rm -rf ~/.amplihack || true

# Step 2: Install amplihack from feature branch
echo "📦 Installing amplihack from branch: ${PLUGIN_BRANCH}..."
uvx --refresh --from "${GITHUB_REPO}@${PLUGIN_BRANCH}" amplihack --help

# Step 3: Verify installation
echo "✅ Verifying plugin installation..."

if [ ! -f ~/.amplihack/.claude/AMPLIHACK.md ]; then
    echo "❌ ERROR: AMPLIHACK.md not found in ~/.amplihack/.claude/"
    exit 1
fi

SKILL_COUNT=$(find ~/.amplihack/.claude/skills -maxdepth 1 -type d 2>/dev/null | wc -l)
echo "📚 Found ${SKILL_COUNT} skills deployed"

if [ "$SKILL_COUNT" -lt 80 ]; then
    echo "⚠️  WARNING: Expected ~83 skills, found only ${SKILL_COUNT}"
fi

# Step 4: Create test directory
TEST_DIR="/tmp/test_plugin_$(date +%s)"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "✅ Setup complete!"
echo "📁 Test directory: $TEST_DIR"
echo "🔌 Plugin directory: ~/.amplihack/.claude/"
echo ""
echo "Ready to run gadugi-agentic-test!"
echo "Run: gadugi-agentic-test run tests/agentic/test-claude-code-plugin-installation.yaml"
