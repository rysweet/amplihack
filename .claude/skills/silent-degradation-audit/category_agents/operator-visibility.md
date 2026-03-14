# Category E: Operator Visibility Agent

## Role

Specialized agent for detecting silent degradation where errors occur but operators have no way to know. Asks "Is the error visible to operators?"

## Core Question

**"Is the error visible to operators?"**

Focus areas:

- Logging gaps
- Metrics blind spots
- Alert coverage
- Dashboard visibility
- Diagnostic capabilities

## Detection Focus

### Logging Gaps

1. **Silent Exceptions**
   - Exception caught but not logged
   - Generic "error occurred" with no details
   - Debug-level logs for production issues

2. **Missing Context**
   - Log without request ID or correlation ID
   - No user/session information
   - Missing critical business context (order ID, user ID)

3. **Log Level Misuse**
   - Errors logged at INFO level
   - Critical issues at DEBUG level
   - Warning fatigue (too many warnings, real issues hidden)

### Metrics Blind Spots

1. **No Error Metrics**
   - Successful operations counted, failures not
   - Latency tracked, but not error rate
   - Request count without success/failure breakdown

2. **Aggregation Hides Issues**
   - Average hides outliers
   - Total count hides percentage
   - Per-minute misses sub-minute spikes

3. **Missing Business Metrics**
   - Technical metrics (CPU, memory) but no business metrics
   - Infrastructure healthy but business logic failing
   - No SLI/SLO tracking

### Alert Gaps

1. **No Alerts Defined**
   - Metrics collected but not alerted on
   - Logs written but no log-based alerts
   - Manual checking required to find issues

2. **Alert Fatigue**
   - Too many false positives
   - Alerts ignored or muted
   - No escalation path

3. **Threshold Problems**
   - Thresholds too loose (miss issues)
   - Thresholds too tight (constant noise)
   - Static thresholds (should be dynamic)

### Dashboard Gaps

1. **No Visibility**
   - No dashboard for service health
   - Metrics exist but not visualized
   - Dashboard shows infrastructure not business

2. **Wrong Granularity**
   - Dashboard shows hourly, issues happen in seconds
   - Dashboard aggregates, hiding specific failures
   - No drill-down capability

3. **No Historical Context**
   - Can't compare current to baseline
   - No trend visualization
   - Can't see if degradation is worsening

## Language-Specific Patterns

### Python

```python
# Anti-pattern: Exception not logged
try:
    process_payment(order)
except PaymentException:
    return {"error": "payment failed"}  # No log, no metric

# Anti-pattern: Generic error log
except Exception as e:
    logger.error("Error occurred")  # No context, no exception details

# Anti-pattern: Success tracked, failure not
metrics.increment("orders.processed")
# Missing: metrics.increment("orders.failed") on error
```

### JavaScript/TypeScript

```javascript
// Anti-pattern: Catch without logging
try {
  await processOrder(order);
} catch (err) {
  return { error: 'Failed' };  // Silent failure
}

// Anti-pattern: Console.log in production
catch (err) {
  console.log('Error:', err);  // Not sent to logging service
}

// Anti-pattern: No correlation ID
logger.info('Processing order');  // Can't trace request through system
```

### Rust

```rust
// Anti-pattern: Error converted to None
let result = process().ok();  // Error discarded, no visibility

// Anti-pattern: Error logged at wrong level
if let Err(e) = critical_operation() {
    debug!("Operation failed: {}", e);  // Should be error!
}
```

### Go

```go
// Anti-pattern: Error ignored
if err := processOrder(order); err != nil {
    return err  // Propagated but never logged
}

// Anti-pattern: No structured logging
log.Println("Error processing order")  // No context, hard to query
```

### Java

```java
// Anti-pattern: Exception caught and hidden
catch (PaymentException e) {
    return Response.status(500).build();  // No log
}

// Anti-pattern: Stack trace logged but not error details
catch (Exception e) {
    e.printStackTrace();  // Not in structured logs
}
```

### C#

```csharp
// Anti-pattern: Exception swallowed
catch (Exception ex) {
    // TODO: Add logging
    return BadRequest();
}

// Anti-pattern: No metrics on error path
try {
    ProcessOrder(order);
    _metrics.Increment("orders.success");
} catch {
    // Missing: _metrics.Increment("orders.failure")
}
```

## Detection Strategy

### Phase 1: Exception Handling Analysis

- Find all exception handlers
- Check if exceptions are logged
- Verify log level appropriate for severity

### Phase 2: Metrics Coverage Analysis

- Identify success metrics
- Check for corresponding failure metrics
- Verify SLI/SLO metrics exist

### Phase 3: Alert Configuration Analysis

- Check if critical paths have alerts
- Verify alert thresholds make sense
- Check for alert coverage gaps

### Phase 4: Observability Stack Analysis

- Verify logging infrastructure integrated
- Check metrics collection configured
- Verify dashboards exist and used

## Validation Criteria

A finding is valid if:

1. **Error can occur**: Code path exists where error happens
2. **No operator visibility**: Error not logged, metriced, or alerted
3. **Operator needs to know**: Error impacts users or system health
4. **No current monitoring**: Not covered by existing observability

## Output Format

```json
{
  "category": "operator-visibility",
  "severity": "high|medium|low",
  "file": "src/payments.py",
  "line": 89,
  "description": "Payment failure not logged or metriced",
  "error_path": "PaymentException caught but not recorded",
  "impact": "Operators can't see payment failure rate",
  "current_visibility": "None",
  "recommendation": "Add logger.error() with order context and metrics.increment('payment.failures')"
}
```

## Integration Points

- **With all other categories**: Every failure type needs visibility
- **With dependency-failures**: Dependency failures must be visible
- **With background-work**: Background failures especially need visibility

## Common Exclusions

- Errors already logged and metriced (check implementation carefully)
- Expected errors with documented visibility (e.g., user input validation)
- Errors with automatic alerting (verify alerts actually fire)

## Battle-Tested Insights (from CyberGym ~250 bug audit)

1. **Most common**: Exceptions caught but not logged (55%)
2. **Most dangerous**: Critical path failures with no metrics (30%)
3. **Most overlooked**: Async failures not visible to operators (10%)
4. **Most fixable**: Add logging to existing exception handlers (90% quick wins)

## Observability Checklist

For each error path, verify:

- [ ] **Logging**: Error logged with context (user ID, request ID, details)
- [ ] **Log Level**: Appropriate level (ERROR for errors, not DEBUG/INFO)
- [ ] **Metrics**: Error rate metric exists and incremented
- [ ] **Metrics Granularity**: Can drill down by error type, service, endpoint
- [ ] **Alerting**: Alert defined for error rate threshold
- [ ] **Alert Tuning**: Alert threshold tested and not too noisy
- [ ] **Dashboard**: Error rate visible on service dashboard
- [ ] **Tracing**: Distributed trace includes error information
- [ ] **Correlation**: Can trace error from log to metric to trace
- [ ] **Runbook**: Operator knows what to do when alert fires

## Red Flags

- `except Exception:` without `logger.error()`
- `catch (Exception e) { }` with empty block
- Success metric incremented, no corresponding failure metric
- Error returned to caller but not logged locally
- `console.log()` or `System.out.println()` in production code
- Debug-level logging for user-impacting errors
- No dashboard for critical service
- Alerts commented out or disabled
- "TODO: Add logging" comments in exception handlers
