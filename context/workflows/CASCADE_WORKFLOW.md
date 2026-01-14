---
name: CASCADE_WORKFLOW
version: 1.0.0
description: Graceful degradation workflow with 3-level fallback cascade (primary → secondary → tertiary)
steps: 7
phases:
  - cascade-level-definition
  - primary-attempt
  - secondary-fallback
  - tertiary-guarantee
  - degradation-reporting
  - metrics-logging
  - continuous-optimization
success_criteria:
  - "Tertiary level always succeeds"
  - "Degradation properly reported to user"
  - "Cascade metrics logged for optimization"
  - "System never completely fails"
philosophy_alignment:
  - principle: Resilience
    application: System always completes through graceful degradation
  - principle: User Experience
    application: Better degraded service than error message
  - principle: Transparency
    application: Users understand what they receive at each level
  - principle: Continuous Improvement
    application: Metrics drive timeout and fallback optimization
references:
  workflows:
    - DEFAULT_WORKFLOW.md
customizable: true
---

# Cascade Workflow with Graceful Degradation

This workflow implements graceful degradation through cascading fallback strategies. When optimal approaches fail or timeout, the system automatically falls back to simpler, more reliable alternatives while maintaining acceptable functionality.

> **DEPRECATION WARNING**: Markdown workflows deprecated. See `docs/WORKFLOW_TO_SKILLS_MIGRATION.md`

## Configuration

### Core Parameters

**Timeout Strategy**: How long to wait at each cascade level

- `aggressive` - Fast failures, quick degradation (5s / 2s / 1s)
- `balanced` - Reasonable attempts (30s / 10s / 5s) - DEFAULT
- `patient` - Thorough attempts before fallback (120s / 30s / 10s)
- `custom` - Define your own timeouts

**Fallback Types**: What degrades at each level

- `service` - External API → Cached data → Static defaults
- `quality` - Comprehensive → Standard → Minimal analysis
- `freshness` - Real-time → Recent → Historical data
- `completeness` - Full dataset → Sample → Summary
- `accuracy` - Precise → Approximate → Estimate

**Degradation Notification**: How to inform users

- `silent` - Log only, no user notification
- `warning` - Inform user of degradation
- `explicit` - Detailed explanation of what degraded and why

### Cost-Benefit Analysis

**When to Use:**

- External service dependencies (APIs, databases)
- Time-sensitive operations with acceptable degraded modes
- Operations where partial results are better than no results
- High-availability requirements (system must always respond)
- Scenarios where waiting for perfect solution is worse than good-enough solution

**When NOT to Use:**

- Operations requiring exact correctness (no acceptable degradation)
- Security-critical operations (authentication, authorization)
- Financial transactions (no room for "approximate")
- When failures must surface to user (diagnostic operations)
- Simple operations with no meaningful fallback

**Trade-offs:**

- Benefit: System always completes, never fully fails
- Cost: Users may receive degraded responses
- Best for: User-facing features where responsiveness matters

## How This Workflow Works

**Integration with DEFAULT_WORKFLOW:**

This workflow can be applied to any step in DEFAULT_WORKFLOW that has fallback options. Most commonly used for external service integrations (Step 5) or data fetching operations.

**Execution:**

- Invoke automatically when operations have known fallbacks
- Or explicitly via `/ultrathink --workflow cascade` for resilient operations
- System attempts optimal approach first
- Falls back automatically on timeout or failure
- Reports degradation level achieved

**Key Principle**: Better to deliver degraded service than no service

## The Cascade Workflow

### Step 1: Define Cascade Levels

- [ ] **Use** architect agent to identify cascade levels
- [ ] Define PRIMARY approach (optimal solution)
- [ ] Define SECONDARY approach (acceptable degradation)
- [ ] Define TERTIARY approach (guaranteed completion)
- [ ] Set timeout for each level
- [ ] Document what degrades at each level
- [ ] **CRITICAL: Ensure tertiary ALWAYS succeeds**

**Cascade Level Requirements:**

**PRIMARY (Optimal)**:

- Best possible outcome
- May depend on external services
- May be slow or resource-intensive
- Can fail or timeout

**SECONDARY (Acceptable)**:

- Reduced quality but functional
- More reliable than primary
- Faster or fewer dependencies
- Acceptable for users

**TERTIARY (Guaranteed)**:

