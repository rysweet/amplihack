# Quick Start Guide: Auto Mode UI Testing

## TL;DR

This is a comprehensive TDD test suite for the Auto Mode Interactive UI feature. **All tests currently FAIL** - this is intentional and correct. The tests serve as specifications for implementation.

## Files Location

```
tests/
├── unit/
│   ├── test_auto_mode_ui.py           # UI components (40+ tests)
│   ├── test_ui_threading.py           # Threading/concurrency (25+ tests)
│   ├── test_ui_sdk_integration.py     # Claude SDK integration (30+ tests)
│   └── README_AUTO_MODE_UI_TESTS.md   # Detailed documentation
├── integration/
│   └── test_auto_mode_ui_integration.py  # E2E workflows (20+ tests)
└── AUTO_MODE_UI_TEST_SUITE_SUMMARY.md    # Executive summary
```

**Total**: 115+ test cases across 4 files

## Quick Test Commands

### Run One Test (Verify Setup)
```bash
pytest tests/unit/test_auto_mode_ui.py::TestAutoModeUIInitialization::test_ui_mode_creates_ui_instance -v
```
**Expected**: FAIL with AttributeError (this is correct!)

### Run by Phase

```bash
# Phase 1: UI Foundation
pytest tests/unit/test_auto_mode_ui.py::TestAutoModeUIInitialization -v

# Phase 2: Threading
pytest tests/unit/test_ui_threading.py::TestAutoModeBackgroundThread -v

# Phase 3: SDK Integration
pytest tests/unit/test_ui_sdk_integration.py::TestTitleGenerationViaSDK -v

# Phase 4: User Interactions
pytest tests/unit/test_auto_mode_ui.py::TestKeyboardCommands -v

# Phase 5: E2E Workflows
pytest tests/integration/test_auto_mode_ui_integration.py::TestFullUIWorkflow -v
```

### Run All Tests
```bash
pytest tests/unit/test_auto_mode_ui.py \
       tests/unit/test_ui_threading.py \
       tests/unit/test_ui_sdk_integration.py \
       tests/integration/test_auto_mode_ui_integration.py -v
```

### With Coverage Report
```bash
pytest tests/unit/test_auto_mode_ui.py \
       tests/unit/test_ui_threading.py \
       tests/unit/test_ui_sdk_integration.py \
       tests/integration/test_auto_mode_ui_integration.py \
       --cov=amplihack.launcher.auto_mode \
       --cov-report=html \
       --cov-report=term-missing
```

## What's Tested

### 5 UI Areas
1. **Title Panel**: Generated from prompt via Claude SDK (max 50 chars)
2. **Session Details**: Turn counter, elapsed time, cost tracking
3. **Todo List**: Status indicators, current task highlighting
4. **Log Area**: Streaming output with timestamps, 1000 line buffer
5. **Prompt Input**: Multiline support, instruction injection

### 3 Keyboard Commands
- **'x'**: Exit UI, continue auto mode in background
- **'p'**: Pause/resume execution toggle
- **'k'**: Kill auto mode completely

### Thread-Based Execution
- **Background Thread**: Auto mode execution
- **Main Thread**: UI rendering and input
- **Thread-Safe**: Locks, Events, Queue for communication
- **Graceful Shutdown**: No deadlocks, clean resource cleanup

### Claude SDK Integration
- **Title Generation**: async query() call with fallback
- **Cost Tracking**: Token counts (input/output), estimated cost
- **Message Streaming**: AssistantMessage, ToolUseMessage, ResultMessage
- **Error Handling**: Connection errors, rate limits, timeouts, retries

## Implementation Order

### Week 1: UI Foundation (10 tests)
Add `ui_mode` parameter, create UIManager class, implement Rich layout

### Week 2: Threading (15 tests)
Background thread, thread-safe state, log queue, pause/stop events

### Week 3: SDK Integration (20 tests)
Async title generation, cost tracking, message streaming, error handling

### Week 4: User Interactions (15 tests)
Keyboard commands, prompt input, instruction injection, todo updates

### Week 5: E2E Workflows (20 tests)
Complete flows: startup, injection, pause/resume, exit

### Week 6: Polish (35 tests)
Edge cases, error recovery, performance, help overlay

## Test Structure (Testing Pyramid)

```
60% Unit Tests (60-70 tests)
    - Individual component isolation
    - Edge cases and boundaries
    - Error conditions

30% Integration Tests (30-35 tests)
    - Component interaction
    - SDK integration
    - Thread communication

10% E2E Tests (15-20 tests)
    - Complete user workflows
    - Real interaction patterns
    - Error recovery
```

## Key Design Decisions

### Threading Model
- **Main Thread**: UI rendering (Rich library)
- **Background Thread**: Auto mode execution
- **Communication**: Queue for logs, Events for signals, Locks for state

### State Management
- **AutoMode owns state**: Turn counter, todos, cost
- **UI queries state**: Thread-safe read methods
- **Updates via queue**: Logs pushed asynchronously

### Instruction Injection
- **File-based**: UI writes to `append/TIMESTAMP.md`
- **Polling**: AutoMode checks before each turn
- **Thread-safe**: File operations atomic

### Error Handling
- **Isolated threads**: UI crash doesn't kill AutoMode
- **Graceful degradation**: Fall back to terminal
- **Retry logic**: Exponential backoff on SDK errors

