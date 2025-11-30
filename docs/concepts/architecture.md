# Architecture Overview

Understanding the design and architecture of the REST API Client library.

## Design Philosophy

The REST API Client is built on these core principles:

1. **Simplicity**: Easy to use for common cases, powerful when needed
2. **Reliability**: Automatic retry logic and error recovery
3. **Performance**: Rate limiting and connection pooling
4. **Type Safety**: Full type hints for better IDE support
5. **Extensibility**: Easy to extend and customize

## Core Components

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│                  APIClient                       │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ Configuration│  │ HTTP Methods │            │
│  └──────────────┘  └──────────────┘            │
│         │                  │                     │
│  ┌──────▼──────────────────▼──────┐            │
│  │     Request Pipeline           │            │
│  │  ┌────────┐  ┌──────────────┐ │            │
│  │  │Prepare │→ │Rate Limiting  │ │            │
│  │  └────────┘  └──────────────┘ │            │
│  │       ↓                        │            │
│  │  ┌────────┐  ┌──────────────┐ │            │
│  │  │Execute │→ │Retry Logic    │ │            │
│  │  └────────┘  └──────────────┘ │            │
│  │       ↓                        │            │
│  │  ┌────────┐  ┌──────────────┐ │            │
│  │  │Process │→ │Error Handling │ │            │
│  │  └────────┘  └──────────────┘ │            │
│  └────────────────────────────────┘            │
└─────────────────────────────────────────────────┘
```

## Request Flow

### 1. Request Preparation

When you call a method like `client.get()`, the library:

```python
# User code
response = client.get("/users", params={"active": True})

# Internal flow
1. Create Request object
2. Merge default headers with request headers
3. Build full URL from base_url + endpoint
4. Validate parameters
```

### 2. Rate Limiting

Before sending, the rate limiter checks:

```python
# Token bucket algorithm
if tokens_available >= 1:
    consume_token()
    proceed_with_request()
else:
    wait_time = calculate_wait_time()
    sleep(wait_time)
    proceed_with_request()
```

### 3. Request Execution

The actual HTTP request:

```python
# With connection pooling
session = get_or_create_session()
raw_response = session.request(
    method=method,
    url=url,
    timeout=timeout,
    **kwargs
)
```

### 4. Retry Logic

On failure, the retry mechanism activates:

```python
for attempt in range(max_attempts):
    try:
        response = make_request()
        if response.ok:
            return response
        if should_retry(response.status_code):
            delay = calculate_backoff(attempt)
            sleep(delay)
            continue
        break
    except RetryableException:
        if attempt < max_attempts - 1:
            delay = calculate_backoff(attempt)
            sleep(delay)
            continue
        raise
```

### 5. Response Processing

Successful responses are processed:

```python
# Transform raw response
response = Response(
    status_code=raw_response.status_code,
    headers=dict(raw_response.headers),
    data=parse_response_body(raw_response),
    elapsed=raw_response.elapsed.total_seconds()
)
```

### 6. Error Handling

Errors are transformed into specific exceptions:

```python
if response.status_code == 401:
    raise AuthenticationError()
elif response.status_code == 429:
    raise RateLimitError(
        retry_after=get_retry_after(response.headers)
    )
elif response.status_code >= 500:
    raise ServerError()
# etc.
```

## Module Structure

### File Organization

```
rest_api_client/
├── __init__.py           # Package exports
├── client.py             # Main APIClient class
├── async_client.py       # AsyncAPIClient class
├── config.py            # Configuration dataclasses
├── exceptions.py        # Exception hierarchy
├── models.py            # Request/Response models
├── retry.py            # Retry logic and strategies
├── rate_limiter.py     # Token bucket implementation
├── utils.py            # Utility functions
└── typing.py           # Type definitions
```

### Module Responsibilities

#### client.py

- Main `APIClient` class
- HTTP method implementations
- Request pipeline coordination
- Session management

#### config.py

- `APIConfig` dataclass
- `RetryConfig` dataclass
- Configuration validation
- Default values

#### exceptions.py

- Exception class hierarchy
- Error message formatting
- Status code mapping

#### models.py

- `Request` dataclass
- `Response` dataclass
- Data serialization

#### retry.py

- Retry strategy interface
- Exponential backoff implementation
- Retry decision logic

#### rate_limiter.py

- Token bucket algorithm
- Rate limit tracking
- Throttling logic

## Key Design Patterns

### 1. Strategy Pattern

Retry strategies are pluggable:

```python
class RetryStrategy(ABC):
    @abstractmethod
    def should_retry(self, response, attempt):
        pass

    @abstractmethod
    def get_delay(self, attempt):
        pass

class ExponentialBackoff(RetryStrategy):
    def get_delay(self, attempt):
        return self.base ** attempt

class LinearBackoff(RetryStrategy):
    def get_delay(self, attempt):
        return self.increment * attempt
```

### 2. Dataclass Configuration

Configuration uses dataclasses for simplicity:

```python
config = APIConfig(
    base_url="https://api.example.com",
    timeout=60,
    rate_limit_calls=100,
    rate_limit_period=60,
    max_retries=5
)
```

### 3. Decorator Pattern

Request/response processing via decorators:

```python
@rate_limit
@retry
@log_request
def make_request(self, method, endpoint, **kwargs):
    # Core request logic
    pass
```

### 4. Template Method

Request pipeline as template:

```python
def execute_request(self, request):
    self.prepare_request(request)    # Hook
    self.check_rate_limit(request)   # Hook
    response = self.send_request(request)
    self.process_response(response)  # Hook
    return response
