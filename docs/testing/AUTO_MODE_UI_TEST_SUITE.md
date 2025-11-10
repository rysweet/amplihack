# Auto Mode Interactive UI - Comprehensive TDD Test Suite

## Executive Summary

This comprehensive test-driven development (TDD) test suite provides complete specifications for implementing the Auto Mode Interactive UI feature. All tests are designed to **FAIL initially** and serve as living documentation guiding implementation.

## Test Suite Overview

### Files Created

1. **tests/unit/test_auto_mode_ui.py** (380 lines)
   - UI component tests
   - 10 test classes, 40+ tests
   - Coverage: Initialization, title generation, session details, todos, logs, input, keyboard commands, edge cases

2. **tests/unit/test_ui_threading.py** (300 lines)
   - Threading and concurrency tests
   - 6 test classes, 25+ tests
   - Coverage: Background threads, thread safety, communication, shutdown, synchronization, error handling

3. **tests/unit/test_ui_sdk_integration.py** (280 lines)
   - Claude SDK integration tests
   - 6 test classes, 30+ tests
   - Coverage: Title generation, cost tracking, todo updates, streaming, error handling, performance

4. **tests/integration/test_auto_mode_ui_integration.py** (320 lines)
   - End-to-end integration tests
   - 5 test classes, 20+ tests
   - Coverage: Full workflows, prompt injection, pause/resume, exit behavior, error recovery

5. **tests/unit/README_AUTO_MODE_UI_TESTS.md** (Complete documentation)
   - Test structure and organization
   - Implementation guide by phase
   - Common issues and solutions
   - Success criteria

**Total**: 1,280+ lines of comprehensive tests, 115+ test cases

## Testing Pyramid Distribution

```
         /\
        /  \      E2E Tests (10%)
       /____\     - Full workflows
      /      \    Integration Tests (30%)
     /        \   - Component interaction
    /__________\  Unit Tests (60%)
                  - Individual components
```

### Coverage by Type

- **Unit Tests**: 60% (~70 tests) - Component isolation, edge cases, boundaries
- **Integration Tests**: 30% (~35 tests) - SDK integration, thread communication
- **E2E Tests**: 10% (~20 tests) - Complete user journeys

## Feature Requirements Tested

### 1. Interactive UI with 5 Areas

- ✓ Title panel (generated from prompt via Claude SDK)
- ✓ Session details panel (turn counter, elapsed time, cost tracking)
- ✓ Todo list panel (status indicators, current task highlighting)
- ✓ Log area panel (streaming output, timestamps, buffer management)
- ✓ Prompt input panel (multiline support, instruction queueing)

### 2. Keyboard Commands

- ✓ 'x' - Exit UI, continue auto mode in background
- ✓ 'p' - Pause/resume execution
- ✓ 'k' - Kill auto mode completely
- ✓ 'h' - Show help overlay (bonus)

### 3. Claude Agent SDK Integration

- ✓ Title generation via SDK query()
- ✓ Cost tracking (input/output tokens, estimated cost)
- ✓ Message streaming (AssistantMessage, ToolUseMessage, ResultMessage)
- ✓ Error handling (connection errors, rate limits, timeouts)
- ✓ Performance metrics (latency, throughput)

### 4. Rich CLI Library Implementation

- ✓ Layout structure (5 panels with proper sizing)
- ✓ Live updates (panel content refresh)
- ✓ Styling (colors, highlighting, status indicators)
- ✓ Unicode support (emoji, CJK characters)

### 5. Thread-Based Execution

- ✓ Background thread for auto mode
- ✓ Main thread for UI rendering
- ✓ Thread-safe state sharing (Locks, Events, Queue)
- ✓ Graceful shutdown and cleanup
- ✓ No deadlocks or race conditions

## Test Organization

### Phase 1: UI Foundation

**File**: test_auto_mode_ui.py
**Classes**: TestAutoModeUIInitialization, TestUITitleGeneration, TestSessionDetailsDisplay

**Focus**:

- UI instance creation with ui_mode=True
- Rich layout with 5 panels
- Title generation (SDK + fallback)
- Session panel (turn, time, cost)

**Key Tests**:

