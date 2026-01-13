# Debugging

Systematic debugging methodology for efficiently identifying and fixing software defects.

## When to Use

- Unexpected behavior or errors occurring
- Tests failing for unclear reasons
- Production issues need investigation
- Performance problems to diagnose
- Understanding unfamiliar code behavior

## The Scientific Debugging Method

### 1. Observe

```
Gather all available information:
- What is the exact error message?
- What is the expected behavior?
- What is the actual behavior?
- When did it start happening?
- Is it reproducible? How often?
- What changed recently?
```

### 2. Hypothesize

```
Form specific, testable hypotheses:
- "The null pointer occurs because X is not initialized when Y happens"
- "The timeout happens because the connection pool is exhausted"
- "The wrong result occurs because the sort is unstable"

NOT vague guesses:
- "Something is wrong with the database"
- "It might be a race condition"
```

### 3. Predict

```
Before testing, predict what you'll see:
- "If my hypothesis is correct, adding a log here will show X"
- "If the pool is exhausted, increasing pool size will fix it"
- "If the sort is unstable, using stable sort will give correct results"
```

### 4. Test

```
Run the smallest experiment that tests your hypothesis:
- Add targeted logging
- Modify one variable
- Isolate the component
- Create a minimal reproduction
```

### 5. Analyze

```
Compare results to predictions:
- Hypothesis confirmed → Fix the issue
- Hypothesis rejected → Form new hypothesis based on data
- Inconclusive → Design better experiment
```

## Binary Search for Bug Location

When you know a bug exists but not where:

### Git Bisect (for regression bugs)

```bash
# Start bisect
git bisect start

# Mark current (buggy) commit as bad
git bisect bad

# Mark known good commit
git bisect good abc123

# Git checks out middle commit - test it
# If bad:
git bisect bad

# If good:
git bisect good

# Repeat until Git identifies the first bad commit
# Reset when done
git bisect reset
```

### Automated Git Bisect

```bash
# With a test script that exits 0 for good, 1 for bad
git bisect start HEAD known_good_commit
git bisect run ./test_script.sh
```

### Code Binary Search

```python
# When bug is in a function, not a commit
def problematic_function(data):
    result1 = step1(data)
    print(f"After step1: {result1}")  # Check here first
    
    result2 = step2(result1)
    print(f"After step2: {result2}")  # Then here
    
    result3 = step3(result2)
    print(f"After step3: {result3}")  # Then here
    
    return step4(result3)

# If wrong after step2, binary search within step2
# Continue until you find the exact line
```

### Data Binary Search

```python
# When bug occurs with certain data
def find_bad_record(records):
    """Binary search to find which record causes the bug."""
    if len(records) == 1:
        return records[0]
    
    mid = len(records) // 2
    first_half = records[:mid]
    
    try:
        process(first_half)
        # Bug is in second half
        return find_bad_record(records[mid:])
    except:
        # Bug is in first half
        return find_bad_record(first_half)
```

## Logging Strategies

### Strategic Log Placement

```python
import logging

logger = logging.getLogger(__name__)

def complex_operation(input_data):
    # Log entry with context
    logger.info(f"Starting operation", extra={
        'input_size': len(input_data),
        'input_type': type(input_data).__name__
    })
    
    try:
        # Log before critical steps
        logger.debug(f"Validating input")
        validated = validate(input_data)
        
        # Log state changes
        logger.debug(f"Processing {len(validated)} items")
        result = process(validated)
        
        # Log success with metrics
        logger.info(f"Operation completed", extra={
            'result_size': len(result),
            'duration_ms': elapsed_ms
        })
        return result
        
    except ValidationError as e:
        # Log expected errors at appropriate level
        logger.warning(f"Validation failed: {e}")
        raise
        
    except Exception as e:
        # Log unexpected errors with full context
        logger.exception(f"Unexpected error in operation")
        raise
```

### Temporary Debug Logging

```python
# Add these for debugging, remove after

# 1. Entry/exit tracing
def debug_function(func):
    def wrapper(*args, **kwargs):
        print(f">>> Entering {func.__name__}")
        print(f"    Args: {args}, Kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            print(f"<<< Exiting {func.__name__}: {result}")
            return result
        except Exception as e:
            print(f"!!! Exception in {func.__name__}: {e}")
            raise
    return wrapper

# 2. Variable inspection
def debug_vars(**kwargs):
    """Print variables with their names."""
    import inspect
    frame = inspect.currentframe().f_back
    print(f"[{frame.f_code.co_filename}:{frame.f_lineno}]")
    for name, value in kwargs.items():
        print(f"  {name} = {value!r} (type: {type(value).__name__})")

# Usage: debug_vars(x=x, result=result)

# 3. Conditional breakpoint
if some_condition:
    import pdb; pdb.set_trace()
```

### Log Levels Guide

```
CRITICAL - System is unusable
  "Database connection pool exhausted, cannot serve requests"

ERROR - Operation failed, needs attention
  "Failed to process payment for order #123"

WARNING - Something unexpected, but handled
  "Retry 2/3 for API call to external-service"

INFO - Normal operations, audit trail
  "User alice@example.com logged in"

DEBUG - Detailed diagnostic information
  "Cache miss for key user:123, fetching from database"
```

