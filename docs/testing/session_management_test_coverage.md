# TDD Test Coverage: Auto Mode Session Management

## Overview

This document describes the comprehensive failing tests created for session management functionality in `auto_mode.py`. Following TDD principles, these tests define success criteria BEFORE implementation.

**Test File**: `/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/worktrees/feat-session-management/tests/test_auto_mode_session_management.py`

## Test Categories

### 1. Message Tracking (8 tests)

**Purpose**: Ensure all messages are captured during auto mode execution for transcript generation.

#### Tests:

- `test_auto_mode_has_messages_list` - AutoMode must have `self.messages` list
- `test_messages_captured_during_clarify_phase` - Messages captured in Turn 1 (clarify)
- `test_messages_captured_during_planning_phase` - Messages captured in Turn 2 (plan)
- `test_messages_captured_during_execution_phase` - Messages captured in execution turns
- `test_messages_captured_during_evaluation_phase` - Messages captured after each execute
- `test_message_format_includes_required_fields` - Messages match transcript builder format
- `test_all_phases_captured_in_complete_session` - All phases present in complete session

**Expected Message Format**:

```python
{
    'role': 'user' | 'assistant',
    'content': 'message content',
    'timestamp': 'ISO format timestamp',
    'phase': 'clarifying' | 'planning' | 'executing' | 'evaluating' | 'summarizing',
    'turn': 1-N
}
```

**Success Criteria**:

- ✓ Messages list exists and starts empty
- ✓ Messages captured at each phase
- ✓ Message format compatible with ClaudeTranscriptBuilder
- ✓ All phases represented in complete session

---

### 2. Duration Tracking (6 tests)

**Purpose**: Track session duration and format it human-readable for logs and transcripts.

#### Tests:

- `test_session_duration_calculated_correctly` - Duration = current_time - start_time
- `test_duration_formatted_as_seconds_for_short_sessions` - "45s" for 45 seconds
- `test_duration_formatted_as_minutes_and_seconds` - "2m 5s" for 125 seconds
- `test_duration_appears_in_progress_string` - Progress shows "[Turn 2/10 | Planning | 1m 23s]"
- `test_session_duration_tracked_in_metadata` - Duration stored in session_metadata
- `test_duration_formatted_for_export` - Both seconds and formatted duration in metadata

**Success Criteria**:

- ✓ Duration calculated from start to current time
- ✓ Format: "<60s" → "Xs", ">=60s" → "Xm Ys"
- ✓ Duration visible in progress logs
- ✓ Duration available in session metadata for export

---

### 3. Fork Detection (6 tests)

**Purpose**: Automatically fork sessions at 60-minute threshold to prevent context loss.

#### Tests:

- `test_fork_not_triggered_before_60_minutes` - No fork at 59 minutes
- `test_fork_triggered_at_60_minutes` - Fork triggers at exactly 60 minutes
- `test_fork_triggered_after_60_minutes` - Fork triggers after 60 minutes
- `test_fork_creates_new_session_with_context` - New AutoMode with continuation context
- `test_fork_exports_current_session_before_forking` - Export transcript before fork
- `test_fork_logs_continuation_marker` - Log fork event with new session ID

**Fork Workflow**:

```python
if session_duration >= 60 minutes:
    1. Export current session transcript
    2. Create summary of work so far
    3. Create new AutoMode instance
    4. Pass summary as context to new session
    5. Log fork event
    6. Continue execution in new session
```

**Success Criteria**:

- ✓ Fork detection at 60-minute threshold
- ✓ Export before forking
- ✓ Context carried forward
- ✓ Fork events logged

---

### 4. Export Integration (7 tests)

**Purpose**: Export session data to transcript files compatible with ClaudeTranscriptBuilder.

#### Tests:

- `test_export_method_exists` - `_export_session_transcript()` method exists
- `test_export_creates_transcript_file` - Creates `CONVERSATION_TRANSCRIPT.md`
- `test_export_includes_all_messages` - All messages from `self.messages` in transcript
- `test_export_includes_duration_metadata` - Duration in transcript header
- `test_export_called_in_stop_hook` - Export triggered when session ends
- `test_export_creates_json_for_programmatic_access` - JSON version created

**Export File Structure**:

