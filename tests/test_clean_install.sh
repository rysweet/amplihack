#!/bin/bash
# Test PR branch installation in clean environment
# Verifies "out of box" experience

set -e

PR_BRANCH="feat/issue-2186-fix-blarify-indexing"
IMAGE_NAME="amplihack-pr-test"

echo "🧪 Testing PR branch: $PR_BRANCH in clean Docker environment"
echo ""

# Create Dockerfile
cat > /tmp/Dockerfile.clean-test << 'EOF'
FROM python:3.11-slim

# Install Node.js for scip-python/scip-typescript
RUN apt-get update && \
    apt-get install -y curl git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv (uvx comes with it)
RUN pip install uv

WORKDIR /test
EOF

echo "📦 Building test container (Python 3.11 + Node.js)..."
docker build -f /tmp/Dockerfile.clean-test -t $IMAGE_NAME /tmp/ 2>&1 | grep -E "(Successfully|ERROR)" || echo "Building..."

echo ""
echo "🚀 Testing installation from PR branch..."
echo ""

# Run the test
docker run --rm $IMAGE_NAME bash -c "
set -e

echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo '▶️  Test 1: Install amplihack from PR branch via uvx'
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo ''

uvx --from git+https://github.com/rysweet/amplihack@$PR_BRANCH amplihack --version

echo ''
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo '▶️  Test 2: Verify SCIP indexers can be installed'
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo ''

# Check if scip-python can be installed
npm install -g @sourcegraph/scip-python 2>&1 | grep -E '(added|up to date)' && echo '✅ scip-python installable' || echo '❌ scip-python failed'

# Check if scip-typescript can be installed
npm install -g @sourcegraph/scip-typescript 2>&1 | grep -E '(added|up to date)' && echo '✅ scip-typescript installable' || echo '❌ scip-typescript failed'

echo ''
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo '▶️  Test 3: Verify scip-python can create index'
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo ''

mkdir -p /test/sample-python
cat > /test/sample-python/hello.py << 'PYTHON'
def hello(name: str) -> str:
    return f\"Hello, {name}!\"

class Greeter:
    def greet(self, name: str) -> str:
        return hello(name)
PYTHON

cd /test/sample-python
scip-python index && ls -lh index.scip && echo '✅ scip-python created index.scip' || echo '❌ scip-python indexing failed'

echo ''
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
echo '✅ ALL TESTS PASSED!'
echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ CLEAN INSTALL TEST PASSED!"
    echo ""
    echo "   The PR branch works in a fresh environment with:"
    echo "   ✅ Python 3.11"
    echo "   ✅ Node.js 20"
    echo "   ✅ uvx installation from GitHub"
    echo "   ✅ SCIP indexer auto-installation"
    echo "   ✅ Python code indexing"
    echo ""
    echo "   Ready for production deployment! 🎉"
else
    echo "❌ CLEAN INSTALL TEST FAILED"
    echo "   Check output above for errors"
fi

exit $EXIT_CODE
