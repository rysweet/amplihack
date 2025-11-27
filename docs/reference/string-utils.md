# String Utilities API Reference

Complete API reference for string manipulation utilities in amplihack.

## Module: `amplihack.utils.string_utils`

String manipulation utilities for text processing, URL generation, and content formatting.

## Functions

### `slugify`

```python
slugify(text: str, max_length: int = 50, separator: str = "-") -> str
```

Convert any string into a URL-friendly slug.

#### Parameters

- **text** (`str`): The input string to convert into a slug
- **max_length** (`int`, optional): Maximum length of the resulting slug. Truncates at word boundaries when possible. Default: `50`
- **separator** (`str`, optional): Character to use between words. Default: `"-"`

#### Returns

`str`: URL-safe slug containing only lowercase letters, numbers, and the separator character

#### Behavior

1. Normalizes Unicode characters (é → e, ñ → n) using NFKD decomposition
2. Converts to lowercase
3. Replaces spaces and underscores with the specified separator
4. Removes all special characters (keeping only alphanumeric and separator)
5. Collapses multiple consecutive separators into a single separator
6. Strips leading/trailing separators
7. Truncates to max_length if needed, preserving word boundaries

#### Examples

```python
from amplihack.utils.string_utils import slugify

# Basic usage
result = slugify("Hello World!")
print(result)
# Output: hello-world

# Unicode normalization
result = slugify("Café Résumé")
print(result)
# Output: cafe-resume

# Custom separator
result = slugify("User Profile Page", separator="_")
print(result)
# Output: user_profile_page

# Length limitation
result = slugify("Very Long Title That Needs Truncation", max_length=20)
print(result)
# Output: very-long-title-that

# Special characters
result = slugify("Price: $99.99 (on sale!)")
print(result)
# Output: price-99-99-on-sale

# Mixed case and numbers
result = slugify("iPhone 15 Pro Max")
print(result)
# Output: iphone-15-pro-max
```

#### Edge Cases

```python
# Empty string
slugify("")  # Returns: ""

# Only special characters
slugify("@#$%")  # Returns: ""

# Already slugified
slugify("already-slugified")  # Returns: "already-slugified"

# Multiple spaces
slugify("Too    many     spaces")  # Returns: "too-many-spaces"

# Leading/trailing special chars
slugify("...Important Message!!!")  # Returns: "important-message"
```

#### Common Use Cases

- **URL Generation**: Create SEO-friendly URLs from page titles
- **File Naming**: Generate safe filenames from user input
- **CSS Classes**: Convert labels to valid CSS class names
- **Database Keys**: Create readable identifiers from natural text
- **API Endpoints**: Transform resource names into URL paths

#### Performance Notes

- O(n) time complexity where n is the length of input text
- Minimal memory allocation through efficient string operations
- Unicode normalization adds slight overhead for non-ASCII text

#### See Also

- [How to Generate URL-Safe Slugs](../howto/url-generation.md) - Practical guide with real examples
- [Slugify Function Details](./slugify.md) - Extended technical reference
- [Safe Filename Generation](../howto/safe-filenames.md) - File system considerations

## Related Modules

- `amplihack.utils.text_processing` - Advanced text manipulation
- `amplihack.utils.validation` - Input validation utilities
- `amplihack.utils.encoding` - Character encoding helpers

## Version History

- **1.0.0** (2024-01): Initial implementation
- **1.1.0** (2024-03): Added Unicode normalization
- **1.2.0** (2024-06): Custom separator support
- **1.3.0** (2024-11): Max length parameter with word boundary awareness

---

**Need help?** See the [URL Generation How-To Guide](../howto/url-generation.md) for practical examples.