- Always succeeds, never fails
- No external dependencies
- Fast and reliable
- Minimal but functional

**Example Cascade Definitions:**

```markdown
## Example 1: Code Analysis with AI

PRIMARY: GPT-4 comprehensive analysis (timeout: 30s)

- Full semantic understanding
- Complex pattern detection
- Detailed recommendations

SECONDARY: GPT-3.5 standard analysis (timeout: 10s)

- Basic pattern detection
- Standard recommendations
- Faster, lower quality

TERTIARY: Static analysis with regex (timeout: 5s)

- Pattern matching only
- No semantic understanding
- Always completes, basic insights

## Example 2: External API Data Fetch

PRIMARY: Live API call (timeout: 10s)

- Real-time data
- Complete information
- Current state

SECONDARY: Cached data (timeout: 2s)

- Recent data (< 1 hour old)
- May be stale
- Fast retrieval

TERTIARY: Default values (timeout: 0s)

- Static fallback data
- Guaranteed available
- Generic/safe defaults

## Example 3: Test Execution

PRIMARY: Full test suite (timeout: 120s)

- All tests run
- Complete coverage
- High confidence

SECONDARY: Critical tests only (timeout: 30s)

- Core functionality verified
- Reduced coverage
- Acceptable confidence

TERTIARY: Smoke tests (timeout: 10s)

- Basic sanity checks
- Minimal coverage
- System functional
```

### Step 2: Attempt Primary Approach

- [ ] Execute optimal solution
- [ ] Set timeout based on strategy configuration
- [ ] Monitor execution progress
- [ ] If completes successfully: DONE (best outcome)
- [ ] If fails or times out: Continue to Step 3
- [ ] Log attempt and reason for failure

**Primary Execution:**

```python
# Pseudocode for primary attempt
try:
    result = execute_primary_approach(timeout=PRIMARY_TIMEOUT)
    log_success(level="PRIMARY", result=result)
    return result  # DONE - best outcome achieved
except TimeoutError:
    log_failure(level="PRIMARY", reason="timeout")
    # Continue to Step 3
except ExternalServiceError as e:
    log_failure(level="PRIMARY", reason=f"service_error: {e}")
    # Continue to Step 3
```

**Example - Code Analysis:**

```markdown
PRIMARY ATTEMPT: GPT-4 Analysis

- Started: 2025-01-20 10:15:30
- Timeout: 30s
- Status: TIMEOUT after 30s
- Reason: GPT-4 API slow response
- Next: Falling back to SECONDARY (GPT-3.5)
```

### Step 3: Attempt Secondary Approach

- [ ] Log degradation to secondary level
- [ ] Execute acceptable fallback solution
- [ ] Set shorter timeout (typically 1/3 of primary)
- [ ] Monitor execution progress
- [ ] If completes successfully: DONE (acceptable outcome)
- [ ] If fails or times out: Continue to Step 4
- [ ] Log attempt and reason for failure

**Secondary Execution:**

```python
# Pseudocode for secondary attempt
log_degradation(from_level="PRIMARY", to_level="SECONDARY")
try:
    result = execute_secondary_approach(timeout=SECONDARY_TIMEOUT)
    log_success(level="SECONDARY", result=result, degraded=True)
    return result  # DONE - acceptable outcome
except TimeoutError:
    log_failure(level="SECONDARY", reason="timeout")
    # Continue to Step 4
except Error as e:
    log_failure(level="SECONDARY", reason=f"error: {e}")
    # Continue to Step 4
```

**Example - Code Analysis:**

```markdown
SECONDARY ATTEMPT: GPT-3.5 Analysis

- Started: 2025-01-20 10:16:00
- Timeout: 10s
- Status: SUCCESS after 6s
- Quality: Standard (degraded from comprehensive)
- Result: Basic analysis completed
- Degradation: Missing advanced semantic insights
- Outcome: ACCEPTABLE - delivered to user
```

### Step 4: Attempt Tertiary Approach

- [ ] Log degradation to tertiary level
- [ ] Execute guaranteed completion approach
- [ ] Set minimal timeout (typically 1s)
- [ ] **MUST succeed - no failures allowed**
- [ ] Return minimal but functional result
- [ ] Log success (degraded but functional)
- [ ] DONE (guaranteed completion)

**Tertiary Execution:**

