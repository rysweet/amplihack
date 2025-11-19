# Workflow Feedback Loops

Feedback loops are iterative patterns within workflows that repeat until success criteria are met. They enable systematic improvement through cycles of execution, evaluation, and refinement.

## What Are Workflow Feedback Loops?

A workflow feedback loop is a repeating sequence within a larger workflow that:

1. **Executes** an action or set of actions
2. **Evaluates** the results against success criteria
3. **Refines** the approach based on evaluation
4. **Repeats** until success criteria are met or iteration limits reached

Feedback loops differ from linear workflows by enabling controlled iteration rather than requiring manual re-execution of entire workflows.

## Core Components

Every feedback loop contains:

- **Entry Condition**: When to start the loop
- **Iteration Logic**: What to execute in each cycle
- **Evaluation Criteria**: How to assess success or failure
- **Refinement Strategy**: How to improve on each iteration
- **Exit Conditions**: When to stop (success or failure limits)
- **Progress Tracking**: How to communicate iteration state

## Examples from Amplihack Workflows

### 1. DEFAULT_WORKFLOW: Test → Fix → Retest Loop

**Location**: Steps 7-8 (Run Tests and Pre-commit Hooks)

**Pattern**: Execute hooks → Fix issues → Re-execute until passing

```markdown
## Test Feedback Loop

Entry Condition: Code ready for testing
Iteration:
  1. Run pre-commit hooks and tests
  2. Capture failures (linting, formatting, type errors)
  3. Fix issues based on failure type
  4. Stage fixes
Exit Conditions:
  - Success: All checks pass
  - Failure: Max iterations (3-5) reached
```

**Key Features**:
- Pre-commit-diagnostic agent orchestrates fixes
- Each iteration targets specific failure categories
- Progress tracked via TodoWrite status updates

**Example Iteration**:
```
Iteration 1: 15 linting errors, 3 type errors
→ Fix linting with ruff --fix
→ Add type annotations

Iteration 2: 2 type errors remaining
→ Add type: ignore for external library
→ Fix import order

Iteration 3: All checks pass ✓
```

### 2. INVESTIGATION_WORKFLOW: Discover → Verify → Refine Loop

**Location**: Phases 3-4 (Parallel Deep Dives → Verification)

**Pattern**: Explore code → Form hypotheses → Test understanding → Refine

```markdown
## Investigation Feedback Loop

Entry Condition: Exploration strategy defined
Iteration:
  1. Deploy parallel agents for exploration
  2. Collect findings and form hypotheses
  3. Verify hypotheses through practical tests
  4. Identify gaps in understanding
  5. Refine hypotheses based on test results
Exit Conditions:
  - Success: All Phase 1 questions answered
  - Failure: Gaps remain after verification rounds
```

**Key Features**:
- Parallel agent deployment in Phase 3
- Verification tests validate understanding
- Gaps trigger focused re-exploration

**Example Iteration**:
```
Iteration 1: Parallel Exploration
→ [analyzer(auth-module), security(auth), patterns(auth)]
→ Hypothesis: "JWT tokens stored in Redis"

Iteration 2: Verification
→ Trace token creation in code
→ Examine Redis logs
→ Refined: "JWT tokens stored in Redis with 1hr TTL"

Iteration 3: Gap Analysis
→ Question: How are tokens refreshed?
→ Deploy analyzer(token-refresh-flow)
→ Complete understanding achieved ✓
```

### 3. CI_DIAGNOSTIC_WORKFLOW: Check CI → Fix → Push → Recheck Loop

**Location**: Entire workflow (States: CHECKING → FAILING → FIXING → PUSHING → CHECKING)

**Pattern**: Monitor CI → Diagnose failures → Apply fixes → Push → Monitor again

```markdown
## CI Fix Feedback Loop

Entry Condition: Code pushed, CI triggered
Iteration:
  1. Poll CI status (smart wait with exponential backoff)
  2. Diagnose failures by category (tests, linting, types, build)
  3. Apply category-specific fixes
  4. Commit and push fixes
  5. Wait for CI to re-run
Exit Conditions:
  - Success: All CI checks pass (PR mergeable)
  - Failure: MAX_ITERATIONS (5) reached
```

**Key Features**:
- Smart polling with exponential backoff (30s → 45s → 67s...)
- Category-based diagnosis (test failures, linting, type errors, build)
- Parallel diagnostic execution for complex failures
- Clear iteration reporting (X of Y attempts)

