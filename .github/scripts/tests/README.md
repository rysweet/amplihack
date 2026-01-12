# Link Fixer Tests (TDD)

Ahoy! These be the tests fer the Link Fixer feature, written BEFORE implementation followin' Test-Driven Development principles.

## Test Structure

```
.github/scripts/tests/
├── __init__.py                  # Package marker
├── conftest.py                  # Shared fixtures and test utilities
├── test_link_fixer.py          # Main orchestrator tests (19 tests)
├── test_integration.py          # Integration & E2E tests (9 tests)
├── test_strategies/             # Strategy-specific tests (38 tests)
│   ├── __init__.py
│   ├── test_case_sensitivity.py     # 5 tests
│   ├── test_git_history.py          # 5 tests
│   ├── test_missing_extension.py    # 7 tests
│   ├── test_broken_anchors.py       # 8 tests
│   ├── test_relative_path.py        # 8 tests
│   └── test_double_slash.py         # 9 tests
├── TEST_SUMMARY.md              # Detailed test documentation
└── README.md                    # This file
```

## Total Test Count: 66 Tests

**Distribution (Testing Pyramid)**:

- Unit Tests (60%): 40 tests
- Integration Tests (30%): 20 tests
- E2E Tests (10%): 6 tests

## Current Status

**ALL TESTS FAILING** (Expected - TDD)

All tests fail with:

```
ModuleNotFoundError: No module named 'link_fixer'
```

This be the correct state fer TDD - tests written first, implementation comes next.

## Running Tests

### Run All Tests

```bash
pytest .github/scripts/tests/ -v
```

### Run Specific Test File

```bash
pytest .github/scripts/tests/test_strategies/test_case_sensitivity.py -v
```

### Run With Coverage

```bash
pytest .github/scripts/tests/ --cov=.github/scripts --cov-report=term-missing
```

### Run Specific Test Class

```bash
pytest .github/scripts/tests/test_link_fixer.py::TestLinkFixer -v
```

### Run Single Test

```bash
pytest .github/scripts/tests/test_link_fixer.py::TestLinkFixer::test_tries_multiple_strategies -v
```

## Test Categories

### 1. Strategy Tests (38 tests)

Each strategy has its own test file with comprehensive coverage:

**Case Sensitivity (5 tests)**

- Single case match → 95% confidence
- Multiple matches → low confidence
- No variants → None
- Preserves path structure
- Handles anchors

**Git History (5 tests)**

- Single move → 90% confidence
- Multiple moves → low confidence
- No history → None
- Directory moves
- Relative paths

**Missing Extension (7 tests)**

- Single .md match → 85% confidence
- Multiple extensions → low confidence
- No matches → None
- Preserves paths
- Handles anchors
- Common extensions (.md, .markdown)
- Prefers .md over .markdown

**Broken Anchors (8 tests)**

- Exact match → 90% confidence
- Fuzzy match → 70-85% confidence
- No similar anchors → None
- Case-insensitive matching
- Special characters
- Duplicate headers
- Preserves file path
- Multi-word headers

**Relative Path (8 tests)**

- Normalizes redundant dots → 75% confidence
- Resolves parent refs (..)
- Multiple parent refs
- Preserves anchors
- Excessive parent refs
- Already normalized → None
- Complex nested paths
- Absolute vs relative

**Double Slash (9 tests)**

