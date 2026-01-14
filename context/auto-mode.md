# Auto Mode Operation

Auto mode enables autonomous, multi-turn execution where the agent works toward a goal without human intervention at each step.

## Enabling Auto Mode

### Via CLI

```bash
# Run with max turns limit (default: 10)
amplifier run --max-turns 20 "Implement the authentication module per the specification"

# Run with timeout
amplifier run --timeout 30m "Complete the security audit"

# Combine with bundle
amplifier run --bundle amplihack --max-turns 15 "Build and test the API"
```

### Via Session Configuration

```yaml
# In bundle or settings
session:
  max_turns: 20
  auto_mode:
    enabled: true
    stop_on_error: false
    checkpoint_interval: 5  # Checkpoint every 5 turns
```

## Auto Mode Behaviors

When auto mode is enabled, Amplifier:

1. **Continues Autonomously**: After each tool call, immediately processes results and continues
2. **Tracks Progress**: Uses todo tool to maintain task visibility
3. **Validates Incrementally**: Runs checks after each significant change
4. **Handles Errors**: Attempts recovery before stopping

## Goal-Driven Execution

Auto mode works best with clear goal definitions:

```markdown
## Good Goal (Auto Mode Friendly)

"Implement user authentication with:
- JWT tokens for session management
- Password hashing with bcrypt
- Rate limiting on login endpoint
- Tests for all auth flows

Success criteria:
- All tests pass
- No security vulnerabilities in scan
- API documentation updated"
```

## Stopping Conditions

Auto mode stops when:

1. **Max turns reached** - Configurable limit hit
2. **Goal achieved** - Success criteria met (if defined)
3. **Unrecoverable error** - Error handler gives up
4. **User interruption** - Ctrl+C or similar

## Safety Controls

### Turn Limits

```yaml
session:
  max_turns: 25        # Hard limit
  warning_turns: 20    # Warning at this point
```

### Checkpoint & Resume

Auto mode creates checkpoints that allow session resumption:

```bash
# Resume interrupted session
amplifier resume <session-id>

# List recent auto mode sessions
amplifier sessions --auto-mode
```

### XPIA Defense

The `hook-xpia-defense` module monitors for prompt injection attempts:

- Scans tool outputs for injection patterns
- Redacts suspicious content
- Alerts on high-confidence attacks

## Workflow Integration

Auto mode integrates with amplihack workflows:

### Default Workflow (Autonomous)

Use `recipes/default-workflow-autonomous.yaml` for fully autonomous execution:

```bash
amplifier tool invoke recipes \
  operation=execute \
  recipe_path=amplihack:recipes/default-workflow-autonomous.yaml \
  context='{"task": "Implement caching layer"}'
```

### Staged Workflows (Approval Gates)

Use `recipes/default-workflow.yaml` for human-in-the-loop:

```bash
amplifier tool invoke recipes \
  operation=execute \
  recipe_path=amplihack:recipes/default-workflow.yaml \
  context='{"task": "Security-critical feature"}'
```

## Best Practices

### 1. Clear Success Criteria

Define measurable success criteria so auto mode knows when to stop:

```
Success criteria:
- [ ] All unit tests pass
- [ ] Integration tests pass  
- [ ] Type checker reports no errors
- [ ] Code coverage > 80%
```

### 2. Incremental Checkpoints

For long-running tasks, structure work in phases:

```
Phase 1: Data models (checkpoint after)
Phase 2: API endpoints (checkpoint after)
Phase 3: Tests (checkpoint after)
Phase 4: Documentation
```

### 3. Error Recovery Strategy

Define fallback behavior:

```yaml
on_error:
  strategy: retry_with_simpler  # or: stop, skip, escalate
  max_retries: 3
```

### 4. Resource Limits

Set appropriate limits for the task:

```yaml
limits:
  max_file_writes: 50
  max_bash_commands: 100
  max_api_calls: 200
```

## Monitoring

### Real-time Progress

Watch auto mode progress:

```bash
# Follow session logs
amplifier logs -f <session-id>

# Watch todo progress
amplifier todos <session-id>
```

### Post-Execution Analysis

Review what auto mode did:

```bash
# Summary of session
amplifier session summary <session-id>

# Detailed events
amplifier session events <session-id> --type tool:*
```

## Example: Full Auto Mode Session

```bash
# Start auto mode with comprehensive goal
amplifier run --bundle amplihack --max-turns 30 "
Implement the user notification system:

Requirements:
- Email notifications for account events
- In-app notification center
- User preferences for notification types
- Async processing with retry logic

Constraints:
- Use existing email service integration
- Follow amplihack philosophy (ruthless simplicity)
- Tests required for all notification types

Success criteria:
- All notification types working end-to-end
- Tests passing with >80% coverage
- No N+1 queries in notification retrieval
- Documentation updated
"
```

This will trigger a multi-turn autonomous session that:
1. Analyzes requirements
2. Creates implementation plan
3. Implements each component
4. Tests incrementally
5. Validates against success criteria
6. Stops when complete or limit reached
