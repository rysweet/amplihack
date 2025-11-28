# slugify Function Reference

The `slugify` function converts arbitrary text into URL-friendly slugs.

## Function Signature

```python
def slugify(
    text: str,
    separator: str = "-",
    max_length: Optional[int] = None
) -> str
```

## Parameters

| Parameter    | Type            | Default  | Description                          |
| ------------ | --------------- | -------- | ------------------------------------ |
| `text`       | `str`           | required | The text to convert into a slug      |
| `separator`  | `str`           | `"-"`    | Character to use between words       |
| `max_length` | `Optional[int]` | `None`   | Maximum length of the resulting slug |

## Return Value

Returns a `str` containing the URL-friendly slug. If the input is empty or contains only non-alphanumeric characters, returns `"untitled"`.

## Behavior

The slugify function:

1. Normalizes Unicode characters using NFD decomposition
2. Converts text to lowercase
3. Replaces spaces and non-alphanumeric characters with the separator
4. Removes consecutive separators
5. Strips separators from the beginning and end
6. Truncates to max_length if specified
7. Returns "untitled" for empty results

## Examples

### Basic Usage

```python
from amplihack.utils.string_utils import slugify

# Simple text conversion
result = slugify("Hello World!")
print(result)
# Output: hello-world

# Mixed case and punctuation
result = slugify("The Quick Brown Fox!!!")
print(result)
# Output: the-quick-brown-fox
```

### Unicode Handling

```python
# Unicode normalization
result = slugify("Café résumé")
print(result)
# Output: cafe-resume

# Non-Latin scripts
result = slugify("你好世界")
print(result)
# Output: untitled  # Non-Latin characters removed

# Mixed scripts
result = slugify("Hello 世界 2024")
print(result)
# Output: hello-2024
```

### Custom Separators

```python
# Underscore separator
result = slugify("Machine Learning Model", separator="_")
print(result)
# Output: machine_learning_model

# Dot separator for versions
result = slugify("Version 1 2 3", separator=".")
print(result)
# Output: version.1.2.3
```

### Length Limiting

```python
# Truncate long titles
result = slugify(
    "A Very Long Article Title That Needs Truncation",
    max_length=20
)
print(result)
# Output: a-very-long-article

# Edge case: max_length shorter than word
result = slugify("Supercalifragilistic", max_length=5)
print(result)
# Output: super
```

### Edge Cases

```python
# Empty string
result = slugify("")
print(result)
# Output: untitled

# Only special characters
result = slugify("!@#$%^&*()")
print(result)
# Output: untitled

# Only whitespace
result = slugify("   \t\n   ")
print(result)
# Output: untitled

# Numbers only
result = slugify("12345")
print(result)
# Output: 12345
```

## Common Use Cases

- **URL generation**: Creating clean URLs from article titles
- **Filename sanitization**: Converting user input to safe filenames
- **Database keys**: Generating readable identifiers
- **CSS class names**: Creating valid class names from content
- **API endpoints**: Converting resource names to URL segments

## Performance Considerations

- Unicode normalization adds overhead for non-ASCII text
- Separator replacement is optimized for single-pass processing
- Max length truncation happens after processing (not before)

## See Also

- [How to Generate Safe URLs](../howto/url-generation.md) - Task-oriented guide
- [String Utilities Module](./string-utils.md) - Other string functions
