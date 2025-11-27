# Slugify Function Reference

In-depth technical reference for the `slugify` function, including implementation details, Unicode handling, and performance characteristics.

## Function Signature

```python
def slugify(text: str, max_length: int = 50, separator: str = "-") -> str
```

## Overview

The `slugify` function transforms arbitrary text into URL-safe slugs suitable for web addresses, filenames, and identifiers. It handles Unicode normalization, special character removal, and customizable word separation.

## Parameters

### `text` (required)

- **Type**: `str`
- **Description**: Input string to convert into a slug
- **Constraints**: Any valid Python string, including Unicode
- **Empty String**: Returns empty string

### `max_length` (optional)

- **Type**: `int`
- **Default**: `50`
- **Description**: Maximum character length of resulting slug
- **Behavior**: Truncates at word boundaries when possible to avoid partial words
- **Minimum**: Should be at least 1
- **Note**: Length is measured after transformation, not from original text

### `separator` (optional)

- **Type**: `str`
- **Default**: `"-"` (hyphen)
- **Description**: Character used to replace spaces and separate words
- **Common Values**:
  - `"-"`: URL slugs (recommended for SEO)
  - `"_"`: Python identifiers, filenames
  - `""`: Concatenated identifiers
- **Constraints**: Should be URL-safe character; typically hyphen or underscore

## Processing Steps

The function performs these transformations in order:

### 1. Unicode Normalization (NFKD)

Decomposes characters into base + combining characters:

```python
# Input: "café"
# After NFKD: "cafe\u0301" (c + a + f + e + combining acute accent)
# Result: "cafe" (after removing non-ASCII)
```

### 2. ASCII Conversion

Removes all non-ASCII characters:

```python
# Examples of conversions:
"naïve" → "naive"
"Zürich" → "Zurich"
"北京" → "" (Chinese characters removed)
"café" → "cafe"
"piñata" → "pinata"
```

### 3. Character Replacement

Replaces non-alphanumeric characters with separator:

```python
# Before: "hello world! (2024)"
# After: "hello-world--2024-"
```

### 4. Lowercase Conversion

Converts all characters to lowercase:

```python
# Before: "Hello-World--2024-"
# After: "hello-world--2024-"
```

### 5. Separator Cleanup

Removes duplicate and trailing separators:

```python
# Before: "hello-world--2024-"
# After: "hello-world-2024"
```

### 6. Length Truncation

If `max_length` specified, truncates intelligently:

```python
# Input: slugify("Very Long Title Here", max_length=15)
# Process: Finds last separator before position 15
# Output: "very-long-title" (respects word boundary)
```

## Detailed Examples

### Basic Transformations

```python
from amplihack.utils.string_utils import slugify

# Whitespace handling
slugify("  Multiple   Spaces  ")  # "multiple-spaces"
slugify("Tabs\tAnd\nNewlines")   # "tabs-and-newlines"

# Number preservation
slugify("Version 2.0.1")         # "version-2-0-1"
slugify("Year 2024")             # "year-2024"

# Special character removal
slugify("Hello@World.com")       # "hello-world-com"
slugify("50% off!")              # "50-off"
slugify("#hashtag")              # "hashtag"
```

### Unicode Handling

```python
# European languages
slugify("Møller")                 # "moller"
slugify("François")               # "francois"
slugify("Jürgen")                 # "jurgen"

# Accented characters
slugify("résumé")                 # "resume"
slugify("naïveté")                # "naivete"

# Mixed scripts (non-Latin removed)
slugify("Hello 世界")              # "hello"
slugify("Привет World")           # "world"
```

### Length Management

```python
# Exact truncation
slugify("abcdefghij", max_length=5)  # "abcde"

# Word boundary respect
slugify("One Two Three Four", max_length=10)  # "one-two"
slugify("One Two Three Four", max_length=11)  # "one-two"
slugify("One Two Three Four", max_length=12)  # "one-two"
slugify("One Two Three Four", max_length=13)  # "one-two-three"

# Long word handling
slugify("Supercalifragilistic", max_length=10)  # "supercalif"
```

### Custom Separators

```python
# Underscore for Python identifiers
slugify("User Profile Data", separator="_")  # "user_profile_data"

# No separator (concatenation)
slugify("Get User Name", separator="")       # "getusername"

# Double hyphen (unusual but valid)
slugify("Part One", separator="--")          # "part--one"
```

## Edge Cases

### Empty and Invalid Input

```python
slugify("")                       # ""
slugify("   ")                    # ""
slugify("!!!")                    # ""
slugify("@#$%^&*()")              # ""
```

### Already Slugified

```python
slugify("already-slugified")      # "already-slugified"
slugify("under_scored")           # "under-scored"
```

### Separator Conflicts

```python
# When text contains the separator character
slugify("dash-separated", separator="-")     # "dash-separated"
slugify("under_scored", separator="_")       # "under_scored"
```

### Maximum Length Edge Cases

```python
# Length shorter than first word
slugify("Extraordinary", max_length=5)       # "extra"

# Length of zero or negative (treated as no limit)
slugify("Hello World", max_length=0)         # "hello-world"
slugify("Hello World", max_length=-1)        # "hello-world"
```

## Performance Characteristics

### Time Complexity

- **Overall**: O(n) where n is the length of input text
- **Unicode normalization**: O(n)
- **Character replacement**: O(n)
- **Separator cleanup**: O(n)
- **Truncation**: O(1) or O(m) where m is max_length

