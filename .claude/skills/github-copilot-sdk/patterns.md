# Production Patterns for GitHub Copilot SDK

Proven patterns for building robust, performant applications with the GitHub Copilot SDK.

## Core Patterns

### 1. Session Lifecycle Management

**Problem:** Sessions hold resources (HTTP connections, memory buffers) that must be cleaned up.

**Solution:** Use context managers and explicit cleanup patterns.

```python
from contextlib import asynccontextmanager
from github_copilot_sdk import CopilotSDK

@asynccontextmanager
async def copilot_session(api_key: str):
    """Managed session lifecycle with guaranteed cleanup."""
    sdk = CopilotSDK(api_key=api_key)
    session = None
    try:
        session = await sdk.create_session()
        yield session
    finally:
        if session:
            await session.close()
        await sdk.close()

# Usage
async def process_request(prompt: str):
    async with copilot_session(API_KEY) as session:
        response = await session.chat(prompt)
        return response.text
```

**Benefits:**
- Guaranteed cleanup even on exceptions
- Clear resource ownership
- Prevents memory leaks
- Thread-safe session handling

**Tradeoffs:**
- Slightly more verbose
- Creates new session per request (consider pooling for high throughput)

---

### 2. Streaming Best Practices

**Problem:** Streaming responses require careful buffer management and UI updates.

**Solution:** Use async generators with backpressure handling.

```python
async def stream_with_backpressure(
    session: CopilotSession,
    prompt: str,
    max_buffer_size: int = 1024
):
    """Stream with controlled buffering."""
    buffer = []
    buffer_size = 0
    
    async for chunk in session.stream(prompt):
        buffer.append(chunk.text)
        buffer_size += len(chunk.text)
        
        # Flush buffer when size threshold reached
        if buffer_size >= max_buffer_size:
            yield "".join(buffer)
            buffer.clear()
            buffer_size = 0
    
    # Flush remaining
    if buffer:
        yield "".join(buffer)

# UI Integration Pattern
class StreamingUI:
    def __init__(self):
        self.update_interval = 0.1  # 100ms
        self.last_update = 0
        
    async def display_stream(self, session, prompt):
        """Update UI with rate limiting."""
        import time
        
        async for chunk in session.stream(prompt):
            self.buffer += chunk.text
            
            now = time.time()
            if now - self.last_update > self.update_interval:
                self.render(self.buffer)
                self.last_update = now
        
        # Final render
        self.render(self.buffer)
```

**Benefits:**
- Prevents UI thrashing from rapid updates
- Controls memory usage
- Responsive user experience
- Handles slow consumers gracefully

**Key Considerations:**
- Buffer size affects latency vs throughput
- UI update rate balances responsiveness and performance
- Always flush final buffer

---

### 3. Tool Design Patterns

**Problem:** Poorly designed tools lead to ambiguous calls and error-prone responses.

**Solution:** Follow strict schema design principles.

```python
# ✅ GOOD: Clear, specific tool schema
{
    "name": "search_codebase",
    "description": "Search for code patterns in repository files. Returns matching files with line numbers.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search (Python re syntax)"
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern for files to search (e.g., '**/*.py')",
                "default": "**/*"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 50,
                "minimum": 1,
                "maximum": 500
            }
        },
        "required": ["pattern"]
    }
}

# ✅ GOOD: Structured error returns
def search_codebase(pattern: str, file_pattern: str = "**/*", max_results: int = 50):
    try:
        results = perform_search(pattern, file_pattern, max_results)
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except re.error as e:
        return {
            "success": False,
            "error": f"Invalid regex pattern: {e}",
            "error_type": "invalid_pattern"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {e}",
            "error_type": "search_error"
        }
```

**Schema Design Rules:**
1. One clear purpose per tool
2. Explicit parameter types with constraints
3. Detailed descriptions (what, not how)
4. Sensible defaults for optional parameters
5. Return structured success/error objects
6. Include error_type for programmatic handling

