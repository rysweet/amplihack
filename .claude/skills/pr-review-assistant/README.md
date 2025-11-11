# PR Review Assistant Skill

Philosophy-aware pull request reviews that check alignment with amplihack principles. Use when reviewing PRs to ensure ruthless simplicity, modular design, and zero-BS implementation. Suggests simplifications, identifies over-engineering, verifies brick module structure.

## Files in This Skill

- **SKILL.md** - Complete skill documentation with full review process and examples
- **QUICK_START.md** - Getting started guide with common scenarios
- **EXAMPLES.md** - Detailed examples of reviews with feedback
- **REVIEW_CHECKLIST.md** - Complete checklist for reviewing code
- **README.md** - This file

## Quick Start

### Basic Usage

```
Claude, review this PR for philosophy alignment:
- Check for over-engineering
- Verify module structure
- Suggest simplifications
```

Claude will:

1. Analyze the code
2. Check against amplihack principles
3. Identify issues with specific file:line references
4. Suggest concrete improvements
5. Explain alignment with philosophy

### Review Focuses

This skill reviews for:

1. **Ruthless Simplicity**
   - Is every line necessary?
   - Are there unnecessary abstractions?
   - Could this be simpler?

2. **Modular Architecture (Brick & Studs)**
   - Does the module have ONE clear responsibility?
   - Are public contracts clear?
   - Are module boundaries well-defined?

3. **Zero-BS Implementation**
   - No TODOs in production code
   - All functions are working implementations
   - Error handling is explicit
   - No swallowed exceptions

4. **Test Coverage**
   - Public interface tested
   - Edge cases covered
   - Error paths tested
   - 85%+ coverage

5. **Documentation**
   - Clear docstrings and type hints
   - Module specifications for new modules
   - Usage examples

## Review Process

### Step 1: Request a Review

```
Claude, review this code for philosophy alignment.
```

Or:

```
Claude, check this PR (#123) against our development philosophy.
```

### Step 2: Understand the Feedback

Claude provides:

- **Compliance Report** - How code aligns with each principle
- **Specific Issues** - Problems with file:line references
- **Concrete Suggestions** - Code examples showing improvements
- **GitHub Review** - Optional detailed review as comments

### Step 3: Address Feedback

Review the suggestions and:

- Implement improvements suggested
- Ask questions if clarification needed
- Explain context if you disagree

### Step 4: Re-Review

```
Claude, I've addressed the issues. Can you re-review?
```

### Step 5: Merge

Once philosophy aligned, ready to merge!

## Common Patterns to Catch

### Over-Engineering

```
DETECTED: Unnecessary abstraction
ISSUE: Base class for 2 implementations
SUGGESTION: Use simple direct classes
```

### Missing Tests

```
DETECTED: New public function untested
ISSUE: validate_token() has no tests
SUGGESTION: Add tests for true/false/edge cases
```

### TODOs in Code

```
DETECTED: TODO comment at line 34
ISSUE: Incomplete work shouldn't be merged
SOLUTION: Implement it or remove the comment
```

### Module Issues

```
DETECTED: New module without specification
ISSUE: Module can't be regenerated
ACTION: Create Specs/module-name.md
```

## Example Review Output

```
RUTHLESS SIMPLICITY: ✓ PASS
- Code is straightforward
- Each function has single purpose
- No over-abstraction

MODULAR ARCHITECTURE: ✓ PASS
- Clear single responsibility
- Public interface minimal
- Dependencies explicit

ZERO-BS IMPLEMENTATION: ⚠ NEEDS WORK
- 2 TODO comments (lines 45, 67)
- 1 swallowed exception (line 52)

TEST COVERAGE: ✗ GAPS
- Missing edge case tests
- Coverage at 72%

DOCUMENTATION: ⚠ PARTIAL
- Module spec missing
- Good docstrings overall

VERDICT: NEEDS IMPROVEMENTS BEFORE MERGE
```

## When to Use

- **New features**: Verify design before big investment
- **Refactoring**: Ensure simplification actual, not more complexity
- **New modules**: Check brick design and specifications
- **Bug fixes**: Verify error handling and tests
- **API changes**: Check for over-engineering or missing documentation
- **Architecture changes**: Verify against philosophy principles

## Philosophy References

All reviews anchor in:

1. **Ruthless Simplicity** - Every line must justify its existence
2. **Brick Philosophy** - Self-contained, regeneratable modules
3. **Zero-BS Implementation** - Production-ready, no shortcuts
4. **Quality Over Speed** - Long-term maintainability
5. **Modular Design** - Clear boundaries and contracts

See `.claude/context/PHILOSOPHY.md` for complete philosophy.

## Acceptance Criteria for Code

### Before Merge

- [ ] Ruthless Simplicity: ✓ PASS
- [ ] Modular Architecture: ✓ PASS
- [ ] Zero-BS Implementation: ✓ PASS
- [ ] Test Coverage: 85%+
- [ ] Documentation: Complete
- [ ] No blocking philosophy issues

## Tips for Better Results

1. **Be Specific**: Ask about specific code sections
2. **Provide Context**: Explain what the code is doing
3. **Ask Questions**: "Why would this be better?" invites dialogue
4. **Listen to Feedback**: There's usually wisdom in the suggestions
5. **Iterate**: Multiple review rounds are normal

## How the Skill Works

The skill:

1. **Understands Context** - Reads code and PR information
2. **Analyzes Philosophy Alignment** - Checks against 5 core principles
3. **Identifies Issues** - Finds problems with specific references
4. **Suggests Improvements** - Provides concrete examples
5. **Explains Rationale** - Teaches why changes align with philosophy
6. **Posts Review** - Optional GitHub review comments

## Learning Outcomes

Through this skill, you learn:

- What constitutes "ruthless simplicity"
- How to design modules with clear boundaries
- Why zero-BS implementation matters
- What makes tests adequate
- How to recognize over-engineering
- How to write reviewable code

## Common Questions

**Q: Does this check Python style?**
A: No. Use linters for style (black, flake8). This checks philosophy.

**Q: Can I disagree with feedback?**
A: Absolutely! That's how we improve. Explain your reasoning and let's discuss.

**Q: What if I think the code is fine?**
A: You might be right. Ask Claude to explain the principle and see if you learn something.

**Q: How often should I use this?**
A: For significant changes. Small bug fixes might not need a full review.

**Q: Can I request re-review?**
A: Yes, after making changes: "Re-review my changes to see if issues are addressed"

**Q: What if I don't understand feedback?**
A: Ask Claude to explain more clearly or provide additional examples.

## See Also

- **SKILL.md** - Complete documentation with review process
- **QUICK_START.md** - Getting started in 5 minutes
- **EXAMPLES.md** - Real review examples with before/after
- **REVIEW_CHECKLIST.md** - Printable checklist for reviews
- **.claude/context/PHILOSOPHY.md** - Core development philosophy
- **Specs/** - Module specifications directory

## Feedback

This skill evolves based on usage:

- What patterns do we keep finding?
- What suggestions lead to better code?
- What's missing from the review process?
- How can we make this more helpful?

Share learnings in `.claude/context/DISCOVERIES.md`.

## Getting Started

1. Pick a PR or code file to review
2. Ask Claude: "Review this code for philosophy alignment"
3. Read the feedback and understand why
4. Implement improvements
5. Ask for re-review
6. Merge when philosophy aligned

That's it! Philosophy-aware code review in action.
