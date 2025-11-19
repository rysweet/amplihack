# Auto Mode Interactive UI Test Suite

## Overview

This comprehensive TDD test suite guides the implementation of the Auto Mode Interactive UI feature. All tests are designed to **FAIL initially** and serve as specifications for the implementation.

## Test Structure (Testing Pyramid)

Following the testing pyramid principle:

- **60% Unit Tests**: Individual component testing
- **30% Integration Tests**: Component interaction testing
- **10% E2E Tests**: Full workflow testing

## Test Files

### 1. `test_auto_mode_ui.py` - UI Component Tests

**Purpose**: Test individual UI components in isolation

**Test Classes**:

#### `TestAutoModeUIInitialization`

- `test_ui_mode_creates_ui_instance()` - UI instance creation
- `test_ui_has_required_components()` - All 5 panels exist
- `test_ui_initializes_with_layout()` - Rich layout structure

**Critical Path**: UI must initialize with all components before anything else works.

#### `TestUITitleGeneration`

- `test_title_generation_uses_claude_sdk()` - SDK-based title generation
- `test_title_truncates_long_prompts()` - Max 50 char titles
- `test_title_handles_empty_prompt()` - Default fallback

**Edge Cases**: Empty prompts, very long prompts (500+ chars), unicode titles

#### `TestSessionDetailsDisplay`

- `test_session_panel_shows_turn_counter()` - "Turn X/Y" format
- `test_session_panel_shows_elapsed_time()` - Time formatting (Xm Ys)
- `test_session_panel_shows_cost_tracking()` - Token counts and cost
- `test_session_panel_formats_large_numbers()` - Comma separators

**Boundaries**: Zero turns, negative elapsed time (clock skew), very large token counts

#### `TestTodoListIntegration`

- `test_todo_panel_displays_current_todos()` - Status indicators (⏸▶✓)
- `test_todo_panel_highlights_current_task()` - Rich styling for in_progress
- `test_todo_panel_handles_empty_list()` - "No tasks yet" message

**Error Cases**: Invalid todo structure, missing status fields

#### `TestLogAreaUpdates`

- `test_log_area_displays_streamed_output()` - Append logs, maintain order
- `test_log_area_handles_rapid_updates()` - Batch updates (max 30/sec)
- `test_log_area_truncates_old_content()` - Max 1000 lines buffer
- `test_log_area_formats_timestamps()` - [HH:MM:SS] prefix

**Performance**: 100+ rapid updates, buffer overflow handling

#### `TestPromptInputHandling`

- `test_input_panel_accepts_text_input()` - Queue and clear input
- `test_input_panel_supports_multiline()` - Preserve formatting
- `test_input_creates_instruction_file()` - Write to append/TIMESTAMP.md

**Edge Cases**: Empty input, very long input (>50KB)

#### `TestKeyboardCommands`

- `test_keyboard_command_x_exits_ui()` - Exit UI, continue auto mode
- `test_keyboard_command_p_pauses_execution()` - Pause/resume toggle
- `test_keyboard_command_k_kills_auto_mode()` - Complete shutdown
- `test_keyboard_commands_case_insensitive()` - X/P/K work same as x/p/k

**Error Cases**: Invalid keys, rapid key presses, concurrent commands

#### `TestUIBoundaryConditions`

- `test_ui_handles_very_long_titles()` - 500+ char prompts
- `test_ui_handles_unicode_in_logs()` - Emoji, CJK characters
- `test_ui_handles_zero_max_turns()` - Edge case max_turns=0
- `test_ui_handles_negative_elapsed_time()` - Clock skew protection

#### `TestUIErrorHandling`

- `test_ui_handles_missing_cost_info()` - Show "N/A" for missing data
- `test_ui_handles_todo_update_failure()` - Graceful degradation
- `test_ui_handles_log_write_failure()` - Continue on disk full

---

### 2. `test_ui_threading.py` - Threading Tests

**Purpose**: Test thread-based execution model and thread safety

**Test Classes**:

#### `TestAutoModeBackgroundThread`

- `test_auto_mode_creates_background_thread()` - Thread creation and start
- `test_background_thread_is_daemon()` - Non-daemon for work completion
- `test_background_thread_has_descriptive_name()` - "AutoMode-claude"

**Critical**: Threading must work before any concurrent operations.

#### `TestThreadSafeStateSharing`

