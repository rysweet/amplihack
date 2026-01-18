# Example: Adaptive Testing with Goal-Seeking Agents

## Scenario: Intelligent Test Generation and Execution

### Problem Statement

Manual test creation and maintenance is:

- **Time-consuming**: 30-60 minutes to write comprehensive tests for new features
- **Coverage-incomplete**: Easy to miss edge cases and error paths
- **Maintenance-heavy**: Tests break when code changes, require manual updates
- **Context-unaware**: Same test strategy regardless of code complexity
- **Flaky**: Tests fail intermittently, require manual investigation

### Is Goal-Seeking Appropriate?

Apply the 5-question decision framework:

**Q1: Well-defined objective but flexible path?**

- **YES**: Objective is clear (generate and run comprehensive tests)
- Multiple paths:
  - Simple functions: Basic unit tests
  - Complex logic: Property-based tests, edge cases
  - APIs: Integration tests with mocks
  - Flaky tests: Retry strategies, better assertions
- Success criteria: ≥ 80% coverage, all tests pass

**Q2: Multiple phases with dependencies?**

- **YES**: 4 phases with dependencies
  1. Code Analysis (understand what to test)
  2. Test Generation (create tests based on analysis)
  3. Test Execution (run tests, handle failures)
  4. Coverage Analysis (verify completeness, suggest improvements)

**Q3: Autonomous recovery valuable?**

- **YES**: Test failures are common and often fixable
  - Flaky tests: Retry with better waits
  - Import errors: Auto-fix imports
  - Assertion errors: Suggest better assertions
  - Mock setup issues: Auto-configure mocks

**Q4: Context affects approach?**

- **YES**: Test strategy varies by:
  - Code complexity (simple vs complex algorithms)
  - Code type (pure functions vs stateful classes vs APIs)
  - Existing coverage (gaps vs comprehensive)
  - Flakiness history (stable vs intermittent failures)

**Q5: Complexity justified?**

- **YES**: High-value automation
  - Frequency: Every feature (50-100 times per year)
  - Manual time: 30-60 minutes per feature
  - Value: 25-100 hours saved per year
  - Quality: Catches more edge cases than manual testing

**Conclusion**: All 5 YES → Goal-seeking agent is appropriate

## Goal-Seeking Agent Design

### Goal Definition

```markdown
# Goal: Intelligent Test Generation and Execution

## Objective

Analyze code to understand functionality, generate comprehensive tests
covering happy paths and edge cases, execute tests with intelligent retry
for flaky failures, and verify coverage thresholds are met.

## Success Criteria

- Code analyzed to identify test requirements
- Tests generated for all public functions/methods
- Coverage ≥ 80% (line coverage)
- All tests pass (or failures are investigated and fixed)
- Edge cases identified and tested
- Flaky tests handled with retries or better assertions

## Constraints

- Must preserve existing tests (don't overwrite)
- Test framework: pytest (Python)
- Max 5 test iterations (prevent infinite loops)
- Tests must run in < 5 minutes
- No external dependencies (use mocks)

## Context

- Language: Python
- Framework: pytest
- Target: New feature functions or classes
- Priority: High (blocking feature merge)
```

### Execution Plan

```python
from amplihack.goal_agent_generator import PromptAnalyzer, ObjectivePlanner

analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

planner = ObjectivePlanner()
execution_plan = planner.generate_plan(goal_def)

# Result: 4-phase plan
```

**Phase 1: Code Analysis** (5 minutes)

- Parse source code (AST analysis)
- Identify functions, classes, methods
- Extract function signatures, docstrings
- Detect complexity (cyclomatic complexity)
- Identify dependencies (imports, external calls)

Dependencies: None
Success indicators:

- All public functions identified
- Signatures extracted
- Complexity assessed
- Dependencies mapped

**Phase 2: Test Generation** (10 minutes, depends on Phase 1)

- Generate unit tests for simple functions
- Generate property-based tests for complex logic
- Generate integration tests for APIs
- Create fixtures and mocks
- Add edge case tests

Dependencies: Phase 1 (needs code analysis)
Success indicators:

- Tests generated for all functions
- Edge cases covered
- Fixtures/mocks created
- Test files organized properly

