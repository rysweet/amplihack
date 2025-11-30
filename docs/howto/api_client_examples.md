# API Client Usage Examples

Practical examples and patterns for using the api_client module.

## Basic Operations

### Simple REST API Integration

```python
from api_client import APIClient, ClientConfig

# Configure client for JSONPlaceholder (test API)
config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# GET: Fetch a user
user = client.get("/users/1").json()
print(f"User: {user['name']} ({user['email']})")
# Output: User: Leanne Graham (Sincere@april.biz)

# POST: Create a new post
new_post = {
    "title": "Test Post",
    "body": "This is a test post created via API",
    "userId": 1
}
response = client.post("/posts", json=new_post)
created_post = response.json()
print(f"Created post with ID: {created_post['id']}")
# Output: Created post with ID: 101

# PUT: Update a post
updated_data = {"title": "Updated Title"}
response = client.put(f"/posts/{created_post['id']}", json=updated_data)
print(f"Updated post: {response.status_code}")
# Output: Updated post: 200

# DELETE: Remove a post
response = client.delete(f"/posts/{created_post['id']}")
print(f"Deleted post: {response.status_code}")
# Output: Deleted post: 200
```

## Authentication Examples

### Bearer Token Authentication

```python
from api_client import APIClient, ClientConfig

# GitHub API with personal access token
config = ClientConfig(
    base_url="https://api.github.com",
    api_key="ghp_your_personal_access_token"
)
client = APIClient(config)

# The api_key is automatically added as Bearer token
user = client.get("/user").json()
print(f"Authenticated as: {user['login']}")

# List your repositories
repos = client.get("/user/repos", params={"per_page": 5}).json()
for repo in repos:
    print(f"- {repo['name']}: {repo['description']}")
```

### Custom Authentication Headers

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

# Add custom authentication headers
response = client.get(
    "/protected-resource",
    headers={
        "X-API-Key": "your-api-key",
        "X-Client-ID": "your-client-id"
    }
)
```

## Error Handling Patterns

### Comprehensive Error Handling

```python
from api_client import APIClient, ClientConfig, HTTPError, APIError
import sys

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

def safe_api_call(endpoint):
    """Make API call with comprehensive error handling"""
    try:
        response = client.get(endpoint)
        return response.json()

    except HTTPError as e:
        # Handle specific HTTP errors
        if e.status_code == 404:
            print(f"Resource not found: {endpoint}")
            return None
        elif e.status_code == 401:
            print("Authentication failed. Check your API key.")
            sys.exit(1)
        elif e.status_code == 429:
            print("Rate limited. Please try again later.")
            return None
        elif e.status_code >= 500:
            print(f"Server error ({e.status_code}). Service may be down.")
            return None
        else:
            print(f"HTTP error {e.status_code}: {e.message}")
            return None

    except APIError as e:
        # Handle connection and other API errors
        print(f"API connection error: {e}")
        return None

    except Exception as e:
        # Catch any unexpected errors
        print(f"Unexpected error: {e}")
        return None

# Usage
result = safe_api_call("/users/1")
if result:
    print(f"Successfully fetched: {result['name']}")
```

### Retry with Custom Logic

```python
from api_client import APIClient, ClientConfig, HTTPError
import time

config = ClientConfig(
    base_url="https://api.example.com",
    max_retries=0  # Disable automatic retries
)
client = APIClient(config)

def custom_retry(endpoint, max_attempts=5):
    """Custom retry logic with progressive backoff"""
    for attempt in range(max_attempts):
        try:
            return client.get(endpoint)

        except HTTPError as e:
            if e.status_code == 429:  # Rate limited
                # Check for Retry-After header
                retry_after = e.headers.get('Retry-After', 2 ** attempt)
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(int(retry_after))

            elif 500 <= e.status_code < 600:  # Server error
                wait_time = 2 ** attempt
                print(f"Server error. Retrying in {wait_time}s...")
                time.sleep(wait_time)

            else:
                # Don't retry client errors
                raise

    raise APIError(f"Failed after {max_attempts} attempts")
