# String Utils Specification

**Issue**: Example for module-spec-generator skill
**Type**: Utility Module
**Complexity**: Simple

## Purpose

Provide common string manipulation utilities with consistent behavior and clear error handling. Single responsibility: transform strings according to well-defined rules.

## Scope

**Handles**:

- Text truncation with length constraints
- Whitespace normalization
- URL-safe slug conversion
- Clear, simple operations

**Does NOT handle**:

- Internationalization (i18n) or complex Unicode handling
- Regular expression validation
- HTML/XML parsing or encoding
- Text encoding (assumes UTF-8)

## Philosophy Alignment

- ✅ **Ruthless Simplicity**: Three focused functions, no abstractions
- ✅ **Single Responsibility**: String manipulation utilities only
- ✅ **No External Dependencies**: Pure Python standard library only
- ✅ **Regeneratable**: Spec completely defines implementation contract

## Public Interface (The "Studs")

### Functions

```python
def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length, appending suffix if truncated.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: String to append if truncated (default: "...")

    Returns:
        Truncated string, max length as specified

    Raises:
        ValueError: If max_length < len(suffix)
        TypeError: If text is not a string

    Example:
        >>> truncate("Hello World", 8, "...")
        'Hello...'
        >>> truncate("Hi", 8)
        'Hi'
    """

def normalize(text: str) -> str:
    """Normalize whitespace by removing leading/trailing and collapsing internal.

    Args:
        text: String to normalize

    Returns:
        String with normalized whitespace

    Raises:
        TypeError: If text is not a string

    Example:
        >>> normalize("  Hello   World  ")
        'Hello World'
        >>> normalize("Line\n  \n  2")
        'Line 2'
    """

def slugify(text: str, max_length: int = None) -> str:
    """Convert text to URL-safe slug (lowercase, hyphens, alphanumeric only).

    Args:
        text: String to convert
        max_length: Optional maximum length for slug

    Returns:
        URL-safe slug in lowercase

    Raises:
        TypeError: If text is not a string
        ValueError: If result would be empty

    Example:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Python & Django", 10)
        'python'
    """
```

### Constants

None - this module has no module-level constants.

### No Classes

This module exports only functions. It does not define custom classes or data models.

## Dependencies

### External

None - pure Python standard library only.

### Internal

None - completely standalone module.

### Standard Library Used

- `string` module for character classifications
- `re` module for pattern matching (optional, only if needed)

## Module Structure

```
string_utils/
├── __init__.py              # Exports: truncate, normalize, slugify
├── core.py                  # All three functions implemented here
├── tests/
│   ├── __init__.py
│   ├── test_truncate.py    # Tests for truncate function
│   ├── test_normalize.py   # Tests for normalize function
│   ├── test_slugify.py     # Tests for slugify function
│   └── fixtures/
│       └── sample_text.txt # Sample text for testing
└── examples/
    └── usage.py            # Usage examples
```

## Module Boundaries

### **init**.py

```python
from .core import truncate, normalize, slugify

__all__ = ["truncate", "normalize", "slugify"]
```

### core.py

Contains all three function implementations. Focus on clarity and correctness, not optimization.

### tests/

Four separate test files, one per function, plus shared fixtures.

## Test Requirements

### truncate() Tests

- ✅ Truncate longer string with default suffix
- ✅ Truncate with custom suffix
- ✅ Don't truncate if already short enough
- ✅ Raise ValueError if max_length < suffix length
- ✅ Handle edge case: text exactly max_length
- ✅ Handle edge case: text one char longer than max_length
- ✅ Raise TypeError if text is not string

### normalize() Tests

- ✅ Remove leading whitespace
- ✅ Remove trailing whitespace
- ✅ Collapse multiple spaces to single space
- ✅ Handle tabs and newlines as whitespace
- ✅ Already normalized text unchanged
- ✅ Empty string returns empty string
- ✅ Whitespace-only string returns empty string
- ✅ Raise TypeError if text is not string

### slugify() Tests

- ✅ Convert to lowercase
- ✅ Replace spaces with hyphens
- ✅ Remove special characters
- ✅ Remove punctuation
- ✅ Handle consecutive hyphens
- ✅ Return empty slug → raise ValueError
- ✅ Optional max_length truncation
- ✅ Raise TypeError if text is not string

### Coverage

85%+ line coverage across all functions.

## Example Usage

```python
from string_utils import truncate, normalize, slugify

# Truncation examples
title = "The Quick Brown Fox Jumps Over The Lazy Dog"
short = truncate(title, 20)
print(short)  # "The Quick Brown F..."

# Normalization examples
messy = "  Hello    World  \n  How are you?  "
clean = normalize(messy)
print(clean)  # "Hello World How are you?"

# Slugify examples
article_title = "Python & Django Best Practices!"
slug = slugify(article_title)
print(slug)  # "python-django-best-practices"

# With length constraint
slug_short = slugify(article_title, max_length=15)
print(slug_short)  # "python-django"
```

## Implementation Notes

### Simplicity First

These implementations should be straightforward:

```python
# Example: truncate - simple, no tricks
def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if max_length < len(suffix):
        raise ValueError("max_length must be >= suffix length")

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
```

### No Over-Engineering

- Don't add configuration options not in the spec
- Don't optimize prematurely
- Don't anticipate future uses
- Keep implementations obvious and readable

### Error Clarity

When raising errors:

- Include the problematic value
- Explain what was wrong
- Suggest how to fix it

```python
raise ValueError(
    f"max_length ({max_length}) must be >= suffix length ({len(suffix)})"
)
```

## Regeneration Notes

This module can be rebuilt from this specification while maintaining:

- ✅ Public contract (truncate, normalize, slugify always available)
- ✅ Function signatures (same types, same behavior)
- ✅ Error handling (same exceptions, same conditions)
- ✅ Test interface (all test requirements preserved)
- ✅ Module structure (same files and organization)

Any new implementation can be verified by:

1. Checking all three functions exist with correct signatures
2. Running the test suite
3. Checking that all examples work correctly
4. Verifying coverage >= 85%

## Quality Checklist

- [ ] Single responsibility: String utilities only
- [ ] Public interface complete: truncate, normalize, slugify
- [ ] Dependencies explicit: Standard library only
- [ ] Tests exhaustive: Cover normal, edge, and error cases
- [ ] Examples working: All code in this spec is valid Python
- [ ] Spec is complete: Could rebuild module from this spec alone
- [ ] No implementation details: Just the contract
- [ ] Clear error messages: When things fail
- [ ] Follows simplicity: Three functions, no complexity
