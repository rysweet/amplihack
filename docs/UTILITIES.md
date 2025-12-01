# String Utilities Guide

This guide covers the string utility functions provided by amplihack.

## slugify()

Convert text to URL-safe slug format for use in URLs, filenames, and identifiers.

### What is a Slug?

A slug is a URL-safe version of text that:

- Contains only lowercase letters, numbers, and hyphens
- Has no spaces or special characters
- Is human-readable and SEO-friendly
- Can be safely used in URLs without encoding

### When to Use

Use `slugify()` when you need to:

- Create URL-friendly versions of article titles or page names
- Generate safe filenames from user input
- Create unique identifiers from descriptive text
- Build REST API endpoints from resource names
- Generate anchor links in documentation

### Common Use Cases

#### 1. Blog Post URLs

```python
from amplihack.utils import slugify

title = "10 Tips for Better Python Code"
url_slug = slugify(title)
# Result: '10-tips-for-better-python-code'
# Usage: https://blog.example.com/posts/10-tips-for-better-python-code
```

#### 2. Filename Generation

```python
from amplihack.utils import slugify

user_input = "My Report (Final).docx"
safe_filename = slugify(user_input)
# Result: 'my-report-final-docx'
```

#### 3. API Resource Identifiers

```python
from amplihack.utils import slugify

resource_name = "User Profile Settings"
api_path = f"/api/{slugify(resource_name)}"
# Result: '/api/user-profile-settings'
```

#### 4. Anchor Links

```python
from amplihack.utils import slugify

heading = "Getting Started with Installation"
anchor = f"#{slugify(heading)}"
# Result: '#getting-started-with-installation'
```

### Character Handling Rules

#### Letters and Numbers

- **Uppercase** → converted to lowercase
- **Letters with accents** → normalized to ASCII (café → cafe)
- **Numbers** → preserved as-is

#### Separators

All separator characters are converted to hyphens:

- Spaces (" ") → hyphen
- Underscores ("\_") → hyphen
- Slashes ("/", "\\") → hyphen
- Multiple consecutive separators → single hyphen

#### Special Characters

Removed completely:

- Punctuation: `! @ # $ % ^ & * ( ) + = | \ / ? . , ; :`
- Brackets: `[ ] { } < >`
- Quotes: `' "` (except in contractions like "don't")

#### Edge Cases

- **Leading/trailing hyphens** → stripped
- **Multiple consecutive hyphens** → consolidated to one
- **Empty result** → returns empty string
- **Unicode** → normalized to ASCII equivalents

### API Reference

```python
def slugify(text: str) -> str
```

**Parameters:**

- `text` (str): Input string with any Unicode characters, special chars, or spaces

**Returns:**

- `str`: URL-safe slug with lowercase alphanumeric characters and hyphens

**Examples:**

Basic usage:

```python
>>> slugify("Hello World")
'hello-world'
>>> slugify("The Quick Brown Fox")
'the-quick-brown-fox'
```

Unicode and accents:

```python
>>> slugify("Café")
'cafe'
>>> slugify("naïve résumé")
'naive-resume'
```

Special characters:

```python
>>> slugify("Rock & Roll")
'rock-roll'
>>> slugify("user@example.com")
'user-example-com'
```

Multiple separators:

```python
>>> slugify("path/to/file.txt")
'path-to-file-txt'
>>> slugify("one___two___three")
'one-two-three'
```

Edge cases:

```python
>>> slugify("don't stop")
'dont-stop'
>>> slugify("100% Pure!")
'100-pure'
>>> slugify("   spaces   ")
'spaces'
```

### Implementation Details

The slugify function uses a 5-step transformation process:

1. **Unicode Normalization**: NFD normalization + ASCII encoding
   - Decomposes accented characters (é → e + accent)
   - Converts to ASCII, discarding non-representable characters

2. **Lowercase Conversion**: All text converted to lowercase

3. **Quote Removal**: Removes quotes while preserving contractions
   - "don't" → "dont" (contraction preserved)
   - "hello 'world'" → "hello world" (quotes removed)

4. **Separator Replacement**: Converts all separators to hyphens
   - Whitespace: spaces, tabs, newlines
   - Path separators: `/`, `\`
   - Other: `_`, `@`, `&`, etc.

5. **Cleanup**:
   - Remove all non-alphanumeric characters except hyphens
   - Consolidate consecutive hyphens
   - Strip leading/trailing hyphens

### Performance Considerations

- **Time Complexity**: O(n) where n is the length of the input string
- **Memory**: Creates intermediate strings during transformation
- **Unicode**: Handles any Unicode input efficiently using standard library

### Testing

The slugify function has comprehensive test coverage including:

- Basic ASCII text transformation
- Unicode and accent handling
- Special character removal
- Multiple separator consolidation
- Edge cases (empty strings, all-special-chars, etc.)
- Contractions and quotes

Run tests:

```bash
pytest tests/unit/utils/test_string_utils.py -v
```

### Philosophy

This implementation follows amplihack's core principles:

- **Ruthless Simplicity**: Uses only Python standard library (re, unicodedata)
- **Single Responsibility**: Does one thing well - converts text to slugs
- **Zero-BS Implementation**: No stubs, no placeholders, fully functional
- **Self-Contained**: No external dependencies
- **Regeneratable**: Can be rebuilt from specification

### See Also

- [Python unicodedata documentation](https://docs.python.org/3/library/unicodedata.html)
- [Python re module documentation](https://docs.python.org/3/library/re.html)
- [URL Slug Best Practices](https://moz.com/learn/seo/url)
