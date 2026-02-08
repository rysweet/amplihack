#!/bin/bash
# Test runner for blarify indexing enhancement tests
# Usage: ./run_tests.sh [OPTIONS]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Blarify Indexing Enhancement Tests ===${NC}\n"

# Default options
VERBOSE=""
COVERAGE=""
TEST_FILTER=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -c|--coverage)
            COVERAGE="--cov=amplihack.memory.kuzu.indexing --cov-report=html --cov-report=term"
            shift
            ;;
        -f|--filter)
            TEST_FILTER="-k $2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose     Verbose output"
            echo "  -c, --coverage    Generate coverage report"
            echo "  -f, --filter      Filter tests by name"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${YELLOW}Running tests from: ${SCRIPT_DIR}${NC}\n"

# Run pytest
if pytest ${SCRIPT_DIR} ${VERBOSE} ${COVERAGE} ${TEST_FILTER}; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Tests failed (expected for TDD)${NC}"
    echo -e "${YELLOW}These tests are written before implementation.${NC}"
    echo -e "${YELLOW}Implement the modules to make tests pass.${NC}"
    exit 1
fi
