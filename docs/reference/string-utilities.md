# String Utilities Reference

## slugify

Convert text to URL-safe slug format.

### Signature

```python
def slugify(text: str) -> str
```

### Description

Transforms any string into a URL-safe slug by:

1. Normalizing Unicode (NFD) and converting to ASCII
2. Converting to lowercase
3. Replacing whitespace and special chars with hyphens
4. Consolidating consecutive hyphens
5. Stripping leading/trailing hyphens

### Parameters

| Parameter | Type  | Description                                                        |
| --------- | ----- | ------------------------------------------------------------------ |
| `text`    | `str` | Input string with any Unicode characters, special chars, or spaces |

### Returns

| Type  | Description                                                                                                           |
| ----- | --------------------------------------------------------------------------------------------------------------------- |
| `str` | URL-safe slug with lowercase alphanumeric characters and hyphens. Empty string if input contains no valid characters. |

### Examples

```python
from amplihack.utils.string_utils import slugify

# Basic usage
slugify("Hello World")  # Returns: "hello-world"

# Unicode handling
slugify("Café")  # Returns: "cafe"
slugify("Crème brûlée")  # Returns: "creme-brulee"

# Special characters
slugify("Rock & Roll")  # Returns: "rock-roll"
slugify("Hello@World!")  # Returns: "hello-world"

# Edge cases
slugify("")  # Returns: ""
slugify("  test  ")  # Returns: "test"
slugify("---")  # Returns: ""
```

### Use Cases

- **URL paths**: Convert blog titles to URL slugs
- **File naming**: Create safe filenames from user input
- **Database identifiers**: Generate human-readable IDs
- **SEO-friendly URLs**: Create search-engine-friendly paths

### Implementation Notes

- Uses only Python standard library (`re`, `unicodedata`)
- NFD normalization decomposes accented characters before ASCII conversion
- Function is idempotent: `slugify(slugify(x)) == slugify(x)`
- No external dependencies required

### Related

- Location: `src/amplihack/utils/string_utils.py`
- Tests: `tests/unit/test_string_utils.py`
