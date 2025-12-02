"""Tests for the REST API Client module.

Testing pyramid distribution:
- 60% unit tests (test_exceptions, test_models, test_retry, test_client)
- 30% integration tests (test_integration)
- 10% E2E tests (covered in integration with mock server)

TDD Approach: These tests are written BEFORE implementation.
All tests should FAIL until the implementation is complete.
"""