```
.claude/runtime/logs/<session_id>/
├── CONVERSATION_TRANSCRIPT.md  (markdown, human-readable)
├── conversation_transcript.json (json, programmatic access)
└── session_summary.json         (summary statistics)
```

**Success Criteria**:

- ✓ Export method exists and is callable
- ✓ Markdown and JSON transcripts created
- ✓ All messages included in transcript
- ✓ Duration metadata in transcript
- ✓ Export triggered at session end

---

### 5. Backward Compatibility (5 tests)

**Purpose**: Ensure session management doesn't break existing auto_mode usage.

#### Tests:

- `test_auto_mode_works_without_session_tracking` - Optional `enable_session_management` flag
- `test_existing_public_api_unchanged` - Public methods unchanged
- `test_session_management_minimal_overhead` - <5% performance overhead
- `test_session_dir_structure_compatible` - Files in `~/.amplihack/.claude/runtime/logs/<session_id>/`
- `test_existing_hooks_still_called` - `session_start` and `stop` hooks still called

**Backward Compatibility Requirements**:

```python
# Old code still works
auto_mode = AutoMode(sdk="claude", prompt="Test")
auto_mode.run()  # Works as before

# New code with session management
auto_mode = AutoMode(sdk="claude", prompt="Test", enable_session_management=True)
auto_mode.run()  # Includes message tracking and export
```

**Success Criteria**:

- ✓ Existing code works without changes
- ✓ Session management is optional
- ✓ No required new parameters
- ✓ Minimal performance impact (<5% overhead)
- ✓ Hooks still called as expected

---

### 6. Session Metadata (3 tests)

**Purpose**: Collect structured metadata for transcript builder and analysis.

#### Tests:

- `test_session_metadata_structure` - Metadata has all required fields
- `test_session_metadata_phase_breakdown` - Time spent in each phase
- `test_session_metadata_compatible_with_transcript_builder` - JSON-serializable format

**Metadata Structure**:

```python
{
    "session_id": "auto_claude_1234567890",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-01T00:05:00",
    "duration_seconds": 300,
    "duration_formatted": "5m 0s",
    "total_turns": 5,
    "max_turns": 10,
    "prompt": "User's initial prompt",
    "sdk": "claude",
    "phase_breakdown": {
        "clarifying": 30,
        "planning": 45,
        "executing": 180,
        "evaluating": 30,
        "summarizing": 15
    }
}
```

**Success Criteria**:

- ✓ Complete metadata structure
- ✓ Phase time breakdown
- ✓ JSON-serializable
- ✓ Compatible with ClaudeTranscriptBuilder

---

## Test Execution Summary

### Current Status: ALL TESTS FAILING (Expected)

This is correct TDD behavior:

1. ✓ Write failing tests FIRST
2. ⏳ Implement functionality to make tests pass
3. ⏳ Refactor while keeping tests green

### Running the Tests

```bash
# Run all session management tests
python tests/test_auto_mode_session_management.py

# Expected output: ~35 failures/errors
# This is GOOD - tests define what needs to be implemented
```

### Test Failure Categories

1. **AttributeError** - Methods/attributes don't exist yet:
   - `self.messages` list
   - `_should_fork_session()` method
   - `_fork_session()` method
   - `_export_session_transcript()` method
   - `session_metadata` attribute

2. **TypeError** - Parameters don't exist yet:
   - `enable_session_management` flag

3. **Logic Failures** - Functionality not implemented:
   - Message capture during phases
   - Duration tracking in metadata
   - Export integration
   - Fork detection

---

## Implementation Roadmap

### Phase 1: Basic Message Tracking

1. Add `self.messages = []` to `__init__()`
2. Add `_capture_message()` helper method
3. Call `_capture_message()` at each phase
4. Ensure message format matches tests

**Tests to pass**: TestMessageTracking (8 tests)

### Phase 2: Duration Tracking

1. Add `self.session_metadata = {}` to `__init__()`
2. Track phase start/end times
3. Calculate phase durations
4. Update metadata with durations

**Tests to pass**: TestDurationTracking (6 tests)

### Phase 3: Export Integration

1. Add `_export_session_transcript()` method
2. Integrate with ClaudeTranscriptBuilder
3. Call export in `finally` block
4. Create both markdown and JSON files

