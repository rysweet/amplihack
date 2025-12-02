# Slugify Utility

Convert text to URL-friendly slugs.

## Usage

```python
from src.utils.slugify import slugify

slugify("Hello World!")     # "hello-world"
slugify("Café Résumé")      # "cafe-resume"
slugify("  Spaces  ")       # "spaces"
```

## Behavior

| Transformation       | Example                       |
| -------------------- | ----------------------------- |
| Lowercase            | `HELLO` → `hello`             |
| Spaces to hyphens    | `hello world` → `hello-world` |
| Remove accents       | `café` → `cafe`               |
| Remove special chars | `hello!` → `hello`            |
| Collapse hyphens     | `a--b` → `a-b`                |
| Strip edge hyphens   | `-hello-` → `hello`           |

## Edge Cases

- Empty string returns empty string
- Numbers are preserved: `"item1"` → `"item1"`
- Function is idempotent: `slugify(slugify(x)) == slugify(x)`