- test_ui_mode_creates_ui_instance()
- test_ui_has_required_components()
- test_title_generation_uses_claude_sdk()
- test_session_panel_shows_turn_counter()

### Phase 2: Threading Infrastructure

**File**: test_ui_threading.py
**Classes**: TestAutoModeBackgroundThread, TestThreadSafeStateSharing, TestGracefulShutdown

**Focus**:

- Background thread creation
- Thread-safe state (turn, logs, todos, cost)
- UI-to-AutoMode communication
- Shutdown and cleanup

**Key Tests**:

- test_auto_mode_creates_background_thread()
- test_turn_counter_is_thread_safe()
- test_log_queue_is_thread_safe()
- test_shutdown_cleans_up_resources()

### Phase 3: SDK Integration

**File**: test_ui_sdk_integration.py
**Classes**: TestTitleGenerationViaSDK, TestCostTrackingDisplay, TestSDKStreamingToUI

**Focus**:

- Claude SDK query() calls
- Token counting and cost calculation
- Message streaming to logs
- Error handling and retries

**Key Tests**:

- test_title_generation_calls_claude_sdk()
- test_cost_accumulates_across_turns()
- test_assistant_messages_stream_to_logs()
- test_sdk_connection_error_shown_in_ui()

### Phase 4: User Interactions

**File**: test_auto_mode_ui.py
**Classes**: TestPromptInputHandling, TestKeyboardCommands, TestTodoListIntegration

**Focus**:

- Keyboard command handling
- Prompt input and injection
- Todo list updates
- Log area updates

**Key Tests**:

- test_keyboard_command_x_exits_ui()
- test_keyboard_command_p_pauses_execution()
- test_input_creates_instruction_file()
- test_todo_panel_displays_current_todos()

### Phase 5: End-to-End Workflows

**File**: test_auto_mode_ui_integration.py
**Classes**: TestFullUIWorkflow, TestPromptInjectionViaUI, TestPauseAndResume

**Focus**:

- Complete startup to completion
- Live instruction injection
- Pause/resume flow
- Exit to terminal mode

**Key Tests**:

- test_ui_starts_and_displays_initial_state()
- test_inject_instruction_during_execution()
- test_pause_stops_new_turns()
- test_exit_ui_keeps_automode_running()

## Critical Paths Tested

### Startup Flow

1. AutoMode(ui_mode=True) → Creates UI instance
2. UI.**init**() → Creates 5 panels with Rich layout
3. generate_title() → Claude SDK query for concise title
4. start_background() → Creates execution thread
5. UI render loop → Display initial state

### Execution Flow

1. Auto mode runs in background thread
2. Logs queued via Queue → UI consumes and displays
3. Turn counter updated → Session panel refreshes
4. Todos updated → Todo panel refreshes
5. Cost info updated → Session panel shows tokens/cost

### Injection Flow

1. User types in input panel → Text queued
2. User submits → Write to append/TIMESTAMP.md
3. Auto mode checks before turn → Detects new file
4. Read and sanitize content → Append to execute prompt
5. Move to appended/ → Process instruction

### Pause/Resume Flow

1. User presses 'p' → Set pause_event
2. Auto mode checks event → Complete current turn
3. Auto mode waits on event → No new turns start
4. User presses 'p' again → Clear pause_event
5. Auto mode continues → Normal execution resumes

### Exit Flow

1. User presses 'x' → Set ui.should_exit()
2. UI render loop exits → Close UI
3. Switch to terminal mode → Continue logging to stdout
4. Auto mode continues → Background thread alive
5. Eventually completes → Cleanup and exit

## Boundary Conditions Tested

### Empty/Zero Cases

- Empty prompt → Default title "Auto Mode Session"
- max_turns=0 → Graceful handling
- Empty todo list → "No tasks yet" message
- No cost info → Display "N/A"

### Large Values

- 500+ char prompts → Truncate to 50 chars
- 1M+ tokens → Comma formatting (1,000,000)
- 100+ rapid log messages → Batch updates (30/sec)
- 1000+ log lines → Buffer truncation

### Edge Cases

