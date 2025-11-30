# Dynamic Debugger Patterns

Production-ready debugging patterns, best practices, and common pitfalls fer all supported languages.

## Architectural Patterns

### Pattern 1: Checkpoint Debugging

**Problem:** Long-running processes where bugs occur after minutes of execution

**Solution:** Set strategic breakpoints at checkpoints and inspect state

```python
# Python example
async def process_pipeline(data):
    # Checkpoint 1: Input validation
    validated = await validate_data(data)  # Breakpoint here

    # Checkpoint 2: Transformation
    transformed = await transform_data(validated)  # Breakpoint here

    # Checkpoint 3: Enrichment
    enriched = await enrich_data(transformed)  # Breakpoint here

    # Checkpoint 4: Output
    result = await save_data(enriched)  # Breakpoint here
    return result
```

**Debugging Strategy:**

1. Set breakpoints at all checkpoints
2. Run until first checkpoint
3. Verify state matches expectations
4. Continue to next checkpoint
5. Identify which stage introduces corruption

**When to Use:** Multi-stage pipelines, ETL processes, data transformations

### Pattern 2: Conditional Breakpoints

**Problem:** Bug only occurs for specific input values

**Solution:** Set breakpoints with conditions to stop only when criteria met

```javascript
// JavaScript example
function processOrder(order) {
  // Stop only for high-value orders
  // Conditional breakpoint: order.total > 10000
  if (order.total > 10000) {
    validateHighValueOrder(order);
  }

  // Stop only for specific customer
  // Conditional breakpoint: order.customerId === 12345
  chargeCustomer(order.customerId, order.total);
}
```

**API Syntax:**

```json
{
  "tool": "dap_set_breakpoints",
  "arguments": {
    "source": { "path": "orders.js" },
    "breakpoints": [
      {
        "line": 4,
        "condition": "order.total > 10000"
      },
      {
        "line": 9,
        "condition": "order.customerId === 12345"
      }
    ]
  }
}
```

**When to Use:** Rare bugs, edge cases, production debugging

### Pattern 3: Watch Point Debugging

**Problem:** Variable changes unexpectedly, don't know where

**Solution:** Set watch expression to break when variable changes

```cpp
// C++ example
class UserManager {
private:
    int user_count = 0;  // Watch this variable

public:
    void addUser(User* user) {
        users.push_back(user);
        user_count++;  // Watch breaks here when user_count changes
    }

    void removeUser(int id) {
        // ... removal logic
        user_count--;  // And here
    }
};
```

**API Syntax:**

```json
{
  "tool": "dap_set_data_breakpoints",
  "arguments": {
    "breakpoints": [
      {
        "dataId": "user_count",
        "accessType": "write"
      }
    ]
  }
}
```

**When to Use:** Unexpected state changes, corruption bugs, race conditions

### Pattern 4: Exception Breakpoints

**Problem:** Exception thrown but stack trace doesn't show origin

**Solution:** Break on all exceptions or specific exception types

```rust
// Rust example
fn process_payment(amount: f64) -> Result<Payment, PaymentError> {
    // Break on all panics
    if amount <= 0.0 {
        panic!("Invalid amount: {}", amount);  // Debugger breaks here
    }

    // Break on specific Result::Err types
    let validation = validate_amount(amount)?;  // Break on PaymentError

    Ok(Payment::new(amount))
}
```

**API Syntax:**

```json
{
  "tool": "dap_set_exception_breakpoints",
  "arguments": {
    "filters": ["raised", "uncaught"],
    "exceptionOptions": [
      {
        "path": [{ "names": ["PaymentError"] }],
        "breakMode": "always"
      }
    ]
  }
}
```

**When to Use:** Exception debugging, panic investigation, error propagation tracking

## Performance Debugging Patterns

### Pattern 5: Hot Path Analysis

**Problem:** Know code is slow, don't know which part

**Solution:** Profile execution with timed breakpoints

