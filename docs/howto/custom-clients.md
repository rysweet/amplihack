# How to Extend the Client

Learn how to create custom clients by extending the base APIClient class.

## Why Extend the Client?

Create custom clients to:

- Add API-specific methods
- Implement custom authentication
- Add business logic
- Create type-safe wrappers
- Handle API-specific errors

## Basic Extension

### Creating a Custom Client

```python
from rest_api_client import APIClient
from rest_api_client.exceptions import APIError

class GitHubClient(APIClient):
    """Custom client for GitHub API."""

    def __init__(self, token=None, **kwargs):
        super().__init__(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {token}" if token else None
            },
            **kwargs
        )

    def get_user(self, username):
        """Get a GitHub user by username."""
        return self.get(f"/users/{username}")

    def get_repos(self, username):
        """Get repositories for a user."""
        return self.get(f"/users/{username}/repos")

    def create_repo(self, name, description=None, private=False):
        """Create a new repository."""
        return self.post("/user/repos", json={
            "name": name,
            "description": description,
            "private": private
        })

# Usage
client = GitHubClient(token="your-token-here")
user = client.get_user("octocat")
repos = client.get_repos("octocat")
```

## Adding Authentication

### OAuth2 Client

```python
import time
from rest_api_client import APIClient
from rest_api_client.exceptions import AuthenticationError

class OAuth2Client(APIClient):
    """Client with OAuth2 authentication."""

    def __init__(self, client_id, client_secret, base_url, **kwargs):
        super().__init__(base_url=base_url, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expires_at = 0

    def authenticate(self):
        """Get or refresh access token."""
        if self.access_token and time.time() < self.token_expires_at:
            return  # Token still valid

        response = self.post("/oauth/token", data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        })

        self.access_token = response.data["access_token"]
        self.token_expires_at = time.time() + response.data["expires_in"] - 60
        self.headers["Authorization"] = f"Bearer {self.access_token}"

    def request(self, method, endpoint, **kwargs):
        """Override request to ensure authentication."""
        self.authenticate()
        try:
            return super().request(method, endpoint, **kwargs)
        except AuthenticationError:
            # Token might be invalid, try refreshing
            self.access_token = None
            self.authenticate()
            return super().request(method, endpoint, **kwargs)

# Usage
client = OAuth2Client(
    client_id="your-client-id",
    client_secret="your-client-secret",  # pragma: allowlist secret
    base_url="https://api.example.com"
)
response = client.get("/protected/resource")  # Automatically authenticates
```

### API Key Authentication

```python
class APIKeyClient(APIClient):
    """Client with API key authentication."""

    def __init__(self, api_key, base_url, key_location="header", **kwargs):
        super().__init__(base_url=base_url, **kwargs)
        self.api_key = api_key
        self.key_location = key_location

        if key_location == "header":
            self.headers["X-API-Key"] = api_key
        # For query parameter authentication, override prepare_request

    def prepare_request(self, method, endpoint, **kwargs):
        """Add API key to query parameters if needed."""
        request = super().prepare_request(method, endpoint, **kwargs)

        if self.key_location == "query":
            if request.params is None:
                request.params = {}
            request.params["api_key"] = self.api_key

        return request

# Usage
# Header authentication
client1 = APIKeyClient(
    api_key="your-key",  # pragma: allowlist secret
    base_url="https://api.example.com",
    key_location="header"
)

# Query parameter authentication
client2 = APIKeyClient(
    api_key="your-key",  # pragma: allowlist secret
    base_url="https://api.example.com",
    key_location="query"
)
```

## Adding Business Logic

### Domain-Specific Methods

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    id: int
    username: str
    email: str
    created_at: datetime

@dataclass
class Post:
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime

