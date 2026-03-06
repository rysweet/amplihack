# Code Smell Detector Skill

A Claude Code Skill that identifies anti-patterns violating amplihack philosophy and provides specific, actionable fixes.

## Quick Start

Use this skill when:

- Reviewing code for quality issues
- Refactoring complex or tightly-coupled code
- Ensuring new modules follow amplihack philosophy
- Learning why certain patterns are problematic
- Training team members on code quality

## What It Detects

1. **Over-Abstraction** - Unnecessary base classes, interfaces, and abstraction layers
2. **Complex Inheritance** - Deep hierarchies (3+ levels), multiple inheritance issues
3. **Large Functions** - Functions over 50 lines doing multiple things
4. **Tight Coupling** - Direct dependencies, hardcoded instantiation, hidden dependencies
5. **Missing `__all__`** - Python modules without explicit public interface

## How It Works

The skill analyzes your code and:

1. Identifies specific violations of amplihack philosophy
2. Explains WHY each pattern is problematic
3. Shows BEFORE and AFTER code examples
4. Provides concrete refactoring steps
5. References philosophy principles violated

## Examples

### Over-Abstraction

**Bad Pattern**:

```python
class DataProcessor(ABC):
    @abstractmethod
    def process(self, data):
        pass

class SimpleDataProcessor(DataProcessor):
    def process(self, data):
        return data * 2
```

**Good Pattern**:

```python
def process_data(data):
    """Process data by doubling it."""
    return data * 2
```

### Complex Inheritance

**Bad Pattern**:

```python
class Entity(Base):
    pass

class TimestampedEntity(Entity):
    pass

class AuditableEntity(TimestampedEntity):
    pass

class User(AuditableEntity):
    pass
```

**Good Pattern**:

```python
class User:
    def __init__(self, storage, timestamp_service, audit_log):
        self.storage = storage
        self.timestamps = timestamp_service
        self.audit = audit_log
```

### Large Functions

**Bad Pattern**:

```python
def process_user(user_dict, validate=True, save=True, notify=True, log=True):
    if validate:
        # validation logic (20 lines)
    if save:
        # save logic (15 lines)
    if notify:
        # email logic (10 lines)
    if log:
        # logging logic (10 lines)
    # ... more mixed concerns
```

**Good Pattern**:

```python
def validate_user(user_dict):
    """Validate user data."""
    # 5 lines of focused validation

def create_user(user_dict):
    """Create user from data."""
    # 5 lines of focused creation

def process_user(user_dict):
    """Orchestrate workflow."""
    validate_user(user_dict)
    user = create_user(user_dict)
    db.save(user)
    notify_user(user)
    log_creation(user)
```

### Tight Coupling

**Bad Pattern**:

```python
class UserService:
    def create_user(self, name, email):
        db = Database()  # Hardcoded dependency
        user = db.save_user(name, email)
        email_service = EmailService()  # Hardcoded dependency
        email_service.send(email, "Welcome!")
        return user
```

**Good Pattern**:

```python
class UserService:
    def __init__(self, db, email_service):
        self.db = db
        self.email_service = email_service

    def create_user(self, name, email):
        user = self.db.save_user(name, email)
        self.email_service.send(email, "Welcome!")
        return user
```

### Missing `__all__`

**Bad Pattern**:

```python
# module/__init__.py
from .core import process_data, _internal_helper
from .utils import validate_input, LOG_LEVEL
# Unclear what users should import
```

**Good Pattern**:

```python
# module/__init__.py
from .core import process_data
from .utils import validate_input

__all__ = ['process_data', 'validate_input']
# Crystal clear public interface
```

## Core Philosophy

This skill ensures code follows amplihack's key principles:

- **Ruthless Simplicity**: Every abstraction must justify its existence
- **Modular Design**: Self-contained modules with clear connection points (bricks & studs)
- **Zero-BS Implementation**: Only working code, no stubs or placeholders
- **Single Responsibility**: Each function/class does ONE thing well

## Philosophy Alignment

Each code smell detected:

- Violates one or more amplihack principles
- Creates unnecessary complexity
- Reduces testability or maintainability
- Makes code harder to understand or modify

## Best Practices

When using this skill:

1. **Be Constructive** - Frame findings as learning opportunities
2. **Provide Context** - Explain which philosophy principle is violated
3. **Show Examples** - BEFORE and AFTER code samples
4. **Suggest Fixes** - Concrete refactoring steps
5. **Prioritize** - List smells by severity and impact

## Common Fixes Summary

| Smell               | Root Cause          | Quick Fix                    |
| ------------------- | ------------------- | ---------------------------- |
| Over-Abstraction    | "Future-proofing"   | Delete the abstraction layer |
| Complex Inheritance | Code reuse attempt  | Use composition instead      |
| Large Functions     | Mixed concerns      | Extract helper functions     |
| Tight Coupling      | Hidden dependencies | Use dependency injection     |
| Missing `__all__`   | Unclear API         | Explicitly define exports    |

## Integration

Use this skill during:

- **Code Review**: Catch issues before merge
- **Refactoring**: Identify improvement opportunities
- **Design Review**: Ensure architecture aligns with philosophy
- **Onboarding**: Help new team members learn patterns
- **Architecture Discussion**: Guide design decisions

## Resources

- **Full Philosophy**: See `~/.amplihack/.claude/context/PHILOSOPHY.md`
- **Design Patterns**: See `~/.amplihack/.claude/context/PATTERNS.md`
- **Detailed SKILL.md**: Full detection rules and analysis process

## Next Steps

1. Use `/skill code-smell-detector` when reviewing code
2. Apply detected fixes to improve code quality
3. Share examples with team to build shared understanding
4. Reference philosophy docs when discussing findings
5. Create custom rules if needed for your project

---

Remember: This skill helps maintain quality and teach philosophy - use it to help, not criticize.
