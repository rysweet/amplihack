# Goal: Test Coverage Analyzer and Improver

Analyze test coverage and automatically improve it by identifying untested code and suggesting test cases.

## Constraints

- Must complete analysis within 10 minutes
- Should follow testing pyramid (60% unit, 30% integration, 10% E2E)
- Must provide specific test suggestions
- Should identify critical untested paths

## Success Criteria

- Identifies untested functions and classes
- Finds critical paths without tests (error handling, edge cases)
- Suggests specific test cases for each gap
- Calculates current coverage percentage
- Prioritizes tests by risk/importance
- Generates example test code

## Context

Help improve test coverage by:

- Running coverage tools (pytest-cov, coverage.py)
- Analyzing which code lacks tests
- Identifying high-risk untested areas
- Suggesting specific test scenarios
- Generating test templates