```go
// Go example
func processOrders(orders []Order) {
    // Timed checkpoint 1
    start := time.Now()
    validated := validateOrders(orders)
    fmt.Printf("Validation took: %v\n", time.Since(start))  // Breakpoint here

    // Timed checkpoint 2
    start = time.Now()
    transformed := transformOrders(validated)
    fmt.Printf("Transform took: %v\n", time.Since(start))  // Breakpoint here

    // Timed checkpoint 3
    start = time.Now()
    saved := saveOrders(transformed)
    fmt.Printf("Save took: %v\n", time.Since(start))  // Breakpoint here
}
```

**Debugging Strategy:**

1. Add timing checkpoints throughout code
2. Run with breakpoints at each checkpoint
3. Inspect timing values at each stop
4. Identify slowest stages
5. Drill down into slow stages with more granular breakpoints

**When to Use:** Performance issues, latency debugging, optimization

### Pattern 6: Memory Leak Detection

**Problem:** Memory usage grows over time, can't find leak

**Solution:** Compare memory snapshots at checkpoints

```cpp
// C++ example
class ConnectionPool {
private:
    std::vector<Connection*> connections;

public:
    void processRequests() {
        for (int i = 0; i < 1000; i++) {
            // Checkpoint: Check connections.size()
            Connection* conn = createConnection();  // Breakpoint here

            handleRequest(conn);

            // Checkpoint: Check connections.size() again
            // BUG: conn not released!  // Breakpoint here
        }
    }
};
```

**Debugging Strategy:**

1. Set breakpoints before and after operations
2. Inspect collection sizes at each breakpoint
3. Verify resources released
4. Look for missing cleanup code

**When to Use:** Memory leaks, resource leaks, growing data structures

## Security Debugging Patterns

### Pattern 7: Input Validation Tracing

**Problem:** SQL injection or XSS vulnerability, need to trace input flow

**Solution:** Track user input through entire flow with breakpoints

```python
# Python example
def create_user(username: str, email: str):
    # Checkpoint 1: Raw input
    print(f"Raw input: {username}, {email}")  # Breakpoint here

    # Checkpoint 2: After validation
    validated_username = validate_username(username)  # Breakpoint here
    validated_email = validate_email(email)  # Breakpoint here

    # Checkpoint 3: Before SQL
    query = f"INSERT INTO users (username, email) VALUES (?, ?)"
    cursor.execute(query, (validated_username, validated_email))  # Breakpoint here
```

**Debugging Strategy:**

1. Inject malicious input (in test environment!)
2. Trace input through validation layers
3. Verify sanitization at each stage
4. Ensure parameterized queries used

**When to Use:** Security audits, vulnerability investigation, input sanitization verification

### Pattern 8: Authentication Flow Debugging

**Problem:** Authentication fails intermittently, need to trace session state

**Solution:** Breakpoint at every authentication checkpoint

```javascript
// JavaScript example
async function authenticateUser(credentials) {
  // Checkpoint 1: Received credentials
  console.log("Credentials:", credentials); // Breakpoint here

  // Checkpoint 2: Database lookup
  const user = await User.findOne({ email: credentials.email }); // Breakpoint here

  // Checkpoint 3: Password verification
  const isValid = await bcrypt.compare(credentials.password, user.passwordHash); // Breakpoint here

  // Checkpoint 4: Session creation
  const session = await createSession(user.id); // Breakpoint here

  // Checkpoint 5: Token generation
  const token = jwt.sign({ userId: user.id, sessionId: session.id }); // Breakpoint here

  return { token, user };
}
```

**When to Use:** Authentication bugs, session management issues, token problems

## Language-Specific Patterns

### Python: Async/Await Debugging

**Pattern 9: Coroutine State Inspection**

