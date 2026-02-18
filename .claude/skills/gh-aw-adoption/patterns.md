# GitHub Agentic Workflows - Production Patterns

Production-proven patterns, anti-patterns, and best practices for building robust agentic workflows at scale.

**Last Updated**: 2026-02-15
**Based On**: 100+ workflows analyzed from gh-aw repository and cybergym5 adoption

---

## Table of Contents

1. [Error Resilience Patterns](#error-resilience-patterns)
2. [Safe-Output Management](#safe-output-management)
3. [Security Hardening](#security-hardening)
4. [Performance Optimization](#performance-optimization)
5. [Testing Strategies](#testing-strategies)
6. [Anti-Patterns](#anti-patterns)
7. [Workflow Composition](#workflow-composition)
8. [Monitoring and Observability](#monitoring-and-observability)

---

## Error Resilience Patterns

### Pattern 1: Exponential Backoff with Jitter

**Problem**: Fixed retry intervals cause thundering herd when many workflows retry simultaneously.

**Solution**: Add randomized jitter to exponential backoff.

```bash
# Bad: Fixed intervals
for attempt in 1 2 3; do
  if api_call; then break; fi
  sleep $((2 ** attempt))  # 2s, 4s, 8s (predictable)
done

# Good: Exponential backoff with jitter
for attempt in 1 2 3; do
  if api_call; then break; fi
  base_delay=$((2 ** attempt))
  jitter=$(( RANDOM % base_delay ))
  sleep $(( base_delay + jitter ))  # 2-4s, 4-8s, 8-16s (randomized)
done
```

**Benefits**:

- Prevents thundering herd during API outages
- Spreads retry load over time
- Reduces collision probability

**When to use**: Any API call with retry logic

### Pattern 2: Circuit Breaker

**Problem**: Continuously retrying failing external services wastes resources and delays failure detection.

**Solution**: Implement circuit breaker pattern with state tracking.

```bash
# Store circuit state in repo-memory
circuit_state_file="memory/workflow/circuit-breaker.json"

check_circuit() {
  local service=$1

  if [ ! -f "$circuit_state_file" ]; then
    echo "closed"
    return
  fi

  state=$(jq -r ".\"$service\".state" "$circuit_state_file" 2>/dev/null || echo "closed")
  last_failure=$(jq -r ".\"$service\".last_failure" "$circuit_state_file" 2>/dev/null || echo "0")

  if [ "$state" = "open" ]; then
    # Check if cooldown period passed (5 minutes)
    now=$(date +%s)
    cooldown=300
    if (( now - last_failure > cooldown )); then
      echo "half-open"  # Allow one test request
    else
      echo "open"  # Still in cooldown
    fi
  else
    echo "$state"
  fi
}

record_failure() {
  local service=$1
  local failure_threshold=3

  # Load current state
  if [ -f "$circuit_state_file" ]; then
    state=$(cat "$circuit_state_file")
  else
    state='{}'
  fi

  # Increment failure count
  failures=$(echo "$state" | jq -r ".\"$service\".failures // 0")
  failures=$((failures + 1))

  # Update state
  if (( failures >= failure_threshold )); then
    circuit_state="open"
  else
    circuit_state="closed"
  fi

  state=$(echo "$state" | jq \
    --arg service "$service" \
    --argjson failures "$failures" \
    --arg state "$circuit_state" \
    --argjson timestamp "$(date +%s)" \
    '.[$service] = {failures: $failures, state: $state, last_failure: $timestamp}')

  echo "$state" > "$circuit_state_file"
}

record_success() {
  local service=$1

  if [ -f "$circuit_state_file" ]; then
    state=$(cat "$circuit_state_file")
    state=$(echo "$state" | jq \
      --arg service "$service" \
      '.[$service] = {failures: 0, state: "closed", last_failure: 0}')
    echo "$state" > "$circuit_state_file"
  fi
}

# Usage
service="external-api"
circuit=$(check_circuit "$service")

if [ "$circuit" = "open" ]; then
  echo "Circuit open for $service, skipping call"
  exit 0
fi

if api_call "$service"; then
  record_success "$service"
else
  record_failure "$service"
  exit 1
fi
```

**Benefits**:

- Fast failure without wasting retries
- Automatic recovery with cooldown period
- Prevents cascading failures

**When to use**: Any external service dependency (APIs, webhooks, etc.)

### Pattern 3: Bulkhead Pattern

**Problem**: Failure in one workflow operation cascades to unrelated operations.

**Solution**: Isolate operations using separate execution contexts.

````markdown
## Bulkhead Pattern Implementation

Divide workflow into isolated sections with independent error handling:

### Section 1: Issue Processing

Process issues independently. If one fails, continue with others.

```bash
for issue in $issues; do
  (
    # Subprocess for isolation
    process_issue "$issue" || echo "Failed to process issue $issue"
  ) &
done
wait  # Wait for all subprocesses
```
````

### Section 2: PR Processing

Separate from issue processing. Even if all issues fail, PRs still process.

```bash
for pr in $prs; do
  (
    process_pr "$pr" || echo "Failed to process PR $pr"
  ) &
done
wait
```

### Section 3: Reporting

Runs regardless of processing failures. Always generate report.

```bash
generate_report
```

````

**Benefits**:
- Limits blast radius of failures
- Improves overall workflow reliability
- Better error isolation and debugging

**When to use**: Workflows processing multiple resource types or independent operations

### Pattern 4: Graceful Degradation

**Problem**: Workflow fails completely when non-critical features unavailable.

**Solution**: Detect feature availability and degrade gracefully.

```bash
# Feature flags for optional functionality
SLACK_NOTIFICATIONS=false
METRICS_REPORTING=false

# Check if Slack webhook available
if [ -n "$SLACK_WEBHOOK_URL" ] && curl -sf "$SLACK_WEBHOOK_URL" >/dev/null; then
  SLACK_NOTIFICATIONS=true
fi

# Check if metrics endpoint available
if curl -sf "https://metrics.example.com/health" >/dev/null; then
  METRICS_REPORTING=true
fi

# Core workflow logic (always runs)
process_items

# Optional features (degrade gracefully if unavailable)
if [ "$SLACK_NOTIFICATIONS" = true ]; then
  send_slack_notification "Workflow completed"
else
  echo "Skipping Slack notification (service unavailable)"
fi

if [ "$METRICS_REPORTING" = true ]; then
  report_metrics
else
  echo "Skipping metrics reporting (service unavailable)"
fi
````

**Benefits**:

- Core functionality preserved during outages
- Better user experience
- Reduced false positive failures

**When to use**: Workflows with optional integrations (notifications, metrics, external services)

---

## Safe-Output Management

### Pattern 1: Prioritized Safe-Output Queue

**Problem**: Hitting safe-output limits leaves most important actions un-performed.

**Solution**: Priority queue with explicit ordering.

```bash
# Define priority levels
declare -A priorities
priorities["security"]=1
priorities["critical-bug"]=2
priorities["bug"]=3
priorities["enhancement"]=4
priorities["cosmetic"]=5

# Collect all pending actions with priorities
actions=()
actions+=("close-issue:123:security")
actions+=("close-issue:124:bug")
actions+=("close-issue:125:cosmetic")
actions+=("close-issue:126:critical-bug")

# Sort by priority
IFS=$'\n' sorted_actions=($(printf '%s\n' "${actions[@]}" | while read action; do
  priority=${action##*:}
  prio_value=${priorities[$priority]}
  echo "$prio_value:$action"
done | sort -n | cut -d: -f2-))

# Process in priority order until limit reached
limit=3
count=0

for action in "${sorted_actions[@]}"; do
  if (( count >= limit )); then
    # Save remaining to repo-memory for next run
    echo "$action" >> memory/workflow/deferred-actions.txt
    continue
  fi

  # Execute action
  issue_num=$(echo "$action" | cut -d: -f2)
  close_issue "$issue_num"
  ((count++))
done

# Log deferral
if [ -f memory/workflow/deferred-actions.txt ]; then
  deferred=$(wc -l < memory/workflow/deferred-actions.txt)
  echo "Deferred $deferred actions due to safe-output limit"
fi
```

**Benefits**:

- Critical actions always execute first
- Transparent deferral mechanism
- Automatic recovery on next run

**When to use**: Any workflow with safe-output limits processing prioritized items

### Pattern 2: Adaptive Limits Based on Context

**Problem**: Static limits don't account for varying workflow needs.

**Solution**: Adjust safe-output limits dynamically based on detected conditions.

```yaml
safe-outputs:
  add-comment:
    max: 10 # Default for normal operations
    expiration: 1d
```

```bash
# Detect high-urgency conditions
urgent_count=$(gh issue list --label urgent --json number --jq 'length')

# Adjust comment limit dynamically
if (( urgent_count > 10 )); then
  effective_limit=20  # Double limit for high-urgency situations
  echo "⚠️ High urgency detected ($urgent_count urgent issues), increasing comment limit to $effective_limit"
else
  effective_limit=10
fi

# Use effective limit in processing
comment_count=0
for issue in $issues; do
  if (( comment_count >= effective_limit )); then
    break
  fi

  post_comment "$issue"
  ((comment_count++))
done
```

**Benefits**:

- Flexibility for exceptional situations
- Maintains safety during normal operations
- Explicit logging of limit adjustments

**When to use**: Workflows with variable load or urgency-based processing

### Pattern 3: Safe-Output Budget Tracking

**Problem**: No visibility into safe-output usage across runs.

**Solution**: Track and visualize safe-output budget consumption.

```bash
# Track safe-output usage in repo-memory
budget_file="memory/workflow/safe-output-budget.jsonl"

record_safe_output() {
  local operation=$1
  local item=$2

  echo "{\"timestamp\":\"$(date -Iseconds)\",\"operation\":\"$operation\",\"item\":\"$item\"}" >> "$budget_file"
}

check_budget() {
  local operation=$1
  local limit=$2
  local expiration_hours=${3:-24}  # Default 1 day

  cutoff=$(date -d "$expiration_hours hours ago" -Iseconds)

  count=$(jq -r \
    --arg op "$operation" \
    --arg cutoff "$cutoff" \
    'select(.operation == $op and .timestamp > $cutoff)' \
    "$budget_file" 2>/dev/null | wc -l)

  remaining=$((limit - count))

  echo "$remaining"
}

# Usage
remaining=$(check_budget "add-comment" 10 24)

if (( remaining > 0 )); then
  post_comment "$issue"
  record_safe_output "add-comment" "$issue"
else
  echo "⚠️ Comment budget exhausted ($remaining/10 remaining)"
fi
```

**Benefits**:

- Real-time budget awareness
- Historical usage tracking
- Prevents accidental over-limit attempts

**When to use**: All workflows with safe-outputs, especially high-volume operations

---

## Security Hardening

### Pattern 1: Input Sanitization

**Problem**: User-provided content in issues/PRs can contain malicious code or template injection.

**Solution**: Sanitize all external inputs before processing.

```bash
sanitize_input() {
  local input=$1

  # Remove potential command injection characters
  input=$(echo "$input" | tr -d '\n\r$`\\')

  # Escape special characters
  input=$(echo "$input" | sed 's/[&<>]/\\&/g')

  # Truncate to reasonable length
  input=$(echo "$input" | cut -c1-1000)

  echo "$input"
}

# Usage
issue_body=$(gh issue view 123 --json body --jq '.body')
safe_body=$(sanitize_input "$issue_body")

# Now safe to use in commands
echo "Processing: $safe_body"
```

**Benefits**:

- Prevents command injection
- Blocks template injection attacks
- Limits DoS via oversized inputs

**When to use**: Any workflow processing user-generated content

### Pattern 2: Principle of Least Privilege

**Problem**: Overly broad permissions increase attack surface.

**Solution**: Grant minimum necessary permissions for each workflow.

```yaml
# Bad: Excessive permissions
permissions:
  contents: write
  issues: write
  pull-requests: write
  discussions: write
  actions: write

# Good: Minimal permissions
permissions:
  contents: read     # Only need to read code
  issues: write      # Only need to write issues
```

**Permission matrix** (use as reference):

| Workflow Type    | contents | issues | pull-requests | discussions | actions |
| ---------------- | -------- | ------ | ------------- | ----------- | ------- |
| Issue triage     | read     | write  | -             | -           | -       |
| PR labeler       | read     | -      | write         | -           | -       |
| Security scan    | read     | write  | -             | -           | -       |
| Workflow monitor | read     | -      | -             | -           | read    |
| Deployment       | write    | -      | write         | -           | write   |

**Benefits**:

- Reduces blast radius of compromised workflows
- Clear permission audit trail
- Easier security review

**When to use**: All workflows (mandatory security practice)

### Pattern 3: Network Firewall Allowlisting

**Problem**: Unrestricted network access enables data exfiltration.

**Solution**: Explicit allowlist of required domains.

```yaml
# Bad: Firewall disabled
network:
  firewall: false

# Good: Explicit allowlist
network:
  firewall: true
  allowed:
    - defaults  # npm, PyPI, GitHub, common registries
    - https://api.github.com
    - https://api.trusted-service.com
```

**How to determine required domains**:

1. List external API calls in workflow
2. Extract domains from URLs
3. Add to allowlist with explicit protocols
4. Test workflow execution with firewall enabled
5. Add missing domains if legitimate failures occur

**Benefits**:

- Prevents data exfiltration
- Enforces declared dependencies
- Supports security audits

**When to use**: All workflows (mandatory security practice)

### Pattern 4: Secret Rotation Monitoring

**Problem**: Expired secrets cause silent failures.

**Solution**: Track secret usage and alert on rotation needs.

```bash
# Track secret last-known-good usage
secret_tracking_file="memory/workflow/secret-health.json"

record_secret_success() {
  local secret_name=$1

  if [ -f "$secret_tracking_file" ]; then
    tracking=$(cat "$secret_tracking_file")
  else
    tracking='{}'
  fi

  tracking=$(echo "$tracking" | jq \
    --arg secret "$secret_name" \
    --argjson timestamp "$(date +%s)" \
    '.[$secret] = {last_success: $timestamp, last_failure: null}')

  echo "$tracking" > "$secret_tracking_file"
}

record_secret_failure() {
  local secret_name=$1

  if [ -f "$secret_tracking_file" ]; then
    tracking=$(cat "$secret_tracking_file")
  else
    tracking='{}'
  fi

  tracking=$(echo "$tracking" | jq \
    --arg secret "$secret_name" \
    --argjson timestamp "$(date +%s)" \
    '.[$secret].last_failure = $timestamp')

  echo "$tracking" > "$secret_tracking_file"
}

check_secret_health() {
  local secret_name=$1
  local rotation_days=90

  if [ ! -f "$secret_tracking_file" ]; then
    echo "unknown"
    return
  fi

  last_success=$(jq -r ".\"$secret_name\".last_success // 0" "$secret_tracking_file")
  now=$(date +%s)
  days_since_success=$(( (now - last_success) / 86400 ))

  if (( days_since_success > rotation_days )); then
    echo "rotation_needed"
  else
    echo "healthy"
  fi
}

# Usage
if api_call_with_secret "ANTHROPIC_API_KEY"; then
  record_secret_success "ANTHROPIC_API_KEY"
else
  record_secret_failure "ANTHROPIC_API_KEY"

  # Alert on persistent failures
  last_success=$(jq -r '.ANTHROPIC_API_KEY.last_success // 0' "$secret_tracking_file")
  if (( last_success == 0 )); then
    create_issue "Secret ANTHROPIC_API_KEY appears invalid or expired"
  fi
fi
```

**Benefits**:

- Early detection of secret expiration
- Proactive rotation reminders
- Audit trail for secret usage

**When to use**: Workflows using sensitive credentials

---

## Performance Optimization

### Pattern 1: Batch API Operations

**Problem**: Sequential API calls slow and waste rate limit.

**Solution**: Batch operations where supported by API.

```bash
# Bad: Sequential issue labeling
for issue in $issues; do
  gh issue edit "$issue" --add-label "triaged"  # N API calls
done

# Good: Batch labeling with GraphQL mutation
issue_ids=$(echo "$issues" | jq -r '.[] | .node_id' | tr '\n' ',' | sed 's/,$//')

gh api graphql -f query='
  mutation AddLabels {
    addLabelsToLabelable(input: {
      labelableIds: ["'"$issue_ids"'"],
      labelIds: ["LA_kwDOABCDEFGH"]
    }) {
      clientMutationId
    }
  }
'  # 1 API call
```

**Benefits**:

- 10-100x faster for large batches
- Preserves rate limit quota
- More reliable (fewer round trips)

**When to use**: Any workflow performing bulk operations on issues, PRs, or labels

### Pattern 2: Cached API Responses

**Problem**: Repeatedly fetching unchanged data wastes time and rate limit.

**Solution**: Cache API responses in repo-memory with TTL.

```bash
cache_dir="memory/workflow/api-cache"
mkdir -p "$cache_dir"

cached_api_call() {
  local endpoint=$1
  local ttl_seconds=${2:-3600}  # Default 1 hour

  local cache_key=$(echo "$endpoint" | md5sum | cut -d' ' -f1)
  local cache_file="$cache_dir/$cache_key.json"
  local cache_meta="$cache_dir/$cache_key.meta"

  # Check cache validity
  if [ -f "$cache_file" ] && [ -f "$cache_meta" ]; then
    cached_at=$(cat "$cache_meta")
    now=$(date +%s)
    age=$((now - cached_at))

    if (( age < ttl_seconds )); then
      echo "Cache hit for $endpoint (age: ${age}s)" >&2
      cat "$cache_file"
      return 0
    fi
  fi

  # Cache miss or expired - fetch fresh
  echo "Cache miss for $endpoint, fetching..." >&2
  response=$(gh api "$endpoint")

  # Store in cache
  echo "$response" > "$cache_file"
  date +%s > "$cache_meta"

  echo "$response"
}

# Usage
issues=$(cached_api_call "repos/owner/repo/issues?state=open" 300)  # 5 min TTL
```

**Benefits**:

- Faster subsequent runs
- Reduced API rate limit consumption
- Configurable freshness requirements

**When to use**: Workflows with repeated API calls for slowly-changing data

### Pattern 3: Parallel Processing

**Problem**: Sequential processing of independent items is slow.

**Solution**: Process items in parallel with concurrency limit.

```bash
# Bad: Sequential processing
for issue in $issues; do
  process_issue "$issue"  # 5 seconds each x 100 = 500 seconds
done

# Good: Parallel processing with limit
max_parallel=10
pids=()

for issue in $issues; do
  # Wait if at max concurrency
  while (( ${#pids[@]} >= max_parallel )); do
    wait -n  # Wait for any job to complete
    pids=( $(jobs -pr) )  # Update active PIDs
  done

  # Start background job
  process_issue "$issue" &
  pids+=( $! )
done

wait  # Wait for remaining jobs

# Result: ~50 seconds (10 parallel x 5 rounds)
```

**Benefits**:

- 5-10x faster for I/O-bound operations
- Controlled resource usage via concurrency limit
- Better throughput

**When to use**: Workflows processing many independent items (issues, PRs, files)

### Pattern 4: Incremental Processing

**Problem**: Re-processing all items on every run wastes resources.

**Solution**: Track processed items and skip unchanged ones.

```bash
processed_file="memory/workflow/processed-items.json"

is_processed() {
  local item_id=$1
  local item_updated=$2

  if [ ! -f "$processed_file" ]; then
    return 1  # Not processed
  fi

  last_processed=$(jq -r ".\"$item_id\" // 0" "$processed_file")

  if [ "$last_processed" = "0" ]; then
    return 1  # Never processed
  fi

  # Compare timestamps
  if [[ "$item_updated" > "$last_processed" ]]; then
    return 1  # Updated since last processing
  fi

  return 0  # Already processed
}

mark_processed() {
  local item_id=$1
  local item_updated=$2

  if [ -f "$processed_file" ]; then
    processed=$(cat "$processed_file")
  else
    processed='{}'
  fi

  processed=$(echo "$processed" | jq \
    --arg id "$item_id" \
    --arg timestamp "$item_updated" \
    '.[$id] = $timestamp')

  echo "$processed" > "$processed_file"
}

# Usage
for issue in $issues; do
  issue_id=$(echo "$issue" | jq -r '.number')
  issue_updated=$(echo "$issue" | jq -r '.updated_at')

  if is_processed "$issue_id" "$issue_updated"; then
    echo "Skipping already processed issue #$issue_id"
    continue
  fi

  process_issue "$issue"
  mark_processed "$issue_id" "$issue_updated"
done
```

**Benefits**:

- Avoids redundant work
- Faster execution for partially-updated datasets
- Automatic change detection

**When to use**: Workflows processing large item sets with infrequent updates

---

## Testing Strategies

### Pattern 1: Dry-Run Mode

**Problem**: Testing workflows in production risks unintended side effects.

**Solution**: Implement dry-run mode for safe testing.

```yaml
# Add workflow input for dry-run
on:
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Enable dry-run mode (no mutations)"
        required: false
        default: "false"
        type: boolean
```

```bash
# Check dry-run mode
DRY_RUN="${{ github.event.inputs.dry_run }}"

post_comment() {
  local issue=$1
  local message=$2

  if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY-RUN] Would post comment to issue #$issue: $message"
  else
    gh issue comment "$issue" --body "$message"
  fi
}

close_issue() {
  local issue=$1

  if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY-RUN] Would close issue #$issue"
  else
    gh issue close "$issue"
  fi
}

# All safe-output operations wrapped similarly
```

**Benefits**:

- Safe testing in production environment
- Validates logic without side effects
- Easy debugging of workflow behavior

**When to use**: All workflows with safe-outputs (mandatory for testing)

### Pattern 2: Canary Deployment

**Problem**: New workflow version may have bugs affecting all runs.

**Solution**: Deploy to small percentage of triggers first.

```bash
# Canary percentage (10%)
CANARY_PERCENTAGE=10

# Determine if this run is canary
run_hash=$(echo "${{ github.run_id }}" | md5sum | cut -c1-2)
run_mod=$((0x$run_hash % 100))

if (( run_mod < CANARY_PERCENTAGE )); then
  echo "⚠️ CANARY RUN - Using new workflow version"
  source /workflows/new-version.sh
else
  echo "✅ STABLE RUN - Using stable workflow version"
  source /workflows/stable-version.sh
fi
```

**Benefits**:

- Limited blast radius for bugs
- Real production validation
- Gradual rollout confidence

**When to use**: Major workflow version upgrades

### Pattern 3: Synthetic Testing

**Problem**: Workflow only tested when real events occur.

**Solution**: Generate synthetic events for testing.

```yaml
# Test workflow with synthetic data
on:
  schedule:
    - cron: "0 2 * * 0" # Weekly test run
  workflow_dispatch:
    inputs:
      test_mode:
        description: "Enable test mode with synthetic data"
        required: false
        default: "false"
```

```bash
TEST_MODE="${{ github.event.inputs.test_mode }}"

if [ "$TEST_MODE" = "true" ] || [ "${{ github.event_name }}" = "schedule" ]; then
  echo "🧪 TEST MODE - Using synthetic data"

  # Create test issue for workflow to process
  test_issue=$(gh issue create \
    --title "[TEST] Synthetic issue for workflow validation" \
    --body "This is a test issue created by the workflow for validation purposes." \
    --label "test,automated")

  # Process test issue
  process_issue "$test_issue"

  # Clean up
  gh issue close "$test_issue"
  gh issue comment "$test_issue" --body "Test completed successfully, closing."

  echo "✅ Test mode completed"
  exit 0
fi

# Normal processing
```

**Benefits**:

- Regular validation without waiting for events
- Catch regressions early
- Confidence in workflow health

**When to use**: Critical workflows, weekly/monthly validation recommended

---

## Anti-Patterns

### Anti-Pattern 1: Silent Failures

**Problem**: Workflow fails but provides no visibility.

```bash
# Bad: Silent failure
api_call || true  # Swallows error

# Good: Log and report failure
if ! api_call; then
  echo "❌ API call failed" >&2
  log_error "API call failed at $(date)"
  create_monitoring_issue "Workflow failure: API call failed"
  exit 1
fi
```

**Why it's bad**:

- Failures go unnoticed
- No audit trail for debugging
- Appears successful when it's not

### Anti-Pattern 2: Hard-Coded Values

**Problem**: Workflow tied to specific repository/environment.

```bash
# Bad: Hard-coded repository
gh issue list --repo owner/specific-repo

# Good: Use GitHub context
gh issue list --repo "${{ github.repository }}"
```

**Why it's bad**:

- Not reusable across repositories
- Breaks when repository renamed
- Requires manual editing for each use

### Anti-Pattern 3: Unbounded Operations

**Problem**: No limits on resource consumption.

```bash
# Bad: Process unlimited items
for issue in $all_issues; do
  process_issue "$issue"
done

# Good: Implement pagination and limits
max_per_run=50
count=0

for issue in $all_issues; do
  if (( count >= max_per_run )); then
    echo "Reached processing limit, deferring remaining items"
    break
  fi

  process_issue "$issue"
  ((count++))
done
```

**Why it's bad**:

- Can exceed GitHub Actions timeout (6 hours)
- May hit API rate limits
- Unpredictable resource usage

### Anti-Pattern 4: No Audit Trail

**Problem**: No record of workflow actions.

```bash
# Bad: No logging
gh issue close "$issue"

# Good: Comprehensive audit trail
echo "{\"timestamp\":\"$(date -Iseconds)\",\"action\":\"close-issue\",\"issue\":$issue}" >> memory/workflow/audit.jsonl
gh issue close "$issue"
```

**Why it's bad**:

- Can't debug issues
- No compliance trail
- Can't analyze workflow effectiveness

### Anti-Pattern 5: Using Direct Write Permissions

**Problem**: Configuring workflows with direct write permissions (`issues: write`, `discussions: write`) instead of using safe-outputs.

```yaml
# Bad: Direct write permissions (blocked in strict mode)
permissions:
  issues: write
  discussions: write

# Good: Read permissions + safe-outputs
permissions:
  contents: read
  issues: read

safe-outputs:
  create-issue:
    max: 5
  create-discussion:
    max: 1
```

**Why it's bad**:

- Violates gh-aw security model (workflows should use safe-outputs)
- No rate limiting on write operations
- No audit trail of what was created/modified
- Compilation fails in strict mode
- Can't enforce expiration policies

**Best practice**: Always use safe-outputs for write operations, never direct write permissions.

### Anti-Pattern 6: Incompatible MCP Servers in CI

**Problem**: Configuring MCP servers in `.mcp.json` that require resources unavailable in GitHub Actions (Docker, host filesystem access).

```json
// Bad: docker-mcp requires Docker daemon
{
  "mcpServers": {
    "docker-mcp": {
      "command": "uvx",
      "args": ["docker-mcp"]
    }
  }
}

// Good: Only CI-compatible servers
{
  "mcpServers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq", "mcp"]
    }
  }
}
```

**Why it's bad**:

- Causes entire workflow to fail even if agent completes successfully
- Hard to debug (MCP launch happens before main workflow)
- Wastes CI minutes on failed launches

**Best practice**: Only configure MCP servers that work in sandboxed CI environments (npm-based, API-based, built-in).

### Anti-Pattern 7: Unnecessary Lockdown Mode

**Problem**: Enabling `lockdown: true` in workflows when the default `GITHUB_TOKEN` is sufficient.

```yaml
# Bad: Lockdown mode without clear security requirement
tools:
  github:
    toolsets: [issues]
    lockdown: true  # Forces custom token requirement

# Good: Default token for standard workflows
tools:
  github:
    toolsets: [issues]
```

**Why it's bad**:

- Adds complexity and maintenance burden (need to manage custom PAT)
- Requires additional repository secrets
- Default GITHUB_TOKEN works fine for 95% of workflows
- Lockdown mode only needed for cross-repo operations or enhanced audit

**Best practice**: Only use lockdown mode when you have specific security requirements that the default token can't satisfy.

### Anti-Pattern 8: Manually Setting GITHUB_TOKEN

**Problem**: Trying to manually configure `GITHUB_TOKEN` as an environment variable or secret.

```yaml
# Bad: Manually setting GITHUB_TOKEN (unnecessary!)
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

# Good: Just declare permissions, token is automatic
permissions:
  contents: read
  issues: read
```

**Why it's bad**:

- `GITHUB_TOKEN` is automatically injected by GitHub Actions
- Manually setting it is redundant and creates confusion
- Token permissions come from `permissions:` declaration, not manual config
- Can cause subtle bugs if misconfigured

**Best practice**: Never manually set `GITHUB_TOKEN`. Just declare the permissions you need and GitHub handles the rest.

---

## Workflow Composition

### Pattern 1: Shared Prompt Components

**Problem**: Duplicating error handling logic across workflows.

**Solution**: Extract common patterns to shared files.

**File**: `.github/workflows/shared/error-handling.md`

```markdown
## Standard Error Handling

All workflows must implement:

1. **API Rate Limiting**: Check before calls, exponential backoff on 429
2. **Network Retries**: 3 attempts with 2s, 4s, 8s delays
3. **Partial Failures**: Continue processing on individual item failures
4. **Audit Logging**: Log all actions to repo-memory in JSON Lines format
```

**Usage in workflows**:

```markdown
---
# Workflow frontmatter
---

# My Workflow

@import "../shared/error-handling.md"

## Workflow-Specific Logic

...
```

### Pattern 2: Workflow Orchestration

**Problem**: Need coordination between multiple workflows.

**Solution**: Create orchestrator workflow that dispatches others.

````yaml
---
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

permissions:
  actions: write  # Can trigger other workflows
---

# Weekly Maintenance Orchestrator

Run comprehensive repository maintenance by coordinating specialized workflows:

1. **Clean stale PRs**: Trigger stale-pr-management workflow
2. **Clean deployments**: Trigger cleanup-deployments workflow
3. **Update dependencies**: Trigger dependency-updates workflow
4. **Generate reports**: Trigger weekly-summary workflow

## Execution

```bash
# Trigger workflows in sequence
workflows=(
  "stale-pr-management.lock.yml"
  "cleanup-deployments.lock.yml"
  "dependency-updates.lock.yml"
  "weekly-summary.lock.yml"
)

for workflow in "${workflows[@]}"; do
  echo "Triggering $workflow..."
  gh workflow run "$workflow"

  # Wait for completion before next
  sleep 60
done
````

````

**Benefits**:
- Coordinated execution
- Centralized scheduling
- Workflow dependency management

---

## Monitoring and Observability

### Pattern 1: Structured Logging

**Problem**: Unstructured logs hard to parse and analyze.

**Solution**: Use JSON Lines format for all logging.

```bash
log() {
  local level=$1
  local message=$2
  local metadata=${3:-{}}

  echo "{\"timestamp\":\"$(date -Iseconds)\",\"level\":\"$level\",\"message\":\"$message\",\"metadata\":$metadata}" >> memory/workflow/workflow.log
}

# Usage
log "info" "Processing issue #123" '{"issue":123,"action":"triage"}'
log "warn" "Rate limit low" '{"remaining":50,"reset_at":"2026-02-15T12:00:00Z"}'
log "error" "API call failed" '{"endpoint":"/issues","status":500}'
````

### Pattern 2: Metrics Collection

**Problem**: No visibility into workflow performance over time.

**Solution**: Collect metrics in structured format for analysis.

```bash
metrics_file="memory/workflow/metrics.jsonl"

record_metric() {
  local metric_name=$1
  local value=$2
  local tags=${3:-{}}

  echo "{\"timestamp\":\"$(date -Iseconds)\",\"metric\":\"$metric_name\",\"value\":$value,\"tags\":$tags}" >> "$metrics_file"
}

# Usage
start=$(date +%s)
process_items
end=$(date +%s)
duration=$((end - start))

record_metric "workflow.duration" "$duration" '{"workflow":"issue-triage"}'
record_metric "workflow.items_processed" "$items_count" '{"workflow":"issue-triage"}'
```

---

**These patterns represent battle-tested production practices from 100+ agentic workflows. Apply them to build robust, reliable, and maintainable automation.**
