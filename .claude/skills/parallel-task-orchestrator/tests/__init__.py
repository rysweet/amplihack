"""Test suite for parallel-task-orchestrator skill.

Test Structure:
- 60% unit tests (fast, heavily mocked)
- 30% integration tests (multiple components)
- 10% E2E tests (complete workflows)

Run all tests:
    pytest

Run specific test categories:
    pytest tests/unit/           # Unit tests only
    pytest tests/integration/    # Integration tests only
    pytest tests/e2e/            # E2E tests only

Run with markers:
    pytest -m "not slow"         # Skip slow E2E tests
    pytest -m simserv            # Run SimServ validation tests

Philosophy: Test behavior, not implementation. TDD - tests written before code.
"""

__version__ = "0.1.0"
