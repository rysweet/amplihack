# Module Spec Generation: Analysis Workflow

This document walks through the step-by-step process of analyzing an existing module and generating its specification.

## Example: Analyzing the String Utils Module

Suppose we have an existing module at `~/.amplihack/.claude/tools/amplihack/string_utils/` and we want to generate its specification.

### Step 1: Explore Module Structure

```bash
ls -la .claude/tools/amplihack/string_utils/

Output:
├── __init__.py
├── core.py
├── utils.py
├── tests/
│   ├── test_core.py
│   ├── test_utils.py
│   └── fixtures/
│       └── sample_text.txt
└── examples/
    └── usage.py
```

**What we learned**:

- Main code in `core.py` and `utils.py`
- Tests in `tests/` directory
- Examples provided
- Appears to be well-organized

### Step 2: Read the Public Interface (**init**.py)

```python
# .claude/tools/amplihack/string_utils/__init__.py
from .core import truncate, normalize, slugify
from .utils import TextMetrics, COMMON_STOPWORDS

__all__ = ["truncate", "normalize", "slugify", "TextMetrics", "COMMON_STOPWORDS"]
```

**What we learned**:

- Exports: three functions and one class
- Primary exports from `core.py`
- Utility exports from `utils.py`

### Step 3: Analyze Core Functions

```python
# .claude/tools/amplihack/string_utils/core.py

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
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if max_length < len(suffix):
        raise ValueError(...)

    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def normalize(text: str) -> str:
    """Normalize whitespace by removing leading/trailing and collapsing internal.

    Args:
        text: String to normalize

    Returns:
        String with normalized whitespace
    """
    return ' '.join(text.split())


def slugify(text: str, max_length: int = None) -> str:
    """Convert text to URL-safe slug (lowercase, hyphens, alphanumeric only).

    Args:
        text: String to convert
        max_length: Optional maximum length for slug

    Returns:
        URL-safe slug in lowercase

    Raises:
        ValueError: If result would be empty
    """
    slug = '-'.join(
        word for word in text.lower().split()
        if word.isalnum() or '-' in word
    )

    if not slug:
        raise ValueError("Slugify resulted in empty string")

    if max_length:
        slug = truncate(slug, max_length, '')

    return slug
```

**What we learned**:

- Three focused functions
- Good docstrings with Args, Returns, Raises
- Type hints present
- Error handling clear
- Truncate is used by slugify (internal dependency)

### Step 4: Analyze Utilities

```python
# .claude/tools/amplihack/string_utils/utils.py

class TextMetrics:
    """Analyze and report string metrics."""

    def __init__(self, text: str):
        self.text = text

    def word_count(self) -> int:
        """Return number of words."""
        return len(self.text.split())

    def char_count(self) -> int:
        """Return character count."""
        return len(self.text)

    def avg_word_length(self) -> float:
        """Return average word length."""
        words = self.text.split()
        return sum(len(w) for w in words) / len(words) if words else 0


COMMON_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by",
    "for", "from", "has", "he", "in", "is", "it", "its", "of",
    "on", "or", "that", "the", "to", "was", "with"
}
```

**What we learned**:

- TextMetrics class for analysis
- Three simple methods
- COMMON_STOPWORDS constant (pre-defined set)

### Step 5: Check Test Coverage

```python
# .claude/tools/amplihack/string_utils/tests/test_core.py

class TestTruncate:
    def test_truncate_longer_string(self):
        assert truncate("Hello World", 8, "...") == "Hello..."

    def test_no_truncate_if_short(self):
        assert truncate("Hi", 8) == "Hi"

    def test_invalid_max_length(self):
        with pytest.raises(ValueError):
            truncate("text", 2, "...")

    # ... more tests


class TestNormalize:
    def test_normalize_spaces(self):
        assert normalize("  Hello   World  ") == "Hello World"

    def test_normalize_newlines(self):
        assert normalize("Hello\n\nWorld") == "Hello World"

    # ... more tests


class TestSlugify:
    def test_basic_slugify(self):
        assert slugify("Hello World") == "hello-world"

    def test_slugify_with_special_chars(self):
        assert slugify("Hello & World!") == "hello-world"

    def test_empty_result_raises(self):
        with pytest.raises(ValueError):
            slugify("!!!")
```

**What we learned**:

- Good test coverage
- Tests normal cases, edge cases, and errors
- Uses pytest

### Step 6: Review Examples

```python
# .claude/tools/amplihack/string_utils/examples/usage.py

from string_utils import truncate, normalize, slugify, TextMetrics

# Example 1: Truncation
title = "The Quick Brown Fox Jumps Over The Lazy Dog"
print(truncate(title, 20))  # "The Quick Brown F..."

# Example 2: Normalization
messy = "  Hello    World  \n  How are you?  "
print(normalize(messy))  # "Hello World How are you?"

# Example 3: Slugification
article = "Python & Django Best Practices!"
print(slugify(article))  # "python-django-best-practices"

# Example 4: Text metrics
text = "Hello World"
metrics = TextMetrics(text)
print(f"Words: {metrics.word_count()}")      # 2
print(f"Chars: {metrics.char_count()}")      # 11
print(f"Avg len: {metrics.avg_word_length()}")  # 5.5
```

