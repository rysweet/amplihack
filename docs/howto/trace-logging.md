# How to Use Trace Logging

Step-by-step guide for enabling, analyzing, and managing Claude API trace logs.

## Quick Reference

| Task                  | Command                                                                           |
| --------------------- | --------------------------------------------------------------------------------- |
| Enable trace logging  | `export AMPLIHACK_TRACE_LOGGING=true`                                             |
| Disable trace logging | `unset AMPLIHACK_TRACE_LOGGING`                                                   |
| View latest trace     | `tail -f .claude/runtime/amplihack-traces/trace_*.jsonl \| jq .`                  |
| List all traces       | `ls -lh .claude/runtime/amplihack-traces/`                                        |
| Count API calls       | `cat trace_*.jsonl \| wc -l`                                                      |
| Calculate token usage | `cat trace_*.jsonl \| jq '.response.usage'`                                       |
| Find errors           | `cat trace_*.jsonl \| jq 'select(.error != null)'`                                |
| Clean old traces      | `find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30 -delete` |

## Common Tasks

### Task 1: Enable Trace Logging for a Single Session

**Goal**: Debug a specific issue without enabling traces permanently.

**Steps**:

1. Enable trace logging inline:

   ```bash
   AMPLIHACK_TRACE_LOGGING=true amplihack
   ```

2. Reproduce your issue in the session.

3. Exit amplihack:

   ```
   exit
   ```

4. Locate the trace file:

   ```bash
   ls -lt .claude/runtime/amplihack-traces/ | head -2

   # Output:
   # total 156
   # -rw------- 1 user user 45231 Jan 22 14:30 trace_20260122_143022_a3f9d8.jsonl
   ```

5. Analyze the trace:

   ```bash
   cat .claude/runtime/amplihack-traces/trace_20260122_143022_a3f9d8.jsonl | jq .
   ```

**Result**: Trace file contains all API calls from that session.

---

### Task 2: Monitor Token Usage in Real-Time

**Goal**: Watch token consumption as you work.

**Steps**:

1. Enable trace logging:

   ```bash
   export AMPLIHACK_TRACE_LOGGING=true
   ```

2. Open a second terminal window.

3. Start monitoring:

   ```bash
   # Terminal 2
   cd /path/to/your/project
   watch -n 5 'cat .claude/runtime/amplihack-traces/*.jsonl | \
     jq -s "[.[] | select(.response.usage != null) | .response.usage] | \
            {calls: length, \
             total_prompt: map(.prompt_tokens) | add, \
             total_completion: map(.completion_tokens) | add, \
             total: map(.total_tokens) | add}"'
   ```

4. Work in amplihack in terminal 1.

5. Watch live token updates every 5 seconds in terminal 2.

**Result**: Real-time token usage dashboard.

---

### Task 3: Extract Conversation History

**Goal**: Export all prompts and responses from a session.

**Steps**:

1. Identify the trace file:

   ```bash
   ls -lt .claude/runtime/amplihack-traces/ | head -2
   ```

2. Extract conversation:

   ```bash
   cat .claude/runtime/amplihack-traces/trace_20260122_143022_a3f9d8.jsonl | \
     jq -r 'select(.event=="request" or .event=="response") |
            if .event=="request" then
              (.request.messages[] | "USER: \(.content)")
            else
              (.response.content[]? | "ASSISTANT: \(.text)")
            end'
   ```

3. Save to file:

   ```bash
   cat trace_*.jsonl | \
     jq -r 'select(.event=="request" or .event=="response") |
            if .event=="request" then
              (.request.messages[] | "USER: \(.content)")
            else
              (.response.content[]? | "ASSISTANT: \(.text)")
            end' > conversation.txt
   ```

**Result**: Readable conversation transcript in `conversation.txt`.

---

### Task 4: Find Failed API Calls

**Goal**: Identify and debug errors.

**Steps**:

1. Search for errors:

   ```bash
   cat .claude/runtime/amplihack-traces/*.jsonl | \
     jq 'select(.error != null)'
   ```

2. Extract error details:

   ```bash
   cat trace_*.jsonl | \
     jq 'select(.error != null) |
         {timestamp, session_id, error: .error.message, code: .error.code}'
   ```

3. Count errors by type:

   ```bash
   cat trace_*.jsonl | \
     jq -r 'select(.error != null) | .error.code' | \
     sort | uniq -c
   ```

**Result**: List of all errors with timestamps and details.

---

