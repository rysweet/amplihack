# Code Quality Fix Template

> **Coverage**: ~25% of all fixes
> **Target Time**: 30-60 seconds assessment, 1-3 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Error patterns:
- "lint", "format", "style"
- "E501", "W503", "C901" (error codes)
- "black", "ruff", "isort", "pyright", "mypy"
- "prettier", "eslint"
- "pre-commit hook failed"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Line Length | 25% | E501, line too long |
| Import Order | 20% | I001, isort, import sorting |
| Type Hints | 25% | pyright, mypy, type errors |
| Style Violations | 30% | various lint codes |

## Quick Assessment (30-60 sec)

### Step 1: Identify the Tool

```bash
# Check which tool is complaining
# Look for tool name in error output:
# - ruff, flake8, pylint → Python linting
# - black, ruff format → Python formatting
# - isort → Import sorting
# - pyright, mypy → Type checking
# - prettier → JS/TS/JSON formatting
# - eslint → JS/TS linting
```

### Step 2: Count and Classify Errors

```bash
# Quick error count
ruff check . 2>&1 | wc -l

# Most common error type
ruff check . 2>&1 | grep -oE '[A-Z]+[0-9]+' | sort | uniq -c | sort -rn | head -5
```

## Auto-Fix vs Manual Fix Classification

### Auto-Fixable (just run the tool)

| Error Type | Tool Command |
|------------|--------------|
| Formatting | `ruff format .` or `black .` |
| Import order | `ruff check --fix .` or `isort .` |
| Unused imports | `ruff check --fix .` |
| Simple lint issues | `ruff check --fix .` |
| Trailing whitespace | `ruff check --fix .` |

### Manual Fix Required

| Error Type | Why Manual |
|------------|------------|
| Type errors | Requires understanding intent |
| Line too long | Need to decide how to split |
| Complexity (C901) | Requires refactoring |
| Naming conventions | Semantic decision |
| Logic issues | Not style, actual bugs |

## Solution Steps by Tool

### Ruff (Preferred for Python)

**Run All Fixes**
```bash
# Format code
ruff format .

# Fix auto-fixable lint issues
ruff check --fix .

# Fix more aggressively (unsafe fixes)
ruff check --fix --unsafe-fixes .

# Check what remains
ruff check .
```

**Common Ruff Errors**

| Code | Issue | Fix |
|------|-------|-----|
| E501 | Line too long | Split line, use parentheses |
| F401 | Unused import | Remove or `# noqa: F401` |
| F841 | Unused variable | Remove or prefix with `_` |
| I001 | Import order | `ruff check --fix` |
| UP | Upgrade syntax | `ruff check --fix` |

**Configuration**
```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]  # If you want to allow long lines

[tool.ruff.format]
quote-style = "double"
```

### Pyright (Type Checking)

**Common Type Errors**

```python
# Error: Cannot assign None to str
name: str = None  # Wrong
name: str | None = None  # Right
name: Optional[str] = None  # Also right

# Error: Missing return type
def foo():  # Wrong
def foo() -> str:  # Right

# Error: Argument type mismatch
def greet(name: str): ...
greet(123)  # Wrong
greet(str(123))  # Right
```

**Quick Fixes**
```python
# Type ignore (use sparingly)
result = something()  # type: ignore

# Better: Cast when you know better
from typing import cast
result = cast(ExpectedType, something())

# Best: Fix the actual type
result: ExpectedType = something_that_returns_expected()
```

**Configuration**
```toml
# pyproject.toml
[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "basic"  # or "strict"
reportMissingTypeStubs = false
```

### Black (Formatting)

```bash
# Format all Python files
black .

# Check without modifying
black --check .

# Show diff
black --diff .
```

### isort (Import Sorting)

```bash
# Fix imports
isort .

# Check only
isort --check .

# Compatible with black
isort --profile black .
```

**Configuration**
```toml
# pyproject.toml
[tool.isort]
profile = "black"
line_length = 88
```

## Pre-commit Integration

### Setup Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/RobertCraiworthy/pyright-python
    rev: v1.1.390
    hooks:
      - id: pyright
```

### Run Pre-commit

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update hooks
pre-commit autoupdate

# Skip hooks temporarily (not recommended)
git commit --no-verify
```

## Handling Specific Issues

### Line Length (E501)

```python
# Strategy 1: Use parentheses for implicit continuation
result = (
    some_long_function_name(argument1, argument2)
    + another_long_function(argument3)
)

# Strategy 2: Break at logical points
very_long_string = (
    "First part of string "
    "second part of string"
)

# Strategy 3: Use variables to shorten
config = some_module.get_configuration()
result = config.process(data)

# Strategy 4: Ignore specific line (last resort)
long_url = "https://..."  # noqa: E501
```

### Import Order (I001)

```python
# Correct order:
# 1. Standard library
import os
import sys

# 2. Third-party
import pandas as pd
import requests

# 3. Local
from myproject import utils
from myproject.models import User
```

### Type Hint Fixes

```python
# Missing Optional
def get_user(id: int) -> User | None:  # Python 3.10+
    ...

# Generic types
def process(items: list[str]) -> dict[str, int]:
    ...

# Callable
from collections.abc import Callable
def apply(fn: Callable[[int], str]) -> None:
    ...

# Type alias for complex types
UserDict = dict[str, list[tuple[int, str]]]
def get_users() -> UserDict:
    ...
```

### Complexity Issues (C901)

```python
# Before: Complex function (C901)
def process(data):
    if condition1:
        if condition2:
            for item in data:
                if item.valid:
                    # deep nesting...

# After: Extract functions
def process(data):
    valid_items = filter_valid(data)
    return transform_items(valid_items)

def filter_valid(data):
    return [item for item in data if item.valid]

def transform_items(items):
    return [transform(item) for item in items]
```

## Validation Steps

### Pre-Commit Validation

```bash
# Run full quality check
ruff format --check .
ruff check .
pyright

# Or via pre-commit
pre-commit run --all-files
```

### Post-Fix Validation

```bash
# 1. Run formatters
ruff format .

# 2. Run fixers
ruff check --fix .

# 3. Verify clean
ruff check . && pyright && echo "All clean!"
```

## Escalation Criteria

### Escalate When

- Type errors require architectural changes
- Lint rules conflict with project requirements
- Need to add/modify tool configuration
- Circular import issues (see import-fix.md)
- Performance-related style changes

### Information to Gather

```
1. Specific error codes and messages
2. Tool and version being used
3. Current configuration (pyproject.toml)
4. Number of errors (isolated vs widespread)
5. Is this new code or regression?
```

## Quick Reference

### Fastest Fixes (< 30 sec)

```bash
# One command to fix most issues
ruff format . && ruff check --fix .
```

### Error Code Lookup

```
E = pycodestyle errors
W = pycodestyle warnings
F = pyflakes
I = isort
UP = pyupgrade
B = bugbear
C = complexity
S = bandit (security)
```

### Common Disable Patterns

```python
# Disable for line
x = 1  # noqa: E501

# Disable for file (top of file)
# ruff: noqa: E501

# Disable in config
[tool.ruff.lint]
ignore = ["E501"]

# Type ignore
result = foo()  # type: ignore[return-type]
```