```python
import asyncio

async def fetch_data(url):
    # Inspect coroutine state
    async with aiohttp.ClientSession() as session:
        # Breakpoint here: Check session state
        async with session.get(url) as response:
            # Breakpoint here: Check response status
            data = await response.json()
            # Breakpoint here: Check data
            return data

# Debugging async code
async def main():
    # Create task
    task = asyncio.create_task(fetch_data('https://api.example.com'))

    # Breakpoint: Inspect task.done(), task.cancelled()
    result = await task

    # Breakpoint: Verify result
```

**Key Inspections:**

- `task.done()` - Is coroutine finished?
- `task.cancelled()` - Was it cancelled?
- `task.exception()` - Did it raise exception?
- `asyncio.all_tasks()` - View all running tasks

### JavaScript: Promise Chain Debugging

**Pattern 10: Promise State Inspection**

```javascript
function debugPromiseChain() {
  const promise = fetchUser(123)
    .then((user) => {
      // Breakpoint: Check user object
      return fetchOrders(user.id);
    })
    .then((orders) => {
      // Breakpoint: Check orders array
      return processOrders(orders);
    })
    .catch((err) => {
      // Breakpoint: Inspect error
      console.error("Error:", err);
    });

  // Inspect promise state immediately
  console.log("Promise state:", promise); // Breakpoint here

  return promise;
}
```

**Key Inspections:**

- Promise state: pending/fulfilled/rejected
- Promise value or rejection reason
- Stack trace at rejection point

### C++: Memory Debugging

**Pattern 11: Pointer Validation**

```cpp
void processUser(User* user) {
    // Validate pointer before use
    if (user == nullptr) {  // Breakpoint: Check this condition
        throw std::invalid_argument("Null user pointer");
    }

    // Check memory validity (use Valgrind or AddressSanitizer)
    // Breakpoint: Inspect user->name, user->id
    std::cout << "User: " << user->name << std::endl;

    // After operations, check pointer still valid
    // Breakpoint: Verify user not deleted
}
```

**Tools Integration:**

- Use with Valgrind: `valgrind --tool=memcheck ./program`
- Use with AddressSanitizer: Compile with `-fsanitize=address`
- Check for use-after-free, double-free, memory leaks

### Go: Goroutine Debugging

**Pattern 12: Goroutine Lifecycle Tracking**

```go
func processInBackground(ctx context.Context, data []int) {
    var wg sync.WaitGroup
    results := make(chan int, len(data))

    for _, item := range data {
        wg.Add(1)
        go func(val int) {
            defer wg.Done()

            // Breakpoint: Check goroutine ID
            // Use: runtime.Goexit() to see stack
            result := processItem(val)

            // Breakpoint: Check channel state before send
            select {
            case results <- result:
                // Success
            case <-ctx.Done():
                // Context cancelled
                return
            }
        }(item)
    }

    // Breakpoint: Check number of active goroutines
    // Use: runtime.NumGoroutine()
    wg.Wait()
    close(results)
}
```

**Key Inspections:**

- `runtime.NumGoroutine()` - Count active goroutines
- Goroutine state: running/blocked/waiting
- Channel state: buffered count, waiters

### Rust: Ownership Debugging

**Pattern 13: Borrow Checker Issues**

```rust
fn process_data(data: Vec<i32>) -> i32 {
    // Breakpoint: data is owned here
    let sum = calculate_sum(&data);  // Borrow

    // Breakpoint: data still valid (immutable borrow)
    let avg = calculate_avg(&data);  // Another borrow

    // Breakpoint: data still valid
    let result = sum + avg;

    // data dropped here (out of scope)
    result
}

fn handle_move() {
    let data = vec![1, 2, 3];

    // Breakpoint: data valid here
    process_data(data);  // Move ownership

    // Breakpoint: data INVALID here - moved!
    // Cannot use data anymore
}
```

**Key Insights:**

- Owned values: Can be moved or borrowed
- Borrowed values: Cannot be moved while borrowed
- Mutable borrows: Exclusive access
- Immutable borrows: Shared access

## Common Pitfalls

### Pitfall 1: Over-Reliance on Print Debugging

