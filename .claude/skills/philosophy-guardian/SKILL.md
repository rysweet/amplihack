---
name: philosophy-guardian
description: |
  Reviews code against amplihack's core philosophy: ruthless simplicity, modular design, zero-BS implementation.
  Use when reviewing PRs, refactoring code, or ensuring philosophy compliance.
  Flags violations and provides specific, actionable improvement suggestions.
  Reads from .claude/context/PHILOSOPHY.md for current principles.
---

# Philosophy Guardian Skill

## Purpose

The philosophy-guardian skill reviews code changes against amplihack's core development philosophy. It ensures that all code embodies our principles of ruthless simplicity, modular design (brick & studs pattern), and zero-BS implementation. This skill provides educational, constructive feedback with concrete improvement suggestions.

## When to Use This Skill

- **Pull Request Reviews**: Ensure PRs align with amplihack philosophy before merging
- **Code Refactoring**: Identify over-engineering and simplification opportunities
- **Philosophy Compliance Checks**: Verify code maintains simplicity principles
- **Onboarding New Features**: Confirm new modules follow brick philosophy
- **Design Decisions**: Challenge architectural choices against philosophy
- **Knowledge Sharing**: Educate team members on philosophy principles through examples

## Core Philosophy Framework

The philosophy-guardian reviews code against three core pillars:

### 1. Ruthless Simplicity
- Minimize abstractions - every layer must justify its existence
- Start minimal, grow as needed - no future-proofing
- Avoid over-engineering - KISS principle taken seriously
- Question unnecessary complexity regularly
- Favor clarity over cleverness

### 2. Modular Design (Bricks & Studs)
- **Brick** = Self-contained module with ONE clear responsibility
- **Stud** = Public contract (functions, API, data models) others connect to
- **Regeneratable** = Can be rebuilt from specification without breaking connections
- Clear module boundaries with defined interfaces
- All code, tests, fixtures isolated within module folder

### 3. Zero-BS Implementation
- No stubs or placeholders - no fake implementations or unimplemented functions
- No dead code - remove unused code completely
- No TODOs in code - implement or don't include it
- Every function must work or not exist
- No faked APIs or mock implementations in production code
- No swallowed exceptions - handle errors transparently

## How to Use This Skill

### Step 1: Gather Code for Review
Provide the code you want reviewed. This can be:
- A pull request diff
- Specific file(s) to analyze
- A module or component
- Architecture or design decisions

### Step 2: Reference Philosophy Principles
The skill reads `.claude/context/PHILOSOPHY.md` to ensure consistent application of current principles.

### Step 3: Comprehensive Review
The skill analyzes code across three dimensions:

#### A. Ruthless Simplicity Check
- Identify over-abstraction (too many layers, unnecessary indirection)
- Find unnecessary complexity (solving non-existent problems)
- Spot future-proofing (building for hypothetical scenarios)
- Detect framework over-usage (using only needed features)
- Flag generic "flexible" code that isn't actually needed

#### B. Modular Design Check
- Verify single, clear responsibility per module
- Confirm public interface is minimal and clear
- Identify circular dependencies or tangled coupling
- Check that modules are self-contained and regeneratable
- Ensure studs (connection points) are well-defined

#### C. Zero-BS Implementation Check
- Find TODO comments, stubs, or NotImplementedError
- Identify unfinished implementations or placeholders
- Spot dead code or unused functions
- Detect swallowed exceptions or silent failures
- Find mock/fake implementations in production code

### Step 4: Provide Specific Feedback
For each violation found, provide:
1. **What**: The specific violation detected
2. **Where**: Exact file and line number
3. **Why It Matters**: How it violates philosophy
4. **Concrete Fix**: Specific improvement suggestion with example code
5. **Educational Context**: Why this matters for the project

## Analysis Checklist