- `test_turn_counter_is_thread_safe()` - Lock-protected turn counter
- `test_log_queue_is_thread_safe()` - Queue for message passing
- `test_todo_list_is_thread_safe()` - Lock-protected todo updates
- `test_cost_tracking_is_thread_safe()` - Lock-protected cost data

**Race Conditions**: Concurrent reads/writes from UI and AutoMode threads

#### `TestUIThreadCommunication`

- `test_pause_signal_is_thread_safe()` - threading.Event for pause
- `test_kill_signal_is_thread_safe()` - threading.Event for stop
- `test_instruction_injection_is_thread_safe()` - File-based injection
- `test_command_queue_for_ui_actions()` - Queue for UI commands

**Synchronization**: Events for signals, Queue for commands

#### `TestGracefulShutdown`

- `test_stop_waits_for_current_turn_completion()` - No mid-turn interruption
- `test_shutdown_cleans_up_resources()` - Thread join, close UI, flush logs
- `test_shutdown_handles_thread_timeout()` - Max 5s timeout
- `test_shutdown_is_idempotent()` - Multiple calls safe

**Cleanup**: Resources must be freed even on error/timeout

#### `TestThreadSynchronization`

- `test_no_race_condition_on_turn_counter()` - Atomic operations
- `test_no_deadlock_on_concurrent_access()` - Complete within 5s
- `test_log_queue_doesnt_block_producer()` - Max 500 item queue

**Anti-Patterns**: Deadlocks, race conditions, blocking producers

#### `TestThreadErrorHandling`

- `test_background_thread_exception_is_captured()` - Exception logged
- `test_ui_thread_exception_doesnt_kill_automode()` - Isolated crashes
- `test_thread_cleanup_on_exception()` - Finally blocks for cleanup

**Resilience**: Threads isolated, exceptions don't cascade

---

### 3. `test_ui_sdk_integration.py` - SDK Integration Tests

**Purpose**: Test integration with Claude Agent SDK

**Test Classes**:

#### `TestTitleGenerationViaSDK`

- `test_title_generation_calls_claude_sdk()` - async query() call
- `test_title_generation_handles_sdk_error()` - Fallback on error
- `test_title_generation_timeout()` - 5s timeout with fallback
- `test_title_generation_when_sdk_unavailable()` - CLAUDE_SDK_AVAILABLE check

**Integration**: Claude SDK query() for title generation

#### `TestCostTrackingDisplay`

- `test_cost_info_extracted_from_sdk_messages()` - Parse ResultMessage.usage
- `test_cost_accumulates_across_turns()` - Sum all turns
- `test_cost_calculation_uses_correct_pricing()` - $3/$15 per 1M tokens
- `test_cost_display_formats_currency()` - $X.XX format

**Pricing**: Claude Sonnet 4 pricing (verify current rates)

#### `TestTodoTrackingDisplay`

- `test_todos_updated_on_turn_phase_change()` - Phase transitions
- `test_custom_todos_can_be_added()` - Dynamic todo lists
- `test_todos_persist_across_ui_refresh()` - State in AutoMode

**State Management**: Todos stored in AutoMode, queried by UI

#### `TestSDKStreamingToUI`

- `test_assistant_messages_stream_to_logs()` - AssistantMessage → logs
- `test_tool_usage_messages_logged()` - ToolUseMessage formatting
- `test_result_messages_show_completion()` - ResultMessage logging
- `test_streaming_handles_rapid_messages()` - 100+ messages/sec

**Message Types**: AssistantMessage, ToolUseMessage, ResultMessage, SystemMessage

#### `TestSDKErrorHandling`

- `test_sdk_connection_error_shown_in_ui()` - ConnectionError display
- `test_sdk_rate_limit_shown_with_retry_info()` - 429 retry countdown
- `test_sdk_unavailable_shows_fallback_message()` - SDK detection

**Error Types**: ConnectionError, rate limits (429), SDK unavailable

#### `TestSDKPerformanceMetrics`

- `test_turn_latency_is_tracked()` - Time per turn
- `test_tokens_per_second_calculated()` - Output throughput

**Metrics**: Latency (seconds), throughput (tokens/sec)

---

### 4. `test_auto_mode_ui_integration.py` - E2E Integration Tests

**Purpose**: End-to-end workflows with all components

**Test Classes**:

#### `TestFullUIWorkflow`

- `test_ui_starts_and_displays_initial_state()` - Complete startup
- `test_ui_updates_during_execution()` - Live updates
- `test_ui_shows_completion_state()` - Final state display
- `test_ui_handles_execution_error()` - Error recovery

**Journey**: Start → Execute → Complete/Error