**Anti-example:**
```python
# ❌ BAD: Vague, multi-purpose tool
{
    "name": "do_stuff",
    "description": "Does various things",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string"},  # What actions? What values?
            "data": {"type": "string"}      # Unstructured data
        }
    }
}
```

---

### 4. Error Recovery Patterns

**Problem:** Network failures, rate limits, and timeouts require robust retry logic.

**Solution:** Implement exponential backoff with circuit breaker.

```python
import asyncio
from typing import TypeVar, Callable
from datetime import datetime, timedelta

T = TypeVar('T')

class CircuitBreaker:
    """Circuit breaker for failing operations."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable[[], T]) -> T:
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func()
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

async def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> T:
    """Retry with exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            import random
            jittered_delay = delay * (0.5 + random.random() * 0.5)
            
            await asyncio.sleep(jittered_delay)

# Combined usage
breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)

async def resilient_chat(session: CopilotSession, prompt: str):
    """Chat with retry and circuit breaker."""
    
    async def attempt():
        return await breaker.call(lambda: session.chat(prompt))
    
    return await retry_with_backoff(attempt, max_retries=3)
```

**Benefits:**
- Handles transient failures gracefully
- Prevents cascading failures (circuit breaker)
- Reduces load during outages (exponential backoff)
- Jitter prevents thundering herd

---

### 5. Context Management

**Problem:** Token limits require careful conversation history management.

**Solution:** Implement sliding window with priority-based pruning.

```python
from dataclasses import dataclass
from typing import List
from enum import Enum

class MessagePriority(Enum):
    SYSTEM = 4      # System prompts (never prune)
    CRITICAL = 3    # User's current question
    HIGH = 2        # Recent responses
    LOW = 1         # Old history

@dataclass
class PrioritizedMessage:
    role: str
    content: str
    priority: MessagePriority
    token_count: int

class ContextWindow:
    """Manage conversation context within token limits."""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.messages: List[PrioritizedMessage] = []
    
    def add_message(self, role: str, content: str, priority: MessagePriority):
        """Add message with priority."""
        token_count = self._estimate_tokens(content)
        msg = PrioritizedMessage(role, content, priority, token_count)
        self.messages.append(msg)
        self._prune_if_needed()
    
    def _prune_if_needed(self):
        """Remove low-priority messages to stay under limit."""
        total_tokens = sum(m.token_count for m in self.messages)
        
        if total_tokens <= self.max_tokens:
            return
        
        # Sort by priority (keep high priority)
        sorted_msgs = sorted(self.messages, key=lambda m: m.priority.value)
        
        # Remove low-priority messages until under limit
        while total_tokens > self.max_tokens and sorted_msgs:
            if sorted_msgs[0].priority == MessagePriority.SYSTEM:
                break  # Never remove system messages
            
            removed = sorted_msgs.pop(0)
            self.messages.remove(removed)
            total_tokens -= removed.token_count
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def get_messages(self) -> List[dict]:
        """Get messages for API call."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]

# Usage
context = ContextWindow(max_tokens=4000)

# System prompt (highest priority)
context.add_message("system", "You are a helpful assistant.", MessagePriority.SYSTEM)

# User questions (critical)
context.add_message("user", "What is Python?", MessagePriority.CRITICAL)

# Assistant response (high initially, demote over time)
context.add_message("assistant", "Python is...", MessagePriority.HIGH)

# Get pruned messages for API
messages = context.get_messages()
```

**Benefits:**
- Stays within token limits automatically
- Preserves important context (system prompts, current query)
- Handles long conversations gracefully
- Predictable memory usage

**Advanced:** Implement semantic compression or summarization for old messages.

---

### 6. Rate Limiting Strategies

**Problem:** API quota limits and throttling require request management.

**Solution:** Token bucket algorithm with queue management.

