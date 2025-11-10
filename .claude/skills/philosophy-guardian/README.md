# Philosophy Guardian Skill

## Overview

The philosophy-guardian is a Claude Code skill that reviews code against amplihack's core development principles. It ensures all code embodies ruthless simplicity, modular design (brick & studs pattern), and zero-BS implementation. This skill provides educational, constructive feedback with concrete improvement suggestions rather than just pointing out problems.

## Quick Start

### Review PR for Philosophy Alignment

```
Claude, review this PR for philosophy compliance and suggest improvements.
[Provide PR diff or code changes]
```

Claude will:
1. Analyze code against three philosophy pillars
2. Identify specific violations with file/line references
3. Provide constructive feedback with concrete examples
4. Highlight good philosophy choices too
5. Suggest specific improvements with working code examples

### Review Refactoring Work

```
Claude, I'm refactoring this service. Help me ensure I stay true to
amplihack's philosophy while simplifying the design.
[Provide old and new code]
```

Claude will:
1. Compare refactoring to philosophy principles
2. Show how changes improve simplicity and modularity
3. Suggest further simplification opportunities
4. Verify modular boundaries are clearer
5. Confirm zero-BS principles are maintained

### Challenge a Design Decision

```
Claude, I'm considering adding a caching layer for performance.
How does this align with our philosophy?
```

Claude will:
1. Question if optimization is necessary now
2. Challenge future-proofing vs. ruthless simplicity
3. Explore simpler alternatives
4. Help think through trade-offs
5. Reference philosophy framework for decision

## What Philosophy Guardian Does

### 1. Ruthless Simplicity Review

Identifies code that's over-engineered, over-abstracted, or built for hypothetical futures:

