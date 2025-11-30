# Architecture Overview

Understanding the design principles and internal architecture of the REST API Client.

## Design Principles

### Zero Dependencies

The REST API Client uses only Python's standard library, ensuring:

- **No dependency conflicts** - Works in any Python environment
- **Lightweight deployment** - No package management overhead
- **Maximum compatibility** - Runs anywhere Python runs
- **Security** - No third-party vulnerability surface

### Modular Design

Following the brick philosophy, each component has a single responsibility:

```
APIClient (orchestrator)
├── RequestBuilder    # Constructs HTTP requests
├── ResponseParser    # Parses HTTP responses
├── RetryManager      # Handles retry logic
├── RateLimiter       # Enforces rate limits
├── ErrorHandler      # Maps errors to exceptions
└── Logger            # Sanitized logging
```

### Separation of Concerns

Each module handles one aspect:

- **APIClient**: Public API and orchestration
- **RequestBuilder**: Request construction and validation
- **ResponseParser**: Response parsing and type conversion
- **RetryManager**: Retry logic and backoff calculations
- **RateLimiter**: Token bucket implementation
- **ErrorHandler**: Exception mapping and context
- **Logger**: Security-aware logging

## Core Components

### APIClient Class

The main orchestrator that coordinates all components:

```python
class APIClient:
    def __init__(self, base_url, **config):
        self.base_url = base_url
        self.request_builder = RequestBuilder(base_url)
        self.response_parser = ResponseParser()
        self.retry_manager = RetryManager(config.get("retry_config"))
        self.rate_limiter = RateLimiter(config.get("rate_limit_config"))
        self.error_handler = ErrorHandler()
        self.logger = Logger(config.get("log_level"))

    def get(self, path, **kwargs):
        return self._execute("GET", path, **kwargs)

    def _execute(self, method, path, **kwargs):
        # Rate limiting
        self.rate_limiter.acquire()

        # Build request
        request = self.request_builder.build(method, path, **kwargs)

        # Execute with retries
        raw_response = self.retry_manager.execute(request)

        # Parse response
        response = self.response_parser.parse(raw_response)

        # Check for errors
        self.error_handler.check(response)

        return response
```

### Request/Response Flow

```
User Code
    │
    ▼
APIClient.get("/users")
    │
    ├─► RateLimiter.acquire()
    │       │
    │       └─► Check token bucket
    │
    ├─► RequestBuilder.build()
    │       │
    │       ├─► Validate parameters
    │       ├─► Construct URL
    │       └─► Build headers
    │
    ├─► RetryManager.execute()
    │       │
    │       ├─► Send HTTP request
    │       ├─► Check response
    │       └─► Retry if needed
    │
    ├─► ResponseParser.parse()
    │       │
    │       ├─► Parse JSON/text
    │       └─► Create Response object
    │
    └─► ErrorHandler.check()
            │
            └─► Raise exception if error
```

## Request Building

### URL Construction

```python
class RequestBuilder:
    def build_url(self, path, params=None):
        # Combine base URL and path
        url = urljoin(self.base_url, path)

        # Add query parameters
        if params:
            query = urlencode(params)
            url = f"{url}?{query}"

        return url
```

### Header Management

Headers are merged in priority order:

1. Default client headers
2. Request-specific headers
3. Automatic headers (Content-Type, User-Agent)

```python
def build_headers(self, method, **kwargs):
    headers = {}

    # Default headers
    headers.update(self.default_headers)

    # Request headers
    headers.update(kwargs.get("headers", {}))

    # Automatic headers
    if method in ["POST", "PUT", "PATCH"] and "json" in kwargs:
        headers["Content-Type"] = "application/json"

    return headers
```

## Response Processing

### Type Detection

The ResponseParser automatically detects response type:

```python
def parse(self, raw_response):
    content_type = raw_response.headers.get("Content-Type", "")

    if "application/json" in content_type:
        data = self._parse_json(raw_response.content)
    elif "text/" in content_type:
        data = self._parse_text(raw_response.content)
    else:
        data = raw_response.content  # Raw bytes

    return Response(
        status_code=raw_response.status_code,
        headers=raw_response.headers,
        data=data,
        raw=raw_response.content
    )
```

### Error Detection

Responses are checked for HTTP errors:

```python
def check(self, response):
    if 400 <= response.status_code < 500:
        self._handle_client_error(response)
    elif 500 <= response.status_code < 600:
        self._handle_server_error(response)
```

## Retry Logic

### Exponential Backoff Algorithm

```python
class RetryManager:
    def calculate_backoff(self, attempt):
        # Exponential backoff with jitter
        base_wait = self.backoff_factor ** attempt
        jitter = random.uniform(0, base_wait * 0.1)
        wait_time = min(base_wait + jitter, self.max_backoff)
        return wait_time

    def should_retry(self, response, attempt):
        # Check attempt count
        if attempt >= self.max_attempts:
            return False

        # Check status code
        if response.status_code in self.retry_on_status:
            return True

        return False
```

### Retry Decision Tree

