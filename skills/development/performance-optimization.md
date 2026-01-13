# Performance Optimization

Systematic performance analysis and optimization methodology.

## When to Use

- Application is noticeably slow
- Resource usage is too high
- Scaling requirements not met
- Users complaining about performance
- Cost optimization needed

## When NOT to Optimize

### Stop Signs

```
[ ] No performance problem exists (don't guess!)
[ ] Haven't measured current performance
[ ] Optimization is premature (feature not done)
[ ] Maintenance cost exceeds benefit
[ ] Simpler solution exists (more hardware)
[ ] Code readability would suffer significantly
```

### The Optimization Rules

```
Rule 1: Don't optimize
Rule 2: Don't optimize yet (for experts)
Rule 3: Profile before optimizing

"Premature optimization is the root of all evil" - Knuth
```

## Baseline Metrics

### What to Measure

```
Response Time Metrics:
- P50 (median) latency
- P95 latency (most users)
- P99 latency (worst case)
- Max latency

Throughput Metrics:
- Requests per second
- Transactions per second
- Data processed per second

Resource Metrics:
- CPU utilization
- Memory usage
- Disk I/O
- Network I/O
- Connection pool usage
```

### Establishing Baseline

```bash
# HTTP endpoint benchmarking
wrk -t12 -c400 -d30s http://localhost:8080/api/users
# or
hey -n 10000 -c 100 http://localhost:8080/api/users

# Record baseline
echo "Baseline $(date): P50=Xms, P99=Yms, RPS=Z" >> performance.log
```

### Setting Targets

```
Performance Budget Example:
- Page load: <2s
- API response: <200ms (P95)
- Database query: <50ms
- Search: <500ms

Improvement Target:
- Current P95: 800ms
- Target P95: 200ms (4x improvement)
```

## Profiling Tools

### Python Profiling

```python
# cProfile - CPU profiling
import cProfile
import pstats

# Profile a function
cProfile.run('main()', 'output.prof')

# Analyze results
stats = pstats.Stats('output.prof')
stats.strip_dirs()
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions

# Profile specific section
profiler = cProfile.Profile()
profiler.enable()
# ... code to profile ...
profiler.disable()
profiler.print_stats(sort='cumulative')

# Line-by-line profiling
# pip install line_profiler
@profile
def slow_function():
    pass
# Run with: kernprof -l -v script.py
```

### Memory Profiling

```python
# pip install memory_profiler
from memory_profiler import profile

@profile
def memory_intensive():
    data = [i for i in range(1000000)]
    return sum(data)

# Run with: python -m memory_profiler script.py

# Track memory over time
# pip install memray
# memray run script.py
# memray flamegraph memray-*.bin
```

### Async/Await Profiling

```python
# pip install py-spy
# py-spy record -o profile.svg -- python script.py

# For async code
import asyncio
import cProfile

async def main():
    pass

# Profile async
with cProfile.Profile() as pr:
    asyncio.run(main())
pr.print_stats()
```

### JavaScript/Node Profiling

```javascript
// Built-in profiler
node --prof app.js
node --prof-process isolate-*.log > processed.txt

// Chrome DevTools
node --inspect app.js
// Open chrome://inspect

// clinic.js (comprehensive)
// npx clinic doctor -- node app.js
// npx clinic flame -- node app.js
// npx clinic bubbleprof -- node app.js
```

## Optimization Decision Framework

### The 5-Step Process

```
1. MEASURE
   - Establish baseline metrics
   - Identify the bottleneck
   - Quantify the problem

2. ANALYZE
   - Why is it slow?
   - What's the theoretical limit?
   - Where is time spent?

3. HYPOTHESIZE
   - What change will help?
   - How much improvement expected?
   - What are the trade-offs?

4. IMPLEMENT
   - Make ONE change
   - Keep it reversible
   - Maintain readability

5. VERIFY
   - Measure again
   - Compare to baseline
   - Confirm improvement
```

### Decision Matrix

| Bottleneck | First Try | Second Try | Nuclear Option |
|------------|-----------|------------|----------------|
| CPU | Algorithm improvement | Caching | Parallel processing |
| Memory | Reduce allocations | Streaming | Increase memory |
| Disk I/O | Caching | Async I/O | Faster storage |
| Network | Reduce requests | Compression | CDN/edge |
| Database | Query optimization | Indexing | Denormalization |

## Common Optimization Patterns

### Caching

