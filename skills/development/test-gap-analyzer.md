# Test Gap Analyzer

Coverage analysis and test quality assessment for identifying testing gaps.

## When to Use

- Assessing test coverage for a codebase
- Prioritizing which tests to write next
- Evaluating test quality beyond line coverage
- Planning testing strategy for new features
- Preparing for production release

## The Testing Pyramid

### Recommended Distribution

```
           /\
          /  \     End-to-End (E2E): 10%
         /    \    - Full user journeys
        /------\   - Critical paths only
       /        \  - Slow, expensive
      /          \ 
     / Integration \ Integration: 30%
    /    Tests      \ - Component interactions
   /----------------\ - API contracts
  /                  \ - Database operations
 /     Unit Tests     \ Unit: 60%
/______________________\ - Single functions
                        - Fast, isolated
                        - Edge cases
```

### Anti-Patterns

```
Ice Cream Cone (inverted pyramid):
- Too many E2E tests
- Few unit tests
- Slow, flaky test suite

Hourglass:
- Many E2E tests
- Few integration tests
- Many unit tests
- Integration bugs slip through

No Tests:
- "We'll add them later"
- Manual testing only
- Debugging in production
```

## Risk-Based Test Prioritization

### Risk Assessment Matrix

| Factor | Weight | Score 1-5 |
|--------|--------|-----------|
| Business criticality | 3x | How important is this feature? |
| Change frequency | 2x | How often does this code change? |
| Complexity | 2x | How complex is the logic? |
| Integration points | 2x | How many external dependencies? |
| Historical bugs | 1x | How often has this broken? |

```
Priority Score = Σ (Weight × Score)
Max Score = 50

High Priority: 35-50 (test first)
Medium Priority: 20-34 (test soon)
Low Priority: <20 (test eventually)
```

### Priority Categories

```
CRITICAL (test immediately):
- Payment processing
- Authentication/authorization
- Data persistence
- Security-sensitive operations
- Core business logic

HIGH (test before release):
- User-facing features
- API endpoints
- Data transformations
- Error handling paths

MEDIUM (test when possible):
- Admin features
- Reporting
- Non-critical workflows
- Helper utilities

LOW (test as time allows):
- Logging
- Metrics
- Development tools
- Deprecated code
```

## Coverage Gap Detection

### Types of Coverage

```python
# Line Coverage - which lines execute
def calculate(x, y):
    if x > 0:         # Covered
        return x + y  # Covered
    else:
        return x - y  # NOT covered

# Branch Coverage - which branches taken
def calculate(x, y):
    if x > 0:         # True branch: covered
        return x + y  # False branch: NOT covered
    else:
        return x - y

# Path Coverage - which execution paths
def calculate(x, y, z):
    result = x
    if y > 0:        # Path 1: y>0, z>0
        result += y  # Path 2: y>0, z<=0
    if z > 0:        # Path 3: y<=0, z>0
        result += z  # Path 4: y<=0, z<=0
    return result    # Need 4 tests for full path coverage
```

### Finding Uncovered Code

```bash
# Python coverage
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html  # Visual report

# JavaScript coverage
npm run test -- --coverage

# View uncovered lines
coverage report -m | grep -v "100%"
```

### Coverage Analysis Checklist

```
[ ] All public functions have tests
[ ] All branches/conditions covered
[ ] Error handling paths tested
[ ] Edge cases identified and tested
[ ] Integration points covered
[ ] Happy path and failure paths tested
```

## Test Quality Indicators

### Good Test Characteristics

```python
# 1. Single responsibility
def test_user_creation_sets_default_role():
    user = create_user("test@example.com")
    assert user.role == "member"  # Tests ONE thing

# 2. Clear assertion message
def test_order_total_includes_tax():
    order = Order(subtotal=100, tax_rate=0.1)
    assert order.total == 110, f"Expected 110, got {order.total}"

# 3. Isolated (no shared state)
def test_user_can_update_email(user_factory):
    user = user_factory()  # Fresh user each test
    user.update_email("new@example.com")
    assert user.email == "new@example.com"

# 4. Deterministic (not flaky)
def test_timestamp_within_range():
    before = datetime.now()
    result = create_timestamped_record()
    after = datetime.now()
    assert before <= result.timestamp <= after

# 5. Fast
# Unit tests should run in milliseconds
# Integration tests in seconds
# E2E tests in tens of seconds
```

### Test Smells

