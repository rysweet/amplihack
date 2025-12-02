# Remote Sessions CLI Reference

Complete command reference for `amplihack remote` session management.

## Command Overview

```
amplihack remote <command> [options] [arguments]

Commands:
  list       List all sessions
  start      Start one or more detached sessions
  output     View session output
  kill       Terminate a session
  status     Show pool status
  prime      Pre-warm VMs (Phase 2)
```

## Commands

### amplihack remote list

List all tracked sessions.

```bash
amplihack remote list [OPTIONS]
```

**Options:**

| Option      | Type   | Default | Description                                               |
| ----------- | ------ | ------- | --------------------------------------------------------- |
| `--status`  | Choice | all     | Filter by status: running, completed, failed, killed, all |
| `--json`    | Flag   | False   | Output as JSON                                            |
| `--verbose` | Flag   | False   | Show full prompts and details                             |

**Examples:**

```bash
# List all sessions
amplihack remote list

# List only running sessions
amplihack remote list --status running

# JSON output for scripting
amplihack remote list --json

# Verbose output with full prompts
amplihack remote list --verbose
```

**Output Format:**

```
SESSION                    VM                              STATUS    AGE     PROMPT
sess-20251125-143022-abc   amplihack-user-20251125-1430    running   5m      implement user auth...
sess-20251125-143025-def   amplihack-user-20251125-1430    running   3m      add pagination to...
sess-20251125-140000-xyz   amplihack-user-20251125-1400    completed 2h      write unit tests...
```

---

### amplihack remote start

Start one or more tasks as detached tmux sessions.

```bash
amplihack remote start [OPTIONS] PROMPTS...
```

**Arguments:**

| Argument  | Required | Description                               |
| --------- | -------- | ----------------------------------------- |
| `PROMPTS` | Yes      | One or more task prompts (quoted strings) |

**Options:**

| Option        | Type    | Default | Description                                       |
| ------------- | ------- | ------- | ------------------------------------------------- |
| `--vm-size`   | Choice  | l       | VM size: s, m, l, xl                              |
| `--region`    | String  | None    | Azure region (uses default if not specified)      |
| `--max-turns` | Integer | 10      | Maximum turns for auto mode                       |
| `--timeout`   | Integer | 120     | Timeout in minutes                                |
| `--command`   | Choice  | auto    | Amplihack command: auto, ultrathink, analyze, fix |

**Examples:**

```bash
# Single task
amplihack remote start "implement user authentication"

# Multiple tasks
amplihack remote start "task one" "task two" "task three"

# With custom options
amplihack remote start --vm-size l --max-turns 20 "complex refactoring"

# Use ultrathink mode
amplihack remote start --command ultrathink "analyze architecture"

# Specify region
amplihack remote start --region eastus "my task"
```

**Output:**

```
Starting 2 session(s)...

[1/2] sess-20251125-143022-abc
  VM: amplihack-user-20251125-143000 (reused)
  Prompt: implement user authentication
  Status: running

[2/2] sess-20251125-143025-def
  VM: amplihack-user-20251125-143000 (reused)
  Prompt: add pagination to API
  Status: running

Sessions started. Use 'amplihack remote list' to monitor.
```

---

### amplihack remote output

View output from a session via tmux capture-pane.

```bash
amplihack remote output [OPTIONS] SESSION_ID
```

**Arguments:**

| Argument     | Required | Description           |
| ------------ | -------- | --------------------- |
| `SESSION_ID` | Yes      | Session ID to observe |

**Options:**

| Option           | Type    | Default | Description                   |
| ---------------- | ------- | ------- | ----------------------------- |
| `--lines`, `-n`  | Integer | 100     | Number of lines to capture    |
| `--follow`, `-f` | Flag    | False   | Follow output (poll every 5s) |
| `--raw`          | Flag    | False   | Output without formatting     |

**Examples:**

```bash
# Get last 100 lines
amplihack remote output sess-20251125-143022-abc

# Get last 500 lines
amplihack remote output sess-20251125-143022-abc --lines 500

# Follow output (Ctrl+C to stop)
amplihack remote output sess-20251125-143022-abc --follow

# Raw output for piping
amplihack remote output sess-20251125-143022-abc --raw > output.log
```

**Output:**

```
=== Session: sess-20251125-143022-abc ===
VM: amplihack-user-20251125-143000
Status: running
Captured: 2025-11-25 14:35:22 (100 lines)

Step 5: Research and Design - Analyzing codebase...
  [architect] Examining authentication patterns
  [architect] Found 3 existing auth modules
  ...
```

---

### amplihack remote kill

Terminate a running session.

```bash
amplihack remote kill [OPTIONS] SESSION_ID
```

**Arguments:**

| Argument     | Required | Description             |
| ------------ | -------- | ----------------------- |
| `SESSION_ID` | Yes      | Session ID to terminate |

**Options:**

| Option    | Type | Default | Description                             |
| --------- | ---- | ------- | --------------------------------------- |
| `--force` | Flag | False   | Force kill (SIGKILL instead of SIGTERM) |

**Examples:**

```bash
# Graceful termination
amplihack remote kill sess-20251125-143022-abc

# Force termination
amplihack remote kill sess-20251125-143022-abc --force
```

**Output:**

```
Killing session: sess-20251125-143022-abc
  Sending SIGTERM...
  Session terminated.
Status updated: killed
```

---

### amplihack remote status

Show pool status and VM utilization.

```bash
amplihack remote status [OPTIONS]
```

**Options:**

