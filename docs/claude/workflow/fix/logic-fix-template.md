# Logic Fix Template

**Usage**: 10% of all fixes - Algorithm bugs, edge case handling, state management, business logic errors

## Problem Pattern Recognition

### Triggers

- Incorrect calculation results
- Wrong conditional logic
- State inconsistencies
- Edge case failures
- Business rule violations
- Algorithm inefficiencies
- Data flow problems

### Error Indicators

```bash
# Common logic error patterns
"unexpected result"
"assertion failed"
"wrong output for input"
"edge case not handled"
"state corruption"
"business rule violation"
"infinite loop"
"race condition"
```

## Quick Assessment (60 seconds)

### Step 1: Error Classification

```python
# Logic error types:
# - Calculation errors (math, formulas)
# - Conditional logic (if/else, switches)
# - Loop logic (iteration, termination)
# - State management (object state, global state)
# - Edge cases (boundary conditions)
# - Business logic (domain rules)
```

### Step 2: Impact Assessment

```bash
# Scope of the logic error:
# - Single function/method
# - Module/class
# - Cross-component
# - System-wide behavior
```

### Step 3: Reproducibility Check

```python
# Can we reproduce the error?
# - Consistent reproduction steps
# - Input data that triggers error
# - Environment conditions
# - Timing dependencies
```

## Solution Steps by Logic Type

### Calculation/Mathematical Logic

```python
# Before (incorrect calculation)
def calculate_compound_interest(principal, rate, time):
    return principal * rate * time  # Wrong formula

# After (correct calculation)
def calculate_compound_interest(principal, rate, time, compound_frequency=1):
    return principal * (1 + rate/compound_frequency) ** (compound_frequency * time)

# Add validation
def calculate_compound_interest(principal, rate, time, compound_frequency=1):
    if principal <= 0:
        raise ValueError("Principal must be positive")
    if rate < 0:
        raise ValueError("Rate cannot be negative")
    if time < 0:
        raise ValueError("Time cannot be negative")

    return principal * (1 + rate/compound_frequency) ** (compound_frequency * time)
```

### Conditional Logic Fixes

```python
# Before (incorrect conditions)
def determine_grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"  # Missing validation for negative scores

# After (robust conditional logic)
def determine_grade(score):
    if not isinstance(score, (int, float)):
        raise TypeError("Score must be a number")
    if score < 0 or score > 100:
        raise ValueError("Score must be between 0 and 100")

    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"
```

### Loop Logic Issues

```python
# Before (potential infinite loop)
def find_first_match(items, condition):
    i = 0
    while i < len(items):
        if condition(items[i]):
            return items[i]
        # Missing increment - infinite loop!

# After (safe loop logic)
def find_first_match(items, condition):
    for item in items:  # Use for loop when possible
        if condition(item):
            return item
    return None  # Explicit handling of no match

# Alternative with while loop
def find_first_match(items, condition):
    i = 0
    while i < len(items):
        if condition(items[i]):
            return items[i]
        i += 1  # Don't forget increment
    return None
```

### State Management Fixes

```python
# Before (state corruption)
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        temp = self.count
        # Some other operations that might fail
        risky_operation()
        self.count = temp + 1  # State can be corrupted if risky_operation fails

# After (atomic state updates)
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        # Do risky operations first
        risky_operation()
        # Then update state atomically
        self.count += 1

# Or with rollback capability
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        old_count = self.count
        try:
            risky_operation()
            self.count += 1
        except Exception:
            self.count = old_count  # Rollback on failure
            raise
```

### Edge Case Handling

```python
# Before (missing edge cases)
def divide_list(items, chunk_size):
    result = []
    for i in range(0, len(items), chunk_size):
        result.append(items[i:i+chunk_size])
    return result

# After (comprehensive edge case handling)
def divide_list(items, chunk_size):
    if not items:
        return []  # Handle empty list
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")
    if chunk_size >= len(items):
        return [items.copy()]  # Single chunk case

    result = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i+chunk_size]
        result.append(chunk)
    return result
```

### Business Logic Validation

```python
# Before (incomplete business rules)
def process_order(order):
    total = sum(item.price * item.quantity for item in order.items)
    order.total = total
    return order

# After (complete business logic)
def process_order(order):
    # Validate business rules
    if not order.items:
        raise ValueError("Order must contain at least one item")

    if order.customer.status == "blocked":
        raise ValueError("Cannot process order for blocked customer")

    # Calculate total with business rules
    subtotal = sum(item.price * item.quantity for item in order.items)

    # Apply discounts
    discount = calculate_discount(order.customer, subtotal)
    discounted_total = subtotal - discount

    # Apply taxes
    tax = calculate_tax(discounted_total, order.customer.location)
    total = discounted_total + tax

    # Validate business constraints
    if total > order.customer.credit_limit:
        raise ValueError("Order exceeds customer credit limit")

    order.subtotal = subtotal
    order.discount = discount
    order.tax = tax
    order.total = total
    return order
```

## Validation Steps

### 1. Unit Testing Logic

