# Slugify Function - Enhanced Documentation

## Overview

The `slugify` function converts any input to a URL-safe slug format. It handles various input types gracefully and is available through the public API at `amplihack.utils.slugify`.

## Function Signature

```python
def slugify(text: str | int | float | bool | None) -> str:
    """Convert text to URL-safe slug format.

    Transforms any input into a URL-safe slug by:
    1. Handling None input (returns empty string)
    2. Converting non-string types (int, float, bool) to strings
    3. Normalizing Unicode (NFD) and converting to ASCII
    4. Converting to lowercase
    5. Replacing whitespace and special chars with hyphens
    6. Consolidating consecutive hyphens
    7. Stripping leading/trailing hyphens

    Args:
        text: Input of any type - string, number, boolean, or None.
              Lists and dicts will raise TypeError.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input is None or contains no valid characters.

    Raises:
        TypeError: If input is a list, dict, or other non-convertible type.
    """
```

## Type Handling

### Supported Types

1. **String**: Processed normally through the slugification pipeline
2. **None**: Returns empty string `""`
3. **Integer**: Converted to string (e.g., `123` → `"123"`)
4. **Float**: Converted to string with dot replaced by hyphen (e.g., `123.45` → `"123-45"`)
5. **Boolean**: Converted to lowercase string (e.g., `True` → `"true"`, `False` → `"false"`)

### Unsupported Types

Lists, dictionaries, and other complex types raise a `TypeError` with a descriptive message.

## Usage Examples

### Basic String Conversion

```python
from amplihack.utils import slugify

# Simple text
slugify("Hello World")  # Returns: "hello-world"

# Unicode normalization
slugify("Café")  # Returns: "cafe"

# Special characters
slugify("Rock & Roll")  # Returns: "rock-roll"
```

### Type Conversion Examples

```python
# None handling
slugify(None)  # Returns: ""

# Number conversion
slugify(123)  # Returns: "123"
slugify(123.45)  # Returns: "123-45"

# Boolean conversion
slugify(True)  # Returns: "true"
slugify(False)  # Returns: "false"
```

### Edge Cases

```python
# Empty string
slugify("")  # Returns: ""

# Already valid slug
slugify("already-a-slug")  # Returns: "already-a-slug"

# Only special characters
slugify("!!!")  # Returns: ""

# Multiple spaces and hyphens
slugify("foo   bar")  # Returns: "foo-bar"
slugify("hello---world")  # Returns: "hello-world"
```

### Error Handling

```python
# Lists raise TypeError
slugify(["hello", "world"])  # Raises: TypeError

# Dicts raise TypeError
slugify({"key": "value"})  # Raises: TypeError
```

## Implementation Notes

The function follows amplihack's philosophy of:

- **Ruthless simplicity**: Uses only standard library (unicodedata, re)
- **Zero-BS implementation**: No stubs or placeholders, fully functional
- **Self-contained**: All logic in a single function
- **Regeneratable**: Can be rebuilt from this specification

## Public API Access

The slugify function is exported through the main utils module:

```python
# Import from public API
from amplihack.utils import slugify

# Also available from the specific module
from amplihack.utils.string_utils import slugify
```

## Testing

The function is thoroughly tested with:

- 44 unit tests covering all edge cases
- 7 public API tests verifying proper export
- Tests for idempotency (applying slugify twice gives same result)
- Comprehensive Unicode normalization tests
- Type conversion validation

## Philosophy Alignment

This implementation embodies:

- **Wabi-sabi philosophy**: Simple, essential functionality without embellishment
- **Present-moment focus**: Handles current needs without over-engineering
- **Trust in emergence**: Type handling added only when needed
- **Pragmatic trust**: Gracefully handles None and common types
