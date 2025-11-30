# Troubleshooting Guide

Common issues and solutions when using the REST API Client.

## Connection Issues

### Problem: "Connection refused" errors

**Symptoms:**

```python
NetworkError: Connection refused to api.example.com:443
```

**Possible Causes:**

1. Server is down
2. Wrong base URL or port
3. Firewall blocking connection
4. Proxy configuration needed

**Solutions:**

Check if the server is accessible:

```bash
# Test connectivity
curl -I https://api.example.com
ping api.example.com
```

Verify base URL:

```python
# Make sure URL is correct
client = APIClient(base_url="https://api.example.com")  # Not "http://"
```

Configure proxy if needed:

```python
client = APIClient(
    base_url="https://api.example.com",
    proxy="http://proxy.company.com:8080",
    proxy_auth=("username", "password")
)
```

### Problem: SSL/TLS certificate errors

**Symptoms:**

```python
NetworkError: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**

For self-signed certificates (development only):

```python
# WARNING: Only for development/testing
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=False
)
```

Use custom CA bundle:

```python
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl="/path/to/ca-bundle.crt"
)
```

## Authentication Issues

### Problem: Getting 401 Unauthorized

**Symptoms:**

```python
AuthenticationError: Authentication required (401)
```

**Solutions:**

Check token format:

```python
# Bearer token
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"}  # Note: "Bearer " prefix
)

# API key in header
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-API-Key": "YOUR_API_KEY"}
)
```

Handle token expiration:

```python
from rest_api_client.exceptions import AuthenticationError

def make_request_with_refresh():
    try:
        return client.get("/data")
    except AuthenticationError:
        # Refresh token
        new_token = refresh_auth_token()
        client.headers["Authorization"] = f"Bearer {new_token}"
        return client.get("/data")
```

### Problem: Getting 403 Forbidden

**Symptoms:**

```python
AuthorizationError: Insufficient permissions (403)
```

**Solutions:**

Verify permissions:

```python
try:
    response = client.delete("/admin/resource")
except AuthorizationError as e:
    print(f"Missing permission: {e.required_permission}")
    print(f"Your permissions: {e.user_permissions}")
```

Use correct API scope:

```python
# Request correct OAuth scopes
auth_url = "https://auth.example.com/oauth/authorize?scope=read+write+admin"
```

## Rate Limiting Issues

### Problem: Getting 429 Too Many Requests

**Symptoms:**

```python
RateLimitError: Rate limit exceeded (429)
```

**Solutions:**

Configure rate limiting:

```python
# Set conservative rate limits
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=10,  # 10 calls
    rate_limit_period=60   # per minute
)
```

Handle rate limit errors:

```python
import time
from rest_api_client.exceptions import RateLimitError

try:
    response = client.get("/data")
except RateLimitError as e:
    print(f"Rate limited. Waiting {e.retry_after} seconds")
    time.sleep(e.retry_after)
    response = client.get("/data")  # Retry
```

Batch requests efficiently:

```python
# Instead of many individual requests
for user_id in range(100):
    client.get(f"/users/{user_id}")  # May hit rate limit

# Use batch endpoints when available
response = client.get("/users", params={"ids": ",".join(map(str, range(100)))})
```

## Timeout Issues

### Problem: Requests timing out

**Symptoms:**

```python
TimeoutError: Request timeout after 30 seconds
```

**Solutions:**

Increase timeout for slow endpoints:

```python
# Global timeout
client = APIClient(
    base_url="https://api.example.com",
    timeout=120  # 2 minutes
)

# Per-request timeout
response = client.get("/slow-endpoint", timeout=300)  # 5 minutes
```

Use async for long operations:

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def fetch_with_timeout():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        try:
            response = await asyncio.wait_for(
                client.get("/very-slow-endpoint"),
                timeout=60.0
            )
            return response
        except asyncio.TimeoutError:
            print("Operation timed out")
            return None
```

## Data Issues

### Problem: JSON parsing errors

**Symptoms:**

```python
ValueError: Invalid JSON in response
```

**Solutions:**

Check response content type:

```python
response = client.get("/data")
print(f"Content-Type: {response.headers.get('Content-Type')}")

# Handle non-JSON responses
if "application/json" not in response.headers.get("Content-Type", ""):
    # Response is not JSON
    text_data = response.text
else:
    json_data = response.data
```

Debug raw response:

```python
# Get raw response for debugging
try:
    response = client.get("/data")
except Exception as e:
    # Check raw response if available
    if hasattr(e, 'response') and e.response:
        print(f"Raw response: {e.response.text}")
```

### Problem: Encoding issues

**Symptoms:**