### Space Complexity

- **Overall**: O(n) for the output string
- **Temporary buffers**: O(n) during processing
- **No external dependencies**: Memory-efficient implementation

### Performance Tips

```python
# Cache slugs for repeated text
slug_cache = {}
def cached_slugify(text):
    if text not in slug_cache:
        slug_cache[text] = slugify(text)
    return slug_cache[text]

# Pre-compile regex patterns (done internally)
# The function maintains compiled patterns for efficiency

# Batch processing
slugs = [slugify(title) for title in titles]  # Efficient list comprehension
```

## Implementation Notes

### Unicode Normalization Details

The function uses NFKD (Compatibility Decomposition) normalization:

- **NFD**: Canonical decomposition (é → e + ´)
- **NFKD**: Compatibility decomposition (℡ → TEL)
- **Why NFKD**: Maximum compatibility, converts stylistic variants

### Regular Expression Patterns

Internal patterns used for processing:

```python
# Remove non-alphanumeric (keeping spaces)
pattern1 = re.compile(r'[^a-z0-9\s-]')

# Replace spaces with separator
pattern2 = re.compile(r'[-\s]+')

# Clean up separators
pattern3 = re.compile(r'^-+|-+$')
```

### Thread Safety

The function is thread-safe:

- No shared state modification
- All operations on local variables
- Compiled regex patterns are immutable

## Comparison with Other Approaches

### vs. `urllib.parse.quote()`

```python
from urllib.parse import quote

# URL encoding (percent-encoding)
quote("Hello World!")  # "Hello%20World%21"

# Slugify (human-readable)
slugify("Hello World!")  # "hello-world"
```

### vs. Simple Replace

```python
# Naive approach
text.lower().replace(" ", "-")  # Doesn't handle special chars

# Slugify
slugify(text)  # Handles Unicode, special chars, duplicates
```

### vs. Django's slugify

```python
# Django slugify (if django installed)
from django.utils.text import slugify as django_slugify

# Similar behavior but:
# - amplihack includes max_length parameter
# - amplihack has customizable separator
# - amplihack is standalone (no Django dependency)
```

## Integration Examples

### Flask Route Generation

```python
from flask import Flask
from amplihack.utils.string_utils import slugify

app = Flask(__name__)

@app.route('/blog/<slug>')
def blog_post(slug):
    # Reverse lookup from slug to title
    return render_template('post.html', slug=slug)

def create_blog_route(title):
    slug = slugify(title, max_length=60)
    return f"/blog/{slug}"
```

### SQLAlchemy Model

```python
from sqlalchemy import Column, String
from amplihack.utils.string_utils import slugify

class Article(Base):
    __tablename__ = 'articles'

    title = Column(String(200))
    slug = Column(String(60), unique=True, index=True)

    def generate_slug(self):
        self.slug = slugify(self.title, max_length=60)
```

### Filename Generation

```python
from pathlib import Path
from amplihack.utils.string_utils import slugify

def save_upload(file_obj, original_name):
    # Generate safe filename
    name_part = Path(original_name).stem
    extension = Path(original_name).suffix

    safe_name = slugify(name_part, separator="_")
    final_name = f"{safe_name}{extension}"

    # Save file
    save_path = Path("uploads") / final_name
    save_path.write_bytes(file_obj.read())
    return final_name
```

## Testing Considerations

### Unit Test Coverage

```python
import pytest
from amplihack.utils.string_utils import slugify

class TestSlugify:
    def test_basic_transformation(self):
        assert slugify("Hello World") == "hello-world"

    def test_unicode_normalization(self):
        assert slugify("café") == "cafe"

    def test_max_length(self):
        result = slugify("Long Title Here", max_length=10)
        assert len(result) <= 10
        assert result == "long-title"

    def test_custom_separator(self):
        assert slugify("Hello World", separator="_") == "hello_world"

    def test_empty_input(self):
        assert slugify("") == ""
        assert slugify("   ") == ""

    @pytest.mark.parametrize("input,expected", [
        ("Already-Slugified", "already-slugified"),
        ("Multiple   Spaces", "multiple-spaces"),
        ("Special!@#Characters", "special-characters"),
    ])
    def test_various_inputs(self, input, expected):
        assert slugify(input) == expected
```

### Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_slugify_properties(text):
    slug = slugify(text)

    # Properties that should always hold
    assert slug == slug.lower()  # Always lowercase
    assert "--" not in slug  # No double separators
    assert not slug.startswith("-")  # No leading separator
    assert not slug.endswith("-")  # No trailing separator
    assert all(c.isalnum() or c == "-" for c in slug)  # Only valid chars
```

## See Also

- [String Utilities Module](./string-utils.md) - Parent module documentation
- [URL Generation How-To](../howto/url-generation.md) - Practical usage guide
- [Safe Filename Generation](../howto/safe-filenames.md) - File system applications

## Version History

### v1.3.0 (2024-11-27)

- Added intelligent truncation at word boundaries
- Improved Unicode handling for more languages
- Performance optimizations for large text

### v1.2.0 (2024-06-15)

- Added custom separator parameter
- Enhanced regex pattern compilation

### v1.1.0 (2024-03-01)

- Implemented NFKD Unicode normalization
- Better handling of accented characters

### v1.0.0 (2024-01-15)

- Initial implementation
- Basic slugification functionality

---

**Implementation Location**: `src/amplihack/utils/string_utils.py`
