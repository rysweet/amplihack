# TDD Prevention Suite - Integration Specification

## Overview

Complete specification for the TDD Prevention Suite that would have prevented PR #1394's syntax errors from reaching CI.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Workflow                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  git commit      │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Pre-commit Hook (Local Validation)              │
│                                                              │
│  1. scripts/pre-commit/check_syntax.py                      │
│     - AST-based validation                                  │
│     - Fast (< 500ms for 50 files)                          │
│     - Zero false positives                                  │
│                                                              │
│  Exit 0 → Continue │ Exit 1 → Block commit                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  git push        │
                    └──────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CI Pipeline (GitHub Actions)              │
│                                                              │
│  1. pytest tests/test_syntax.py                             │
│     - Order 1: Basic syntax validation                      │
│     - Order 2: Performance tests (< 2s full codebase)       │
│     - Order 3: Edge case tests (zero false positives)       │
│     - Order 4: Integration tests                            │
│                                                              │
│  Pass → Continue │ Fail → Block merge                       │
└─────────────────────────────────────────────────────────────┘
```

## Component Integration

### Component 1: Pre-commit Hook
**File**: `scripts/pre-commit/check_syntax.py`
**Config**: `.pre-commit-config.yaml`

**Integration Points**:
- Called by pre-commit framework on staged Python files
- Exits 0 (success) or 1 (failure) to control commit flow
- Outputs errors in standard format for IDE integration

**Contract**:
```python
# Input: List of file paths from pre-commit
# Output: Exit code + error messages to stdout
# Performance: < 500ms for 50 files
```

### Component 2: Test Suite
**File**: `tests/test_syntax.py` (or add to `tests/test_code_quality.py`)

**Test Hierarchy**:
1. **Order 1** - Basic Syntax Tests
   - Valid file passes
   - Invalid file fails
   - Error location is accurate

2. **Order 2** - Performance Tests
   - Single file < 50ms
   - 50 files < 500ms
   - Full codebase < 2s

3. **Order 3** - Edge Case Tests
   - Valid code with "=====" in strings passes
   - Valid code with "<<<" in comments passes
   - Real merge conflicts fail

4. **Order 4** - Integration Tests
   - Pre-commit hook works end-to-end
   - CI integration works

**Integration Points**:
- Imports `check_syntax` module
- Uses pytest fixtures from `conftest.py`
- Reports to CI via pytest exit codes

### Component 3: Test Ordering
**Config**: `pyproject.toml` or `pytest.ini`
**Dependency**: `pytest-order`

**Integration Points**:
- Configures pytest to respect `@pytest.mark.order()`
- Ensures fail-fast behavior (syntax errors found first)
- Works with existing pytest configuration

### Component 4: CI Integration
**File**: `.github/workflows/*.yml`

**Integration Points**:
- Pre-commit runs on all PRs
- Pytest runs with ordered tests
- Blocks merge if syntax validation fails

## Data Flow

### Local Development Flow
```
Developer writes code
       ↓
git add file.py
       ↓
git commit
       ↓
pre-commit hook triggers
       ↓
check_syntax.py validates file.py
       ↓
   ┌───┴───┐
   │       │
Valid    Invalid
   │       │
   │       └→ Show error, block commit
   │
   └→ Commit succeeds
       ↓
git push
```

### CI Validation Flow
```
PR opened/updated
       ↓
CI starts
       ↓
Run pytest with ordered tests
       ↓
Order 1: Syntax validation
   ┌───┴───┐
   │       │
Pass    Fail → Block PR, show errors
   │
   └→ Order 2: Performance tests
       ┌───┴───┐
       │       │
    Pass    Fail → Block PR, show performance issue
       │
       └→ Order 3: Edge cases
           ┌───┴───┐
           │       │
        Pass    Fail → Block PR, show false positive/negative
           │
           └→ Order 4: Integration tests
               ┌───┴───┐
               │       │
            Pass    Fail → Block PR, show integration issue
               │
               └→ All tests pass → PR ready for merge
```

## File Structure

```
amplihack/
├── scripts/
│   └── pre-commit/
│       └── check_syntax.py          # Component 1: Pre-commit hook
├── tests/
│   ├── conftest.py                  # Existing fixtures
│   └── test_syntax.py               # Component 2: Test suite
│       ├── TestSyntaxValidation     # Order 1
│       ├── TestSyntaxPerformance    # Order 2
│       ├── TestSyntaxEdgeCases      # Order 3
│       └── TestSyntaxIntegration    # Order 4
├── .pre-commit-config.yaml          # Component 3: Pre-commit config
├── pyproject.toml                   # Component 3: Pytest ordering config
└── Specs/
    ├── check_syntax.md              # Spec for Component 1
    ├── performance_tests.md         # Spec for Component 2
    ├── test_ordering.md             # Spec for Component 3
    ├── edge_case_tests.md           # Spec for Component 4
    └── INTEGRATION.md               # This file
```

## Implementation Order

### Phase 1: Core Validation (MVP)
1. Implement `scripts/pre-commit/check_syntax.py`
2. Add basic tests (Order 1)
3. Add to `.pre-commit-config.yaml`
4. Manual testing

**Deliverable**: Working pre-commit hook that blocks syntax errors

### Phase 2: Performance & Ordering
1. Add performance tests (Order 2)
2. Add `pytest-order` dependency
3. Configure `pyproject.toml`
4. Verify test ordering

**Deliverable**: Performance guarantees + fail-fast testing

### Phase 3: Edge Cases & Hardening
1. Add edge case tests (Order 3)
2. Verify zero false positives
3. Add integration tests (Order 4)
4. Full CI validation

**Deliverable**: Production-ready, hardened system

### Phase 4: Documentation & Rollout
1. Update README
2. Update CONTRIBUTING
3. Add usage examples
4. Team communication

**Deliverable**: Team adoption + documentation

## Success Criteria

### Must-Have (MVP)
- ✅ Pre-commit hook blocks syntax errors
- ✅ Basic tests validate hook works
- ✅ Performance: < 500ms for 50 files

### Should-Have (Production)
- ✅ Performance: < 2s for full codebase
- ✅ Test ordering (syntax first)
- ✅ Zero false positives on valid code

### Nice-to-Have (Polish)
- ✅ Integration tests
- ✅ Detailed documentation
- ✅ Performance monitoring

## Verification Plan

### Manual Verification
1. **Valid file**: Create valid Python file, verify commit succeeds
2. **Invalid file**: Create file with syntax error, verify commit blocked
3. **Performance**: Time validation on real codebase
4. **Edge cases**: Create files with "=====" in strings, verify pass

### Automated Verification
1. **Unit tests**: All tests pass
2. **CI pipeline**: Green on all checks
3. **Integration**: Pre-commit hook works in CI

### Regression Prevention
1. **Add test for PR #1394**: Specific test case for the original bug
2. **Document in DISCOVERIES.md**: Record what we learned
3. **Monitor**: Track if similar bugs occur (should be zero)

## Performance Budget

| Component | Scenario | Budget | Measured | Status |
|-----------|----------|--------|----------|--------|
| check_syntax.py | 1 file | 50ms | TBD | - |
| check_syntax.py | 50 files | 500ms | TBD | - |
| check_syntax.py | Full codebase | 2s | TBD | - |
| Test suite | All tests | 5s | TBD | - |

## Error Handling

### Pre-commit Hook Errors
1. **File not found**: Clear error message, exit 1
2. **Syntax error**: Show file:line:column, exit 1
3. **Performance timeout**: Warn but don't block (fail open)
4. **Internal error**: Log error, fail open (don't block commits)

### Test Errors
1. **Import failure**: Clear error, fail test
2. **Performance regression**: Show delta, fail test
3. **False positive**: Show code sample, fail test
4. **CI timeout**: Configurable timeout, fail gracefully

## Maintenance Plan

### Weekly
- Monitor CI run times
- Check for false positives/negatives
- Review performance metrics

### Monthly
- Update performance budgets if needed
- Review edge cases
- Update documentation

### Quarterly
- Evaluate pytest-order alternatives
- Review tool effectiveness
- Consider new edge cases

## Dependencies

### Required
- Python 3.8+
- `pytest`
- `pytest-order`

### Optional
- `pytest-benchmark` (for detailed performance metrics)
- `pytest-xdist` (for parallel test execution)

## Rollout Checklist

- [ ] Implement `check_syntax.py`
- [ ] Add to `.pre-commit-config.yaml`
- [ ] Add basic tests (Order 1)
- [ ] Add performance tests (Order 2)
- [ ] Add edge case tests (Order 3)
- [ ] Configure test ordering
- [ ] Verify in CI
- [ ] Update documentation
- [ ] Team announcement
- [ ] Monitor for issues

## Success Metrics

### Effectiveness
- **Goal**: Zero syntax errors reach CI
- **Measure**: Count syntax errors in CI over 30 days
- **Target**: 0 (100% prevention)

### Performance
- **Goal**: Fast feedback (< 500ms pre-commit)
- **Measure**: p95 pre-commit hook execution time
- **Target**: < 500ms

### Reliability
- **Goal**: Zero false positives
- **Measure**: Count blocked commits on valid code
- **Target**: 0 (100% accuracy)

### Adoption
- **Goal**: All developers use pre-commit hooks
- **Measure**: % of commits with pre-commit hook enabled
- **Target**: 100%

## Related Issues

- **Original Bug**: PR #1394 (syntax error reached CI)
- **Prevention Issue**: #1420 (this implementation)

## References

- **Python AST**: https://docs.python.org/3/library/ast.html
- **pytest-order**: https://pytest-order.readthedocs.io/
- **pre-commit**: https://pre-commit.com/
