# PR Review Checklist

Use this checklist when reviewing code for philosophy alignment.

## Pre-Review

- [ ] Understand PR purpose and scope
- [ ] Identify affected modules and files
- [ ] Note any dependencies added or removed
- [ ] Read PR description and context

## Ruthless Simplicity

### Code Complexity

- [ ] Each function has single, clear purpose
- [ ] Functions are easy to understand in one read
- [ ] No excessive nesting or branching
- [ ] No duplicate or similar logic
- [ ] No unnecessary helper functions

### Abstractions

- [ ] No unnecessary base classes or inheritance
- [ ] No factory patterns for single implementation
- [ ] No generic frameworks built for hypothetical needs
- [ ] No template method patterns over-killing simple cases
- [ ] Interfaces justified by actual use

### Parameters and Configuration

- [ ] Functions aren't over-parameterized (< 5 params)
- [ ] No configuration objects when simple args work
- [ ] Default values provided where sensible
- [ ] No boolean flags creating code paths

### Names and Clarity

- [ ] Variable names are self-documenting
- [ ] Function names describe what they do
- [ ] Class names describe responsibility
- [ ] Avoid cryptic abbreviations
- [ ] Comments explain WHY, not WHAT

### Future-Proofing

- [ ] No "we might need this someday" code
- [ ] Features aren't speculative
- [ ] Current needs met, not hypothetical ones
- [ ] Extensibility comes through clear design, not speculation

## Modular Architecture (Brick & Studs)

### Module Responsibility

- [ ] Module has ONE clear responsibility
- [ ] Module name describes what it does
- [ ] Responsibilities are explicit
- [ ] No "utility" modules doing everything
- [ ] Clear why this module exists

### Public Interface

- [ ] Exports are clear and minimal
- [ ] `__all__` defined or obvious
- [ ] Public functions documented
- [ ] Clear what's meant for external use
- [ ] No private functions in public interface

### Internal Organization

- [ ] Internal utilities isolated
- [ ] Internal modules prefixed with underscore
- [ ] Clear separation of concerns
- [ ] Related code grouped together
- [ ] No internal details leaked outside

### Dependencies

- [ ] All external dependencies listed
- [ ] All internal dependencies explicit
- [ ] No circular dependencies
- [ ] Dependencies are justified
- [ ] Version constraints specified

### Module Structure

- [ ] Files organized logically
- [ ] Tests co-located with module
- [ ] Examples provided
- [ ] README or specification exists
- [ ] Module can be understood independently

## Zero-BS Implementation

### Code Completeness

- [ ] No TODO comments in code
- [ ] No FIXME or HACK comments (except in issues)
- [ ] No NotImplementedError (except abstract classes)
- [ ] No stubbed-out functions
- [ ] All functions fully implemented

### Production Readiness

- [ ] No mock or test data in production code
- [ ] No commented-out code blocks
- [ ] No dead code or unused imports
- [ ] No debug print statements
- [ ] No logging from every function

### Error Handling

- [ ] Errors explicitly handled
- [ ] No swallowed exceptions
- [ ] No silent failures
- [ ] Error messages are clear
- [ ] Exception type is specific (not just Exception)

### Visibility

- [ ] Errors are visible during development
- [ ] Problems don't hide until production
- [ ] Debugging information available
- [ ] Clear what happened when things fail
- [ ] Stack traces are preserved (use `from e`)

## Test Coverage

### Public Interface Testing

- [ ] Public functions have tests
- [ ] Test happy path (expected behavior)
- [ ] Test error cases (raises correct exceptions)
- [ ] Test boundary conditions
- [ ] Test empty/null inputs

### Edge Cases

- [ ] Empty lists/strings tested
- [ ] None/null values tested
- [ ] Max/min values tested
- [ ] Boundary conditions tested
- [ ] Invalid input tested

### Error Paths

- [ ] Each raised exception tested
- [ ] Error messages verified
- [ ] Exception type verified
- [ ] Context preserved (not just Exception)

### Contract Verification

- [ ] Return types match documentation
- [ ] Raised exceptions match documentation
- [ ] Accepted types match documentation
- [ ] Documentation matches actual behavior

### Coverage and Quality

- [ ] Coverage adequate (85%+)
- [ ] Critical paths fully tested
- [ ] Tests are independent
- [ ] Tests use realistic data
- [ ] Tests document behavior

### Integration Testing

- [ ] Module connections verified
- [ ] Dependencies called correctly
- [ ] Data flows through layers
- [ ] External service calls appropriate

## Documentation

### Docstrings

- [ ] All public functions documented
- [ ] Clear one-line summary
- [ ] Args section complete with types
- [ ] Returns section describes output
- [ ] Raises section lists exceptions
- [ ] Examples provided for complex functions

### Type Hints

- [ ] Type hints present
- [ ] Types are accurate
- [ ] Return types specified
- [ ] Optional types use Optional[]
- [ ] Avoid `Any` unless necessary

