# slugify()

Convert any string into a URL-friendly slug.

## Quick Reference

```python
from amplihack.utils.string_utils import slugify

# Basic usage
slug = slugify("Hello World!")
# Returns: "hello-world"

# With max length
slug = slugify("Very long title here", max_length=10)
# Returns: "very-long"

# Unicode handling
slug = slugify("Café résumé")
# Returns: "cafe-resume"
```

## Function Signature

```python
def slugify(
    text: str,
    max_length: Optional[int] = None
) -> str
```

## Parameters

| Parameter    | Type            | Default  | Description                                                                                                         |
| ------------ | --------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `text`       | `str`           | Required | Input string to convert to slug. Raises `TypeError` for non-string types.                                           |
| `max_length` | `Optional[int]` | `None`   | Maximum length of the resulting slug. Truncates at word boundaries when possible. Must be non-negative if provided. |

## Return Value

Returns a `str` containing the slugified text. The returned string:

- Contains only lowercase alphanumeric characters and hyphens
- Has no leading or trailing hyphens
- Has no consecutive hyphens
- Is empty if the input produces no valid characters

## Edge Case Handling

### Empty Inputs

```python
from amplihack.utils.string_utils import slugify

slugify("")             # Returns: ""
slugify("   ")          # Returns: ""
```

### Special Characters

```python
from amplihack.utils.string_utils import slugify

slugify("Hello@World#2024!")      # Returns: "hello-world-2024"
slugify("Price: $99.99")          # Returns: "price-99-99"
slugify("C++ Programming")        # Returns: "c-programming"
```

### Unicode Handling

```python
from amplihack.utils.string_utils import slugify

# Accented characters are normalized
slugify("Björk")                  # Returns: "bjork"
slugify("Café")                   # Returns: "cafe"
slugify("naïve")                  # Returns: "naive"

# Non-ASCII characters are removed
slugify("北京")                    # Returns: ""
slugify("Москва")                 # Returns: ""
slugify("Hello 世界")              # Returns: "hello"
```

### Whitespace and Separators

```python
from amplihack.utils.string_utils import slugify

slugify("  Multiple   Spaces  ")  # Returns: "multiple-spaces"
slugify("Already-slugified")      # Returns: "already-slugified"
slugify("Mix__of---separators")   # Returns: "mix-of-separators"
```

### Maximum Length Handling

```python
from amplihack.utils.string_utils import slugify

# Truncates at word boundaries
slugify("The quick brown fox", max_length=10)     # Returns: "the-quick"
slugify("Verylongwordhere", max_length=10)        # Returns: "verylongwo"

# Handles edge cases
slugify("A", max_length=10)                       # Returns: "a"
slugify("Word", max_length=2)                     # Returns: "wo"
```

### Numeric Handling

```python
from amplihack.utils.string_utils import slugify

slugify("2024 Report")             # Returns: "2024-report"
slugify("Version 3.14.159")        # Returns: "version-3-14-159"
slugify("123456")                  # Returns: "123456"
slugify("№1 Product")              # Returns: "1-product"
```

### Mixed Scripts

```python
from amplihack.utils.string_utils import slugify

# Non-ASCII characters are removed
slugify("Hello世界2024")           # Returns: "hello-2024"
slugify("Café-バー")               # Returns: "cafe"
```

## Performance Characteristics

### Time Complexity

- **Basic operation**: O(n) where n is the length of the input string
- **With Unicode normalization**: O(n) with slightly higher constant factor

### Memory Usage

- **Space complexity**: O(n) for the output string
- **Unicode handling**: Additional temporary buffer for normalization

### Performance Tips

```python
# For bulk operations, reuse the slugify function
from amplihack.utils.string_utils import slugify

# Good - function overhead amortized
slugs = [slugify(title) for title in titles]

# The function uses pre-compiled regex patterns for optimal performance
# Processing 10,000+ strings per second is typical
```

## Common Use Cases

### URL Generation

```python
from amplihack.utils.string_utils import slugify

def create_blog_url(title: str, post_id: int) -> str:
    slug = slugify(title, max_length=60)
    return f"/blog/{post_id}/{slug}"

url = create_blog_url("10 Python Tips & Tricks!", 42)
# Returns: "/blog/42/10-python-tips-tricks"
```

### Filename Sanitization

```python
from amplihack.utils.string_utils import slugify

def safe_filename(name: str) -> str:
    base = slugify(name, max_length=200)
    # Replace hyphens with underscores for filename convention
    base = base.replace("-", "_")
    return f"{base}.txt" if base else "unnamed.txt"

filename = safe_filename("Report: Q3 2024 (Final)")
# Returns: "report_q3_2024_final.txt"
```

### Database Keys

```python
from amplihack.utils.string_utils import slugify

def generate_key(category: str, name: str) -> str:
    cat_slug = slugify(category, max_length=20)
    name_slug = slugify(name, max_length=30)
    return f"{cat_slug}:{name_slug}"

key = generate_key("User Settings", "Email Preferences")
# Returns: "user-settings:email-preferences"
```

### Internationalization

```python
from amplihack.utils.string_utils import slugify

# The function normalizes accented Latin characters automatically
french_slug = slugify("Café français")
# Returns: "cafe-francais"

german_slug = slugify("Über München")
# Returns: "uber-munchen"

# Note: Non-Latin scripts (Chinese, Arabic, etc.) are removed
# as they cannot be normalized to ASCII
chinese_text = slugify("北京欢迎你")
# Returns: "" (no ASCII-convertible characters)
```

## Error Handling

### Type Handling

The function expects string input and will raise `TypeError` for non-string types:

```python
from amplihack.utils.string_utils import slugify

# Valid: strings
slugify("test")                    # Returns: "test"
slugify("")                        # Returns: ""

# Invalid: Non-string types raise TypeError
slugify(None)                      # Raises: TypeError
slugify(12345)                     # Raises: TypeError
slugify({"dict": "value"})         # Raises: TypeError
slugify([1, 2, 3])                 # Raises: TypeError
```

### Parameter Validation

```python
from amplihack.utils.string_utils import slugify

# Negative max_length raises ValueError
slugify("test", max_length=-5)     # Raises: ValueError

# Zero max_length returns empty string
slugify("test", max_length=0)      # Returns: ""
```

## Thread Safety

The `slugify` function is thread-safe and can be used in concurrent contexts without synchronization. Thread safety is achieved through:

1. **No shared state**: The function does not modify any global or module-level state
2. **Immutable operations**: All string operations create new strings rather than modifying existing ones
3. **Pre-compiled patterns**: Regular expression patterns are compiled once at module load time and are read-only during execution
4. **No side effects**: The function is pure - it only depends on its inputs and produces no side effects

```python
import concurrent.futures
from amplihack.utils.string_utils import slugify

titles = ["Title 1", "Title 2", "Title 3"]

with concurrent.futures.ThreadPoolExecutor() as executor:
    slugs = list(executor.map(slugify, titles))
# Safe for parallel execution
```

## See Also

- [String Utilities Overview](./string-utils.md) - Other string manipulation functions
- [URL Generation How-To](../howto/url-generation.md) - Best practices for URL creation
- [Safe Filenames How-To](../howto/safe-filenames.md) - Creating filesystem-safe names

## Changelog

- **v1.0.0** (2024-11) - Initial implementation with Unicode normalization and max_length support
