#!/bin/bash
# Test runner for Issue #2353 workflow tests
# Runs tests in TDD order: verify RED phase, then track progress to GREEN

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "============================================"
echo "Issue #2353 Workflow Tests - TDD Runner"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run test category
run_test_category() {
    local category=$1
    local marker=$2
    local description=$3

    echo ""
    echo "=========================================="
    echo "${description}"
    echo "=========================================="

    if [ -n "$marker" ]; then
        pytest "${SCRIPT_DIR}" -m "${marker}" -v --tb=short || true
    else
        pytest "${SCRIPT_DIR}/${category}" -v --tb=short || true
    fi
}

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest not found. Please install: pip install pytest pytest-mock${NC}"
    exit 1
fi

echo "Test Location: ${SCRIPT_DIR}"
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# Parse command line arguments
MODE="${1:-all}"

case "$MODE" in
    "red")
        echo -e "${YELLOW}Running TDD RED Phase Check${NC}"
        echo "Verifying all tests fail (no implementation exists)"
        echo ""
        run_test_category "test_classifier.py" "" "Unit Tests: Classifier"
        run_test_category "test_execution_tier_cascade.py" "" "Unit Tests: Execution Tier Cascade"
        run_test_category "test_session_start_integration.py" "" "Integration Tests: Session Start"
        ;;

    "unit")
        echo -e "${YELLOW}Running Unit Tests (60% of pyramid)${NC}"
        run_test_category "" "unit" "Unit Tests"
        ;;

    "integration")
        echo -e "${YELLOW}Running Integration Tests (30% of pyramid)${NC}"
        run_test_category "" "integration" "Integration Tests"
        ;;

    "e2e")
        echo -e "${YELLOW}Running E2E Tests (10% of pyramid)${NC}"
        run_test_category "" "e2e" "E2E Tests"
        ;;

    "performance")
        echo -e "${YELLOW}Running Performance Tests${NC}"
        run_test_category "" "performance" "Performance Tests"
        ;;

    "acceptance")
        echo -e "${YELLOW}Running Acceptance Criteria Tests (6 Scenarios)${NC}"
        run_test_category "test_e2e_acceptance_criteria.py" "" "Acceptance Criteria"
        ;;

    "scenario1")
        echo -e "${YELLOW}Scenario 1: Session Start with Recipe Runner Available${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario1" -v
        ;;

    "scenario2")
        echo -e "${YELLOW}Scenario 2: Session Start without Recipe Runner${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario2" -v
        ;;

    "scenario3")
        echo -e "${YELLOW}Scenario 3: Q&A Request${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario3" -v
        ;;

    "scenario4")
        echo -e "${YELLOW}Scenario 4: Explicit Command${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario4" -v
        ;;

    "scenario5")
        echo -e "${YELLOW}Scenario 5: Recipe Runner Disabled${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario5" -v
        ;;

    "scenario6")
        echo -e "${YELLOW}Scenario 6: Recipe Runner Failure${NC}"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py::TestAcceptanceCriteriaScenario6" -v
        ;;

    "regression")
        echo -e "${YELLOW}Running Regression Tests (NFR1: Backward Compatibility)${NC}"
        run_test_category "test_regression.py" "" "Regression Tests"
        ;;

    "coverage")
        echo -e "${YELLOW}Running with Coverage Report${NC}"
        pytest "${SCRIPT_DIR}" \
            --cov=amplihack.workflows \
            --cov-report=html \
            --cov-report=term \
            --cov-report=term-missing \
            -v
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    "fast")
        echo -e "${YELLOW}Running Fast Tests Only (exclude slow/performance)${NC}"
        pytest "${SCRIPT_DIR}" -v -m "not slow and not performance"
        ;;

    "all")
        echo -e "${YELLOW}Running All Tests${NC}"
        echo ""

        # Run in order: Unit -> Integration -> E2E
        run_test_category "test_classifier.py" "" "1. Unit: Classifier (40 tests)"
        run_test_category "test_execution_tier_cascade.py" "" "2. Unit: Execution Cascade (35 tests)"
        run_test_category "test_session_start_integration.py" "" "3. Integration: Session Start (30 tests)"
        run_test_category "test_e2e_acceptance_criteria.py" "" "4. E2E: Acceptance Criteria (18 tests)"
        run_test_category "test_performance.py" "" "5. Performance Tests (20 tests)"
        run_test_category "test_regression.py" "" "6. Regression Tests (25 tests)"

        echo ""
        echo "=========================================="
        echo "Test Summary"
        echo "=========================================="
        pytest "${SCRIPT_DIR}" --collect-only -q
        ;;

    "count")
        echo -e "${YELLOW}Counting Tests${NC}"
        echo ""
        echo "Unit Tests (test_classifier.py):"
        pytest "${SCRIPT_DIR}/test_classifier.py" --collect-only -q | tail -1
        echo ""
        echo "Unit Tests (test_execution_tier_cascade.py):"
        pytest "${SCRIPT_DIR}/test_execution_tier_cascade.py" --collect-only -q | tail -1
        echo ""
        echo "Integration Tests (test_session_start_integration.py):"
        pytest "${SCRIPT_DIR}/test_session_start_integration.py" --collect-only -q | tail -1
        echo ""
        echo "E2E Tests (test_e2e_acceptance_criteria.py):"
        pytest "${SCRIPT_DIR}/test_e2e_acceptance_criteria.py" --collect-only -q | tail -1
        echo ""
        echo "Performance Tests (test_performance.py):"
        pytest "${SCRIPT_DIR}/test_performance.py" --collect-only -q | tail -1
        echo ""
        echo "Regression Tests (test_regression.py):"
        pytest "${SCRIPT_DIR}/test_regression.py" --collect-only -q | tail -1
        echo ""
        echo "Total Tests:"
        pytest "${SCRIPT_DIR}" --collect-only -q | tail -1
        ;;

    "help"|*)
        echo "Usage: $0 [MODE]"
        echo ""
        echo "Modes:"
        echo "  red          - Verify TDD RED phase (all tests fail)"
        echo "  unit         - Run unit tests only (60% of pyramid)"
        echo "  integration  - Run integration tests only (30% of pyramid)"
        echo "  e2e          - Run E2E tests only (10% of pyramid)"
        echo "  performance  - Run performance tests (NFR2: <5s)"
        echo "  regression   - Run regression tests (NFR1: backward compat)"
        echo "  acceptance   - Run all 6 acceptance criteria scenarios"
        echo "  scenario1-6  - Run specific acceptance scenario"
        echo "  coverage     - Run with coverage report"
        echo "  fast         - Run fast tests only (exclude slow/performance)"
        echo "  all          - Run all tests (default)"
        echo "  count        - Count tests in each category"
        echo "  help         - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 red                    # Verify TDD RED phase"
        echo "  $0 unit                   # Run unit tests"
        echo "  $0 scenario1              # Run Scenario 1 only"
        echo "  $0 coverage               # Generate coverage report"
        echo ""
        exit 0
        ;;
esac

echo ""
echo "============================================"
echo "Test run complete"
echo "============================================"