### Task 5: Generate Daily Token Report

**Goal**: Track token usage for cost analysis.

**Steps**:

1. Enable permanent trace logging:

   ```bash
   echo 'export AMPLIHACK_TRACE_LOGGING=true' >> ~/.bashrc
   source ~/.bashrc
   ```

2. Create report script:

   ```bash
   cat > ~/bin/amplihack-token-report.sh <<'EOF'
   #!/bin/bash

   TRACE_DIR="${1:-.claude/runtime/amplihack-traces}"

   echo "=== amplihack Token Usage Report ==="
   echo "Generated: $(date)"
   echo

   echo "By Session:"
   for trace in "$TRACE_DIR"/trace_*.jsonl; do
     if [ -f "$trace" ]; then
       echo "  $(basename "$trace"):"
       cat "$trace" | \
         jq -s '[.[] | select(.response.usage != null) | .response.usage] |
                {calls: length, prompt: map(.prompt_tokens) | add,
                 completion: map(.completion_tokens) | add,
                 total: map(.total_tokens) | add}'
     fi
   done

   echo
   echo "Total Across All Sessions:"
   cat "$TRACE_DIR"/*.jsonl | \
     jq -s '[.[] | select(.response.usage != null) | .response.usage] |
            {total_calls: length,
             total_prompt: map(.prompt_tokens) | add,
             total_completion: map(.completion_tokens) | add,
             total_tokens: map(.total_tokens) | add}'
   EOF

   chmod +x ~/bin/amplihack-token-report.sh
   ```

3. Run the report:

   ```bash
   ~/bin/amplihack-token-report.sh

   # Output:
   # === amplihack Token Usage Report ===
   # Generated: Wed Jan 22 14:30:45 PST 2026
   #
   # By Session:
   #   trace_20260122_143022_a3f9d8.jsonl:
   #     {"calls": 25, "prompt": 12034, "completion": 3421, "total": 15455}
   #   trace_20260122_151345_b4e2f1.jsonl:
   #     {"calls": 18, "prompt": 8956, "completion": 2187, "total": 11143}
   #
   # Total Across All Sessions:
   #   {"total_calls": 43, "total_prompt": 20990, "total_completion": 5608, "total_tokens": 26598}
   ```

**Result**: Automated token usage reporting.

---

### Task 6: Archive Traces for Compliance

**Goal**: Preserve traces for audit requirements.

**Steps**:

1. Create archive script:

   ```bash
   cat > ~/bin/amplihack-archive-traces.sh <<'EOF'
   #!/bin/bash

   ARCHIVE_DIR="${AMPLIHACK_ARCHIVE_DIR:-$HOME/amplihack-audit}"
   TRACE_DIR=".claude/runtime/amplihack-traces"
   DATE=$(date +%Y%m%d)

   mkdir -p "$ARCHIVE_DIR/$DATE"

   if [ -d "$TRACE_DIR" ]; then
     cp "$TRACE_DIR"/*.jsonl "$ARCHIVE_DIR/$DATE/" 2>/dev/null
     echo "Archived $(ls "$TRACE_DIR"/*.jsonl 2>/dev/null | wc -l) trace files to $ARCHIVE_DIR/$DATE/"
   else
     echo "No trace directory found at $TRACE_DIR"
   fi
   EOF

   chmod +x ~/bin/amplihack-archive-traces.sh
   ```

2. Run manually or via cron:

   ```bash
   # Manual archive
   ~/bin/amplihack-archive-traces.sh

   # Or add to crontab for daily archiving at 11:59 PM
   (crontab -l 2>/dev/null; echo "59 23 * * * ~/bin/amplihack-archive-traces.sh") | crontab -
   ```

3. Verify archives:

   ```bash
   ls -lh ~/amplihack-audit/

   # Output:
   # drwxr-xr-x 2 user user 4096 Jan 22 23:59 20260122
   # drwxr-xr-x 2 user user 4096 Jan 23 23:59 20260123
   ```

**Result**: Daily automated trace archiving.

---

### Task 7: Clean Up Old Traces

**Goal**: Remove traces older than 30 days (default retention).

**Steps**:

1. Check current traces:

   ```bash
   find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -ls
   ```

2. Preview what will be deleted:

   ```bash
   find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30
   ```

3. Delete old traces:

   ```bash
   find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30 -delete
   ```

4. Verify cleanup:

   ```bash
   ls -lh .claude/runtime/amplihack-traces/
   ```

