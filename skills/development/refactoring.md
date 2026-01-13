# Refactoring

Systematic code improvement patterns while preserving behavior.

## When to Use

- Code is difficult to understand or modify
- Adding features requires touching many files
- Tests are difficult to write for existing code
- Performance issues from poor structure
- Tech debt is slowing development
- During code review when suggesting improvements

## When NOT to Refactor

### Stop Signs

```
[ ] No tests exist (write tests first!)
[ ] Deadline is imminent (ship, then refactor)
[ ] You don't understand the code yet (learn first)
[ ] The code works and rarely changes (leave it alone)
[ ] You're refactoring to avoid real work (focus on value)
[ ] The system is being replaced soon (not worth it)
```

### The Rule of Three

```
1st time: Just do it (even if ugly)
2nd time: Wince and duplicate anyway
3rd time: NOW refactor

Don't over-engineer preemptively.
Only refactor when pain is real.
```

## Code Smell Detection

### Function-Level Smells

| Smell | Symptoms | Refactoring |
|-------|----------|-------------|
| Long Method | >30 lines, scrolling required | Extract Method |
| Long Parameter List | >4 parameters | Introduce Parameter Object |
| Duplicate Code | Same logic in multiple places | Extract Method/Class |
| Dead Code | Unused functions/variables | Delete it |
| Speculative Generality | "Might need this later" | Delete it |

### Class-Level Smells

| Smell | Symptoms | Refactoring |
|-------|----------|-------------|
| God Class | >500 lines, many responsibilities | Extract Class |
| Data Class | Only getters/setters | Move methods to class |
| Feature Envy | Method uses other class more | Move Method |
| Lazy Class | Class does almost nothing | Inline Class |
| Parallel Inheritance | Change one hierarchy, must change another | Collapse Hierarchy |

### Architecture Smells

| Smell | Symptoms | Refactoring |
|-------|----------|-------------|
| Shotgun Surgery | One change = many file edits | Move related code together |
| Divergent Change | Class changes for unrelated reasons | Extract Class |
| Inappropriate Intimacy | Classes know too much about each other | Move/Hide methods |
| Message Chains | a.getB().getC().getD() | Hide Delegate |

## Extract Method Pattern

### Before

```python
def process_order(order):
    # Validate order
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")
    for item in order.items:
        if item.quantity <= 0:
            raise ValueError(f"Invalid quantity for {item.name}")
    
    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in order.items)
    tax = subtotal * 0.1
    shipping = 5.99 if subtotal < 50 else 0
    total = subtotal + tax + shipping
    
    # Save order
    order.subtotal = subtotal
    order.tax = tax
    order.shipping = shipping
    order.total = total
    order.status = "processed"
    db.save(order)
    
    # Send confirmation
    email = create_email(order.customer_email)
    email.subject = f"Order {order.id} confirmed"
    email.body = f"Your order total is ${total:.2f}"
    email_service.send(email)
    
    return order
```

### After

```python
def process_order(order):
    validate_order(order)
    calculate_totals(order)
    save_order(order)
    send_confirmation(order)
    return order

def validate_order(order):
    """Validate order has valid items and totals."""
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")
    for item in order.items:
        if item.quantity <= 0:
            raise ValueError(f"Invalid quantity for {item.name}")

def calculate_totals(order):
    """Calculate and set order totals."""
    order.subtotal = sum(item.price * item.quantity for item in order.items)
    order.tax = order.subtotal * TAX_RATE
    order.shipping = 0 if order.subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    order.total = order.subtotal + order.tax + order.shipping

def save_order(order):
    """Persist order to database."""
    order.status = "processed"
    db.save(order)

def send_confirmation(order):
    """Send order confirmation email."""
    email = create_email(order.customer_email)
    email.subject = f"Order {order.id} confirmed"
    email.body = f"Your order total is ${order.total:.2f}"
    email_service.send(email)
```

## Extract Class Pattern

### Before

```python
class User:
    def __init__(self, name, email, street, city, state, zip_code,
                 card_number, card_expiry, card_cvv):
        self.name = name
        self.email = email
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.card_number = card_number
        self.card_expiry = card_expiry
        self.card_cvv = card_cvv
    
    def get_full_address(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"
    
    def validate_card(self):
        # Card validation logic
        pass
    
    def charge_card(self, amount):
        # Charging logic
        pass
```

### After

```python
@dataclass
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    
    def format(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"

@dataclass
class PaymentMethod:
    card_number: str
    expiry: str
    cvv: str
    
    def validate(self) -> bool:
        # Card validation logic
        pass
    
    def charge(self, amount: Decimal) -> bool:
        # Charging logic
        pass

@dataclass
class User:
    name: str
    email: str
    address: Address
    payment: PaymentMethod
```

## Move Method Pattern

### Before (Feature Envy)

```python
class Report:
    def calculate_total(self, order):
        # This method uses Order more than Report
        subtotal = sum(item.price * item.quantity for item in order.items)
        discount = order.discount_percent * subtotal / 100
        tax = (subtotal - discount) * order.tax_rate
        return subtotal - discount + tax
```

### After

```python
class Order:
    def calculate_total(self) -> Decimal:
        """Total belongs with Order, not Report."""
        subtotal = sum(item.price * item.quantity for item in self.items)
        discount = self.discount_percent * subtotal / 100
        tax = (subtotal - discount) * self.tax_rate
        return subtotal - discount + tax

class Report:
    def get_order_total(self, order):
        return order.calculate_total()  # Delegate to Order
```

## Replace Conditional with Polymorphism

### Before