#### `TestPromptInjectionViaUI`

- `test_inject_instruction_during_execution()` - Live injection workflow
- `test_multiple_injections_queued_in_order()` - FIFO processing
- `test_injection_appears_in_ui_logs()` - User feedback
- `test_injection_with_multiline_content()` - Preserve formatting

**Workflow**: Type input → Submit → File created → Auto mode picks up → Process

#### `TestPauseAndResume`

- `test_pause_stops_new_turns()` - No turn advancement when paused
- `test_resume_continues_execution()` - Normal execution after resume
- `test_pause_indicator_in_ui()` - "PAUSED" or ⏸ indicator
- `test_can_inject_while_paused()` - Queue instructions while paused

**User Flow**: Running → Pause → Inject → Resume → Process

#### `TestExitUIAutoModeContinues`

- `test_exit_ui_keeps_automode_running()` - Background continues
- `test_exit_switches_to_terminal_output()` - Fallback to terminal
- `test_logs_flushed_on_ui_exit()` - No lost logs

**Use Case**: Start with UI, exit to terminal (long-running tasks)

#### `TestErrorRecoveryScenarios`

- `test_recover_from_sdk_timeout()` - Retry with backoff
- `test_recover_from_ui_thread_crash()` - Isolated crashes
- `test_graceful_degradation_on_missing_dependencies()` - Rich unavailable

**Resilience**: Timeouts, crashes, missing dependencies

---

## Running the Tests

### Run All UI Tests

```bash
pytest tests/unit/test_auto_mode_ui.py -v
pytest tests/unit/test_ui_threading.py -v
pytest tests/unit/test_ui_sdk_integration.py -v
pytest tests/integration/test_auto_mode_ui_integration.py -v
```

### Run by Test Class

```bash
# UI components only
pytest tests/unit/test_auto_mode_ui.py::TestAutoModeUIInitialization -v

# Threading only
pytest tests/unit/test_ui_threading.py::TestThreadSafeStateSharing -v

# SDK integration only
pytest tests/unit/test_ui_sdk_integration.py::TestTitleGenerationViaSDK -v

# E2E workflows only
pytest tests/integration/test_auto_mode_ui_integration.py::TestFullUIWorkflow -v
```

### Run with Coverage

```bash
pytest tests/unit/test_auto_mode_ui.py --cov=amplihack.launcher.auto_mode --cov-report=html
```

### Expected Initial Results

**All tests should FAIL** with `AttributeError` until implementation:

```
FAILED test_auto_mode_ui.py::TestAutoModeUIInitialization::test_ui_mode_creates_ui_instance
  AttributeError: 'AutoMode' object has no attribute 'ui_enabled'

FAILED test_ui_threading.py::TestAutoModeBackgroundThread::test_auto_mode_creates_background_thread
  AttributeError: 'AutoMode' object has no attribute 'start_background'

FAILED test_ui_sdk_integration.py::TestTitleGenerationViaSDK::test_title_generation_calls_claude_sdk
  AttributeError: 'NoneType' object has no attribute 'generate_title_async'
```

---

## Implementation Guide

### Phase 1: UI Foundation (test_auto_mode_ui.py)

1. Add `ui_mode` parameter to AutoMode.**init**()
2. Create UIManager class with 5 panels (title, session, todos, logs, input)
3. Implement Rich layout structure
4. Basic rendering loop

**Tests to Pass**: TestAutoModeUIInitialization

### Phase 2: Threading (test_ui_threading.py)

1. Add threading.Thread for background execution
2. Implement thread-safe state (Locks, Events, Queue)
3. UI-to-AutoMode communication (pause/kill/inject)
4. Graceful shutdown with cleanup

**Tests to Pass**: TestAutoModeBackgroundThread, TestThreadSafeStateSharing

### Phase 3: SDK Integration (test_ui_sdk_integration.py)

1. Title generation via Claude SDK query()
2. Cost tracking from ResultMessage.usage
3. Message streaming to log queue
4. Error handling and retries

**Tests to Pass**: TestTitleGenerationViaSDK, TestCostTrackingDisplay

### Phase 4: User Interactions (test_auto_mode_ui.py)

1. Keyboard command handling (x, p, k)
2. Prompt input panel
3. Instruction file creation
4. Todo list updates

**Tests to Pass**: TestKeyboardCommands, TestPromptInputHandling

### Phase 5: E2E Workflows (test_auto_mode_ui_integration.py)

1. Complete startup workflow
2. Live injection during execution
3. Pause/resume functionality
4. Exit to terminal mode

