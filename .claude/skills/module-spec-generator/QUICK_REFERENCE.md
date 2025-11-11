# Module Spec Generator: Quick Reference

## When to Use This Skill

| Scenario                 | Command                           | Output               |
| ------------------------ | --------------------------------- | -------------------- |
| Plan new module          | Generate spec before coding       | Specs/module-name.md |
| Document existing module | Analyze working code              | Specs/module-name.md |
| Verify spec accuracy     | Compare spec vs code              | Discrepancy report   |
| Design review            | Check brick philosophy compliance | Review feedback      |

## Specification Template (One Page)

````markdown
# [Module Name] Specification

## Purpose

[One sentence describing core responsibility]

## Public Interface

### Functions

```python
def function_name(param: Type) -> ReturnType:
    """Brief description.
    Args: ...
    Returns: ...
    Raises: ...
    """
```
````

### Classes

- `ClassName`: Description with key methods

### Constants

- `CONSTANT_NAME`: Description

## Dependencies

- External: [package name (version)]
- Internal: [module path]

## Module Structure

```
module_name/
├── __init__.py
├── core.py
├── tests/
└── examples/
```

## Test Requirements

- ✅ Test 1: description
- ✅ Test 2: description
- ✅ Coverage: 85%+

## Example Usage

```python
from module_name import function, Class
# usage examples
```

## Regeneration Notes

This module can be rebuilt from this spec preserving:

- ✅ Public contract
- ✅ Dependencies
- ✅ Test interface

```

## Brick Philosophy Checklist

```

BRICK = Self-contained module with ONE clear responsibility
STUD = Public connection point (function/class/API)
REGENERATABLE = Can rebuild without breaking connections

```

**Every spec must answer:**
- [ ] What is the SINGLE core responsibility?
- [ ] What are the PUBLIC "studs"?
- [ ] What dependencies does it have?
- [ ] Can someone rebuild it from this spec alone?

## Common Mistakes to Avoid

| Mistake | Wrong | Right |
|---------|-------|-------|
| Multiple responsibilities | "Handles auth, validation, caching" | "Validates JWTs" |
| Implementation details | "Use Pydantic + Redis" | "Validate and cache" |
| Vague signatures | "def check(x)" | "def validate(token: str) -> Payload" |
| Missing errors | "Returns result" | "Raises ValueError if invalid" |
| No examples | "See code for usage" | Include 3-5 working examples |
| Unclear dependencies | "Some packages" | "PyJWT 2.8+, PyYAML 6.0+" |

## Analysis Workflow (Steps 1-10)

1. **Explore Structure**: `ls -la module_dir/` - map files
2. **Read Exports**: `cat __init__.py` - see `__all__`
3. **Analyze Functions**: Read function signatures and docstrings
4. **Document Classes**: Classes, attributes, key methods
5. **Map Dependencies**: All imports, categorize them
6. **Check Tests**: Count tests, identify coverage areas
7. **Review Examples**: Look for working code
8. **Draft Spec**: Synthesize all findings
9. **Validate Spec**: Verify completeness
10. **Write Document**: Create Specs/module-name.md

## File Locations

```

.claude/skills/module-spec-generator/
├── SKILL.md # Full skill documentation
├── README.md # Skill overview and philosophy
├── QUICK_REFERENCE.md # This file
├── examples/
│ ├── simple-utility-spec.md # Simple module example
│ ├── session-management-spec.md # Complex module example
│ └── analysis-workflow.md # Step-by-step analysis