**Result**: Old traces removed, disk space freed.

---

### Task 8: Compare Two Sessions

**Goal**: Analyze differences between two amplihack sessions.

**Steps**:

1. Identify the two trace files:

   ```bash
   ls -lt .claude/runtime/amplihack-traces/ | head -3
   ```

2. Extract key metrics from each:

   ```bash
   # Session 1
   cat trace_20260122_143022_a3f9d8.jsonl | \
     jq -s '{session: "a3f9d8",
            calls: length,
            tokens: [.[] | select(.response.usage != null) | .response.usage.total_tokens] | add}'

   # Session 2
   cat trace_20260122_151345_b4e2f1.jsonl | \
     jq -s '{session: "b4e2f1",
            calls: length,
            tokens: [.[] | select(.response.usage != null) | .response.usage.total_tokens] | add}'
   ```

3. Compare side-by-side:

   ```bash
   paste <(cat trace_20260122_143022_a3f9d8.jsonl | jq -s '{calls: length, tokens: [.[] | select(.response.usage != null) | .response.usage.total_tokens] | add}') \
         <(cat trace_20260122_151345_b4e2f1.jsonl | jq -s '{calls: length, tokens: [.[] | select(.response.usage != null) | .response.usage.total_tokens] | add}')
   ```

**Result**: Side-by-side session comparison.

---

### Task 9: Export Traces to CSV

**Goal**: Import trace data into spreadsheet software.

**Steps**:

1. Create CSV export script:

   ```bash
   cat .claude/runtime/amplihack-traces/*.jsonl | \
     jq -r '[.timestamp, .session_id, .event,
             (.request.model // "N/A"),
             (.response.usage.prompt_tokens // 0),
             (.response.usage.completion_tokens // 0),
             (.response.usage.total_tokens // 0),
             (.error.message // "success")] | @csv' > traces.csv
   ```

2. Add header row:

   ```bash
   echo "timestamp,session_id,event,model,prompt_tokens,completion_tokens,total_tokens,status" | \
     cat - traces.csv > traces_with_header.csv
   ```

3. Open in spreadsheet software:

   ```bash
   # macOS
   open traces_with_header.csv

   # Linux
   libreoffice traces_with_header.csv

   # Windows
   start excel traces_with_header.csv
   ```

**Result**: Trace data in CSV format for analysis.

---

### Task 10: Disable Trace Logging

**Goal**: Return to zero-overhead operation.

**Steps**:

1. Unset environment variable:

   ```bash
   unset AMPLIHACK_TRACE_LOGGING
   ```

2. Remove from shell profile (if added):

   ```bash
   # Edit ~/.bashrc or ~/.zshrc and remove:
   # export AMPLIHACK_TRACE_LOGGING=true

   # Then reload
   source ~/.bashrc
   ```

3. Verify trace logging is disabled:

   ```bash
   echo $AMPLIHACK_TRACE_LOGGING
   # Output: (empty)

   amplihack --version
   # No trace file created
   ```

**Result**: Trace logging completely disabled.

## Advanced Techniques

### Filter Traces by Model

```bash
# Extract only Claude Sonnet 4.5 calls
cat trace_*.jsonl | \
  jq 'select(.request.model == "claude-sonnet-4-5-20250929")'
```

### Calculate Average Response Time

```bash
# Requires paired request/response events
cat trace_*.jsonl | \
  jq -s 'group_by(.session_id) |
         map(select(length >= 2) |
             {session: .[0].session_id,
              avg_ms: (.[1].timestamp - .[0].timestamp) * 1000})' | \
  jq -s 'map(.avg_ms) | add / length'
```

### Find Long-Running Requests

```bash
# Find requests that took > 5 seconds
cat trace_*.jsonl | \
  jq -s 'group_by(.session_id) |
         map(select(length >= 2 and (.[1].timestamp - .[0].timestamp) > 5) |
             {session: .[0].session_id,
              duration: (.[1].timestamp - .[0].timestamp),
              prompt: .[0].request.messages[0].content})'
```

## Troubleshooting

See [Troubleshooting: Trace Logging](../troubleshooting/trace-logging.md) for common issues.

## Next Steps

- [Feature Overview: Trace Logging](../features/trace-logging.md) - Understanding trace logging
- [Developer Reference: Trace Logging API](../reference/trace-logging-api.md) - Technical implementation
- [Migration Guide: claude-trace to Native](../migration/claude-trace-to-native.md) - Upgrade from claude-trace
