# Error Handling Guide

Comprehensive guide for handling errors when using the REST API Client.

## Contents

- [Error Types](#error-types)
- [HTTP Status Codes](#http-status-codes)
- [Exception Handling](#exception-handling)
- [Retry Logic](#retry-logic)
- [Error Recovery Strategies](#error-recovery-strategies)
- [Logging and Monitoring](#logging-and-monitoring)
- [Common Error Patterns](#common-error-patterns)
- [Best Practices](#best-practices)

## Error Types

### Network Errors

Connection-level errors that prevent requests from reaching the server:

```python
from api_client import RESTClient
import urllib.error

def handle_network_errors(client: RESTClient, path: str):
    """Handle various network-related errors."""
    try:
        response = client.get(path)
        return response.json()

    except urllib.error.URLError as e:
        # Network is unreachable
        print(f"Network error: {e.reason}")
        return None

    except TimeoutError:
        # Request timed out
        print(f"Request timed out for {path}")
        return None

    except ConnectionError:
        # Connection refused or reset
        print(f"Connection failed to {client.base_url}")
        return None

# Usage
client = RESTClient("https://api.example.com")
data = handle_network_errors(client, "/users")
```

### HTTP Errors

Server responses indicating request problems:

```python
def handle_http_status(response):
    """Handle different HTTP status codes."""
    if response.status_code == 200:
        return response.json()

    elif response.status_code == 400:
        error = response.json()
        print(f"Bad Request: {error.get('message', 'Invalid input')}")
        return None

    elif response.status_code == 401:
        print("Unauthorized: Check your authentication credentials")
        return None

    elif response.status_code == 403:
        print("Forbidden: You don't have permission for this resource")
        return None

    elif response.status_code == 404:
        print("Not Found: The requested resource doesn't exist")
        return None

    elif response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        print(f"Rate Limited: Retry after {retry_after} seconds")
        return None

    elif 500 <= response.status_code < 600:
        print(f"Server Error ({response.status_code}): Try again later")
        return None

    else:
        print(f"Unexpected status: {response.status_code}")
        return None
```

### Parsing Errors

Errors when processing response data:

```python
import json

def safe_json_parse(response):
    """Safely parse JSON response with error handling."""
    try:
        return response.json()

    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}")
        # Try to get raw text for debugging
        try:
            text = response.body.decode('utf-8')
            print(f"Raw response: {text[:200]}...")
        except:
            pass
        return None

    except UnicodeDecodeError as e:
        print(f"Encoding error: {e}")
        return None

# Usage
response = client.get("/data")
data = safe_json_parse(response)
if data:
    process_data(data)
```

## HTTP Status Codes

### Status Code Reference

| Code | Meaning               | Action                        |
| ---- | --------------------- | ----------------------------- |
| 200  | OK                    | Process response              |
| 201  | Created               | Resource created successfully |
| 204  | No Content            | Success with no response body |
| 400  | Bad Request           | Fix request parameters        |
| 401  | Unauthorized          | Check authentication          |
| 403  | Forbidden             | Check permissions             |
| 404  | Not Found             | Verify endpoint/resource      |
| 429  | Too Many Requests     | Implement rate limiting       |
| 500  | Internal Server Error | Retry with backoff            |
| 502  | Bad Gateway           | Retry with backoff            |
| 503  | Service Unavailable   | Check service status          |
| 504  | Gateway Timeout       | Increase timeout, retry       |

### Handling Status Code Groups

```python
def handle_response(response):
    """Handle response based on status code groups."""
    status = response.status_code

    # Success (2xx)
    if 200 <= status < 300:
        return {"success": True, "data": response.json()}

    # Redirection (3xx)
    elif 300 <= status < 400:
        new_location = response.headers.get("Location")
        return {"redirect": True, "location": new_location}

    # Client Error (4xx)
    elif 400 <= status < 500:
        return {"error": "client", "status": status,
                "message": f"Client error: {status}"}

    # Server Error (5xx)
    elif 500 <= status < 600:
        return {"error": "server", "status": status,
                "message": f"Server error: {status}",
                "retry": True}

    else:
        return {"error": "unknown", "status": status}
```

## Exception Handling

### Comprehensive Error Wrapper

```python
from api_client import RESTClient
from typing import Optional, Dict, Any
import traceback

class SafeAPIClient:
    """Wrapper for RESTClient with comprehensive error handling."""

    def __init__(self, base_url: str):
        self.client = RESTClient(base_url)
        self.last_error = None

    def safe_request(self, method: str, path: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Make request with full error handling."""
        self.last_error = None

        try:
            # Make the request
            response = getattr(self.client, method)(path, **kwargs)

            # Check status
            if response.status_code >= 400:
                self.last_error = {
                    "type": "http_error",
                    "status": response.status_code,
                    "message": f"HTTP {response.status_code}"
                }
                return None

            # Parse response
            return response.json()

        except TimeoutError as e:
            self.last_error = {
                "type": "timeout",
                "message": "Request timed out",
                "path": path
            }
            return None

        except ConnectionError as e:
            self.last_error = {
                "type": "connection",
                "message": str(e),
                "path": path
            }
            return None

        except json.JSONDecodeError as e:
            self.last_error = {
                "type": "parse_error",
                "message": f"Invalid JSON: {e}",
                "path": path
            }
            return None

        except Exception as e:
            self.last_error = {
                "type": "unknown",
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            return None

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """Get details of the last error."""
        return self.last_error

# Usage
safe_client = SafeAPIClient("https://api.example.com")
data = safe_client.safe_request("get", "/users")

if data is None:
    error = safe_client.get_last_error()
    print(f"Request failed: {error['type']} - {error['message']}")
```

### Context Manager for Error Handling

```python
from contextlib import contextmanager
import logging

@contextmanager
def api_error_handler(operation: str):
    """Context manager for handling API errors."""
    try:
        logging.info(f"Starting: {operation}")
        yield
        logging.info(f"Completed: {operation}")

    except TimeoutError:
        logging.error(f"Timeout during: {operation}")
        raise

    except ConnectionError as e:
        logging.error(f"Connection error during {operation}: {e}")
        raise

    except Exception as e:
        logging.error(f"Unexpected error during {operation}: {e}")
        raise

# Usage
client = RESTClient("https://api.example.com")

with api_error_handler("fetch user data"):
    response = client.get("/users/123")
    user = response.json()
```

## Retry Logic

### Smart Retry with Backoff

```python
import time
import random
from typing import Optional, Callable

def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Optional[Any]:
    """Retry function with exponential backoff and jitter."""
    delay = initial_delay

    for attempt in range(max_attempts):
        try:
            return func()

        except Exception as e:
            if attempt == max_attempts - 1:
                # Last attempt failed
                raise

            # Calculate delay with jitter
            if jitter:
                actual_delay = delay * (0.5 + random.random())
            else:
                actual_delay = delay

            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {actual_delay:.2f} seconds...")
            time.sleep(actual_delay)

            # Increase delay exponentially
            delay = min(delay * exponential_base, max_delay)

    return None

# Usage
client = RESTClient("https://api.example.com")

def fetch_data():
    response = client.get("/unstable-endpoint")
    return response.json()

try:
    data = retry_with_backoff(fetch_data, max_attempts=5)
    print(f"Success: {data}")
except Exception as e:
    print(f"Failed after all retries: {e}")
```

### Conditional Retry

```python
def should_retry(error: Exception, response: Optional[Response] = None) -> bool:
    """Determine if error is retryable."""
    # Network errors - usually retryable
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    # Check HTTP status if we have a response
    if response:
        # Retry on server errors and rate limiting
        if response.status_code in {429, 500, 502, 503, 504}:
            return True

        # Don't retry client errors
        if 400 <= response.status_code < 500:
            return False

    # Don't retry parsing errors
    if isinstance(error, json.JSONDecodeError):
        return False

    # Default: don't retry unknown errors
    return False

def resilient_request(client: RESTClient, method: str, path: str,
                       max_retries: int = 3, **kwargs):
    """Make request with smart retry logic."""
    last_error = None
    response = None

    for attempt in range(max_retries + 1):
        try:
            response = getattr(client, method)(path, **kwargs)

            if response.status_code < 400:
                return response

            # Check if we should retry this status
            if not should_retry(None, response):
                return response

        except Exception as e:
            last_error = e
            if not should_retry(e):
                raise

        if attempt < max_retries:
            wait_time = 2 ** attempt
            print(f"Retrying after {wait_time} seconds...")
            time.sleep(wait_time)

    # All retries exhausted
    if last_error:
        raise last_error
    return response
```

## Error Recovery Strategies

### Fallback Mechanism

```python
from typing import List, Optional

class FallbackClient:
    """Client with fallback URLs for resilience."""

    def __init__(self, urls: List[str]):
        self.urls = urls
        self.current_index = 0
        self.clients = [RESTClient(url) for url in urls]

    def get_with_fallback(self, path: str) -> Optional[Response]:
        """Try primary URL, fallback to secondaries if needed."""
        errors = []

        for i, client in enumerate(self.clients):
            try:
                response = client.get(path)
                if response.status_code < 500:
                    # Success or client error - don't fallback
                    return response

            except Exception as e:
                errors.append(f"{self.urls[i]}: {e}")
                continue

        # All URLs failed
        print("All endpoints failed:")
        for error in errors:
            print(f"  - {error}")
        return None

# Usage
fallback_client = FallbackClient([
    "https://api.example.com",
    "https://api-backup.example.com",
    "https://api-secondary.example.com"
])

response = fallback_client.get_with_fallback("/critical-data")
```

### Cache Fallback

```python
import pickle
from pathlib import Path
from datetime import datetime, timedelta

class CachedClient(RESTClient):
    """Client with cache fallback for resilience."""

    def __init__(self, base_url: str, cache_dir: str = ".api_cache"):
        super().__init__(base_url)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_with_cache(self, path: str, cache_hours: int = 24):
        """Get data with cache fallback."""
        cache_file = self.cache_dir / f"{path.replace('/', '_')}.cache"

        try:
            # Try to get fresh data
            response = self.get(path)
            if response.status_code == 200:
                # Cache successful response
                data = response.json()
                cache_entry = {
                    "data": data,
                    "timestamp": datetime.now(),
                    "path": path
                }
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_entry, f)
                return data

        except Exception as e:
            print(f"API call failed: {e}")

            # Fallback to cache if available
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cache_entry = pickle.load(f)

                    age = datetime.now() - cache_entry["timestamp"]
                    if age < timedelta(hours=cache_hours):
                        print(f"Using cached data ({age.total_seconds():.0f}s old)")
                        return cache_entry["data"]
                    else:
                        print(f"Cache too old ({age.total_seconds():.0f}s)")

                except Exception as cache_error:
                    print(f"Cache read failed: {cache_error}")

        return None
```

## Logging and Monitoring

### Structured Error Logging

```python
import logging
import json
from datetime import datetime

class LoggingClient(RESTClient):
    """Client with structured error logging."""

    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.logger = logging.getLogger(__name__)
        self.error_count = {}

    def request(self, method: str, path: str, **kwargs):
        """Make request with error logging."""
        start_time = datetime.now()

        try:
            response = super().request(method, path, **kwargs)

            # Log successful requests
            self.logger.info(json.dumps({
                "event": "api_request",
                "method": method,
                "path": path,
                "status": response.status_code,
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }))

            # Track error rates
            if response.status_code >= 400:
                self.track_error(path, response.status_code)

            return response

        except Exception as e:
            # Log failed requests
            self.logger.error(json.dumps({
                "event": "api_error",
                "method": method,
                "path": path,
                "error": str(e),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
            }))
            self.track_error(path, "exception")
            raise

    def track_error(self, path: str, error_type):
        """Track error counts for monitoring."""
        key = f"{path}:{error_type}"
        self.error_count[key] = self.error_count.get(key, 0) + 1

        # Alert if error rate is high
        if self.error_count[key] > 10:
            self.logger.warning(f"High error rate for {key}: {self.error_count[key]}")

    def get_error_stats(self) -> dict:
        """Get error statistics."""
        return dict(self.error_count)
```

## Common Error Patterns

### Authentication Errors

```python
class AuthClient(RESTClient):
    """Client with authentication error handling."""

    def __init__(self, base_url: str, auth_token: str):
        super().__init__(base_url)
        self.auth_token = auth_token
        self.refresh_token = None

    def handle_auth_error(self, response):
        """Handle authentication errors."""
        if response.status_code == 401:
            # Try to refresh token
            if self.refresh_token:
                new_token = self.refresh_auth_token()
                if new_token:
                    self.auth_token = new_token
                    return True
            raise AuthenticationError("Authentication failed")
        return False

    def refresh_auth_token(self) -> Optional[str]:
        """Refresh authentication token."""
        try:
            response = self.post("/auth/refresh",
                                 json={"refresh_token": self.refresh_token})
            if response.status_code == 200:
                return response.json()["access_token"]
        except:
            pass
        return None
```

### Rate Limiting Errors

```python
import time

def handle_rate_limit(response) -> bool:
    """Handle rate limit response."""
    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")

        if retry_after:
            # Could be seconds or HTTP date
            try:
                wait_seconds = int(retry_after)
            except ValueError:
                # Try parsing as date
                from email.utils import parsedate_to_datetime
                retry_date = parsedate_to_datetime(retry_after)
                wait_seconds = (retry_date - datetime.now()).total_seconds()

            print(f"Rate limited. Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            return True

        # No Retry-After header, use exponential backoff
        print("Rate limited. Using default 60 second wait...")
        time.sleep(60)
        return True

    return False
```

## Best Practices

1. **Always handle network errors** - Networks are unreliable
2. **Implement retry logic** - But know when to give up
3. **Use exponential backoff** - Prevent thundering herd
4. **Log errors with context** - Include request details
5. **Monitor error rates** - Detect problems early
6. **Provide fallbacks** - Cache, default values, or alternate endpoints
7. **Fail fast in development** - But gracefully in production
8. **Test error scenarios** - Simulate failures in tests
9. **Document error behavior** - Users need to know what to expect
10. **Use structured logging** - Makes analysis easier