**Phase 3: Test Execution** (15 minutes, depends on Phase 2)

- Run pytest on generated tests
- Capture failures and analyze
- Apply fixes for common failures
- Retry flaky tests with better strategies
- Re-run until all pass or max iterations

Dependencies: Phase 2 (needs generated tests)
Success indicators:

- All tests executed
- Failures analyzed and fixed
- Flaky tests identified and handled
- Final run: all tests pass

**Phase 4: Coverage Analysis** (5 minutes, depends on Phase 3)

- Run pytest with coverage
- Analyze coverage report
- Identify uncovered lines
- Suggest additional tests for gaps
- Verify coverage threshold met

Dependencies: Phase 3 (needs passing tests)
Success indicators:

- Coverage ≥ 80%
- Coverage gaps identified
- Suggestions for improvements
- Report generated

**Total Duration**: 35 minutes (estimated)

### Implementation

```python
from amplihack.goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)
from pathlib import Path
import ast
import subprocess
from typing import List, Dict, Any

# Goal definition
goal_text = """
Analyze code, generate comprehensive tests (unit + edge cases),
execute tests with intelligent retry for flaky failures,
verify coverage ≥ 80%.
"""

# Create agent
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

planner = ObjectivePlanner()
execution_plan = planner.generate_plan(goal_def)

synthesizer = SkillSynthesizer()
skills = synthesizer.synthesize(execution_plan)

assembler = AgentAssembler()
agent_bundle = assembler.assemble(
    goal_definition=goal_def,
    execution_plan=execution_plan,
    skills=skills,
    bundle_name="adaptive-test-generator"
)

packager = GoalAgentPackager()
packager.package(
    bundle=agent_bundle,
    output_dir=Path(".claude/agents/goal-driven/adaptive-test-generator")
)
```

### Adaptive Behavior

The agent adapts based on code characteristics:

**Scenario 1: Simple Pure Function** (basic unit tests)

```python
# Code to test
def calculate_total(items: List[float]) -> float:
    """Calculate total of item prices."""
    return sum(items)

# Agent generates:
def test_calculate_total_happy_path():
    """Test with valid input"""
    assert calculate_total([1.0, 2.0, 3.0]) == 6.0

def test_calculate_total_empty_list():
    """Test edge case: empty list"""
    assert calculate_total([]) == 0.0

def test_calculate_total_single_item():
    """Test edge case: single item"""
    assert calculate_total([5.0]) == 5.0

def test_calculate_total_negative_values():
    """Test edge case: negative values"""
    assert calculate_total([-1.0, 2.0]) == 1.0
```

**Scenario 2: Complex Logic** (property-based tests)

```python
# Code to test
def binary_search(arr: List[int], target: int) -> int:
    """Binary search implementation. Returns index or -1."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# Agent detects complexity (cyclomatic = 5) and generates property-based tests:
from hypothesis import given, strategies as st

@given(st.lists(st.integers()).map(sorted), st.integers())
def test_binary_search_property_found(sorted_list, target):
    """Property: If target in list, result should be valid index"""
    result = binary_search(sorted_list, target)
    if target in sorted_list:
        assert result != -1
        assert sorted_list[result] == target

@given(st.lists(st.integers()).map(sorted), st.integers())
def test_binary_search_property_not_found(sorted_list, target):
    """Property: If target not in list, result should be -1"""
    result = binary_search(sorted_list, target)
    if target not in sorted_list:
        assert result == -1

def test_binary_search_edge_empty():
    """Edge case: empty list"""
    assert binary_search([], 5) == -1

def test_binary_search_edge_single():
    """Edge case: single element"""
    assert binary_search([5], 5) == 0
    assert binary_search([5], 3) == -1
```

**Scenario 3: API Endpoint** (integration tests with mocks)

