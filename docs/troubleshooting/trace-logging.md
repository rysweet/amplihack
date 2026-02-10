# Troubleshooting: Trace Logging

Common issues and solutions for native binary trace logging.

## Quick Diagnostics

Run these commands to quickly diagnose trace logging issues:

```bash
# Check if trace logging is enabled
echo $AMPLIHACK_TRACE_LOGGING

# Check trace directory exists and is writable
ls -ld .claude/runtime/amplihack-traces/

# List existing trace files
ls -lh .claude/runtime/amplihack-traces/

# Verify trace file format
cat .claude/runtime/amplihack-traces/trace_*.jsonl | jq . | head -20

# Check disk space
df -h .claude/runtime/amplihack-traces/
```

## Common Issues

### Issue 1: No Trace Files Created

**Symptoms**:

- `AMPLIHACK_TRACE_LOGGING=true` is set
- No files appear in `.claude/runtime/amplihack-traces/`
- No errors displayed

**Diagnosis**:

```bash
# Verify environment variable
echo $AMPLIHACK_TRACE_LOGGING
# Should output: true

# Check if directory exists
ls -ld .claude/runtime/amplihack-traces/
# Should show directory with drwx------ permissions
```

**Solutions**:

**Solution 1: Environment variable not set correctly**

```bash
# Check exact value
echo "[$AMPLIHACK_TRACE_LOGGING]"
# Should be: [true] (not [True], [1], or [yes])

# Fix: Use lowercase 'true'
export AMPLIHACK_TRACE_LOGGING=true

# Verify
amplihack --version
# Trace file should now be created
```

**Solution 2: Directory permission issue**

```bash
# Check directory permissions
ls -ld .claude/runtime/amplihack-traces/

# If permission denied
chmod 755 .claude/runtime/amplihack-traces/

# If directory doesn't exist
mkdir -p .claude/runtime/amplihack-traces/
chmod 755 .claude/runtime/amplihack-traces/
```

**Solution 3: Disk space exhausted**

```bash
# Check available space
df -h .claude/runtime/amplihack-traces/

# If full, clean old traces
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +7 -delete

# Or increase disk space
```

**Verification**:

```bash
# Enable and test
export AMPLIHACK_TRACE_LOGGING=true
amplihack --version

# Check for trace file
ls -lh .claude/runtime/amplihack-traces/
# Should show new trace file
```

---

### Issue 2: Malformed JSONL Entries

**Symptoms**:

- Trace files exist but contain invalid JSON
- `jq` fails with parse errors
- Entries missing fields

**Diagnosis**:

```bash
# Test JSONL validity
cat .claude/runtime/amplihack-traces/trace_*.jsonl | jq . > /dev/null
# Error: parse error: Invalid numeric literal at line X, column Y

# Find problematic lines
cat trace_*.jsonl | while IFS= read -r line; do
  echo "$line" | jq . > /dev/null 2>&1 || echo "Bad line: $line"
done
```

**Solutions**:

**Solution 1: File corruption**

```bash
# Validate each entry
cat trace_20260122_143022_a3f9d8.jsonl | \
  jq -c '.' > trace_20260122_143022_a3f9d8_fixed.jsonl

# If successful, replace original
mv trace_20260122_143022_a3f9d8_fixed.jsonl trace_20260122_143022_a3f9d8.jsonl

# If jq fails, remove corrupted file
rm trace_20260122_143022_a3f9d8.jsonl
```

**Solution 2: Incomplete writes**

```bash
# Check if amplihack crashed during write
tail -1 trace_*.jsonl | jq .
# Error: parse error

# Remove incomplete last line
head -n -1 trace_*.jsonl > temp.jsonl && mv temp.jsonl trace_*.jsonl

# Verify
tail -1 trace_*.jsonl | jq .
# Should succeed
```

**Verification**:

```bash
# All entries should parse
cat trace_*.jsonl | jq . | wc -l
# Should equal: wc -l < trace_*.jsonl
```

---

### Issue 3: Sensitive Data in Traces

**Symptoms**:

- API keys visible in trace files
- Credentials not redacted
- Headers contain secrets

**Diagnosis**:

```bash
# Search for API keys
grep -r "sk-ant-api" .claude/runtime/amplihack-traces/
grep -r "sk-proj" .claude/runtime/amplihack-traces/
grep -r "Bearer" .claude/runtime/amplihack-traces/

# Check headers
cat trace_*.jsonl | jq '.request.headers' | grep -i "api-key\|authorization"
```