```python
import asyncio
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        self.rate = requests_per_minute / 60.0  # requests per second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = datetime.now()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make request (blocks if rate limited)."""
        async with self._lock:
            now = datetime.now()
            elapsed = (now - self.last_update).total_seconds()
            
            # Refill tokens based on elapsed time
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now
            
            # If no tokens available, calculate wait time
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 1.0
            
            self.tokens -= 1.0

class RequestQueue:
    """Priority queue for API requests."""
    
    def __init__(self, rate_limiter: RateLimiter, max_concurrent: int = 5):
        self.rate_limiter = rate_limiter
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.metrics = {
            "total_requests": 0,
            "rate_limited": 0,
            "errors": 0
        }
    
    async def execute(self, func, *args, **kwargs):
        """Execute function with rate limiting and concurrency control."""
        async with self.semaphore:
            await self.rate_limiter.acquire()
            self.metrics["total_requests"] += 1
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                self.metrics["errors"] += 1
                raise

# Usage
limiter = RateLimiter(requests_per_minute=60, burst_size=10)
queue = RequestQueue(limiter, max_concurrent=5)

async def process_batch(prompts: List[str]):
    """Process multiple prompts with rate limiting."""
    tasks = [
        queue.execute(session.chat, prompt)
        for prompt in prompts
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

**Benefits:**
- Respects API rate limits automatically
- Allows bursts for responsiveness
- Controls concurrent requests
- Tracks metrics for monitoring

---

### 7. Testing Strategies

**Problem:** Testing AI integrations is challenging due to non-determinism and costs.

**Solution:** Layer testing with mocks, fixtures, and contract tests.

```python
import pytest
from unittest.mock import AsyncMock, Mock
from typing import AsyncIterator

# Layer 1: Mock SDK for unit tests
class MockCopilotSession:
    """Mock session for testing without API calls."""
    
    def __init__(self, canned_responses: dict = None):
        self.canned_responses = canned_responses or {}
        self.call_history = []
    
    async def chat(self, prompt: str, **kwargs):
        """Return canned response based on prompt."""
        self.call_history.append(("chat", prompt, kwargs))
        
        # Pattern matching for responses
        for pattern, response in self.canned_responses.items():
            if pattern in prompt.lower():
                return Mock(text=response)
        
        return Mock(text="Default mock response")
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[Mock]:
        """Stream canned response as chunks."""
        self.call_history.append(("stream", prompt, kwargs))
        
        response = await self.chat(prompt, **kwargs)
        chunks = response.text.split()
        
        for chunk in chunks:
            yield Mock(text=chunk + " ")

# Layer 2: Fixture-based integration tests
@pytest.fixture
def sample_responses():
    """Realistic response fixtures."""
    return {
        "python": "Python is a high-level programming language...",
        "javascript": "JavaScript is a scripting language...",
        "error": "I encountered an error processing your request."
    }

@pytest.mark.asyncio
async def test_chat_with_mock(sample_responses):
    """Test chat logic without API calls."""
    session = MockCopilotSession(canned_responses=sample_responses)
    
    response = await session.chat("Tell me about Python")
    assert "programming language" in response.text
    assert len(session.call_history) == 1

# Layer 3: Contract tests (verify SDK assumptions)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_sdk_contract():
    """Verify SDK behaves as expected (use sparingly)."""
    if not os.getenv("COPILOT_API_KEY"):
        pytest.skip("No API key for integration test")
    
    sdk = CopilotSDK(api_key=os.getenv("COPILOT_API_KEY"))
    session = await sdk.create_session()
    
    try:
        response = await session.chat("Say 'hello' and nothing else")
        
        # Verify contract assumptions
        assert hasattr(response, 'text')
        assert isinstance(response.text, str)
        assert len(response.text) > 0
    finally:
        await session.close()
        await sdk.close()

# Layer 4: Property-based testing for edge cases
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
@pytest.mark.asyncio
async def test_handles_arbitrary_input(prompt):
    """Verify system handles arbitrary inputs gracefully."""
    session = MockCopilotSession()
    
    # Should not raise exceptions
    response = await session.chat(prompt)
    assert isinstance(response.text, str)
