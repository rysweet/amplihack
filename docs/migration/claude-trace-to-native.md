# Migration Guide: claude-trace to Native Binary

**Complete migration guide for transitioning from the claude-trace NPM package to native binary trace logging**

## Overview

This guide helps you migrate from the deprecated `claude-trace` NPM package to amplihack's native binary trace logging system. The new system provides better performance, zero external dependencies, and improved security.

## What Changed

### Before (claude-trace NPM)

```javascript
// NPM dependency required
import { TraceLogger } from 'claude-trace';

// Always enabled, always overhead
const logger = new TraceLogger({
  outputDir: './traces'
});

// Manual initialization
await logger.init();

// Manual logging
logger.logRequest(request);
logger.logResponse(response);
```

### After (Native Binary)

```bash
# No NPM dependency - uses native Claude binary
# Disabled by default - zero overhead when off
export AMPLIHACK_TRACE_LOGGING=true
amplihack

# Automatic logging via LiteLLM callbacks
# No code changes required
```

## Benefits of Migration

| Feature | claude-trace NPM | Native Binary |
|---------|-----------------|---------------|
| NPM dependency | Required | None |
| Default state | Enabled | Disabled |
| Overhead when disabled | ~1-2ms | <0.1ms |
| Overhead when enabled | ~15-20ms | <10ms |
| Security | Manual sanitization | Automatic TokenSanitizer |
| Integration | Manual instrumentation | Automatic LiteLLM callbacks |
| Binary | Node.js only | Native Claude binary |
| Session handling | Manual | Automatic |

## Migration Steps

### Step 1: Verify Current Setup

Check if you're using `claude-trace`:

```bash
# Check package.json
cat package.json | jq '.dependencies["claude-trace"]'

# Check imports in code
grep -r "claude-trace" src/
grep -r "TraceLogger" src/
```

**Result**: If found, proceed with migration.

---

### Step 2: Remove claude-trace Dependency

Remove the NPM package:

```bash
# NPM
npm uninstall claude-trace

# Yarn
yarn remove claude-trace

# PNPM
pnpm remove claude-trace
```

**Verify removal**:

```bash
cat package.json | jq '.dependencies["claude-trace"]'
# Output: null
```

---

### Step 3: Remove Manual Instrumentation

Remove all `claude-trace` code:

**Before**:

```javascript
// Remove these imports
import { TraceLogger } from 'claude-trace';

// Remove initialization
const logger = new TraceLogger({
  outputDir: './traces',
  sanitize: true
});
await logger.init();

// Remove manual logging
logger.logRequest(request);
logger.logResponse(response);
logger.close();
```

**After**:

```javascript
// No imports needed
// No initialization needed
// No manual logging needed

// LiteLLM callbacks handle everything automatically
```

**Search and remove**:

```bash
# Find all files using claude-trace
grep -r "claude-trace" src/ | cut -d: -f1 | sort -u

# Remove imports and usage from each file
# (Use your editor or automated refactoring tools)
```

---

### Step 4: Enable Native Trace Logging

Configure the new system:

```bash
# Option 1: Enable for specific session
export AMPLIHACK_TRACE_LOGGING=true
amplihack

# Option 2: Enable permanently
echo 'export AMPLIHACK_TRACE_LOGGING=true' >> ~/.bashrc
source ~/.bashrc
```

**Verify configuration**:

```bash
echo $AMPLIHACK_TRACE_LOGGING
# Output: true
```

---

### Step 5: Update Trace File Paths

The new system uses a different directory structure:

**Before (claude-trace)**:

```
./traces/
  ├── 2026-01-22/
  │   ├── trace_001.json
  │   ├── trace_002.json
  │   └── trace_003.json
  └── 2026-01-23/
      └── trace_001.json
```

**After (native binary)**:

```
./.claude/runtime/amplihack-traces/
  ├── trace_20260122_143022_a3f9d8.jsonl
  ├── trace_20260122_151345_b4e2f1.jsonl
  └── trace_20260123_090015_c5f3a2.jsonl
```

**Update scripts and tools**:

```bash
# Old path
TRACE_DIR="./traces"

# New path
TRACE_DIR="./.claude/runtime/amplihack-traces"

# Update analysis scripts
sed -i 's|./traces|./.claude/runtime/amplihack-traces|g' scripts/analyze-traces.sh
```

---

### Step 6: Update Analysis Scripts