- Negative elapsed time → Clamp to 0s (clock skew)
- Unicode in logs → Emoji, CJK display correctly
- Concurrent reads/writes → No race conditions
- Thread timeout → Max 5s wait on shutdown

### Error Cases

- SDK connection error → Display error, continue
- Rate limit (429) → Show retry countdown, backoff
- UI thread crash → Auto mode isolated, continues
- Missing Rich library → Fall back to terminal
- Disk full → Skip log write, continue

## Thread Safety Verification

### Protected State

- **turn_counter**: threading.Lock
- **todos_list**: threading.Lock
- **cost_info**: threading.Lock
- **log_messages**: Queue (thread-safe by default)

### Signals

- **pause_event**: threading.Event
- **stop_event**: threading.Event

### Race Condition Tests

- 100 concurrent turn increments → Final value correct
- Concurrent todo reads/writes → No corruption
- Log queue overflow → Oldest dropped, no block

### Deadlock Prevention

- Timeout on all Queue.get() calls (1-5 seconds)
- Timeout on Thread.join() calls (5 seconds)
- Lock acquisition order documented
- Test completes in <5 seconds

## Performance Targets

### UI Responsiveness

- **Frame Rate**: 30 FPS target (33ms per frame)
- **Input Latency**: <100ms from keypress to UI update
- **Log Batching**: Max 30 updates/sec (reduce flickering)

### Memory Usage

- **Log Buffer**: 1000 lines max (~100KB)
- **Queue Size**: 500 items max (~50KB)
- **No Leaks**: Memory stable over 1000 turns

### Throughput

- **Streaming**: Handle 100+ messages/sec
- **Tokens/sec**: Display output rate
- **Turn Latency**: Track and display per-turn time

## Implementation Roadmap

### Week 1: UI Foundation

- [ ] Add ui_mode parameter to AutoMode
- [ ] Create UIManager class with Rich layout
- [ ] Implement 5 panel structure
- [ ] Basic title generation (truncate prompt)
- **Tests to Pass**: TestAutoModeUIInitialization (10 tests)

### Week 2: Threading Infrastructure

- [ ] Add background thread for execution
- [ ] Implement thread-safe state (Locks)
- [ ] Add log queue (Queue)
- [ ] Implement pause/stop events (Event)
- **Tests to Pass**: TestAutoModeBackgroundThread, TestThreadSafeStateSharing (15 tests)

### Week 3: SDK Integration

- [ ] Async title generation via SDK
- [ ] Cost tracking from ResultMessage.usage
- [ ] Message streaming to log queue
- [ ] Error handling with retry
- **Tests to Pass**: TestTitleGenerationViaSDK, TestCostTrackingDisplay (20 tests)

### Week 4: User Interactions

- [ ] Keyboard input handling (x, p, k)
- [ ] Prompt input panel with submit
- [ ] Instruction file creation
- [ ] Todo list updates
- **Tests to Pass**: TestKeyboardCommands, TestPromptInputHandling (15 tests)

### Week 5: E2E Integration

- [ ] Complete startup workflow
- [ ] Live injection during execution
- [ ] Pause/resume functionality
- [ ] Exit to terminal mode
- **Tests to Pass**: TestFullUIWorkflow, TestPromptInjectionViaUI (20 tests)

### Week 6: Polish & Bug Fixes

- [ ] Fix remaining edge cases
- [ ] Performance optimization
- [ ] UI styling and colors
- [ ] Help overlay ('h' command)
- **Tests to Pass**: All remaining tests (~35 tests)

**Total**: ~115 tests to pass over 6 weeks

## Running the Tests

### All Tests

```bash
# Run all unit tests
pytest tests/unit/test_auto_mode_ui.py -v
pytest tests/unit/test_ui_threading.py -v
pytest tests/unit/test_ui_sdk_integration.py -v

# Run all integration tests
pytest tests/integration/test_auto_mode_ui_integration.py -v

# Run everything
pytest tests/unit/test_auto_mode_ui.py tests/unit/test_ui_threading.py tests/unit/test_ui_sdk_integration.py tests/integration/test_auto_mode_ui_integration.py -v
```

### By Phase