**Example Iteration**:
```
Iteration 1/5: Initial Status
→ Tests: 5 failing
→ Linting: Passed
→ Type Check: 12 errors
→ Fix import errors, add type annotations
→ Push fixes

Iteration 2/5: Re-check CI
→ Tests: 2 failing (3 fixed)
→ Type Check: Passed ✓
→ Fix timeout in integration test
→ Push fixes

Iteration 3/5: Re-check CI
→ All checks pass ✓
→ PR mergeable, awaiting user approval
```

## Generic Feedback Loop Template

Use this template when designing new workflows with iteration needs:

```markdown
## [Workflow Name] Feedback Loop

### Entry Condition
When: [Describe when to start the loop]
Prerequisites: [What must be true to start]

### Iteration Logic (Single Cycle)

1. **Execute**
   - [ ] Action 1: [Specific executable step]
   - [ ] Action 2: [Specific executable step]
   - [ ] Capture results and outputs

2. **Evaluate**
   - [ ] Check success criteria: [What defines success?]
   - [ ] Identify failure categories: [How do failures group?]
   - [ ] Assess progress: [Are we improving?]

3. **Refine**
   - [ ] For each failure category, apply targeted fix
   - [ ] Update approach based on learnings
   - [ ] Document attempted fixes

4. **Track Progress**
   - [ ] Update TodoWrite: "Iteration X of Y: [status]"
   - [ ] Log decisions and reasoning
   - [ ] Communicate visible progress

### Exit Conditions

**Success Criteria** (Stop and proceed):
- [ ] Primary goal achieved: [Define precisely]
- [ ] All validation checks pass
- [ ] No blockers remaining

**Failure Limits** (Stop and escalate):
- MAX_ITERATIONS: [Number, typically 3-5]
- MAX_TIME: [Duration, if applicable]
- BLOCKING_ERRORS: [Unrecoverable conditions]

### Escalation Protocol

If exit via failure limits:
1. Generate diagnostic report (all iterations attempted)
2. List blockers preventing success
3. Suggest manual investigation areas
4. Provide rollback option if state corrupted
```

## Best Practices

### 1. Iteration Limits

**Always set explicit limits** to prevent infinite loops:

- **MAX_ITERATIONS**: Typically 3-5 for automated fixes, 2-3 for investigations
- **MAX_TIME**: Optional timeout for long-running operations
- **EARLY_EXIT**: Stop if same error repeats 2+ times (no progress)

```python
# Example iteration control
MAX_ITERATIONS = 5
iteration = 0
last_error = None
repeated_errors = 0

while iteration < MAX_ITERATIONS:
    result = execute_step()

    if result.success:
        break  # Success exit

    if result.error == last_error:
        repeated_errors += 1
        if repeated_errors >= 2:
            escalate("Same error repeated 3 times")
            break

    last_error = result.error
    iteration += 1

if iteration >= MAX_ITERATIONS:
    escalate("Max iterations reached")
```

### 2. Progress Tracking

**Communicate visible progress** at each iteration:

```markdown
Iteration 1 of 5: Starting diagnostics
→ 15 issues found (linting: 10, types: 5)

Iteration 2 of 5: Fixing linting issues
→ 5 issues remaining (linting: 0, types: 5)

Iteration 3 of 5: Fixing type errors
→ All issues resolved ✓
```

**Use TodoWrite** to track loop status:
- Format: `Iteration X of Y: [Current Status]`
- Update activeForm for in-progress iterations
- Mark completed when loop exits successfully

### 3. Smart Waiting

**For loops with external dependencies** (CI, API calls, builds):

```python
def smart_wait(base_delay=30, max_delay=300):
    """Exponential backoff for polling"""
    delay = base_delay
    while delay < max_delay:
        status = check_external_status()
        if status.complete:
            return status

        time.sleep(delay)
        delay *= 1.5  # Exponential growth
```

**Benefits**:
- Fast feedback for quick operations
- Patient waiting for slow operations
- Prevents API rate limiting

### 4. Failure Categorization

**Group failures by type** for targeted fixes:

```python
def diagnose_failures(results):
    categories = {
        "import_errors": [],
        "type_errors": [],
        "test_failures": [],
        "linting": []
    }

    for error in results.errors:
        category = classify_error(error)
        categories[category].append(error)

    return categories

def apply_fixes(categories):
    # Handle each category with specialized logic
    if categories["import_errors"]:
        fix_imports(categories["import_errors"])
    if categories["type_errors"]:
        fix_types(categories["type_errors"])
    # etc.
```

**Why categorize?**
- Single iteration can fix entire category
- Specialized fix strategies per category
- Clear reporting ("10 linting errors fixed")

### 5. Rollback Safety

**Always provide safe rollback** if loop exits via failure:

```bash
# Safe revert - create new commit, never force push
git log --oneline -10  # Review recent attempts
git revert HEAD~2..HEAD  # Revert last 3 commits
git commit -m "revert: rollback failed fix attempts"
git push  # Safe push of revert
```

