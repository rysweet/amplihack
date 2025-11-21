#!/bin/bash
# Convenience script for running PM tests

set -e

PM_TEST_DIR=".claude/tools/amplihack/pm/tests"

echo "PM Architect Phase 1 - Test Runner"
echo "===================================="
echo ""

case "${1:-all}" in
    all)
        echo "Running all tests..."
        pytest "$PM_TEST_DIR" -v
        ;;
    state)
        echo "Running state management tests..."
        pytest "$PM_TEST_DIR/test_pm_state.py" -v
        ;;
    workstream)
        echo "Running workstream tests..."
        pytest "$PM_TEST_DIR/test_pm_workstream.py" -v
        ;;
    cli)
        echo "Running CLI tests..."
        pytest "$PM_TEST_DIR/test_pm_cli.py" -v
        ;;
    workflow)
        echo "Running integration workflow tests..."
        pytest "$PM_TEST_DIR/test_pm_workflow.py" -v
        ;;
    unit)
        echo "Running unit tests only..."
        pytest "$PM_TEST_DIR" -m unit -v
        ;;
    integration)
        echo "Running integration tests only..."
        pytest "$PM_TEST_DIR" -m integration -v
        ;;
    coverage)
        echo "Running tests with coverage..."
        pytest "$PM_TEST_DIR" \
            --cov=.claude/tools/amplihack/pm \
            --cov-report=html \
            --cov-report=term-missing
        echo ""
        echo "Coverage report generated: htmlcov/index.html"
        ;;
    count)
        echo "Test count by file:"
        for file in "$PM_TEST_DIR"/test_*.py; do
            count=$(grep -c '^def test_' "$file" || echo 0)
            echo "  $(basename "$file"): $count tests"
        done
        echo ""
        total=$(grep -r '^def test_' "$PM_TEST_DIR"/test_*.py | wc -l | tr -d ' ')
        echo "Total: $total tests"
        ;;
    help|*)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  all          Run all tests (default)"
        echo "  state        Run state management tests"
        echo "  workstream   Run workstream tests"
        echo "  cli          Run CLI tests"
        echo "  workflow     Run integration workflow tests"
        echo "  unit         Run unit tests only"
        echo "  integration  Run integration tests only"
        echo "  coverage     Run tests with coverage report"
        echo "  count        Count tests by file"
        echo "  help         Show this help message"
        ;;
esac