The new format is JSONL instead of separate JSON files:

**Before (claude-trace)**:

```bash
# Analyze JSON files
for file in traces/*/*.json; do
  jq '.usage.total_tokens' "$file"
done
```

**After (native binary)**:

```bash
# Analyze JSONL files
cat .claude/runtime/amplihack-traces/*.jsonl | \
  jq 'select(.response.usage != null) | .response.usage.total_tokens'
```

**Migration script**:

```bash
# Create migration script
cat > migrate-trace-analysis.sh <<'EOF'
#!/bin/bash

OLD_DIR="./traces"
NEW_DIR="./.claude/runtime/amplihack-traces"

echo "Migrating trace analysis from $OLD_DIR to $NEW_DIR"

# Count total tokens (example)
echo "Total tokens (new format):"
cat "$NEW_DIR"/*.jsonl | \
  jq -s '[.[] | select(.response.usage != null) | .response.usage.total_tokens] | add'
EOF

chmod +x migrate-trace-analysis.sh
```

---

### Step 7: Migrate Existing Trace Data (Optional)

Convert old traces to new format:

```bash
# Create conversion script
cat > convert-traces.sh <<'EOF'
#!/bin/bash

OLD_DIR="./traces"
NEW_DIR="./.claude/runtime/amplihack-traces"

mkdir -p "$NEW_DIR"

for date_dir in "$OLD_DIR"/*/; do
  for trace_file in "$date_dir"*.json; do
    if [ -f "$trace_file" ]; then
      # Extract date from directory
      date=$(basename "$date_dir")
      date_compact=$(echo "$date" | tr -d '-')

      # Generate session ID
      session_id=$(head /dev/urandom | tr -dc a-f0-9 | head -c 6)

      # Convert JSON to JSONL format
      output_file="$NEW_DIR/trace_${date_compact}_000000_${session_id}.jsonl"

      # Read old format and convert
      jq -c '.' "$trace_file" >> "$output_file"

      echo "Converted $trace_file -> $output_file"
    fi
  done
done

echo "Migration complete!"
EOF

chmod +x convert-traces.sh
./convert-traces.sh
```

**Verify conversion**:

```bash
ls -lh .claude/runtime/amplihack-traces/
cat .claude/runtime/amplihack-traces/*.jsonl | jq . | head -20
```

---

### Step 8: Test the Migration

Verify the new system works:

```bash
# Enable trace logging
export AMPLIHACK_TRACE_LOGGING=true

# Start amplihack
amplihack

# Perform some operations
# ... interact with amplihack ...

# Exit
exit

# Verify trace file was created
ls -lh .claude/runtime/amplihack-traces/

# Analyze the trace
cat .claude/runtime/amplihack-traces/trace_*.jsonl | jq . | head -50
```

**Expected output**:

```json
{
  "timestamp": "2026-01-22T14:30:22.451Z",
  "session_id": "a3f9d8",
  "event": "request",
  "request": {
    "model": "claude-sonnet-4-5-20250929",
    "messages": [...]
  }
}
{
  "timestamp": "2026-01-22T14:30:23.102Z",
  "session_id": "a3f9d8",
  "event": "response",
  "response": {
    "id": "msg_abc123",
    "usage": {
      "prompt_tokens": 12,
      "completion_tokens": 8,
      "total_tokens": 20
    }
  }
}
```

---

### Step 9: Update Documentation and Scripts

Update all references:

```bash
# Find documentation mentioning claude-trace
grep -r "claude-trace" docs/ README.md

# Update to reference native binary trace logging
# (Manual editing required)

# Update CI/CD scripts
grep -r "claude-trace" .github/ .gitlab-ci.yml jenkins/ 2>/dev/null
```

**Example CI/CD update**:

```yaml
# Before (GitHub Actions)
- name: Install trace logger
  run: npm install claude-trace

- name: Enable tracing
  run: |
    export TRACE_OUTPUT=./traces
    npm run build

# After
- name: Enable native trace logging
  run: export AMPLIHACK_TRACE_LOGGING=true

- name: Build
  run: npm run build
```

---

### Step 10: Clean Up

Remove old traces and dependencies:

```bash
# Archive old traces (optional)
tar -czf traces-backup-$(date +%Y%m%d).tar.gz traces/

# Remove old trace directory
rm -rf traces/

# Verify package.json is clean
cat package.json | jq '.dependencies'
# Should not contain "claude-trace"

# Commit changes
git add package.json package-lock.json
git commit -m "Remove claude-trace dependency, migrate to native binary trace logging"
```

