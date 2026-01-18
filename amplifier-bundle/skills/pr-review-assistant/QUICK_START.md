# PR Review Assistant - Quick Start Guide

## What is This Skill?

A Claude Code skill that reviews pull requests against amplihack's core philosophy:

- **Ruthless Simplicity**: Every line must justify its existence
- **Modular Architecture**: Clear contracts and boundaries (Brick & Studs)
- **Zero-BS Implementation**: Production-ready code, no shortcuts
- **Quality Over Speed**: Long-term maintainability over quick wins

## When to Use

```
"Review this PR for philosophy alignment"
"Check if this module follows brick design"
"Is there over-engineering in this PR?"
"Suggest simplifications for these changes"
```

## How to Use

### Option 1: Review a PR (GitHub)

```
Claude, review PR #123 against our philosophy.
Focus on:
- Over-engineering patterns
- Module structure
- Test coverage
```

Claude will:

1. Analyze PR changes
2. Check philosophy alignment
3. Identify issues with specific file:line references
4. Suggest concrete improvements
5. Post review comments to GitHub

### Option 2: Review Code Files

```
Claude, review these changes in user_service.py
for ruthless simplicity and over-engineering.
```

Claude will:

1. Read the file
2. Assess against philosophy
3. Identify issues
4. Suggest simplifications
5. Explain why changes align (or don't) with principles

### Option 3: Analyze Module Structure

```
Claude, verify that this authentication module
follows brick design principles.
```

Claude will:

1. Check public interface clarity
2. Verify single responsibility
3. Assess module boundaries
4. Suggest improvements
5. Recommend specification documentation

## What Gets Reviewed

### 1. Ruthless Simplicity Check

```
✓ Every function has ONE clear purpose
✓ No unnecessary abstractions or indirection
✓ No future-proofing or speculation
✓ No duplicate logic
✓ Clear, self-documenting names
✓ Minimal parameters and branching
```

**Common Issues Found:**

- Base classes for 2-3 implementations (unnecessary)
- Configuration frameworks that aren't needed
- Factory patterns for single implementations
- Premature optimization
- Generic "helper" functions

### 2. Modular Architecture Check

```
✓ Module has ONE clear responsibility
✓ Public interface is minimal and clear
✓ Internal utilities properly isolated
✓ Dependencies are explicit
✓ No circular dependencies
✓ Clear contracts at boundaries
```

**Common Issues Found:**

- Unclear what's public vs private
- Dependencies not documented
- Modules doing too many things
- No specification for regeneration
- Missing tests for module contract

### 3. Zero-BS Implementation Check

```
✓ No TODOs or NotImplementedError in production code
✓ No mock/test data in production
✓ No dead code or unused imports
✓ Error handling is explicit
✓ All functions are working implementations
✓ No swallowed exceptions
✓ Clear error messages
```

**Common Issues Found:**

- TODO comments in code
- Functions that return None on error
- Caught exceptions with no context
- Code paths that can't happen
- Silent failures

### 4. Test Coverage Check

```
✓ Public interface has tests
✓ Edge cases covered
✓ Error conditions tested
✓ Integration points verified
✓ Coverage adequate (85%+)
✓ Tests verify contract, not implementation
```

**Common Issues Found:**

- No tests for new public functions
- Edge cases not covered
- Error paths not tested
- Coverage below 85%
- Tests that only verify implementation

### 5. Documentation Check

```
✓ Docstrings are clear and complete
✓ Public interface documented
✓ Examples provided for new features
✓ Type hints present and accurate
✓ Module README updated if needed
✓ Specification created for new modules
```

**Common Issues Found:**

- Missing docstrings
- No type hints
- Vague error documentation
- No usage examples
- No module specification

## Review Output

The skill produces:

### 1. Compliance Report

```
RUTHLESS SIMPLICITY: ✓ PASS
- Code is straightforward with no unnecessary abstractions
- Each function has single clear purpose
- No over-parameterization

MODULAR ARCHITECTURE: ✓ PASS
- Module has clear single responsibility
- Public interface is minimal
- Dependencies are explicit

ZERO-BS IMPLEMENTATION: ⚠ ISSUES FOUND
- 2 TODO comments (lines 45, 67)
- 1 swallowed exception (line 52)

TEST COVERAGE: ✗ NEEDS WORK
- Missing tests for validate_token()
- No edge case coverage

DOCUMENTATION: ⚠ PARTIAL
- Module spec missing (required for new modules)
- Good docstrings on new functions

OVERALL: NEEDS IMPROVEMENTS BEFORE MERGE
```

### 2. Specific Recommendations

```
FILE: auth/token.py (line 45)

ISSUE: TODO comment in production code
"# TODO: Add rate limiting"

SUGGESTION: Either implement it or file an issue.
TODO in code = incomplete work. Don't merge.

---

FILE: auth/token.py (line 52)

ISSUE: Swallowed exception

CURRENT CODE:
try:
    result = validate_signature(token)
except Exception:
    return None

PROBLEM: Caller doesn't know why validation failed.
Impossible to debug.

SUGGESTION:
try:
    result = validate_signature(token)
except SignatureError as e:
    raise ValueError(f"Invalid token: {e}") from e
```

### 3. GitHub Review (Optional)

If reviewing a GitHub PR, creates detailed review:

```
**Philosophy Compliance Review**

This PR has good structure and clear functionality.
Before merge, address these items:

**Issues Found:**
- 2 TODO comments (production code should be complete)
- 1 swallowed exception (makes debugging impossible)
- Missing test for edge case
- Module spec missing (required for brick design)

**Suggestions:**
- See inline comments for specific code
- Create Specs/authentication.md per template
- Add test for expired token case

**Strengths:**
- Clear module structure
- Good error handling overall
- Comprehensive docstrings
- Type hints throughout
```

## Common Review Scenarios

### Scenario 1: Over-Engineering

```
DETECTED: Unnecessary abstraction
- Abstract base class for 2 implementations
- Template method pattern adds complexity

SUGGESTION: Use simple direct classes
- Each class is 10 lines, not 20 in hierarchy
- Easier to understand and test
```

### Scenario 2: Missing Tests

```
DETECTED: New public function without tests
- check_permission(user, resource) → bool
- No tests for true/false cases
- No tests for edge cases

ACTION: Add tests/test_permissions.py
- ✓ Valid user → True
- ✓ Invalid user → False
- ✓ Empty user string
- ✓ Null resource
```

### Scenario 3: TODOs in Code

```
DETECTED: TODO comment at line 34
"# TODO: Add caching"

PROBLEM: Incomplete code shouldn't be merged

SOLUTION:
Option A: Implement the caching now
Option B: Remove TODO, file issue for future
Option C: Remove the comment and the commented-out code
```

### Scenario 4: No Module Spec

```
DETECTED: New module without specification

REQUIRED: Create Specs/module-name.md

Template includes:
- Purpose (one sentence)
- Public interface (exported functions/classes)
- Dependencies (external and internal)
- Test requirements
- Example usage

This enables module regeneration in future.
```

## How to Respond to Feedback

### If You Agree

```
Claude, I agree. Let me fix these issues:
1. Remove TODOs and implement properly
2. Add test for edge case
3. Create module specification
```

### If You Disagree

```
Claude, I disagree about the abstraction.
Here's why it's necessary:
[explain context]

Is there a simpler approach I'm missing?
```

### If You Have Questions

```
Claude, I'm not sure about this suggestion.
Can you explain:
1. What principle is violated?
2. Why is the simpler approach better?
3. Are there cases where my approach makes sense?
```

## Philosophy References

All reviews anchor in these principles:

- **Ruthless Simplicity**: The solution should be as simple as possible, but no simpler
- **Brick Architecture**: Self-contained modules with clear connection points
- **Zero-BS Implementation**: Production-ready code, no shortcuts or TODOs
- **Quality Over Speed**: Long-term maintainability over quick implementation
- **Regeneratable Modules**: Any module can be rebuilt from its specification

See `.claude/context/PHILOSOPHY.md` for full philosophy.

## Tips for Better Reviews

1. **Ask Questions**: "Why do we need this abstraction?" invites dialogue
2. **Provide Examples**: Show simpler code alongside your suggestion
3. **Acknowledge Good Work**: "I like how you handled errors here"
4. **Be Specific**: Reference exact line numbers and code
5. **Explain Why**: Help reviewee understand the principle, not just the rule
6. **Suggest Alternatives**: Offer multiple approaches, not just one "right" way
7. **Learn Together**: Reviews are teaching opportunities

## What Happens After Review

1. **Issues identified**: Developer reviews feedback
2. **Discussion**: Can ask questions or explain context
3. **Updates made**: Code is revised based on feedback
4. **Re-review**: Verify changes address concerns
5. **Approval**: If philosophy aligned, ready to merge

## Common Questions

**Q: Does this check syntax and style?**
A: No. Use linters for style. This checks philosophy alignment.

**Q: Can I ignore feedback?**
A: You can, but philosophy is the development foundation. Consider why.

**Q: What if my code violates philosophy?**
A: Discuss it. Sometimes constraints require trade-offs. Let's talk.

**Q: Can I request a re-review?**
A: Yes, after making changes, ask Claude to re-review specific parts.

**Q: Is this used for every PR?**
A: Recommended for significant changes, especially new modules or refactoring.

## Next Steps

1. **Request a review**: Ask Claude to review a PR or code
2. **Read feedback**: Understand what's suggested and why
3. **Ask questions**: Clarify anything you don't understand
4. **Iterate**: Improve code based on feedback
5. **Merge**: When philosophy aligned, ready to go

## See Also

- `SKILL.md` - Complete skill documentation
- `EXAMPLES.md` - Detailed review examples
- `.claude/context/PHILOSOPHY.md` - Core development philosophy
- `Specs/` - Module specifications directory
- `.claude/context/DISCOVERIES.md` - Known issues and solutions
