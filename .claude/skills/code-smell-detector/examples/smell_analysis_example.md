# Code Smell Analysis - Real Examples

This document shows how the code-smell-detector skill analyzes real code patterns.

## Example 1: User Service Module Analysis

### Code Under Review

```python
# user_service.py
from abc import ABC, abstractmethod
from datetime import datetime

class UserProcessor(ABC):
    @abstractmethod
    def process(self, user):
        pass

class BasicUserProcessor(UserProcessor):
    def process(self, user):
        user.processed = True
        return user

class UserService:
    def __init__(self):
        self.processor = BasicUserProcessor()

    def create_user_and_notify(self, name, email, phone, country, notify=True,
                                validate=True, log=True, audit=True):
        if validate:
            if not name or len(name) < 2:
                raise ValueError("Name too short")
            if not email or '@' not in email:
                raise ValueError("Invalid email")
            if not phone or len(phone) < 10:
                raise ValueError("Invalid phone")
            if not country or len(country) < 2:
                raise ValueError("Invalid country")

        if log:
            print(f"Creating user: {name}")

        user = {
            'name': name,
            'email': email,
            'phone': phone,
            'country': country,
            'created_at': datetime.now(),
        }

        if audit:
            print(f"AUDIT: User created at {datetime.now()}")

        processed_user = self.processor.process(user)

        if notify:
            email_service = EmailService()
            email_service.send(email, f"Welcome {name}!")

        if log:
            print(f"User {name} created successfully")

        return processed_user

class EmailService:
    def send(self, email, message):
        print(f"Email sent to {email}: {message}")
```

### Smell Analysis

#### Smell 1: Over-Abstraction

**Severity**: MAJOR
**Location**: Lines 5-14 (`UserProcessor` ABC)

**Issue**:

- Abstract base class with exactly ONE concrete implementation
- No indication multiple implementations will ever be needed
- Adds unnecessary layer of indirection

**Philosophy Violated**: Ruthless Simplicity - "Every abstraction must justify its existence"

**Fix**:

```python
# BEFORE (has abstraction)
class UserProcessor(ABC):
    @abstractmethod
    def process(self, user):
        pass

class BasicUserProcessor(UserProcessor):
    def process(self, user):
        user.processed = True
        return user

# AFTER (direct implementation)
def process_user(user):
    """Mark user as processed."""
    user.processed = True
    return user
```

#### Smell 2: Large Function

**Severity**: CRITICAL
**Location**: Lines 23-62 (`create_user_and_notify`)

**Issue**:

- 40+ lines doing 7 different things
- Mixed concerns: validation, logging, auditing, processing, notification
- Hard to test each concern in isolation
- Difficult to modify one aspect without affecting others

**Philosophy Violated**: Single Responsibility - "Each function does ONE thing well"

**Fix**:

```python
# BEFORE - One big function doing everything
def create_user_and_notify(self, name, email, phone, country, notify=True,
                            validate=True, log=True, audit=True):
    # 40 lines of mixed concerns

# AFTER - Separated concerns
def validate_user_data(name, email, phone, country):
    """Validate all user fields."""
    if not name or len(name) < 2:
        raise ValueError("Name too short")
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    if not phone or len(phone) < 10:
        raise ValueError("Invalid phone")
    if not country or len(country) < 2:
        raise ValueError("Invalid country")

def create_user_dict(name, email, phone, country):
    """Create user data structure."""
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'country': country,
        'created_at': datetime.now(),
    }

def create_user_and_notify(self, name, email, phone, country,
                          notify=True, validate=True, log=True, audit=True):
    """Orchestrate user creation workflow."""
    if validate:
        validate_user_data(name, email, phone, country)

    if log:
        print(f"Creating user: {name}")

    user = create_user_dict(name, email, phone, country)

    if audit:
        print(f"AUDIT: User created at {datetime.now()}")

    processed_user = process_user(user)

    if notify:
        self.email_service.send(user['email'], f"Welcome {name}!")

    if log:
        print(f"User {name} created successfully")

    return processed_user
```

#### Smell 3: Tight Coupling

**Severity**: MAJOR
**Location**: Lines 37-39 (hardcoded EmailService)

**Issue**:

- `EmailService` instantiated inside method
- Can't test without actually sending emails
- Can't swap implementations
- Hidden dependency

**Philosophy Violated**: Modular Design - "Dependencies should be explicit and injected"

**Fix**:

```python
# BEFORE - Hidden dependency
class UserService:
    def __init__(self):
        self.processor = BasicUserProcessor()

    def create_user_and_notify(self, ...):
        # ...
        email_service = EmailService()  # Where'd this come from?
        email_service.send(email, f"Welcome {name}!")

# AFTER - Explicit dependencies
class UserService:
    def __init__(self, email_service):
        self.email_service = email_service

    def create_user_and_notify(self, ...):
        # ...
        self.email_service.send(user['email'], f"Welcome {name}!")

# Usage:
service = UserService(email_service=SMTPEmailService())
```

