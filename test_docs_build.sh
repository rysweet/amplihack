#!/bin/bash
# Test script to verify documentation build success

set -e

echo "🧪 Documentation Build Test Suite"
echo "=================================="

# Test 1: Check mkdocs is available
echo "Test 1: Checking mkdocs availability..."
if command -v mkdocs &> /dev/null; then
    echo "✅ mkdocs found: $(mkdocs --version)"
else
    echo "❌ mkdocs not found - installing from requirements-docs.txt"
    pip install -r requirements-docs.txt
fi

# Test 2: Validate mkdocs.yml syntax
echo ""
echo "Test 2: Validating mkdocs.yml syntax..."
python -c "import yaml; yaml.safe_load(open('mkdocs.yml'))" && echo "✅ mkdocs.yml syntax valid"

# Test 3: Build docs without strict mode
echo ""
echo "Test 3: Building docs (non-strict mode)..."
mkdocs build --clean && echo "✅ Build succeeded (non-strict)"

# Test 4: Build docs with strict mode (fail on warnings)
echo ""
echo "Test 4: Building docs (STRICT mode - zero warnings required)..."
if mkdocs build --strict --clean 2>&1; then
    echo "✅ Build succeeded with zero warnings!"
    exit 0
else
    echo "❌ Build failed with warnings"
    echo ""
    echo "Run 'mkdocs build --strict 2>&1 | tee build-errors.log' to see all warnings"
    exit 1
fi
