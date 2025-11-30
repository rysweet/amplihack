# Rate Limiting Explained

Understanding how the token bucket algorithm works and why it's used for rate limiting.

## What is Rate Limiting?

Rate limiting controls the number of requests a client can make to an API within a specific time period. It's essential for:

- **API Protection**: Preventing abuse and overload
- **Fair Usage**: Ensuring equitable resource distribution
- **Cost Control**: Managing API usage costs
- **Stability**: Maintaining consistent performance

## The Token Bucket Algorithm

The REST API Client uses the token bucket algorithm, a flexible and efficient approach to rate limiting.

### How It Works

Imagine a bucket that:

1. Holds a fixed number of tokens
2. Each request consumes one token
3. Tokens refill at a constant rate
4. If the bucket is empty, requests must wait

### Visual Representation

```
Initial State (Full Bucket):
┌─────────────┐
│ ● ● ● ● ● ● │ Capacity: 10 tokens
│ ● ● ● ● ● ● │ Current: 10 tokens
└─────────────┘

After 3 Requests:
┌─────────────┐
│ ● ● ● ● ● ● │ Capacity: 10 tokens
│ ● ○ ○ ○ ○ ○ │ Current: 7 tokens
└─────────────┘

Tokens Refilling (1 token/second):
┌─────────────┐
│ ● ● ● ● ● ● │ Capacity: 10 tokens
│ ● ● ○ ○ ○ ○ │ Current: 8 tokens
└─────────────┘

Bucket Empty (Must Wait):
┌─────────────┐
│ ○ ○ ○ ○ ○ ○ │ Capacity: 10 tokens
│ ○ ○ ○ ○ ○ ○ │ Current: 0 tokens
└─────────────┘ ← Wait for refill
```

## Implementation Details

### Core Algorithm

```python
class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()

    def consume(self, tokens=1):
        """Try to consume tokens."""
        # Refill bucket based on time elapsed
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Calculate new tokens
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)

        self.last_refill = now

    def time_until_available(self, tokens=1):
        """Calculate wait time for tokens."""
        if self.tokens >= tokens:
            return 0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate
```

### Rate Limiter Integration

The REST API Client integrates the token bucket:

```python
class RateLimiter:
    def __init__(self, calls_per_period, period_seconds):
        # Convert to tokens and refill rate
        self.bucket = TokenBucket(
            capacity=calls_per_period,
            refill_rate=calls_per_period / period_seconds
        )

    def acquire(self):
        """Acquire permission to make a request."""
        while not self.bucket.consume():
            wait_time = self.bucket.time_until_available()
            time.sleep(wait_time)
```

## Configuration Examples

### Basic Rate Limiting

```python
# 100 requests per minute
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=100,
    rate_limit_period=60
)
```

This creates a token bucket with:

- Capacity: 100 tokens
- Refill rate: 1.67 tokens/second
- Burst capacity: 100 requests

### Different Rate Limit Patterns

#### Steady Rate (No Burst)

```python
# 1 request per second, no bursting
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=1,
    rate_limit_period=1
)
```

#### High Burst, Low Sustained

```python
# Burst of 50, but only 100 per hour sustained
config = RateLimiterConfig(
    calls=100,
    period=3600,
    burst=50
)
```

#### Aggressive Rate Limiting

```python
# Very restrictive: 10 requests per minute
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=10,
    rate_limit_period=60
)
```

## Advantages of Token Bucket

### 1. Burst Handling

Token bucket allows bursts up to the bucket capacity:

```python
# Can make 10 rapid requests, then must slow down
bucket = TokenBucket(capacity=10, refill_rate=1.0)

# Burst: 10 quick requests
for i in range(10):
    bucket.consume()  # All succeed immediately

# 11th request must wait
bucket.consume()  # Waits ~1 second
```

### 2. Smooth Rate Control

Unlike fixed windows, token bucket provides smooth rate limiting:

```
Fixed Window (Problems):
[0-60s]: 100 requests allowed
[60-120s]: 100 requests allowed
Problem: 200 requests possible at boundary (59-61s)

Token Bucket (Smooth):
Continuous refill prevents boundary exploitation
```

### 3. Flexibility

Supports various patterns:

```python
# Bursty traffic
burst_config = TokenBucket(capacity=100, refill_rate=1.0)

# Steady traffic
steady_config = TokenBucket(capacity=1, refill_rate=1.0)

# Mixed pattern
mixed_config = TokenBucket(capacity=50, refill_rate=2.0)
```

## Comparison with Other Algorithms

### Fixed Window

```python
class FixedWindow:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self.requests = []

    def allow_request(self):
        now = time.time()
        # Remove old requests
        self.requests = [
            t for t in self.requests
            if now - t < self.window
        ]

        if len(self.requests) < self.limit:
            self.requests.append(now)
            return True
        return False
```

**Pros**: Simple implementation
**Cons**: Boundary issues, less flexible

### Sliding Window

```python
class SlidingWindow:
    def __init__(self, limit, window_seconds):
        self.limit = limit
        self.window = window_seconds
        self.requests = deque()

    def allow_request(self):
        now = time.time()
        # Remove expired entries
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()

        if len(self.requests) < self.limit:
            self.requests.append(now)
            return True
        return False
```

