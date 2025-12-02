# Remote Sessions Tutorial

This tutorial walks through common remote session workflows with real examples and expected outputs.

## Prerequisites

Before starting this tutorial, ensure you have:

1. **azlin installed and configured**

   ```bash
   # Install via uvx from GitHub (not available on PyPI)
   uvx --from git+https://github.com/rysweet/azlin --python 3.11 azlin --help

   # Or create persistent wrapper script
   cat > /usr/local/bin/azlin << 'EOF'
#!/bin/bash
exec uvx --from git+https://github.com/rysweet/azlin --python 3.11 azlin "$@"
EOF
   chmod +x /usr/local/bin/azlin

   # Configure Azure authentication
   azlin auth setup
   ```

2. **Azure CLI authenticated**

   ```bash
   az login
   # Select your subscription
   az account set --subscription "Your Subscription Name"
   ```

3. **ANTHROPIC_API_KEY set**

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

4. **amplihack installed**

   ```bash
   pip install amplihack
   ```

## Tutorial 1: Start and Monitor a Single Session

**Goal**: Start a remote task, monitor its progress, and view the final result.

### Step 1: Start the Session

```bash
amplihack remote start "create a simple hello world Python script"
```

**Expected Output**:

```
Starting 1 session(s)...

[1/1] sess-20251202-083022-a1b
  VM: amplihack-azureuser-20251202-083000 (provisioning new VM)
  Prompt: create a simple hello world Python script
  Status: pending

Provisioning VM... (this may take 4-7 minutes)
VM ready: amplihack-azureuser-20251202-083000
Session started on VM.

Sessions started. Use 'amplihack remote list' to monitor.
```

### Step 2: List Active Sessions

```bash
amplihack remote list
```

**Expected Output**:

```
SESSION                    VM                              STATUS    AGE     PROMPT
sess-20251202-083022-a1b   amplihack-azureuser-20251202... running   2m      create a simple hello...
```

### Step 3: View Session Output

```bash
amplihack remote output sess-20251202-083022-a1b
```

**Expected Output**:

```
=== Session: sess-20251202-083022-a1b ===
VM: amplihack-azureuser-20251202-083000
Status: running
Captured: 2025-12-02 08:32:45 (100 lines)

Step 1: Rewrite and Clarify Requirements
  [prompt-writer] Analyzing task: "create a simple hello world Python script"
  [prompt-writer] Task classification: simple implementation
  [prompt-writer] Success criteria: Python script that prints "Hello, World!"

Step 2: Create GitHub Issue
  Creating issue: "Create Hello World Python script"
  Issue created: #123

Step 3: Setup Worktree and Branch
  Creating branch: feat/issue-123-hello-world
  Branch created and pushed.

Step 4: Research and Design
  [architect] This is a simple script, no complex design needed
  [architect] Will create hello.py with single print statement

Step 5: Implement the Solution
  [builder] Creating hello.py...
  [builder] Implementation complete.

...
```

### Step 4: Follow Output in Real-Time

```bash
amplihack remote output sess-20251202-083022-a1b --follow
```

**Expected Behavior**:

- Output refreshes every 5 seconds
- New lines appear as work progresses
- Press Ctrl+C to stop following

### Step 5: Check When Session Completes

```bash
amplihack remote list
```

**Expected Output** (after completion):

```
SESSION                    VM                              STATUS     AGE     PROMPT
sess-20251202-083022-a1b   amplihack-azureuser-20251202... completed  15m     create a simple hello...
```

### Step 6: View Final Output

```bash
amplihack remote output sess-20251202-083022-a1b --lines 500
```

**Expected Output** (final lines):

```
Step 21: Ensure PR is Mergeable
  [reviewer] All checks passing
  [reviewer] PR is mergeable

Task completed successfully.
PR #45 ready for merge: https://github.com/user/repo/pull/45
```

## Tutorial 2: Run Multiple Sessions in Parallel

**Goal**: Start multiple tasks simultaneously and monitor them.

### Step 1: Start Multiple Sessions

```bash
amplihack remote start \
  "implement user authentication" \
  "add pagination to API" \
  "write unit tests for database layer"
```

**Expected Output**:

```
Starting 3 session(s)...

[1/3] sess-20251202-084522-x1y
  VM: amplihack-azureuser-20251202-084500 (provisioning new VM)
  Prompt: implement user authentication
  Status: pending

[2/3] sess-20251202-084525-x2y
  VM: amplihack-azureuser-20251202-084500 (reused)
  Prompt: add pagination to API
  Status: pending

[3/3] sess-20251202-084528-x3y
  VM: amplihack-azureuser-20251202-084500 (reused)
  Prompt: write unit tests for database layer
  Status: pending

VM provisioning in progress...
All sessions started on VM: amplihack-azureuser-20251202-084500

Sessions started. Use 'amplihack remote list' to monitor.
```

**Key Observation**: All 3 sessions share the same VM because they fit within the L-size capacity (4 sessions max).