## Common Debugging Tools

### Python

```python
# Built-in debugger
import pdb; pdb.set_trace()  # Breakpoint (old way)
breakpoint()  # Python 3.7+ (preferred)

# pdb commands:
# n - next line
# s - step into
# c - continue
# p expr - print expression
# l - list source
# w - where (stack trace)
# q - quit

# Better debuggers
# pip install ipdb  # IPython debugger
import ipdb; ipdb.set_trace()

# pip install pudb  # Visual TUI debugger
import pudb; pudb.set_trace()

# Profiling
import cProfile
cProfile.run('main()', 'output.prof')

# Memory profiling
# pip install memory_profiler
from memory_profiler import profile
@profile
def memory_intensive_function():
    pass
```

### JavaScript/Node

```javascript
// Built-in debugger
debugger;  // Breakpoint

// Node.js inspection
// node --inspect script.js
// node --inspect-brk script.js  // Break on first line

// Console methods
console.log(variable);
console.dir(object, { depth: null });  // Deep print
console.table(arrayOfObjects);  // Table format
console.trace();  // Stack trace
console.time('label'); /* code */ console.timeEnd('label');
```

### Shell/System

```bash
# Trace system calls
strace -f -p PID

# Trace library calls
ltrace command

# Watch file changes
watch -n 1 'ls -la /path/to/file'

# Monitor process
top -p PID
htop -p PID

# Network debugging
tcpdump -i any port 8080
netstat -tlnp
lsof -i :8080

# Disk I/O
iotop
iostat -x 1
```

## Debugging Checklists

### General Debugging Checklist

```
[ ] Can I reproduce the bug consistently?
[ ] What is the minimal reproduction case?
[ ] What are the exact error messages?
[ ] What does the stack trace tell me?
[ ] What changed recently (code, config, data)?
[ ] Does it happen in all environments?
[ ] Have I checked the logs?
[ ] Is this a known issue (search codebase, issues)?
```

### "It Works On My Machine" Checklist

```
[ ] Same code version? (git status, git log)
[ ] Same dependencies? (pip freeze, npm list)
[ ] Same configuration? (.env, config files)
[ ] Same data? (database state, fixtures)
[ ] Same environment? (OS, runtime version)
[ ] Same resources? (memory, disk, network)
```

### Intermittent Bug Checklist

```
[ ] Race condition? (timing, concurrency)
[ ] Resource exhaustion? (memory, connections)
[ ] External dependency? (network, API)
[ ] Time-based? (timezone, clock skew)
[ ] Data-dependent? (specific input patterns)
[ ] Load-dependent? (only under traffic)
[ ] Cache-related? (stale data, eviction)
```

### Performance Bug Checklist

```
[ ] What's the baseline performance?
[ ] Where is time being spent? (profiling)
[ ] N+1 query problem?
[ ] Missing indexes?
[ ] Unnecessary computation in loops?
[ ] Memory leaks?
[ ] Blocking I/O in async code?
[ ] Cache misses?
```

## Debugging Patterns

### Rubber Duck Debugging

```
1. Explain the code line by line to an inanimate object
2. Describe what each line SHOULD do
3. When explanation doesn't match behavior, you've found the bug
4. The act of articulating forces careful thinking
```

### Wolf Fence Algorithm

```
1. Put a "fence" in the middle of the code
2. Determine which side the "wolf" (bug) is on
3. Put a fence in the middle of that half
4. Repeat until you find the bug
5. Implementation: strategic print/log statements
```

### Delta Debugging

```
1. Start with failing input and passing input
2. Find the minimal difference that causes failure
3. Reduce the failing case systematically
4. Often reveals the exact condition triggering the bug
```

### Time Travel Debugging

```
1. Start from a known good state
2. Step through execution chronologically
3. Note the exact point where state becomes invalid
4. Often more effective than starting from the error

Tools:
- rr (record and replay for Linux)
- Chrome DevTools timeline
- Git bisect for regression
```

## Common Bug Categories

| Category | Symptoms | Investigation |
|----------|----------|---------------|
| Null/Undefined | TypeError, NullPointerException | Check all access paths |
| Off-by-one | Wrong count, missing item | Check loop bounds, indexing |
| Race condition | Intermittent, timing-dependent | Add logging with timestamps |
| Resource leak | Gradual degradation | Monitor handles, connections |
| Encoding | Garbled text, special chars fail | Check encoding at boundaries |
| Timezone | Wrong times, date math errors | Log timestamps with timezone |
| Floating point | Comparison fails, accumulated error | Use decimal or epsilon compare |

## Emergency Production Debugging

```bash
# Quick health check
curl -s http://localhost:8080/health | jq .

# Recent logs
tail -f /var/log/app/error.log
journalctl -u app -f

# Resource usage
top -bn1 | head -20
df -h
free -m

# Network connections
netstat -tlnp | grep :8080
ss -s

# Quick process inspection
ps aux | grep python
pgrep -a python

# Dump thread stacks (Python)
kill -USR1 <pid>  # If signal handler installed

# Enable debug logging temporarily
curl -X POST http://localhost:8080/admin/log-level -d 'level=DEBUG'
```