- Removes double slash → 70% confidence
- Multiple slashes
- Preserves protocol (https://)
- Leading slash
- Trailing slash
- Preserves anchors
- No double slashes → None
- Mixed with parent refs
- Combines with normalization

### 2. Orchestrator Tests (19 tests)

**LinkFixer Class (9 tests)**

- Tries multiple strategies
- Confidence threshold filtering (>= 90%)
- Stops after successful fix
- Returns None when all fail
- Strategy execution order
- Modifies file with fix
- Batch fix multiple links
- Creates PR with fixes
- Creates issue for unfixable

**ConfidenceCalculator (4 tests)**

- Single match confidence
- Multiple match confidence
- Fuzzy match confidence
- Git history confidence

**FixResult (2 tests)**

- Creation
- Comparison

### 3. Integration Tests (9 tests)

**Workflow Integration (7 tests)**

- End-to-end case sensitivity fix
- Multiple strategies cascade
- Confidence threshold filtering
- Batch fix preserves formatting
- Git operations workflow
- Issue creation for unfixable
- Mixed success and failure

**Strategy Integration (2 tests)**

- Strategies respect priority
- Combined fixes in same file

## Shared Fixtures (conftest.py)

### Repository Fixtures

- `temp_repo`: Temporary git repository
- `sample_markdown_files`: Pre-populated test files
- `git_history_repo`: Repository with file move history

### Data Fixtures

- `broken_link_data`: Structured broken link scenarios
- `confidence_test_cases`: Confidence calculation test cases

## Key Test Patterns

### 1. Arrange-Act-Assert

Every test follows clear AAA structure:

```python
def test_example(temp_repo):
    # Arrange
    docs_dir = temp_repo / "docs"
    docs_dir.mkdir()

    # Act
    result = strategy.attempt_fix(source_file, broken_path)

    # Assert
    assert result.confidence == 0.95
```

### 2. Strategic Mocking

Unit tests mock external dependencies:

```python
with patch("subprocess.run") as mock_run:
    mock_run.return_value = Mock(returncode=0)
    result = fixer.create_pr(fixes)
```

### 3. Real File Operations

Integration tests use real temporary repositories:

```python
def test_workflow(temp_repo):
    # Real git operations
    readme = temp_repo / "README.md"
    readme.write_text("[Link](./GUIDE.MD)")
```

## Confidence Thresholds

Tests validate these confidence scores:

| Strategy              | Single Match | Multiple Matches |
| --------------------- | ------------ | ---------------- |
| Case Sensitivity      | 95%          | < 70%            |
| Git History           | 90%          | < 80%            |
| Missing Extension     | 85%          | < 70%            |
| Broken Anchor (Exact) | 90%          | -                |
| Broken Anchor (Fuzzy) | 70-85%       | -                |
| Relative Path         | 75%          | -                |
| Double Slash          | 70%          | -                |

**Orchestrator Threshold**: Only apply fixes >= 90% confidence

## Edge Cases Covered

### Boundary Conditions

- Empty paths
- Single character paths
- Maximum path length
- Root directory references

### Special Characters

- GitHub-style anchor generation
- Special characters in headers
- Duplicate headers with suffixes
- Protocol slashes (https://)

### Path Handling

- Relative paths (../, ./)
- Absolute paths
- Mixed slashes
- Redundant dots
- Excessive parent refs

### Git Operations

- File moves
- Directory moves
- Multiple moves
- No history

### Anchor Handling

- Exact matches
- Fuzzy matches
- Case-insensitive
- Multi-word headers
- Special characters

## Next Steps

1. **Implement `link_fixer.py`**
   - Start with simple components (FixResult, ConfidenceCalculator)
   - Implement strategies one by one
   - Build orchestrator last

2. **Run Tests Iteratively**

   ```bash
   # Watch mode for TDD cycle
   pytest .github/scripts/tests/ --watch
   ```

3. **Measure Coverage**

   ```bash
   pytest .github/scripts/tests/ --cov=.github/scripts/link_fixer --cov-report=html
   open htmlcov/index.html
   ```

4. **Verify All Pass**
   - Target: 100% pass rate
   - Coverage: >= 80%
   - All edge cases handled

## Architecture Validation

These tests validate the architect's design:

- ✅ Strategy pattern with abstract base
- ✅ 6 independent strategies
- ✅ Orchestrator coordinates execution
- ✅ Confidence-based filtering
- ✅ File modification workflow
- ✅ PR/Issue creation
- ✅ Batch processing

## Philosophy Alignment

Tests follow amplihack philosophy:

- **Testing Pyramid**: 60/30/10 distribution
- **Zero-BS**: No stubs, all real tests
- **Fast Unit Tests**: < 100ms each
- **Strategic Mocking**: Only external dependencies
- **Clear Purpose**: Each test has single responsibility

## Documentation

- **TEST_SUMMARY.md**: Detailed analysis of test coverage
- **This file**: Quick reference and usage guide
- **Test docstrings**: Explain what each test validates

---

Arr, now ye have a complete test suite ready fer implementation! Follow TDD principles:

1. Red: Tests fail (we be here)
2. Green: Implement until tests pass
3. Refactor: Clean up while keepin' tests green

Set sail and start implementin'! 🏴‍☠️