**Solutions**:

**Solution 1: TokenSanitizer not working**

```bash
# Verify TokenSanitizer is enabled
# Check source: src/trace/token_sanitizer.py should be imported

# If API keys still appear, file a bug report
# For immediate fix, manually sanitize:

cat trace_*.jsonl | \
  sed 's/sk-ant-api[0-9][0-9]-[A-Za-z0-9_-]*/[REDACTED]/g' | \
  sed 's/sk-proj-[A-Za-z0-9_-]*/[REDACTED]/g' > trace_sanitized.jsonl

mv trace_sanitized.jsonl trace_*.jsonl
```

**Solution 2: Custom sensitive data**

```python
# Extend TokenSanitizer for custom patterns
# File: custom_sanitizer.py

from trace.token_sanitizer import TokenSanitizer

class CustomSanitizer(TokenSanitizer):
    # Add your patterns
    CUSTOM_PATTERNS = [
        r'custom-secret-\w+',
        r'internal-token-\d+',
    ]

    def sanitize_string(self, text: str) -> str:
        text = super().sanitize_string(text)

        for pattern in self.CUSTOM_PATTERNS:
            text = re.sub(pattern, '[REDACTED]', text)

        return text
```

**Verification**:

```bash
# No API keys should be found
grep -r "sk-ant-api[0-9][0-9]-" .claude/runtime/amplihack-traces/
# Output: (nothing)

grep -r "\[REDACTED\]" .claude/runtime/amplihack-traces/
# Output: (multiple matches showing redaction worked)
```

---

### Issue 4: High Disk Usage

**Symptoms**:

- `.claude/runtime/amplihack-traces/` consuming excessive disk space
- Many old trace files accumulating
- Disk full warnings

**Diagnosis**:

```bash
# Check total trace directory size
du -sh .claude/runtime/amplihack-traces/

# Count trace files
ls .claude/runtime/amplihack-traces/ | wc -l

# Find largest files
ls -lhS .claude/runtime/amplihack-traces/ | head -10

# Check disk usage
df -h .claude/runtime/amplihack-traces/
```

**Solutions**:

**Solution 1: Enable automatic cleanup**

```bash
# Set retention policy (default: 30 days)
export AMPLIHACK_TRACE_RETENTION_DAYS=7

# Clean old traces manually
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +7 -delete

# Verify
du -sh .claude/runtime/amplihack-traces/
```

**Solution 2: Archive and compress**

```bash
# Archive traces older than 30 days
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30 \
  -exec tar -czf traces_archive_$(date +%Y%m%d).tar.gz {} + \
  -delete

# Move archive to backup location
mv traces_archive_*.tar.gz ~/backups/amplihack-traces/

# Verify disk usage reduced
du -sh .claude/runtime/amplihack-traces/
```

**Solution 3: Disable trace logging**

```bash
# If not needed, disable completely
unset AMPLIHACK_TRACE_LOGGING

# Remove from shell profile
sed -i '/AMPLIHACK_TRACE_LOGGING/d' ~/.bashrc

# Clean all traces (CAREFUL!)
rm -rf .claude/runtime/amplihack-traces/
```

**Verification**:

```bash
# Check reduced size
du -sh .claude/runtime/amplihack-traces/
# Should be significantly smaller

# Verify only recent files remain
ls -lt .claude/runtime/amplihack-traces/ | head
```

---

### Issue 5: Performance Degradation

**Symptoms**:

- amplihack slower when `AMPLIHACK_TRACE_LOGGING=true`
- API calls taking >100ms longer
- Noticeable lag in responses

**Diagnosis**:

```bash
# Measure overhead
time amplihack --version

# With tracing enabled (should be <100ms total)
AMPLIHACK_TRACE_LOGGING=true time amplihack --version

# Without tracing (baseline)
AMPLIHACK_TRACE_LOGGING=false time amplihack --version

# Calculate overhead
# Overhead = (enabled time) - (disabled time)
# Expected: <10ms
```

**Solutions**:

**Solution 1: I/O bottleneck**

```bash
# Check if trace directory is on slow disk
df -Th .claude/runtime/amplihack-traces/

# If on network filesystem (NFS, CIFS), move to local disk
export AMPLIHACK_TRACE_DIR=/tmp/amplihack-traces
mkdir -p /tmp/amplihack-traces

# Restart amplihack
amplihack
```

**Solution 2: Large trace files**