```python
# Pseudocode for tertiary attempt
log_degradation(from_level="SECONDARY", to_level="TERTIARY")
try:
    result = execute_tertiary_approach(timeout=TERTIARY_TIMEOUT)
    log_success(level="TERTIARY", result=result, heavily_degraded=True)
    return result  # DONE - minimal but functional
except Exception as e:
    # THIS SHOULD NEVER HAPPEN
    log_critical_failure("TERTIARY approach failed - this is a bug!")
    # Tertiary must be designed to never fail
    raise SystemError("Cascade safety violation: tertiary failed")
```

**Example - Code Analysis:**

```markdown
TERTIARY ATTEMPT: Static Regex Analysis

- Started: 2025-01-20 10:16:10
- Timeout: 5s
- Status: SUCCESS after 0.3s
- Quality: Minimal (heavily degraded)
- Result: Basic pattern matching completed
- Degradation: No semantic understanding, pattern-based only
- Outcome: FUNCTIONAL - delivered basic insights to user
```

### Step 5: Report Degradation

- [ ] Determine notification level from configuration
- [ ] If `silent`: Log only, no user message
- [ ] If `warning`: Brief notification to user
- [ ] If `explicit`: Detailed degradation explanation
- [ ] Document which level succeeded
- [ ] Explain impact of degradation
- [ ] Log cascade path taken for analysis

**Degradation Reporting Templates:**

**Silent Mode** (logs only):

```
[LOG] CASCADE: PRIMARY timeout (30s) → SECONDARY success (6s)
Result: standard_analysis (degraded from comprehensive)
```

**Warning Mode** (brief user notification):

```
⚠️  Using cached data (less than 1 hour old)
Current real-time data unavailable.
```

**Explicit Mode** (detailed explanation):

```
ℹ️  Analysis Quality Notice

We attempted to provide comprehensive code analysis using GPT-4,
but encountered slow response times (>30s timeout).

Fallback Applied:
- Used: GPT-3.5 standard analysis (completed in 6s)
- Quality: Standard (vs. Comprehensive)
- Impact: Advanced semantic insights not included

What You're Getting:
✓ Basic pattern detection
✓ Standard recommendations
✓ Code quality assessment

What's Missing:
✗ Complex architectural insights
✗ Deep semantic analysis
✗ Advanced refactoring suggestions

This is still actionable analysis, just less detailed than optimal.
```

**Cascade Path Documentation:**

```markdown
# Cascade Execution Report

Operation: Code Analysis
Timestamp: 2025-01-20 10:15:30
Strategy: Balanced timeouts

## Cascade Path

1. PRIMARY: GPT-4 Comprehensive Analysis
   - Timeout: 30s
   - Result: TIMEOUT
   - Reason: API response time exceeded threshold
   - Duration: 30.1s

2. SECONDARY: GPT-3.5 Standard Analysis
   - Timeout: 10s
   - Result: SUCCESS
   - Duration: 6.2s
   - Degradation: Reduced from comprehensive to standard

3. TERTIARY: Not Attempted (secondary succeeded)

## Final Outcome

- Level: SECONDARY (acceptable degradation)
- Quality: Standard analysis delivered
- User Impact: Moderate (missing advanced insights)
- Total Time: 36.2s (primary timeout + secondary execution)
```

### Step 6: Log Cascade Metrics

- [ ] Record cascade path taken
- [ ] Document level reached (primary/secondary/tertiary)
- [ ] Log timing for each level attempted
- [ ] Track degradation frequency
- [ ] Identify patterns in failures
- [ ] Update cascade strategy if needed

**Metrics to Track:**

```markdown
## Cascade Metrics (Last 30 Days)

Operation: Code Analysis (500 attempts)

Success by Level:

- PRIMARY: 320 (64%) - Optimal outcome
- SECONDARY: 150 (30%) - Acceptable degradation
- TERTIARY: 30 (6%) - Minimal outcome

Average Response Times:

- PRIMARY success: 12s
- PRIMARY timeout: 30s (then fallback)
- SECONDARY success: 5s
- TERTIARY success: 0.3s

Degradation Impact:

- 36% of requests served degraded results
- 94% acceptable quality (primary + secondary)
- 6% minimal quality (tertiary)

Recommendations:

- Consider increasing PRIMARY timeout from 30s to 45s
  (64% success rate suggests timeout too aggressive)
- SECONDARY performing well (30% fallback, 5s average)
- TERTIARY rarely needed (6%), working as designed
```