```

## Pagination Patterns

### Cursor-Based Pagination

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

def fetch_all_with_cursor(endpoint):
    """Fetch all pages using cursor pagination"""
    results = []
    cursor = None

    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor

        response = client.get(endpoint, params=params)
        data = response.json()

        results.extend(data["items"])

        # Check for next page
        cursor = data.get("next_cursor")
        if not cursor:
            break

        print(f"Fetched {len(results)} items so far...")

    return results

# Usage
all_items = fetch_all_with_cursor("/items")
print(f"Total items fetched: {len(all_items)}")
```

### Page-Based Pagination

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

def fetch_all_pages(endpoint, per_page=10):
    """Fetch all pages of results"""
    all_results = []
    page = 1

    while True:
        response = client.get(endpoint, params={
            "_page": page,
            "_limit": per_page
        })

        results = response.json()

        # Empty page means we're done
        if not results:
            break

        all_results.extend(results)
        print(f"Fetched page {page} ({len(results)} items)")
        page += 1

    return all_results

# Usage
all_posts = fetch_all_pages("/posts", per_page=20)
print(f"Total posts: {len(all_posts)}")
```

## Concurrent Requests

### Thread Pool for Parallel Requests

```python
from api_client import APIClient, ClientConfig
import concurrent.futures

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)  # Single client, thread-safe

def fetch_post(post_id):
    """Fetch a single post"""
    response = client.get(f"/posts/{post_id}")
    return response.json()

# Fetch multiple posts in parallel
post_ids = range(1, 21)  # Posts 1-20

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Submit all tasks
    futures = {executor.submit(fetch_post, pid): pid for pid in post_ids}

    # Collect results as they complete
    results = []
    for future in concurrent.futures.as_completed(futures):
        post_id = futures[future]
        try:
            post = future.result()
            results.append(post)
            print(f"Fetched post {post_id}: {post['title'][:30]}...")
        except Exception as e:
            print(f"Failed to fetch post {post_id}: {e}")

print(f"Successfully fetched {len(results)} posts")
```

### Async-like Pattern with Threads

```python
from api_client import APIClient, ClientConfig
import threading
import queue

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

class AsyncAPIClient:
    """Async-like wrapper using threads"""

    def __init__(self, client):
        self.client = client
        self.results = queue.Queue()

    def get_async(self, endpoint, callback=None):
        """Non-blocking GET request"""
        def worker():
            try:
                response = self.client.get(endpoint)
                result = response.json()
                if callback:
                    callback(result)
                self.results.put(("success", result))
            except Exception as e:
                self.results.put(("error", e))

        thread = threading.Thread(target=worker)
        thread.start()
        return thread

    def wait_all(self, threads):
        """Wait for all async requests to complete"""
        for thread in threads:
            thread.join()

        # Collect all results
        results = []
        while not self.results.empty():
            status, data = self.results.get()
            if status == "success":
                results.append(data)
        return results

# Usage
async_client = AsyncAPIClient(client)

# Start multiple async requests
threads = []
for user_id in range(1, 6):
    thread = async_client.get_async(
        f"/users/{user_id}",
        callback=lambda u: print(f"Got user: {u['name']}")
    )
    threads.append(thread)

# Do other work while requests are in progress
print("Doing other work...")

# Wait for all requests to complete
results = async_client.wait_all(threads)
print(f"All {len(results)} users fetched")
```

## File Operations

### Upload Files

```python
from api_client import APIClient, ClientConfig
import json

config = ClientConfig(base_url="https://httpbin.org")
client = APIClient(config)

# Upload JSON file
data_to_upload = {"key": "value", "items": [1, 2, 3]}
response = client.post(
    "/post",
    data=json.dumps(data_to_upload).encode(),
    headers={"Content-Type": "application/json"}
)
echo = response.json()
print(f"Server received: {echo['data']}")

# Upload binary file
with open("image.png", "rb") as f:
    image_data = f.read()

response = client.post(
    "/post",
    data=image_data,
    headers={"Content-Type": "image/png"}
)
print(f"Uploaded {len(image_data)} bytes")
```

### Download Files

```python
from api_client import APIClient, ClientConfig
from pathlib import Path

config = ClientConfig(base_url="https://httpbin.org")
client = APIClient(config)

# Download binary data
response = client.get("/image/png")

# Save to file
output_path = Path("downloaded_image.png")
output_path.write_bytes(response.content)
print(f"Downloaded image saved to {output_path}")