```bash
# Phase 1: UI Foundation
pytest tests/unit/test_auto_mode_ui.py::TestAutoModeUIInitialization -v
pytest tests/unit/test_auto_mode_ui.py::TestUITitleGeneration -v

# Phase 2: Threading
pytest tests/unit/test_ui_threading.py::TestAutoModeBackgroundThread -v
pytest tests/unit/test_ui_threading.py::TestThreadSafeStateSharing -v

# Phase 3: SDK Integration
pytest tests/unit/test_ui_sdk_integration.py::TestTitleGenerationViaSDK -v
pytest tests/unit/test_ui_sdk_integration.py::TestSDKStreamingToUI -v

# Phase 4: User Interactions
pytest tests/unit/test_auto_mode_ui.py::TestKeyboardCommands -v
pytest tests/unit/test_auto_mode_ui.py::TestPromptInputHandling -v

# Phase 5: E2E
pytest tests/integration/test_auto_mode_ui_integration.py::TestFullUIWorkflow -v
```

### With Coverage

```bash
pytest tests/unit/test_auto_mode_ui.py \
       tests/unit/test_ui_threading.py \
       tests/unit/test_ui_sdk_integration.py \
       tests/integration/test_auto_mode_ui_integration.py \
       --cov=amplihack.launcher.auto_mode \
       --cov-report=html \
       --cov-report=term-missing
```

## Expected Initial State

**All tests should FAIL** with AttributeError until implementation begins:

```
FAILED test_auto_mode_ui.py::TestAutoModeUIInitialization::test_ui_mode_creates_ui_instance
    AttributeError: 'AutoMode' object has no attribute 'ui_enabled'

FAILED test_ui_threading.py::TestAutoModeBackgroundThread::test_auto_mode_creates_background_thread
    AttributeError: 'AutoMode' object has no attribute 'start_background'

FAILED test_ui_sdk_integration.py::TestTitleGenerationViaSDK::test_title_generation_calls_claude_sdk
    AttributeError: 'NoneType' object has no attribute 'generate_title_async'

FAILED test_auto_mode_ui_integration.py::TestFullUIWorkflow::test_ui_starts_and_displays_initial_state
    AttributeError: 'AutoMode' object has no attribute 'start_ui'
```

This is **expected and correct** - tests drive implementation!

## Success Criteria

### Code Complete

- [ ] All 115+ tests passing
- [ ] Code coverage >85%
- [ ] No race conditions detected
- [ ] Memory usage stable

### Performance Targets Met

- [ ] UI renders at 30 FPS
- [ ] Input latency <100ms
- [ ] No blocking operations
- [ ] Graceful degradation on errors

### Quality Gates Passed

- [ ] Manual testing confirms usability
- [ ] No crashes on edge cases
- [ ] Clean shutdown on all paths
- [ ] Documentation complete

### User Acceptance

- [ ] UI is intuitive and responsive
- [ ] Commands work as expected
- [ ] Error messages are helpful
- [ ] Performance is acceptable

## Next Steps

1. **Start Implementation**: Begin with Phase 1 (UI Foundation)
2. **TDD Cycle**: Red (test fails) → Green (minimal code to pass) → Refactor
3. **Incremental Progress**: Pass tests in order, phase by phase
4. **Review & Iterate**: Code review after each phase
5. **Manual Testing**: Real usage testing throughout
6. **Performance Profiling**: Optimize hotspots as needed

## Documentation References

- **Main README**: tests/unit/README_AUTO_MODE_UI_TESTS.md
- **Test Files**:
  - tests/unit/test_auto_mode_ui.py
  - tests/unit/test_ui_threading.py
  - tests/unit/test_ui_sdk_integration.py
  - tests/integration/test_auto_mode_ui_integration.py
- **Existing Code**: src/amplihack/launcher/auto_mode.py

## Contact & Support

For questions about this test suite:

1. Read the detailed README in tests/unit/
2. Review test code for specifications
3. Check existing auto_mode.py for current implementation
4. Refer to Rich library docs for UI patterns

---

**Generated**: 2025-01-28
**Test Files**: 4
**Test Classes**: 27
**Test Cases**: 115+
**Lines of Test Code**: 1,280+
**Coverage Target**: >85%
**Implementation Time**: 6 weeks estimated
