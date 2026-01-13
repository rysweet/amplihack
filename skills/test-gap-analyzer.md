# Test Gap Analyzer

Domain knowledge for identifying missing test coverage and prioritizing test development.

## When to Use

- Before releasing features
- During code review
- Test planning sessions
- Keywords: "test coverage", "missing tests", "test gaps", "what to test"

## Testing Pyramid

```
        /\          10% E2E
       /  \         (Critical paths only)
      /----\        30% Integration
     /      \       (Module boundaries)
    /--------\      60% Unit
   /          \     (Business logic)
```

### Unit Tests (60%)
- Pure functions and business logic
- Individual class methods
- Fast, isolated, many

### Integration Tests (30%)
- Module boundaries
- Database interactions
- External service calls (mocked at boundary)

### E2E Tests (10%)
- Critical user journeys only
- Happy path + major error cases
- Expensive, slow, few

## Test Gap Detection Framework

### 1. Code Path Analysis

| Path Type | Must Test | Priority |
|-----------|-----------|----------|
| Happy path | Always | HIGH |
| Validation failures | Always | HIGH |
| Error handling | Always | HIGH |
| Edge cases | If business-critical | MEDIUM |
| Boundary conditions | If numeric/collection | MEDIUM |
| Rare conditions | If failure is severe | LOW |

### 2. Risk-Based Prioritization

```markdown
## Risk Assessment: [component]

### High Risk (Test First)
- [ ] Security-sensitive code (auth, permissions)
- [ ] Financial/monetary calculations
- [ ] Data mutation operations
- [ ] Public API endpoints
- [ ] Core business logic

### Medium Risk (Test Next)
- [ ] Complex conditional logic
- [ ] Integration points
- [ ] State management
- [ ] Error recovery paths

### Low Risk (Test If Time Permits)
- [ ] Simple getters/setters
- [ ] Trivial transformations
- [ ] Internal utilities
- [ ] UI presentation only
```

### 3. Coverage Gaps Checklist

```markdown
## Test Gap Analysis: [module]

### Untested Code Paths
- [ ] Identify branches without coverage
- [ ] List error handlers without tests
- [ ] Find validation logic gaps

### Missing Test Types
- [ ] Happy path covered?
- [ ] Error cases covered?
- [ ] Boundary conditions covered?
- [ ] Concurrency scenarios (if applicable)?

### Integration Gaps
- [ ] Module A ↔ Module B boundary tested?
- [ ] External API error handling tested?
- [ ] Database transaction rollback tested?
```

## Test Prioritization Matrix

| Coverage Gap | Business Impact | Priority |
|--------------|-----------------|----------|
| Auth bypass possible | CRITICAL | P0 - Now |
| Data corruption possible | CRITICAL | P0 - Now |
| Core feature broken | HIGH | P1 - This sprint |
| Edge case failure | MEDIUM | P2 - Next sprint |
| UX degradation | LOW | P3 - Backlog |

## What NOT to Test

- Third-party library internals
- Framework behavior
- Trivial code (getters, simple constructors)
- Private implementation details
- Code that will be deleted

## Test Quality Indicators

### Good Test Characteristics
- Tests ONE thing
- Descriptive name explains what and why
- Arrange-Act-Assert structure
- No logic in tests (no if/loops)
- Fast execution
- Independent of other tests

### Test Smells (Problems)
- Test name doesn't describe behavior
- Multiple assertions testing different things
- Complex setup indicating design problem
- Flaky/intermittent failures
- Tests that require specific order

## Output Format

```markdown
## Test Gap Report: [component/feature]

### Summary
- Current coverage: [X%]
- Critical gaps: [N]
- Recommended new tests: [N]

### Critical Gaps (P0)
1. [Function/path] - [Risk if untested]
2. ...

### High Priority Gaps (P1)
1. [Function/path] - [Risk if untested]
2. ...

### Recommended Test Plan
1. [ ] Add unit test for [specific case]
2. [ ] Add integration test for [boundary]
3. [ ] Add E2E test for [critical journey]

### Tests to Skip
- [Item] - [Reason it's low value]
```

## Philosophy Alignment

Testing supports amplihack philosophy:
- **Ruthless Simplicity**: Test pyramid prevents over-testing
- **Brick Philosophy**: Tests verify module contracts (studs)
- **Zero-BS**: No placeholder tests, every test provides value
