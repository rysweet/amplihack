# Philosophy Guardian: Quick Reference

## When to Use This Skill

| Scenario | Description | Output |
|----------|-------------|--------|
| PR Review | Ensure code aligns with philosophy | Philosophy assessment with recommendations |
| Refactoring Check | Verify simplification maintains principles | Comparison of old vs new code |
| Design Decision | Challenge architectural choices | Trade-off analysis with philosophy lens |
| Module Review | Check brick & studs pattern | Modularity assessment and improvements |

## The Three Pillars

### 1. Ruthless Simplicity
```
Check for:
- Over-abstraction (unnecessary layers)
- Unnecessary complexity
- Future-proofing (building for hypothetical futures)
- Over-use of frameworks
- Overly generic code

Question: "Is this the simplest way to solve this problem?"
```

### 2. Modular Design (Bricks & Studs)
```
Check for:
- Multiple responsibilities
- Unclear public interface
- Circular dependencies
- Tightly coupled modules
- Non-regeneratable code

Question: "Does this have ONE clear responsibility?"
```

### 3. Zero-BS Implementation
```
Check for:
- TODO comments
- Stub functions
- Dead code
- Swallowed exceptions
- Mock/fake data in production

Question: "Are all functions complete and working?"
```

## Common Violations & Fixes

| Violation | Red Flag | Fix | Philosophy |
|-----------|----------|-----|-----------|
| Over-abstraction | Abstract base class for hypothetical use | Make it concrete | Ruthless Simplicity |
| Multiple responsibilities | Service does A, B, C, D... | Split into services | Modular Design |
| TODOs in code | "TODO: implement..." | Finish or delete | Zero-BS |
| Dead code | Unused functions | Remove | Zero-BS |
| Swallowed errors | `except: pass` | Handle visibly | Zero-BS |
| Over-generic | "Flexible for any case" | Be specific | Ruthless Simplicity |

## Review Checklist

### Ruthless Simplicity Checks
- [ ] Is this the simplest solution?
- [ ] Any unnecessary abstraction?
- [ ] Building for hypothetical futures?
- [ ] Using framework features not needed?

### Modular Design Checks
- [ ] ONE clear responsibility?
- [ ] Public interface minimal and clear?
- [ ] Self-contained (tests in module)?
- [ ] Can be understood independently?
- [ ] Any circular dependencies?

### Zero-BS Implementation Checks
- [ ] All functions complete?
- [ ] Any TODO comments?
- [ ] Any NotImplementedError?
- [ ] All errors handled (not swallowed)?
- [ ] No dead code?

## Quick Examples

### Example 1: Over-Abstraction (WRONG)
```python
from abc import ABC

class AbstractHandler(ABC):  # Future-proofing - WRONG!
    def process(self, data):
        self.validate(data)
        self.transform(data)
        return self.finalize(data)

class JSONHandler(AbstractHandler):
    # implementation
```

**Why it's wrong**: Building abstract framework for handler types that don't exist. Future-proofing violates ruthless simplicity.

**Fix**: Make it concrete
```python
class JSONHandler:  # Concrete and simple - RIGHT!
    def process(self, data):
        self.validate(data)
        self.transform(data)
        return self.finalize(data)
```

### Example 2: Too Many Responsibilities (WRONG)
```python
class UserService:  # WRONG - 7 responsibilities!
    def create_user(self, data):
        # validates user
        # saves to database
        # sends email notification
        # logs event
        # updates cache
        # triggers webhook
        # generates audit trail
```

**Why it's wrong**: One class doing validation, persistence, notification, logging, caching, webhooks, AND audit. Violates brick philosophy.

**Fix**: Create separate services
```python
class UserService:  # RIGHT - one responsibility
    """Single responsibility: User data management"""
    def create_user(self, data: UserData) -> User:
        return self._save_user(data)

class EmailNotifier:
    """Single responsibility: User notifications"""
    def notify_user_created(self, user: User):
        send_email(user)

class AuditLogger:
    """Single responsibility: Audit trail"""
    def log_user_created(self, user: User):
        log_event("user.created", user.id)
```