```

## Connection Management

### Session Pooling

The client maintains a session pool:

```python
class SessionPool:
    def __init__(self, pool_size=10):
        self.sessions = []
        self.pool_size = pool_size

    def get_session(self):
        if self.sessions:
            return self.sessions.pop()
        return self.create_session()

    def return_session(self, session):
        if len(self.sessions) < self.pool_size:
            self.sessions.append(session)
        else:
            session.close()
```

### Connection Reuse

HTTP keep-alive for efficiency:

```python
session.mount('https://', HTTPAdapter(
    pool_connections=10,
    pool_maxsize=10,
    max_retries=0,  # We handle retries ourselves
    pool_block=False
))
```

## Thread Safety

The client is thread-safe:

```python
import threading

class APIClient:
    def __init__(self):
        self._lock = threading.RLock()
        self._rate_limiter_lock = threading.Lock()

    def get(self, endpoint):
        with self._lock:
            # Thread-safe operations
            pass
```

Multiple threads can share a client:

```python
client = APIClient(base_url="https://api.example.com")

def worker(thread_id):
    response = client.get(f"/data/{thread_id}")
    print(f"Thread {thread_id}: {response.data}")

threads = [
    threading.Thread(target=worker, args=(i,))
    for i in range(10)
]

for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Async Architecture

### AsyncAPIClient

Async version uses `aiohttp`:

```python
class AsyncAPIClient:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get(self, endpoint):
        async with self.rate_limiter:
            async with self.session.get(url) as response:
                return await self.process_response(response)
```

### Async Rate Limiting

Using asyncio primitives:

```python
class AsyncRateLimiter:
    def __init__(self, calls, period):
        self.semaphore = asyncio.Semaphore(calls)
        self.calls = calls
        self.period = period

    async def acquire(self):
        async with self.semaphore:
            await self.execute()
            asyncio.create_task(self.release_after_period())

    async def release_after_period(self):
        await asyncio.sleep(self.period)
        self.semaphore.release()
```

## Extensibility Points

### Custom Clients

Extend the base client:

```python
class MyAPIClient(APIClient):
    def authenticate(self, username, password):
        """Custom authentication method."""
        response = self.post("/auth", json={
            "username": username,
            "password": password
        })
        self.headers["Authorization"] = f"Bearer {response.data['token']}"

    def handle_error(self, response):
        """Custom error handling."""
        if response.status_code == 402:
            raise PaymentRequiredError()
        super().handle_error(response)
```

### Future Enhancements

The following features are planned for future releases:

#### Middleware System

- Request/response interceptors
- Custom processing pipeline
- Logging and monitoring hooks

#### Plugin Architecture

- Caching plugins
- Authentication plugins
- Custom serialization

#### Advanced Features

- Circuit breaker pattern
- Request/response streaming
- WebSocket support

## Performance Considerations

### Memory Usage

- Request/response objects are lightweight dataclasses
- Connection pooling limits resource usage
- Rate limiter uses minimal memory (token counter)

### CPU Usage

- JSON parsing is the main CPU consumer
- Retry delays use sleep (no CPU spinning)
- Rate limiting uses efficient token bucket

### Network Optimization

- HTTP keep-alive reduces connection overhead
- Connection pooling reuses TCP connections
- Compression support (gzip, deflate)

## Security Features

### SSL/TLS

- SSL verification enabled by default
- Custom CA bundle support
- Certificate pinning capability

### Authentication

- Multiple auth schemes supported
- Token refresh capability
- Secure credential storage

### Data Protection

- No credential logging
- Sensitive header masking
- Request/response sanitization

## Monitoring and Observability

### Metrics

Track key metrics:

```python
class MetricsCollector:
    def record_request(self, method, endpoint, duration, status):
        self.request_count.increment()
        self.request_duration.observe(duration)
        self.status_codes[status].increment()
```

### Logging

Structured logging throughout:

```python
logger.info(
    "API request",
    extra={
        "method": method,
        "endpoint": endpoint,
        "duration": duration,
        "status": status_code,
        "retry_count": retries
    }
)
```

### Tracing

OpenTelemetry support is planned for a future release. The library is designed with observability in mind, making it easy to add tracing when needed.

## Roadmap

### Version 1.0 (Current)

✅ Core HTTP client functionality
✅ Retry logic with exponential backoff
✅ Rate limiting with token bucket
✅ Comprehensive exception hierarchy
✅ Async support
✅ Type hints
✅ Connection pooling

### Version 1.1 (Planned)

- [ ] Middleware system for request/response processing
- [ ] Plugin architecture for extensibility
- [ ] OpenTelemetry integration for distributed tracing
- [ ] Circuit breaker pattern for fault tolerance
- [ ] Request/response streaming for large payloads

### Version 1.2 (Future)

- [ ] GraphQL support
- [ ] WebSocket connections
- [ ] HTTP/2 support
- [ ] Advanced caching strategies
- [ ] Batch request optimization

### Version 2.0 (Long-term)

- [ ] gRPC support
- [ ] Multi-protocol abstraction
- [ ] Advanced retry strategies (adaptive, predictive)
- [ ] Built-in API mocking for testing
- [ ] Performance profiling tools

## Summary

The REST API Client architecture provides:

1. **Robust request handling** through a clear pipeline
2. **Reliability** via retry logic and error recovery
3. **Performance** through rate limiting and connection pooling
4. **Extensibility** via inheritance and clear extension points
5. **Observability** through logging and metrics

This design ensures the library is both simple for basic use cases and powerful enough for complex enterprise requirements, with a clear path for future enhancements.
