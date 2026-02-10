# Native Binary Trace Logging

**Optional request/response logging for Claude API calls using Anthropic's native binary with zero-overhead when disabled**

## What is Trace Logging?

Trace Logging captures detailed request and response data from Claude API calls during amplihack sessions. It uses Anthropic's official native Claude binary and LiteLLM callbacks to record interactions in structured JSONL format, enabling debugging, analysis, and compliance workflows.

## Why Use Trace Logging?

Trace Logging helps with debugging, analysis, and compliance:

✅ **Optional by default** - Disabled by default, zero performance impact when off
✅ **Minimal overhead** - <0.1ms when disabled, <10ms when enabled
✅ **Session-scoped** - Automatic JSONL files per session
✅ **Security-first** - TokenSanitizer removes API keys and sensitive data
✅ **Native binary** - Uses Anthropic's official Claude binary, no NPM dependencies
✅ **Developer-friendly** - Structured JSONL for easy parsing and analysis

## How It Works

When trace logging is enabled:

1. **Session initialization** - Creates unique trace file in `.claude/runtime/amplihack-traces/`
2. **LiteLLM callbacks** - Intercepts Claude API requests/responses
3. **Security filtering** - TokenSanitizer removes API keys and sensitive tokens
4. **JSONL writing** - Appends structured log entries to session file
5. **Session cleanup** - File closed on session end, preserved for analysis

### Performance Impact

Trace logging is designed for negligible performance impact:

```
Disabled: <0.1ms overhead per API call
Enabled:  <10ms overhead per API call (mostly I/O)

Tested with 1000 API calls:
- Disabled: 0ms total overhead
- Enabled:  ~8-9ms average per call
```

## Quick Start

### Enable Trace Logging

Trace logging is **disabled by default**. Enable it with an environment variable:

```bash
# Enable for single session
export AMPLIHACK_TRACE_LOGGING=true
amplihack

# Enable with inline variable
AMPLIHACK_TRACE_LOGGING=true amplihack

# Enable permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export AMPLIHACK_TRACE_LOGGING=true' >> ~/.bashrc
```

### View Trace Logs

Trace files are stored in `.claude/runtime/amplihack-traces/`:

```bash
# List all trace files
ls -lh .claude/runtime/amplihack-traces/

# Example output:
# trace_20260122_143022_a3f9d8.jsonl  (current session)
# trace_20260122_140815_b2c4e1.jsonl  (previous session)

# View latest trace file
tail -f .claude/runtime/amplihack-traces/trace_*.jsonl | jq .

# View specific session trace
cat .claude/runtime/amplihack-traces/trace_20260122_143022_a3f9d8.jsonl | jq .
```

### Analyze Trace Data

Each trace entry contains structured data:

```bash
# Count total API calls
cat trace_*.jsonl | wc -l

# Extract all prompts
cat trace_*.jsonl | jq -r '.request.messages[].content' 2>/dev/null

# Calculate token usage
cat trace_*.jsonl | jq '.response.usage' 2>/dev/null

# Find errors
cat trace_*.jsonl | jq 'select(.error != null)'

# Export to CSV for analysis
cat trace_*.jsonl | jq -r '[.timestamp, .request.model, .response.usage.prompt_tokens, .response.usage.completion_tokens] | @csv'
```

## Trace File Format

Each trace file uses JSONL format (newline-delimited JSON):

```jsonl
{"timestamp":"2026-01-22T14:30:22.451Z","session_id":"a3f9d8","event":"request","request":{"model":"claude-sonnet-4-5-20250929","messages":[{"role":"user","content":"Hello"}],"max_tokens":1024}}
{"timestamp":"2026-01-22T14:30:23.102Z","session_id":"a3f9d8","event":"response","response":{"id":"msg_abc123","model":"claude-sonnet-4-5-20250929","content":[{"type":"text","text":"Hello! How can I help?"}],"usage":{"prompt_tokens":12,"completion_tokens":8,"total_tokens":20}}}
```

### Trace Entry Schema

| Field        | Type     | Description                                |
| ------------ | -------- | ------------------------------------------ |
| `timestamp`  | ISO 8601 | Event timestamp                            |
| `session_id` | string   | Unique session identifier                  |
| `event`      | string   | Event type: `request`, `response`, `error` |
| `request`    | object   | Claude API request (sanitized)             |
| `response`   | object   | Claude API response (sanitized)            |
| `error`      | object   | Error details (if applicable)              |

## Common Scenarios

### Scenario 1: Debug Unexpected Responses

**Goal**: Understand why Claude responded unexpectedly.

```bash
# Enable trace logging
export AMPLIHACK_TRACE_LOGGING=true
amplihack

# Reproduce the issue
# ... interact with amplihack ...

# Find the session trace file
ls -lt .claude/runtime/amplihack-traces/ | head -2

# Analyze requests and responses
cat .claude/runtime/amplihack-traces/trace_20260122_143022_a3f9d8.jsonl | jq .

# Extract conversation flow
cat trace_*.jsonl | jq -r 'select(.event=="request") | .request.messages[] | "\(.role): \(.content)"'
```

