#!/bin/bash
# Convenience script for running beads integration tests
# Usage: ./run_beads_tests.sh [phase|all|coverage]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "Beads Integration Test Runner"
echo "=========================================="
echo ""

case "${1:-all}" in
    verify)
        echo -e "${YELLOW}Verifying TDD setup...${NC}"
        python tests/verify_beads_tests_fail.py
        ;;

    models|phase1)
        echo -e "${YELLOW}Running Phase 1: Models tests...${NC}"
        pytest tests/unit/memory/test_beads_models.py -v
        ;;

    adapter|phase2)
        echo -e "${YELLOW}Running Phase 2: Adapter tests...${NC}"
        pytest tests/unit/memory/test_beads_adapter.py -v
        ;;

    sync|phase3)
        echo -e "${YELLOW}Running Phase 3: Sync tests...${NC}"
        pytest tests/unit/memory/test_beads_sync.py -v
        ;;

    provider|phase4)
        echo -e "${YELLOW}Running Phase 4: Provider tests...${NC}"
        pytest tests/unit/memory/test_beads_provider.py -v
        ;;

    integration|phase5)
        echo -e "${YELLOW}Running Phase 5: Integration tests...${NC}"
        pytest tests/integration/test_beads_*.py -v
        ;;

    e2e|phase6)
        echo -e "${YELLOW}Running Phase 6: E2E tests...${NC}"
        pytest tests/e2e/test_beads_*.py -v -m e2e
        ;;

    unit)
        echo -e "${YELLOW}Running all unit tests...${NC}"
        pytest tests/unit/memory/test_beads_*.py -v
        ;;

    integration-only)
        echo -e "${YELLOW}Running all integration tests...${NC}"
        pytest tests/integration/test_beads_*.py -v
        ;;

    e2e-only)
        echo -e "${YELLOW}Running all E2E tests...${NC}"
        pytest tests/e2e/test_beads_*.py -v -m e2e
        ;;

    all)
        echo -e "${YELLOW}Running all beads tests...${NC}"
        pytest tests/unit/memory/test_beads_*.py \
               tests/integration/test_beads_*.py \
               tests/e2e/test_beads_*.py \
               -v
        ;;

    fast)
        echo -e "${YELLOW}Running fast tests (no E2E, no slow)...${NC}"
        pytest tests/unit/memory/test_beads_*.py \
               tests/integration/test_beads_*.py \
               -v -m "not slow and not e2e"
        ;;

    coverage)
        echo -e "${YELLOW}Running tests with coverage report...${NC}"
        pytest tests/unit/memory/test_beads_*.py \
               tests/integration/test_beads_*.py \
               --cov=amplihack.memory \
               --cov-report=html \
               --cov-report=term-missing \
               -v
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;

    count)
        echo -e "${YELLOW}Counting test functions...${NC}"
        echo ""
        echo "Unit tests:"
        grep -E "^def test_" tests/unit/memory/test_beads_*.py | wc -l
        echo "Integration tests:"
        grep -E "^def test_" tests/integration/test_beads_*.py | wc -l
        echo "E2E tests:"
        grep -E "^def test_" tests/e2e/test_beads_*.py | wc -l
        echo ""
        echo "Total test functions:"
        grep -E "^def test_" tests/unit/memory/test_beads_*.py \
                              tests/integration/test_beads_*.py \
                              tests/e2e/test_beads_*.py | wc -l
        ;;

    help|--help|-h)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  verify          - Verify TDD setup (tests should fail)"
        echo "  models, phase1  - Run Phase 1: Models tests"
        echo "  adapter, phase2 - Run Phase 2: Adapter tests"
        echo "  sync, phase3    - Run Phase 3: Sync tests"
        echo "  provider, phase4- Run Phase 4: Provider tests"
        echo "  integration, phase5 - Run Phase 5: Integration tests"
        echo "  e2e, phase6     - Run Phase 6: E2E tests"
        echo "  unit            - Run all unit tests"
        echo "  integration-only- Run all integration tests"
        echo "  e2e-only        - Run all E2E tests"
        echo "  all             - Run all beads tests (default)"
        echo "  fast            - Run tests without slow/E2E tests"
        echo "  coverage        - Run with coverage report"
        echo "  count           - Count test functions"
        echo "  help            - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 verify       # Verify TDD setup"
        echo "  $0 phase1       # Run models tests"
        echo "  $0 fast         # Run fast tests"
        echo "  $0 coverage     # Generate coverage report"
        echo ""
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ Tests completed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
fi
echo ""

exit $exit_code
