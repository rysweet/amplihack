# How to Generate Safe URLs

Generate URL-friendly slugs from user input using the `slugify` utility.

## Quick Start

```python
from amplihack.utils.string_utils import slugify

# Convert article title to URL slug
title = "My First Blog Post!"
url_slug = slugify(title)
print(f"/blog/{url_slug}")
# Output: /blog/my-first-blog-post
```

## Common Scenarios

### Blog Post URLs

Generate clean URLs from article titles:

```python
from amplihack.utils.string_utils import slugify
from datetime import date

def create_blog_url(title: str, publish_date: date) -> str:
    """Create a blog URL with date and title slug."""
    year = publish_date.year
    month = publish_date.month
    slug = slugify(title, max_length=60)
    return f"/blog/{year}/{month:02d}/{slug}"

# Example usage
url = create_blog_url("10 Python Tips & Tricks!", date(2024, 3, 15))
print(url)
# Output: /blog/2024/03/10-python-tips-tricks
```

### Product URLs

Create SEO-friendly product URLs:

```python
def create_product_url(product_name: str, sku: str) -> str:
    """Generate product URL with name and SKU."""
    name_slug = slugify(product_name, max_length=40)
    sku_slug = slugify(sku, separator="_")
    return f"/products/{name_slug}-{sku_slug}"

# Example usage
url = create_product_url("Nike Air Max 90", "NKE-AM90-2024")
print(url)
# Output: /products/nike-air-max-90-nke_am90_2024
```

### User Profile URLs

Create readable profile URLs from usernames:

```python
def create_profile_url(display_name: str, user_id: int) -> str:
    """Generate profile URL from display name."""
    slug = slugify(display_name, max_length=30)
    # Handle empty slugs
    if slug == "untitled":
        slug = f"user-{user_id}"
    return f"/u/{slug}"

# Example usage
url1 = create_profile_url("John Smith", 12345)
print(url1)
# Output: /u/john-smith

url2 = create_profile_url("!@#$", 67890)  # Special chars only
print(url2)
# Output: /u/user-67890
```

### Category Hierarchies

Build hierarchical category paths:

```python
def create_category_path(categories: list[str]) -> str:
    """Create nested category URL path."""
    slugs = [slugify(cat, max_length=20) for cat in categories]
    return "/c/" + "/".join(slugs)

# Example usage
path = create_category_path(["Electronics", "Computers & Tablets", "Laptops"])
print(path)
# Output: /c/electronics/computers-tablets/laptops
```

### API Endpoints

Generate RESTful API paths:

```python
def create_api_endpoint(resource: str, filters: dict) -> str:
    """Build API endpoint with query-safe parameters."""
    resource_slug = slugify(resource, separator="_")

    # Build query parameters
    params = []
    for key, value in filters.items():
        key_slug = slugify(key, separator="_")
        value_slug = slugify(str(value), separator="_")
        params.append(f"{key_slug}={value_slug}")

    query = "&".join(params) if params else ""
    base = f"/api/{resource_slug}"

    return f"{base}?{query}" if query else base

# Example usage
endpoint = create_api_endpoint(
    "User Reports",
    {"Status": "Active", "Type": "Premium"}
)
print(endpoint)
# Output: /api/user_reports?status=active&type=premium
```

## Handling International Content

Work with multilingual content:

```python
def create_intl_slug(text: str, fallback_id: str) -> str:
    """Handle international text with fallback."""
    slug = slugify(text, max_length=50)

    # Use fallback ID if slug is empty
    if slug == "untitled":
        return slugify(f"content-{fallback_id}")

    return slug

# Example usage
# Latin script
url1 = create_intl_slug("Bonjour le monde!", "fr-123")
print(url1)
# Output: bonjour-le-monde

# Non-Latin script (will use fallback)
url2 = create_intl_slug("こんにちは世界", "ja-456")
print(url2)
# Output: content-ja-456

# Mixed scripts
url3 = create_intl_slug("Hello 世界 2024", "mixed-789")
print(url3)
# Output: hello-2024
```

## File Naming

Create safe filenames from user input:

```python
from pathlib import Path

def create_safe_filename(name: str, extension: str = "") -> str:
    """Generate safe filename from user input."""
    # Remove extension if present in name
    if "." in name:
        name, _ = name.rsplit(".", 1)

    # Create slug with underscores
    base = slugify(name, separator="_", max_length=100)

    # Add extension
    if extension:
        extension = extension.lstrip(".")
        return f"{base}.{extension}"

    return base

# Example usage
filename1 = create_safe_filename("My Report (Final).docx", "pdf")
print(filename1)
# Output: my_report_final.pdf

filename2 = create_safe_filename("Screenshot 2024/03/15", "png")
print(filename2)
# Output: screenshot_2024_03_15.png
```

## Best Practices

### Always Validate Empty Slugs

```python
def safe_slug_with_fallback(text: str, prefix: str = "item") -> str:
    """Ensure slug is never empty."""
    slug = slugify(text)
    if slug == "untitled":
        import uuid
        return f"{prefix}-{str(uuid.uuid4())[:8]}"
    return slug
```

### Cache Generated Slugs

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_slugify(text: str) -> str:
    """Cache frequently slugified text."""
    return slugify(text)

# Useful for repeated conversions
for _ in range(1000):
    url = cached_slugify("Frequently Used Title")  # Only computed once
```

### Preserve Uniqueness

```python
def ensure_unique_slug(text: str, existing_slugs: set[str]) -> str:
    """Generate unique slug by appending numbers."""
    base_slug = slugify(text, max_length=50)

    if base_slug not in existing_slugs:
        return base_slug

    # Append numbers until unique
    counter = 2
    while f"{base_slug}-{counter}" in existing_slugs:
        counter += 1

    return f"{base_slug}-{counter}"

# Example usage
existing = {"python-tutorial", "python-tutorial-2"}
slug = ensure_unique_slug("Python Tutorial", existing)
print(slug)
# Output: python-tutorial-3
```

## Common Pitfalls

### Don't Slugify Already-Slugified Text

```python
# WRONG - Double slugification
slug1 = slugify("Hello World")
slug2 = slugify(slug1)  # Unnecessary

# RIGHT - Slugify once
slug = slugify("Hello World")
```

### Handle Unicode Properly

```python
# Account for Unicode normalization
text = "Résumé"  # Contains accented characters
slug = slugify(text)
print(slug)
# Output: resume  # Accents removed
```

### Consider SEO Requirements

```python
def seo_friendly_slug(title: str, keywords: list[str] = None) -> str:
    """Create SEO-optimized slug."""
    # Start with title
    slug = slugify(title, max_length=40)

    # Append important keywords if space allows
    if keywords and len(slug) < 40:
        for keyword in keywords[:2]:  # Max 2 keywords
            keyword_slug = slugify(keyword)
            if len(f"{slug}-{keyword_slug}") <= 60:
                slug = f"{slug}-{keyword_slug}"

    return slug

# Example usage
url = seo_friendly_slug(
    "Best Laptops",
    keywords=["2024", "reviews"]
)
print(url)
# Output: best-laptops-2024-reviews
```

## See Also

- [slugify Function Reference](../reference/slugify.md) - Complete API documentation
- [String Utilities Reference](../reference/string-utils.md) - Other string functions
- [Safe Filename Generation](./safe-filenames.md) - Detailed filename handling
