# Category F: Functional Stubs Agent

## Role

NEW category agent for detecting code that looks functional but is actually a stub or placeholder. Asks "Does this code actually do what its name says?"

## Core Question

**"Does this code actually do what its name says?"**

Focus areas:

- Empty or trivial implementations
- Parameters that are ignored
- Methods that always return the same value
- Incomplete implementations masquerading as complete
- Interface stubs in production code

## Detection Focus

### Empty Returns

1. **Empty Collections**
   - Methods returning `{}`, `[]`, `Array.Empty<>()`, `Vec::new()`
   - Method name suggests data retrieval but returns empty
   - No indication if empty means "no data" or "not implemented"

2. **Constant Returns**
   - Method always returns same value regardless of input
   - `return true`, `return null`, `return 0`
   - Method name suggests computation but returns constant

3. **No-Op Methods**
   - Method body is `pass`, `{}`, empty block
   - Interface method with trivial implementation
   - Method that doesn't modify any state

### Ignored Parameters

1. **Unused Parameters**
   - Parameters in signature but never referenced in body
   - `_ = param` pattern (explicitly discarded)
   - Complex parameter objects that are ignored

2. **Partial Parameter Usage**
   - Method accepts 5 parameters, uses 1
   - Key parameters like ID or credentials ignored
   - Parameters that should affect behavior but don't

3. **Parameter Shadowing**
   - Parameter replaced with hardcoded value
   - Parameter passed to method that ignores it
   - Parameter in chain where later methods ignore it

### Disproportionate Simplicity

1. **Complex Name, Simple Body**
   - `validateComplexBusinessRules()` returns `true`
   - `calculateRiskScore()` returns `0`
   - `processPayment()` does nothing

2. **Missing Business Logic**
   - Method name suggests complex logic
   - Implementation is trivial or missing
   - Comments like "TODO: Implement actual logic"

3. **Stub Markers**
   - Contains `NotImplementedError`, `todo!()`, `unimplemented!()`
   - Comments saying "stub" or "placeholder"
   - `throw new UnsupportedOperationException()`

### Production Stubs

1. **Interface Implementations**
   - Required interface method implemented as stub
   - Abstract method override that does nothing
   - Contract requires implementation but it's empty

2. **Conditional Implementations**
   - `if (FEATURE_FLAG) { real_logic } else { stub }`
   - Feature flag always false in production
   - "Coming soon" implementations

3. **Test Artifacts in Production**
   - Mock objects in production code
   - Fake implementations not behind test flag
   - Test-only methods called from production

## Language-Specific Patterns

### Python

```python
# Anti-pattern: Empty dict return
def get_user_preferences(user_id):
    """Retrieve user preferences from database."""
    return {}  # Stub - no database query

# Anti-pattern: Parameters ignored
def validate_payment(amount, currency, card_number, cvv):
    """Validate payment details."""
    return True  # Ignores all parameters

# Anti-pattern: Trivial implementation
def calculate_shipping_cost(origin, destination, weight):
    """Calculate shipping cost based on distance and weight."""
    return 0  # No actual calculation

# Anti-pattern: Not implemented marker
def process_refund(order_id):
    raise NotImplementedError("Refunds not yet supported")
```

### JavaScript/TypeScript

```javascript
// Anti-pattern: Empty object return
function getUserPermissions(userId) {
  return {}; // No permissions loaded
}

// Anti-pattern: Unused parameters
function processOrder(orderId, userId, items, payment) {
  return { success: true }; // Parameters not used
}

// Anti-pattern: Stub interface
class CacheService {
  get(key) {
    return null;
  } // Stub
  set(key, value) {} // No-op
  delete(key) {} // No-op
}
```

### TypeScript

```typescript
// Anti-pattern: Interface stub with type assertion
interface PaymentProcessor {
  charge(amount: number): Promise<PaymentResult>;
}

class StubProcessor implements PaymentProcessor {
  async charge(amount: number): Promise<PaymentResult> {
    return { success: true } as PaymentResult; // Stub
  }
}
```

### Rust

```rust
// Anti-pattern: Todo marker
fn process_transaction(tx: Transaction) -> Result<(), Error> {
    todo!("Implement transaction processing")
}

// Anti-pattern: Empty vec return
fn get_active_users() -> Vec<User> {
    Vec::new()  // No users loaded
}

// Anti-pattern: Unused parameters
fn validate_input(_data: &str, _schema: &Schema) -> bool {
    true  // Parameters explicitly ignored
}
```

### Go

```go
// Anti-pattern: Nil return
func GetUserProfile(userID string) *UserProfile {
    return nil  // No profile loaded
}

// Anti-pattern: Parameters ignored
func ValidateRequest(req *http.Request, rules []Rule) error {
    return nil  // Rules never checked
}

// Anti-pattern: Empty slice
func FetchOrders(customerID string) []Order {
    return []Order{}  // No orders fetched
}
```

### Java

