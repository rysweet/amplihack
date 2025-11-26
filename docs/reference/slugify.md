# slugify

Convert text to URL-safe slug format.

## Import

```python
from amplihack.utils import slugify
```

## Usage

```python
slugify("Hello World")          # 'hello-world'
slugify("Café")                 # 'cafe'
slugify("Rock & Roll")          # 'rock-roll'
slugify("already-a-slug")       # 'already-a-slug' (idempotent)
```

## Behavior

- Converts to lowercase
- Normalizes Unicode (café → cafe)
- Replaces spaces/punctuation with hyphens
- Removes special characters
- Collapses multiple hyphens to single
- Returns empty string if no valid characters remain
- Uses only Python standard library

## Function Signature

```python
def slugify(text: str) -> str:
    """Convert text to URL-safe slug format."""
```

## Use Cases

- URL paths: `/blog/{slugify(title)}`
- File names: `{slugify(title)}.md`
- HTML IDs: `id="section-{slugify(title)}"`