| Option   | Type | Default | Description    |
| -------- | ---- | ------- | -------------- |
| `--json` | Flag | False   | Output as JSON |

**Examples:**

```bash
# Show status
amplihack remote status

# JSON output
amplihack remote status --json
```

**Output:**

```
=== Remote Session Pool Status ===

VMs: 2 total
  amplihack-user-20251125-143000 (l, eastus)
    Sessions: 2/4 (50% capacity)
    Memory: 32GB/128GB used
    Age: 35m

  amplihack-user-20251125-140000 (l, westus3)
    Sessions: 1/4 (25% capacity)
    Memory: 16GB/128GB used
    Age: 2h

Sessions: 3 total
  Running: 3
  Completed: 0
  Failed: 0

Total Capacity: 5/8 slots available
```

---

### amplihack remote prime (Future Enhancement)

Pre-warm VMs to reduce cold start latency.

```bash
amplihack remote prime [OPTIONS]
```

**Options:**

| Option      | Type    | Default | Description            |
| ----------- | ------- | ------- | ---------------------- |
| `--count`   | Integer | 1       | Number of VMs to prime |
| `--vm-size` | Choice  | l       | VM size: s, m, l, xl   |
| `--region`  | String  | None    | Azure region           |

**Examples:**

```bash
# Prime 3 L-size VMs
amplihack remote prime --count 3 --vm-size l

# Prime in specific region
amplihack remote prime --count 2 --region eastus
```

**Note:** This command is planned for a future enhancement. Currently, VMs are provisioned on-demand with intelligent pooling and reuse.

---

## Environment Variables

| Variable                  | Description                      | Default                          |
| ------------------------- | -------------------------------- | -------------------------------- |
| `ANTHROPIC_API_KEY`       | API key for Claude (required)    | None                             |
| `AMPLIHACK_REMOTE_STATE`  | State file location              | `~/.amplihack/remote-state.json` |
| `AMPLIHACK_AZURE_REGIONS` | Comma-separated fallback regions | westus3,eastus,centralus         |
| `AMPLIHACK_VM_SIZE`       | Default VM size                  | l                                |

## Exit Codes

| Code | Meaning              |
| ---- | -------------------- |
| 0    | Success              |
| 1    | General error        |
| 2    | Invalid arguments    |
| 3    | Session not found    |
| 4    | VM not reachable     |
| 5    | Azure quota exceeded |
| 130  | Interrupted (Ctrl+C) |

## State File Format

Location: `~/.amplihack/remote-state.json`

```json
{
  "sessions": {
    "sess-20251125-143022-abc": {
      "session_id": "sess-20251125-143022-abc",
      "vm_name": "amplihack-user-20251125-143000",
      "workspace": "/workspace/sess-20251125-143022-abc",
      "tmux_session": "sess-20251125-143022-abc",
      "prompt": "implement user authentication",
      "command": "auto",
      "max_turns": 10,
      "status": "running",
      "memory_mb": 16384,
      "created_at": "2025-11-25T14:30:22Z",
      "started_at": "2025-11-25T14:30:45Z",
      "completed_at": null,
      "exit_code": null
    }
  },
  "vm_pool": {
    "amplihack-user-20251125-143000": {
      "size": "Standard_D4s_v3",
      "capacity": 4,
      "active_sessions": [
        "sess-20251125-143022-abc",
        "sess-20251125-143025-def"
      ],
      "region": "westus3",
      "created_at": "2025-11-25T14:30:00Z"
    }
  }
}
```

**Note:** VM pool tracking with capacity management is now available in Phase 2.

## Memory Management

| VM Size | Total RAM | Max Sessions | Per Session |
| ------- | --------- | ------------ | ----------- |
| s       | 32GB      | 1            | 32GB        |
| m       | 64GB      | 2            | 32GB        |
| l       | 128GB     | 4            | 32GB        |
| xl      | 256GB     | 8            | 32GB        |

Memory is set via `NODE_OPTIONS="--max-old-space-size=32768"` in each tmux session (32GB).

## tmux Session Structure

Each session creates a tmux session named after the session ID:

```bash
# List tmux sessions on VM (for debugging)
azlin connect amplihack-user-xxx "tmux ls"

# Attach to session (for debugging)
azlin connect amplihack-user-xxx "tmux attach -t sess-20251125-143022-abc"

# Capture pane content manually
azlin connect amplihack-user-xxx "tmux capture-pane -t sess-20251125-143022-abc -p"
```

## Troubleshooting

### Session stuck in "pending"

**Symptom**: Session shows `pending` status for >5 minutes.

**Cause**: VM provisioning may have failed or context transfer stalled.

**Solution**:

```bash
amplihack remote kill sess-xxx
amplihack remote start "same prompt"
```

### "Session not found on VM"

**Symptom**: `output` command fails with session not found.

**Cause**: tmux session crashed or was killed externally.

**Solution**: Check session status; if completed/failed, retrieve results manually.

### Azure quota exceeded

**Symptom**: Start fails with quota error.

**Cause**: Subscription has reached VM quota for the region.

**Solution**: Use `--region` to try a different region, or clean up unused VMs:

```bash
azlin list
azlin kill amplihack-user-xxx
```

### State file corruption

**Symptom**: Commands fail with JSON parse errors.

**Cause**: State file was corrupted (partial write, disk issue).

**Solution**: Delete and recreate state:

```bash
rm ~/.amplihack/remote-state.json
# Sessions on VMs will continue but won't be tracked locally
```