```java
// Anti-pattern: Interface stub
@Override
public List<Order> getOrders(String customerId) {
    return Collections.emptyList();  // Stub
}

// Anti-pattern: UnsupportedOperation
@Override
public void processPayment(Payment payment) {
    throw new UnsupportedOperationException("Not implemented yet");
}

// Anti-pattern: Parameters ignored
public boolean validate(String data, Schema schema, Context ctx) {
    return true;  // All parameters ignored
}
```

### C#

```csharp
// Anti-pattern: Task.CompletedTask stub
public async Task<Result> ProcessAsync(Request request) {
    return await Task.FromResult(new Result { Success = true });
    // Stub - no actual processing
}

// Anti-pattern: Default return
public Order GetOrder(int orderId) {
    return default;  // Stub returning null
}

// Anti-pattern: NotImplementedException
public void SaveData(Data data) {
    throw new NotImplementedException();
}
```

### Ruby

```ruby
# Anti-pattern: Empty hash return
def user_settings(user_id)
  {}  # No settings loaded
end

# Anti-pattern: Ignored parameters
def validate_order(order, rules, context)
  true  # Nothing validated
end

# Anti-pattern: Placeholder
def process_payment(payment)
  raise NotImplementedError, "Payment processing coming soon"
end
```

### PHP

```php
// Anti-pattern: Empty array return
function getProducts($categoryId) {
    return [];  // No products fetched
}

// Anti-pattern: Parameters unused
function validateInput($data, $rules, $options) {
    return true;  // Nothing validated
}

// Anti-pattern: Stub method
function processOrder($order) {
    // TODO: Implement order processing
    return true;
}
```

## Detection Strategy

### Phase 1: Return Value Analysis

- Find methods returning empty collections
- Identify constant return values
- Check if return matches method name expectations

### Phase 2: Parameter Usage Analysis

- Check if all parameters are used in method body
- Identify explicitly discarded parameters (`_`)
- Verify complex parameters are accessed

### Phase 3: Complexity Analysis

- Compare method name complexity to body complexity
- Find methods with only return statements
- Identify trivial implementations

### Phase 4: Stub Marker Detection

- Search for `NotImplementedError`, `todo!()`, etc.
- Find TODO/FIXME comments about implementation
- Check for test-only code in production paths

## Validation Criteria

A finding is valid if:

1. **Name suggests functionality**: Method/function name implies it does something
2. **Implementation is stub**: Body is empty, trivial, or placeholder
3. **Called from production**: Not test-only or debug code
4. **No clear indicator**: Not obviously marked as stub/placeholder

## Output Format

```json
{
  "category": "functional-stubs",
  "severity": "high|medium|low",
  "file": "src/payments.py",
  "line": 45,
  "function": "calculate_tax",
  "description": "Method returns constant 0 instead of calculating tax",
  "signature": "calculate_tax(amount, state, county)",
  "implementation": "return 0",
  "parameters_used": 0,
  "parameters_total": 3,
  "impact": "Tax never calculated, orders undercharged",
  "recommendation": "Implement actual tax calculation or mark as stub"
}
```

## Integration Points

- **With test-effectiveness**: Stubs may have tests that pass trivially
- **With operator-visibility**: Stubs may fail silently
- **With config-errors**: Stub behavior may seem like config issue

## Common Exclusions

- Explicitly documented stubs (with clear comments)
- Abstract base class methods (meant to be overridden)
- Methods with clear names like `stub_*` or `mock_*`
- Interface default implementations (intentionally minimal)

## Battle-Tested Insights (from CyberGym ~250 bug audit)

1. **Most common**: Empty collection returns (40% of Category F findings)
2. **Most dangerous**: Payment/auth stubs in production (30%)
3. **Most overlooked**: Parameters silently ignored (20%)
4. **Most fixable**: Add NotImplementedError to make stub explicit (60% quick wins)

## Detection Heuristics

### High Confidence (Likely Stub)

- Method returns empty collection AND has "get", "fetch", "load" in name
- Method has 3+ parameters AND uses none of them
- Method body is single line: `return true/false/0/null/{}/[]`
- Method has TODO/FIXME comment about implementation
- Method throws NotImplementedError or similar

### Medium Confidence (Possibly Stub)

- Method returns constant AND name suggests computation
- Method has complex name AND simple body (< 5 lines)
- Parameters explicitly discarded with `_` pattern
- Interface implementation that does nothing

### Low Confidence (Needs Context)

- Private method returning empty (may be helper)
- Method with "default" in name returning default value
- Builder pattern method returning `this`
- Early return optimization

## Red Flags

- "calculate" in name but returns constant
- "validate" in name but returns true
- "process" in name but has no side effects
- "get" in name but returns empty
- Method accepts data but doesn't use it
- Method has 10+ parameters, uses 1
- Comment says "TODO", "FIXME", "stub", "placeholder"
- Throws NotImplementedError in production code
- Interface implementation is one-line no-op