**Result**: Complete request/response history for debugging.

---

### Scenario 2: Monitor Token Usage

**Goal**: Track token consumption across sessions.

```bash
# Enable trace logging
export AMPLIHACK_TRACE_LOGGING=true

# Run multiple sessions
amplihack
# ... work ...
# exit

# Aggregate token usage
cat .claude/runtime/amplihack-traces/*.jsonl | \
  jq -s '[.[] | select(.response.usage != null) | .response.usage] |
         {total_prompt: map(.prompt_tokens) | add,
          total_completion: map(.completion_tokens) | add,
          total: map(.total_tokens) | add}'

# Output:
# {
#   "total_prompt": 45231,
#   "total_completion": 12403,
#   "total": 57634
# }
```

**Result**: Comprehensive token usage metrics.

---

### Scenario 3: Compliance Audit Trail

**Goal**: Maintain audit trail for compliance requirements.

```bash
# Enable trace logging permanently
echo 'export AMPLIHACK_TRACE_LOGGING=true' >> ~/.bashrc

# Archive traces daily
mkdir -p ~/amplihack-audit/$(date +%Y%m%d)
cp .claude/runtime/amplihack-traces/*.jsonl ~/amplihack-audit/$(date +%Y%m%d)/

# Generate compliance report
cat ~/amplihack-audit/*/*.jsonl | \
  jq -r '[.timestamp, .session_id, .event, (.request.model // "N/A")] | @csv' > compliance-report.csv
```

**Result**: Complete audit trail with session history.

---

### Scenario 4: Disable Trace Logging (Default)

**Goal**: Run amplihack with zero trace overhead.

```bash
# Default behavior - no environment variable needed
amplihack

# Or explicitly disable if variable was previously set
unset AMPLIHACK_TRACE_LOGGING
amplihack

# Verify no trace files created
ls .claude/runtime/amplihack-traces/
# Output: ls: cannot access '.claude/runtime/amplihack-traces/': No such file or directory
```

**Result**: Zero trace overhead, no log files created.

## Security Considerations

### Automatic Sanitization

TokenSanitizer automatically removes sensitive data:

- **API keys**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- **Tokens**: Bearer tokens, session tokens
- **Credentials**: Passwords, secrets in environment variables
- **Personal data**: Email addresses, phone numbers (configurable)

### Example Sanitization

```json
// Original request
{
  "headers": {
    "x-api-key": "sk-ant-api03-abc123...",
    "authorization": "Bearer sk-proj-xyz789..."
  }
}

// Sanitized trace entry
{
  "headers": {
    "x-api-key": "[REDACTED]",
    "authorization": "[REDACTED]"
  }
}
```

### Trace File Permissions

Trace files are created with restricted permissions:

```bash
# Check trace file permissions
ls -l .claude/runtime/amplihack-traces/

# Output:
# -rw------- 1 user user 45231 Jan 22 14:30 trace_20260122_143022_a3f9d8.jsonl
#            ^^^ only owner can read/write
```

## Environment Variables

| Variable                         | Default                             | Description                          |
| -------------------------------- | ----------------------------------- | ------------------------------------ |
| `AMPLIHACK_TRACE_LOGGING`        | `false`                             | Enable/disable trace logging         |
| `AMPLIHACK_TRACE_DIR`            | `.claude/runtime/amplihack-traces/` | Trace file directory                 |
| `AMPLIHACK_TRACE_RETENTION_DAYS` | `30`                                | Auto-delete traces older than N days |

## File Naming Convention

Trace files follow a consistent naming pattern:

```
trace_YYYYMMDD_HHMMSS_SESSION.jsonl

Examples:
trace_20260122_143022_a3f9d8.jsonl
trace_20260122_151345_b4e2f1.jsonl
trace_20260123_090015_c5f3a2.jsonl

Parts:
- YYYYMMDD: Date (2026-01-22)
- HHMMSS: Time (14:30:22)
- SESSION: 6-char session ID (a3f9d8)
- .jsonl: JSONL format
```

## Trace Retention

Old trace files are automatically cleaned up:

```bash
# Check retention policy
echo $AMPLIHACK_TRACE_RETENTION_DAYS
# Output: 30 (default)

# Set custom retention
export AMPLIHACK_TRACE_RETENTION_DAYS=90

# Manual cleanup (delete traces older than 30 days)
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30 -delete
```

## Migrating from claude-trace

If you previously used the `claude-trace` NPM package, see [Migration Guide](../migration/claude-trace-to-native.md) for transition steps.

## Next Steps

- [How-To: Trace Logging](../howto/trace-logging.md) - Task-oriented recipes
- [Developer Reference: Trace Logging API](../reference/trace-logging-api.md) - Technical implementation
- [Troubleshooting: Trace Logging](../troubleshooting/trace-logging.md) - Common issues
- [Migration: claude-trace to Native](../migration/claude-trace-to-native.md) - Upgrade guide

## Related Features

- [Smart Memory Management](./smart-memory-management.md) - Automatic Node.js memory optimization
- [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) - Security best practices
- [Auto Mode Safety](../AUTOMODE_SAFETY.md) - Autonomous operation guardrails
