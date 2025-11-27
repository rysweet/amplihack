# How to Generate URL-Safe Slugs

Convert any text into clean, SEO-friendly URLs using the slugify utility.

## Quick Start

```python
from amplihack.utils.string_utils import slugify

# Convert a blog post title to URL
title = "My First Blog Post!"
url_slug = slugify(title)
print(f"/blog/{url_slug}")
# Output: /blog/my-first-blog-post
```

## Common Tasks

### Generate SEO-Friendly URLs

Transform page titles into readable, search-engine-optimized URLs:

```python
from amplihack.utils.string_utils import slugify

def create_article_url(title, article_id=None):
    """Generate SEO-friendly article URL."""
    slug = slugify(title, max_length=50)

    if article_id:
        return f"/articles/{article_id}/{slug}"
    return f"/articles/{slug}"

# Examples
url = create_article_url("10 Python Tips Every Developer Should Know")
print(url)
# Output: /articles/10-python-tips-every-developer-should-know

url = create_article_url("Python vs JavaScript: A Comparison", article_id=42)
print(url)
# Output: /articles/42/python-vs-javascript-a-comparison
```

### Handle International Content

Process content in multiple languages with proper Unicode handling:

```python
from amplihack.utils.string_utils import slugify

# French content
french_title = "Café et Croissants: Le Petit Déjeuner Français"
slug = slugify(french_title)
print(f"/fr/articles/{slug}")
# Output: /fr/articles/cafe-et-croissants-le-petit-dejeuner-francais

# Spanish content
spanish_title = "Programación en Español: Guía para Principiantes"
slug = slugify(spanish_title)
print(f"/es/tutorials/{slug}")
# Output: /es/tutorials/programacion-en-espanol-guia-para-principiantes

# German content
german_title = "Über uns: Unsere Geschichte"
slug = slugify(german_title)
print(f"/de/about/{slug}")
# Output: /de/about/uber-uns-unsere-geschichte
```

### Create Category URLs

Build hierarchical URL structures for navigation:

```python
from amplihack.utils.string_utils import slugify

def build_category_path(categories):
    """Build nested category URL path."""
    slugs = [slugify(cat) for cat in categories]
    return "/category/" + "/".join(slugs)

# Example category hierarchy
path = build_category_path(["Electronics", "Computers & Tablets", "Laptops"])
print(path)
# Output: /category/electronics/computers-tablets/laptops

# Product URL with categories
def product_url(category_path, product_name):
    product_slug = slugify(product_name, max_length=50)
    return f"{category_path}/{product_slug}"

url = product_url(path, "MacBook Pro 16-inch (2024)")
print(url)
# Output: /category/electronics/computers-tablets/laptops/macbook-pro-16-inch-2024
```

### Generate API Endpoints

Create consistent REST API paths from resource names:

```python
from amplihack.utils.string_utils import slugify

class APIEndpointBuilder:
    """Build consistent API endpoints."""

    def __init__(self, base_url="https://api.example.com"):
        self.base_url = base_url

    def resource_endpoint(self, resource_name, version="v1"):
        """Generate resource endpoint."""
        slug = slugify(resource_name, separator="_")
        return f"{self.base_url}/{version}/{slug}"

    def action_endpoint(self, resource, action):
        """Generate action-specific endpoint."""
        resource_slug = slugify(resource, separator="_")
        action_slug = slugify(action, separator="_")
        return f"{self.base_url}/v1/{resource_slug}/{action_slug}"

# Usage
api = APIEndpointBuilder()

# Resource endpoints
print(api.resource_endpoint("User Profiles"))
# Output: https://api.example.com/v1/user_profiles

print(api.resource_endpoint("Shopping Cart Items"))
# Output: https://api.example.com/v1/shopping_cart_items

# Action endpoints
print(api.action_endpoint("Users", "Reset Password"))
# Output: https://api.example.com/v1/users/reset_password
```

### Handle User-Generated Content

Safely process user input for URLs while preventing issues:

```python
from amplihack.utils.string_utils import slugify
import hashlib
import time

def create_user_content_url(user_input, content_type="post"):
    """Generate URL for user-generated content with safety checks."""

    # Slugify user input
    slug = slugify(user_input, max_length=50)

    # Handle empty or invalid slugs
    if not slug:
        # Generate fallback slug from timestamp
        timestamp = str(int(time.time()))
        slug = f"{content_type}-{timestamp}"

    # Ensure uniqueness with hash suffix if needed
    elif len(slug) < 3:
        # Too short, add hash suffix
        hash_suffix = hashlib.md5(user_input.encode()).hexdigest()[:6]
        slug = f"{slug}-{hash_suffix}"

    return f"/user-content/{content_type}/{slug}"

# Examples
print(create_user_content_url("My Amazing Recipe!!!"))
# Output: /user-content/post/my-amazing-recipe

print(create_user_content_url("🎉🎊🎈"))  # Only emojis
# Output: /user-content/post/post-1701234567

print(create_user_content_url("Hi"))  # Very short
# Output: /user-content/post/hi-a2c3b4
```

### Create Filename-Safe Slugs

Generate safe filenames for uploads and exports:

```python
from amplihack.utils.string_utils import slugify
from datetime import datetime

def safe_filename(original_name, preserve_extension=True):
    """Generate safe filename from user input."""

    if preserve_extension and "." in original_name:
        name, ext = original_name.rsplit(".", 1)
        slug = slugify(name, separator="_")
        return f"{slug}.{ext.lower()}"

    return slugify(original_name, separator="_")

def versioned_filename(base_name):
    """Add timestamp to filename for versioning."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(base_name, separator="_")
    return f"{slug}_{timestamp}"

# Examples
print(safe_filename("Project Report (Final).pdf"))
# Output: project_report_final.pdf

print(safe_filename("Sales Data Q4 2024.xlsx"))
# Output: sales_data_q4_2024.xlsx

print(versioned_filename("Database Backup"))
# Output: database_backup_20241127_143052
```

## Best Practices

### 1. Set Appropriate Length Limits

```python
# Good: Reasonable limits for URLs
slug = slugify(title, max_length=50)  # SEO-friendly length (default)

# Bad: No limit on user input
slug = slugify(user_input)  # Could be extremely long
```

### 2. Choose Consistent Separators

```python
# URLs: Use hyphens (SEO best practice)
url_slug = slugify(text, separator="-")

# Filenames: Use underscores (programming convention)
file_slug = slugify(text, separator="_")

# CSS classes: Use hyphens (CSS convention)
class_slug = slugify(text, separator="-")
```

### 3. Handle Edge Cases

```python
def robust_slugify(text, fallback="untitled"):
    """Slugify with fallback for edge cases."""
    slug = slugify(text)
    return slug if slug else fallback

# Never returns empty string
print(robust_slugify(""))  # Output: untitled
print(robust_slugify("!!!"))  # Output: untitled
```

### 4. Maintain URL Consistency

```python
class URLManager:
    """Ensure consistent URL generation."""

    def __init__(self):
        self.cache = {}

    def get_url(self, title):
        """Get consistent URL for title."""
        if title not in self.cache:
            self.cache[title] = slugify(title, max_length=50)
        return f"/page/{self.cache[title]}"
```

## Troubleshooting

### Problem: Special Characters Not Handled

```python
# Issue: Currency symbols remain
text = "Price: €50"
# Solution: Slugify handles this automatically
print(slugify(text))  # Output: price-50
```

### Problem: Duplicate URLs

```python
def unique_slug(text, existing_slugs):
    """Generate unique slug with counter."""
    base_slug = slugify(text)
    slug = base_slug
    counter = 1

    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug

# Example
existing = ["python-tutorial", "python-tutorial-1"]
new_slug = unique_slug("Python Tutorial", existing)
print(new_slug)  # Output: python-tutorial-2
```

### Problem: URLs Too Long

```python
# Smart truncation at word boundaries
long_title = "This Is an Extremely Long Title That Goes On and On"
slug = slugify(long_title, max_length=30)
print(slug)  # Truncates cleanly at word boundary
```

## See Also

- [String Utilities API Reference](../reference/string-utils.md) - Complete API documentation
- [Slugify Function Reference](../reference/slugify.md) - Detailed technical specification
- [Safe Filename Generation](./safe-filenames.md) - File system specific considerations

---

**Questions?** Check the [API Reference](../reference/string-utils.md) for complete parameter details.