```python
# Code to test
from flask import Flask, jsonify, request
app = Flask(__name__)

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = database.create_user(data['name'], data['email'])
    return jsonify(user), 201

# Agent generates integration tests with mocks:
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    return app.test_client()

@pytest.fixture
def mock_database():
    """Mock database"""
    with patch('app.database') as mock_db:
        yield mock_db

def test_create_user_success(client, mock_database):
    """Test successful user creation"""
    mock_database.create_user.return_value = {
        'id': 1, 'name': 'John', 'email': 'john@example.com'
    }

    response = client.post('/api/users', json={
        'name': 'John',
        'email': 'john@example.com'
    })

    assert response.status_code == 201
    assert response.json['name'] == 'John'
    mock_database.create_user.assert_called_once()

def test_create_user_missing_field(client, mock_database):
    """Test error handling: missing required field"""
    response = client.post('/api/users', json={'name': 'John'})
    assert response.status_code in [400, 422]  # Bad request

def test_create_user_invalid_email(client, mock_database):
    """Test validation: invalid email"""
    response = client.post('/api/users', json={
        'name': 'John',
        'email': 'not-an-email'
    })
    assert response.status_code in [400, 422]
```

**Scenario 4: Flaky Test** (intelligent retry with better assertions)

```python
# Original flaky test (timing-sensitive)
def test_async_operation():
    """Test async operation completion"""
    start_async_operation()
    time.sleep(0.1)  # Race condition!
    result = get_operation_result()
    assert result == 'completed'

# Agent detects flakiness and improves:
import pytest
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def wait_for_operation():
    """Wait for operation with retries"""
    result = get_operation_result()
    if result != 'completed':
        raise AssertionError("Operation not completed")
    return result

def test_async_operation_improved():
    """Test async operation with proper waiting"""
    start_async_operation()

    # Better: Poll until complete or timeout
    result = wait_for_operation()
    assert result == 'completed'

# Alternative: Use pytest-asyncio for proper async testing
@pytest.mark.asyncio
async def test_async_operation_asyncio():
    """Test async operation with asyncio"""
    operation = start_async_operation()
    result = await operation
    assert result == 'completed'
```

### Error Recovery and Fix Strategies

**Fix Strategy 1: Import Errors** (auto-fix imports)

```python
# Test failure: ModuleNotFoundError: No module named 'calculator'
# Agent analyzes and fixes:

# Original generated test:
from calculator import calculate_total  # WRONG PATH

# Agent detects source file location and fixes:
from app.utils.calculator import calculate_total  # CORRECT PATH

# Auto-fix applied:
def fix_import_errors(test_file: Path, source_file: Path):
    """Auto-fix import paths"""
    module_path = get_module_path(source_file)
    test_content = test_file.read_text()

    # Replace incorrect imports
    test_content = test_content.replace(
        f"from {source_file.stem} import",
        f"from {module_path} import"
    )

    test_file.write_text(test_content)
```

**Fix Strategy 2: Assertion Errors** (improve assertions)

```python
# Test failure: AssertionError (no clear message)
def test_calculate_total():
    result = calculate_total([1, 2, 3])
    assert result == 7  # Wrong expected value

# Agent detects and suggests fix:
def test_calculate_total_improved():
    items = [1, 2, 3]
    result = calculate_total(items)
    expected = sum(items)  # Calculate expected value

    assert result == expected, (
        f"calculate_total({items}) returned {result}, expected {expected}"
    )
```

**Fix Strategy 3: Mock Setup** (auto-configure mocks)

```python
# Test failure: AttributeError: 'MagicMock' object has no attribute 'return_value'
# Agent detects missing mock setup:

# Original (incomplete):
@patch('app.database')
def test_create_user(mock_db):
    result = create_user({'name': 'John'})
    # Fails: mock_db not configured

# Agent improves:
@patch('app.database')
def test_create_user_improved(mock_db):
    # Agent adds proper mock configuration
    mock_db.create_user.return_value = {'id': 1, 'name': 'John'}

    result = create_user({'name': 'John'})
    assert result['name'] == 'John'
    mock_db.create_user.assert_called_once_with('John')
```

### Execution Example

