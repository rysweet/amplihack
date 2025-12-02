# Code Quality Fix Template

**Usage**: 25% of all fixes - Linting violations, type errors, formatting issues, style guide compliance

## Problem Pattern Recognition

### Triggers

- Pre-commit hooks failing on linting
- CI failing on code quality checks
- Type checker errors (mypy, pyright)
- Formatting violations (black, prettier)
- Style guide violations (flake8, eslint)

### Error Indicators

```bash
# Common error patterns
"line too long"
"missing type annotation"
"unused import"
"undefined variable"
"trailing whitespace"
"indentation error"
```

## Quick Assessment (30 seconds)

### Step 1: Identify Tool

```bash
# Check which tool is failing
grep -E "(flake8|black|mypy|eslint|prettier)" error_output
```

### Step 2: Scope Check

```bash
# Single file or multiple?
wc -l error_output  # More than 10 lines = multiple issues
```

### Step 3: Severity Assessment

- **Simple**: Formatting, imports, whitespace
- **Medium**: Type annotations, variable naming
- **Complex**: Logic errors flagged by linter

## Solution Steps

### Simple Fixes (Auto-fixable)

```bash
# Python formatting
black .
isort .

# JavaScript formatting
prettier --write .

# Auto-fix linting where possible
flake8 --select=E,W --ignore=E501 . | head -20
```

### Type Annotation Fixes

```python
# Before
def process_data(data):
    return data.upper()

# After
def process_data(data: str) -> str:
    return data.upper()
```

### Import Cleanup

```python
# Remove unused imports
import ast  # Remove if not used
from typing import List, Dict  # Remove unused types

# Fix import order
from standard_library import os
from third_party import requests
from local_module import utils
```

### Common Pattern Fixes

#### Unused Variables

```python
# Before
result = expensive_calculation()
return True

# After
_ = expensive_calculation()  # Or remove if truly unused
return True
```

#### Line Length

```python
# Before
really_long_function_call_with_many_parameters(param1, param2, param3, param4, param5)

# After
really_long_function_call_with_many_parameters(
    param1, param2, param3,
    param4, param5
)
```

## Validation Steps

### 1. Run Quality Checks

```bash
# Python
black --check .
isort --check .
flake8 .
mypy .

# JavaScript
prettier --check .
eslint .

# General
pre-commit run --all-files
```

### 2. Verify No New Issues

```bash
# Compare before/after
git diff --stat
git status --porcelain
```

### 3. Test Impact

```bash
# Ensure fixes don't break functionality
pytest  # or relevant test command
```

## Integration Points

### With Pre-commit Diagnostic Agent

- Hand off complex pre-commit failures
- Use this template for standard quality issues
- Escalate architectural violations

### With CI Diagnostic Workflow

- Apply these fixes before CI re-run
- Use for quality-only CI failures
- Integrate with broader CI fix strategies

### With Main Workflow

- Apply during Step 7 (Pre-commit hooks)
- Use in Step 6 (Refactor and Simplify)
- Integrate with Step 14 (Final cleanup)

## Tool-Specific Guidance

### Python Quality Fixes

```bash
# Standard Python quality pipeline
black .
isort .
flake8 .
mypy .
bandit -r .  # Security
```

### JavaScript Quality Fixes

```bash
# Standard JavaScript quality pipeline
prettier --write .
eslint --fix .
tsc --noEmit  # Type check
```

### General Quality Fixes

```bash
# Cross-language tools
pre-commit run --all-files
git diff --check  # Whitespace
```

## Quick Reference

### 5-Minute Fix Checklist

- [ ] Run auto-formatters (black, prettier)
- [ ] Fix obvious imports and unused variables
- [ ] Add missing type annotations
- [ ] Run quality checks to verify
- [ ] Commit with descriptive message

### When to Escalate

- **Multiple files affected**: Use cleanup agent
- **Architectural violations**: Use reviewer agent
- **Complex type issues**: Use architect agent
- **Performance concerns**: Use optimizer agent

## Success Patterns

### High-Success Scenarios

- Formatting violations (98% success)
- Import order issues (95% success)
- Simple type annotations (90% success)
- Unused variable cleanup (88% success)

### Challenging Scenarios

- Complex type definitions (60% success)
- Architectural violations (40% success)
- Performance-related quality issues (50% success)

## Template Evolution

### Learning Integration

- Track fix success rates by tool
- Identify new common patterns
- Update auto-fix commands
- Improve escalation triggers

### Metrics to Track

- Time to resolution by issue type
- Success rate by tool
- Recurrence rate
- User satisfaction

Remember: Quality fixes should improve code without changing functionality. When in doubt, prioritize correctness over style.