**Problem:** Using print statements instead of proper debugging

**Why It Fails:**

- Clutters codebase with debug prints
- Hard to remove all prints after debugging
- Doesn't show full state, only what you printed
- Performance impact if prints in hot paths

**Solution:** Use proper debugger with breakpoints

### Pitfall 2: Debugging in Production

**Problem:** Setting breakpoints in live production system

**Why It's Dangerous:**

- Pauses execution for all users
- May timeout requests
- Exposes sensitive data in debugger
- Performance impact

**Solution:**

- Debug in staging/development only
- Use logging for production issues
- Use profiling for production performance
- Reproduce bug in development, then debug

### Pitfall 3: Ignoring Stack Traces

**Problem:** Not checking full stack trace when debugging

**Why It Fails:**

- Root cause often several frames up
- Missing context from calling code
- Symptoms appear far from actual bug

**Solution:** Always inspect full stack, work backward from crash

### Pitfall 4: Single-Step Debugging Everything

**Problem:** Stepping through every line of code

**Why It's Inefficient:**

- Wastes huge amounts of time
- Easy to lose context
- May timeout debugging session

**Solution:** Use strategic breakpoints at key locations only

### Pitfall 5: Not Verifying Fixes

**Problem:** Stopping debugger after finding suspected bug

**Why It's Risky:**

- Suspected cause may not be root cause
- Fix may introduce new bugs
- Multiple bugs may have same symptom

**Solution:**

1. Identify suspected bug
2. Verify with test case
3. Apply fix
4. Re-run debugger to confirm fix
5. Add regression test

## Best Practices Summary

### Before Debugging

1. **Reproduce reliably** - Can't debug intermittent bugs
2. **Minimize test case** - Smaller reproduction = faster debugging
3. **Check prerequisites** - Ensure debug symbols compiled in
4. **Review recent changes** - Bug likely in recent code

### During Debugging

1. **Hypothesis-driven** - Form hypothesis, test with breakpoints
2. **Binary search** - Narrow down location with strategic breakpoints
3. **Document findings** - Take notes as you discover things
4. **Stay focused** - Don't get distracted by unrelated issues

### After Debugging

1. **Verify fix** - Run full test suite
2. **Add regression test** - Prevent bug from returning
3. **Clean up** - Remove debug code, temporary changes
4. **Document solution** - Help others who hit same bug

## Advanced Techniques

### Technique 1: Reverse Debugging

**Concept:** Step backward through execution to find bug origin

**Tools:**

- GDB: `record` and `reverse-step` commands
- rr (Record and Replay): Record execution, replay with debugger

**When to Use:** Complex bugs where cause occurs long before symptom

### Technique 2: Time-Travel Debugging

**Concept:** Record entire execution, replay at any point

**Tools:**

- rr for C/C++
- Chronon for Java
- WinDBG Time Travel Debugging for Windows

**When to Use:** Race conditions, heisenbug investigation

### Technique 3: Remote Debugging

**Concept:** Debug code running on different machine

**Setup:**

- Python: `debugpy --listen 0.0.0.0:5678 script.py`
- Node: `node --inspect=0.0.0.0:9229 script.js`
- Go: `dlv attach --headless --listen=:2345 <pid>`

**When to Use:** Container debugging, cloud debugging, embedded systems

## Token Budget Optimization

**Skill overhead should be minimal:**

- Intent detection: <20 tokens (cached patterns)
- Language detection: <30 tokens (cached after first)
- Command orchestration: <50 tokens (direct MCP calls)
- Error messages: <50 tokens (templated responses)

**Total per command: <100 tokens**

**Optimization strategies:**

1. Cache language detection results
2. Use pattern matching for intent (not LLM)
3. Template common error messages
4. Minimize explanation text in responses

---

**Philosophy:** Debugging is about asking the right questions at the right times. Strategic breakpoints beat random single-stepping. The debugger is a precision tool - use it like a surgeon's scalpel, not a lumberjack's axe.
