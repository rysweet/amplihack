# How to Use String Utilities

This guide shows you how to use the string utility functions in amplihack.

## Slugify Function

The `slugify()` function converts any string into a URL-safe slug.

### Basic Usage

```python
from amplihack.utils.string_utils import slugify

# Convert text to slug
result = slugify("Hello World")
# Returns: "hello-world"
```

### What It Does

The slugify function transforms your text by:

1. Normalizing unicode characters (accents become plain letters)
2. Converting to lowercase
3. Removing special characters
4. Replacing spaces and underscores with hyphens
5. Collapsing multiple hyphens into one
6. Stripping leading and trailing hyphens

### Common Examples

**Basic text conversion:**

```python
slugify("My Blog Post Title")  # Returns: "my-blog-post-title"
```

**Handling special characters:**

```python
slugify("Hello@World!")  # Returns: "hello-world"
slugify("Rock & Roll")   # Returns: "rock-roll"
```

**Unicode normalization:**

```python
slugify("Café")          # Returns: "cafe"
slugify("Crème brûlée")  # Returns: "creme-brulee"
```

**Numbers are preserved:**

```python
slugify("Project 123 Version 2")  # Returns: "project-123-version-2"
slugify("test123")                # Returns: "test123"
```

**Underscores converted to hyphens:**

```python
slugify("hello_world")  # Returns: "hello-world"
```

### Edge Cases

**Empty strings:**

```python
slugify("")      # Returns: ""
slugify("   ")   # Returns: ""
```

**Only special characters:**

```python
slugify("!!!")  # Returns: ""
slugify("@#$")  # Returns: ""
```

**Already valid slugs:**

```python
slugify("already-a-slug")  # Returns: "already-a-slug"
```

**Emoji and unicode:**

```python
slugify("Hello 😀 World")  # Returns: "hello-world"
```

### Return Value

The function always returns a string:

- Valid slugs contain only lowercase letters, numbers, and single hyphens
- No leading or trailing hyphens
- No consecutive hyphens
- Returns empty string if input contains no valid characters

### Function Signature

```python
def slugify(text: str) -> str:
    """Convert string to URL-safe slug.

    Args:
        text: String to convert

    Returns:
        URL-safe slug string (lowercase, alphanumeric + hyphens)
    """
```

### Idempotency

Slugify is idempotent - running it twice gives the same result:

```python
original = "Hello World!"
first = slugify(original)      # "hello-world"
second = slugify(first)        # "hello-world" (same)
```

This means it's safe to slugify text that might already be a slug.