class BlogAPIClient(APIClient):
    """Client for a blog API with typed responses."""

    def __init__(self, base_url, **kwargs):
        super().__init__(base_url=base_url, **kwargs)

    def get_user(self, user_id: int) -> User:
        """Get a user by ID."""
        response = self.get(f"/users/{user_id}")
        data = response.data
        return User(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            created_at=datetime.fromisoformat(data["created_at"])
        )

    def get_user_posts(self, user_id: int) -> List[Post]:
        """Get all posts by a user."""
        response = self.get(f"/users/{user_id}/posts")
        return [
            Post(
                id=p["id"],
                title=p["title"],
                content=p["content"],
                author_id=p["author_id"],
                created_at=datetime.fromisoformat(p["created_at"])
            )
            for p in response.data
        ]

    def create_post(self, title: str, content: str, author_id: int) -> Post:
        """Create a new blog post."""
        response = self.post("/posts", json={
            "title": title,
            "content": content,
            "author_id": author_id
        })
        data = response.data
        return Post(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            author_id=data["author_id"],
            created_at=datetime.fromisoformat(data["created_at"])
        )

# Usage with type hints
client = BlogAPIClient(base_url="https://blog-api.example.com")
user: User = client.get_user(123)
posts: List[Post] = client.get_user_posts(user.id)
new_post: Post = client.create_post(
    title="My New Post",
    content="Hello, world!",
    author_id=user.id
)
```

## Custom Error Handling

### API-Specific Exceptions

```python
from rest_api_client.exceptions import APIError

class BlogAPIError(APIError):
    """Base exception for blog API."""
    pass

class PostNotFoundError(BlogAPIError):
    """Post not found."""
    def __init__(self, post_id):
        super().__init__(f"Post {post_id} not found", status_code=404)

class InsufficientKarmaError(BlogAPIError):
    """User doesn't have enough karma."""
    def __init__(self, required, current):
        self.required = required
        self.current = current
        super().__init__(
            f"Insufficient karma: need {required}, have {current}",
            status_code=403
        )

class BlogClient(APIClient):
    """Client with custom error handling."""

    def handle_error_response(self, response):
        """Convert API errors to custom exceptions."""
        if response.status_code == 404:
            # Parse error details from response
            if "post" in response.text.lower():
                error_data = response.json()
                raise PostNotFoundError(error_data.get("post_id"))

        if response.status_code == 403:
            error_data = response.json()
            if error_data.get("error_code") == "INSUFFICIENT_KARMA":
                raise InsufficientKarmaError(
                    required=error_data.get("required_karma"),
                    current=error_data.get("current_karma")
                )

        # Fall back to default error handling
        super().handle_error_response(response)

# Usage
client = BlogClient(base_url="https://api.example.com")

try:
    post = client.get("/posts/99999")
except PostNotFoundError as e:
    print(f"Post not found: {e}")
except InsufficientKarmaError as e:
    print(f"Need {e.required - e.current} more karma")
```

## Adding Caching

### Simple Cache Implementation

```python
import time
from functools import lru_cache
import hashlib
import json

