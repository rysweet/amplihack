# API Client Reference

Complete API reference for the amplihack REST API client.

## Classes

### APIClient

Main class for making HTTP requests with retry logic.

```python
from amplihack.utils import APIClient

client = APIClient(base_url, timeout=30, max_retries=3, retry_delay=1.0)
```

#### Constructor Parameters

| Parameter     | Type  | Default  | Description                             |
| ------------- | ----- | -------- | --------------------------------------- |
| `base_url`    | str   | required | Base URL for all API requests           |
| `timeout`     | int   | 30       | Request timeout in seconds              |
| `max_retries` | int   | 3        | Maximum number of retry attempts        |
| `retry_delay` | float | 1.0      | Initial delay between retries (seconds) |

#### Methods

##### execute(method, endpoint, \*\*kwargs)

Execute an HTTP request with automatic retries.

```python
response = client.execute("GET", "/users", params={"page": 1})
```

**Parameters:**

- `method` (str): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `endpoint` (str): API endpoint path (relative to base_url)
- `**kwargs`: Additional arguments passed to requests library
  - `params` (dict): Query parameters
  - `json` (dict): JSON request body
  - `data` (dict): Form data
  - `headers` (dict): Additional headers

**Returns:** `APIResponse` object

**Raises:**

- `APIError`: General API error
- `RateLimitError`: Rate limit exceeded
- `ValidationError`: Invalid request data

### APIResponse

Response object returned from API calls.

```python
response = client.execute("GET", "/users")
print(response.status_code)  # 200
print(response.data)          # Parsed JSON data
print(response.headers)       # Response headers
```

#### Attributes

| Attribute      | Type              | Description               |
| -------------- | ----------------- | ------------------------- |
| `status_code`  | int               | HTTP status code          |
| `data`         | dict/list         | Parsed JSON response body |
| `headers`      | dict              | Response headers          |
| `raw_response` | requests.Response | Original response object  |

### APIRequest

Data class for structured API requests.

```python
from amplihack.utils import APIRequest

request = APIRequest(
    method="POST",
    endpoint="/users",
    json={"name": "Alice"}
)
```

#### Attributes

| Attribute  | Type | Description                 |
| ---------- | ---- | --------------------------- |
| `method`   | str  | HTTP method                 |
| `endpoint` | str  | API endpoint                |
| `params`   | dict | Query parameters (optional) |
| `json`     | dict | JSON body (optional)        |
| `headers`  | dict | Request headers (optional)  |

## Exceptions

### APIError

Base exception for all API-related errors.

```python
try:
    response = client.execute("GET", "/users")
except APIError as e:
    print(f"Error {e.status_code}: {e.message}")
```

#### Attributes

| Attribute     | Type | Description                        |
| ------------- | ---- | ---------------------------------- |
| `status_code` | int  | HTTP status code                   |
| `message`     | str  | Error message                      |
| `response`    | dict | Full error response (if available) |

### RateLimitError

Raised when API rate limit is exceeded.

```python
try:
    response = client.execute("GET", "/search")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    print(f"Limit: {e.rate_limit}")
```

#### Attributes

| Attribute              | Type | Description                     |
| ---------------------- | ---- | ------------------------------- |
| `retry_after`          | int  | Seconds to wait before retrying |
| `rate_limit`           | int  | Request limit (from headers)    |
| `rate_limit_remaining` | int  | Remaining requests              |

### ValidationError

Raised when request data fails validation.

```python
try:
    response = client.execute("POST", "/users", json={"invalid": "data"})
except ValidationError as e:
    print(f"Validation failed: {e.errors}")
```

#### Attributes

| Attribute | Type | Description              |
| --------- | ---- | ------------------------ |
| `errors`  | dict | Validation error details |

## Retry Logic

The client implements exponential backoff for retries:

1. First retry: wait `retry_delay` seconds
2. Second retry: wait `retry_delay * 2` seconds
3. Third retry: wait `retry_delay * 4` seconds

### Retryable Status Codes

The following status codes trigger automatic retries:

- 429 (Rate Limited)
- 500 (Internal Server Error)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

### Non-Retryable Status Codes

These errors fail immediately without retries:

- 400 (Bad Request)
- 401 (Unauthorized)
- 403 (Forbidden)
- 404 (Not Found)
- 422 (Unprocessable Entity)

## Usage Examples

### Basic GET Request

```python
from amplihack.utils import APIClient

client = APIClient("https://api.example.com")
response = client.execute("GET", "/users")

for user in response.data:
    print(f"User: {user['name']}")
```

### POST with JSON Data

```python
client = APIClient("https://api.example.com")

user_data = {"name": "Alice", "email": "alice@example.com"}
response = client.execute("POST", "/users", json=user_data)

print(f"Created user ID: {response.data['id']}")
```

### Error Handling

```python
from amplihack.utils import APIClient, APIError, RateLimitError

client = APIClient("https://api.example.com")

try:
    response = client.execute("GET", "/protected")
except RateLimitError as e:
    # Wait and retry
    time.sleep(e.retry_after)
    response = client.execute("GET", "/protected")
except APIError as e:
    # Handle other errors
    print(f"API error: {e.message}")
```

### Custom Headers

```python
client = APIClient("https://api.example.com")

headers = {
    "Authorization": "Bearer token123",
    "X-Custom-Header": "value"
}

response = client.execute("GET", "/private", headers=headers)
```

## Configuration Best Practices

### Development Environment

```python
# More retries, longer timeout for unreliable dev servers
client = APIClient(
    base_url="https://dev-api.example.com",
    timeout=60,
    max_retries=5,
    retry_delay=2.0
)
```

### Production Environment

```python
# Balanced settings for production
client = APIClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    retry_delay=1.0
)
```

### High-Performance APIs

```python
# Fast-fail for high-performance APIs
client = APIClient(
    base_url="https://fast-api.example.com",
    timeout=5,
    max_retries=1,
    retry_delay=0.5
)
```

## Thread Safety

The APIClient is thread-safe and can be shared across threads:

```python
from concurrent.futures import ThreadPoolExecutor
from amplihack.utils import APIClient

client = APIClient("https://api.example.com")

def fetch_user(user_id):
    return client.execute("GET", f"/users/{user_id}")

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(fetch_user, i) for i in range(100)]
    results = [f.result() for f in futures]
```

## See Also

- [Using the API Client](../howto/use-api-client.md) - Practical usage guide
- [Error Handling](../concepts/error-handling.md) - Error handling patterns
