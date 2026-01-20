# Code Smell Detector - Quick Start Guide

## How to Use This Skill

### Basic Usage

```
User: Review this module for code smells and philosophy compliance.
      Target: /path/to/module/

Claude Code:
1. Loads and analyzes all Python files in module
2. Checks each for the 5 code smell patterns
3. Reports findings with:
   - Exact line numbers
   - Severity (critical/major/minor)
   - Philosophy violation
   - Before/after fix examples
4. Provides refactoring guidance
```

### Step-by-Step Analysis

**Step 1: Identify the Code**

```
"Check this authentication service for code smells."
→ Claude finds auth_service.py
```

**Step 2: Scan for Smells**

```
Code Smells Found:
1. Over-Abstraction (Line 15)
2. Large Function (Line 42)
3. Tight Coupling (Line 56)
```

**Step 3: Get Fixes**

```
For each smell, Claude provides:
- What's wrong and why
- Before code (problematic)
- After code (fixed)
- How to apply the fix
```

**Step 4: Learn Philosophy**

```
Why this matters:
- Violates "ruthless simplicity"
- Makes code harder to test
- Increases technical debt
```

## Common Scenarios

### Scenario 1: Code Review

```
User: Review this PR for philosophy compliance.
Claude:
1. Analyzes all changed files
2. Reports code smells found
3. Suggests fixes with examples
4. Explains philosophy principles
```

### Scenario 2: Refactoring Session

```
User: This module is getting complex. Help me refactor it.
Claude:
1. Identifies refactoring opportunities
2. Prioritizes by impact
3. Shows before/after patterns
4. Guides through refactoring steps
```

### Scenario 3: Learning

```
User: Why is this code considered a "smell"?
Claude:
1. Explains the pattern
2. Shows why it's problematic
3. Demonstrates the fix
4. References philosophy principle
```

### Scenario 4: Team Training

```
User: Show the team common code smells.
Claude:
1. Demonstrates 5 smell types
2. Shows real examples
3. Explains fixes clearly
4. Provides discussion points
```

## Quick Reference

### What to Ask

```
Good: "Review this module for code smells"
Good: "Is this function too large?"
Good: "Find tight coupling issues"
Good: "Check for over-abstraction"
Good: "Are there missing __all__ exports?"

Also Good: Show specific code and ask:
- "Is this inheritance hierarchy too deep?"
- "Should I inject this dependency?"
- "Is this class doing too much?"
```

### What You Get

For each smell found:

| Item        | Detail                   |
| ----------- | ------------------------ |
| Location    | File and line number     |
| Severity    | Critical/Major/Minor     |
| Description | What's wrong             |
| Philosophy  | Which principle violated |
| Example     | Bad pattern shown        |
| Fix         | Good pattern shown       |
| Steps       | How to refactor          |

## Example Analysis

### Example 1: Find Over-Abstraction

```
User Input:
"Check this UserProcessor class for unnecessary abstraction."

Code:
abstract class UserProcessor:
    @abstractmethod
    def process(user): pass

class SimpleUserProcessor(UserProcessor):
    def process(user): return user

Claude Output:
SMELL: Over-Abstraction
SEVERITY: MAJOR
LOCATION: userservice.py:5-12

ISSUE:
Abstract base class with only 1 concrete implementation.
Adds unnecessary layer without providing value.
Violates "ruthless simplicity" - every abstraction must justify itself.

PHILOSOPHY: Ruthless Simplicity

EXAMPLE - BEFORE:
abstract class UserProcessor:
    @abstractmethod
    def process(user): pass

class SimpleUserProcessor(UserProcessor):
    def process(user): return user

EXAMPLE - AFTER:
def process_user(user):
    """Process user data."""
    return user

WHY IT MATTERS:
- Removes unnecessary indirection
- Easier to test and understand
- Clearer code with less to maintain
- One thing does what needs doing
```

### Example 2: Find Large Function