```python
# Test normal cases
def test_calculate_interest_normal():
    result = calculate_compound_interest(1000, 0.05, 2)
    expected = 1000 * (1.05) ** 2
    assert abs(result - expected) < 0.01

# Test edge cases
def test_calculate_interest_edge_cases():
    # Zero principal
    assert calculate_compound_interest(0, 0.05, 2) == 0

    # Zero rate
    assert calculate_compound_interest(1000, 0, 2) == 1000

    # Zero time
    assert calculate_compound_interest(1000, 0.05, 0) == 1000

# Test error cases
def test_calculate_interest_errors():
    with pytest.raises(ValueError):
        calculate_compound_interest(-1000, 0.05, 2)
```

### 2. Integration Testing

```python
# Test business logic in context
def test_order_processing_workflow():
    customer = create_test_customer()
    order = create_test_order(customer)

    processed_order = process_order(order)

    assert processed_order.total > 0
    assert processed_order.total <= customer.credit_limit
    assert processed_order.tax >= 0
```

### 3. Property-Based Testing

```python
# Use hypothesis for property testing
from hypothesis import given, strategies as st

@given(st.floats(min_value=0.01, max_value=1000000),
       st.floats(min_value=0, max_value=1),
       st.floats(min_value=0, max_value=50))
def test_interest_properties(principal, rate, time):
    result = calculate_compound_interest(principal, rate, time)

    # Properties that should always hold
    assert result >= principal  # Interest never negative
    if rate > 0 and time > 0:
        assert result > principal  # Positive growth
```

## Debugging Techniques

### Add Debugging Information

```python
# Before (opaque logic)
def complex_algorithm(data):
    result = process_step1(data)
    result = process_step2(result)
    result = process_step3(result)
    return result

# After (debug-friendly)
def complex_algorithm(data, debug=False):
    if debug:
        print(f"Input: {data}")

    result = process_step1(data)
    if debug:
        print(f"After step 1: {result}")

    result = process_step2(result)
    if debug:
        print(f"After step 2: {result}")

    result = process_step3(result)
    if debug:
        print(f"After step 3: {result}")

    return result
```

### Use Assertions for Invariants

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1

    while left <= right:
        # Assert invariants
        assert 0 <= left < len(arr)
        assert 0 <= right < len(arr)
        assert left <= right + 1

        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1
```

## Integration Points

### With Fix Agent

- Use DIAGNOSTIC mode for complex logic issues
- Use COMPREHENSIVE mode for business logic overhauls
- Escalate algorithm design to architect agent

### With Main Workflow

- Apply during Step 5 (Implementation)
- Use in Step 6 (Refactor and Simplify)
- Integrate with Step 11 (Review feedback)

### With Other Agents

- **Architect agent**: For algorithm design issues
- **Tester agent**: For comprehensive test coverage
- **Reviewer agent**: For logic validation
- **Optimizer agent**: For performance improvements

## Quick Reference

### 15-Minute Fix Checklist

- [ ] Identify the specific logic error
- [ ] Reproduce the error consistently
- [ ] Trace through the logic step by step
- [ ] Identify the root cause
- [ ] Implement fix with validation
- [ ] Add tests for the edge case
- [ ] Verify fix doesn't break other functionality

### Common Debugging Steps

```python
# Add logging
import logging
logging.debug(f"Variable state: {variable}")

# Add breakpoints (for interactive debugging)
import pdb; pdb.set_trace()

# Add assertions
assert len(items) > 0, "Items list should not be empty"

# Print intermediate values
print(f"DEBUG: value at step {i}: {value}")
```

## Success Patterns

### High-Success Scenarios

- Simple calculation errors (85% success)
- Basic conditional logic (80% success)
- Missing validation (90% success)
- Off-by-one errors (75% success)

### Challenging Scenarios

- Complex state management (50% success)
- Race conditions (40% success)
- Business logic edge cases (60% success)
- Algorithm optimization (45% success)

## Prevention Strategies

### Development Practices

- Write tests first (TDD)
- Use type hints for clarity
- Add comprehensive validation
- Document business rules clearly

### Code Review Focus

- Logic correctness
- Edge case coverage
- State management safety
- Business rule compliance

### Design Patterns

- Use immutable data structures when possible
- Separate business logic from presentation
- Implement proper error handling
- Use state machines for complex state

## Advanced Scenarios

### Concurrent Logic Issues

```python
import threading

class ThreadSafeCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self._count += 1

    @property
    def count(self):
        with self._lock:
            return self._count
```

### Complex Business Rules

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class OrderProcessor:
    def process(self, order: Order) -> OrderStatus:
        # Apply business rules in order
        for rule in self.get_business_rules():
            result = rule.apply(order)
            if result == OrderStatus.REJECTED:
                return result

        return OrderStatus.APPROVED

    def get_business_rules(self) -> List[BusinessRule]:
        return [
            CreditLimitRule(),
            InventoryRule(),
            CustomerStatusRule(),
            # Add more rules as needed
        ]
```

Remember: Logic errors often indicate missing requirements or unclear specifications. Fix the bug but also consider if the requirements need clarification or documentation.