```

## Key Principles

### Ruthless Simplicity
- No unnecessary abstractions
- Functions do one thing
- No future-proofing
- Obvious implementations

### Single Responsibility
- Module has ONE core job
- "Handles X" not "Handles A, B, C, D"
- Everything serves that core purpose

### No External Dependencies (When Possible)
- Pure Python > external package
- Standard library > PyPI
- Dependencies justified explicitly

### Regeneratable
- Spec is THE source of truth
- Can rebuild module from spec alone
- Implementation is just details
- Preserves all connection points

### Clear Contracts
- All exports documented
- Type hints specified
- Errors explicit
- Examples provided

## Spec Length Guidelines

| Module Type | Typical Spec Length |
|-------------|-------------------|
| Utility functions (3-5 functions) | 1-2 pages |
| Class-based module (1-2 classes) | 2-3 pages |
| Integration module (API wrapper) | 3-4 pages |
| Complex infrastructure | 4-5 pages |

*If spec exceeds 5 pages, module probably does too much - consider splitting it.*

## Questions to Ask While Analyzing

1. **Purpose**: What is the ONE core job of this module?
2. **Interface**: What exactly is exported? Are names clear?
3. **Usage**: How would someone use this?
4. **Dependencies**: Why is each dependency needed?
5. **Errors**: What can fail and how is it handled?
6. **Tests**: What behaviors must be guaranteed?
7. **Regeneration**: Could I rebuild this from the spec?

## Spec Validation Questions

- [ ] Is there ONE clear core responsibility?
- [ ] Are all exports documented?
- [ ] Are type hints specified?
- [ ] Are error conditions documented?
- [ ] Are examples provided and working?
- [ ] Are dependencies justified?
- [ ] Are test requirements clear?
- [ ] Could someone rebuild from this spec?
- [ ] Does it follow brick philosophy?
- [ ] Would implementation match spec exactly?

## Integration Points

### Creating New Modules
1. Generate spec with this skill
2. Review and refine with team
3. Pass to Builder Agent
4. Builder implements from spec
5. Reviewer verifies code matches spec

### Documenting Existing Modules
1. Analyze module with this skill
2. Generate spec
3. Compare spec vs code
4. Update spec if needed
5. Store in Specs/ for reference

### Architecture Decisions
1. Use this skill to clarify design
2. Generate spec for review
3. Debate alternatives based on specs
4. Choose best approach
5. Implement from final spec

## Common Module Types

### Type 1: Utility Functions
**Example**: string_utils, math_utils, path_utils

```

Public Interface: 3-5 focused functions
Dependencies: Often none (pure Python)
Tests: Unit tests for each function
Complexity: Low
Spec Size: 1-2 pages

```

### Type 2: Class-Based Module
**Example**: session_management, configuration, models

```

Public Interface: 1-3 classes + helper functions
Dependencies: Usually internal + standard library
Tests: Unit tests + integration tests
Complexity: Medium
Spec Size: 2-3 pages

```

### Type 3: Integration Module
**Example**: github_client, database_driver, api_wrapper

```

Public Interface: High-level functions wrapping external service
Dependencies: External package + internal models
Tests: Unit + integration + fixture handling
Complexity: Medium-High
Spec Size: 3-4 pages

```

### Type 4: Data Models
**Example**: config models, database schemas, message formats

```

Public Interface: Classes/dataclasses with fields
Dependencies: Often none
Tests: Validation + serialization tests
Complexity: Low
Spec Size: 1-2 pages

```

## Examples in This Skill

1. **simple-utility-spec.md**
   - Type: Utility functions (truncate, normalize, slugify)
   - Complexity: Low
   - Use as template for simple modules

2. **session-management-spec.md**
   - Type: Class-based infrastructure
   - Complexity: Medium
   - Use as template for complex modules

3. **analysis-workflow.md**
   - Real-world step-by-step analysis
   - Shows how to extract spec from existing code
   - Use as process guide

## Success Indicators

✅ **Your spec is good if...**
- Someone could rebuild the module without asking questions
- All functions/classes are explained
- Error conditions are clear
- Examples actually work
- Dependencies are justified
- It's 1-4 pages (concise)
- Follows brick philosophy
- Matches the actual implementation

❌ **Your spec needs work if...**
- You're unsure what the module does
- You can't explain it in one sentence
- There are multiple core responsibilities
- Dependencies aren't justified
- Examples don't work
- Test requirements are vague
- It's more than 5 pages
- It describes HOW instead of WHAT

## Next Steps After Spec

1. **For new modules**: Pass spec to Builder Agent
2. **For existing modules**: File in Specs/ directory
3. **For architecture**: Use spec to debate design
4. **For reviews**: Reference spec as contract
5. **For updates**: Update spec first, then code

## Module Regeneration Process

When code needs updating:

```

1. Update spec with new requirements
   ↓
2. Pass updated spec to Builder Agent
   ↓
3. Builder rebuilds module to match new spec
   ↓
4. Tests verify behavior matches spec
   ↓
5. Module is updated
   ↓
6. All connections preserved (studs unchanged)

```

This is why clear specs enable rapid iteration.
```