### Step 7: Continuous Optimization

- [ ] **Use** analyzer agent to review cascade metrics
- [ ] Identify optimization opportunities
- [ ] Adjust timeouts based on success rates
- [ ] Improve secondary approaches if frequently used
- [ ] Update tertiary if inadequate
- [ ] Document learnings in `@amplihack:context/DISCOVERIES.md`

**Optimization Criteria:**

**If PRIMARY succeeds < 50%**:

- Timeout too aggressive → Increase timeout
- Approach too brittle → Improve reliability
- External service unreliable → Consider different primary

**If SECONDARY used > 40%**:

- Secondary is really the "normal" case → Swap primary and secondary
- Primary too optimistic → Recalibrate expectations

**If TERTIARY used > 10%**:

- Secondary not reliable enough → Improve secondary
- Timeouts too aggressive → Increase secondary timeout
- System under stress → Investigate root cause

**Example Optimization:**

```markdown
## Optimization: Code Analysis Cascade

Current Performance:

- PRIMARY: 64% success (GPT-4, 30s timeout)
- SECONDARY: 30% usage (GPT-3.5, 10s timeout)
- TERTIARY: 6% usage (regex, 5s timeout)

Issue Identified:
PRIMARY timeout of 30s too aggressive. 64% success means
36% of requests waiting full 30s before fallback.

Optimization:

- Increase PRIMARY timeout: 30s → 45s
- Add fast-fail detection: If no response in 5s, likely to timeout
- Implement speculative execution: Start SECONDARY at 20s
  while PRIMARY still running, use whichever completes first

Expected Impact:

- PRIMARY success rate: 64% → 80%
- Average response time: 18s → 15s (less timeout waste)
- User experience: Fewer degraded results, similar speed
```

## Cascade Patterns Library

### Pattern 1: External API with Cache

**Use Case**: Fetching data from external API that may be slow or unavailable

```markdown
PRIMARY: Live API call (timeout: 10s)

- Fresh data from API
- Complete and current

SECONDARY: Cached data (timeout: 2s)

- Data from cache (< 1 hour old)
- May be stale but recent

TERTIARY: Default/Historical data (timeout: 0s)

- Safe default values or old historical data
- Always available
```

**Notification**: Warning ("Using cached data from 30 minutes ago")

### Pattern 2: AI Analysis Quality Levels

**Use Case**: Code analysis with AI models of varying capability

```markdown
PRIMARY: GPT-4 comprehensive (timeout: 30s)

- Deep semantic analysis
- Complex insights

SECONDARY: GPT-3.5 standard (timeout: 10s)

- Basic analysis
- Standard patterns

TERTIARY: Static analysis (timeout: 5s)

- Pattern matching
- No AI, guaranteed fast
```

**Notification**: Explicit (explain quality degradation)

### Pattern 3: Database Query Optimization

**Use Case**: Complex database queries that may be slow

```markdown
PRIMARY: Exact query with full JOINs (timeout: 5s)

- Precise results
- All relationships included

SECONDARY: Simplified query (timeout: 2s)

- Approximate results
- Fewer JOINs, main data only

TERTIARY: Cached summary (timeout: 0s)

- Precomputed aggregates
- May be stale but instant
```

**Notification**: Silent (log only)

### Pattern 4: Test Execution Levels

**Use Case**: Running tests with time constraints

```markdown
PRIMARY: Full test suite (timeout: 120s)

- All tests run
- Complete coverage

SECONDARY: Critical tests (timeout: 30s)

- Core functionality only
- Reduced coverage

TERTIARY: Smoke tests (timeout: 10s)

- Basic sanity only
- Minimal validation
```

**Notification**: Warning ("Ran critical tests only, skipped full suite")

### Pattern 5: Data Processing Completeness

**Use Case**: Processing large datasets

```markdown
PRIMARY: Full dataset (timeout: 60s)

- Process all records
- Complete accuracy

SECONDARY: 10% sample (timeout: 10s)

- Statistical sample
- Approximate results

TERTIARY: Summary statistics (timeout: 1s)

- Precomputed aggregates
- High-level overview only
```

**Notification**: Explicit (explain sampling used)

## Integration with DEFAULT_WORKFLOW

### During Step 5: Implementation

When implementing features with external dependencies:

