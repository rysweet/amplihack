#!/bin/bash
# Pre-commit hooks uninstall script

set -e

echo "==================================="
echo "Pre-Commit Hooks Uninstallation"
echo "==================================="

# Uninstall git hooks
if command -v pre-commit &> /dev/null; then
    echo "Removing git hooks..."
    pre-commit uninstall
    echo "✓ Git hooks removed"
else
    echo "Pre-commit not found, skipping hook removal"
fi

# Optionally remove pre-commit package
read -p "Also uninstall pre-commit package? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 uninstall -y pre-commit
    echo "✓ Pre-commit package removed"
fi

echo ""
echo "==================================="
echo "Uninstallation Complete!"
echo "==================================="
echo ""
echo "Pre-commit hooks have been removed."
echo "Configuration files are preserved for future use."
