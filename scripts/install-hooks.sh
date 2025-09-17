#!/bin/bash
# Pre-commit hooks installation script
# This script installs and configures pre-commit hooks for the project

set -e  # Exit on error

# Check for batch mode (non-interactive)
BATCH_MODE=false
if [[ "$1" == "--batch" ]]; then
    BATCH_MODE=true
fi

echo "==================================="
echo "Pre-Commit Hooks Installation"
echo "==================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit framework..."
    pip3 install --user pre-commit
    echo "✓ Pre-commit installed"
else
    echo "✓ Pre-commit already installed ($(pre-commit --version))"
fi

# Install detect-secrets for security scanning
if ! command -v detect-secrets &> /dev/null; then
    echo "Installing detect-secrets for security scanning..."
    pip3 install --user detect-secrets
    echo "✓ detect-secrets installed"
else
    echo "✓ detect-secrets already installed ($(detect-secrets --version 2>&1 | head -1))"
fi

# Install the git hook scripts
echo "Installing git hooks..."
pre-commit install
echo "✓ Git hooks installed"

# Create detect-secrets baseline if it doesn't exist
if [ ! -f .secrets.baseline ]; then
    echo "Creating detect-secrets baseline..."
    detect-secrets scan --baseline .secrets.baseline
    echo "✓ Secrets baseline created"
else
    echo "✓ Secrets baseline already exists"
fi

# Install commit-msg hook for conventional commits (optional)
# pre-commit install --hook-type commit-msg

# Run hooks on all files (optional first-time check)
if [[ "$BATCH_MODE" == "false" ]]; then
    read -p "Run hooks on all existing files? This may take a few minutes [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Running hooks on all files..."
        pre-commit run --all-files || true
        echo "✓ Initial run complete"
    fi
else
    echo "Batch mode: Skipping initial hook run"
fi


echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "Pre-commit hooks are now active. They will run automatically on:"
echo "  git commit"
echo ""
echo "To bypass hooks (use sparingly):"
echo "  git commit --no-verify"
echo ""
echo "To run hooks manually:"
echo "  pre-commit run                 # On staged files"
echo "  pre-commit run --all-files     # On all files"
echo "  pre-commit run <hook-id>       # Specific hook"
echo ""
echo "To skip specific hooks:"
echo "  SKIP=pyright git commit"
echo ""