```
User Input:
"This payment processing function seems too big. Help?"

Claude Output:
SMELL: Large Function (>50 lines)
SEVERITY: CRITICAL
LOCATION: payment.py:23-78 (56 lines)

ISSUES FOUND:
- Line count: 56 (target: <50)
- Nesting depth: 4 levels (target: <3)
- Responsibilities: 5 separate concerns
- Parameters: 7 (target: <5)

CONCERNS DETECTED:
1. Validation (lines 25-35)
2. Processing (lines 36-45)
3. Database operations (lines 46-55)
4. Notification (lines 56-65)
5. Logging (lines 66-78)

RECOMMENDATION:
Extract each concern to separate function.
Orchestrate workflow in main function.

[Shows complete refactoring with before/after]
```

### Example 3: Find Tight Coupling

```
User Input:
"Is this service tightly coupled?"

Claude Output:
SMELL: Tight Coupling
SEVERITY: MAJOR
LOCATION: UserService.py:12-28

DEPENDENCIES FOUND:
- Line 15: db = Database()    ← Hardcoded
- Line 22: email = Email()    ← Hardcoded
- Line 25: cache = Redis()    ← Hardcoded

PROBLEMS:
- Can't test without real database
- Can't swap implementations
- Dependencies hidden in code
- Hard to mock for testing

PHILOSOPHY: Modular Design (Studs)

FIX: Dependency Injection
Pass dependencies as constructor arguments.
Makes code testable and flexible.

[Shows complete refactoring]
```

## Analysis Output Format

The skill provides consistent output:

```
SMELL: [Name]
SEVERITY: [CRITICAL/MAJOR/MINOR]
LOCATION: [File:StartLine-EndLine]

ISSUE:
[What's wrong and why]

PHILOSOPHY VIOLATED:
[Which principle and how]

EXAMPLE - BEFORE:
[Bad code]

EXAMPLE - AFTER:
[Good code with explanation]

IMPACT:
[Why this matters for your project]

RECOMMENDED ACTIONS:
1. [Step 1]
2. [Step 2]
3. [Step 3]
```

## Integration Patterns

### With Code Review

```
PR Review:
1. Use skill to identify smells
2. Reference specific line numbers
3. Show before/after examples
4. Explain philosophy principle
5. Guide toward fix
```

### With Refactoring

```
Refactoring Plan:
1. Identify smells to fix (prioritize)
2. Get fixes from skill
3. Apply refactoring
4. Run tests to verify
5. Document changes
```

### With Architecture Review

```
Design Discussion:
1. Question proposed pattern
2. Check for potential smells
3. Reference philosophy
4. Suggest alternatives
5. Build team consensus
```

## Tips for Best Results

1. **Be Specific**: Show exact code when asking
2. **Ask Context**: Explain what you're trying to do
3. **Request Examples**: Ask for before/after comparisons
4. **Learn Philosophy**: Understand WHY each rule exists
5. **Share Results**: Use findings to build team understanding

## Document References

- **Full SKILL.md**: Complete detection rules and analysis process
- **README.md**: Overview and core concepts
- **examples/smell_analysis_example.md**: Real-world analysis examples

## Philosophy Foundation

This skill is based on amplihack's core principles:

- **Ruthless Simplicity**: Keep everything as simple as possible
- **Modular Design**: Self-contained modules with clear contracts
- **Zero-BS Code**: Only working implementations, no stubs
- **Single Responsibility**: Each function/class does ONE thing

See `.claude/context/PHILOSOPHY.md` for complete philosophy.

## Success Indicators

You're using this skill effectively when:

- Code is simpler and easier to understand
- Tests are easier to write and maintain
- Modules can be tested independently
- Team understands philosophy principles
- New code follows patterns naturally
- Refactoring discussions become constructive
- Quality and productivity both improve

## Next Steps

1. Use the skill to review a real module
2. Apply the fixes and improvements
3. Share examples with your team
4. Discuss philosophy principles
5. Build shared understanding
6. Continuously improve code quality

Remember: The goal is learning and improvement, not criticism.
