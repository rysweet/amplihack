#!/bin/bash
# Quick test runner for power-steering compaction tests
# Usage: ./RUN_COMPACTION_TESTS.sh [unit|integration|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

run_unit_tests() {
    echo "=========================================="
    echo "Running Unit Tests (test_compaction_validator.py)"
    echo "=========================================="
    python test_compaction_validator.py -v
}

run_integration_tests() {
    echo "=========================================="
    echo "Running Integration Tests (test_power_steering_compaction.py)"
    echo "=========================================="
    python test_power_steering_compaction.py -v
}

show_test_count() {
    echo ""
    echo "=========================================="
    echo "Test Count Summary"
    echo "=========================================="
    python -c "
import unittest
loader = unittest.TestLoader()

validator_suite = loader.loadTestsFromName('test_compaction_validator')
integration_suite = loader.loadTestsFromName('test_power_steering_compaction')

def count_tests(suite):
    count = 0
    for test in suite:
        if hasattr(test, '__iter__'):
            count += count_tests(test)
        else:
            count += 1
    return count

validator_count = count_tests(validator_suite)
integration_count = count_tests(integration_suite)

print(f'Unit tests: {validator_count}')
print(f'Integration tests: {integration_count}')
print(f'Total: {validator_count + integration_count}')
print('')
print('Status: All tests currently skipped (TDD - implementation pending)')
"
}

case "${1:-all}" in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    all)
        run_unit_tests
        echo ""
        run_integration_tests
        show_test_count
        ;;
    *)
        echo "Usage: $0 [unit|integration|all]"
        exit 1
        ;;
esac