```python
def calculate_shipping(order):
    if order.shipping_type == "standard":
        if order.total < 50:
            return 5.99
        return 0
    elif order.shipping_type == "express":
        return 15.99
    elif order.shipping_type == "overnight":
        return 25.99
    elif order.shipping_type == "pickup":
        return 0
    else:
        raise ValueError(f"Unknown shipping: {order.shipping_type}")
```

### After

```python
from abc import ABC, abstractmethod

class ShippingStrategy(ABC):
    @abstractmethod
    def calculate(self, order) -> Decimal:
        pass

class StandardShipping(ShippingStrategy):
    def calculate(self, order) -> Decimal:
        return Decimal("0") if order.total >= 50 else Decimal("5.99")

class ExpressShipping(ShippingStrategy):
    def calculate(self, order) -> Decimal:
        return Decimal("15.99")

class OvernightShipping(ShippingStrategy):
    def calculate(self, order) -> Decimal:
        return Decimal("25.99")

class PickupShipping(ShippingStrategy):
    def calculate(self, order) -> Decimal:
        return Decimal("0")

# Usage
SHIPPING_STRATEGIES = {
    "standard": StandardShipping(),
    "express": ExpressShipping(),
    "overnight": OvernightShipping(),
    "pickup": PickupShipping(),
}

def calculate_shipping(order):
    strategy = SHIPPING_STRATEGIES.get(order.shipping_type)
    if not strategy:
        raise ValueError(f"Unknown shipping: {order.shipping_type}")
    return strategy.calculate(order)
```

## Simplification Techniques

### Replace Nested Conditionals with Guard Clauses

```python
# Before
def get_payment_amount(employee):
    if employee.is_separated:
        result = separated_amount(employee)
    else:
        if employee.is_retired:
            result = retired_amount(employee)
        else:
            result = normal_amount(employee)
    return result

# After
def get_payment_amount(employee):
    if employee.is_separated:
        return separated_amount(employee)
    if employee.is_retired:
        return retired_amount(employee)
    return normal_amount(employee)
```

### Decompose Conditional

```python
# Before
if date.before(SUMMER_START) or date.after(SUMMER_END):
    charge = quantity * winter_rate + winter_service_charge
else:
    charge = quantity * summer_rate

# After
def is_winter(date):
    return date.before(SUMMER_START) or date.after(SUMMER_END)

def winter_charge(quantity):
    return quantity * WINTER_RATE + WINTER_SERVICE_CHARGE

def summer_charge(quantity):
    return quantity * SUMMER_RATE

charge = winter_charge(quantity) if is_winter(date) else summer_charge(quantity)
```

### Consolidate Duplicate Conditionals

```python
# Before
def disability_amount(employee):
    if employee.seniority < 2:
        return 0
    if employee.months_disabled > 12:
        return 0
    if employee.is_part_time:
        return 0
    return compute_disability(employee)

# After
def disability_amount(employee):
    if is_not_eligible_for_disability(employee):
        return 0
    return compute_disability(employee)

def is_not_eligible_for_disability(employee):
    return (employee.seniority < 2 or 
            employee.months_disabled > 12 or 
            employee.is_part_time)
```

## Refactoring Workflow

### Safe Refactoring Process

```
1. VERIFY TESTS PASS
   - Run full test suite
   - Add tests if coverage is low
   - Never refactor without tests

2. MAKE ONE SMALL CHANGE
   - Single responsibility per commit
   - Keep changes reversible
   - Don't mix refactoring with features

3. RUN TESTS
   - Must pass after each change
   - If tests fail, revert immediately
   - Don't debug refactoring failures

4. COMMIT
   - Small, focused commits
   - Clear commit messages
   - Easy to review and revert

5. REPEAT
   - Incremental improvement
   - Stop when good enough
   - Don't chase perfection
```

### Commit Messages for Refactoring

```bash
# Good refactoring commits
git commit -m "refactor: extract OrderValidator class"
git commit -m "refactor: rename calculate to calculate_total"
git commit -m "refactor: move shipping logic to ShippingCalculator"
git commit -m "refactor: replace if-else with strategy pattern"

# Bad (too broad)
git commit -m "refactor: major refactoring of order system"
git commit -m "cleanup"
git commit -m "refactoring"
```

## Refactoring Checklist

### Before Refactoring

```
[ ] Tests exist and pass
[ ] I understand what the code does
[ ] I have a clear goal for this refactoring
[ ] The refactoring is worth the time investment
[ ] I've communicated with the team
```

### During Refactoring

```
[ ] Making one small change at a time
[ ] Running tests after each change
[ ] Committing frequently
[ ] Not adding new features
[ ] Keeping changes reversible
```

### After Refactoring

```
[ ] All tests still pass
[ ] Code is actually simpler/clearer
[ ] No behavior has changed
[ ] Performance is acceptable
[ ] Changes are documented if significant
```

## Common Refactoring Mistakes

### Mistake: Big Bang Refactoring

```
Problem: Rewriting everything at once
Result: Weeks of work, merge conflicts, bugs

Fix: Incremental refactoring
- Small, focused changes
- Merge frequently
- Keep system working
```

### Mistake: Refactoring Without Tests

```
Problem: No safety net for changes
Result: Introducing bugs, behavior changes

Fix: Write characterization tests first
- Test current behavior (even if wrong)
- Then refactor safely
- Then fix behavior if needed
```

### Mistake: Mixing Refactoring with Features

```
Problem: Hard to review, test, revert
Result: Bugs from mixed changes

Fix: Separate commits/PRs
- PR 1: Refactoring (no behavior change)
- PR 2: New feature (uses refactored code)
```