```
Adaptive Test Generator: Starting

Target: src/app/calculator.py (3 functions)

Phase 1: Code Analysis [In Progress]
├── Parsing source code...
│   └── AST analysis: ✓ COMPLETED
├── Identifying functions...
│   ├── calculate_total(items: List[float]) -> float
│   ├── calculate_average(items: List[float]) -> float
│   └── calculate_median(items: List[float]) -> float
│   └── ✓ 3 functions identified
├── Assessing complexity...
│   ├── calculate_total: Cyclomatic 1 (simple)
│   ├── calculate_average: Cyclomatic 2 (simple)
│   └── calculate_median: Cyclomatic 4 (moderate)
│   └── ✓ Complexity assessed
└── Analyzing dependencies...
    ├── Imports: statistics (standard library)
    └── External calls: None
    └── ✓ No external dependencies

Phase 1: ✓ COMPLETED (2 minutes)

Phase 2: Test Generation [In Progress]
├── Generating tests for calculate_total...
│   ├── Happy path test: ✓ Generated
│   ├── Edge case (empty list): ✓ Generated
│   ├── Edge case (single item): ✓ Generated
│   └── Edge case (negative values): ✓ Generated
├── Generating tests for calculate_average...
│   ├── Happy path test: ✓ Generated
│   ├── Edge case (empty list): ✓ Generated (expects ZeroDivisionError)
│   ├── Edge case (single item): ✓ Generated
│   └── Edge case (all zeros): ✓ Generated
└── Generating tests for calculate_median...
    ├── Happy path (odd count): ✓ Generated
    ├── Happy path (even count): ✓ Generated
    ├── Edge case (empty list): ✓ Generated
    ├── Edge case (single item): ✓ Generated
    └── Property-based test: ✓ Generated (complexity ≥ 3)

Phase 2: ✓ COMPLETED
- Tests generated: 14
- Test file: tests/test_calculator.py
- Fixtures: 0
- Mocks: 0 (no external dependencies)
- Duration: 8 minutes

Phase 3: Test Execution [In Progress]

Iteration 1:
├── Running pytest... ✓ COMPLETED
├── Results: 13/14 passed, 1 failed
├── Failures:
│   └── test_calculate_average_empty_list:
│       Expected ZeroDivisionError, got statistics.StatisticsError
├── Analyzing failure...
│   └── Root cause: Wrong exception type
├── Applying fix...
│   └── Updated: expect statistics.StatisticsError instead
└── Re-running tests...

Iteration 2:
├── Running pytest... ✓ COMPLETED
└── Results: 14/14 passed ✓

Phase 3: ✓ COMPLETED
- Total tests: 14
- Iterations: 2
- Final status: All tests passing
- Duration: 5 minutes

Phase 4: Coverage Analysis [In Progress]
├── Running pytest with coverage...
│   └── ✓ COMPLETED
├── Coverage report:
│   ├── calculate_total: 100% (4/4 lines)
│   ├── calculate_average: 100% (6/6 lines)
│   └── calculate_median: 87.5% (7/8 lines)
│   └── Overall: 94.4% ✓ (threshold: 80%)
├── Uncovered lines:
│   └── calculator.py:45 (error path in calculate_median)
└── Suggestion:
    └── Add test for calculate_median with invalid input type

Phase 4: ✓ COMPLETED (3 minutes)

Test Generation Complete: ✓ SUCCESS (18 minutes)

Summary:
┌──────────────────────────────────────────────────────────────┐
│ Adaptive Test Generator - Summary                            │
├──────────────────────────────────────────────────────────────┤
│ Target: src/app/calculator.py                                │
│ Functions analyzed: 3                                        │
│ Tests generated: 14                                          │
│ Test iterations: 2                                           │
│ Final status: All tests passing ✓                           │
│                                                              │
│ Coverage:                                                    │
│ - Overall: 94.4% ✓ (threshold: 80%)                         │
│ - calculate_total: 100%                                      │
│ - calculate_average: 100%                                    │
│ - calculate_median: 87.5%                                    │
│                                                              │
│ Test Distribution:                                           │
│ - Happy path: 5 tests                                       │
│ - Edge cases: 8 tests                                       │
│ - Property-based: 1 test                                    │
│                                                              │
│ Improvements:                                                │
│ - Fixed 1 assertion error (wrong exception type)            │
│ - Suggested 1 additional test (uncovered error path)        │
│                                                              │
│ Next Steps:                                                  │
│ - Review generated tests: tests/test_calculator.py          │
│ - Run tests: pytest tests/test_calculator.py                │
│ - Add suggested test for 100% coverage                      │
└──────────────────────────────────────────────────────────────┘
```