```python
# Simple memoization
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_calculation(x, y):
    return complex_math(x, y)

# TTL cache
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=300)  # 5 min TTL

def get_user(user_id):
    if user_id in cache:
        return cache[user_id]
    user = db.fetch_user(user_id)
    cache[user_id] = user
    return user

# Application-level caching
import redis

redis_client = redis.Redis()

def get_expensive_data(key):
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    data = compute_expensive_data()
    redis_client.setex(key, 3600, json.dumps(data))  # 1 hour
    return data
```

### Batching

```python
# Before: N database calls
for user_id in user_ids:
    user = db.get_user(user_id)  # N queries

# After: 1 database call
users = db.get_users(user_ids)  # 1 query

# Batch API calls
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        return await asyncio.gather(*tasks)
```

### Lazy Loading

```python
# Before: Load everything upfront
class Document:
    def __init__(self, id):
        self.id = id
        self.content = load_content(id)  # Always loaded
        self.metadata = load_metadata(id)  # Always loaded

# After: Load on demand
class Document:
    def __init__(self, id):
        self.id = id
        self._content = None
        self._metadata = None
    
    @property
    def content(self):
        if self._content is None:
            self._content = load_content(self.id)
        return self._content
```

### Streaming/Chunking

```python
# Before: Load all into memory
def process_file(path):
    with open(path) as f:
        data = f.read()  # 10GB in memory
    return process(data)

# After: Stream processing
def process_file(path):
    results = []
    with open(path) as f:
        for line in f:  # One line at a time
            results.append(process_line(line))
    return results

# Generator for large datasets
def read_large_csv(path):
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            yield row  # One row at a time
```

### Async I/O

```python
# Before: Sequential I/O
def fetch_all(urls):
    results = []
    for url in urls:
        results.append(requests.get(url))  # Wait for each
    return results

# After: Concurrent I/O
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        return await asyncio.gather(*tasks)  # All at once
```

### Database Optimization

```python
# Add appropriate indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);

# Use EXPLAIN to analyze queries
EXPLAIN ANALYZE SELECT * FROM orders WHERE user_id = 123;

# Avoid SELECT *
SELECT id, name, email FROM users WHERE active = true;

# Use connection pooling
from sqlalchemy.pool import QueuePool
engine = create_engine(url, poolclass=QueuePool, pool_size=10)
```

## Performance Anti-Patterns

### Premature Optimization

```python
# Bad: Optimizing without evidence
def get_users():
    # "This might be slow someday"
    return complicated_caching_logic()

# Good: Simple first, optimize when needed
def get_users():
    return db.query(User).all()
```

### Over-Caching

```python
# Bad: Cache everything
@cache.memoize(timeout=3600)
def get_current_time():  # Don't cache this!
    return datetime.now()

# Good: Cache expensive, stable operations
@cache.memoize(timeout=3600)
def get_user_permissions(user_id):
    return expensive_permission_calculation(user_id)
```

### Micro-Optimizations

```python
# Bad: Micro-optimizing non-bottleneck
# Spending hours optimizing a function called once

# Good: Focus on actual bottlenecks
# If database is 90% of time, optimize queries first
```

## Performance Testing Checklist

### Before Optimization

```
[ ] Baseline metrics recorded
[ ] Bottleneck identified via profiling
[ ] Target improvement defined
[ ] Trade-offs understood
[ ] Rollback plan exists
```

### During Optimization

```
[ ] One change at a time
[ ] Measuring after each change
[ ] Keeping code readable
[ ] Not breaking functionality
[ ] Documenting changes
```

### After Optimization

```
[ ] Target met?
[ ] No regression in other areas?
[ ] Tests still pass?
[ ] Code still maintainable?
[ ] Performance documented?
```

## Quick Commands

```bash
# Python CPU profiling
python -m cProfile -s cumulative script.py | head -20

# Python memory profiling
python -m memory_profiler script.py

# Linux process monitoring
top -p $(pgrep python)
htop

# Disk I/O monitoring
iostat -x 1

# Network monitoring
iftop
nethogs

# Database query analysis
EXPLAIN ANALYZE SELECT ...;
```

## Performance Documentation Template

```markdown
## Performance Optimization: [Feature/Component]

### Problem
- Current P95: Xms
- Target P95: Yms
- User impact: [Description]

### Analysis
- Bottleneck: [CPU/Memory/I/O/Database]
- Root cause: [Description]
- Profile data: [Link/summary]

### Solution
- Approach: [Description]
- Trade-offs: [What we gave up]
- Implementation: [Brief description]

### Results
- Before: P95=Xms, P99=X'ms
- After: P95=Yms, P99=Y'ms
- Improvement: Z%

### Monitoring
- Metric to watch: [Name]
- Alert threshold: [Value]
```