### Step 2: Monitor All Sessions

```bash
amplihack remote list
```

**Expected Output**:

```
SESSION                    VM                              STATUS    AGE     PROMPT
sess-20251202-084522-x1y   amplihack-azureuser-20251202... running   5m      implement user auth...
sess-20251202-084525-x2y   amplihack-azureuser-20251202... running   5m      add pagination to...
sess-20251202-084528-x3y   amplihack-azureuser-20251202... running   5m      write unit tests for...
```

### Step 3: Check Pool Status

```bash
amplihack remote status
```

**Expected Output**:

```
=== Remote Session Pool Status ===

VMs: 1 total
  amplihack-azureuser-20251202-084500 (l, westus3)
    Sessions: 3/4 (75% capacity)
    Memory: 48GB/128GB used
    Age: 10m

Sessions: 3 total
  Running: 3
  Completed: 0
  Failed: 0

Total Capacity: 1/4 slots available
```

### Step 4: View Specific Session Output

```bash
amplihack remote output sess-20251202-084522-x1y
```

**Expected Output**: Session-specific output for the user authentication task.

### Step 5: Monitor Until Completion

```bash
# Watch sessions complete over time
watch -n 10 'amplihack remote list'
```

**Expected Behavior**: List refreshes every 10 seconds, showing sessions transitioning from `running` to `completed`.

## Tutorial 3: Handle Session Failures

**Goal**: Learn how to identify and handle failed sessions.

### Step 1: Start a Session That May Fail

```bash
amplihack remote start "implement feature X with intentionally vague requirements"
```

### Step 2: Monitor Session

```bash
amplihack remote list --status running
```

### Step 3: Check Output for Errors

```bash
amplihack remote output sess-xxx --lines 200
```

**Expected Output** (if session encounters issues):

```
Error: Ambiguous requirements detected
  [ambiguity] Requirement "feature X" lacks specificity
  [ambiguity] Cannot proceed without clarification

Session paused, awaiting user input.
```

### Step 4: Kill the Session

If the session is stuck or needs to be restarted:

```bash
amplihack remote kill sess-xxx
```

**Expected Output**:

```
Killing session: sess-xxx
  Sending SIGTERM...
  Session terminated.
Status updated: killed
```

### Step 5: Restart with Clearer Requirements

```bash
amplihack remote start "implement user profile page with avatar upload and bio editing"
```

## Tutorial 4: Pool Capacity Management

**Goal**: Understand VM capacity limits and how sessions distribute across VMs.

### Step 1: Fill a VM to Capacity

```bash
# Start 4 sessions (fills one L-size VM)
amplihack remote start \
  "task 1" \
  "task 2" \
  "task 3" \
  "task 4"
```

**Expected Output**:

```
Starting 4 session(s)...
All 4 sessions allocated to amplihack-azureuser-xxx (4/4 capacity)
```

### Step 2: Check Pool Status

```bash
amplihack remote status
```

**Expected Output**:

```
=== Remote Session Pool Status ===

VMs: 1 total
  amplihack-azureuser-20251202-090000 (l, westus3)
    Sessions: 4/4 (100% capacity)
    Memory: 64GB/128GB used
    Age: 5m

Sessions: 4 total
  Running: 4
  Completed: 0
  Failed: 0

Total Capacity: 0/4 slots available (FULL)
```

### Step 3: Start a Fifth Session

```bash
amplihack remote start "task 5"
```

**Expected Output**:

```
Starting 1 session(s)...

No capacity available on existing VMs.
Provisioning new VM... (this may take 4-7 minutes)

[1/1] sess-20251202-090822-z5z
  VM: amplihack-azureuser-20251202-090800 (provisioning new VM)
  Status: pending
```

**Key Observation**: When all VMs are at capacity, a new VM is provisioned automatically.

### Step 4: View Pool with Multiple VMs

```bash
amplihack remote status
```

**Expected Output**:

```
=== Remote Session Pool Status ===

VMs: 2 total
  amplihack-azureuser-20251202-090000 (l, westus3)
    Sessions: 4/4 (100% capacity)
    Memory: 64GB/128GB used
    Age: 15m

  amplihack-azureuser-20251202-090800 (l, westus3)
    Sessions: 1/4 (25% capacity)
    Memory: 16GB/128GB used
    Age: 2m

Sessions: 5 total
  Running: 5
  Completed: 0
  Failed: 0

Total Capacity: 3/8 slots available
```

## Tutorial 5: Long-Running Overnight Tasks

**Goal**: Start a task at end of day and review results next morning.

### Step 1: Evening - Start Long-Running Task

```bash
amplihack remote start --vm-size l --max-turns 50 \
  "comprehensive refactoring of authentication system with full test coverage"
```

**Expected Output**:

```
Starting 1 session(s)...

[1/1] sess-20251202-170022-eve
  VM: amplihack-azureuser-20251202-170000 (provisioning new VM)
  Prompt: comprehensive refactoring of...
  Status: pending

Session started. Will run overnight.
```

