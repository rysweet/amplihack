# String Utilities Module

Collection of string manipulation utilities for text processing.

## Module Location

```python
from amplihack.utils import string_utils
# Or import specific functions
from amplihack.utils.string_utils import slugify
```

## Available Functions

### slugify

Converts text to URL-friendly slugs.

```python
def slugify(
    text: str,
    separator: str = "-",
    max_length: Optional[int] = None
) -> str
```

**Purpose**: Transform arbitrary text into safe, readable identifiers suitable for URLs, filenames, and keys.

**Example**:

```python
from amplihack.utils.string_utils import slugify

url_slug = slugify("Hello World!", max_length=10)
print(url_slug)
# Output: hello-worl
```

**Full Documentation**: [slugify Function Reference](./slugify.md)

## Module Philosophy

The string utilities module follows these principles:

1. **Zero Dependencies**: Uses only Python standard library
2. **Unicode Aware**: Properly handles international text
3. **Safe Defaults**: Returns safe values for edge cases
4. **Single Responsibility**: Each function does one thing well
5. **Predictable Behavior**: Consistent handling across functions

## Common Patterns

### URL Generation

```python
from amplihack.utils.string_utils import slugify

def create_permalink(title: str, id: int) -> str:
    """Generate permanent link from title."""
    slug = slugify(title, max_length=50)
    return f"/posts/{id}/{slug}"
```

### Filename Sanitization

```python
from amplihack.utils.string_utils import slugify

def safe_filename(name: str) -> str:
    """Create filesystem-safe filename."""
    return slugify(name, separator="_", max_length=200)
```

### Database Keys

```python
from amplihack.utils.string_utils import slugify

def create_key(category: str, name: str) -> str:
    """Generate database key from components."""
    cat_slug = slugify(category, separator="_")
    name_slug = slugify(name, separator="_")
    return f"{cat_slug}:{name_slug}"
```

## Error Handling

All string utility functions follow these conventions:

1. **Never raise exceptions** for invalid input
2. **Return safe defaults** when processing fails
3. **Handle empty input** gracefully
4. **Process Unicode** without errors

Example:

```python
# These all return safe values, never raise
slugify("")           # Returns: "untitled"
slugify(None)         # Returns: "untitled"
slugify("!@#$%")      # Returns: "untitled"
slugify("你好")        # Returns: "untitled"
```

## Performance Considerations

- Functions are optimized for single-pass processing
- Unicode normalization has overhead for non-ASCII text
- Consider caching results for repeated operations
- Max length truncation happens after processing

### Caching Example

```python
from functools import lru_cache
from amplihack.utils.string_utils import slugify

@lru_cache(maxsize=1000)
def cached_slugify(text: str) -> str:
    """Cache frequently slugified text."""
    return slugify(text)
```

## Testing String Utilities

When testing code that uses string utilities:

```python
import pytest
from amplihack.utils.string_utils import slugify

def test_slugify_basic():
    """Test basic slugification."""
    assert slugify("Hello World") == "hello-world"

def test_slugify_unicode():
    """Test Unicode handling."""
    assert slugify("Café") == "cafe"

def test_slugify_empty():
    """Test empty input handling."""
    assert slugify("") == "untitled"
    assert slugify("!!!") == "untitled"

def test_slugify_length():
    """Test length limiting."""
    result = slugify("Very Long Text", max_length=5)
    assert len(result) <= 5
    assert result == "very"
```

## Integration with Other Modules

String utilities integrate with:

- **Web Framework Routing**: URL slug generation
- **File Operations**: Safe filename creation
- **Database Operations**: Key generation
- **API Development**: Endpoint naming
- **Content Management**: Permalink creation

## Module Maintenance

This module is:

- **Stable**: API will not break backward compatibility
- **Self-contained**: No external dependencies
- **Well-tested**: Comprehensive test coverage
- **Regeneratable**: Can be rebuilt from this specification

## See Also

- [slugify Function](./slugify.md) - Detailed slugify documentation
- [URL Generation Guide](../howto/url-generation.md) - Creating web-safe URLs
- [Safe Filename Guide](../howto/safe-filenames.md) - Filesystem-safe names