**Tests to pass**: TestExportIntegration (7 tests)

### Phase 4: Fork Detection

1. Add `_should_fork_session()` method
2. Add `_fork_session()` method
3. Check duration at each turn
4. Export before forking
5. Create new session with context

**Tests to pass**: TestForkDetection (6 tests)

### Phase 5: Metadata & Compatibility

1. Complete metadata structure
2. Add `enable_session_management` flag
3. Ensure backward compatibility
4. Performance validation

**Tests to pass**: TestSessionMetadata (3 tests) + TestBackwardCompatibility (5 tests)

---

## Success Metrics

### Code Coverage

- **Target**: >95% coverage of new session management code
- **Focus**: All new methods and attributes

### Test Coverage

- **Total Tests**: 35
- **Categories**: 6 (Message Tracking, Duration, Fork, Export, Compatibility, Metadata)
- **Current Status**: 0/35 passing (Expected - TDD approach)

### Performance Requirements

- **Overhead**: <5% performance impact when enabled
- **Memory**: <10MB additional memory for typical session
- **Export Time**: <1s for 100 messages

### Quality Gates

- ✓ All 35 tests passing
- ✓ No breaking changes to public API
- ✓ Backward compatible with existing code
- ✓ Integration with ClaudeTranscriptBuilder validated
- ✓ Fork workflow tested end-to-end

---

## Integration Points

### 1. ClaudeTranscriptBuilder

**File**: `~/.amplihack/.claude/tools/amplihack/builders/claude_transcript_builder.py`

**Interface**:

```python
from builders.claude_transcript_builder import ClaudeTranscriptBuilder

builder = ClaudeTranscriptBuilder(session_id=self.session_id)
transcript_path = builder.build_session_transcript(
    messages=self.messages,
    metadata=self.session_metadata
)
```

### 2. Stop Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/stop.py`

**Integration**: Export should be called before stop hook runs, allowing stop hook to process the transcript.

### 3. Session Start Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/session_start.py`

**Integration**: Session start hook should receive session metadata, including whether this is a forked session.

---

## Testing Strategy

### Unit Tests (Current)

- Test individual methods in isolation
- Mock external dependencies
- Focus on logic correctness

### Integration Tests (Future)

- Test interaction with ClaudeTranscriptBuilder
- Test interaction with hooks
- Test complete session lifecycle

### E2E Tests (Future)

- Test real auto mode sessions
- Validate transcript quality
- Test fork workflow in real scenarios

---

## Critical Test Cases

### Most Important Tests (Must Pass First)

1. **test_auto_mode_has_messages_list** - Foundation for all message tracking
2. **test_message_format_includes_required_fields** - Ensures compatibility
3. **test_export_method_exists** - Core export functionality
4. **test_session_metadata_structure** - Metadata foundation
5. **test_existing_public_api_unchanged** - Backward compatibility

### High-Risk Tests (Focus on Edge Cases)

1. **test_fork_triggered_at_60_minutes** - Exact threshold behavior
2. **test_session_management_minimal_overhead** - Performance impact
3. **test_export_called_in_stop_hook** - Integration with existing hooks
4. **test_fork_exports_current_session_before_forking** - Data integrity

---

## Notes for Implementation

### Design Decisions

1. **Message Format**: Follow ClaudeTranscriptBuilder expectations exactly
2. **Fork Threshold**: 60 minutes (configurable in future)
3. **Export Timing**: In `finally` block to ensure it always runs
4. **Backward Compatibility**: Optional via `enable_session_management` flag
5. **Performance**: Lazy initialization, minimal overhead

### Future Enhancements

1. Configurable fork threshold
2. Compression for large sessions
3. Streaming export (don't wait for end)
4. Multiple export formats (HTML, PDF)
5. Session replay functionality

---

## Conclusion

These tests provide complete coverage for session management functionality:

- ✓ Message tracking across all phases
- ✓ Duration tracking and formatting
- ✓ Fork detection at 60 minutes
- ✓ Export integration with transcript builder
- ✓ Backward compatibility preservation
- ✓ Metadata collection and structure

**Current Status**: All 35 tests failing as expected (TDD approach)

**Next Step**: Implement functionality to make tests pass, one category at a time.