### Comments

- [ ] Comments explain WHY, not WHAT
- [ ] Complex logic is explained
- [ ] Non-obvious decisions noted
- [ ] Links to related issues/docs

### Module Documentation

- [ ] Module purpose clear
- [ ] Public interface documented
- [ ] Dependencies listed
- [ ] Example usage provided
- [ ] For new modules: spec created in Specs/

### README Updates

- [ ] Module README updated if needed
- [ ] New features documented
- [ ] Breaking changes noted
- [ ] Migration guide for changes
- [ ] Usage examples updated

## New Modules (Additional Checks)

### Module Specification

- [ ] Specs/module-name.md created
- [ ] Purpose section complete
- [ ] Public interface documented
- [ ] Dependencies listed
- [ ] Test requirements defined
- [ ] Example usage included

### Brick Design

- [ ] Module is regeneratable from spec
- [ ] Public contracts (studs) defined
- [ ] Module boundaries clear
- [ ] Single responsibility
- [ ] Can be rebuilt independently

### Structure

- [ ] Consistent with existing modules
- [ ] **init**.py exports clear
- [ ] core.py has main logic
- [ ] models.py for data structures
- [ ] utils.py for internal utilities
- [ ] tests/ with comprehensive tests

## Refactoring Changes (Additional Checks)

### No Regressions

- [ ] Tests still pass
- [ ] No public interface changes
- [ ] Behavior unchanged
- [ ] Performance not degraded
- [ ] Error handling preserved

### Simplification

- [ ] Complexity reduced
- [ ] Clarity improved
- [ ] Lines of code decreased
- [ ] Easier to understand
- [ ] Maintenance easier

### Cleanup

- [ ] Dead code removed
- [ ] Unused imports removed
- [ ] No new technical debt
- [ ] Deprecation handled properly

## Breaking Changes (If Any)

- [ ] Clearly marked breaking
- [ ] Deprecation path provided
- [ ] Migration guide included
- [ ] Affected modules identified
- [ ] Version number updated

## Review Decision

### Ready to Merge

- [ ] Ruthless Simplicity: ✓ PASS
- [ ] Modular Architecture: ✓ PASS
- [ ] Zero-BS Implementation: ✓ PASS
- [ ] Test Coverage: ✓ ADEQUATE (85%+)
- [ ] Documentation: ✓ COMPLETE
- [ ] No blocking issues remaining

### Needs Improvements

List specific issues to address:

1. [ ] Issue 1
2. [ ] Issue 2
3. [ ] Issue 3

### Conditional Approval

- [ ] Approve with changes needed (non-blocking)
- [ ] Changes needed before merge (blocking)
- [ ] Specific items required

## Post-Review Actions

- [ ] Feedback provided in clear comments
- [ ] Specific file:line references included
- [ ] Suggestions are concrete, not vague
- [ ] Respectful and constructive tone
- [ ] Learning opportunity highlighted
- [ ] Good work acknowledged

## Learning Points

After this review, document:

- [ ] What pattern did we see?
- [ ] What principle was violated?
- [ ] How do we prevent this?
- [ ] Update DISCOVERIES.md if needed?
- [ ] Should we create tooling/linting for this?

## Reviewer Notes

Space for specific findings and observations:

```
[Review notes here]
```

---

## Quick Reference: Common Issues

### Over-Engineering

- [ ] Unnecessary abstraction layers
- [ ] Premature optimization
- [ ] Configuration complexity
- [ ] Generic "framework" building
- [ ] Feature flags for non-existent features

### Missing Tests

- [ ] New public functions untested
- [ ] Edge cases uncovered
- [ ] Error paths not tested
- [ ] Coverage below 85%

### Zero-BS Violations

- [ ] TODO comments
- [ ] Swallowed exceptions
- [ ] Silent failures (None returns)
- [ ] NotImplementedError in non-abstract code
- [ ] Dead code

### Module Issues

- [ ] No specification document
- [ ] Unclear public interface
- [ ] Circular dependencies
- [ ] Mixed responsibilities
- [ ] Unclear what's public vs private

### Documentation Gaps

- [ ] Missing docstrings
- [ ] No type hints
- [ ] Examples missing
- [ ] Module spec missing
- [ ] README not updated

---

## Print-Friendly Summary

**RUTHLESS SIMPLICITY**: Every line justified, no unnecessary abstractions
**MODULAR ARCHITECTURE**: Single responsibility, clear boundaries, no circular deps
**ZERO-BS IMPLEMENTATION**: Production-ready, no TODOs, explicit error handling
**TEST COVERAGE**: 85%+ coverage, contract verified, edge cases tested
**DOCUMENTATION**: Complete docstrings, type hints, examples, module specs

If all these pass → READY TO MERGE
If any fail → NEEDS IMPROVEMENTS
