# Native Binary Trace Logging

**Complete documentation for the native binary migration with optional trace logging feature**

## Overview

amplihack now uses Anthropic's native Claude binary with optional trace logging instead of the deprecated `claude-trace` NPM package. This provides better performance, zero external dependencies, and enhanced security.

## What Changed

### Key Improvements

- **No NPM dependency**: Uses native Claude binary instead of `claude-trace` package
- **Optional by default**: Trace logging disabled by default, zero overhead when off
- **Better performance**: <0.1ms overhead when disabled, <10ms when enabled
- **Automatic security**: TokenSanitizer removes API keys and secrets automatically
- **Session-scoped logs**: JSONL files organized by session in `.claude/runtime/amplihack-traces/`
- **LiteLLM integration**: Automatic request/response capture via callbacks

### Performance Comparison

| Metric | claude-trace NPM | Native Binary |
|--------|-----------------|---------------|
| Overhead (disabled) | ~1-2ms | <0.1ms |
| Overhead (enabled) | ~15-20ms | <10ms |
| NPM dependency | Required (250KB) | None |
| Default state | Enabled | Disabled |
| Security | Manual | Automatic |

## Quick Start

### Enable Trace Logging

Trace logging is **disabled by default**. Enable it when needed:

```bash
# Enable for single session
AMPLIHACK_TRACE_LOGGING=true amplihack

# Enable permanently
export AMPLIHACK_TRACE_LOGGING=true
echo 'export AMPLIHACK_TRACE_LOGGING=true' >> ~/.bashrc

# Launch amplihack
amplihack
```

### View Traces

```bash
# List trace files
ls -lh .claude/runtime/amplihack-traces/

# View latest trace
tail -f .claude/runtime/amplihack-traces/trace_*.jsonl | jq .

# Analyze token usage
cat .claude/runtime/amplihack-traces/*.jsonl | \
  jq -s '[.[] | select(.response.usage != null) | .response.usage] |
         {calls: length, total_tokens: map(.total_tokens) | add}'
```

## Documentation

### For Users

Start here to learn how to use trace logging:

1. **[Feature Overview](features/trace-logging.md)**
   - What is trace logging and why use it
   - Common scenarios and use cases
   - Quick start guide
   - Security considerations

2. **[How-To Guide](howto/trace-logging.md)**
   - Step-by-step recipes for common tasks
   - Enable/disable trace logging
   - Analyze traces with jq
   - Monitor token usage
   - Archive traces for compliance
   - Export to CSV

### For Migrators

If you're upgrading from `claude-trace`:

3. **[Migration Guide](migration/claude-trace-to-native.md)**
   - Complete migration checklist
   - Breaking changes and impacts
   - Step-by-step upgrade process
   - Convert existing trace data
   - Update analysis scripts
   - Rollback plan

### For Developers

For technical details and API reference:

4. **[Developer Reference](reference/trace-logging-api.md)**
   - Architecture overview
   - Module reference (TraceLogger, TokenSanitizer, etc.)
   - Trace entry schema
   - Performance characteristics
   - Extension points
   - Testing strategies

### For Troubleshooting

When things go wrong:

5. **[Troubleshooting Guide](troubleshooting/trace-logging.md)**
   - Common issues and solutions
   - No trace files created
   - Malformed JSONL entries
   - Sensitive data in traces
   - High disk usage
   - Performance degradation
   - Permission errors

## Common Use Cases

### Debug Unexpected Responses

```bash
# Enable trace logging
export AMPLIHACK_TRACE_LOGGING=true

# Run session that shows unexpected behavior
amplihack
# ... reproduce issue ...
exit

# Analyze the conversation
cat .claude/runtime/amplihack-traces/trace_*.jsonl | \
  jq 'select(.event=="request" or .event=="response")'
```

### Monitor Token Usage

```bash
# Generate token report
cat .claude/runtime/amplihack-traces/*.jsonl | \
  jq -s '[.[] | select(.response.usage != null) | .response.usage] |
         {total_calls: length,
          total_prompt: map(.prompt_tokens) | add,
          total_completion: map(.completion_tokens) | add,
          total_tokens: map(.total_tokens) | add}'
```

### Compliance Audit Trail

```bash
# Enable permanent trace logging
export AMPLIHACK_TRACE_LOGGING=true

# Archive daily
mkdir -p ~/amplihack-audit/$(date +%Y%m%d)
cp .claude/runtime/amplihack-traces/*.jsonl ~/amplihack-audit/$(date +%Y%m%d)/

# Generate compliance report
cat ~/amplihack-audit/*/*.jsonl | \
  jq -r '[.timestamp, .session_id, .event] | @csv' > audit-report.csv
```

## Architecture

### Component Diagram

```
amplihack Session
        │
        ▼
LiteLLM Callback Manager
        │
        ▼
TraceLogger (checks AMPLIHACK_TRACE_LOGGING)
        │
        ▼
TokenSanitizer (removes API keys, secrets)
        │
        ▼
JSONL Writer (.claude/runtime/amplihack-traces/)
```

### File Structure

```
.claude/runtime/amplihack-traces/
├── trace_20260122_143022_a3f9d8.jsonl  (session 1)
├── trace_20260122_151345_b4e2f1.jsonl  (session 2)
└── trace_20260123_090015_c5f3a2.jsonl  (session 3)

File naming: trace_YYYYMMDD_HHMMSS_SESSION.jsonl
- YYYYMMDD: Date
- HHMMSS: Time
- SESSION: 6-char unique ID
```

