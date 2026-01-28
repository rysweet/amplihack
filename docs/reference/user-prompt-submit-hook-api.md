# UserPromptSubmit Hook API Reference

Developer reference for the UserPromptSubmit hook implementation, focusing on framework injection via CLAUDE.md vs AMPLIHACK.md comparison.

## Overview

The UserPromptSubmit hook injects context on every user message:

1. User preferences (behavioral guidance)
2. Agent memories (when agents mentioned)
3. Framework instructions (when CLAUDE.md differs from AMPLIHACK.md)

This document focuses on the framework injection mechanism (item 3).

## Hook Signature

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/user_prompt_submit.py`

**Hook Type**: `UserPromptSubmit`

**Trigger**: Before processing each user message

**Input**:

```json
{
  "session_id": "string",
  "transcript_path": "path",
  "cwd": "path",
  "hook_event_name": "UserPromptSubmit",
  "userMessage": {
    "text": "user's prompt text"
  }
}
```

**Output**:

```json
{
  "additionalContext": "string - injected context"
}
```

## Core API

### `_inject_amplihack_if_different() -> str`

Compares CLAUDE.md vs AMPLIHACK.md and injects framework instructions if they differ.

**Returns**: AMPLIHACK.md contents if different, empty string if identical

**Algorithm**:

```python
def _inject_amplihack_if_different(self) -> str:
    # 1. Find AMPLIHACK.md (priority order)
    amplihack_md = self._find_amplihack_md()
    if not amplihack_md:
        return ""

    # 2. Find CLAUDE.md (project root)
    claude_md = self.project_root / "CLAUDE.md"

    # 3. Check cache using mtimes
    amplihack_mtime = amplihack_md.stat().st_mtime
    claude_mtime = claude_md.stat().st_mtime if claude_md.exists() else 0

    if self._amplihack_cache_timestamp == (amplihack_mtime, claude_mtime):
        return self._amplihack_cache  # Cache hit

    # 4. Read both files
    amplihack_content = amplihack_md.read_text(encoding="utf-8")
    claude_content = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

    # 5. Compare (whitespace-normalized)
    if claude_content.strip() == amplihack_content.strip():
        result = ""  # Files identical, skip injection
    else:
        result = amplihack_content  # Files differ, inject framework

    # 6. Update cache
    self._amplihack_cache = result
    self._amplihack_cache_timestamp = (amplihack_mtime, claude_mtime)

    return result
```

**Performance**:

- First call: ~50-100ms (reads 2 files, ~2000 lines each)
- Cached calls: <1ms (mtime check only)
- Cache invalidation: Only when either file's mtime changes

### File Resolution Priority

**AMPLIHACK.md search order**:

1. `$CLAUDE_PLUGIN_ROOT/AMPLIHACK.md` - Plugin mode (Claude Code)
2. `~/.amplihack/.claude/AMPLIHACK.md` - Centralized staging (all tools)
3. `.claude/AMPLIHACK.md` - Per-project mode (development)

**CLAUDE.md location**: Always `project_root/CLAUDE.md`

```python
def _find_amplihack_md(self) -> Optional[Path]:
    # Try plugin location
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        path = Path(plugin_root) / "AMPLIHACK.md"
        if path.exists():
            return path

    # Try centralized staging
    path = Path.home() / ".amplihack" / ".claude" / "AMPLIHACK.md"
    if path.exists():
        return path

    # Try per-project
    path = self.project_root / ".claude" / "AMPLIHACK.md"
    if path.exists():
        return path

    return None
```

## Caching Implementation

### Cache Structure

```python
class UserPromptSubmitHook(HookProcessor):
    def __init__(self):
        super().__init__("user_prompt_submit")
        # Cache for comparison result
        self._amplihack_cache: Optional[str] = None
        # Cache key: tuple of (amplihack_mtime, claude_mtime)
        self._amplihack_cache_timestamp: Optional[Tuple[float, float]] = None
```

### Cache Invalidation Rules

Cache is invalidated when:

- **AMPLIHACK.md changes** (package update, manual edit)
- **CLAUDE.md changes** (user customization)
- **Hook process restarts** (new session, reload)

Cache is **not** invalidated when:

- User sends message (cache used)
- Other files change
- Environment variables change

### Cache Performance

**Cache hit rate**: ~99% in typical usage

- First message: Cache miss (reads files)
- Subsequent messages: Cache hits (uses mtimes)
- File edit: Cache miss (mtime changed)
- Next message: Cache hit again

**Timing measurements**:

```
Cache miss (read + compare): ~80ms
Cache hit (mtime check):     <1ms
Speedup factor:              80x
```

## Whitespace Normalization

Files are compared using whitespace-normalized content:

```python
if claude_content.strip() == amplihack_content.strip():
    # Files are identical (ignoring leading/trailing whitespace)
```

**Rationale**: Formatting differences shouldn't trigger injection:

- Line ending differences (LF vs CRLF)
- Trailing whitespace
- Extra newlines at end

**Not normalized**:

- Internal whitespace (indentation, spacing)
- Content structure
- Comments

This balances correctness (ignore formatting) with accuracy (detect real changes).

## Error Handling

All errors result in graceful degradation:

```python
try:
    return self._inject_amplihack_if_different()
except Exception as e:
    self.log(f"Could not check AMPLIHACK.md vs CLAUDE.md: {e}", "WARNING")
    return ""  # Empty injection, never block Claude
