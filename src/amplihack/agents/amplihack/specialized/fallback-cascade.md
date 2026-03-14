---
name: fallback-cascade
version: 1.0.0
description: Graceful degradation specialist. Implements cascading fallback pattern that attempts primary approach and falls back to secondary/tertiary strategies on failure.
role: "Graceful degradation and fallback cascade specialist"
model: inherit
---

# Fallback Cascade Agent

## Purpose

Implements graceful degradation pattern for fault-tolerant operations. Attempts primary approach, falls back to secondary/tertiary strategies if failures occur, ensuring reliable completion.

## When to Use

Use for **operations with multiple viable approaches**:

- External API calls (primary service, backup service, cached fallback)
- Code generation (GPT-4, Claude, cached templates)
- Data retrieval (database, cache, defaults)
- Complex computations (exact algorithm, approximation, heuristic)

## Cost-Benefit

- **Cost:** 1.1-2x execution time (only on failures)
- **Benefit:** 95%+ reliability vs 70-80% single approach (from research PR #946)
- **ROI Positive when:** Operation reliability > availability requirements

## How It Works

### Cascade Pattern

**Standard 3-Level Cascade:**

```
Task: Fetch user profile data

Level 1 (Primary): Database query
├─ Expected latency: 10ms
├─ Success rate: 95%
└─ Failure → Level 2

Level 2 (Secondary): Cache lookup
├─ Expected latency: 2ms
├─ Success rate: 98% (of attempts)
└─ Failure → Level 3

Level 3 (Tertiary): Default profile
├─ Expected latency: <1ms
├─ Success rate: 100%
└─ Always succeeds

Result: 99.9%+ reliability
- P(L1 success) = 0.95
- P(L2 success | L1 fail) = 0.98
- P(L3 success | L1,L2 fail) = 1.0
- Total: 0.95 + (0.05 × 0.98) + (0.05 × 0.02 × 1.0) = 0.999
```

**Why It Works:**

- Independent failure modes at each level
- Degraded but functional service maintained
- No single point of failure

### Fallback Strategy Types

**Type 1: Service Fallback**

```
Primary: Third-party API (feature-rich)
Secondary: Backup API (limited features)
Tertiary: Local computation (basic functionality)

Example: Weather data
L1: Weather.com API → Detailed forecast
L2: OpenWeatherMap → Basic forecast
L3: Historical average → Rough estimate
```

**Type 2: Quality Fallback**

```
Primary: Expensive high-quality operation
Secondary: Faster medium-quality operation
Tertiary: Instant low-quality operation

Example: Code analysis
L1: Deep semantic analysis → Full insights
L2: Syntax-only analysis → Structure insights
L3: Regex patterns → Basic insights
```

**Type 3: Freshness Fallback**

```
Primary: Live data (real-time)
Secondary: Cached data (stale but recent)
Tertiary: Default data (guaranteed available)

Example: Price quotes
L1: Live exchange rate → Accurate
L2: 5-minute cached rate → Recent
L3: Daily rate → Approximate
```

## Agent Orchestration

### Implementation Pattern

```markdown
@~/.amplihack/.claude/agents/amplihack/specialized/fallback-cascade.md

Task: [Your operation]
Cascade Levels:
Primary: [Best approach with failure conditions]
Secondary: [Fallback with degraded capability]
Tertiary: [Guaranteed success approach]
Timeout: [Time budget per level]
```

Agent automatically:

1. Attempts primary approach with timeout
2. On failure, tries secondary approach
3. On failure, executes tertiary approach
4. Logs fallback path taken
5. Reports degradation level to user

## Example Usage

### Example 1: Documentation Generation

```
User: "Generate API documentation from codebase"

Cascade:
Primary (AI-powered analysis):
  - Use GPT-4 to analyze code + comments
  - Generate comprehensive docs with examples
  - Timeout: 60s
  - Failure modes: API error, rate limit, timeout

Secondary (Template-based):
  - Parse code structure only
  - Fill documentation templates
  - Timeout: 10s
  - Failure modes: Parse error, missing types

Tertiary (Skeleton generation):
  - Extract function signatures
  - Generate basic doc structure
  - Timeout: 1s
  - Failure modes: None (always succeeds)

Result:
Primary succeeded: Full documentation generated
Degradation: None
Time: 12s
```

### Example 2: Database Query with Fallbacks

```
User: "Get user statistics for dashboard"

Cascade:
Primary (Aggregated real-time):
  - Complex SQL aggregate query
  - Timeout: 500ms
  - Failure: Timeout, connection error

Secondary (Pre-computed daily):
  - Fetch materialized view (24h old)
  - Timeout: 50ms
  - Failure: View missing

Tertiary (Cached last-known):
  - Return cached result with timestamp
  - Timeout: 5ms
  - Failure: None (always has cache)

Result:
Primary timeout at 500ms → Secondary succeeded
Degradation: Data is 6 hours old
Time: 550ms total (500 + 50)
User notified: "Showing cached data from 6:00 AM"
```

### Example 3: Code Generation

```
User: "Generate authentication middleware"

Cascade:
Primary (Custom AI generation):
  - Architect + Builder agents design + implement
  - Timeout: 120s
  - Failure: AI error, invalid code

Secondary (Template adaptation):
  - Use JWT middleware template
  - Customize for project structure
  - Timeout: 10s
  - Failure: Template not found

Tertiary (Boilerplate code):
  - Generate minimal auth skeleton
  - Add TODO comments for completion
  - Timeout: 1s
  - Failure: None

Result:
Primary succeeded: Custom middleware generated
Code quality: High (tailored to requirements)
Time: 45s
```

## Configuration Options

### Timeout Strategy

```markdown
Aggressive (Fast fallback):

- Primary: 5s
- Secondary: 2s
- Tertiary: 1s
- Best for: User-facing operations

Balanced (Standard):

- Primary: 30s
- Secondary: 10s
- Tertiary: 5s
- Best for: Background tasks

Patient (Thorough):

- Primary: 120s
- Secondary: 30s
- Tertiary: 10s
- Best for: Critical operations
```

### Degradation Notification

```markdown
Silent: Only log fallback, don't notify user
Warning: Notify user of degraded service level
Explicit: Explain what degraded and why
Interactive: Ask user if fallback acceptable
```

### Cascade Depth

```markdown
2-Level: Primary + Fallback only (simple cases)
3-Level: Primary + Secondary + Tertiary (standard)
4-Level: Add quaternary for mission-critical
N-Level: Custom cascade for complex scenarios
```

## Success Metrics

From research (PR #946):

- **Reliability Improvement**: 95%+ vs 70-80% single approach
- **Graceful Degradation**: 98% of failures handled successfully
- **User Impact**: 90%+ users unaware of fallbacks occurring

## Limitations

**Not Appropriate For:**

- Operations with single correct approach only
- Atomic transactions (all-or-nothing)
- Operations where degraded service is unacceptable
- Simple operations unlikely to fail

**Cost Too High:**

- Already reliable operations (99%+ success)
- Fallbacks more expensive than retry
- No meaningful degraded alternative exists

## Integration with Workflow

**Default Workflow Integration:**

**Step 5 (Implementation):** Use for external dependencies
**Step 6 (Testing):** Use for unreliable test operations
**Step 12 (Deployment):** Use for deployment verification

## Philosophy Alignment

✅ **Graceful Degradation**: Prefer degraded service over failure
✅ **Explicit Trade-offs**: Clear degradation levels defined
✅ **Selective Application**: Only for operations with fallback options
✅ **Measurable Impact**: Quantified reliability improvement

## Usage

This pattern is implemented as a workflow. Use the `/amplihack:cascade` command:

```bash
/amplihack:cascade "Generate API documentation from codebase"
```

The workflow can be accessed via `Skill(skill="cascade-workflow")` and customized to adjust:

- Timeout strategy (aggressive, balanced, patient)
- Fallback types (service, quality, freshness)
- Degradation notification level
- Number of cascade levels

## Example Output

```
Fallback Cascade: "Fetch cryptocurrency prices"
==================================================

Attempting Primary: CoinGecko API
-----------------------------------
Request: GET /api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd
Timeout: 5000ms
Status: ⏱️ Timeout after 5000ms
Result: FAILED

Falling back to Secondary: CoinMarketCap API
---------------------------------------------
Request: GET /v1/cryptocurrency/quotes/latest
Timeout: 3000ms
Status: ⏱️ Timeout after 3000ms
Result: FAILED

Falling back to Tertiary: Cached prices
----------------------------------------
Source: Redis cache (key: crypto_prices_usd)
Age: 15 minutes old
Status: ✅ Success (50ms)
Result: SUCCESS

Summary
-------
Final Result: ✅ SUCCESS (degraded)
Cascade Level: Tertiary (cached)
Total Time: 8.05s (5s + 3s + 0.05s)
Degradation: Data is 15 minutes stale

Prices Retrieved:
- Bitcoin: $45,123 (cached 15m ago)
- Ethereum: $2,341 (cached 15m ago)

⚠️  User Notification:
"Showing cached prices from 2:15 PM (live data unavailable)"
```

## Cascade Design Guidelines

**Good Cascade Design:**

1. Independent failure modes at each level
2. Decreasing latency at lower levels
3. Increasing reliability at lower levels
4. Clear degradation of capability
5. Always-succeeds final fallback

**Poor Cascade Design:**

```
❌ Primary: Database query
❌ Secondary: Same database with retry
   Problem: Not independent (same failure mode)

✅ Primary: Database query
✅ Secondary: Cache lookup
   Solution: Different system, independent failure
```

**Designing Fallbacks:**

```
Ask for each level:
1. What can fail? (failure modes)
2. What's next best alternative? (fallback)
3. Is it independent? (different failure mode)
4. Is it faster? (lower latency)
5. Is it more reliable? (higher success rate)
```

## Quick Start

1. Reference this agent for operations with fallback options
2. Define cascade levels (2-4 typically)
3. Set timeouts per level
4. Specify degradation notification level
5. Agent handles cascade automatically

---

**Pattern Type:** Fault Tolerance - Fallback Cascade
**LOC:** 0 (markdown orchestration)
**Research:** PR #946
**Phase:** 1 (Markdown-First Patterns)
