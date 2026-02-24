# Category C: Background Work Agent

## Role

Specialized agent for detecting silent degradation in asynchronous, background, and scheduled work. Asks "What happens when background work fails?"

## Core Question

**"What happens when background work fails?"**

Where "background work" includes:

- Async tasks and futures
- Message queue consumers
- Cron jobs and scheduled tasks
- Background threads and workers
- Event handlers and callbacks
- Webhook receivers

## Detection Focus

### Async Task Failures

1. **Fire-and-Forget**
   - Tasks launched without awaiting result
   - Exceptions in async context not caught
   - No retry or error handling

2. **Promise/Future Abandonment**
   - Promises created but never awaited
   - Futures dropped without checking result
   - Async operations assumed to succeed

3. **Callback Failures**
   - Exception in callback handler ignored
   - Callback registration failures silent
   - No timeout on callback execution

### Queue Processing Failures

1. **Message Loss**
   - Message acknowledged before processing
   - Processing failure doesn't requeue
   - Dead letter queue silently accumulating

2. **Consumer Failures**
   - Consumer crashes without alerting
   - Consumer stalls (no messages processed)
   - Poison messages block queue

3. **Batch Processing**
   - Partial batch success treated as full success
   - Individual item failures not tracked
   - No visibility into batch progress

### Scheduled Work Failures

1. **Cron Job Failures**
   - Job fails but cron continues
   - Job never runs (bad schedule)
   - Job runs but takes no action

2. **Timer-Based Work**
   - Timer fires but handler fails
   - Timer stops firing (uncaught exception)
   - Timer drift (expected hourly, actually every 90 minutes)

3. **Event Polling**
   - Polling loop stops but system continues
   - Events processed but handlers fail
   - Event backlog growing without visibility

## Language-Specific Patterns

### Python

```python
# Anti-pattern: Fire-and-forget async
async def process_data():
    asyncio.create_task(expensive_operation())  # No await, no error handling

# Anti-pattern: Thread exception ignored
def background_worker():
    try:
        while True:
            process_item()
    except Exception:
        pass  # Thread dies silently

# Anti-pattern: Celery task failure silent
@app.task
def process_order(order_id):
    # If this fails, no one knows unless explicitly checking
    process_payment(order_id)
```

### JavaScript/TypeScript

```javascript
// Anti-pattern: Promise not awaited
async function handler() {
  processInBackground(); // Returns promise, not awaited
}

// Anti-pattern: Catch without logging
queue.on("message", async (msg) => {
  try {
    await process(msg);
  } catch {
    // Silent failure, message lost
  }
});

// Anti-pattern: Event handler failure ignored
emitter.on("event", (data) => {
  dangerousOperation(data); // Throws, event emitter continues
});
```

### Rust

```rust
// Anti-pattern: Task spawned without join
tokio::spawn(async {
    dangerous_operation().await  // Panic not visible
});

// Anti-pattern: Background task result ignored
let handle = thread::spawn(|| {
    process_forever()  // Error not checked
});
// handle never joined
```

### Go

```go
// Anti-pattern: Goroutine panic not recovered
go func() {
    processMessages()  // Panic kills goroutine, silent
}()

// Anti-pattern: Error channel not read
errCh := make(chan error)
go func() {
    errCh <- processData()  // If no reader, goroutine blocks
}()
```

### Java

```java
// Anti-pattern: ExecutorService exception ignored
executor.submit(() -> {
    processItem();  // Exception caught by Future, never checked
});

// Anti-pattern: @Async method failure silent
@Async
public void processOrder(Order order) {
    // Exception here is logged but not surfaced
    paymentService.charge(order);
}
```

### C#

```c#
// Anti-pattern: Fire-and-forget Task
Task.Run(() => ProcessData());  // Exception not observed

// Anti-pattern: Background service failure hidden
protected override async Task ExecuteAsync(CancellationToken token) {
    try {
        await ProcessForever(token);
    } catch {
        // Service stops, no one notified
    }
}
```

## Detection Strategy

### Phase 1: Async Pattern Analysis

- Find async functions that return unawaited tasks
- Check for fire-and-forget patterns
- Identify callback registrations without error handlers

### Phase 2: Queue Integration Analysis

- Locate message queue consumers
- Check acknowledgment vs. processing order
- Verify dead letter queue monitoring

### Phase 3: Scheduled Work Analysis

- Find cron job definitions
- Check timer and polling implementations
- Verify health checks for scheduled work

### Phase 4: Error Propagation Analysis

- Check if background errors are logged
- Verify metrics for background task success/failure
- Identify alerting for background work issues

## Validation Criteria

A finding is valid if:

1. **Failure is silent**: Background work fails with no immediate visibility
2. **No retry or recovery**: Failure is permanent with no remediation
3. **No monitoring**: No metrics, logs, or alerts for the failure
4. **Impact unclear**: Can't determine if background work is healthy

## Output Format

```json
{
  "category": "background-work",
  "severity": "high|medium|low",
  "file": "path/to/worker.py",
  "line": 67,
  "description": "Celery task failure not monitored or retried",
  "impact": "Order processing silently fails, customer never charged",
  "visibility": "Task shows failed in Celery but no alert",
  "recommendation": "Add metrics for task success/failure rate and alert on threshold"
}
```

## Integration Points

- **With operator-visibility**: Background failures must be visible
- **With test-effectiveness**: Tests should verify background work failures
- **With dependency-failures**: Background work often depends on external services

## Common Exclusions

- Best-effort background work (explicitly documented as optional)
- Background work with explicit monitoring (metrics + alerts)
- Fire-and-forget patterns with clear documentation

## Battle-Tested Insights (from CyberGym ~250 bug audit)

1. **Most common**: Fire-and-forget async without error handling (45%)
2. **Most dangerous**: Queue consumers dying silently (30%)
3. **Most overlooked**: Cron jobs failing without alerting (15%)
4. **Most fixable**: Add try/catch with logging in background handlers (85% quick wins)

## Red Flags

- `asyncio.create_task()` without await or exception handler
- Thread/goroutine spawned without join/panic recovery
- Message acknowledged before processing complete
- Cron job with no health check or monitoring
- Executor service submit() without future check
- Background task with no success/failure metrics