### Trace Entry Format

Each trace file contains JSONL (newline-delimited JSON):

```jsonl
{"timestamp":"2026-01-22T14:30:22.451Z","session_id":"a3f9d8","event":"request","request":{...}}
{"timestamp":"2026-01-22T14:30:23.102Z","session_id":"a3f9d8","event":"response","response":{...}}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AMPLIHACK_TRACE_LOGGING` | `false` | Enable/disable trace logging |
| `AMPLIHACK_TRACE_DIR` | `.claude/runtime/amplihack-traces/` | Trace file directory |
| `AMPLIHACK_TRACE_RETENTION_DAYS` | `30` | Auto-delete traces older than N days |

### Examples

```bash
# Custom trace directory
export AMPLIHACK_TRACE_DIR=/var/log/amplihack-traces
mkdir -p /var/log/amplihack-traces

# Custom retention (keep 7 days)
export AMPLIHACK_TRACE_RETENTION_DAYS=7

# Launch with tracing
AMPLIHACK_TRACE_LOGGING=true amplihack
```

## Security

### Automatic Sanitization

TokenSanitizer automatically removes:

- **API keys**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.
- **Bearer tokens**: Authorization headers
- **Sensitive patterns**: `sk-ant-api03-...`, `sk-proj-...`, etc.

### Example

```json
// Original request
{"headers": {"x-api-key": "sk-ant-api03-abc123..."}}

// Sanitized trace entry
{"headers": {"x-api-key": "[REDACTED]"}}
```

### File Permissions

Trace files are created with owner-only permissions:

```bash
ls -l .claude/runtime/amplihack-traces/
# -rw------- (600) - only you can read/write
```

## Performance

### Benchmarks

```
Tested with 1000 API calls:

AMPLIHACK_TRACE_LOGGING=false:
  Overhead: <0.1ms per call
  Total: ~0ms

AMPLIHACK_TRACE_LOGGING=true:
  Overhead: ~8-10ms per call
  Breakdown:
    - Sanitization: 2ms
    - JSON serialization: 3ms
    - File I/O: 4ms (buffered)
```

### Optimization

When disabled, trace logging has near-zero impact:

```python
def log_request(self, request):
    if not self.is_enabled():
        return  # <0.1ms exit
    # ... logging logic only runs if enabled
```

## Migration from claude-trace

If you previously used `claude-trace`:

1. Remove NPM dependency: `npm uninstall claude-trace`
2. Remove manual instrumentation code
3. Enable native trace logging: `export AMPLIHACK_TRACE_LOGGING=true`
4. Update scripts for JSONL format

See [complete migration guide](migration/claude-trace-to-native.md) for details.

## Troubleshooting

### No trace files created

```bash
# Verify environment variable
echo $AMPLIHACK_TRACE_LOGGING
# Should output: true

# If not set:
export AMPLIHACK_TRACE_LOGGING=true
```

### Disk space issues

```bash
# Clean old traces
find .claude/runtime/amplihack-traces/ -name "trace_*.jsonl" -mtime +30 -delete

# Or disable tracing
unset AMPLIHACK_TRACE_LOGGING
```

### Performance degradation

```bash
# Only enable when needed
alias amplihack-debug='AMPLIHACK_TRACE_LOGGING=true amplihack'

# Regular use (no tracing)
amplihack
```

See [complete troubleshooting guide](troubleshooting/trace-logging.md) for more issues.

## FAQ

### Q: Is trace logging enabled by default?

**A**: No. Trace logging is **disabled by default** for zero performance overhead. Enable it explicitly with `AMPLIHACK_TRACE_LOGGING=true`.

### Q: Where are trace files stored?

**A**: By default in `.claude/runtime/amplihack-traces/`. Customize with `AMPLIHACK_TRACE_DIR`.

### Q: How much disk space do traces use?

**A**: Approximately 1-5KB per API call. A typical session with 50 calls uses ~100KB. Old traces are auto-deleted after 30 days (configurable).

### Q: Are API keys logged?

**A**: No. TokenSanitizer automatically removes all API keys, bearer tokens, and sensitive data before writing traces.

### Q: Can I use traces for compliance?

**A**: Yes. Traces provide a complete audit trail of all API interactions. Enable permanent logging and archive regularly.

### Q: What's the performance impact?

**A**: When disabled: <0.1ms. When enabled: ~8-10ms per API call (mostly I/O).

### Q: How do I analyze traces?

**A**: Traces use JSONL format. Use `jq` for analysis:

```bash
cat trace_*.jsonl | jq 'select(.response.usage != null) | .response.usage'
```

See [How-To Guide](howto/trace-logging.md) for recipes.

### Q: Can I migrate from claude-trace?

**A**: Yes. See [Migration Guide](migration/claude-trace-to-native.md) for step-by-step instructions.

## Next Steps

Choose your path:

- **New to trace logging?** Start with [Feature Overview](features/trace-logging.md)
- **Want to use it?** See [How-To Guide](howto/trace-logging.md)
- **Migrating from claude-trace?** Read [Migration Guide](migration/claude-trace-to-native.md)
- **Need technical details?** Check [Developer Reference](reference/trace-logging-api.md)
- **Having issues?** Consult [Troubleshooting Guide](troubleshooting/trace-logging.md)

## Support

- **Documentation**: See guides above
- **Issues**: [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/discussions)

---

**Version**: 1.0.0 (Native Binary)
**Last Updated**: 2026-01-22
**Status**: Production Ready