### Step 2: Evening - Verify Session Running

```bash
amplihack remote list
```

**Expected Output**:

```
SESSION                    VM                              STATUS    AGE     PROMPT
sess-20251202-170022-eve   amplihack-azureuser-20251202... running   2m      comprehensive refacto...
```

### Step 3: Evening - Close Laptop

You can now:

- Close your laptop
- Shut down your terminal
- Disconnect from network
- Go home

The session continues running on the remote VM.

### Step 4: Next Morning - Check Session Status

```bash
amplihack remote list
```

**Expected Output**:

```
SESSION                    VM                              STATUS     AGE     PROMPT
sess-20251202-170022-eve   amplihack-azureuser-20251202... completed  14h     comprehensive refacto...
```

### Step 5: Next Morning - Review Results

```bash
amplihack remote output sess-20251202-170022-eve --lines 1000 > overnight-results.txt
```

**Expected Output**: Full session output saved to `overnight-results.txt` for review.

### Step 6: Next Morning - Check PR

```bash
# Extract PR URL from output
grep "PR #" overnight-results.txt
```

**Expected Output**:

```
PR #789 ready for merge: https://github.com/user/repo/pull/789
```

## Tutorial 6: Using JSON Output for Scripting

**Goal**: Parse session data programmatically.

### Step 1: List Sessions as JSON

```bash
amplihack remote list --json
```

**Expected Output**:

```json
{
  "sessions": [
    {
      "session_id": "sess-20251202-083022-a1b",
      "vm_name": "amplihack-azureuser-20251202-083000",
      "status": "running",
      "prompt": "create a simple hello world Python script",
      "created_at": "2025-12-02T08:30:22Z",
      "age_minutes": 45
    }
  ]
}
```

### Step 2: Get Pool Status as JSON

```bash
amplihack remote status --json
```

**Expected Output**:

```json
{
  "total_vms": 1,
  "total_capacity": 4,
  "active_sessions": 2,
  "available_capacity": 2,
  "vms": [
    {
      "name": "amplihack-azureuser-20251202-083000",
      "size": "Standard_D4s_v3",
      "region": "westus3",
      "capacity": 4,
      "active_sessions": 2,
      "available_capacity": 2
    }
  ]
}
```

### Step 3: Script to Monitor Sessions

```bash
#!/bin/bash
# monitor-sessions.sh

while true; do
    RUNNING=$(amplihack remote list --json | jq '.sessions | map(select(.status == "running")) | length')
    echo "$(date): $RUNNING sessions running"

    if [ "$RUNNING" -eq 0 ]; then
        echo "All sessions completed!"
        break
    fi

    sleep 60
done
```

## Common Issues and Solutions

### Issue 1: "Azure quota exceeded"

**Symptom**:

```
Error: Azure quota exceeded in region westus3
Hint: Try a different region with --region eastus
```

**Solution**:

```bash
# Try different region
amplihack remote start --region eastus "your task"

# Or check current quota
az vm list-usage --location westus3 -o table
```

### Issue 2: Session stuck in "pending"

**Symptom**: Session shows "pending" for >10 minutes.

**Solution**:

```bash
# Kill and restart
amplihack remote kill sess-xxx
amplihack remote start "same task"
```

### Issue 3: Cannot see session output

**Symptom**:

```
Error: Session sess-xxx not found on VM
```

**Solution**:

```bash
# Check session status first
amplihack remote list

# If completed, session may have been cleaned up
# Review final output before it completes
```

## Best Practices

### 1. Use Descriptive Prompts

**Bad**:

```bash
amplihack remote start "fix bug"
```

**Good**:

```bash
amplihack remote start "fix authentication token expiration bug in /api/auth/refresh endpoint"
```

### 2. Monitor Long-Running Tasks

```bash
# Set up periodic checks
watch -n 300 'amplihack remote output sess-xxx --lines 50'
```

### 3. Clean Up Completed Sessions

```bash
# After reviewing results, kill old sessions
amplihack remote list --status completed | grep sess- | cut -d' ' -f1 | xargs -n1 amplihack remote kill
```

### 4. Use Appropriate VM Sizes

- **s** (32GB): Quick tests, single simple task
- **m** (64GB): Standard development work, 2 concurrent tasks
- **l** (128GB): Complex tasks, 4 parallel sessions (recommended)
- **xl** (256GB): Heavy workloads, 8+ parallel sessions

**Cost optimization**: L-size provides best cost per session ($0.25/hr per session). Only use XL for truly parallel workloads.

## Next Steps

- Review [CLI Reference](CLI_REFERENCE.md) for complete command documentation
- Read [User Guide](README.md) for architecture details
- Check [Developer Guide](../../.claude/tools/amplihack/remote/README.md) for implementation details
- Report issues at [GitHub Issues](https://github.com/amplihack/amplihack/issues)
