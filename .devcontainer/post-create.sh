#!/usr/bin/env bash
set -euo pipefail

# Log file for debugging post-create issues
LOG_FILE="/tmp/devcontainer-post-create.log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================="
echo "Post-create script starting at $(date)"
echo "========================================="

# Expected versions (aligned with CI configuration in .github/workflows/ci.yml)
EXPECTED_PYTHON_MAJOR_MINOR="3.12"
EXPECTED_NODE_MAJOR="20"

echo ""
echo "Step 1: Upgrading pip to latest..."
python3 -m pip install --upgrade pip --quiet
echo "    pip upgraded to: $(pip --version | cut -d' ' -f2)"

echo ""
echo "Step 2: Installing uv via official installer..."
# Use official astral.sh installer for latest uv (more reliable than pipx)
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    echo "    uv installed: $(uv --version 2>&1)"
else
    echo "    uv already installed: $(uv --version 2>&1)"
    # Upgrade uv if already installed
    uv self update 2>/dev/null || true
fi

echo ""
echo "Step 3: Configuring Git..."
git config --global push.autoSetupRemote true
echo "    Git configured for auto-upstream on push"

echo ""
echo "Step 4: Setting up pnpm global bin directory..."
# Ensure SHELL is set for pnpm setup
export SHELL="${SHELL:-/bin/bash}"
# Configure pnpm to use a global bin directory
pnpm setup 2>&1 | grep -v "^$" || true
# Export for current session (will also be in ~/.bashrc for future sessions)
export PNPM_HOME="/home/vscode/.local/share/pnpm"
export PATH="$PNPM_HOME:$PATH"
echo "    pnpm configured"

echo ""
echo "========================================="
echo "Version Verification"
echo "========================================="

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1,2)
if [[ "$PYTHON_MAJOR_MINOR" == "$EXPECTED_PYTHON_MAJOR_MINOR" ]]; then
    echo "✅ Python: $PYTHON_VERSION (expected $EXPECTED_PYTHON_MAJOR_MINOR.x)"
else
    echo "⚠️  Python: $PYTHON_VERSION (expected $EXPECTED_PYTHON_MAJOR_MINOR.x)"
fi

# Verify Node.js version
NODE_VERSION=$(node --version | tr -d 'v')
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d'.' -f1)
if [[ "$NODE_MAJOR" == "$EXPECTED_NODE_MAJOR" ]]; then
    echo "✅ Node.js: v$NODE_VERSION (expected v$EXPECTED_NODE_MAJOR.x)"
else
    echo "⚠️  Node.js: v$NODE_VERSION (expected v$EXPECTED_NODE_MAJOR.x)"
fi

# Display all tool versions
echo "  • pip: $(pip --version | cut -d' ' -f2)"
echo "  • uv: $(uv --version 2>&1 | head -1)"
echo "  • npm: $(npm --version)"
echo "  • pnpm: $(pnpm --version)"
echo "  • Git: $(git --version | cut -d' ' -f3)"
echo "  • Make: $(make --version 2>&1 | head -n 1 | cut -d' ' -f3)"
echo "  • Claude CLI: $(claude --version 2>&1 || echo 'NOT INSTALLED')"

echo ""
echo "========================================="
echo "Post-create tasks complete at $(date)"
echo "========================================="
echo ""
echo "Logs saved to: $LOG_FILE"
echo ""