```

**Testing Strategy:**
1. **Unit tests** (90%): Use mocks, fast, no API calls
2. **Integration tests** (8%): Real SDK, limited scope, CI only
3. **Contract tests** (2%): Verify SDK behavior assumptions
4. **Property tests**: Edge cases and input validation

**Benefits:**
- Fast test suite (mostly mocked)
- Minimal API costs
- Catch regressions early
- Document expected behavior

---

### 8. Security Patterns

**Problem:** API keys, user input, and sensitive data require protection.

**Solution:** Defense-in-depth security layers.

```python
import os
import re
from typing import Optional
from dataclasses import dataclass
from functools import wraps

# Pattern 1: Secure API Key Management
class SecureConfig:
    """Secure configuration management."""
    
    @staticmethod
    def get_api_key() -> str:
        """Get API key from secure source."""
        # Priority order:
        # 1. Environment variable (production)
        # 2. Secret management service (e.g., Azure Key Vault)
        # 3. Encrypted config file (development)
        
        key = os.getenv("COPILOT_API_KEY")
        if not key:
            raise ValueError(
                "COPILOT_API_KEY not found. "
                "Set environment variable or use secret manager."
            )
        
        # Validate key format
        if not re.match(r'^[A-Za-z0-9_-]+$', key):
            raise ValueError("Invalid API key format")
        
        return key
    
    @staticmethod
    def mask_api_key(key: str) -> str:
        """Mask API key for logging."""
        if len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

# Pattern 2: Input Validation
class InputValidator:
    """Validate and sanitize user inputs."""
    
    MAX_PROMPT_LENGTH = 10000
    FORBIDDEN_PATTERNS = [
        r"(?i)ignore\s+previous\s+instructions",
        r"(?i)system\s*:\s*new\s+role",
        r"<script.*?>",  # XSS attempt
    ]
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> str:
        """Validate and sanitize prompt."""
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            raise ValueError(
                f"Prompt exceeds maximum length of {cls.MAX_PROMPT_LENGTH}"
            )
        
        # Check for prompt injection attempts
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, prompt):
                raise ValueError(f"Prompt contains forbidden pattern: {pattern}")
        
        return prompt.strip()

# Pattern 3: Sensitive Data Detection
class SensitiveDataFilter:
    """Detect and redact sensitive information."""
    
    PATTERNS = {
        "api_key": r"(?i)(api[_-]?key|token)\s*[=:]\s*['\"]?([A-Za-z0-9_-]{20,})",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    }
    
    @classmethod
    def redact(cls, text: str) -> str:
        """Redact sensitive data from text."""
        redacted = text
        
        for name, pattern in cls.PATTERNS.items():
            redacted = re.sub(pattern, f"[REDACTED_{name.upper()}]", redacted)
        
        return redacted
    
    @classmethod
    def contains_sensitive_data(cls, text: str) -> bool:
        """Check if text contains sensitive data."""
        for pattern in cls.PATTERNS.values():
            if re.search(pattern, text):
                return True
        return False

# Pattern 4: Secure Logging
import logging