### Failure Scenario: Persistent Test Failures

```
Phase 3: Test Execution [In Progress]

Iteration 1:
├── Running pytest...
└── Results: 10/14 passed, 4 failed
    ├── test_api_call: ConnectionError (mock not configured)
    ├── test_database_query: AttributeError (mock missing method)
    ├── test_async_operation: TimeoutError (async not awaited)
    └── test_complex_logic: AssertionError (edge case not handled)

Iteration 2:
├── Fixing mock configuration...
│   └── ✓ Mock setup improved
├── Fixing async handling...
│   └── ✓ Added pytest.mark.asyncio
├── Re-running pytest...
└── Results: 12/14 passed, 2 failed
    ├── test_database_query: Still failing (complex mock)
    └── test_complex_logic: Still failing (algorithm bug?)

Iteration 3:
├── Analyzing complex failures...
│   ├── test_database_query: Needs multi-level mock
│   └── test_complex_logic: Possible code bug
├── Applying advanced fixes...
│   └── ✓ Multi-level mock configured
├── Re-running pytest...
└── Results: 13/14 passed, 1 failed
    └── test_complex_logic: Still failing

Iteration 4:
├── Deep analysis of test_complex_logic...
│   └── Hypothesis: Algorithm bug in code (not test issue)
├── Escalating to human...

Phase 3: ⚠ PARTIAL SUCCESS (Max iterations reached)

┌──────────────────────────────────────────────────────────────┐
│ ⚠ Test Execution Incomplete                                  │
│                                                              │
│ Status: 13/14 tests passing (92.9%)                         │
│ Remaining failure: test_complex_logic                        │
│                                                              │
│ Investigation:                                               │
│ - Test appears correct                                       │
│ - Failure is consistent (not flaky)                         │
│ - Possible bug in source code (calculate_median)            │
│                                                              │
│ Recommended Actions:                                         │
│ 1. Review algorithm in calculate_median (line 40-48)        │
│ 2. Debug with failing input: [1, 2, 3, 4, 5, 6]            │
│ 3. Expected: 3.5, Got: 3.0                                  │
│ 4. Possible issue: Integer division instead of float        │
│                                                              │
│ Fix Suggestion:                                              │
│ Replace: result = (sorted_items[mid] + sorted_items[mid+1]) / 2
│ With: result = (sorted_items[mid] + sorted_items[mid+1]) / 2.0
│                                                              │
│ After fixing code, re-run:                                   │
│ pytest tests/test_calculator.py::test_complex_logic         │
└──────────────────────────────────────────────────────────────┘
```

## Lessons Learned

**Benefits Realized**:

1. **Time savings**: 18 minutes automated vs 30-60 minutes manual
2. **Coverage**: 94.4% achieved automatically (better than manual)
3. **Edge cases**: 8 edge case tests generated (often missed manually)
4. **Adaptive**: Different strategies for simple vs complex code
5. **Self-fixing**: Fixed 1 assertion error automatically

**Challenges Encountered**:

1. **Complex mocks**: Multi-level mocking required manual intervention
2. **Code bugs**: Test revealed algorithm bug (not test issue)
3. **Async testing**: Required pytest-asyncio (dependency management)
4. **Property-based tests**: Hypothesis integration added complexity

**Philosophy Compliance**:

- **Ruthless simplicity**: 4 clear phases, straightforward logic
- **Single responsibility**: Each phase focused (analyze, generate, execute, validate)
- **Modularity**: Test generators (unit, property-based, integration) are reusable
- **Regeneratable**: Can rebuild tests from code analysis

**When to Use This Pattern**:

- New features requiring comprehensive tests
- Legacy code lacking test coverage
- Refactoring (ensure behavior preserved)
- Flaky test investigation and fixing
- CI failures from missing tests

**When NOT to Use**:

- Simple one-liner functions (manual test faster)
- UI tests (requires different approach)
- Performance tests (needs benchmarking framework)
- Security tests (specialized tools required)
- Tests already exist and are comprehensive
