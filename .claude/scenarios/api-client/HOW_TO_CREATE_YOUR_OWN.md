# How to Create Your Own API Client

This guide shows you how to create a custom API client module for a specific service, following the same patterns used in the base `api_client.py`.

## Overview

Use this template when you need to:

- Wrap a specific API (GitHub, Stripe, OpenAI, etc.)
- Add service-specific methods and error handling
- Customize authentication for a particular service

## Architecture

```
your-api-client/
├── README.md                    # Document your client
├── your_client.py              # Single file implementation
├── tests/
│   └── test_your_client.py     # Unit tests
└── examples/
    └── usage_example.py        # Working examples
```

## Step-by-Step Guide

### Step 1: Define Your Purpose

Answer these questions:

- What API are you wrapping?
- What operations do users need most?
- What authentication does it use?

### Step 2: Create Directory Structure

```bash
mkdir -p .claude/scenarios/your-api-client/{tests,examples}
cd .claude/scenarios/your-api-client
touch your_client.py README.md tests/test_your_client.py
```

### Step 3: Implement the Client

Use this template:

```python
"""Your API Client - Brief description.

Philosophy:
- Single responsibility: [what it does]
- Standard library + requests only
- Self-contained and regeneratable

Public API:
    YourClient: Main client class
    YourAPIError: Service-specific exception
"""

from enum import Enum
from typing import Any, Dict, Optional
import requests

__all__ = ["YourClient", "YourAPIError"]


class YourAPIError(Exception):
    """Raised when API request fails."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Optional[str] = None
    ):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"HTTP {status_code}: {message}")


class YourClient:
    """Client for Your API Service."""

    BASE_URL = "https://api.yourservice.com/v1"

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
    ):
        """
        Initialize client.

        Args:
            api_key: Your API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request with error handling."""
        url = f"{self.BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=self.timeout,
            )
        except requests.ConnectionError as e:
            raise YourAPIError(0, f"Connection failed: {e}")
        except requests.Timeout:
            raise YourAPIError(0, f"Request timed out after {self.timeout}s")

        if not response.ok:
            raise YourAPIError(
                response.status_code,
                response.reason,
                response.text,
            )

        try:
            return response.json()
        except ValueError:
            raise YourAPIError(
                response.status_code,
                "Invalid JSON response",
                response.text,
            )

    # Add your service-specific methods here

    def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """Get a resource by ID."""
        return self._request("GET", f"/resources/{resource_id}")

    def create_resource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new resource."""
        return self._request("POST", "/resources", data=data)

    def list_resources(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List resources with pagination."""
        return self._request("GET", "/resources", params={"page": page, "limit": limit})
```

### Step 4: Write Tests

```python
"""Tests for your_client.py"""

import pytest
from unittest.mock import patch, Mock
from your_client import YourClient, YourAPIError


class TestYourClient:
    """Unit tests for YourClient."""

    def test_get_resource_success(self):
        """GET returns parsed JSON."""
        client = YourClient(api_key="test-key")

        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "123", "name": "Test"}
            mock_request.return_value = mock_response

            result = client.get_resource("123")

            assert result["id"] == "123"

    def test_authentication_header(self):
        """API key is sent in Authorization header."""
        client = YourClient(api_key="my-secret-key")

        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {}
            mock_request.return_value = mock_response

            client.get_resource("123")

            call_kwargs = mock_request.call_args[1]
            assert "Bearer my-secret-key" in call_kwargs["headers"]["Authorization"]

    def test_404_raises_error(self):
        """404 response raises YourAPIError."""
        client = YourClient(api_key="test-key")

        with patch("requests.request") as mock_request:
            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 404
            mock_response.reason = "Not Found"
            mock_response.text = '{"error": "Resource not found"}'
            mock_request.return_value = mock_response

            with pytest.raises(YourAPIError) as exc_info:
                client.get_resource("nonexistent")

            assert exc_info.value.status_code == 404
```

### Step 5: Create Usage Example

```python
"""Example usage of YourClient."""

from your_client import YourClient, YourAPIError

def main():
    # Initialize client
    client = YourClient(api_key="your-api-key-here")

    # List resources
    resources = client.list_resources(page=1, limit=10)
    print(f"Found {len(resources['items'])} resources")

    # Get specific resource
    try:
        resource = client.get_resource("abc123")
        print(f"Resource: {resource['name']}")
    except YourAPIError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### Step 6: Write README

Document your client with:

- Purpose and what API it wraps
- Installation instructions
- Quick start example
- API reference for all methods
- Error handling guide
- Authentication setup

### Step 7: Add Makefile Target

In the project root Makefile:

```makefile
your-client-example:
	@python .claude/scenarios/your-api-client/examples/usage_example.py
```

### Step 8: Graduate to Production

Ensure your client meets the graduation criteria:

- [ ] 2-3 successful real-world uses
- [ ] Complete README.md
- [ ] HOW_TO_CREATE_YOUR_OWN.md (if useful for others)
- [ ] Test suite with good coverage
- [ ] Makefile integration

## Customization Points

### Adding Rate Limiting

```python
import time

class YourClient:
    def __init__(self, api_key: str, requests_per_minute: int = 60):
        self.min_interval = 60.0 / requests_per_minute
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.time()

    def _request(self, method, path, **kwargs):
        self._rate_limit()
        # ... rest of request logic
```

### Adding Retry Logic

```python
import time

class YourClient:
    def _request_with_retry(self, method, path, max_retries=3, **kwargs):
        for attempt in range(max_retries):
            try:
                return self._request(method, path, **kwargs)
            except YourAPIError as e:
                if e.status_code >= 500 and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
```

### Adding Pagination Helper

```python
class YourClient:
    def list_all_resources(self, **kwargs):
        """Iterate through all pages of resources."""
        page = 1
        while True:
            result = self.list_resources(page=page, **kwargs)
            yield from result["items"]
            if page >= result["total_pages"]:
                break
            page += 1
```

## Best Practices

1. **Keep it simple**: Start with minimal features, add complexity only when needed
2. **Single file**: One module file unless absolutely necessary
3. **Clear errors**: Include status code, message, and response body
4. **Document everything**: Every public method needs a docstring
5. **Test with mocks**: Don't hit real APIs in unit tests
6. **Use type hints**: Help IDE completion and catch errors

## Related Resources

- Base API Client: `api_client.py`
- Scenario Pattern Guide: `.claude/scenarios/README.md`
- Testing Patterns: `.claude/context/PATTERNS.md`