class SecureLogger:
    """Logger that redacts sensitive information."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.filter = SensitiveDataFilter()
    
    def _redact(self, message: str) -> str:
        """Redact message before logging."""
        return self.filter.redact(str(message))
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._redact(message), **kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(self._redact(message), **kwargs)

# Usage Pattern
def secure_chat_handler(prompt: str) -> str:
    """Secure chat handler with all protections."""
    logger = SecureLogger(__name__)
    
    try:
        # 1. Validate input
        validated_prompt = InputValidator.validate_prompt(prompt)
        
        # 2. Check for sensitive data
        if SensitiveDataFilter.contains_sensitive_data(validated_prompt):
            logger.error("Prompt contains sensitive data, rejecting")
            raise ValueError("Prompt contains sensitive information")
        
        # 3. Get API key securely
        api_key = SecureConfig.get_api_key()
        
        # 4. Log safely (redacted)
        logger.info(f"Processing prompt: {validated_prompt[:50]}...")
        
        # 5. Make API call
        sdk = CopilotSDK(api_key=api_key)
        # ... rest of implementation
        
        return "Success"
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
```

**Security Checklist:**
- ✅ API keys from environment/secrets manager, never hardcoded
- ✅ Input validation and sanitization
- ✅ Prompt injection detection
- ✅ Sensitive data detection and redaction
- ✅ Secure logging (no secrets in logs)
- ✅ Principle of least privilege (API scopes)
- ✅ Rate limiting to prevent abuse
- ✅ Error messages don't leak sensitive info

---

## Anti-Patterns (What NOT to Do)

### ❌ Anti-Pattern 1: Unbounded Streaming

```python
# BAD: No buffer limits, can exhaust memory
async def stream_forever(session, prompt):
    all_text = ""
    async for chunk in session.stream(prompt):
        all_text += chunk.text  # Growing unbounded
    return all_text
```

**Why it's bad:** Memory grows unbounded, can crash on large responses.

**Fix:** Use buffer limits and streaming processing (Pattern 2).

---

### ❌ Anti-Pattern 2: Swallowing Errors

```python
# BAD: Silent failures
try:
    response = await session.chat(prompt)
except Exception:
    pass  # Error disappears
```

**Why it's bad:** Failures go unnoticed, debugging is impossible.

**Fix:** Log errors, return structured error objects (Pattern 3).

---

### ❌ Anti-Pattern 3: Synchronous Blocking

```python
# BAD: Blocking the event loop
def chat(prompt):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(session.chat(prompt))
```

**Why it's bad:** Blocks event loop, kills concurrency.

**Fix:** Use async/await throughout, or run in thread pool.

---

### ❌ Anti-Pattern 4: Hardcoded API Keys

```python
# BAD: API key in source code
sdk = CopilotSDK(api_key="ghp_abc123...")
```

**Why it's bad:** Security vulnerability, keys leak in git history.

**Fix:** Use environment variables (Pattern 8).

---

### ❌ Anti-Pattern 5: No Timeout Handling

```python
# BAD: Can hang forever
response = await session.chat(prompt)
```

**Why it's bad:** Requests can hang indefinitely.

**Fix:** Always use timeouts:

```python
# GOOD: With timeout
try:
    response = await asyncio.wait_for(
        session.chat(prompt),
        timeout=30.0
    )
except asyncio.TimeoutError:
    # Handle timeout
    response = handle_timeout()
```

---

### ❌ Anti-Pattern 6: Ignoring Token Limits

```python
# BAD: Appending to history without pruning
messages.append({"role": "user", "content": prompt})
messages.append({"role": "assistant", "content": response})
# Eventually hits token limit
```

**Why it's bad:** Requests fail when token limit exceeded.

**Fix:** Implement context window management (Pattern 5).

---

### ❌ Anti-Pattern 7: Over-Generic Tools

```python
# BAD: Swiss-army knife tool
{
    "name": "execute",
    "description": "Execute any operation",
    "parameters": {
        "operation": {"type": "string"},
        "data": {"type": "object"}
    }
}
```

**Why it's bad:** Ambiguous, error-prone, hard to test.

**Fix:** Create focused, single-purpose tools (Pattern 3).

---

### ❌ Anti-Pattern 8: Insufficient Testing

```python
# BAD: Only testing the happy path
def test_chat():
    response = await session.chat("Hello")
    assert response.text
```

**Why it's bad:** Misses error cases, edge cases, failures.

**Fix:** Test errors, edge cases, timeouts (Pattern 7).

---

## Production Checklist

Before deploying to production:

### Reliability
- [ ] Error handling with retries (Pattern 4)
- [ ] Circuit breaker for failing services (Pattern 4)
- [ ] Timeouts on all API calls
- [ ] Graceful degradation when API unavailable
- [ ] Health check endpoint
- [ ] Structured logging with correlation IDs

### Performance
- [ ] Rate limiting implemented (Pattern 6)
- [ ] Connection pooling/reuse
- [ ] Streaming for large responses (Pattern 2)
- [ ] Context pruning for long conversations (Pattern 5)
- [ ] Caching where appropriate
- [ ] Performance monitoring and alerting

### Security
- [ ] API keys from secure source (Pattern 8)
- [ ] Input validation (Pattern 8)
- [ ] Sensitive data redaction (Pattern 8)
- [ ] Secure logging (no secrets) (Pattern 8)
- [ ] HTTPS only for API calls
- [ ] Principle of least privilege

### Observability
- [ ] Metrics: request rate, latency, errors
- [ ] Distributed tracing
- [ ] Structured logs with context
- [ ] Alerting on error rates, latency
- [ ] Dashboard with key metrics
- [ ] Log aggregation and search

### Testing
- [ ] Unit tests with mocks (>80% coverage)
- [ ] Integration tests (critical paths)
- [ ] Load testing (expected throughput)
- [ ] Chaos testing (failure scenarios)
- [ ] Security testing (injection, XSS)

### Operations
- [ ] Deployment automation (CI/CD)
- [ ] Rollback plan
- [ ] Runbook for common issues
- [ ] On-call rotation and escalation
- [ ] Capacity planning
- [ ] Disaster recovery plan

---

## Performance Optimization Tips

### 1. Connection Reuse

```python
# Reuse SDK instance
sdk = CopilotSDK(api_key=api_key)
# Create multiple sessions from same SDK
session1 = await sdk.create_session()
session2 = await sdk.create_session()
```

**Benefit:** Reduces connection overhead.

---

### 2. Parallel Processing

```python
# Process multiple prompts in parallel
async def batch_process(prompts: List[str]):
    tasks = [session.chat(p) for p in prompts]
    return await asyncio.gather(*tasks)
```

**Benefit:** Reduces total latency for batches.

---

### 3. Request Deduplication

```python
class RequestCache:
    """Cache identical requests."""
    
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl
    
    async def get_or_compute(self, key: str, func):
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
        
        result = await func()
        self.cache[key] = (result, time.time())
        return result
```

**Benefit:** Avoid redundant API calls for duplicate requests.

---

### 4. Streaming for Large Responses

```python
# Use streaming instead of buffering complete response
async for chunk in session.stream(prompt):
    process_chunk(chunk)  # Process incrementally
```

**Benefit:** Lower latency to first byte, reduced memory.

---

### 5. Lazy Loading

```python
# Don't create sessions until needed
class LazySession:
    def __init__(self, sdk):
        self.sdk = sdk
        self._session = None
    
    async def get(self):
        if not self._session:
            self._session = await self.sdk.create_session()
        return self._session
```

**Benefit:** Reduces initialization overhead.

---

### 6. Compression

```python
# Enable compression for large payloads
sdk = CopilotSDK(
    api_key=api_key,
    compression=True  # If supported
)
```

**Benefit:** Reduces network transfer time.

---

### 7. Monitor and Profile

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

@measure_time
async def chat(prompt):
    return await session.chat(prompt)
```

**Benefit:** Identify bottlenecks with data.

---

## Conclusion

These patterns represent battle-tested approaches for production GitHub Copilot SDK integrations. Follow them to build robust, secure, and performant applications.

**Key Principles:**
- Explicit resource management (Pattern 1)
- Graceful error handling (Pattern 4)
- Security by default (Pattern 8)
- Test at multiple layers (Pattern 7)
- Monitor everything in production

**When in doubt:**
- Start simple, add complexity only when needed
- Measure before optimizing
- Test failure cases, not just happy paths
- Log everything (safely)
- Fail fast and explicitly