## Migration Checklist

Use this checklist to track migration progress:

```markdown
- [ ] Step 1: Verify current claude-trace usage
- [ ] Step 2: Remove claude-trace NPM dependency
- [ ] Step 3: Remove manual instrumentation code
- [ ] Step 4: Enable native trace logging
- [ ] Step 5: Update trace file paths in scripts
- [ ] Step 6: Update analysis scripts for JSONL format
- [ ] Step 7: Migrate existing trace data (optional)
- [ ] Step 8: Test the new system end-to-end
- [ ] Step 9: Update documentation and CI/CD
- [ ] Step 10: Clean up old traces and commit
```

## Breaking Changes

### File Format

**Before**: Individual JSON files per trace event
**After**: Session-scoped JSONL files

**Impact**: Analysis scripts must use `jq -s` or read line-by-line.

### Directory Structure

**Before**: `./traces/YYYY-MM-DD/trace_NNN.json`
**After**: `./.claude/runtime/amplihack-traces/trace_YYYYMMDD_HHMMSS_SESSION.jsonl`

**Impact**: Update all hardcoded paths.

### Default State

**Before**: Enabled by default
**After**: Disabled by default

**Impact**: Must explicitly enable with `AMPLIHACK_TRACE_LOGGING=true`.

### API

**Before**: Manual `logger.logRequest()` / `logger.logResponse()`
**After**: Automatic LiteLLM callbacks

**Impact**: Remove all manual logging code.

## Common Migration Issues

### Issue 1: Traces Not Being Created

**Symptom**: No trace files appear in `.claude/runtime/amplihack-traces/`

**Solution**:

```bash
# Verify environment variable is set
echo $AMPLIHACK_TRACE_LOGGING
# Should output: true

# If not set
export AMPLIHACK_TRACE_LOGGING=true

# Verify directory exists and is writable
mkdir -p .claude/runtime/amplihack-traces
chmod 755 .claude/runtime/amplihack-traces
```

---

### Issue 2: Old Scripts Fail with New Format

**Symptom**: `jq` errors when parsing JSONL

**Solution**:

```bash
# Old script (fails on JSONL)
jq '.usage.total_tokens' trace_*.jsonl
# Error: parse error

# Fixed script (handles JSONL)
cat trace_*.jsonl | jq '.response.usage.total_tokens'
# Works correctly
```

---

### Issue 3: Missing Trace Data After Migration

**Symptom**: Converted traces missing fields

**Solution**:

```bash
# Check old format schema
jq 'keys' ./traces/2026-01-22/trace_001.json

# Check new format schema
cat .claude/runtime/amplihack-traces/trace_*.jsonl | jq 'keys' | head -1

# Adjust conversion script to map fields correctly
```

## Performance Comparison

### Before Migration (claude-trace)

```
NPM dependency size: ~250KB
Overhead (disabled): ~1-2ms per call
Overhead (enabled): ~15-20ms per call
Memory usage: ~50MB baseline
```

### After Migration (Native Binary)

```
NPM dependency size: 0 (native binary)
Overhead (disabled): <0.1ms per call
Overhead (enabled): <10ms per call
Memory usage: <5MB baseline
```

**Result**: ~50% faster tracing, 90% less overhead when disabled.

## Rollback Plan

If issues arise, you can temporarily rollback:

```bash
# Reinstall claude-trace
npm install claude-trace@latest

# Restore code from git
git checkout HEAD~1 -- src/

# Disable native trace logging
unset AMPLIHACK_TRACE_LOGGING

# File bug report
# Then plan migration retry
```

## Next Steps

After successful migration:

- [How-To: Trace Logging](../howto/trace-logging.md) - Learn new workflows
- [Feature Overview: Trace Logging](../features/trace-logging.md) - Understand capabilities
- [Developer Reference: Trace Logging API](../reference/trace-logging-api.md) - Technical details
- [Troubleshooting: Trace Logging](../troubleshooting/trace-logging.md) - Fix common issues

## Support

If you encounter migration issues:

1. Check [Troubleshooting: Trace Logging](../troubleshooting/trace-logging.md)
2. Review [Feature Overview](../features/trace-logging.md) for configuration
3. File issue: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
