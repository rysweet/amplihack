# Migration Guide

Learn how to migrate from requests or httpx to the REST API Client library.

## Migrating from Requests

### Basic Requests

**Before (requests):**

```python
import requests

response = requests.get("https://api.example.com/users")
data = response.json()
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient

client = APIClient(base_url="https://api.example.com")
response = client.get("/users")
data = response.data  # Already parsed
```

### POST with JSON

**Before (requests):**

```python
import requests

response = requests.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"}
)
```

**After (rest_api_client):**

```python
client = APIClient(base_url="https://api.example.com")
response = client.post(
    "/users",
    json={"name": "Alice", "email": "alice@example.com"}
)
```

### Headers and Authentication

**Before (requests):**

```python
import requests

headers = {
    "Authorization": "Bearer token123",
    "User-Agent": "MyApp/1.0"
}
response = requests.get(
    "https://api.example.com/protected",
    headers=headers
)
```

**After (rest_api_client):**

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": "Bearer token123",
        "User-Agent": "MyApp/1.0"
    }
)
response = client.get("/protected")
```

### Query Parameters

**Before (requests):**

```python
import requests

params = {"page": 1, "per_page": 100}
response = requests.get(
    "https://api.example.com/users",
    params=params
)
```

**After (rest_api_client):**

```python
client = APIClient(base_url="https://api.example.com")
response = client.get("/users", params={"page": 1, "per_page": 100})
```

### Error Handling

**Before (requests):**

```python
import requests

try:
    response = requests.get("https://api.example.com/users")
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if response.status_code == 401:
        print("Authentication required")
    elif response.status_code == 429:
        print("Rate limited")
except requests.exceptions.ConnectionError:
    print("Network error")
except requests.exceptions.Timeout:
    print("Request timed out")
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient
from rest_api_client.exceptions import (
    AuthenticationError,
    RateLimitError,
    NetworkError,
    TimeoutError
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users")
except AuthenticationError:
    print("Authentication required")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except NetworkError:
    print("Network error")
except TimeoutError:
    print("Request timed out")
```

### Sessions

**Before (requests):**

```python
import requests

with requests.Session() as session:
    session.headers.update({"Authorization": "Bearer token"})
    response1 = session.get("https://api.example.com/users")
    response2 = session.get("https://api.example.com/posts")
```

**After (rest_api_client):**

```python
with APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token"}
) as client:
    response1 = client.get("/users")
    response2 = client.get("/posts")
```

### Retry Logic

**Before (requests with urllib3):**

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

response = session.get("https://api.example.com/users")
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient
from rest_api_client.config import RetryConfig

client = APIClient(
    base_url="https://api.example.com",
    retry_config=RetryConfig(
        max_attempts=3,
        exponential_base=2.0,
        retry_on_statuses=[500, 502, 503, 504]
    )
)
response = client.get("/users")  # Automatic retry
```

## Migrating from HTTPX

### Sync Client

**Before (httpx):**

```python
import httpx

with httpx.Client(base_url="https://api.example.com") as client:
    response = client.get("/users")
    data = response.json()
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient

with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/users")
    data = response.data
```

### Async Client

**Before (httpx):**

```python
import httpx
import asyncio

async def fetch_data():
    async with httpx.AsyncClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        return response.json()

data = asyncio.run(fetch_data())
```

**After (rest_api_client):**

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def fetch_data():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        return response.data

data = asyncio.run(fetch_data())
```

### Timeout Configuration

**Before (httpx):**

```python
import httpx

timeout = httpx.Timeout(10.0, connect=5.0)
client = httpx.Client(timeout=timeout)
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    timeout=10  # Total timeout in seconds
)
```

### Custom Headers

**Before (httpx):**

```python
import httpx

headers = {"X-Custom-Header": "value"}
client = httpx.Client(
    base_url="https://api.example.com",
    headers=headers
)
```

**After (rest_api_client):**

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-Custom-Header": "value"}
)
```

## Feature Comparison