**Never use force push** in feedback loops - destroys iteration history.

### 6. Escalation Protocol

**When loop exits via failure limits**, provide clear escalation:

```markdown
## Feedback Loop Failed After 5 Iterations

### Attempts Summary
1. Iteration 1: Fixed 10 linting errors
2. Iteration 2: Fixed 5 type errors
3. Iteration 3: Fixed 2 test failures
4. Iteration 4: Same timeout error (API)
5. Iteration 5: Same timeout error (API) - BLOCKED

### Blocking Issues
- test_integration.py::test_api_connection
- Consistently times out after 30s
- May require manual API investigation

### Suggested Actions
1. Check API health/status manually
2. Review API rate limits
3. Increase timeout threshold
4. Consider mocking API for tests

### Rollback Option
Run: git revert HEAD~4..HEAD
To undo all fix attempts and return to pre-loop state
```

## When to Use Feedback Loops

### Good Candidates

- **Iterative refinement**: Testing, fixing, CI resolution
- **Hypothesis validation**: Investigations, experiments
- **External dependencies**: Waiting for CI, APIs, builds
- **Quality gates**: Code review cycles, approval workflows

### Poor Candidates

- **Linear workflows**: No iteration needed
- **Single-shot operations**: Cannot be retried safely
- **Non-deterministic**: No clear success criteria
- **Manual tasks**: Human intervention required

## Integration with Workflows

Feedback loops integrate into larger workflows as **sub-workflows**:

```markdown
## Example: DEFAULT_WORKFLOW with Embedded Loop

Step 1: Requirements Clarification (linear)
Step 2: GitHub Issue Creation (linear)
Step 3: Worktree Setup (linear)
Step 4: Research and Design (linear)
Step 5: Implementation (linear)
Step 6: Refactor (linear)
Step 7: Testing → FEEDBACK LOOP → until passing
Step 8: Mandatory Local Testing (linear)
Step 9: Commit and Push (linear)
Step 10: Open PR (linear)
Step 11-13: Review cycles (could be feedback loop)
Step 14: CI Status → FEEDBACK LOOP → until mergeable
Step 15: Final Cleanup (linear)
```

**Key points**:
- Loops embedded at specific steps
- Workflow pauses at loop until exit condition
- Loop failure can fail entire workflow
- Loop success allows workflow to continue

## Anti-Patterns to Avoid

### 1. Infinite Loops
```python
# BAD - no exit condition
while True:
    fix_and_retry()

# GOOD - explicit limits
for iteration in range(MAX_ITERATIONS):
    if fix_and_retry():
        break
```

### 2. Silent Failures
```python
# BAD - failures hidden
try:
    result = fix_issue()
except Exception:
    pass  # Silent failure

# GOOD - track and report
try:
    result = fix_issue()
except Exception as e:
    log_failure(iteration, e)
    if should_escalate(e):
        raise
```

### 3. Blind Iteration
```python
# BAD - same approach every time
for i in range(5):
    run_same_fix()  # Won't help

# GOOD - adaptive refinement
for i in range(5):
    diagnosis = analyze_failure()
    fix = select_strategy(diagnosis)
    apply_fix(fix)
```

### 4. No Progress Tracking
```python
# BAD - user sees nothing
while not done:
    work()

# GOOD - visible progress
for i in range(MAX_ITERATIONS):
    TodoWrite(f"Iteration {i+1} of {MAX_ITERATIONS}: Working...")
    work()
```

## Success Metrics

Track these metrics to validate feedback loop effectiveness:

- **Convergence Rate**: Percentage that reach success within MAX_ITERATIONS
- **Average Iterations**: How many cycles typically needed
- **First-Pass Success**: Percentage that succeed on iteration 1
- **Escalation Rate**: Percentage requiring manual intervention
- **Time to Success**: Total duration from entry to exit

**Example Dashboard**:
```
CI Feedback Loop Metrics (Last 30 Days)
- Convergence Rate: 87% (52 of 60 PRs)
- Average Iterations: 2.3
- First-Pass Success: 35%
- Escalation Rate: 13%
- Time to Success: 14 minutes (median)
```

## Remember

Feedback loops are powerful tools for systematic iteration, but they require careful design:

- **Always set explicit limits** (iterations, time, repeated failures)
- **Track and communicate progress** visibly at each cycle
- **Categorize failures** for targeted fixes
- **Provide escalation paths** when limits reached
- **Enable safe rollback** if loop corrupts state
- **Measure effectiveness** to validate loop value

Well-designed feedback loops transform brittle one-shot operations into resilient, self-healing workflows.