class CachedClient(APIClient):
    """Client with simple caching."""

    def __init__(self, cache_ttl=300, **kwargs):
        super().__init__(**kwargs)
        self.cache_ttl = cache_ttl
        self.cache = {}

    def _cache_key(self, method, endpoint, **kwargs):
        """Generate cache key from request parameters."""
        key_data = {
            "method": method,
            "endpoint": endpoint,
            "params": kwargs.get("params"),
            "json": kwargs.get("json")
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cacheable(self, method):
        """Only cache GET requests."""
        return method.upper() == "GET"

    def request(self, method, endpoint, **kwargs):
        """Override to add caching."""
        if not self._is_cacheable(method):
            return super().request(method, endpoint, **kwargs)

        cache_key = self._cache_key(method, endpoint, **kwargs)

        # Check cache
        if cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_response

        # Make request and cache result
        response = super().request(method, endpoint, **kwargs)
        self.cache[cache_key] = (response, time.time())
        return response

    def clear_cache(self):
        """Clear the cache."""
        self.cache.clear()

# Usage
client = CachedClient(
    base_url="https://api.example.com",
    cache_ttl=600  # Cache for 10 minutes
)

# First call hits the API
response1 = client.get("/expensive/data")

# Second call returns cached result
response2 = client.get("/expensive/data")  # Fast!

# Clear cache when needed
client.clear_cache()
```

## Adding Pagination Support

### Automatic Pagination

```python
class PaginatedClient(APIClient):
    """Client with automatic pagination."""

    def paginate(self, endpoint, params=None, max_pages=None):
        """Generator that automatically handles pagination."""
        params = params or {}
        page = 1

        while True:
            params["page"] = page
            response = self.get(endpoint, params=params)

            # Yield items from current page
            items = response.data.get("items", [])
            for item in items:
                yield item

            # Check if there are more pages
            total_pages = response.data.get("total_pages", 1)
            if page >= total_pages:
                break

            if max_pages and page >= max_pages:
                break

            page += 1

    def get_all(self, endpoint, params=None, max_pages=None):
        """Get all items from paginated endpoint."""
        return list(self.paginate(endpoint, params, max_pages))

# Usage
client = PaginatedClient(base_url="https://api.example.com")

# Iterate through all pages
for item in client.paginate("/users"):
    print(f"User: {item['name']}")

# Get all at once (be careful with large datasets)
all_users = client.get_all("/users")

# Limit to first 5 pages
recent_posts = client.get_all("/posts", max_pages=5)
```

## Adding Retry Logic

### Custom Retry Strategy

```python
import random
from rest_api_client.exceptions import NetworkError, ServerError

class SmartRetryClient(APIClient):
    """Client with smart retry logic."""

    def should_retry(self, exception, attempt):
        """Determine if request should be retried."""
        # Always retry network errors
        if isinstance(exception, NetworkError):
            return attempt < 5

        # Retry server errors with backoff
        if isinstance(exception, ServerError):
            return attempt < 3

        # Don't retry client errors (4xx)
        return False

    def calculate_delay(self, attempt):
        """Calculate delay with exponential backoff and jitter."""
        base_delay = 2 ** attempt
        jitter = random.uniform(0, 1)
        return base_delay + jitter

    def request_with_retry(self, method, endpoint, **kwargs):
        """Make request with custom retry logic."""
        attempt = 0
        last_exception = None

        while attempt < 5:
            try:
                return self.request(method, endpoint, **kwargs)
            except Exception as e:
                last_exception = e
                if not self.should_retry(e, attempt):
                    raise

                delay = self.calculate_delay(attempt)
                print(f"Retry {attempt + 1} after {delay:.1f}s: {e}")
                time.sleep(delay)
                attempt += 1

        raise last_exception

# Usage
client = SmartRetryClient(base_url="https://flaky-api.example.com")
response = client.request_with_retry("GET", "/unreliable/endpoint")
```

## Testing Custom Clients

```python
import unittest
from unittest.mock import Mock, patch
from rest_api_client.models import Response

class TestCustomClient(unittest.TestCase):
    def test_github_client_get_user(self):
        """Test GitHubClient.get_user method."""
        client = GitHubClient(token="test-token")

        # Mock the underlying get method
        mock_response = Response(
            status_code=200,
            headers={},
            data={"login": "octocat", "id": 1}
        )
        client.get = Mock(return_value=mock_response)

        # Test the method
        user = client.get_user("octocat")
        self.assertEqual(user.data["login"], "octocat")
        client.get.assert_called_with("/users/octocat")

    def test_cached_client(self):
        """Test caching functionality."""
        client = CachedClient(
            base_url="https://api.example.com",
            cache_ttl=60
        )

        # Mock the request method
        mock_response = Response(status_code=200, headers={}, data={"test": "data"})
        with patch.object(APIClient, "request", return_value=mock_response) as mock_request:
            # First call should hit the API
            response1 = client.request("GET", "/test")
            self.assertEqual(mock_request.call_count, 1)

            # Second call should use cache
            response2 = client.request("GET", "/test")
            self.assertEqual(mock_request.call_count, 1)  # Still 1

            # Clear cache and call again
            client.clear_cache()
            response3 = client.request("GET", "/test")
            self.assertEqual(mock_request.call_count, 2)  # Now 2
```

## Best Practices

1. **Keep it simple**: Only add what you need
2. **Use composition**: Consider using the client as a dependency rather than inheritance
3. **Document your methods**: Add docstrings with usage examples
4. **Handle errors gracefully**: Convert API errors to meaningful exceptions
5. **Test thoroughly**: Mock API responses for unit tests
6. **Version your client**: Match it to the API version you're targeting

## Summary

Extending the APIClient allows you to:

- Create API-specific interfaces
- Add custom authentication
- Implement business logic
- Handle errors appropriately
- Add features like caching and pagination

Build custom clients that make your API integration clean, type-safe, and easy to use.
