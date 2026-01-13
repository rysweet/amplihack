# Logic/Algorithm Fix Template

> **Coverage**: ~10% of all fixes
> **Target Time**: 60 seconds assessment, 5-15 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Symptoms (not error messages):
- "returns wrong value", "incorrect output"
- "works sometimes", "intermittent failure"
- "only fails with certain input"
- "infinite loop", "never terminates"
- "race condition", "timing issue"
- "off-by-one", "boundary error"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Off-by-one Errors | 30% | Arrays, loops, ranges, boundaries |
| Null/None Handling | 25% | NoneType errors, missing checks |
| State Management | 25% | Wrong state, stale data, mutations |
| Race Conditions | 20% | Timing, async, concurrent access |

## Quick Assessment (60 sec)

### Step 1: Reproduce the Bug

```python
# Get a minimal reproduction case
# What input causes the bug?
# What output is expected vs actual?

# Document the case:
input_data = [...]
expected = "..."
actual = function(input_data)
assert actual == expected, f"Got {actual}"
```

### Step 2: Classify the Bug

```
Q: Does it fail consistently or intermittently?
→ Consistent: Logic error, boundary issue
→ Intermittent: Race condition, timing, state

Q: Does it fail with edge cases only?
→ Yes: Boundary handling, null checks
→ No: Core algorithm issue

Q: Has it worked before?
→ Yes (regression): Find what changed
→ No (new code): Review algorithm
```

## Debugging Methodology

### The Scientific Method

```python
# 1. OBSERVE: What exactly is happening?
print(f"Input: {input_data}")
print(f"Expected: {expected}")
print(f"Actual: {actual}")

# 2. HYPOTHESIZE: Why might this happen?
# - Off-by-one in range?
# - Missing null check?
# - Wrong operator?

# 3. TEST: Add diagnostic output
def function_debug(data):
    print(f"Step 1: {data}")
    result = step1(data)
    print(f"After step 1: {result}")
    # ... continue tracing

# 4. CONCLUDE: Identify the exact failure point
```

### Binary Search Debugging

```python
# When you don't know where the bug is:

def complex_function(data):
    a = step_a(data)     # Insert print here
    b = step_b(a)        # Is b correct?
    c = step_c(b)        # Check c
    d = step_d(c)        
    return step_e(d)     # If result wrong, work backwards

# Add checkpoints at midpoint, then narrow down
```

## Solution Steps by Category

### Off-by-one Errors

**Common Patterns**
```python
# WRONG: Excludes last element
for i in range(len(items) - 1):  # Missing last
    process(items[i])

# RIGHT: Include all elements
for i in range(len(items)):
    process(items[i])

# WRONG: Index out of bounds
for i in range(len(items)):
    compare(items[i], items[i + 1])  # Fails at last

# RIGHT: Stop one early when comparing pairs
for i in range(len(items) - 1):
    compare(items[i], items[i + 1])
```

**Boundary Checks**
```python
# WRONG: Doesn't handle empty
def get_first(items):
    return items[0]  # IndexError if empty

# RIGHT: Check boundary
def get_first(items):
    if not items:
        return None
    return items[0]

# WRONG: Fence post error
def count_segments(points):
    return len(points)  # Should be len(points) - 1

# RIGHT: Segments = points - 1
def count_segments(points):
    return len(points) - 1 if len(points) > 1 else 0
```

**Range Fixes**
```python
# WRONG: Exclusive when should be inclusive
if value > min and value < max:  # Excludes boundaries

# RIGHT: Inclusive bounds
if value >= min and value <= max:  # Includes boundaries

# Alternative: Use explicit comparison
if min <= value <= max:  # Python's chained comparison
```

### Null/None Handling

**Defensive Checks**
```python
# WRONG: Assumes value exists
def process(data):
    return data["key"]["nested"]  # KeyError or NoneType

# RIGHT: Check at each level
def process(data):
    if not data:
        return None
    if "key" not in data:
        return None
    if "nested" not in data["key"]:
        return None
    return data["key"]["nested"]

# BETTER: Use get() with defaults
def process(data):
    return data.get("key", {}).get("nested")
```

**Optional Chaining Pattern**
```python
# Helper for deep access
def safe_get(obj, *keys, default=None):
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            obj = getattr(obj, key, None)
    return obj if obj is not None else default

# Usage
value = safe_get(data, "user", "profile", "name", default="Unknown")
```

**None in Collections**
```python
# WRONG: None in list causes issues
items = [1, None, 3]
total = sum(items)  # TypeError

# RIGHT: Filter None values
items = [1, None, 3]
total = sum(x for x in items if x is not None)

# Or with explicit filter
total = sum(filter(None, items))  # Note: also filters 0!
```

### State Management

**Mutable Default Arguments**
```python
# WRONG: Mutable default shared across calls
def add_item(item, items=[]):  # Bug! Same list reused
    items.append(item)
    return items

# RIGHT: Use None as default
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

**Unintended Mutation**
```python
# WRONG: Mutates input
def process(data):
    data["processed"] = True  # Modifies original!
    return data