#### Smell 4: Missing `__all__`

**Severity**: MINOR
**Location**: Module level (entire file)

**Issue**:

- No explicit public interface
- Users don't know what to import
- Internal classes might be imported by mistake

**Philosophy Violated**: Modular Design (Studs) - "Clear public interface"

**Fix**:

```python
# Add at module level
__all__ = ['UserService', 'validate_user_data', 'create_user_dict']

# This tells users:
# - UserService is the main entry point
# - These helpers are available if needed
# - EmailService and process_user are internal
```

### Refactored Code (All Smells Fixed)

```python
# user_service.py
"""User management and notification service."""

from datetime import datetime

__all__ = ['UserService']

# Validation
def validate_user_data(name, email, phone, country):
    """Validate all user fields."""
    if not name or len(name) < 2:
        raise ValueError("Name too short")
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    if not phone or len(phone) < 10:
        raise ValueError("Invalid phone")
    if not country or len(country) < 2:
        raise ValueError("Invalid country")

# User creation
def create_user_dict(name, email, phone, country):
    """Create user data structure."""
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'country': country,
        'created_at': datetime.now(),
    }

def process_user(user):
    """Mark user as processed."""
    user['processed'] = True
    return user

# Service
class UserService:
    """Manage user creation with notifications."""

    def __init__(self, email_service):
        """Initialize with email service dependency."""
        self.email_service = email_service

    def create_user_and_notify(self, name, email, phone, country,
                              notify=True, validate=True, log=True, audit=True):
        """Orchestrate user creation workflow."""
        if validate:
            validate_user_data(name, email, phone, country)

        if log:
            print(f"Creating user: {name}")

        user = create_user_dict(name, email, phone, country)

        if audit:
            print(f"AUDIT: User created at {datetime.now()}")

        processed_user = process_user(user)

        if notify:
            self.email_service.send(user['email'], f"Welcome {name}!")

        if log:
            print(f"User {name} created successfully")

        return processed_user
```

### Summary of Improvements

| Smell             | Severity | Fix                                                                       |
| ----------------- | -------- | ------------------------------------------------------------------------- |
| Over-Abstraction  | MAJOR    | Removed `UserProcessor` ABC, use direct `process_user()`                  |
| Large Function    | CRITICAL | Split into `validate_user_data()`, `create_user_dict()`, `process_user()` |
| Tight Coupling    | MAJOR    | Inject `email_service` as constructor parameter                           |
| Missing `__all__` | MINOR    | Added explicit `__all__ = ['UserService']`                                |

### Benefits of Refactored Code

1. **Simpler**: No unnecessary abstractions, clear flow
2. **Testable**: Each function can be tested independently
3. **Flexible**: Easy to swap email implementations
4. **Maintainable**: Clear responsibilities for each function
5. **Philosophy-Aligned**: Follows ruthless simplicity and modular design

---

## Example 2: Quick Analysis Template

When reviewing code, use this format:

```
SMELL: [Name]
SEVERITY: [CRITICAL/MAJOR/MINOR]
LOCATION: [File:Line]
PHILOSOPHY VIOLATED: [Which principle]

ISSUE:
[Explain what's wrong and why]

EXAMPLE:
[Show the problematic code]

FIX:
[Show the fixed code]

IMPACT:
[Why this matters for the project]
```

---

## Example 3: Before & After Gallery

### Pattern 1: Composition Over Inheritance

```python
# BEFORE: 3-level inheritance
class Entity: pass
class TimestampedEntity(Entity): pass
class User(TimestampedEntity): pass

# AFTER: Composition
class User:
    def __init__(self, storage, timestamps):
        self.storage = storage
        self.timestamps = timestamps
```

### Pattern 2: Direct Functions Over Utility Classes

```python
# BEFORE: Utility class
class StringUtils:
    @staticmethod
    def clean(s): return s.strip().lower()

# AFTER: Direct function
def clean_string(s): return s.strip().lower()
```

### Pattern 3: Dependency Injection

```python
# BEFORE: Hidden dependency
def fetch_user(id):
    db = Database()
    return db.query(id)

# AFTER: Explicit dependency
def fetch_user(id, db):
    return db.query(id)
```

### Pattern 4: Split God Functions

```python
# BEFORE: 100 line function
def complex_workflow(data, ...): pass

# AFTER: Orchestrated workflow
def complex_workflow(data):
    step1(data)
    step2(data)
    step3(data)
```

---

## Using This Analysis

1. **Learn**: Study the examples to understand each smell
2. **Apply**: Use these patterns when reviewing your code
3. **Teach**: Share examples with team members
4. **Measure**: Track improvements over time

Remember: The goal is continuous improvement and learning, not perfection.