### Example 3: Unfinished Code (WRONG)
```python
def calculate_metric(data):
    # TODO: implement this calculation
    # TODO: handle edge cases
    # TODO: add logging
    return None

def process(records):
    for record in records:
        result = calculate_metric(record)  # Crashes when None!
        process_result(result)
```

**Why it's wrong**: Function is incomplete stub. Will crash. Violates zero-BS principle.

**Fix**: Complete implementation or remove
```python
def calculate_metric(data):  # RIGHT - complete and working
    try:
        result = expensive_computation(data)
        return result if result is not None else 0
    except ValueError as e:
        log_error(f"Invalid data: {e}")
        raise
```

## Philosophy Guardian Commands

### Review a PR
```
Claude, review this PR for philosophy alignment.
[Paste PR diff or code]
```

### Review Refactoring
```
Claude, I'm refactoring this service.
Help me ensure I stay true to amplihack's philosophy.
[Paste old and new code]
```

### Challenge a Design Decision
```
Claude, I'm thinking about adding a caching layer for performance.
How does this align with our philosophy?
```

### Assess a Module
```
Claude, review this module for philosophy compliance.
[Paste module code]
```

## Response Format

Philosophy Guardian provides structured feedback:

```
## Philosophy Review: [Component Name]

### Ruthless Simplicity Assessment
[Analysis of complexity and abstraction]

Findings:
- Specific violation 1 (file:line)
- Specific violation 2 (file:line)

### Modular Design Assessment
[Analysis of responsibilities and boundaries]

Findings:
- Specific violation 1 (file:line)
- Specific violation 2 (file:line)

### Zero-BS Implementation Assessment
[Analysis of completeness and errors]

Findings:
- Specific violation 1 (file:line)
- Specific violation 2 (file:line)

### Recommended Actions
1. [Specific improvement with code example]
2. [Specific improvement with code example]
3. [Specific improvement with code example]
```

## Key Principles (One-Liners)

| Principle | Meaning |
|-----------|---------|
| KISS | Keep It Simple, Stupid |
| YAGNI | You Aren't Gonna Need It (no future-proofing) |
| SRP | Single Responsibility Principle |
| DRY | Don't Repeat Yourself |
| No TODOs | Implement or delete, never leave incomplete |
| No Stubs | Every function must work |
| No Dead Code | Remove unused code completely |
| Clear Interfaces | Public functions minimal and documented |
| Regeneratable | Can rebuild module from spec without breaking system |

## Anti-Patterns to Avoid

| Anti-Pattern | Red Flag | Philosophy Response |
|--------------|----------|-------------------|
| Future-Proofing | "We might need this later" | Build for NOW, add later if needed |
| Over-Generic | "Let's make it flexible" | Specific code is easier to adapt |
| God Class | "Service handles A, B, C, D..." | Each needs its own brick |
| Incomplete Code | "TODO: implement..." | Finish completely or remove |
| Dead Code | Unused functions | Delete completely |
| Silent Errors | `except: pass` | Handle errors visibly |
| Over-Engineering | "Just to be safe..." | Simpler is better |

## Most Common Violations Found

1. **Over-abstraction** (25%)
   - Abstract base classes for non-existent use cases
   - Generic frameworks built speculatively
   - Unnecessary layers of indirection

2. **Multiple Responsibilities** (20%)
   - Services doing multiple jobs
   - Classes with unclear focus
   - Mixing concerns

3. **Unfinished Code** (20%)
   - TODO comments in production
   - Stub functions returning None
   - NotImplementedError in live code

4. **Dead Code** (15%)
   - Unused functions and imports
   - Unreachable code paths
   - Obsolete modules

5. **Silent Failures** (10%)
   - Swallowed exceptions
   - Error paths not visible
   - Failed operations hidden

6. **Over-Engineering** (10%)
   - Complex solutions to simple problems
   - Premature optimization
   - Unnecessary features

## Easiest Fixes