### Ruthless Simplicity
- [ ] No over-abstraction or unnecessary layers
- [ ] Solving immediate problem, not hypothetical futures
- [ ] Code is direct and clear, not overly generic
- [ ] All abstractions and indirection justified
- [ ] Framework usage is minimal (only what's needed)
- [ ] No premature optimization
- [ ] Complex logic is simplified where possible
- [ ] Each function has single, clear purpose

### Modular Design (Bricks & Studs)
- [ ] Module has ONE clear responsibility
- [ ] Public interface is small and clear
- [ ] All exports documented and justified
- [ ] Module is self-contained (code, tests, fixtures in one place)
- [ ] Clear connection points (studs) to rest of system
- [ ] Can be understood and modified independently
- [ ] Dependencies are explicit and justified
- [ ] No circular dependencies between modules

### Zero-BS Implementation
- [ ] No TODO comments or unfinished code
- [ ] No NotImplementedError in production code
- [ ] No placeholder functions or stub implementations
- [ ] No dead code or unused functions
- [ ] No mock/fake data in production
- [ ] Errors are handled, not swallowed
- [ ] All error paths are visible during development
- [ ] Every exported function works completely

## Review Template

When reviewing code, structure feedback using this template:

```
## Philosophy Review: [Component/PR Name]

### Ruthless Simplicity Assessment
[Analysis of abstraction level, complexity, and future-proofing]

Findings:
- Finding 1 with specific location
- Finding 2 with specific location

### Modular Design Assessment
[Analysis of module boundaries, responsibility, and regeneratability]

Findings:
- Finding 1 with specific location
- Finding 2 with specific location

### Zero-BS Implementation Assessment
[Analysis of completeness, no stubs, proper error handling]

Findings:
- Finding 1 with specific location
- Finding 2 with specific location

### Overall Assessment
[Summary of philosophy alignment]

### Recommended Actions
1. [Specific improvement with code example]
2. [Specific improvement with code example]
3. [Specific improvement with code example]
```

## Example Violations and Feedback

### Example 1: Over-Abstraction (Ruthless Simplicity Violation)

**Problem Code:**
```python
# Over-engineered generic handler
class AbstractBaseHandler(ABC):
    def process(self, data):
        result = self.validate(data)
        result = self.transform(result)
        result = self.enrich(result)
        return self.finalize(result)

class JSONHandler(AbstractBaseHandler):
    def validate(self, data):
        # validation code
    def transform(self, data):
        # transform code
    # etc...
```

**Why It Violates Philosophy:**
- Unnecessary abstraction layer that doesn't solve current problem
- Future-proofing for potential other handler types
- Adds indirection and complexity without clear benefit

**Constructive Feedback:**
```
FILE: handlers.py, lines 1-20

VIOLATION: Over-abstraction (Ruthless Simplicity)

This code builds an abstract handler framework for potential future
handler types that don't exist yet. This is future-proofing that violates
ruthless simplicity.

RECOMMENDATION: Simplify to concrete JSONHandler class.

BEFORE (over-engineered):
    class AbstractBaseHandler(ABC):
        def process(self, data):
            result = self.validate(data)
            result = self.transform(result)
            result = self.enrich(result)
            return self.finalize(result)

AFTER (ruthlessly simple):
    class JSONHandler:
        def process(self, data):
            self.validate(data)
            self.transform(data)
            self.enrich(data)
            return self.finalize(data)

If another handler type is needed in the FUTURE, create it then.
Don't build for problems that don't exist yet.
```

### Example 2: Unclear Module Boundaries (Modular Design Violation)

**Problem Code:**
```python
# In user_service.py
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

**Why It Violates Philosophy:**
- Too many responsibilities (validation, persistence, notification, logging, caching, webhooks, audit)
- Not a single "brick" - does too many things
- Hard to test and modify independently
- Unclear what the "studs" (public interface) actually are

**Constructive Feedback:**
```
FILE: user_service.py, lines 5-25

VIOLATION: Multiple Responsibilities (Modular Design)

The UserService has too many responsibilities mixed together:
- User validation
- Database persistence
- Email notifications
- Event logging
- Cache management
- Webhook triggering
- Audit trail generation

This violates the brick philosophy (one responsibility per module).

RECOMMENDATION: Create separate, focused services.

REFACTORED STRUCTURE:

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
This is how we build regeneratable bricks.
```

### Example 3: Stub Implementation (Zero-BS Implementation Violation)

**Problem Code:**
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
        result.append(processed)  # Will crash when processed is None!
    return result
```

**Why It Violates Philosophy:**
- Functions with TODO comments are incomplete stubs
- Code that returns None will cause downstream failures
- No actual implementation

**Constructive Feedback:**
```
FILE: metrics.py, lines 3-8

VIOLATION: Stub Implementation (Zero-BS)

This function is incomplete with TODO comments and returns None.
This breaks the zero-BS principle: "Every function must work or not exist."

Options:

1. IMPLEMENT IT NOW if it's needed:
   def calculate_complex_metric(data):
       try:
           # actual calculation
           result = expensive_computation(data)
           return result if result is not None else 0
       except ValueError as e:
           # Handle edge cases
           log_error(f"Invalid data: {e}")
           raise

2. REMOVE IT if it's not ready:
   Delete the function entirely. Add it when actually needed,
   not as a placeholder.

3. DEFER TO LATER if blocking:
   Move to a separate module and update task tracking.
   Remove from production code.

Choose one, but don't leave stubs in the codebase.
```

## Educational Principles

When providing feedback, remember:

1. **Be Constructive**: Frame as learning opportunity, not criticism
2. **Provide Context**: Explain WHY the principle matters
3. **Offer Solutions**: Give specific, working code examples
4. **Celebrate Alignment**: Acknowledge good philosophy choices
5. **Ask Questions**: Help developers think through implications
6. **Reference Philosophy**: Point to philosophy.md for detailed principles
7. **Suggest Learning**: "See philosophy.md section X for more on this"

## Key Insights to Communicate

### On Ruthless Simplicity
- "KISS principle: Keep It Simple, Stupid"
- "It's easier to add complexity later than remove it"
- "Code you don't write has no bugs"
- "Start with the simplest solution that works"

### On Modular Design
- "One responsibility = one reason to change"
- "Bricks are regeneratable - imagine rebuilding this module"
- "Studs are the connection points others depend on"
- "Self-contained modules are easier to test and understand"

### On Zero-BS Implementation
- "Every function must work or not exist"
- "No TODOs in code - implement or don't include it"
- "Error handling must be visible, not swallowed"
- "Fake implementations are technical debt from day one"

## Usage Scenarios

### Scenario 1: PR Philosophy Review

```
User: "Review this PR for philosophy alignment"
      [Provides PR diff with new authentication module]

Philosophy Guardian:
1. Analyzes code across simplicity, modularity, and completeness
2. Identifies 3 violations with specific suggestions
3. Highlights 2 areas that exemplify good philosophy
4. Provides educational context for each finding
5. Suggests concrete improvements with code examples
```

### Scenario 2: Refactoring Check

```
User: "I'm refactoring this service - help ensure I stay true to philosophy"
      [Provides old and new service code]

Philosophy Guardian:
1. Compares to philosophy principles
2. Shows how refactoring improves simplicity
3. Suggests further simplification opportunities
4. Verifies modular boundaries are clearer
5. Confirms zero-BS principles are maintained
```

### Scenario 3: Design Decision Challenge

```
User: "I'm thinking about adding a caching layer to improve performance"

Philosophy Guardian:
1. Questions if optimization is premature
2. Challenges necessity vs. future-proofing
3. Explores simpler alternatives
4. Helps think through trade-offs
5. References philosophy framework for decision
```

## Integration with Other Skills

Philosophy Guardian works with:

- **Builder Agent**: Ensures implementations align with philosophy
- **Reviewer Agent**: Validates code meets project principles
- **Architect Agent**: Challenges design decisions against philosophy
- **Cleanup Agent**: Helps identify and remove unnecessary complexity
- **Tester Agent**: Verifies zero-BS implementations work completely

## Common Patterns

### Pattern 1: Future-Proofing

**Red Flag**: "We might need this later for..."

**Philosophy Response**:
> "YAGNI - You Aren't Gonna Need It. Build for NOW, add later if needed.
> The code you don't write has no bugs and doesn't need maintenance."

### Pattern 2: "Flexible" Code

**Red Flag**: "Let's make this generic so it's flexible for other use cases"

**Philosophy Response**:
> "Flexibility comes from clarity and modularity, not generic code.
> Clear, specific modules are easier to adapt than over-engineered generic ones."

### Pattern 3: Many Responsibilities

**Red Flag**: "This service handles user, auth, logging, and caching"

**Philosophy Response**:
> "That's at least 4 different responsibilities. Each needs its own brick.
> Separate services are easier to test, understand, and modify independently."

### Pattern 4: Incomplete Code

**Red Flag**: "TODO: implement feature X"

**Philosophy Response**:
> "No TODOs in code. Either implement it completely or don't include it.
> If it's future work, track it separately, not in the code."

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

## Quality Checklist

Before providing philosophy feedback, verify:

1. **Specific**: Point to exact violations, not vague concerns
2. **Constructive**: Offer clear improvements, not just criticism
3. **Educational**: Help developers understand underlying principles
4. **Actionable**: Provide code examples developers can use
5. **Fair**: Acknowledge good philosophy choices too
6. **Proportionate**: Flag real problems, not nitpicks
7. **Consistent**: Apply principles uniformly across reviews
8. **Referenced**: Point to philosophy.md for details

## Philosophy.md Reference

Key sections from `.claude/context/PHILOSOPHY.md`:

- **Ruthless Simplicity** (lines 32-38)
- **Modular Architecture** (lines 40-46)
- **Zero-BS Implementations** (lines 48-56)
- **Decision-Making Framework** (lines 133-142)
- **Areas to Simplify** (lines 153-161)

## Tips for Effective Reviews

1. **Read Philosophy First**: Understand current principles in philosophy.md
2. **Be Specific**: Always provide file/line numbers and concrete examples
3. **Explain Context**: Help developers understand the reasoning
4. **Offer Alternatives**: Show multiple ways to improve
5. **Ask Questions**: Prompt developers to think critically
6. **Celebrate Good Choices**: Acknowledge philosophy-aligned code
7. **Use Examples**: Concrete code examples clarify intent better than prose
8. **Reference Philosophy**: Point developers to philosophy.md for learning
9. **Be Proportionate**: Flag real issues, not nitpicks
10. **Build Understanding**: Goal is to spread philosophy knowledge, not score points

## Evolution and Learning

This skill should improve through:

- Tracking patterns in common violations
- Building more detailed examples over time
- Understanding team's philosophy maturity
- Documenting discovered anti-patterns
- Evolving feedback based on team feedback
- Recording learnings in `.claude/context/DISCOVERIES.md`

## Remember

Philosophy Guardian is not about gatekeeping or perfectionism. It's about:

- **Educating**: Helping team understand principles
- **Preventing**: Catching complexity before it compounds
- **Improving**: Making code simpler and clearer over time
- **Aligning**: Ensuring shared understanding of how we build
- **Growing**: Building a culture of ruthless simplicity