# Download with progress tracking
def download_with_progress(url, output_file):
    """Download file with progress indication"""
    response = client.get(url)

    # Check content length
    total_size = int(response.headers.get('Content-Length', 0))

    if total_size > 0:
        print(f"Downloading {total_size:,} bytes...")

    # Save the file
    Path(output_file).write_bytes(response.content)
    print(f"Download complete: {output_file}")

# Usage
download_with_progress("/image/jpeg", "image.jpg")
```

## Caching Responses

### Simple Memory Cache

```python
from api_client import APIClient, ClientConfig
import time
from functools import lru_cache
import hashlib

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

class CachedAPIClient:
    """Client with response caching"""

    def __init__(self, client, cache_ttl=300):
        self.client = client
        self.cache = {}
        self.cache_ttl = cache_ttl  # Cache TTL in seconds

    def _cache_key(self, method, endpoint, params=None):
        """Generate cache key from request parameters"""
        key_parts = [method, endpoint]
        if params:
            key_parts.append(str(sorted(params.items())))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, endpoint, params=None, force_refresh=False):
        """GET with caching"""
        cache_key = self._cache_key("GET", endpoint, params)

        # Check cache unless forced refresh
        if not force_refresh and cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            age = time.time() - timestamp

            if age < self.cache_ttl:
                print(f"Cache hit for {endpoint} (age: {age:.1f}s)")
                return cached_data

        # Fetch fresh data
        print(f"Cache miss for {endpoint}, fetching...")
        response = self.client.get(endpoint, params=params)
        data = response.json()

        # Update cache
        self.cache[cache_key] = (data, time.time())

        return data

    def clear_cache(self):
        """Clear all cached responses"""
        self.cache.clear()
        print("Cache cleared")

# Usage
cached_client = CachedAPIClient(client, cache_ttl=60)

# First call fetches from API
user1 = cached_client.get("/users/1")
print(f"User: {user1['name']}")

# Second call uses cache
user1_again = cached_client.get("/users/1")  # Cache hit

# Force refresh
user1_fresh = cached_client.get("/users/1", force_refresh=True)
```

## WebSocket-like Polling

### Long Polling Pattern

```python
from api_client import APIClient, ClientConfig
import time

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

def poll_for_updates(resource_id, interval=5, timeout=300):
    """Poll for resource updates"""
    last_version = None
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = client.get(f"/resources/{resource_id}")
            data = response.json()

            # Check if resource has changed
            current_version = data.get("version") or data.get("updated_at")

            if current_version != last_version:
                if last_version is not None:  # Skip first fetch
                    print(f"Resource updated: {current_version}")
                    yield data

                last_version = current_version

        except Exception as e:
            print(f"Polling error: {e}")

        time.sleep(interval)

    print("Polling timeout reached")

# Usage
for update in poll_for_updates("resource123", interval=2):
    print(f"Got update: {update}")
    # Process the update
```

## Testing Support

### Mock Client for Testing

```python
from api_client import APIClient, ClientConfig
from unittest.mock import MagicMock
import json

class MockAPIClient:
    """Mock client for testing"""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.call_history = []

    def get(self, endpoint, **kwargs):
        """Mock GET request"""
        self.call_history.append(("GET", endpoint, kwargs))

        if endpoint in self.responses:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = self.responses[endpoint]
            return response

        # Default 404 response
        response = MagicMock()
        response.status_code = 404
        raise HTTPError(404, "Not found")

    def post(self, endpoint, **kwargs):
        """Mock POST request"""
        self.call_history.append(("POST", endpoint, kwargs))

        response = MagicMock()
        response.status_code = 201
        response.json.return_value = {"id": 123, **kwargs.get("json", {})}
        return response

# Usage in tests
def test_user_service():
    # Setup mock client
    mock_client = MockAPIClient({
        "/users/1": {"id": 1, "name": "Test User"},
        "/users/1/posts": [
            {"id": 1, "title": "Post 1"},
            {"id": 2, "title": "Post 2"}
        ]
    })

    # Test your code
    user = mock_client.get("/users/1").json()
    assert user["name"] == "Test User"

    posts = mock_client.get("/users/1/posts").json()
    assert len(posts) == 2

    # Verify calls were made
    assert len(mock_client.call_history) == 2
    assert mock_client.call_history[0] == ("GET", "/users/1", {})
```