# RIGHT: Work on a copy
def process(data):
    result = data.copy()  # Shallow copy
    result["processed"] = True
    return result

# For nested structures
import copy
def process(data):
    result = copy.deepcopy(data)
    result["nested"]["value"] = True
    return result
```

**Stale State**
```python
# WRONG: Caching without invalidation
_cache = {}
def get_value(key):
    if key not in _cache:
        _cache[key] = expensive_fetch(key)
    return _cache[key]  # Never updates!

# RIGHT: Cache with expiry
from functools import lru_cache
from time import time

@lru_cache(maxsize=100)
def get_value_cached(key, cache_time):
    return expensive_fetch(key)

def get_value(key):
    # Expires every hour
    cache_time = int(time() / 3600)
    return get_value_cached(key, cache_time)
```

### Race Conditions

**Diagnosis**
```python
# Signs of race condition:
# - Works in debugger, fails at full speed
# - "Works on my machine"
# - Intermittent failures
# - Only fails under load
```

**Threading Issues**
```python
# WRONG: Unsynchronized access
counter = 0

def increment():
    global counter
    counter += 1  # Not atomic!

# RIGHT: Use threading lock
from threading import Lock

counter = 0
counter_lock = Lock()

def increment():
    global counter
    with counter_lock:
        counter += 1
```

**Async Issues**
```python
# WRONG: Shared mutable state in async
results = []

async def fetch_and_store(url):
    data = await fetch(url)
    results.append(data)  # Race condition!

# RIGHT: Use asyncio-safe structures
import asyncio

async def fetch_all(urls):
    tasks = [fetch(url) for url in urls]
    return await asyncio.gather(*tasks)  # Returns list safely
```

**Time-of-check to Time-of-use (TOCTOU)**
```python
# WRONG: Check then act (race window)
if os.path.exists(path):
    with open(path) as f:  # File might be deleted!
        data = f.read()

# RIGHT: Try/except (atomic operation)
try:
    with open(path) as f:
        data = f.read()
except FileNotFoundError:
    data = None
```

## Edge Case Identification

### Systematic Edge Cases

```python
# For numeric inputs:
test_cases = [
    0,          # Zero
    1,          # One
    -1,         # Negative one
    MAX_INT,    # Maximum
    MIN_INT,    # Minimum
    0.5,        # Fractional (if applicable)
]

# For collections:
test_cases = [
    [],         # Empty
    [x],        # Single element
    [x, y],     # Two elements
    [x] * 1000, # Large
    [None],     # Contains None
    [same] * n, # All same value
]

# For strings:
test_cases = [
    "",         # Empty
    "x",        # Single char
    " ",        # Whitespace
    "emoji🎉",  # Unicode
    "a" * 10000,# Long
]
```

### Test-First Verification

```python
# Write the failing test first
def test_edge_case():
    assert function([]) == expected_empty_result
    assert function([single]) == expected_single_result
    assert function(None) == expected_none_result

# Then fix the code until tests pass
```

## Validation Steps

### Pre-Fix Validation

```bash
# 1. Write failing test case
pytest tests/test_bug.py::test_specific_case -v

# 2. Confirm it fails
# Expected: FAILED

# 3. Understand why it fails
pytest tests/test_bug.py::test_specific_case -v --tb=long
```

### Post-Fix Validation

```bash
# 1. Verify the specific fix
pytest tests/test_bug.py::test_specific_case -v

# 2. Run related tests
pytest tests/test_module.py -v

# 3. Run full test suite (check for regressions)
pytest

# 4. Test edge cases manually
python -c "from module import func; print(func(edge_case))"
```

## Escalation Criteria

### Escalate When

- Root cause is unclear after 15 minutes of investigation
- Fix requires architectural changes
- Bug involves complex concurrency/threading
- Performance regression from fix
- Affects multiple systems/modules

### Information to Gather

```
1. Minimal reproduction case
2. Expected vs actual behavior
3. What has been tried
4. When did it start (commit/change)?
5. Is it environment-specific?
6. Frequency (always, sometimes, rarely)
```

## Quick Reference

### Common Bug Patterns

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Wrong last element | Off-by-one in range | `range(len(x))` vs `range(len(x)-1)` |
| NoneType error | Missing null check | Add `if x is None` guards |
| Works then fails | State mutation | Check for shared mutable state |
| Intermittent failure | Race condition | Add locks or use atomic operations |
| Wrong on boundaries | Inclusive vs exclusive | Check `<` vs `<=` |

### Debug Print Template

```python
def debug_function(arg):
    print(f"=== DEBUG {function.__name__} ===")
    print(f"Input: {arg!r}")
    
    result = original_logic(arg)
    
    print(f"Output: {result!r}")
    print(f"Type: {type(result)}")
    print("=" * 40)
    
    return result
```

### Quick Hypothesis Checklist

```
[ ] Off-by-one error in loop/range?
[ ] Missing None/empty check?
[ ] Wrong comparison operator (< vs <=)?
[ ] Mutating input instead of copying?
[ ] Mutable default argument?
[ ] Shared state between calls?
[ ] Integer division instead of float?
[ ] String comparison instead of numeric?
```
