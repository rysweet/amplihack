# API Client

A simple, minimal HTTP client for JSON APIs following the Brick Philosophy.

## Overview

**Problem**: Agents and tools need to make HTTP requests to external APIs, but raw `requests` code is repetitive and error handling is inconsistent.

**Solution**: A self-contained API client module that handles JSON serialization, authentication, and error handling with a clean, minimal interface.

**Key Benefits**:

- Single file, no complex dependencies
- Clear error messages with status codes
- Support for common auth patterns (Bearer, API key)
- Configurable timeout with sensible defaults

## Quick Start

```python
from api_client import APIClient, APIError, AuthType

# Create client
client = APIClient("https://api.example.com")

# Make requests
users = client.get("/users")
new_user = client.post("/users", data={"name": "Alice"})
```

## Installation

Copy `api_client.py` to your project or import directly:

```python
from .claude.scenarios.api_client.api_client import APIClient
```

**Dependencies**: `requests` library only.

## API Reference

### AuthType

Enum for authentication methods:

```python
class AuthType(Enum):
    NONE = "none"      # No authentication
    BEARER = "bearer"  # Bearer token in Authorization header
    API_KEY = "api_key"  # API key in custom header  # pragma: allowlist secret
```

### APIClient

Main client class for HTTP operations.

#### Constructor

```python
APIClient(
    base_url: str,
    auth_type: AuthType = AuthType.NONE,
    auth_token: Optional[str] = None,
    api_key_header: str = "X-API-Key",
    timeout: int = 30,
)
```

| Parameter        | Type     | Default     | Description                            |
| ---------------- | -------- | ----------- | -------------------------------------- |
| `base_url`       | str      | required    | Base URL for all requests              |
| `auth_type`      | AuthType | NONE        | Authentication method                  |
| `auth_token`     | str      | None        | Token for Bearer auth or API key value |
| `api_key_header` | str      | "X-API-Key" | Header name for API key auth           |
| `timeout`        | int      | 30          | Request timeout in seconds             |

#### Methods

**get(path, params=None) -> dict**

```python
# Simple GET
users = client.get("/users")

# GET with query parameters
user = client.get("/users", params={"id": 123})
```

**post(path, data=None) -> dict**

```python
# POST with JSON body
result = client.post("/users", data={"name": "Alice", "email": "alice@example.com"})
```

**put(path, data=None) -> dict**

```python
# PUT to update resource
result = client.put("/users/123", data={"name": "Alice Updated"})
```

**delete(path) -> dict**

```python
# DELETE resource
result = client.delete("/users/123")
```

### APIError

Exception raised for HTTP errors.

```python
class APIError(Exception):
    status_code: int      # HTTP status code (0 for non-HTTP errors like connection/timeout)
    message: str          # Error description
    response_body: str    # Raw response body (if available)
```

**Usage**:

```python
try:
    result = client.get("/protected")
except APIError as e:
    print(f"Error {e.status_code}: {e.message}")
    if e.response_body:
        print(f"Details: {e.response_body}")
```

## Authentication Examples

### No Authentication

```python
client = APIClient("https://api.publicapis.org")
data = client.get("/entries")
```

### Bearer Token (JWT, OAuth)

```python
client = APIClient(
    base_url="https://api.example.com",
    auth_type=AuthType.BEARER,
    auth_token="eyJhbGciOiJIUzI1NiIs..."
)
# Adds: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### API Key

```python
# Default header (X-API-Key)
client = APIClient(
    base_url="https://api.example.com",
    auth_type=AuthType.API_KEY,
    auth_token="your-api-key-here"
)
# Adds: X-API-Key: your-api-key-here

# Custom header name
client = APIClient(
    base_url="https://api.example.com",
    auth_type=AuthType.API_KEY,
    auth_token="your-api-key-here",
    api_key_header="Authorization"  # pragma: allowlist secret
)
# Adds: Authorization: your-api-key-here
```

## Error Handling

### HTTP Status Codes

```python
try:
    result = client.get("/resource")
except APIError as e:
    if e.status_code == 401:
        print("Authentication failed - check your token")
    elif e.status_code == 404:
        print("Resource not found")
    elif e.status_code >= 500:
        print("Server error - try again later")
    else:
        print(f"Request failed: {e}")
```

### Special Status Codes

| Code | Meaning        | Cause                                               |
| ---- | -------------- | --------------------------------------------------- |
| 0    | Non-HTTP Error | Connection error, timeout, or other request failure |

```python
try:
    result = client.get("/slow-endpoint")
except APIError as e:
    if e.status_code == 0:
        # Non-HTTP error - check message for details
        if "timeout" in e.message.lower():
            print("Request timed out - server too slow")
        else:
            print("Cannot connect - check network/URL")
```

## Troubleshooting

| Problem                         | Cause                    | Solution                         |
| ------------------------------- | ------------------------ | -------------------------------- |
| `APIError: HTTP 401`            | Invalid or expired token | Refresh your auth token          |
| `APIError: HTTP 0` (connection) | Network/DNS issue        | Check URL and network connection |
| `APIError: HTTP 0` (timeout)    | Slow server              | Increase timeout parameter       |
| `JSONDecodeError`               | Non-JSON response        | API returned HTML or text        |

## Security Considerations

- **Never hardcode tokens**: Use environment variables
- **Use HTTPS**: Always use `https://` base URLs
- **Rotate tokens**: Implement token refresh for long-running processes
- **Handle errors gracefully**: Don't expose error details to end users

## Module Structure

```
.claude/scenarios/api-client/
├── README.md                    # This file
├── HOW_TO_CREATE_YOUR_OWN.md   # Template guide
├── api_client.py               # Main implementation
├── tests/
│   └── test_api_client.py      # Unit tests
└── examples/
    └── usage_example.py        # Working examples
```

## Philosophy Alignment

This module follows amplihack's core principles:

- **Ruthless Simplicity**: Single file, minimal API surface
- **Brick Philosophy**: Self-contained, single responsibility
- **Zero-BS**: No stubs, no TODOs, everything works
- **Regeneratable**: Can be rebuilt from this specification