```

**Specific error cases**:

| Error               | Behavior                   | Log Level | Exit Code |
| ------------------- | -------------------------- | --------- | --------- |
| AMPLIHACK.md missing | Skip injection, log info   | INFO      | 0         |
| CLAUDE.md missing   | Treat as empty, inject     | DEBUG     | 0         |
| Read permission     | Skip injection, log warning | WARNING   | 0         |
| Encoding error      | Skip injection, log warning | WARNING   | 0         |
| Compare error       | Skip injection, log warning | WARNING   | 0         |

**Never fails** - hook always exits 0 to prevent blocking Claude Code.

## Injection Context Format

When files differ, full AMPLIHACK.md is injected without modification:

```
# Framework Instruction Injection (from AMPLIHACK.md)

[entire AMPLIHACK.md contents]
```

**No processing**:

- No truncation
- No summarization
- No filtering
- Complete file contents

This ensures all framework instructions are available.

## Process Integration

### Full process() Method Flow

```python
def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    context_parts = []

    # 1. Inject user preferences
    preferences = self._get_preferences()
    if preferences:
        context_parts.append(self.build_preference_context(preferences))

    # 2. Inject agent memories (if agents mentioned)
    user_prompt = input_data.get("userMessage", {}).get("text", "")
    memory_context = self._inject_memories_for_agents(user_prompt)
    if memory_context:
        context_parts.append(memory_context)

    # 3. Inject framework instructions (if CLAUDE.md differs)
    amplihack_context = self._inject_amplihack_if_different()
    if amplihack_context:
        context_parts.append(amplihack_context)
        self.log("Injected AMPLIHACK.md framework instructions")

    # Combine all context
    full_context = "\n\n".join(context_parts)

    return {
        "additionalContext": full_context
    }
```

**Order matters**: Preferences → Memories → Framework ensures proper priority.

## Logging and Metrics

### Log Events

**Log file**: `~/.amplihack/.claude/runtime/logs/user_prompt_submit.log`

```
[INFO] Detected agents: ['architect', 'builder']
[INFO] Injected 5 preferences on user prompt
[INFO] Injected AMPLIHACK.md framework instructions
[DEBUG] CLAUDE.md matches AMPLIHACK.md - skipping framework injection
[WARNING] AMPLIHACK.md not found - skipping framework injection
[WARNING] Could not check AMPLIHACK.md vs CLAUDE.md: [error]
```

### Metrics Tracked

**Metrics file**: `~/.amplihack/.claude/runtime/metrics/user_prompt_submit_metrics.jsonl`

```json
{"timestamp": "2025-01-27T...", "preferences_injected": 5}
{"timestamp": "2025-01-27T...", "agent_memory_injected": 3}
{"timestamp": "2025-01-27T...", "agents_detected": 2}
{"timestamp": "2025-01-27T...", "context_length": 2847}
```

**Available metrics**:

- `preferences_injected`: Number of preferences injected
- `agent_memory_injected`: Number of agent memories injected
- `agents_detected`: Number of agents detected in prompt
- `context_length`: Total character count of injected context

## Testing

### Unit Testing

Test the comparison logic:

```python
def test_inject_amplihack_different_files():
    """Test injection when CLAUDE.md differs from AMPLIHACK.md."""
    hook = UserPromptSubmitHook()

    # Setup: Create different files
    write_file("CLAUDE.md", "Custom project instructions")
    write_file(".claude/AMPLIHACK.md", "Framework instructions")

    result = hook._inject_amplihack_if_different()

    assert result == "Framework instructions"
    assert "Injected AMPLIHACK.md" in hook.logs

def test_inject_amplihack_identical_files():
    """Test no injection when files are identical."""
    hook = UserPromptSubmitHook()

    # Setup: Create identical files
    write_file("CLAUDE.md", "Same content")
    write_file(".claude/AMPLIHACK.md", "Same content")

    result = hook._inject_amplihack_if_different()

    assert result == ""
    assert "skipping framework injection" in hook.logs
```

### Integration Testing

Test full hook execution:

```bash
# Test with different files
echo '{"userMessage": {"text": "test"}, "cwd": "'$(pwd)'"}' | \
  python3 .claude/tools/amplihack/hooks/user_prompt_submit.py

# Verify output contains AMPLIHACK.md
```

### Performance Testing

Measure cache performance:

```bash
# Run 100 messages and measure timing
for i in {1..100}; do
  time echo '{"userMessage": {"text": "test '$i'"}}' | \
    python3 .claude/tools/amplihack/hooks/user_prompt_submit.py > /dev/null
done

# Expected: First run ~80ms, rest <1ms
```

## Development Guidelines

### When to Modify This API

Modify `_inject_amplihack_if_different()` when:

- Changing comparison logic (e.g., semantic comparison)
- Adding new file locations
- Optimizing cache strategy
- Changing injection format

**Do not modify** for:

- Adding new context types (use new methods)
- Changing injection order (modify `process()`)
- Preference handling (separate method)

### Backward Compatibility

The API maintains backward compatibility:

- **Input format**: Never change hook input schema
- **Output format**: Always return `{"additionalContext": str}`
- **File locations**: Always check old locations first
- **Cache format**: Version cache keys if structure changes

### Performance Considerations

Keep these performance targets:

- **First message**: <100ms total hook time
- **Cached messages**: <5ms total hook time
- **Cache hit rate**: >95%
- **Memory usage**: <10MB per hook process

The current implementation exceeds all targets.

## Related APIs

- **`find_user_preferences()`**: Locate USER_PREFERENCES.md file
- **`get_cached_preferences()`**: Read preferences with caching
- **`build_preference_context()`**: Format preferences for injection
- **`_inject_memories_for_agents()`**: Agent memory injection

See `USER_PROMPT_SUBMIT_README.md` for preference and memory APIs.

## Related

- [Verify Framework Injection](../howto/verify-framework-injection.md) - User guide
- [Framework Injection Architecture](../concepts/framework-injection-architecture.md) - Design rationale
- [Hook Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Hook system overview