1. Identify operations that can degrade gracefully
2. Define cascade levels for each operation
3. Implement primary approach first
4. Add secondary and tertiary fallbacks
5. Configure timeouts and notification levels
6. Test all cascade levels independently

### During Step 7: Testing

Test cascade behavior explicitly:

```python
def test_cascade_levels():
    """Test all cascade levels independently"""

    # Test primary succeeds
    result = operation_with_cascade()
    assert result.level == "PRIMARY"
    assert result.quality == "optimal"

    # Test secondary fallback (mock primary failure)
    with mock_primary_timeout():
        result = operation_with_cascade()
        assert result.level == "SECONDARY"
        assert result.quality == "acceptable"

    # Test tertiary fallback (mock primary and secondary failure)
    with mock_primary_and_secondary_timeout():
        result = operation_with_cascade()
        assert result.level == "TERTIARY"
        assert result.quality == "minimal"
```

## Examples

### Example 1: Weather API Integration

**Configuration**:

- Strategy: Balanced (30s / 10s / 5s)
- Type: Service fallback
- Notification: Warning

**Implementation**:

```python
async def get_weather(location: str) -> WeatherData:
    """Get weather data with cascade fallback"""

    # PRIMARY: Live weather API
    try:
        return await fetch_weather_api(location, timeout=30)
    except (TimeoutError, APIError):
        log.warning("PRIMARY weather API failed, trying cache")

    # SECONDARY: Cached weather data
    try:
        cached = await get_cached_weather(location, max_age=3600)
        if cached:
            notify_user("Using weather data from cache (< 1 hour old)")
            return cached
    except CacheError:
        log.warning("SECONDARY cache failed, using defaults")

    # TERTIARY: Default weather data
    return get_default_weather(location)  # Never fails
```

**Outcome**: System always returns weather data, quality degrades gracefully

### Example 2: Code Review with AI

**Configuration**:

- Strategy: Patient (120s / 30s / 10s)
- Type: Quality fallback
- Notification: Explicit

**Cascade Path** (actual execution):

1. PRIMARY: GPT-4 comprehensive review - TIMEOUT after 120s
2. SECONDARY: GPT-3.5 standard review - SUCCESS in 18s
3. TERTIARY: Not attempted

**User Notification**:

```
ℹ️  Code Review Quality Notice

We attempted comprehensive AI review using GPT-4, but encountered
slow response times (>120s timeout).

Delivered: Standard review using GPT-3.5 (completed in 18s)
- Basic code quality checks ✓
- Standard best practices ✓
- Security pattern detection ✓

Not included in this review:
- Advanced architectural insights
- Complex refactoring suggestions
- Deep semantic analysis

This is still a thorough review, just less detailed than optimal.
```

### Example 3: Search Results Ranking

**Configuration**:

- Strategy: Aggressive (5s / 2s / 1s)
- Type: Accuracy fallback
- Notification: Silent

**Implementation**:

```python
def search_and_rank(query: str) -> List[Result]:
    """Search with ML ranking, fallback to simple ranking"""

    results = fetch_results(query)

    # PRIMARY: ML-based ranking (sophisticated)
    try:
        return ml_rank(results, timeout=5)
    except TimeoutError:
        pass  # Silent fallback

    # SECONDARY: Heuristic ranking (good enough)
    try:
        return heuristic_rank(results, timeout=2)
    except TimeoutError:
        pass

    # TERTIARY: Simple text match ranking (basic)
    return simple_rank(results)  # Always fast
```

**Outcome**: User always gets results, ranking quality degrades silently

## Customization

To customize this workflow:

1. Edit Configuration section to adjust timeouts and notification levels
2. Define cascade levels for your specific operations
3. Choose appropriate fallback types (service, quality, freshness, etc.)
4. Set notification preferences based on user expectations
5. Monitor metrics and optimize timeout values
6. Save changes - updated workflow applies to future executions

## Philosophy Notes

This workflow enforces:

- **Resilience**: System always completes, never completely fails
- **User Experience**: Better degraded service than error message
- **Transparency**: Users understand what they're getting (if explicit mode)
- **Progressive Enhancement**: Optimal by default, degrade when necessary
- **Measurable Quality**: Clear definition of what degrades at each level
- **Continuous Improvement**: Metrics drive timeout optimization
- **Guaranteed Completion**: Tertiary level must never fail
