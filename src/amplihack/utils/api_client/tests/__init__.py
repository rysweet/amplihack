"""
Tests for amplihack.utils.api_client module.

This package contains comprehensive tests for the REST API Client following TDD approach.

Test Structure:
- test_client.py: Core APIClient functionality tests
- test_retry.py: Retry logic and exponential backoff tests
- test_rate_limit.py: Rate limiting and 429 handling tests
- test_exceptions.py: Custom exception hierarchy tests
- test_security.py: Security feature tests
- test_integration.py: Integration and end-to-end tests

Testing Philosophy:
- TDD approach: Tests written before implementation
- Testing pyramid: 60% unit, 30% integration, 10% E2E
- Mock external dependencies using responses library
- Comprehensive coverage of all 9 explicit requirements
"""