**Pros**: No boundary issues
**Cons**: More memory usage, complex implementation

### Leaky Bucket

```python
class LeakyBucket:
    def __init__(self, capacity, leak_rate):
        self.capacity = capacity
        self.volume = 0
        self.leak_rate = leak_rate
        self.last_leak = time.time()

    def add(self, amount=1):
        self.leak()
        if self.volume + amount <= self.capacity:
            self.volume += amount
            return True
        return False

    def leak(self):
        now = time.time()
        leaked = (now - self.last_leak) * self.leak_rate
        self.volume = max(0, self.volume - leaked)
        self.last_leak = now
```

**Pros**: Smooth output rate
**Cons**: No burst capability

## Rate Limiting Strategies

### Conservative Strategy

Be well below limits to account for:

- Clock skew
- Network delays
- Other clients

```python
# API allows 100/minute, we use 80
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=80,  # 20% buffer
    rate_limit_period=60
)
```

### Adaptive Strategy

Adjust based on response headers:

```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.current_limit = 100
        self.bucket = TokenBucket(100, 100/60)

    def update_from_headers(self, headers):
        """Adapt to server's rate limit headers."""
        if 'X-RateLimit-Limit' in headers:
            new_limit = int(headers['X-RateLimit-Limit'])
            if new_limit != self.current_limit:
                self.current_limit = new_limit
                self.bucket = TokenBucket(new_limit, new_limit/60)

        if 'X-RateLimit-Remaining' in headers:
            remaining = int(headers['X-RateLimit-Remaining'])
            self.bucket.tokens = min(remaining, self.bucket.tokens)
```

### Multi-Tier Strategy

Different limits for different operations:

```python
class MultiTierRateLimiter:
    def __init__(self):
        self.limiters = {
            'read': TokenBucket(1000, 1000/60),   # 1000/min for reads
            'write': TokenBucket(100, 100/60),    # 100/min for writes
            'delete': TokenBucket(10, 10/60)      # 10/min for deletes
        }

    def acquire(self, operation_type):
        limiter = self.limiters.get(operation_type, self.limiters['read'])
        return limiter.consume()
```

## Handling Rate Limit Errors

### Retry After Header

```python
def handle_429_response(response):
    """Handle rate limit response."""
    retry_after = response.headers.get('Retry-After')

    if retry_after:
        if retry_after.isdigit():
            # Seconds to wait
            wait_seconds = int(retry_after)
        else:
            # HTTP date
            retry_time = parsedate_to_datetime(retry_after)
            wait_seconds = (retry_time - datetime.now()).total_seconds()

        time.sleep(wait_seconds)
    else:
        # Exponential backoff if no header
        time.sleep(2 ** attempt)
```

### Rate Limit Headers

Common headers to check:

```python
def parse_rate_limit_headers(headers):
    """Extract rate limit information."""
    return {
        'limit': int(headers.get('X-RateLimit-Limit', 0)),
        'remaining': int(headers.get('X-RateLimit-Remaining', 0)),
        'reset': int(headers.get('X-RateLimit-Reset', 0)),
        'retry_after': headers.get('Retry-After')
    }
```

## Best Practices

### 1. Start Conservative

Begin with lower limits and increase gradually:

```python
# Development
dev_limit = 10  # Very conservative

# Staging
staging_limit = 50  # Half of production

# Production
prod_limit = 90  # 10% below actual limit
```

### 2. Monitor Usage

Track your rate limit consumption:

```python
class MonitoredRateLimiter(RateLimiter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_requests = 0
        self.total_wait_time = 0

    def acquire(self):
        start = time.time()
        super().acquire()
        wait_time = time.time() - start

        self.total_requests += 1
        self.total_wait_time += wait_time

        if self.total_requests % 100 == 0:
            avg_wait = self.total_wait_time / self.total_requests
            print(f"Avg wait time: {avg_wait:.3f}s")
```

### 3. Implement Backpressure

Slow down request generation when hitting limits:

```python
class BackpressureClient:
    def __init__(self, client):
        self.client = client
        self.pressure_level = 0

    def request(self, *args, **kwargs):
        # Add delay based on pressure
        if self.pressure_level > 0:
            time.sleep(self.pressure_level * 0.1)

        try:
            return self.client.request(*args, **kwargs)
        except RateLimitError:
            self.pressure_level = min(10, self.pressure_level + 1)
            raise
        else:
            self.pressure_level = max(0, self.pressure_level - 0.1)
```

### 4. Use Circuit Breakers

Temporarily stop requests when consistently rate limited:

```python
class CircuitBreaker:
    def __init__(self, threshold=3, timeout=60):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure = None
        self.state = "CLOSED"

    def call(self, func, *args):
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker OPEN")

        try:
            result = func(*args)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except RateLimitError:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.threshold:
                self.state = "OPEN"
            raise
```

## Summary

The token bucket algorithm provides:

1. **Flexible rate limiting** with burst capability
2. **Smooth traffic shaping** without boundary issues
3. **Efficient implementation** with minimal overhead
4. **Adaptability** to different traffic patterns

Understanding rate limiting helps you:

- Design efficient API clients
- Respect API provider limits
- Handle rate limit errors gracefully
- Optimize request patterns