```python
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solutions:**

Specify encoding:

```python
response = client.get("/data")
# Force encoding
text = response.text.encode('latin-1').decode('utf-8')
```

Handle binary data:

```python
# For binary data (images, PDFs, etc.)
response = client.get("/download/file.pdf")
with open("file.pdf", "wb") as f:
    f.write(response.content)  # Binary content
```

## Performance Issues

### Problem: Slow response times

**Solutions:**

Enable connection pooling:

```python
# Reuse client instance
client = APIClient(base_url="https://api.example.com")

# Good - reuses connection
for i in range(100):
    client.get(f"/item/{i}")

# Bad - creates new connection each time
for i in range(100):
    new_client = APIClient(base_url="https://api.example.com")
    new_client.get(f"/item/{i}")
```

Use compression:

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"Accept-Encoding": "gzip, deflate"}
)
```

### Problem: High memory usage

**Solutions:**

Stream large responses:

```python
# For large datasets, process in chunks
def process_large_dataset():
    page = 1
    while True:
        response = client.get("/data", params={"page": page, "size": 100})

        # Process chunk
        for item in response.data:
            process_item(item)

        if page >= response.data.get("total_pages", 1):
            break
        page += 1
```

Clean up resources:

```python
# Use context manager for automatic cleanup
with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/data")
    # Client is automatically closed
```

## Retry Issues

### Problem: Retries not working as expected

**Solutions:**

Configure retry properly:

```python
from rest_api_client.config import RetryConfig

retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    exponential_base=2.0,
    retry_on_statuses=[429, 500, 502, 503, 504],
    retry_on_exceptions=[NetworkError, TimeoutError]
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

Debug retry behavior:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Will show retry attempts in logs
response = client.get("/flaky-endpoint")
```

### Problem: Too many retries

**Solutions:**

Limit retry attempts:

```python
# Disable retries for certain operations
client = APIClient(
    base_url="https://api.example.com",
    max_retries=0  # No retries
)

# Or limit to specific status codes
retry_config = RetryConfig(
    max_attempts=2,
    retry_on_statuses=[503]  # Only retry on service unavailable
)
```

## Debugging Tips

### Enable verbose logging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Will show detailed request/response info
client = APIClient(base_url="https://api.example.com")
response = client.get("/debug")
```

### Inspect request details

```python
# Prepare request without sending
request = client.prepare_request("GET", "/users")
print(f"URL: {request.url}")
print(f"Headers: {request.headers}")
print(f"Method: {request.method}")

# Then send if looks correct
response = client.send(request)
```

### Use debugging proxy

```python
# Route through debugging proxy like Charles or Fiddler
client = APIClient(
    base_url="https://api.example.com",
    proxy="http://localhost:8888",
    verify_ssl=False  # Proxy uses self-signed cert
)
```

### Capture full exception details

```python
from rest_api_client.exceptions import APIError

try:
    response = client.get("/endpoint")
except APIError as e:
    print(f"Error Type: {type(e).__name__}")
    print(f"Message: {e.message}")
    print(f"Status Code: {e.status_code}")

    if e.response:
        print(f"Response Headers: {e.response.headers}")
        print(f"Response Body: {e.response.text}")

    if e.request:
        print(f"Request Method: {e.request.method}")
        print(f"Request URL: {e.request.url}")
```

## Common Mistakes

### Mistake 1: Not reusing client instance

```python
# Bad - creates new client for each request
def get_user(user_id):
    client = APIClient(base_url="https://api.example.com")
    return client.get(f"/users/{user_id}")

# Good - reuse client
CLIENT = APIClient(base_url="https://api.example.com")

def get_user(user_id):
    return CLIENT.get(f"/users/{user_id}")
```

### Mistake 2: Not handling specific exceptions

```python
# Bad - catches all exceptions
try:
    response = client.get("/data")
except Exception:
    print("Something went wrong")

# Good - handle specific exceptions
try:
    response = client.get("/data")
except NetworkError:
    handle_network_error()
except AuthenticationError:
    refresh_token()
except RateLimitError as e:
    wait_and_retry(e.retry_after)
```

### Mistake 3: Hardcoding configuration

```python
# Bad - hardcoded values
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer abc123"}
)

# Good - use environment variables
import os

client = APIClient(
    base_url=os.environ.get("API_BASE_URL", "https://api.example.com"),
    headers={"Authorization": f"Bearer {os.environ['API_TOKEN']}"}
)
```

## Getting Further Help

If you're still experiencing issues:

1. **Check the logs** - Enable debug logging to see full request/response details
2. **Isolate the problem** - Try the same request with curl or Postman
3. **Review the documentation** - Check the API documentation for the endpoint
4. **File an issue** - Include:
   - Full error message and stack trace
   - Minimal code to reproduce
   - Library version (`pip show rest_api_client`)
   - Python version
   - Operating system