- Over-abstraction (unnecessary layers of indirection)
- Unnecessary complexity (solving non-existent problems)
- Future-proofing (building for hypothetical scenarios)
- Framework over-usage (using features that aren't needed)
- Generic "flexible" code that's harder to understand than specific code

**Example violation**: Creating an abstract handler framework for potential future handler types that don't exist yet.

### 2. Modular Design Review

Ensures code follows the brick & studs pattern:

- Single, clear responsibility per module
- Minimal, clear public interface (the "studs")
- Self-contained modules (code, tests, examples in one place)
- Well-defined connection points
- Regeneratable - can be rebuilt from specification without breaking system

**Example violation**: A UserService that handles validation, persistence, email notifications, logging, caching, webhooks, AND audit trails (7 different responsibilities in one class).

### 3. Zero-BS Implementation Review

Ensures code is complete and working:

- No TODO comments or unfinished implementations
- No placeholder functions or stub implementations
- No dead code or unused functions
- All error paths handled, not swallowed
- No mock/fake data in production code

**Example violation**: Functions with TODO comments and returning None, which will crash downstream consumers.

## How It Works

### Step 1: Provide Code for Review

Give the skill code to review:
- A pull request diff
- Specific file(s)
- A module or component
- Architecture/design decisions

### Step 2: Analysis Across Three Dimensions

The skill analyzes your code against these core principles:

```
RUTHLESS SIMPLICITY
├─ No over-abstraction
├─ Solving current problem, not hypothetical futures
├─ Direct, clear code (not over-engineered)
├─ All abstractions justified
├─ Minimal framework usage
├─ No premature optimization
├─ Complex logic simplified
└─ Single, clear purpose per function

MODULAR DESIGN (Bricks & Studs)
├─ ONE clear responsibility per module
├─ Small, clear public interface
├─ Self-contained (tests/fixtures in module)
├─ Clear connection points to system
├─ Independent understanding/modification
├─ Explicit, justified dependencies
├─ No circular dependencies
└─ Regeneratable from specification

ZERO-BS IMPLEMENTATION
├─ No TODO comments or unfinished code
├─ No NotImplementedError in production
├─ No placeholder functions
├─ No dead code
├─ No mock/fake data in production
├─ Errors handled, not swallowed
├─ Error paths visible during development
└─ Every exported function works completely
```

### Step 3: Specific, Constructive Feedback

For each violation found, you get:

1. **What**: The specific violation
2. **Where**: Exact file and line numbers
3. **Why**: How it violates philosophy
4. **How**: Concrete improvement with code examples
5. **Why It Matters**: Educational context

### Step 4: Educational, Actionable Guidance

The skill educates, not gatekeeps:
- Explains underlying principles
- Offers multiple solutions where applicable
- Celebrates philosophy-aligned code too
- Points to philosophy.md for deeper learning
- Helps build shared understanding

## Real-World Examples

### Example 1: Over-Abstraction

**Problem**: Generic AbstractBaseHandler for hypothetical future handler types

```python
class AbstractBaseHandler(ABC):
    def process(self, data):
        result = self.validate(data)
        result = self.transform(result)
        result = self.enrich(result)
        return self.finalize(result)

class JSONHandler(AbstractBaseHandler):
    # ... implementation
```

**Philosophy Guardian Feedback**:
```
VIOLATION: Over-abstraction (Ruthless Simplicity)

This builds an abstract handler framework for potential future handler types
that don't exist yet. This violates ruthless simplicity.

RECOMMENDATION: Build the concrete JSONHandler first.

BEFORE (over-engineered):
    class AbstractBaseHandler(ABC): ...

AFTER (ruthlessly simple):
    class JSONHandler:
        def process(self, data):
            self.validate(data)
            self.transform(data)
            self.enrich(data)
            return self.finalize(data)

If another handler type is needed in the FUTURE, create it then.
The code you don't write has no bugs.
```

### Example 2: Too Many Responsibilities

**Problem**: UserService doing validation, persistence, email, logging, caching, webhooks, audit

```python
class UserService:
    def create_user(self, data):
        # validates user
        # saves to database
        # sends email notification
        # logs event
        # updates cache
        # triggers webhook
        # generates audit trail
```

**Philosophy Guardian Feedback**:
```
VIOLATION: Multiple Responsibilities (Modular Design)

UserService has 7 different responsibilities. This violates the brick
philosophy (one responsibility per module).

RECOMMENDATION: Create separate, focused services.

REFACTORED:

  class UserService:
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

Each service now has ONE clear job and can be tested/modified independently.
This is regeneratable bricks.
```

### Example 3: Stub Implementation

**Problem**: Functions with TODO comments and returning None

```python
def calculate_complex_metric(data):
    # TODO: implement this calculation
    # TODO: handle edge cases
    # TODO: add logging
    return None

def process_records(records):
    result = []
    for record in records:
        processed = calculate_complex_metric(record)
        result.append(processed)  # Crashes when processed is None!
    return result
```

**Philosophy Guardian Feedback**:
```
VIOLATION: Stub Implementation (Zero-BS)

Functions with TODO comments and returning None break zero-BS principle:
"Every function must work or not exist."

OPTIONS:

1. IMPLEMENT IT NOW if needed:
   def calculate_complex_metric(data):
       try:
           result = expensive_computation(data)
           return result if result is not None else 0
       except ValueError as e:
           log_error(f"Invalid data: {e}")
           raise

2. REMOVE IT if not ready:
   Delete the function. Add it when actually needed.

3. DEFER TO LATER if blocking:
   Move to separate module, update task tracking.
   Remove from production code.

Choose one. Don't leave stubs in the codebase.
```

## Philosophy Principles

### Ruthless Simplicity

- **KISS principle**: Keep It Simple, Stupid
- **Start minimal**: Solve the current problem, not hypothetical futures
- **No premature optimization**: Build simple first, optimize when needed
- **Code you don't write has no bugs**: Every line must justify its existence
- **Favor clarity**: Simple, clear code is better than clever code

### Modular Design (Bricks & Studs)

- **Brick** = Self-contained module with ONE clear responsibility
- **Stud** = Public contract (functions, classes, APIs) others connect to
- **Regeneratable** = Can be rebuilt from specification without breaking system
- **One responsibility** = One reason to change
- **Self-contained** = Code, tests, examples in module folder
- **Clear interfaces** = Public functions well-documented and minimal

### Zero-BS Implementation

- **Every function must work**: No stubs, no placeholders, no NotImplementedError
- **No TODOs in code**: Either implement it or don't include it
- **No dead code**: Remove unused functions and imports
- **Errors visible**: Don't swallow exceptions, handle them explicitly
- **Real implementations**: No mock/fake data in production code

## Philosophy Guardian Review Template

```
## Philosophy Review: [Component/PR Name]

### Ruthless Simplicity Assessment
[Analysis of abstraction level, complexity, future-proofing]

Findings:
- Specific violation 1 with location
- Specific violation 2 with location

### Modular Design Assessment
[Analysis of responsibilities, boundaries, regeneratability]

Findings:
- Specific violation 1 with location
- Specific violation 2 with location

### Zero-BS Implementation Assessment
[Analysis of completeness, working functions, error handling]

Findings:
- Specific violation 1 with location
- Specific violation 2 with location

### Overall Assessment
[Summary of philosophy alignment]

### Recommended Actions
1. [Specific improvement with code example]
2. [Specific improvement with code example]
3. [Specific improvement with code example]
```

## Common Anti-Patterns

### Anti-Pattern 1: Future-Proofing

**Red Flag**: "We might need this later for..."

**Philosophy Response**:
> "YAGNI - You Aren't Gonna Need It. Build for NOW, add later if needed.
> It's easier to add features than remove unnecessary complexity."

### Anti-Pattern 2: "Flexible" Code

**Red Flag**: "Let's make this generic so it's flexible for other use cases"

**Philosophy Response**:
> "Flexibility comes from clarity and modularity, not generic code.
> Clear, specific modules are easier to adapt than over-engineered generic ones."

### Anti-Pattern 3: Multiple Responsibilities

**Red Flag**: "This service handles authentication, logging, caching, and validation"

**Philosophy Response**:
> "That's 4 different responsibilities. Each should be its own brick.
> Separate services are easier to test, understand, and modify independently."

### Anti-Pattern 4: Incomplete Code

**Red Flag**: "TODO: implement feature X"

**Philosophy Response**:
> "No TODOs in code. Either implement it completely or don't include it.
> If it's future work, track it separately, not in the code."

## Integration with Other Skills

Philosophy Guardian works alongside:

- **Builder Agent**: Ensures implementations align with philosophy
- **Reviewer Agent**: Validates code meets project principles
- **Architect Agent**: Challenges design decisions against philosophy
- **Cleanup Agent**: Identifies and removes unnecessary complexity
- **Tester Agent**: Verifies zero-BS implementations work completely

## Success Metrics

A good philosophy review:

- [ ] Identifies specific violations with file/line references
- [ ] Provides concrete code examples for improvements
- [ ] Explains WHY violations matter
- [ ] Offers multiple solutions where applicable
- [ ] Educates, doesn't just criticize
- [ ] References philosophy principles consistently
- [ ] Builds shared understanding of philosophy
- [ ] Helps team internalize principles

## Tips for Effective Use

1. **Be Specific**: Always provide exact violations with file/line numbers
2. **Provide Context**: Explain the reasoning behind feedback
3. **Offer Solutions**: Give concrete code examples developers can use
4. **Ask Questions**: Help developers think critically about trade-offs
5. **Celebrate Good Choices**: Acknowledge philosophy-aligned code
6. **Reference Philosophy**: Point to philosophy.md for deeper learning
7. **Use Examples**: Show before/after code samples
8. **Be Proportionate**: Flag real issues, not nitpicks
9. **Build Understanding**: Goal is shared knowledge, not gatekeeping
10. **Keep Learning**: Record patterns and learnings in discoveries.md

## Philosophy.md Reference

Key sections to understand:

- **Ruthless Simplicity** (lines 32-38 in PHILOSOPHY.md)
- **Modular Architecture** (lines 40-46)
- **Zero-BS Implementations** (lines 48-56)
- **Decision-Making Framework** (lines 133-142)
- **Areas to Simplify** (lines 153-161)

Read `.claude/context/PHILOSOPHY.md` for complete details.

## Philosophy in Action

### When Reviewing Code, Ask:

1. **Ruthless Simplicity**:
   - Is this the simplest way to solve this problem?
   - Is there unnecessary abstraction?
   - Am I building for a problem that doesn't exist yet?

2. **Modular Design**:
   - Does this module have ONE clear responsibility?
   - Can someone understand this module independently?
   - Are the public interfaces minimal and clear?

3. **Zero-BS Implementation**:
   - Is this function complete and working?
   - Are all error cases handled?
   - Is there any unfinished code?

## Remember

Philosophy Guardian is about:

- **Educating**: Helping team understand principles
- **Preventing**: Catching complexity before it compounds
- **Improving**: Making code simpler and clearer over time
- **Aligning**: Ensuring shared understanding of how we build
- **Growing**: Building a culture of ruthless simplicity

Not about:
- Gatekeeping or perfectionism
- Catching every possible improvement
- Making code "perfect" before merging
- Creating barriers to contribution

## Evolution and Learning

This skill improves through:

- Tracking patterns in common violations
- Building more detailed examples
- Understanding team's philosophy maturity
- Recording discovered anti-patterns
- Evolving feedback based on results
- Documenting learnings in DISCOVERIES.md

## Related Resources

- `.claude/context/PHILOSOPHY.md` - Complete development philosophy
- `.claude/context/PATTERNS.md` - Common implementation patterns
- `.claude/context/DISCOVERIES.md` - Patterns and learnings
- `docs/document_driven_development/` - DDD methodology
- Skill SKILL.md - Complete detailed documentation

---

Use philosophy-guardian whenever you want to ensure code aligns with amplihack's development principles and culture.
