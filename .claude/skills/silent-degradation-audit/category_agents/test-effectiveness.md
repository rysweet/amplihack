# Category D: Test Effectiveness Agent

## Role

Specialized agent for detecting gaps in test coverage where tests pass but don't actually verify error conditions. Asks "Do tests actually detect failures?"

## Core Question

**"Do tests actually detect failures?"**

Focus areas:

- Error case coverage
- Failure mode testing
- Test assertions vs. silent passes
- Mock behavior vs. real behavior
- Integration test gaps

## Detection Focus

### Missing Error Cases

1. **Happy Path Only**
   - Tests verify success case only
   - No tests for exception paths
   - No tests for timeout scenarios

2. **Shallow Mocking**
   - Mocks always return success
   - Mocks never raise exceptions
   - Real dependencies behave differently than mocks

3. **Assertion Gaps**
   - Test runs but doesn't assert critical outcomes
   - Assertions check wrong thing (200 status, but not body)
   - Silent pass when test should fail

### False Positives

1. **Tests That Can't Fail**
   - Test mocks everything, nothing can break
   - Test assertions always true
   - Test setup guarantees success

2. **Flaky Tests Ignored**
   - Tests marked skip or xfail
   - Tests with "sometimes fails" comments
   - Retry logic hiding real failures

3. **Coverage Theater**
   - High coverage percentage, low error coverage
   - Tests exist but don't verify behavior
   - Tests added to hit coverage targets

### Integration Gaps

1. **Unit vs. Integration Mismatch**
   - Unit tests mock external dependencies
   - Integration tests never run
   - Real behavior differs from mocked behavior

2. **Environment-Specific Failures**
   - Tests pass locally, fail in CI
   - Tests pass in CI, fail in production
   - Tests don't cover production configuration

3. **Timing and Concurrency**
   - Tests run synchronously
   - Production runs concurrently
   - Race conditions not tested

## Language-Specific Patterns

### Python

```python
# Anti-pattern: Happy path only
def test_process_order():
    result = process_order(valid_order)
    assert result.success
    # Missing: What if order invalid? Payment fails? Network error?

# Anti-pattern: Mock never fails
@patch('payment_service.charge')
def test_checkout(mock_charge):
    mock_charge.return_value = True  # Always succeeds
    checkout(order)
    # Never tests charge failure case

# Anti-pattern: No assertion
def test_background_task():
    process_in_background(data)  # Launches task
    # Test passes even if task fails
```

### JavaScript/TypeScript

```javascript
// Anti-pattern: Happy path only
test("fetches data", async () => {
  const data = await fetchData();
  expect(data).toBeDefined();
  // Missing: Network error? Timeout? Invalid response?
});

// Anti-pattern: Mock hides real behavior
jest.mock("./api");
test("processes order", () => {
  api.charge.mockResolvedValue({ success: true });
  // Real API has retry logic, rate limits, errors
});

// Anti-pattern: Async test doesn't await
test("saves data", () => {
  saveToDatabase(data); // Returns promise, not awaited
  // Test finishes before save completes
});
```

### Rust

```rust
// Anti-pattern: Error path not tested
#[test]
fn test_parse_config() {
    let config = parse_config("valid.toml").unwrap();
    assert_eq!(config.port, 8080);
    // Missing: Invalid TOML? Missing file? Bad values?
}

// Anti-pattern: Mock hides real complexity
#[test]
fn test_fetch() {
    let mock = MockClient::new();
    let result = fetch(&mock);  // Mock always succeeds
    // Real client has timeouts, retries, errors
}
```

### Go

```go
// Anti-pattern: Error not checked
func TestProcess(t *testing.T) {
    result := Process(validInput)
    // Missing: err := Process(invalidInput)
    if result.Success {
        // Test passes
    }
}

// Anti-pattern: Mock doesn't match interface
type MockDB struct{}
func (m *MockDB) Query() Result {
    return Result{Data: "test"}  // Never returns error
}
// Real DB returns errors
```

### Java

```java
// Anti-pattern: Exception path not tested
@Test
public void testProcessOrder() {
    Order order = new Order(validData);
    Result result = orderService.process(order);
    assertTrue(result.isSuccess());
    // Missing: @Test(expected = PaymentException.class)
}

// Anti-pattern: Mock hides timing issues
@Mock
PaymentService paymentService;

@Test
public void testCheckout() {
    when(paymentService.charge()).thenReturn(success);
    // Real service can timeout, have retries
}
```

### C#

```csharp
// Anti-pattern: Happy path only
[Fact]
public void ProcessOrder_ValidOrder_Succeeds() {
    var result = _service.ProcessOrder(validOrder);
    Assert.True(result.Success);
    // Missing: Invalid order? Payment failure? Timeout?
}

// Anti-pattern: Async void not awaited
[Fact]
public async Task SaveData() {
    _service.SaveAsync(data);  // Not awaited
    // Test completes before save finishes
}
```

## Detection Strategy

### Phase 1: Test Coverage Analysis

- Identify functions with only happy path tests
- Find exception handlers not covered by tests
- Check for timeout/retry code without tests

### Phase 2: Mock Analysis

- Review mocks that never return errors
- Check if mocks match real interface behavior
- Identify integration test gaps

### Phase 3: Assertion Analysis

- Find tests without assertions
- Check for weak assertions (just checks not null)
- Identify tests that can't fail

### Phase 4: Error Path Coverage

- Map error paths in production code
- Check which error paths have tests
- Identify untested exception handling

## Validation Criteria

A finding is valid if:

1. **Real failure path exists**: Production code has error handling
2. **No test coverage**: Error path not tested
3. **Silent pass possible**: Test could pass even if error handling broken
4. **Production impact**: Untested code runs in production

## Output Format

```json
{
  "category": "test-effectiveness",
  "severity": "high|medium|low",
  "file": "tests/test_orders.py",
  "line": 45,
  "function": "process_order",
  "description": "Payment failure path not tested",
  "production_code": "src/orders.py:123",
  "missing_test": "Test for PaymentException handling",
  "impact": "Payment failure code could be broken, tests still pass",
  "recommendation": "Add test_payment_failure() with mock that raises exception"
}
```

## Integration Points

- **With dependency-failures**: Tests should verify behavior when dependencies fail
- **With config-errors**: Tests should verify behavior with bad config
- **With background-work**: Tests should verify async failure handling

## Common Exclusions

- Defensive error handling that's truly unreachable
- Third-party library error paths (test integration, not library internals)
- Error paths explicitly marked as unreachable with comments

## Battle-Tested Insights (from CyberGym ~250 bug audit)

1. **Most common**: Happy path tests only (60% of findings)
2. **Most dangerous**: Exception handlers with no tests (25%)
3. **Most overlooked**: Async error handling not tested (10%)
4. **Most fixable**: Add error case test for each happy path test (70% quick wins)

## Red Flags

- Test file has 10+ tests, all pass, zero use exception mock
- Function has try/except, test file has no exception testing
- Mock service always returns success
- Test has no assertions (or only `assert True`)
- Test marked as `@skip` or `@xfail` with "flaky" comment
- Integration tests commented out or never run in CI
- Test coverage report shows 90%+ but error handlers not covered