**What we learned**:

- Clear usage examples
- All functions demonstrated
- TextMetrics usage shown

### Step 7: Check Dependencies

```python
# Review all imports
# core.py: no imports (uses only builtins)
# utils.py: no imports (uses only builtins)
# tests: pytest (testing only, not runtime)
```

**What we learned**:

- Pure Python, no external dependencies
- Standard library only
- Even tests don't need external libraries (except pytest)

### Step 8: Draft Specification

Based on the analysis above, we can now draft the specification:

```markdown
# String Utils Specification

## Purpose

Provide common string manipulation utilities with consistent behavior and clear error handling.

## Public Interface

### Functions

- `truncate(text: str, max_length: int, suffix: str = "...") -> str`
- `normalize(text: str) -> str`
- `slugify(text: str, max_length: int = None) -> str`

### Classes

- `TextMetrics`: Analyze text with word_count(), char_count(), avg_word_length()

### Constants

- `COMMON_STOPWORDS`: Set of 18 common English words

## Dependencies

- External: None
- Internal: None

## Test Requirements

✅ Truncate: 5+ tests (normal, edge, error cases)
✅ Normalize: 4+ tests (spaces, newlines, empty, whitespace-only)
✅ Slugify: 4+ tests (basic, special chars, empty result, max_length)
✅ TextMetrics: 3+ tests (word_count, char_count, avg_word_length)
✅ Coverage: 85%+

## Module Structure

(as observed above)

## Example Usage

(from usage.py above)
```

### Step 9: Validate Specification

Check that the spec:

- [ ] Accurately reflects the code
- [ ] Documents all exported items
- [ ] Lists all dependencies correctly
- [ ] Test requirements match actual tests
- [ ] Examples are working code
- [ ] Someone could rebuild module from this spec

**Result**: Specification is accurate and complete.

### Step 10: Write Specification Document

Create `/Specs/string-utils.md` with complete specification incorporating all above analysis.

## Practical Analysis Checklist

When analyzing a module to generate its spec:

### Code Files

- [ ] Read all `*.py` files in module
- [ ] Identify `__init__.py` exports
- [ ] Extract all function signatures
- [ ] Document all classes and methods
- [ ] List all module constants
- [ ] Check for data models (dataclass, NamedTuple, etc.)

### Dependencies

- [ ] List all imports in each file
- [ ] Categorize: standard library, external, internal
- [ ] Note version requirements if specified
- [ ] Identify circular dependencies (red flag)
- [ ] Check for optional dependencies

### Tests

- [ ] Count test files and test functions
- [ ] Identify test coverage areas
- [ ] Note edge cases being tested
- [ ] Check error handling tests
- [ ] Look for integration tests

### Documentation

- [ ] Read existing docstrings
- [ ] Review any READMEs
- [ ] Check for inline comments
- [ ] Look at examples

### Module Structure

- [ ] Map directory organization
- [ ] Note what files handle what
- [ ] Identify test organization
- [ ] Check for example files

### Philosophy Alignment

- [ ] Single responsibility: Does module do ONE thing?
- [ ] Simplicity: Are implementations straightforward?
- [ ] Dependencies: Are they justified?
- [ ] Public interface: Is it minimal and clear?
- [ ] Regeneratable: Could this module be rebuilt from the spec?

## Common Patterns to Document

### Pattern 1: Simple Function Module

```
✅ Functions only, no classes
✅ Single responsibility
✅ Pure Python, no dependencies
Example: string_utils
```

### Pattern 2: Class-Based Module

```
✅ One main class (or small set)
✅ Related helper functions
✅ Data models if needed
Example: session_management
```

### Pattern 3: Integration Module

```
✅ Wraps external service (API, database)
✅ Clear error handling
✅ Dependencies documented
Example: github_client
```

### Pattern 4: Data Structures Module

```
✅ Primarily classes/dataclasses
✅ Minimal methods
✅ Focuses on schema/structure
Example: models
```

## Specification Quality Metrics

After generating a spec, measure:

1. **Completeness**: Does it describe all public items? (100% = 1.0)
2. **Clarity**: Would someone understand how to use this? (1-5 scale)
3. **Precision**: Are types, errors, and returns specific? (1-5 scale)
4. **Regenerability**: Could someone rebuild from this spec? (1-5 scale)

**Target**: Completeness = 1.0, Clarity >= 4, Precision >= 4, Regenerability >= 4

## Automation Possibilities

While this skill is designed for Claude to guide the analysis, future enhancements could include:

1. **AST Analysis**: Automatically extract function signatures
2. **Import Analysis**: Automatically categorize dependencies
3. **Coverage Detection**: Read coverage reports
4. **Documentation Generation**: Auto-populate from docstrings
5. **Diff Detection**: Compare spec vs. implementation

However, the human expertise in understanding PURPOSE and RESPONSIBILITY is irreplaceable and should always drive specification quality.
