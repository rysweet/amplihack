# How-To: Generate URL Slugs

Learn how to create URL-friendly slugs from arbitrary text using the slugify utility.

## Problem

You need to convert user-provided text (titles, names, descriptions) into clean, URL-safe slugs for web addresses, filenames, or identifiers.

## Solution

Use the `slugify()` function from `amplihack.utils.string_utils`.

## Prerequisites

```bash
pip install amplihack
```

Or if using uvx:

```bash
uvx amplihack
```

## Basic Usage

### Simple String to Slug

```python
from amplihack.utils.string_utils import slugify

# Convert article title to URL slug
title = "My First Blog Post"
slug = slugify(title)

print(f"URL: /posts/{slug}")
# Output: URL: /posts/my-first-blog-post
```

### Handling Special Characters

```python
from amplihack.utils.string_utils import slugify

# User input with special characters
user_title = "Hello, World! 🌍 #awesome"
safe_slug = slugify(user_title)

print(safe_slug)
# Output: hello-world-awesome
```

### Unicode and International Text

```python
from amplihack.utils.string_utils import slugify

# French text with accents
french_title = "Café au Lait: Guide Complet"
slug = slugify(french_title)

print(slug)
# Output: cafe-au-lait-guide-complet
```

## Common Scenarios

### Blog Post URLs

```python
from amplihack.utils.string_utils import slugify
from datetime import date

def create_blog_url(title: str) -> str:
    """Generate blog post URL from title."""
    slug = slugify(title)
    today = date.today().strftime("%Y/%m/%d")
    return f"/blog/{today}/{slug}"

url = create_blog_url("10 Python Tips for Beginners")
print(url)
# Output: /blog/2025/11/30/10-python-tips-for-beginners
```

### Safe Filenames

```python
from amplihack.utils.string_utils import slugify
from pathlib import Path

def save_user_file(user_filename: str, content: bytes) -> Path:
    """Save file with sanitized filename."""
    # Remove extension if present
    name_without_ext = user_filename.rsplit(".", 1)[0]
    safe_name = slugify(name_without_ext)

    # Add extension back
    extension = user_filename.rsplit(".", 1)[1] if "." in user_filename else "txt"
    filepath = Path(f"uploads/{safe_name}.{extension}")

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(content)
    return filepath

# User uploads "My Project (Final) v2.docx"
saved_path = save_user_file("My Project (Final) v2.docx", b"content")
print(saved_path)
# Output: uploads/my-project-final-v2.docx
```

### Database Keys

```python
from amplihack.utils.string_utils import slugify
import uuid

def create_unique_id(name: str) -> str:
    """Create unique identifier from name."""
    base_slug = slugify(name)
    unique_suffix = str(uuid.uuid4())[:8]
    return f"{base_slug}-{unique_suffix}"

user_id = create_unique_id("John Smith")
print(user_id)
# Output: john-smith-a1b2c3d4
```

### Tag Normalization

```python
from amplihack.utils.string_utils import slugify

def normalize_tags(raw_tags: list[str]) -> list[str]:
    """Normalize user-entered tags."""
    normalized = []
    seen = set()

    for tag in raw_tags:
        slug = slugify(tag)
        if slug and slug not in seen:
            normalized.append(slug)
            seen.add(slug)

    return normalized

user_tags = ["Python", "python", "PYTHON!", "Machine Learning", "ML"]
clean_tags = normalize_tags(user_tags)
print(clean_tags)
# Output: ['python', 'machine-learning', 'ml']
```

### Length-Limited Slugs

```python
from amplihack.utils.string_utils import slugify

def create_short_slug(text: str, max_length: int = 50) -> str:
    """Create slug with length limit for database constraints."""
    return slugify(text, max_length=max_length)

# Very long title
long_title = "This is an extremely long article title that needs to be truncated for database storage and URL cleanliness"
short_slug = create_short_slug(long_title, max_length=40)

print(f"Length: {len(short_slug)}")
print(f"Slug: {short_slug}")
# Output:
# Length: 39
# Slug: this-is-an-extremely-long-article-tit
```

## Validation Pattern

```python
from amplihack.utils.string_utils import slugify

def validate_and_slugify(user_input: str) -> tuple[bool, str, str]:
    """
    Validate user input and return slug with feedback.

    Returns:
        (is_valid, slug, message)
    """
    if not user_input or not user_input.strip():
        return False, "", "Input cannot be empty"

    slug = slugify(user_input)

    if not slug:
        return False, "", "Input must contain at least one letter or number"

    if len(slug) < 3:
        return False, slug, "Slug must be at least 3 characters long"

    return True, slug, "Valid slug generated"

# Test cases
test_inputs = [
    "Hello World",           # Valid
    "   ",                   # Invalid: empty
    "!!!",                   # Invalid: no alphanumeric
    "Hi",                    # Invalid: too short
]

for test in test_inputs:
    valid, slug, message = validate_and_slugify(test)
    print(f"Input: '{test}' → Valid: {valid}, Slug: '{slug}', Message: {message}")

# Output:
# Input: 'Hello World' → Valid: True, Slug: 'hello-world', Message: Valid slug generated
# Input: '   ' → Valid: False, Slug: '', Message: Input cannot be empty
# Input: '!!!' → Valid: False, Slug: '', Message: Input must contain at least one letter or number
# Input: 'Hi' → Valid: False, Slug: 'hi', Message: Slug must be at least 3 characters long
```

## Troubleshooting

### Empty Output

**Problem**: `slugify()` returns empty string

**Causes**:

- Input contains only special characters
- Input is only whitespace

**Solution**:

```python
from amplihack.utils.string_utils import slugify

def safe_slugify(text: str, fallback: str = "untitled") -> str:
    """Slugify with fallback for empty results."""
    slug = slugify(text)
    return slug if slug else fallback

result = safe_slugify("!@#$%")
print(result)
# Output: untitled
```

### Unexpected Hyphen Placement

**Problem**: Multiple hyphens or leading/trailing hyphens

**Cause**: This is expected behavior - slugify normalizes all hyphens

**Solution**: This is correct behavior. The function ensures clean output:

```python
from amplihack.utils.string_utils import slugify

# All produce the same output
inputs = ["hello--world", "hello---world", "-hello-world-"]
for inp in inputs:
    print(slugify(inp))

# Output (all same):
# hello-world
# hello-world
# hello-world
```

### Unicode Character Loss

**Problem**: Some Unicode characters disappear

**Cause**: Characters are transliterated to ASCII equivalents

**Solution**: This is expected. Non-ASCII characters are converted:

```python
from amplihack.utils.string_utils import slugify

# Accented characters are transliterated
print(slugify("naïve café"))
# Output: naive-cafe

# Emoji and symbols are removed
print(slugify("Hello 🌍 World ™"))
# Output: hello-world
```

## Best Practices

1. **Always validate output**: Check that slug is not empty before using
2. **Store original text**: Keep the original text alongside the slug
3. **Handle uniqueness**: Add suffixes or timestamps for duplicate slugs
4. **Consider length limits**: Database columns often have character limits
5. **Test with real data**: Try international characters and special cases

## See Also

- [String Utilities Reference](../reference/string-utilities.md) - Complete API documentation
- [Tutorial: String Sanitization](../tutorials/string-sanitization.md) - Learn text cleaning techniques

---

**Last Updated**: 2025-11-30