```bash
# Check if individual trace files are too large
ls -lhS .claude/runtime/amplihack-traces/ | head -5

# If files > 100MB, rotate more frequently
# Create rotation script
cat > rotate_traces.sh <<'EOF'
#!/bin/bash
MAX_SIZE_MB=50

for trace in .claude/runtime/amplihack-traces/trace_*.jsonl; do
  size=$(du -m "$trace" | cut -f1)
  if [ "$size" -gt "$MAX_SIZE_MB" ]; then
    # Compress and archive
    gzip "$trace"
    mv "$trace.gz" ~/amplihack-archive/
  fi
done
EOF

chmod +x rotate_traces.sh
```

**Solution 3: Disable when not needed**

```bash
# Only enable for debugging sessions
alias amplihack-debug='AMPLIHACK_TRACE_LOGGING=true amplihack'
alias amplihack='AMPLIHACK_TRACE_LOGGING=false amplihack'

# Use amplihack-debug only when investigating issues
```

**Verification**:

```bash
# Overhead should be <10ms
AMPLIHACK_TRACE_LOGGING=true time amplihack --version
# real: 0m0.050s (acceptable)

# vs disabled
AMPLIHACK_TRACE_LOGGING=false time amplihack --version
# real: 0m0.045s (baseline)
```

---

### Issue 6: Permission Denied Errors

**Symptoms**:

- Error: `Permission denied: '.claude/runtime/amplihack-traces/trace_*.jsonl'`
- Cannot create trace files
- Cannot write to trace directory

**Diagnosis**:

```bash
# Check directory permissions
ls -ld .claude/runtime/amplihack-traces/

# Check parent directory permissions
ls -ld .claude/runtime/

# Check file ownership
ls -l .claude/runtime/amplihack-traces/
```

**Solutions**:

**Solution 1: Directory not writable**

```bash
# Fix directory permissions
chmod 755 .claude/runtime/amplihack-traces/

# Fix parent permissions
chmod 755 .claude/runtime/

# Verify
touch .claude/runtime/amplihack-traces/test.txt
# Should succeed

rm .claude/runtime/amplihack-traces/test.txt
```

**Solution 2: File ownership issue**

```bash
# Check ownership
ls -l .claude/runtime/amplihack-traces/

# If owned by different user, take ownership
sudo chown -R $USER:$USER .claude/runtime/amplihack-traces/

# Verify
ls -l .claude/runtime/amplihack-traces/
# Should show your username
```

**Solution 3: SELinux/AppArmor restrictions**

```bash
# Check SELinux status
getenforce
# If: Enforcing

# Allow amplihack to write traces
sudo semanage fcontext -a -t user_home_t ".claude/runtime/amplihack-traces(/.*)?"
sudo restorecon -Rv .claude/runtime/amplihack-traces/

# Or disable SELinux (not recommended)
sudo setenforce 0
```

**Verification**:

```bash
# Should create trace file without errors
AMPLIHACK_TRACE_LOGGING=true amplihack --version

# Check file was created
ls -l .claude/runtime/amplihack-traces/
```

---

### Issue 7: Trace Files in Wrong Location

**Symptoms**:

- Expected trace files in `.claude/runtime/amplihack-traces/`
- Files appearing elsewhere or not at all
- `AMPLIHACK_TRACE_DIR` not respected

**Diagnosis**:

```bash
# Check environment variable
echo $AMPLIHACK_TRACE_DIR

# Search for trace files
find . -name "trace_*.jsonl" 2>/dev/null

# Check default location
ls -la .claude/runtime/amplihack-traces/
```

**Solutions**:

**Solution 1: Custom directory not created**

```bash
# If custom directory set but doesn't exist
export AMPLIHACK_TRACE_DIR=/custom/path/traces
mkdir -p /custom/path/traces
chmod 755 /custom/path/traces

# Restart amplihack
amplihack
```

**Solution 2: Working directory mismatch**

```bash
# Traces created in launch directory, not project directory
pwd
# If wrong directory, cd to project first

cd /path/to/project
export AMPLIHACK_TRACE_LOGGING=true
amplihack
```

**Solution 3: Absolute vs relative paths**

```bash
# Use absolute path to avoid ambiguity
export AMPLIHACK_TRACE_DIR="$HOME/.amplihack/traces"
mkdir -p "$HOME/.amplihack/traces"

# Restart amplihack
amplihack

# Verify location
ls -l $AMPLIHACK_TRACE_DIR
```

**Verification**:

```bash
# Trace files should be in expected location
ls -l $AMPLIHACK_TRACE_DIR
# Or default:
ls -l .claude/runtime/amplihack-traces/
```

---

### Issue 8: Missing Events in Traces

**Symptoms**:

- Some API calls not appearing in traces
- Incomplete conversation history
- Gaps in request/response pairs

**Diagnosis**:

```bash
# Count requests vs responses
cat trace_*.jsonl | jq 'select(.event=="request")' | wc -l
cat trace_*.jsonl | jq 'select(.event=="response")' | wc -l
# Should be roughly equal

# Check for errors
cat trace_*.jsonl | jq 'select(.event=="error")'

# Look for incomplete pairs
cat trace_*.jsonl | jq -s 'group_by(.session_id) | map({session: .[0].session_id, requests: map(select(.event=="request")) | length, responses: map(select(.event=="response")) | length})'
```

**Solutions**:

**Solution 1: Buffer not flushed**

```bash
# Ensure amplihack shutdown cleanly
# Use exit command, not kill -9

# If already killed, restart and exit cleanly
amplihack
# ... work ...
exit

# Verify flush
cat trace_*.jsonl | tail -5
```

**Solution 2: Error during logging**

```bash
# Check amplihack logs for trace errors
cat .claude/logs/*.log | grep -i "trace\|sanitiz"

# If errors found, fix underlying issue
# (e.g., disk space, permissions)
```

**Solution 3: API call bypassed logging**

```python
# If using custom API client, ensure callbacks registered
from trace.litellm_callbacks import setup_trace_callbacks

logger = TraceLogger()
setup_trace_callbacks(logger)

# Now all litellm calls will be traced
```

**Verification**:

```bash
# Requests and responses should match
cat trace_*.jsonl | \
  jq -s 'group_by(.session_id) |
         map({session: .[0].session_id,
              requests: map(select(.event=="request")) | length,
              responses: map(select(.event=="response")) | length})'

# Output: Matching counts
# [{"session": "a3f9d8", "requests": 15, "responses": 15}]
```

---

## Error Messages

### `OSError: [Errno 28] No space left on device`

**Cause**: Disk full, cannot write trace files.

**Solution**:

```bash
# Free up space
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +7 -delete

# Or disable tracing
unset AMPLIHACK_TRACE_LOGGING
```

---

### `PermissionError: [Errno 13] Permission denied`

**Cause**: Cannot write to trace directory.

**Solution**:

```bash
# Fix permissions
chmod 755 .claude/runtime/amplihack-traces/

# Or use custom directory
export AMPLIHACK_TRACE_DIR=/tmp/traces
mkdir -p /tmp/traces
```

---

### `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`

**Cause**: Malformed JSON in trace file.

**Solution**:

```bash
# Find bad lines
cat trace_*.jsonl | while read line; do
  echo "$line" | jq . > /dev/null 2>&1 || echo "Bad: $line"
done

# Remove corrupted file
rm trace_*.jsonl

# Restart fresh
AMPLIHACK_TRACE_LOGGING=true amplihack
```

---

## Getting Help

If you cannot resolve the issue:

1. Collect diagnostic information:

```bash
cat > trace_diagnostics.txt <<EOF
=== Environment ===
AMPLIHACK_TRACE_LOGGING=$AMPLIHACK_TRACE_LOGGING
AMPLIHACK_TRACE_DIR=$AMPLIHACK_TRACE_DIR
AMPLIHACK_TRACE_RETENTION_DAYS=$AMPLIHACK_TRACE_RETENTION_DAYS

=== Directory ===
$(ls -ld .claude/runtime/amplihack-traces/)

=== Files ===
$(ls -lh .claude/runtime/amplihack-traces/)

=== Disk Space ===
$(df -h .claude/runtime/amplihack-traces/)

=== Recent Trace Sample ===
$(cat .claude/runtime/amplihack-traces/trace_*.jsonl | tail -5)

=== Errors ===
$(cat .claude/logs/*.log 2>/dev/null | grep -i "trace" | tail -20)
EOF

cat trace_diagnostics.txt
```

2. Check existing issues: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)

3. File new issue with diagnostics

## Next Steps

- [Feature Overview: Trace Logging](../features/trace-logging.md) - Understanding trace logging
- [How-To: Trace Logging](../howto/trace-logging.md) - Practical recipes
- [Developer Reference: Trace Logging API](../reference/trace-logging-api.md) - Technical details
- [Migration Guide: claude-trace to Native](../migration/claude-trace-to-native.md) - Upgrade from claude-trace
