#!/bin/bash
# Script to run recipe CLI tests
# These tests follow TDD - they will fail until implementation is complete

set -e

echo "=== Recipe CLI Test Suite ==="
echo ""
echo "Test Structure:"
echo "  - Unit Tests (Command Handlers): test_recipe_command.py"
echo "  - Unit Tests (Output Formatters): test_recipe_output.py"
echo "  - Integration Tests (E2E): test_recipe_cli_e2e.py"
echo "  - Test Fixtures: conftest.py"
echo ""
echo "Total: 2,851 lines of tests"
echo ""
echo "=== Running Tests ==="
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest not found. Install with: pip install pytest pytest-cov"
    exit 1
fi

# Run unit tests
echo "Running unit tests for command handlers..."
pytest tests/unit/cli/test_recipe_command.py -v --tb=short || true

echo ""
echo "Running unit tests for output formatters..."
pytest tests/unit/cli/test_recipe_output.py -v --tb=short || true

echo ""
echo "Running integration tests..."
pytest tests/integration/test_recipe_cli_e2e.py -v --tb=short || true

echo ""
echo "=== Test Summary ==="
echo "Tests are EXPECTED to fail until recipe_command.py and recipe_output.py are implemented."
echo "This follows TDD (Test-Driven Development) principles."