**Tests to Pass**: TestFullUIWorkflow, TestPromptInjectionViaUI

---

## Test Coverage Goals

### By Component

| Component         | Target | Critical Paths                           |
| ----------------- | ------ | ---------------------------------------- |
| UI Components     | 90%    | Initialization, rendering, updates       |
| Threading         | 95%    | State sharing, synchronization, shutdown |
| SDK Integration   | 85%    | Streaming, cost tracking, errors         |
| User Interactions | 90%    | Commands, input, injection               |
| E2E Workflows     | 70%    | Happy path, error recovery               |

### By Test Type

| Type              | Percentage | Focus                             |
| ----------------- | ---------- | --------------------------------- |
| Unit Tests        | 60%        | Individual components, edge cases |
| Integration Tests | 30%        | Component interactions, SDK calls |
| E2E Tests         | 10%        | Full workflows, user journeys     |

---

## Key Design Decisions

### 1. Threading Model

- **Main Thread**: UI rendering and input handling
- **Background Thread**: Auto mode execution
- **Communication**: Queue for logs, Events for signals, Locks for shared state

### 2. State Management

- **AutoMode owns state**: Turn counter, todos, cost info
- **UI queries state**: Read-only access via thread-safe methods
- **Updates via queue**: Logs pushed to UI via Queue

### 3. Instruction Injection

- **File-based**: UI writes to append/TIMESTAMP.md
- **Polling**: AutoMode checks before each turn
- **Thread-safe**: File operations atomic, no locks needed

### 4. Error Handling

- **Isolated threads**: UI crash doesn't kill AutoMode
- **Graceful degradation**: Fall back to terminal if UI fails
- **Retry logic**: SDK errors retry with exponential backoff

### 5. Performance

- **Log batching**: Max 30 UI updates/sec
- **Buffer limits**: 1000 line log buffer, 500 item queue
- **Non-blocking**: UI never blocks AutoMode execution

---

## Common Issues and Solutions

### Issue: Tests hang on threading operations

**Solution**: Use timeout parameters on Thread.join() and Queue.get()

```python
auto_mode.execution_thread.join(timeout=5)
log = auto_mode.log_queue.get(timeout=1)
```

### Issue: Race conditions in tests

**Solution**: Add small sleeps to let threads synchronize

```python
auto_mode.start_background()
time.sleep(0.1)  # Let thread start
assert auto_mode.execution_thread.is_alive()
```

### Issue: Mocked SDK not working

**Solution**: Patch at correct import location

```python
with patch('amplihack.launcher.auto_mode.query', ...):  # Correct
with patch('claude_agent_sdk.query', ...):  # Wrong - not imported there
```

### Issue: AttributeError on ui_mode

**Solution**: Add ui_mode parameter with default False

```python
def __init__(self, sdk, prompt, max_turns=10, working_dir=None, ui_mode=False):
    self.ui_enabled = ui_mode
```

---

## Success Criteria

### Implementation Complete When:

1. ✓ All unit tests pass (test_auto_mode_ui.py, test_ui_threading.py, test_ui_sdk_integration.py)
2. ✓ All integration tests pass (test_auto_mode_ui_integration.py)
3. ✓ No race conditions or deadlocks detected
4. ✓ Memory usage stable (no leaks from queue/threads)
5. ✓ Performance meets targets (30 FPS UI, <100ms input latency)
6. ✓ Manual testing confirms usability

### Quality Gates:

- **Code Coverage**: >85% for UI module
- **Thread Safety**: All shared state protected
- **Error Handling**: All error paths tested
- **Performance**: <50ms 95th percentile latency for UI updates
- **Documentation**: Docstrings for all public methods

---

## Next Steps After Tests Pass

1. **Manual Testing**: Real usage with Claude SDK
2. **Performance Profiling**: Identify bottlenecks
3. **UI Polish**: Colors, formatting, help text
4. **User Feedback**: Beta test with team
5. **Documentation**: User guide and demos

---

## References

- **Testing Pyramid**: https://martinfowler.com/bliki/TestPyramid.html
- **Thread Safety**: https://docs.python.org/3/library/threading.html
- **Rich Library**: https://rich.readthedocs.io/
- **Claude SDK**: Project documentation
- **TDD Principles**: Red-Green-Refactor cycle

---

**Generated**: 2025-01-28
**Test Count**: 100+ comprehensive tests
**Coverage**: Unit (60%), Integration (30%), E2E (10%)
