#!/bin/bash
# Test runner for native binary trace logging tests
# All tests should FAIL until implementation is complete (TDD approach)

set -e

echo "================================"
echo "Native Binary Trace Logging Tests"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Warning: pytest not found. Install with: pip install pytest pytest-asyncio${NC}"
    echo ""
    echo "Install command:"
    echo "  pip install pytest pytest-asyncio pytest-cov"
    exit 1
fi

echo "Test Suite Status: Expected to FAIL (TDD - Implementation Not Complete)"
echo ""

# Function to run test category
run_tests() {
    local name=$1
    local path=$2
    local marker=$3

    echo -e "${YELLOW}Running $name...${NC}"

    if [ -z "$marker" ]; then
        pytest "$path" -v --tb=short 2>&1 | head -50 || true
    else
        pytest "$path" -v -m "$marker" --tb=short 2>&1 | head -50 || true
    fi

    echo ""
}

# Test execution order (fastest to slowest)
echo "1. Unit Tests (Expected: ~103 failures)"
echo "----------------------------------------"
run_tests "TraceLogger Unit Tests" "tests/tracing/test_trace_logger.py"
run_tests "BinaryManager Unit Tests" "tests/tracing/test_binary_manager.py"
run_tests "LiteLLM Callbacks Unit Tests" "tests/tracing/test_litellm_callbacks.py"

echo ""
echo "2. Integration Tests (Expected: ~37 failures)"
echo "----------------------------------------------"
run_tests "Integration Tests" "tests/tracing/test_integration.py"
run_tests "Prerequisites Integration Tests" "tests/tracing/test_prerequisites_integration.py"

echo ""
echo "3. E2E Tests (Expected: ~16 failures)"
echo "--------------------------------------"
run_tests "E2E Tests" "tests/tracing/test_e2e.py"

echo ""
echo "================================"
echo "Test Summary"
echo "================================"
echo ""
echo "Total Expected: 156 tests"
echo "Status: All FAILING (Expected for TDD)"
echo ""
echo "Next Steps:"
echo "1. Implement src/amplihack/tracing/trace_logger.py"
echo "2. Implement src/amplihack/launcher/claude_binary_manager.py"
echo "3. Implement src/amplihack/proxy/litellm_callbacks.py"
echo "4. Update src/amplihack/launcher/core.py"
echo "5. Update src/amplihack/utils/prerequisites.py"
echo ""
echo "Run specific categories:"
echo "  pytest tests/tracing/test_trace_logger.py -v"
echo "  pytest tests/tracing/ -m integration -v"
echo "  pytest tests/tracing/ -m e2e -v"
echo "  pytest tests/tracing/ -m performance -v"
echo ""
echo "Generate coverage report:"
echo "  pytest tests/tracing/ --cov=amplihack.tracing --cov-report=html"
echo ""