| Feature            | requests | httpx | rest_api_client |
| ------------------ | -------- | ----- | --------------- |
| Sync support       | ✅       | ✅    | ✅              |
| Async support      | ❌       | ✅    | ✅              |
| Built-in retry     | ❌       | ❌    | ✅              |
| Rate limiting      | ❌       | ❌    | ✅              |
| Typed exceptions   | ❌       | ❌    | ✅              |
| Connection pooling | ✅       | ✅    | ✅              |
| Base URL           | ❌       | ✅    | ✅              |
| Automatic JSON     | Partial  | ✅    | ✅              |
| Type hints         | Partial  | ✅    | ✅              |

## Common Patterns

### Creating a Reusable Client Class

**Before (requests):**

```python
import requests

class MyAPIClient:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}"
        })
        self.base_url = "https://api.example.com"

    def get_users(self):
        response = self.session.get(f"{self.base_url}/users")
        response.raise_for_status()
        return response.json()

    def close(self):
        self.session.close()
```

**After (rest_api_client):**

```python
from rest_api_client import APIClient

class MyAPIClient(APIClient):
    def __init__(self, api_key):
        super().__init__(
            base_url="https://api.example.com",
            headers={"Authorization": f"Bearer {api_key}"}
        )

    def get_users(self):
        response = self.get("/users")
        return response.data
```

### Handling Pagination

**Before (requests):**

```python
import requests

def get_all_users():
    users = []
    page = 1

    while True:
        response = requests.get(
            "https://api.example.com/users",
            params={"page": page}
        )
        data = response.json()

        users.extend(data["items"])

        if page >= data["total_pages"]:
            break
        page += 1

    return users
```

**After (rest_api_client):**

```python
def get_all_users():
    client = APIClient(base_url="https://api.example.com")
    users = []
    page = 1

    while True:
        response = client.get("/users", params={"page": page})
        users.extend(response.data["items"])

        if page >= response.data["total_pages"]:
            break
        page += 1

    return users
```

### File Uploads

**Before (requests):**

```python
import requests

files = {"file": open("document.pdf", "rb")}
data = {"description": "Important document"}

response = requests.post(
    "https://api.example.com/upload",
    files=files,
    data=data
)
```

**After (rest_api_client):**

```python
client = APIClient(base_url="https://api.example.com")

files = {"file": open("document.pdf", "rb")}
data = {"description": "Important document"}

response = client.post(
    "/upload",
    files=files,
    data=data
)
```

## Benefits of Migration

### 1. Built-in Resilience

- Automatic retry with exponential backoff
- Rate limiting prevents 429 errors
- Better error recovery

### 2. Better Error Handling

- Typed exceptions for each error type
- Meaningful error messages
- Easy to handle specific errors

### 3. Cleaner Code

- No need for manual retry logic
- Automatic JSON parsing
- Consistent interface

### 4. Performance

- Connection pooling by default
- Efficient rate limiting
- Async support when needed

### 5. Type Safety

- Full type hints
- IDE autocomplete
- Catch errors at development time

## Migration Checklist

- [ ] Install rest_api_client: `pip install rest_api_client`
- [ ] Replace requests/httpx imports
- [ ] Create APIClient with base_url
- [ ] Move default headers to client initialization
- [ ] Update error handling to use typed exceptions
- [ ] Replace manual retry logic with RetryConfig
- [ ] Test rate limiting behavior
- [ ] Update type hints if using mypy
- [ ] Run tests to verify functionality

## Gradual Migration

You can migrate gradually by using both libraries side by side:

```python
import requests
from rest_api_client import APIClient

# Old code using requests
legacy_response = requests.get("https://old-api.example.com/data")

# New code using rest_api_client
client = APIClient(base_url="https://new-api.example.com")
new_response = client.get("/data")
```

This allows you to migrate endpoint by endpoint without breaking existing code.

## Getting Help

If you encounter issues during migration:

1. Check the [API Reference](../reference/api.md)
2. Review [examples](../tutorials/getting-started.md)
3. Look at [error handling guide](./error-handling.md)
4. File an issue on GitHub with your migration scenario