| Issue | Fix | Effort |
|-------|-----|--------|
| Abstract class | Make concrete | Low |
| TODOs | Finish or delete | Low |
| Dead code | Remove | Low |
| Swallowed errors | Handle visibly | Low |
| Over-generic | Make specific | Low |
| Multiple responsibilities | Split services | Medium |

## When to Use Philosophy Guardian

1. **Before Merging PRs**
   - Ensure philosophy alignment
   - Catch over-engineering early
   - Educate team on principles

2. **During Refactoring**
   - Verify simplification
   - Stay true to principles
   - Identify further improvements

3. **Design Decisions**
   - Challenge architectural choices
   - Evaluate trade-offs
   - Reference philosophy framework

4. **Onboarding Features**
   - Confirm new modules follow pattern
   - Verify brick & studs structure
   - Check regeneratability

5. **Team Learning**
   - Share philosophy knowledge
   - Build shared understanding
   - Educate through examples

6. **Code Reviews**
   - Provide constructive feedback
   - Reference principles
   - Help team grow

## Philosophy.md Key Sections

| Section | Lines | Focus |
|---------|-------|-------|
| Ruthless Simplicity | 32-38 | Minimize abstractions |
| Modular Architecture | 40-46 | Brick & studs pattern |
| Zero-BS Implementation | 48-56 | Complete, working code |
| Decision Framework | 133-142 | How to make choices |
| Areas to Simplify | 153-161 | Where to focus effort |

Read `.claude/context/PHILOSOPHY.md` for complete guidance.

## What Philosophy Guardian IS

- Educational and constructive
- Focused on preventing complexity
- About building shared understanding
- Helping code stay simple and clear
- Guiding through examples
- Learning and evolving with team

## What Philosophy Guardian Is NOT

- Gatekeeping or perfectionism
- Catching every possible improvement
- Making code "perfect" before merging
- Creating barriers to contribution
- About author's ego or style
- Enforcing arbitrary rules

## Success Indicators

### Your Code Review is Good If
- Specific violations identified with file:line
- Concrete code examples provided
- Philosophy principles referenced
- Educational context given
- Multiple solutions offered where applicable
- Good choices celebrated too

### Your Code Follows Philosophy If
- Simplicity is obvious
- One clear responsibility
- Public interface is minimal
- All functions complete and working
- No TODOs or stubs
- Errors handled visibly

## Integration with Other Skills

Philosophy Guardian works with:
- **Builder Agent**: Ensures implementations align
- **Reviewer Agent**: Validates code principles
- **Architect Agent**: Challenges design decisions
- **Cleanup Agent**: Identifies complexity to remove
- **Tester Agent**: Verifies complete implementations

## Quick Wins (High Impact, Low Effort)

1. Remove abstract layers (make concrete)
2. Delete TODO comments or complete code
3. Remove dead code and unused imports
4. Split classes with multiple responsibilities
5. Handle errors visibly instead of swallowing

## Learning Resources

1. **SKILL.md** - Complete detailed documentation
2. **README.md** - Skill overview and examples
3. **PHILOSOPHY.md** - Core principles (read first!)
4. **Examples** - Real violation patterns
5. **This file** - Quick reference

## Tips for Effective Reviews

1. **Be Specific**: Always give file:line references
2. **Show Examples**: Before/after code samples
3. **Explain Why**: Connect to philosophy principles
4. **Offer Solutions**: Give concrete recommendations
5. **Celebrate Good Code**: Acknowledge philosophy-aligned choices
6. **Ask Questions**: Help developers think critically
7. **Reference Docs**: Point to philosophy.md for learning
8. **Be Proportionate**: Flag real issues, not nitpicks

## Remember

Philosophy Guardian is about:
- **Educating**: Helping team understand principles
- **Preventing**: Catching complexity before it compounds
- **Improving**: Making code simpler and clearer
- **Aligning**: Ensuring shared understanding
- **Growing**: Building a culture of simplicity

The goal is not perfect code, but code that embodies amplihack's values.