| Smell | Symptom | Fix |
|-------|---------|-----|
| Mystery Guest | Uses external data without explanation | Inline test data or explain |
| Eager Test | Tests multiple things | Split into focused tests |
| Flaky Test | Sometimes passes, sometimes fails | Fix timing, isolation |
| Obscure Test | Hard to understand | Improve naming, add comments |
| Test Logic | Complex logic in test | Simplify or extract |
| Conditional Test | if/switch in test | Split into separate tests |

### Test Metrics

```
Coverage Metrics:
- Line coverage: % of lines executed
- Branch coverage: % of branches taken
- Function coverage: % of functions called

Quality Metrics:
- Mutation score: % of mutants killed
- Test execution time: How fast tests run
- Flakiness rate: % of tests that intermittently fail
- Test/code ratio: Lines of test per line of code
```

## Gap Analysis Template

### Module Assessment

```markdown
## Module: [Name]

### Current State
- Line coverage: X%
- Branch coverage: X%
- Number of tests: N
- Test execution time: Xs

### Risk Assessment
| Factor | Score (1-5) | Notes |
|--------|-------------|-------|
| Business criticality | | |
| Change frequency | | |
| Complexity | | |
| Integration points | | |
| Historical bugs | | |
| **Priority Score** | **/50** | |

### Coverage Gaps
1. [Function/path not tested]
2. [Edge case not covered]
3. [Error path not tested]

### Recommended Tests (Priority Order)
1. [ ] Test for [critical gap]
2. [ ] Test for [high-risk area]
3. [ ] Test for [common failure]

### Test Quality Issues
1. [Flaky test to fix]
2. [Slow test to optimize]
3. [Test smell to address]
```

### Codebase-Wide Assessment

```markdown
## Test Gap Analysis: [Project Name]

### Summary
| Metric | Current | Target |
|--------|---------|--------|
| Overall line coverage | X% | 80% |
| Critical path coverage | X% | 95% |
| Test count | N | N+M |
| Flaky tests | N | 0 |
| Average test time | Xs | <Ys |

### Coverage by Module
| Module | Coverage | Priority | Gap Count |
|--------|----------|----------|-----------|
| auth | 85% | Critical | 3 |
| payment | 72% | Critical | 8 |
| reports | 45% | Medium | 12 |

### Top Priority Gaps
1. Payment processing error paths (Risk: 45/50)
2. Authentication edge cases (Risk: 42/50)
3. Data validation (Risk: 38/50)

### Recommended Actions
1. **Week 1**: Cover payment processing gaps
2. **Week 2**: Complete auth coverage
3. **Week 3**: Address data validation
4. **Ongoing**: Fix flaky tests
```

## Quick Commands

### Check Current Coverage

```bash
# Python
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Show only files below threshold
coverage report --fail-under=80 2>&1 | grep "FAIL"

# JavaScript
npm test -- --coverage --coverageThreshold='{"global":{"lines":80}}'
```

### Find Untested Functions

```bash
# Python - functions without tests
grep -r "def " src/ | while read line; do
    func=$(echo "$line" | grep -oP "def \K\w+")
    if ! grep -r "test.*$func\|$func.*test" tests/ > /dev/null; then
        echo "Untested: $func in $line"
    fi
done

# Simpler: use coverage report
coverage report -m | grep "0%"
```

### Identify Flaky Tests

```bash
# Run tests multiple times, find inconsistent results
for i in {1..10}; do
    pytest --tb=no -q 2>&1 | tail -1
done | sort | uniq -c

# pytest-repeat plugin
pytest --count=10 -x  # Stop on first failure
```

## Test Writing Priority Checklist

When deciding what to test next:

```
[ ] Is there a critical path without tests?
[ ] Did a recent bug reveal a testing gap?
[ ] Is there high-churn code without coverage?
[ ] Are there integration points untested?
[ ] Are error handling paths covered?
[ ] Are edge cases (null, empty, max) tested?
[ ] Is there security-sensitive code untested?
[ ] Are there flaky tests to fix first?
```

## Coverage Goals by Code Type

| Code Type | Line Coverage | Branch Coverage | Notes |
|-----------|---------------|-----------------|-------|
| Business logic | 90%+ | 85%+ | High priority |
| API handlers | 85%+ | 80%+ | Include error cases |
| Data access | 80%+ | 75%+ | CRUD + edge cases |
| Utilities | 75%+ | 70%+ | Common functions |
| Configuration | 70%+ | 60%+ | Key paths |
| Generated code | N/A | N/A | Skip from coverage |
