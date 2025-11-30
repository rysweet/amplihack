# How to Use the REST API Client

This guide shows common patterns for using the amplihack REST API Client in real applications.

## Contents

- [Basic Usage](#basic-usage)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [File Uploads](#file-uploads)
- [Webhook Handling](#webhook-handling)
- [Testing](#testing)

## Basic Usage

### Simple GET Request

```python
from amplihack.api_client import APIClient

async def fetch_user(user_id: int):
    async with APIClient(base_url="https://api.example.com") as client:
        response = await client.get(f"/users/{user_id}")
        return response.data
```

### POST with JSON Body

```python
async def create_user(name: str, email: str):
    async with APIClient(base_url="https://api.example.com") as client:
        response = await client.post(
            "/users",
            json={"name": name, "email": email}
        )
        return response.data
```

### Type-Safe Responses

```python
from dataclasses import dataclass
from typing import List

@dataclass
class User:
    id: int
    name: str
    email: str

async def get_users() -> List[User]:
    async with APIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users", response_type=List[User])
        return response.data  # Type: List[User]
```

## Authentication

### Bearer Token

```python
async def create_authenticated_client(token: str):
    return APIClient(
        base_url="https://api.example.com",
        headers={"Authorization": f"Bearer {token}"}
    )

async def fetch_protected_data(token: str):
    async with create_authenticated_client(token) as client:
        response = await client.get("/protected/data")
        return response.data
```

### API Key Authentication

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-API-Key": "your-api-key"}
)
```

### OAuth2 Flow

```python
from amplihack.api_client import APIClient

class OAuth2Client:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.client = APIClient(base_url="https://oauth.example.com")

    async def authenticate(self):
        async with self.client:
            response = await self.client.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            self.token = response.data["access_token"]

    async def make_request(self, path: str):
        if not self.token:
            await self.authenticate()

        async with APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": f"Bearer {self.token}"}
        ) as client:
            return await client.get(path)
```

## Error Handling

### Basic Error Handling

```python
from amplihack.api_client import (
    APIClient,
    NetworkError,
    HTTPError,
    RateLimitError
)

async def safe_api_call():
    async with APIClient(base_url="https://api.example.com") as client:
        try:
            response = await client.get("/users")
            return response.data
        except NetworkError as e:
            print(f"Network error: {e}")
            return None
        except RateLimitError as e:
            print(f"Rate limited, retry after {e.retry_after} seconds")
            return None
        except HTTPError as e:
            if e.status_code == 404:
                print("Resource not found")
            else:
                print(f"HTTP {e.status_code}: {e.message}")
            return None
```

### Retry with Circuit Breaker

```python
from amplihack.api_client import APIClient, RetryConfig
import asyncio

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False

    async def call(self, func, *args, **kwargs):
        if self.is_open:
            if time.time() - self.last_failure_time > self.timeout:
                self.is_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.is_open = True
            raise

# Usage
breaker = CircuitBreaker()
client = APIClient(base_url="https://api.example.com")

async def protected_api_call():
    async with client:
        return await breaker.call(client.get, "/users")
```

## Pagination

### Cursor-Based Pagination

```python
async def fetch_all_users():
    users = []
    cursor = None

    async with APIClient(base_url="https://api.example.com") as client:
        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = await client.get("/users", params=params)
            data = response.data

            users.extend(data["users"])

            if not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]

    return users
```

### Page-Based Pagination

```python
async def fetch_paginated_data(total_pages: int = None):
    all_data = []
    page = 1

    async with APIClient(base_url="https://api.example.com") as client:
        while True:
            response = await client.get(
                "/items",
                params={"page": page, "per_page": 50}
            )

            data = response.data
            all_data.extend(data["items"])

            # Stop if we have all pages or no more data
            if not data["items"] or (total_pages and page >= total_pages):
                break

            page += 1

    return all_data
```

## File Uploads

### Single File Upload

```python
async def upload_file(file_path: str):
    async with APIClient(base_url="https://api.example.com") as client:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'application/octet-stream')}
            response = await client.post(
                "/upload",
                data=files
            )
        return response.data
```

### Multipart Form Data

```python
async def upload_with_metadata(file_path: str, metadata: dict):
    async with APIClient(base_url="https://api.example.com") as client:
        with open(file_path, 'rb') as f:
            data = {
                'file': (file_path, f, 'image/jpeg'),
                'title': metadata['title'],
                'description': metadata['description']
            }
            response = await client.post("/upload", data=data)
        return response.data
```

## Webhook Handling

### Webhook Receiver

```python
from fastapi import FastAPI, Request
from amplihack.api_client import APIClient

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    # Verify webhook signature
    signature = request.headers.get("X-Webhook-Signature")
    if not verify_signature(await request.body(), signature):
        return {"error": "Invalid signature"}, 401

    # Process webhook
    data = await request.json()

    # Make callback if needed
    async with APIClient(base_url="https://api.example.com") as client:
        await client.post(
            "/webhook/acknowledge",
            json={"id": data["id"], "status": "received"}
        )

    return {"status": "ok"}
```

## Testing

### Mock Responses

```python
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_user_fetch():
    mock_response = AsyncMock()
    mock_response.data = {"id": 1, "name": "Test User"}
    mock_response.status_code = 200

    with patch('amplihack.api_client.APIClient.get', return_value=mock_response):
        result = await fetch_user(1)
        assert result["name"] == "Test User"
```

### Integration Testing

```python
import pytest
from amplihack.api_client import APIClient

@pytest.mark.asyncio
async def test_real_api():
    async with APIClient(base_url="https://jsonplaceholder.typicode.com") as client:
        response = await client.get("/posts/1")
        assert response.status_code == 200
        assert response.data["id"] == 1
```

### Testing Error Scenarios

```python
from amplihack.api_client import APIClient, HTTPError

@pytest.mark.asyncio
async def test_404_handling():
    async with APIClient(base_url="https://api.example.com") as client:
        with pytest.raises(HTTPError) as exc_info:
            await client.get("/nonexistent")

        assert exc_info.value.status_code == 404
```

## Best Practices

### 1. Always Use Context Managers

```python
# Good
async with APIClient(base_url="https://api.example.com") as client:
    response = await client.get("/users")

# Bad - session won't be properly closed
client = APIClient(base_url="https://api.example.com")
response = await client.get("/users")
```

### 2. Configure Retry Appropriately

```python
from amplihack.api_client import RetryConfig

# For critical operations
critical_config = RetryConfig(
    max_retries=5,
    initial_delay=1.0,
    max_delay=60.0
)

# For non-critical operations
quick_config = RetryConfig(
    max_retries=1,
    initial_delay=0.5,
    max_delay=5.0
)
```

### 3. Handle Rate Limits Gracefully

```python
async def respectful_bulk_fetch(ids: List[int]):
    results = []

    async with APIClient(base_url="https://api.example.com") as client:
        for batch in chunks(ids, 10):  # Process in batches
            for id in batch:
                try:
                    response = await client.get(f"/items/{id}")
                    results.append(response.data)
                except RateLimitError as e:
                    # Wait for the specified time
                    await asyncio.sleep(e.retry_after or 60)
                    # Retry the request
                    response = await client.get(f"/items/{id}")
                    results.append(response.data)

            # Small delay between batches
            await asyncio.sleep(0.1)

    return results
```

## See Also

- [API Reference](../reference/api-client.md) - Complete API documentation
- [Configuration Guide](./api-client-config.md) - Detailed configuration options
- [Error Handling](../concepts/api-client-errors.md) - Understanding exceptions
