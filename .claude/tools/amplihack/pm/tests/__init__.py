"""
PM Architect Phase 1 Test Suite

Comprehensive test coverage for file-based PM system:
- 80+ unit tests across state, workstream, and CLI modules
- 15+ integration tests for end-to-end workflows
- Fixtures and helpers for consistent testing

Test Organization:
    test_pm_state.py (~30 tests): State management and persistence
    test_pm_workstream.py (~25 tests): Workstream lifecycle and agent integration
    test_pm_cli.py (~25 tests): CLI commands and user interaction
    test_pm_workflow.py (~15 tests): End-to-end integration flows
    conftest.py: Shared fixtures and test utilities

Running Tests:
    # All tests
    pytest .claude/tools/amplihack/pm/tests/

    # Specific module
    pytest .claude/tools/amplihack/pm/tests/test_pm_state.py

    # By marker
    pytest -m unit  # Fast unit tests only
    pytest -m integration  # Integration tests only

    # With coverage
    pytest --cov=.claude/tools/amplihack/pm --cov-report=html

Test Philosophy:
    - Test behavior, not implementation
    - Clear Arrange-Act-Assert pattern
    - Descriptive test names (test_should_X_when_Y)
    - Mock external dependencies (ClaudeProcess)
    - Real file I/O for integration tests
"""

__version__ = "1.0.0"
