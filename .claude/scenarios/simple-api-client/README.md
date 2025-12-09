# simple-api-client

Minimal HTTP client for JSON APIs. Two functions, one exception, zero complexity.

## Quick Start

```python
from simple_api_client import get, post, APIError

# Fetch data
users = get("https://jsonplaceholder.typicode.com/users")
print(users[0]["name"])  # "Leanne Graham"

# Post data
new_post = post("https://jsonplaceholder.typicode.com/posts", {
    "title": "Hello",
    "body": "World",
    "userId": 1
})
print(new_post["id"])  # 101
```

## Installation

```bash
pip install requests
```

Copy `simple_api_client.py` to your project, or run directly:

```bash
python simple_api_client.py
```

## API Reference

### `get(url: str) -> dict | list`

Fetch JSON from a URL.

```python
# Returns parsed JSON (dict or list)
user = get("https://jsonplaceholder.typicode.com/users/1")
# {"id": 1, "name": "Leanne Graham", ...}

posts = get("https://jsonplaceholder.typicode.com/posts")
# [{"id": 1, "title": "...", ...}, ...]
```

### `post(url: str, data: dict) -> dict | list`

Send JSON data to a URL.

```python
result = post("https://jsonplaceholder.typicode.com/posts", {
    "title": "My Post",
    "body": "Content here",
    "userId": 1
})
# {"id": 101, "title": "My Post", ...}
```

### `APIError`

Raised when any API call fails.

```python
class APIError(Exception):
    message: str        # Human-readable error description
    status_code: int | None  # HTTP status code (None for network errors)
```

## Error Handling

```python
from simple_api_client import get, APIError

try:
    data = get("https://jsonplaceholder.typicode.com/posts/999")
except APIError as e:
    print(f"Failed: {e.message}")
    if e.status_code:
        print(f"HTTP {e.status_code}")
```

Common errors:

- **404**: Resource not found
- **500**: Server error
- **Network error**: Connection failed (status_code is None)

## Examples

### Fetch a single resource

```python
post = get("https://jsonplaceholder.typicode.com/posts/1")
print(f"Title: {post['title']}")
```

### Fetch a collection

```python
comments = get("https://jsonplaceholder.typicode.com/posts/1/comments")
for comment in comments:
    print(f"- {comment['email']}: {comment['body'][:50]}...")
```

### Create a resource

```python
new_comment = post("https://jsonplaceholder.typicode.com/comments", {
    "postId": 1,
    "name": "My Comment",
    "email": "test@example.com",
    "body": "This is a comment."
})
print(f"Created comment {new_comment['id']}")
```

### Handle errors gracefully

```python
def safe_get(url):
    try:
        return get(url)
    except APIError as e:
        print(f"Error: {e.message}")
        return None

user = safe_get("https://jsonplaceholder.typicode.com/users/1")
if user:
    print(user["name"])
```

## Requirements

- Python 3.8+
- `requests` library

## Design

This module follows the brick philosophy:

- **Single responsibility**: HTTP JSON operations only
- **Minimal API**: Two functions, one exception
- **No configuration**: Sensible defaults, no options to misconfigure
- **Fail clearly**: All errors surface as `APIError` with context

Total: < 150 lines of code.
