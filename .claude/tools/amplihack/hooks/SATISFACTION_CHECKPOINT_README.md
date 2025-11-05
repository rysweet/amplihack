# User Satisfaction Checkpoints

## Overview

Satisfaction checkpoints provide explicit user feedback moments after investigation tasks complete their synthesis. This ensures users can indicate whether the explanation answered their questions and provides clear pathways for follow-up actions.

## Feature Summary

**What**: Automatic checkpoint display after investigation commands (knowledge-builder, analyze, expert-panel, debate, socratic)

**Why**: Addresses Issue #1107 - Sessions were ending without confirming if explanations were sufficient or if follow-up was needed

**How**: Modified `post_tool_use.py` hook to detect investigation completions and display satisfaction checkpoint template

## Implementation Details

### Components

1. **Detection Logic** (`post_tool_use.py`)
   - Monitors tool usage via post_tool_use hook
   - Detects investigation commands: knowledge-builder, analyze, expert-panel, debate, socratic
   - Extracts topics from investigation results for personalization

2. **Checkpoint Template** (`.claude/templates/SATISFACTION_CHECKPOINT.md`)
   - Displays 5 follow-up options (A-E)
   - Respects user communication preferences (pirate, formal, technical)
   - Dynamically injects extracted topics

3. **User Preferences Integration**
   - Loads `USER_PREFERENCES.md` for communication style
   - Applies style transformations to template
   - Supports: pirate, formal, technical, casual

4. **Metrics Logging**
   - Tracks satisfaction checkpoint displays
   - Logs investigation type and timestamp
   - Enables future satisfaction metrics analysis

### How It Works

```
Investigation Command Executed
       ↓
post_tool_use hook fires
       ↓
Is it an investigation command?
       ↓ (yes)
Extract topics from result
       ↓
Load checkpoint template
       ↓
Apply user preferences
       ↓
Display checkpoint to user (stderr)
       ↓
Log metric
       ↓
User responds in next message
```

### Checkpoint Options

When displayed, users see:

- **Option A**: Dive deeper into [topic 1]
- **Option B**: Explore [topic 2] in detail
- **Option C**: Create documentation
- **Option D**: Generate diagrams
- **Option E**: Stop here
- **Custom**: Or tell me something else you'd like to explore

## Configuration

### Enable/Disable Checkpoints

Create `.claude/tools/amplihack/.satisfaction_checkpoint_config`:

```json
{
  "enabled": true
}
```

Set `"enabled": false` to disable checkpoints globally.

### Communication Style

Checkpoints respect the communication_style in `USER_PREFERENCES.md`:

```markdown
communication_style: pirate
```

Supported styles:

- `pirate` (default): Casual, pirate-themed language
- `formal`: Professional, formal language
- `technical`: Direct, technical language
- `casual`: Conversational tone

## Testing

### Unit Tests

Run unit tests for satisfaction checkpoint:

```bash
cd .claude/tools/amplihack/hooks
python -m pytest test_satisfaction_checkpoint.py -v
```

### Integration Tests

Test with actual investigation commands:

```bash
# Test knowledge-builder triggers checkpoint
/amplihack:knowledge-builder "Test topic"

# Test analyze triggers checkpoint
/analyze ./src

# Verify checkpoint appears in output
```

### Manual Testing

1. Run an investigation command
2. Verify checkpoint appears after synthesis
3. Check that topics are extracted correctly
4. Verify communication style is applied
5. Test each option (A-E) with user response

## Metrics

Satisfaction checkpoints log metrics to:

`.claude/runtime/metrics/post_tool_use_metrics.jsonl`

Metric fields:

- `metric`: "satisfaction_checkpoint_shown"
- `value`: investigation_type (e.g., "knowledge-builder")
- `timestamp`: ISO 8601 timestamp
- `metadata`: Additional context

## Future Enhancements

Potential improvements for future iterations:

1. **Response Tracking**: Log which option users select
2. **Satisfaction Scoring**: Track yes/no/partial responses
3. **Smart Topic Extraction**: Use NLP for better topic identification
4. **Template Variations**: Different templates for different investigation types
5. **A/B Testing**: Compare checkpoint effectiveness

## Architecture Decisions

### Decision 1: Use post_tool_use Hook

**Why**: Reuses existing infrastructure, minimal new code
**Alternatives**: Create new `PostInvestigation` hook (rejected: over-engineering)

### Decision 2: Display via stderr

**Why**: Visible to user, non-intrusive, doesn't block Claude response
**Alternatives**: Block with decision (rejected: too intrusive)

### Decision 3: Template-based Design

**Why**: Easy to customize, separates content from logic
**Alternatives**: Hardcoded strings (rejected: not preference-aware)

## Related Files

- `post_tool_use.py` - Main implementation
- `.claude/templates/SATISFACTION_CHECKPOINT.md` - Checkpoint template
- `test_satisfaction_checkpoint.py` - Unit tests
- `USER_PREFERENCES.md` - Communication style configuration

## Issue Reference

- **Issue**: #1107
- **PR**: (To be added after PR creation)
- **Reflection**: reflection-session-20251104_210400 (Recommendation 2)

## Success Criteria

- ✅ Checkpoint appears after investigation commands
- ✅ Template respects user preferences
- ✅ User can select options naturally
- ✅ Satisfaction metrics are logged
- ✅ No false positives on non-investigation commands
- ✅ Feature can be disabled via config

---

**Last Updated**: 2025-11-05
**Author**: Claude (Builder Agent)
**Status**: Complete - Ready for Testing
