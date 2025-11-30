# REST API Client

A simple, robust REST API client built with Python's standard library for making HTTP requests with rate limiting and automatic retries.

## Quick Start

Make your first API request in 3 steps:

```python
from api_client import RESTClient

# Create client
client = RESTClient("https://api.example.com")

# Make request
response = client.get("/users/123")

# Access data
user = response.json()
print(f"User: {user['name']}")
```

## Contents

- [Installation](#installation)
- [Features](#features)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Examples](#examples)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Related Documentation](#related-documentation)

## Installation

The REST API Client requires Python 3.8+ and uses only standard library modules:

```bash
# Copy the module to your project
cp -r .claude/scenarios/api-client/ /path/to/your/project/

# Import and use
python -c "from api_client import RESTClient; print('Ready!')"
```

No external dependencies required - uses `urllib`, `json`, `time`, and `dataclasses` from the standard library.

## Features

- **Standard Library Only** - No external dependencies
- **Rate Limiting** - Configurable requests per second
- **Automatic Retries** - Exponential backoff for transient failures
- **Simple Interface** - Intuitive method names matching HTTP verbs
- **Response Objects** - Structured responses with convenient `json()` method
- **Timeout Support** - Configurable request timeouts
- **Custom Headers** - Easy header management

## Basic Usage

### Creating a Client

```python
from api_client import RESTClient

# Basic client
client = RESTClient("https://api.github.com")

# With configuration
client = RESTClient(
    base_url="https://api.github.com",
    timeout=30,
    max_retries=3,
    rate_limit=10  # 10 requests per second
)
```

### Making Requests

```python
# GET request
response = client.get("/repos/python/cpython")
print(f"Stars: {response.json()['stargazers_count']}")

# POST with JSON body
new_issue = {
    "title": "Bug report",
    "body": "Description here"
}
response = client.post("/repos/owner/repo/issues", json=new_issue)
print(f"Created issue #{response.json()['number']}")

# PUT to update
update_data = {"description": "Updated description"}
response = client.put("/repos/owner/repo", json=update_data)

# DELETE resource
response = client.delete("/repos/owner/repo/issues/123")
```

## API Reference

### RESTClient Class

```python
RESTClient(base_url: str, timeout: int = 30, max_retries: int = 3, rate_limit: float = 10)
```

**Parameters:**

- `base_url` - Base URL for all requests (e.g., "https://api.example.com")
- `timeout` - Request timeout in seconds (default: 30)
- `max_retries` - Maximum retry attempts for failed requests (default: 3)
- `rate_limit` - Maximum requests per second (default: 10)

### Methods

#### get(path: str, params: dict = None, headers: dict = None) -> Response

Makes a GET request.

```python
response = client.get("/users", params={"page": 2})
```

#### post(path: str, json: dict = None, data: bytes = None, headers: dict = None) -> Response

Makes a POST request.

```python
response = client.post("/users", json={"name": "Alice"})
```

#### put(path: str, json: dict = None, data: bytes = None, headers: dict = None) -> Response

Makes a PUT request.

```python
response = client.put("/users/123", json={"name": "Bob"})
```

#### delete(path: str, headers: dict = None) -> Response

Makes a DELETE request.

```python
response = client.delete("/users/123")
```

#### patch(path: str, json: dict = None, data: bytes = None, headers: dict = None) -> Response

Makes a PATCH request.

```python
response = client.patch("/users/123", json={"email": "new@example.com"})
```

### Response Object

```python
@dataclass
class Response:
    status_code: int
    headers: dict
    body: bytes
    url: str

    def json(self) -> dict:
        """Parse response body as JSON."""
        return json.loads(self.body)
```

**Attributes:**

- `status_code` - HTTP status code (200, 404, etc.)
- `headers` - Response headers as dictionary
- `body` - Raw response body as bytes
- `url` - Final URL after redirects

**Methods:**

- `json()` - Parse body as JSON and return dictionary

## Configuration

### Environment Variables

Configure defaults via environment variables:

```bash
# Set default timeout
export API_CLIENT_TIMEOUT=60

# Set default rate limit
export API_CLIENT_RATE_LIMIT=5

# Run your script
python my_api_script.py
```

### Per-Request Configuration

Override client defaults for specific requests:

```python
# Custom timeout for slow endpoint
response = client.get("/slow-endpoint", headers={"X-Timeout": "120"})

# Custom headers
response = client.get("/users", headers={
    "Authorization": "Bearer token123",
    "Accept": "application/json"
})
```

## Examples

### GitHub API Integration

```python
from api_client import RESTClient

# Initialize GitHub client
github = RESTClient(
    base_url="https://api.github.com",
    rate_limit=5  # GitHub's rate limit
)

# Get repository information
repo_response = github.get("/repos/python/cpython")
repo = repo_response.json()
print(f"Python has {repo['stargazers_count']} stars")

# List recent commits
commits_response = github.get(
    "/repos/python/cpython/commits",
    params={"per_page": 5}
)
for commit in commits_response.json():
    print(f"- {commit['commit']['message'].split('\n')[0]}")
```

### Weather API Example

```python
from api_client import RESTClient

weather_client = RESTClient(
    base_url="https://api.openweathermap.org/data/2.5",
    timeout=10
)

# Get current weather
response = weather_client.get("/weather", params={
    "q": "London",
    "appid": "your_api_key"
})

weather = response.json()
print(f"Temperature in London: {weather['main']['temp']}K")
```

### Pagination Handler

```python
from api_client import RESTClient

def fetch_all_pages(client: RESTClient, endpoint: str, per_page: int = 100):
    """Fetch all pages from a paginated API."""
    all_items = []
    page = 1

    while True:
        response = client.get(endpoint, params={
            "page": page,
            "per_page": per_page
        })

        items = response.json()
        if not items:  # No more pages
            break

        all_items.extend(items)
        page += 1

    return all_items

# Usage
client = RESTClient("https://api.example.com")
all_users = fetch_all_pages(client, "/users")
print(f"Total users: {len(all_users)}")
```

## Error Handling

See [Error Handling Guide](./docs/error-handling.md) for comprehensive error handling patterns.

## Testing

See [Testing Guide](./docs/testing.md) for testing strategies and examples.

## Related Documentation

- [Configuration Guide](./docs/configuration.md) - Advanced configuration options
- [Error Handling Guide](./docs/error-handling.md) - Error handling patterns
- [Testing Guide](./docs/testing.md) - Testing your API integrations
- [Usage Patterns](./docs/usage-patterns.md) - Common usage patterns and best practices

## Support

- **Issues**: Report bugs via GitHub Issues
- **Source**: [api-client module](./api_client.py)
- **Tests**: Run `python -m pytest tests/` to verify functionality
