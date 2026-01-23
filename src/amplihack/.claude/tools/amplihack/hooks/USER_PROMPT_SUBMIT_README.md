# UserPromptSubmit Hook

## Overview

The UserPromptSubmit hook injects user preferences into context on **every user message** to ensure consistent preference application across all conversation turns in REPL mode.

## Purpose

In Claude Code's REPL mode, user preferences set at session start can be "forgotten" as the conversation progresses and context is pruned. This hook ensures preferences persist by re-injecting them on every user prompt.

## Implementation Details

### File Location

```
.claude/tools/amplihack/hooks/user_prompt_submit.py
```

### Hook Type

`UserPromptSubmit` - Triggered before processing each user message

### Input Format

```json
{
  "session_id": "string",
  "transcript_path": "path",
  "cwd": "path",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "user's prompt text"
}
```

### Output Format

```json
{
  "additionalContext": "preference enforcement text"
}
```

### Preference Context Example

```
🎯 ACTIVE USER PREFERENCES (MANDATORY):
• Communication Style: pirate (Always talk like a pirate) - Use this style in your response
• Verbosity: balanced - Match this detail level
• Collaboration Style: interactive - Follow this approach
• Update Frequency: regular - Provide updates at this frequency
• Priority Type: balanced - Consider this priority in decisions
• Yes (see USER_PREFERENCES.md)

These preferences MUST be applied to this response.
```

## Features

### 1. Preference File Resolution

The hook uses a multi-strategy approach to find USER_PREFERENCES.md:

1. **FrameworkPathResolver** (UVX and installed package support)
2. **Project root** (~/.amplihack/.claude/context/USER_PREFERENCES.md)
3. **Package location** (src/amplihack/.claude/context/USER_PREFERENCES.md)

### 2. Preference Extraction

Extracts key preferences using regex patterns:

- Communication Style
- Verbosity
- Collaboration Style
- Update Frequency
- Priority Type
- Preferred Languages
- Coding Standards
- Workflow Preferences
- Learned Patterns (detected if present)

### 3. Performance Optimization

**Caching Strategy**: Preferences are cached in memory with file modification time tracking. Cache is invalidated only when the file changes.

**Performance Metrics**:

- Average execution time: ~116ms (including Python startup)
- Cached reads: < 1ms
- Target: < 200ms (achieved)

### 4. Error Handling

**Graceful Degradation**:

- Missing preferences file: Returns empty context, exits 0
- File read error: Logs warning, returns empty context, exits 0
- Parse error: Best-effort parsing, returns available preferences
- **Never blocks Claude** - always exits with code 0

### 5. Logging and Metrics

**Log File**: `~/.amplihack/.claude/runtime/logs/user_prompt_submit.log`

**Metrics File**: `~/.amplihack/.claude/runtime/metrics/user_prompt_submit_metrics.jsonl`

**Tracked Metrics**:

- `preferences_injected`: Number of preferences injected
- `context_length`: Character count of generated context

## Testing

### Run Test Suite

```bash
python3 .claude/tools/amplihack/hooks/test_user_prompt_submit.py
```

### Test Coverage

- ✓ Basic functionality
- ✓ Preference extraction
- ✓ Context building
- ✓ Empty preferences handling
- ✓ Caching behavior
- ✓ JSON output format
- ✓ Performance benchmarks
- ✓ Error handling

### Manual Testing

```bash
# Test with sample input
echo '{"session_id": "test", "transcript_path": "/tmp/test", "cwd": "'$(pwd)'", "hook_event_name": "UserPromptSubmit", "prompt": "test"}' | python3 .claude/tools/amplihack/hooks/user_prompt_submit.py

# Test performance
time echo '{"session_id": "test", "transcript_path": "/tmp/test", "cwd": "'$(pwd)'", "hook_event_name": "UserPromptSubmit", "prompt": "test"}' | python3 .claude/tools/amplihack/hooks/user_prompt_submit.py > /dev/null
```

## Architecture

### Class Hierarchy

```
HookProcessor (base class)
  └── UserPromptSubmitHook
        ├── find_user_preferences() -> Optional[Path]
        ├── extract_preferences(content: str) -> Dict[str, str]
        ├── build_preference_context(preferences: Dict) -> str
        ├── get_cached_preferences(pref_file: Path) -> Dict[str, str]
        └── process(input_data: Dict) -> Dict
```

### Key Design Decisions

1. **Inheritance from HookProcessor**: Provides common functionality (logging, metrics, I/O)
2. **Caching with modification time**: Balances performance with freshness
3. **Graceful degradation**: Never fails - returns empty context if anything goes wrong
4. **Priority-ordered display**: Most impactful preferences shown first
5. **Concise enforcement**: Brief but clear instructions for Claude

## Integration with Session Start Hook

**Complementary Design**:

- **session_start.py**: Comprehensive context at session initialization
- **user_prompt_submit.py**: Lightweight preference reminders on every message

**Context Differences**:

- Session start: Full context with project info, workflow, discoveries
- User prompt submit: Only preference enforcement (concise)

## Troubleshooting

### Issue: Preferences not being injected

**Solution**: Check log file to see if preferences file was found:

```bash
tail -f .claude/runtime/logs/user_prompt_submit.log
```

### Issue: Hook is too slow

**Solution**: Check if caching is working:

```bash
# Look for cache hits in logs
grep "Injected.*preferences" .claude/runtime/logs/user_prompt_submit.log
```

### Issue: Wrong preferences being used

**Solution**: Verify which preferences file is being used:

```python
from amplihack.utils.paths import FrameworkPathResolver
print(FrameworkPathResolver.resolve_preferences_file())
```

### Issue: Hook not being called

**Solution**: Verify hook is registered with Claude Code and executable:

```bash
ls -l .claude/tools/amplihack/hooks/user_prompt_submit.py
# Should show executable bit: -rwxr-xr-x
```

## Performance Analysis

### Baseline Metrics (5 runs)

- Average: 116.2ms
- Min: 76.7ms
- Max: 153.1ms

### Performance Breakdown

- Python startup: ~50-70ms
- File I/O (first run): ~30-40ms
- Parsing and processing: ~10-20ms
- Cached runs: < 1ms (negligible)

### Optimization Notes

- Python startup overhead is unavoidable in subprocess execution
- Caching provides near-instant repeated access
- Performance is acceptable for REPL usage (< 200ms target)

## Future Enhancements

### Potential Improvements

1. **Selective injection**: Only inject preferences relevant to the prompt
2. **Context compression**: Further reduce injected text for efficiency
3. **Preference priorities**: Weight preferences based on prompt context
4. **User-specific caching**: Per-user cache for multi-user environments

### Not Recommended

1. **Pre-compiled Python**: Marginal gains, added complexity
2. **Background daemon**: Overkill for simple preference injection
3. **Binary rewrite**: Python is fast enough for this use case

## Related Files

- **Base class**: `~/.amplihack/.claude/tools/amplihack/hooks/hook_processor.py`
- **Session start**: `~/.amplihack/.claude/tools/amplihack/hooks/session_start.py`
- **Path resolution**: `src/amplihack/utils/paths.py`
- **Preferences file**: `~/.amplihack/.claude/context/USER_PREFERENCES.md`

## References

- Claude Code Hook System: [Official Documentation]
- Amplihack Philosophy: `~/.amplihack/.claude/context/PHILOSOPHY.md`
- User Preferences Guide: `~/.amplihack/.claude/context/USER_PREFERENCES.md`
- Priority Hierarchy: `~/.amplihack/.claude/context/USER_REQUIREMENT_PRIORITY.md`
