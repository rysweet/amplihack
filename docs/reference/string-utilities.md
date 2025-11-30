# String Utilities Reference

Complete API reference for amplihack string manipulation utilities.

## Overview

The `amplihack.utils.string_utils` module provides utilities for text manipulation, URL slug generation, and string sanitization.

## Functions

### slugify()

Convert strings to URL-friendly slugs.

```python
def slugify(text: str, max_length: int = 0) -> str
```

**Purpose**: Transform arbitrary strings into lowercase, hyphen-separated slugs suitable for URLs, filenames, and identifiers.

**Parameters**:

- `text` (str): The string to convert to a slug
- `max_length` (int, optional): Maximum length of the output slug. 0 means no limit. Default: 0

**Returns**: str - URL-friendly slug string

**Behavior**:

- Converts to lowercase
- Replaces spaces and underscores with hyphens
- Removes special characters (keeps only a-z, 0-9, hyphens)
- Collapses multiple consecutive hyphens to single hyphen
- Strips leading and trailing hyphens
- Handles Unicode by transliterating (café → cafe)
- Idempotent: `slugify(slugify(x)) == slugify(x)`
- Pure function: no side effects, same input always produces same output

**Examples**:

```python
from amplihack.utils.string_utils import slugify

# Basic usage
slug = slugify("Hello World")
print(slug)
# Output: hello-world

# Unicode handling
slug = slugify("Café au Lait")
print(slug)
# Output: cafe-au-lait

# Special characters removed
slug = slugify("Hello! World? #awesome")
print(slug)
# Output: hello-world-awesome

# Multiple spaces collapsed
slug = slugify("Hello   World")
print(slug)
# Output: hello-world

# Max length enforcement
slug = slugify("This is a very long title that should be truncated", max_length=20)
print(slug)
# Output: this-is-a-very-long

# Underscores converted to hyphens
slug = slugify("snake_case_string")
print(slug)
# Output: snake-case-string

# Numbers preserved
slug = slugify("Python 3.11 Release")
print(slug)
# Output: python-3-11-release

# Idempotent behavior
original = slugify("Hello World")
repeated = slugify(original)
assert original == repeated
# Output: hello-world (both times)

# Empty string handling
slug = slugify("")
print(slug)
# Output: ""

# Only special characters
slug = slugify("!@#$%^&*()")
print(slug)
# Output: ""
```

**Edge Cases**:

| Input                          | Output    | Notes                                             |
| ------------------------------ | --------- | ------------------------------------------------- |
| `""`                           | `""`      | Empty string returns empty string                 |
| `"   "`                        | `""`      | Whitespace-only returns empty string              |
| `"!@#$"`                       | `""`      | Special chars only returns empty string           |
| `"a--b"`                       | `"a-b"`   | Multiple hyphens collapsed                        |
| `"-hello-"`                    | `"hello"` | Leading/trailing hyphens stripped                 |
| `"HELLO"`                      | `"hello"` | Uppercase converted to lowercase                  |
| `"hello world"` (max_length=5) | `"hello"` | Truncation happens at word boundary when possible |

**Character Handling**:

| Character Type | Behavior                  | Example                            |
| -------------- | ------------------------- | ---------------------------------- |
| Uppercase A-Z  | Convert to lowercase      | `"Hello"` → `"hello"`              |
| Lowercase a-z  | Keep as-is                | `"hello"` → `"hello"`              |
| Digits 0-9     | Keep as-is                | `"test123"` → `"test123"`          |
| Spaces         | Replace with hyphen       | `"hello world"` → `"hello-world"`  |
| Underscores    | Replace with hyphen       | `"hello_world"` → `"hello-world"`  |
| Hyphens        | Keep (collapse multiples) | `"hello--world"` → `"hello-world"` |
| Accented chars | Transliterate             | `"café"` → `"cafe"`                |
| Special chars  | Remove                    | `"hello!"` → `"hello"`             |

**Common Use Cases**:

1. **URL generation**: Convert page titles to URL slugs
2. **Filename sanitization**: Make safe filenames from user input
3. **Identifier creation**: Generate database keys from text
4. **Tag normalization**: Standardize user-entered tags
5. **Search optimization**: Create searchable identifiers

**Thread Safety**: Yes - pure function with no shared state

**Performance**: O(n) where n is the length of input string

**See Also**:

- [How-To: Generate URL Slugs](../howto/generate-url-slugs.md) - Common usage patterns
- [Tutorial: String Sanitization](../tutorials/string-sanitization.md) - Learn string cleaning techniques

---

**Module**: `amplihack.utils.string_utils`

**Import**: `from amplihack.utils.string_utils import slugify`

**Version**: Added in amplihack 0.1.0

**Last Updated**: 2025-11-30
