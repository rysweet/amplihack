# Module Spec Generator Skill

## Overview

The module-spec-generator is a Claude Code skill that automatically generates comprehensive module specifications following amplihack's **brick philosophy**. It analyzes existing or planned module code to extract the essential blueprint that enables any module to be rebuilt without breaking system connections.

## Quick Start

### Generate Spec for New Module

```
Claude, generate a spec for a new authentication module with:
- JWT token validation
- Role-based access control
- Error handling for invalid tokens
```

Claude will:
1. Clarify the module's scope and boundaries
2. Define the public contract (exported functions and classes)
3. Identify dependencies
4. Create test requirements
5. Generate `Specs/authentication.md`

### Generate Spec for Existing Module

```
Claude, generate a spec for the module at .claude/tools/amplihack/session/
```

Claude will:
1. Analyze all Python files in the module
2. Extract the public interface from `__init__.py`
3. Document all exported functions and classes
4. Map dependencies
5. Create `Specs/session-management.md`

### Verify Spec Matches Implementation

```
Claude, verify that Specs/caching.md accurately describes
the actual implementation in .claude/tools/amplihack/caching/
```

Claude will:
1. Read the specification
2. Analyze the actual code
3. Compare public contracts
4. Report discrepancies
5. Suggest corrections

## What Makes a Good Module Spec

A good spec enables the **Builder Agent** to implement the module correctly without asking questions. It defines:

### 1. Single, Clear Responsibility
```
GOOD: "Handles JWT token validation and refresh"
BAD: "Handles authentication, validation, user management, logging, and metrics"
```

### 2. Complete Public Contract (The "Studs")
```python
# Good: Clear, type-hinted, documented
def validate_token(token: str, secret: str) -> TokenPayload:
    """Validate JWT token and return decoded payload.

    Args:
        token: JWT token string
        secret: Secret key for validation

    Returns:
        TokenPayload with decoded claims

    Raises:
        ValueError: If token is invalid or expired
    """

# Bad: Unclear what it returns or when it fails
def check_token(tok):
    """Check a token"""
```

### 3. Explicit Dependencies
```markdown
## Dependencies

### External
- `PyJWT` (2.8+): Token encoding/decoding

### Internal
- `.models.TokenPayload`: Data structure
- `.exceptions`: Error definitions

### None
Pure Python standard library.
```

### 4. Realistic Test Requirements
```
## Test Requirements

### Core Functionality
- ✅ Valid token validation succeeds
- ✅ Expired token raises ValueError
- ✅ Invalid signature raises ValueError
- ✅ Malformed token raises ValueError

### Contract Verification
- ✅ TokenPayload has all expected fields
- ✅ Functions accept documented types
- ✅ Error messages are clear

### Coverage
85%+ line coverage
```

### 5. Working Examples
```python
from authentication import validate_token, TokenPayload

# Example: Validate a token
try:
    payload = validate_token(token, secret)
    print(f"User: {payload.user_id}, Role: {payload.role}")
except ValueError as e:
    print(f"Invalid token: {e}")
```

## Brick Philosophy in Specs

### What is a "Brick"?
- Self-contained module with ONE clear responsibility
- Can be rebuilt independently
- All code, tests, examples in one directory

### What are "Studs"?
- Public connection points (exported functions, classes)
- Clear, documented interface
- Type-hinted with examples

### Why Regeneratable?
- When code changes, rebuild from the spec
- Spec defines the contract, code is an implementation
- If implementation diverges from spec, spec is authoritative

## Module Spec Template Structure

Every spec includes:

```
# Module Name Specification

## Purpose
[One sentence core responsibility]

## Public Interface (The "Studs")
[Exported functions, classes, constants]

## Dependencies
[What it depends on - external and internal]

## Module Structure
[File organization and what goes where]

## Test Requirements
[What must be tested]

## Example Usage
[Working code examples]

## Regeneration Notes
[Why this module can be rebuilt from spec]
```

## Real-World Examples

### Example 1: Simple Utility Module

```markdown
# String Utils Specification

## Purpose
Provide common string manipulation utilities with consistent error handling.

## Public Interface
- `truncate(text: str, length: int) -> str`: Truncate to max length
- `normalize(text: str) -> str`: Normalize whitespace
- `slugify(text: str) -> str`: Convert to URL-safe slug

## Dependencies
- External: None
- Internal: None

## Test Requirements
- ✅ truncate preserves UTF-8
- ✅ normalize removes extra whitespace
- ✅ slugify removes special characters
```

This spec enables the Builder Agent to implement all three functions with complete clarity.

### Example 2: Integration Module