```
Response Received
    │
    ├─► Is status in retry_on_status?
    │     │
    │     ├─► YES: Calculate backoff
    │     └─► NO: Return response
    │
    ├─► Is exception in retry_on_exception?
    │     │
    │     ├─► YES: Calculate backoff
    │     └─► NO: Raise exception
    │
    └─► Attempts < max_attempts?
          │
          ├─► YES: Wait and retry
          └─► NO: Give up
```

## Rate Limiting

### Token Bucket Algorithm

The rate limiter uses a token bucket for smooth traffic:

```python
class RateLimiter:
    def __init__(self, requests_per_second, burst_size):
        self.rate = requests_per_second
        self.bucket_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()

    def acquire(self):
        # Refill tokens based on time passed
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.bucket_size,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now

        # Check if token available
        if self.tokens >= 1:
            self.tokens -= 1
            return True

        # Wait or raise exception
        if self.wait_on_limit:
            wait_time = (1 - self.tokens) / self.rate
            time.sleep(wait_time)
            self.tokens = 0
            return True
        else:
            raise RateLimitException(
                "Rate limit exceeded",
                retry_after=int((1 - self.tokens) / self.rate)
            )
```

### Rate Limit Visualization

```
Token Bucket (size=20, rate=10/sec)
│
├─► Request arrives
│     │
│     ├─► Tokens available? ─► YES ─► Consume token ─► Allow request
│     │                                                      │
│     └─► NO ─► Wait for refill? ─► YES ─► Sleep ──────────┘
│                    │
│                    └─► NO ─► Raise RateLimitException
│
└─► Time passes ─► Refill tokens (rate * elapsed)
```

## Security Features

### SSL Verification

```python
def _create_ssl_context(self, verify_ssl):
    if not verify_ssl:
        # Disable verification (development only)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    # Production SSL verification
    context = ssl.create_default_context()
    return context
```

### Header Validation

```python
def validate_headers(self, headers):
    # Prevent header injection
    for key, value in headers.items():
        if "\n" in key or "\r" in key:
            raise ValidationException(f"Invalid header key: {key}")
        if "\n" in str(value) or "\r" in str(value):
            raise ValidationException(f"Invalid header value: {value}")
```

### Log Sanitization

```python
class Logger:
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "x-auth-token",
        "cookie",
        "x-csrf-token"
    }

    def sanitize_headers(self, headers):
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def log_request(self, request):
        self.logger.info(f"Request: {request.method} {request.url}")
        self.logger.debug(f"Headers: {self.sanitize_headers(request.headers)}")
        # Never log request body in production
```

## Performance Optimizations

### Connection Pooling

While using only standard library, we optimize connections:

```python
class ConnectionPool:
    def __init__(self, max_connections=10):
        self.connections = {}
        self.max_connections = max_connections

    def get_connection(self, host):
        # Reuse existing connection if available
        if host in self.connections:
            conn = self.connections[host]
            if self._is_alive(conn):
                return conn

        # Create new connection
        conn = http.client.HTTPSConnection(host)
        self.connections[host] = conn
        return conn

    def _is_alive(self, conn):
        # Check if connection is still valid
        try:
            conn.sock.getpeername()
            return True
        except:
            return False
```

### Response Streaming

For large responses, streaming prevents memory issues:

```python
def stream_response(self, response):
    chunk_size = 8192

    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        yield chunk
```

## Error Handling Architecture

### Exception Hierarchy Design

```
APIException
    │
    ├─► ConnectionException    # Network layer
    ├─► TimeoutException       # Timeout layer
    ├─► RateLimitException     # Rate limit layer
    └─► ValidationException    # Validation layer
```

Each exception carries context:

```python
class APIException(Exception):
    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        self.timestamp = datetime.now()
        self.request = response.request if response else None
```

## Testing Architecture

### Test Pyramid

```
        ╱╲
       ╱E2E╲       10% - Full integration tests
      ╱──────╲
     ╱  Integ  ╲    30% - Component integration
    ╱────────────╲
   ╱     Unit     ╲  60% - Unit tests
  ╱────────────────╲
```

### Mock Strategy

```python
class MockHTTPConnection:
    """Mock for testing without network calls."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def request(self, method, url, body=None, headers=None):
        self.requests.append({
            "method": method,
            "url": url,
            "body": body,
            "headers": headers
        })

    def getresponse(self):
        return self.responses.pop(0)
```

## Future Considerations

While maintaining zero dependencies, future enhancements could include:

- **Async Support**: Using asyncio from standard library
- **HTTP/2**: When available in standard library
- **Caching**: Simple in-memory cache
- **Metrics**: Performance tracking
- **Circuit Breaker**: Built-in resilience patterns

## Summary

The REST API Client architecture prioritizes:

1. **Simplicity** - Each component does one thing well
2. **Reliability** - Retry logic and rate limiting built-in
3. **Security** - SSL verification, validation, sanitization
4. **Performance** - Connection reuse, streaming
5. **Maintainability** - Clear separation of concerns

This design ensures the client is robust, efficient, and easy to understand.
