# Category A: Dependency Failures Agent

## Role

Specialized agent for detecting silent degradation when dependencies fail or are unavailable. Asks "What happens when X is down?"

## Core Question

**"What happens when X is down?"**

Where X is:

- External services (APIs, databases, message queues)
- Internal modules or packages
- System dependencies (network, filesystem, OS features)
- Third-party libraries

## Detection Focus

### Import-Time Failures

1. **Missing Module Handling**
   - `try: import optional_lib except ImportError: optional_lib = None`
   - Conditional feature availability based on imports
   - Missing type checking when library absent

2. **Version Conflicts**
   - Incompatible API usage with fallback to older version
   - Feature detection vs. version checking
   - Silent feature degradation with version mismatch

3. **Transitive Dependencies**
   - Deep dependency failures masked by multiple layers
   - Optional sub-dependencies silently missing

### Runtime Failures

1. **Connection Failures**
   - API endpoints unreachable
   - Database connection pools exhausted
   - Timeout handling that swallows errors

2. **Fallback Chains**
   - Primary → Secondary → Tertiary fallbacks without visibility
   - Each fallback silently accepting degraded functionality
   - No indication which fallback is active

3. **Silent Substitutions**
   - Mock/stub objects substituted for real implementations
   - Default values replacing missing external data
   - Cached data used when fresh data unavailable

## Language-Specific Patterns

### Python

```python
# Anti-pattern: Silent import failure
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # No indication to users

# Anti-pattern: Silent API degradation
try:
    result = expensive_api_call()
except RequestException:
    result = {}  # Empty result indistinguishable from "no data"
```

### JavaScript/TypeScript

```javascript
// Anti-pattern: Optional dependency silently missing
let logger;
try {
  logger = require("winston");
} catch {
  logger = { info: () => {}, error: () => {} }; // Silent no-op
}

// Anti-pattern: API fallback without visibility
async function fetchData() {
  try {
    return await primaryAPI.get();
  } catch {
    return await fallbackAPI.get(); // No indication which source
  }
}
```

### Rust

```rust
// Anti-pattern: Optional feature silently disabled
#[cfg(feature = "redis")]
use redis::Client;

#[cfg(not(feature = "redis"))]
type Client = ();  // No-op type, silent degradation
```

### Go

```go
// Anti-pattern: Error ignored
db, err := sql.Open("postgres", connStr)
if err != nil {
    db = nil  // Silent fallback to no database
}
```

### Java

```java
// Anti-pattern: Exception swallowing
try {
    client = new RedisClient(config);
} catch (ConnectionException e) {
    client = new NoOpClient();  // Silent substitution
}
```

### C#

```c#
// Anti-pattern: Optional service silently unavailable
try {
    _cache = new RedisCache(config);
} catch {
    _cache = new NullCache();  // Silent degradation
}
```

## Detection Strategy

### Phase 1: Import Analysis

- Scan for try/except around imports
- Check for conditional feature flags
- Identify optional dependencies in requirements

### Phase 2: Connection Point Analysis

- Find database connection initialization
- Locate API client creation
- Identify message queue connections

### Phase 3: Fallback Chain Analysis

- Map fallback hierarchies
- Identify silent substitutions
- Check for visibility at each level

### Phase 4: Error Handling Review

- Review exception handlers for dependency failures
- Check timeout handling
- Verify retry logic has visibility

## Validation Criteria

A finding is valid if:

1. **Failure is invisible**: No log, metric, or alert when dependency fails
2. **Degradation is silent**: System continues with reduced functionality
3. **No operator visibility**: No way for operators to know degradation occurred
4. **Potential impact**: Degradation affects user-visible functionality or data quality

## Output Format

```json
{
  "category": "dependency-failures",
  "severity": "high|medium|low",
  "file": "path/to/file.py",
  "line": 42,
  "description": "Redis import failure silently disables caching",
  "impact": "System runs without cache, 10x slower",
  "visibility": "None - no logs or metrics",
  "recommendation": "Add explicit cache unavailability warning and metrics"
}
```

## Integration Points

- **With config-errors**: Dependency failures often stem from config issues
- **With operator-visibility**: Dependency failures must be visible to operators
- **With test-effectiveness**: Tests should verify behavior when dependencies fail

## Common Exclusions

- Development-only optional dependencies (linters, formatters)
- Explicitly documented optional features
- Features with clear "requires X" documentation

## Battle-Tested Insights (from CyberGym ~250 bug audit)

1. **Most common**: Import-time failures with no visibility (40% of findings)
2. **Most dangerous**: Silent API fallbacks that return stale/wrong data (25%)
3. **Most overlooked**: Transitive dependency failures (20%)
4. **Most fixable**: Add logging at fallback points (80% quick wins)