```markdown
# GitHub API Client Specification

## Purpose
Simplified wrapper for GitHub API operations with error handling.

## Public Interface
- `create_issue(title: str, body: str) -> str`: Returns issue URL
- `get_pr_status(pr_number: int) -> PRStatus`: Returns current status
- `create_workflow_dispatch(workflow_id: str) -> bool`: Trigger workflow

## Dependencies
- External: `requests` (2.28+)
- Internal: `.models.PRStatus`

## Test Requirements
- ✅ HTTP errors are caught and re-raised as custom exceptions
- ✅ Credentials are validated before use
- ✅ JSON parsing handles malformed responses
```

This spec ensures the module handles GitHub API consistently and predictably.

## Specification Lifecycle

### Phase 1: Planning
Use spec generator to plan module BEFORE implementation.
```
User: Generate a spec for a new validation module
Claude: [Creates comprehensive spec]
User: Review spec, make changes
Claude: Update spec based on feedback
```

### Phase 2: Implementation
Builder Agent uses spec to implement.
```
Claude (Builder): Read spec and implement exactly as specified
→ Module works correctly
→ Tests pass
```

### Phase 3: Documentation
Spec becomes the authoritative documentation.
```
Other developers read spec to understand module
Other modules depend on the "studs" defined in spec
```

### Phase 4: Evolution
When requirements change, update the spec.
```
User: Module needs new function
Claude: Update spec first
Claude: Regenerate implementation from new spec
```

## Integration with Builder Agent

The Builder Agent can directly use module specs:

1. **Read spec**: `Specs/module-name.md`
2. **Implement from spec**: Create module exactly as specified
3. **Verify contract**: All exported items work as documented
4. **Test according to spec**: Implement test requirements
5. **Result**: Working module that matches spec perfectly

## Common Spec Mistakes to Avoid

### ❌ Mistake 1: Specifying Implementation

```
BAD: "Use Pydantic for validation, store in Redis cache"
GOOD: "Validate input according to schema, cache results"
```

The WHAT, not the HOW.

### ❌ Mistake 2: Ambiguous Contracts

```
BAD: "Handle errors gracefully"
GOOD: "Raise ValueError if input is invalid, return None if not found"
```

Be specific about behavior.

### ❌ Mistake 3: Unclear Dependencies

```
BAD: "Some external stuff"
GOOD: "PyJWT 2.8+, PyYAML 6.0+"
```

List exact packages and versions.

### ❌ Mistake 4: Missing Test Requirements

```
BAD: "Test that it works"
GOOD:
- ✅ Valid input returns expected output
- ✅ Invalid input raises ValueError
- ✅ Empty input returns None
```

Specify testable behaviors.

### ❌ Mistake 5: Insufficient Examples

```
BAD: "See code for usage"
GOOD: Include 3-5 realistic examples
```

Make it easy to understand intended usage.

## Verification Checklist

After generating a spec, verify:

- [ ] Single, clear responsibility
- [ ] Public interface is complete
- [ ] All exports are documented
- [ ] Type hints are precise
- [ ] Dependencies are listed
- [ ] Test requirements are realistic
- [ ] Examples are working code
- [ ] Someone could rebuild this module from spec alone
- [ ] Follows brick philosophy
- [ ] No implementation details
- [ ] No future-proofing or speculation

## Tips for Effective Specs

1. **Be Precise**: Vague specs lead to incorrect implementations
2. **Include Examples**: Working code clarifies intent better than prose
3. **List Errors**: Document what can fail and how
4. **Name Clearly**: Function/class names should be self-documenting
5. **Justify Dependencies**: If you need an external package, explain why
6. **Keep it Simple**: If the spec is complex, the module needs simplification
7. **Test Early**: Use spec to design tests before implementation
8. **Document Why**: Include context about design decisions
9. **Check Completeness**: Could someone rebuild this module from this spec?
10. **Embrace Regeneration**: Write specs that enable rebuilding

## Philosophy

This skill embodies amplihack's core values:

- **Ruthless Simplicity**: Specs focus on essentials, not implementation details
- **Brick Philosophy**: Clear contracts enable independent module building
- **Regeneratable**: Every module can be rebuilt from its spec
- **Human-AI Partnership**: Humans define specs, AI implements them
- **Trust in Emergence**: Simple, well-specified modules combine into complex systems

## Related Skills and Workflows

- **Builder Agent**: Implements modules from specs
- **Reviewer Agent**: Verifies code matches specs
- **Tester Agent**: Tests according to spec requirements
- **Document-Driven Development**: Uses specs as source of truth

## Feedback and Evolution

This skill should evolve based on usage:

- What makes specs more useful?
- What information is consistently needed?
- What leads to failed implementations?
- How can specs better prevent mistakes?

Document learnings in `.claude/context/DISCOVERIES.md`.