## Common First Steps

### 1. Add ui_mode Parameter
```python
class AutoMode:
    def __init__(self, sdk, prompt, max_turns=10, working_dir=None, ui_mode=False):
        self.sdk = sdk
        self.prompt = prompt
        self.max_turns = max_turns
        self.ui_enabled = ui_mode  # New
        self.ui = None  # New

        if self.ui_enabled:
            self.ui = UIManager(self)  # Create UI
```

**Passes**: `test_ui_mode_creates_ui_instance`

### 2. Create UIManager Class
```python
from rich.layout import Layout
from rich.live import Live

class UIManager:
    def __init__(self, auto_mode):
        self.auto_mode = auto_mode
        self.layout = Layout()

        # Create 5 panels
        self.title_panel = Panel("Title")
        self.session_panel = Panel("Session")
        self.todo_panel = Panel("Todos")
        self.log_panel = Panel("Logs")
        self.input_panel = Panel("Input")

        # Configure layout
        self.layout.split(
            Layout(name="title", size=3),
            Layout(name="session", size=5),
            Layout(name="todos", size=10),
            Layout(name="logs"),
            Layout(name="input", size=3)
        )
```

**Passes**: `test_ui_has_required_components`

### 3. Add Thread-Safe State
```python
import threading
from queue import Queue

class AutoMode:
    def __init__(self, ...):
        # ... existing code ...

        # Thread-safe state
        self._turn_lock = threading.Lock()
        self._todos_lock = threading.Lock()
        self._cost_lock = threading.Lock()
        self.log_queue = Queue(maxsize=500)

        # Events for signals
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()

    def get_current_turn(self):
        with self._turn_lock:
            return self.turn

    def queue_log(self, message):
        try:
            self.log_queue.put_nowait(message)
        except:
            pass  # Drop if queue full
```

**Passes**: `test_turn_counter_is_thread_safe`, `test_log_queue_is_thread_safe`

## Troubleshooting

### Tests won't run
```bash
# Install pytest if needed
pip install pytest pytest-asyncio

# Or use uv
uv pip install pytest pytest-asyncio
```

### Tests hang
- Check for missing `timeout` on `Thread.join()` and `Queue.get()`
- Should have `join(timeout=5)` and `get(timeout=1)`

### AttributeError on mocked SDK
```python
# Correct: Patch at import location
with patch('amplihack.launcher.auto_mode.query', ...):

# Wrong: Patch at original location
with patch('claude_agent_sdk.query', ...):
```

### Race conditions in tests
```python
# Add small sleep to let threads synchronize
auto_mode.start_background()
time.sleep(0.1)  # Let thread start
assert auto_mode.execution_thread.is_alive()
```

## Documentation

### Detailed Docs
- **tests/unit/README_AUTO_MODE_UI_TESTS.md**: Complete test documentation
- **tests/AUTO_MODE_UI_TEST_SUITE_SUMMARY.md**: Executive summary

### Test Files
- **test_auto_mode_ui.py**: UI component specs (380 lines)
- **test_ui_threading.py**: Threading specs (300 lines)
- **test_ui_sdk_integration.py**: SDK integration specs (280 lines)
- **test_auto_mode_ui_integration.py**: E2E workflow specs (320 lines)

### External References
- Rich Library: https://rich.readthedocs.io/
- Python Threading: https://docs.python.org/3/library/threading.html
- Testing Pyramid: https://martinfowler.com/bliki/TestPyramid.html

## Expected Test Results

### Before Implementation (Current State)
```
FAILED test_auto_mode_ui.py::test_ui_mode_creates_ui_instance - AttributeError
FAILED test_ui_threading.py::test_auto_mode_creates_background_thread - AttributeError
FAILED test_ui_sdk_integration.py::test_title_generation_calls_claude_sdk - AttributeError
```
**This is correct!** Tests are specifications.

### After Phase 1 (UI Foundation)
```
PASSED test_auto_mode_ui.py::TestAutoModeUIInitialization (10 tests)
FAILED test_ui_threading.py::TestAutoModeBackgroundThread - Not implemented yet
```

### After All Phases (Complete)
```
PASSED tests/unit/test_auto_mode_ui.py (40 tests)
PASSED tests/unit/test_ui_threading.py (25 tests)
PASSED tests/unit/test_ui_sdk_integration.py (30 tests)
PASSED tests/integration/test_auto_mode_ui_integration.py (20 tests)

Total: 115 tests passed
Coverage: 87%
```

## Next Actions

1. **Read Full Docs**: tests/unit/README_AUTO_MODE_UI_TESTS.md
2. **Run One Test**: Verify pytest works and test fails correctly
3. **Start Phase 1**: Implement UI foundation (Week 1)
4. **TDD Cycle**: Red → Green → Refactor
5. **Progress Through Phases**: Week-by-week implementation

## Questions?

1. Check test docstrings for expected behavior
2. Review README_AUTO_MODE_UI_TESTS.md for details
3. Look at existing auto_mode.py for current structure
4. See Rich library docs for UI patterns

---

**Status**: Tests ready for implementation
**Test Count**: 115+ comprehensive test cases
**Coverage Target**: >85%
**Estimated Time**: 6 weeks
