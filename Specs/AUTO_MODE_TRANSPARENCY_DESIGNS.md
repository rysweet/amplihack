# Auto Mode Transparency - Implementation Designs

## Executive Summary

This document presents three distinct architectural approaches to improve transparency in auto mode execution. Each approach has different complexity levels, implementation timelines, and user value propositions. All three can be implemented in parallel branches and evaluated independently.

**Design Philosophy Alignment:**
- Ruthless simplicity: Start with minimal approach
- Modular design: Each approach is a self-contained brick
- Zero-BS implementation: All features must work completely
- Regeneratable: Clear specs enable AI implementation

---

## Approach 1: Minimal Progress Indicators

**Branch:** `feat/auto-transparency-minimal`

**Philosophy:** The simplest thing that could work. Add basic progress visibility without changing architecture.

### 1.1 Technical Architecture

#### Core Component: ProgressTracker

```python
class ProgressTracker:
    """Minimal progress tracking for auto mode execution.

    Responsibility: Track and display execution progress
    Dependencies: None (pure Python)
    """

    def __init__(self, max_turns: int):
        self.max_turns = max_turns
        self.current_turn = 0
        self.start_time = time.time()
        self.phase = "initializing"

    def update(self, turn: int, phase: str):
        """Update current state and display progress."""
        self.current_turn = turn
        self.phase = phase
        self._display_progress()

    def _display_progress(self):
        """Display progress indicator."""
        elapsed = time.time() - self.start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        # Format: [Turn 2/10 | Executing | 1m 23s]
        indicator = f"[Turn {self.current_turn}/{self.max_turns} | {self.phase.title()} | {mins}m {secs}s]"
        print(f"\n{indicator}", flush=True)
```

#### Integration Points

**File:** `/src/amplihack/launcher/auto_mode.py`

**Modifications:**

1. Add ProgressTracker initialization in `AutoMode.__init__()`:
   ```python
   self.progress = ProgressTracker(max_turns)
   ```

2. Update progress at each turn:
   ```python
   # Line 291: Before Turn 1
   self.progress.update(1, "clarifying objective")

   # Line 310: Before Turn 2
   self.progress.update(2, "creating plan")

   # Line 344: In execute loop
   self.progress.update(turn, "executing")

   # Line 372: During evaluation
   self.progress.update(turn, "evaluating")
   ```

3. Add final progress display:
   ```python
   # Line 409: After completion
   self.progress.update(self.turn, "complete")
   ```

#### Data Flow

```
AutoMode.run()
  ├─> ProgressTracker.update(turn, phase)
  │   └─> _display_progress() → stdout
  │
  ├─> run_sdk(prompt)
  │   └─> [existing SDK/subprocess logic]
  │
  └─> log() → [existing logging]
```

### 1.2 Implementation Complexity

**Lines of Code:** ~60 LOC
- ProgressTracker class: 40 LOC
- Integration points: 20 LOC

**Time Estimate:** 2-3 hours
- Implementation: 1 hour
- Testing: 1 hour
- Documentation: 30 min

**Files Modified:**
1. `/src/amplihack/launcher/auto_mode.py` (5 insertions)

**Files Created:**
1. None (inline in auto_mode.py)

### 1.3 User Experience

**Before:**
```
[AUTO CLAUDE] Starting auto mode (max 10 turns)
[AUTO CLAUDE] Prompt: Add authentication to the API

--- TURN 1: Clarify Objective ---
[AUTO CLAUDE] Using Claude SDK (streaming mode)
[Claude starts outputting text...]
```

**After:**
```
[AUTO CLAUDE] Starting auto mode (max 10 turns)
[AUTO CLAUDE] Prompt: Add authentication to the API

[Turn 1/10 | Clarifying Objective | 0m 0s]

--- TURN 1: Clarify Objective ---
[AUTO CLAUDE] Using Claude SDK (streaming mode)
[Claude starts outputting text...]

[Turn 2/10 | Creating Plan | 1m 23s]

--- TURN 2: Create Plan ---
...
```

**User Benefits:**
- Always know current turn number
- See elapsed time at a glance
- Understand current phase (clarifying/planning/executing/evaluating)
- No guessing about progress

### 1.4 Philosophy Compliance

**Ruthless Simplicity:** ✓ EXCELLENT
- Minimal code addition (~60 LOC)
- No new dependencies
- No architectural changes
- Pure display logic

**Modular Design:** ✓ GOOD
- ProgressTracker is self-contained
- Clear single responsibility
- Could extract to separate file if needed
- No impact on existing modules

**Zero-BS Implementation:** ✓ EXCELLENT
- No stubs or placeholders
- Complete feature from day one
- No half-implemented functionality
- Works immediately

**Regeneratable:** ✓ EXCELLENT
- Clear specification
- Minimal surface area
- Easy to rebuild from scratch
- No hidden complexity

### 1.5 Trade-offs

**Benefits:**
- Extremely low risk (minimal code changes)
- Fast implementation (<1 day)
- Immediate user value
- No performance overhead
- Easy to test and validate
- Foundation for more complex approaches

**Costs:**
- Limited information (no substep visibility)
- No machine-readable output
- No agent transparency
- No subprocess progress indication
- Static display (no live updates during long operations)

**When to Choose:**
- Need quick wins
- Risk-averse environment
- Testing transparency concept
- Foundation for future enhancements

---

## Approach 2: Structured Event System

**Branch:** `feat/auto-transparency-events`

**Philosophy:** Event-driven architecture enables machine-readable progress and extensibility.

### 2.1 Technical Architecture

#### Core Components

**Component 1: EventEmitter**

```python
class AutoModeEvent:
    """Base class for auto mode events.

    Contract: All events must have type, timestamp, and data
    """
    def __init__(self, event_type: str, data: dict):
        self.type = event_type
        self.timestamp = time.time()
        self.data = data

    def to_json(self) -> str:
        """Serialize to JSON for machine parsing."""
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp,
            "data": self.data
        })


class EventEmitter:
    """Event emission system for auto mode.

    Responsibility: Emit and route events to registered handlers
    Dependencies: None
    """
    def __init__(self):
        self.handlers: List[Callable[[AutoModeEvent], None]] = []

    def register_handler(self, handler: Callable[[AutoModeEvent], None]):
        """Register event handler."""
        self.handlers.append(handler)

    def emit(self, event_type: str, data: dict):
        """Emit event to all handlers."""
        event = AutoModeEvent(event_type, data)
        for handler in self.handlers:
            try:
                handler(event)
            except Exception as e:
                # Don't let handler failures break execution
                print(f"[WARN] Event handler failed: {e}", file=sys.stderr)
```

**Component 2: ProgressHandler**

```python
class ProgressHandler:
    """Display progress updates from events.

    Responsibility: Convert events to human-readable progress display
    Dependencies: EventEmitter
    """
    def __init__(self, max_turns: int):
        self.max_turns = max_turns
        self.start_time = time.time()

    def handle_event(self, event: AutoModeEvent):
        """Handle auto mode events."""
        if event.type == "turn_start":
            self._display_turn_start(event.data)
        elif event.type == "phase_change":
            self._display_phase_change(event.data)
        elif event.type == "agent_start":
            self._display_agent_start(event.data)
        elif event.type == "agent_complete":
            self._display_agent_complete(event.data)

    def _display_turn_start(self, data: dict):
        turn = data.get("turn", 0)
        phase = data.get("phase", "unknown")
        elapsed = time.time() - self.start_time
        print(f"\n[Turn {turn}/{self.max_turns} | {phase} | {elapsed:.1f}s]", flush=True)

    def _display_phase_change(self, data: dict):
        phase = data.get("phase", "unknown")
        print(f"  → {phase}", flush=True)

    def _display_agent_start(self, data: dict):
        agent = data.get("agent", "unknown")
        print(f"    • Running {agent}...", flush=True)

    def _display_agent_complete(self, data: dict):
        agent = data.get("agent", "unknown")
        duration = data.get("duration", 0)
        print(f"    ✓ {agent} complete ({duration:.1f}s)", flush=True)
```

**Component 3: JSONLHandler**

```python
class JSONLHandler:
    """Write events to JSONL file for machine consumption.

    Responsibility: Persist events in machine-readable format
    Dependencies: EventEmitter
    """
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.file_handle = None

    def __enter__(self):
        self.file_handle = open(self.output_path, "a")
        return self

    def __exit__(self, *args):
        if self.file_handle:
            self.file_handle.close()

    def handle_event(self, event: AutoModeEvent):
        """Write event to JSONL file."""
        if self.file_handle:
            self.file_handle.write(event.to_json() + "\n")
            self.file_handle.flush()
```

#### Integration Points

**File:** `/src/amplihack/launcher/auto_mode.py`

**Modifications:**

1. Initialize event system in `AutoMode.__init__()`:
   ```python
   # Create event emitter
   self.events = EventEmitter()

   # Register handlers
   progress_handler = ProgressHandler(max_turns)
   self.events.register_handler(progress_handler.handle_event)

   # Optional: JSONL logging
   jsonl_path = self.log_dir / "events.jsonl"
   jsonl_handler = JSONLHandler(jsonl_path)
   self.events.register_handler(jsonl_handler.handle_event)
   ```

2. Emit events throughout execution:
   ```python
   # Turn start
   self.events.emit("turn_start", {"turn": self.turn, "phase": "clarifying"})

   # Phase changes
   self.events.emit("phase_change", {"phase": "executing"})

   # Agent orchestration (requires prompt parsing)
   self.events.emit("agent_start", {"agent": "architect"})
   # ... SDK execution ...
   self.events.emit("agent_complete", {"agent": "architect", "duration": elapsed})
   ```

3. Emit completion events:
   ```python
   self.events.emit("session_complete", {
       "turns": self.turn,
       "duration": time.time() - start_time,
       "status": "success"
   })
   ```

#### Data Flow

```
AutoMode.run()
  ├─> events.emit("turn_start", data)
  │   ├─> ProgressHandler.handle_event() → stdout
  │   └─> JSONLHandler.handle_event() → events.jsonl
  │
  ├─> run_sdk(prompt)
  │   ├─> events.emit("agent_start", ...)
  │   ├─> [SDK execution]
  │   └─> events.emit("agent_complete", ...)
  │
  └─> events.emit("session_complete", ...)
```

### 2.2 Implementation Complexity

**Lines of Code:** ~250 LOC
- AutoModeEvent: 20 LOC
- EventEmitter: 40 LOC
- ProgressHandler: 80 LOC
- JSONLHandler: 40 LOC
- Integration in auto_mode.py: 70 LOC

**Time Estimate:** 1-2 days
- Implementation: 4-6 hours
- Testing: 2-3 hours
- Documentation: 1-2 hours

**Files Modified:**
1. `/src/amplihack/launcher/auto_mode.py` (~70 insertions)

**Files Created:**
1. `/src/amplihack/launcher/auto_events.py` (~180 LOC - event system)
2. `/tests/launcher/test_auto_events.py` (~150 LOC - event tests)

### 2.3 User Experience

**Terminal Output:**
```
[AUTO CLAUDE] Starting auto mode (max 10 turns)

[Turn 1/10 | clarifying | 0.0s]
  → Analyzing requirements
    • Running architect...
    ✓ architect complete (12.3s)
    • Running ambiguity...
    ✓ ambiguity complete (8.1s)

[Turn 2/10 | planning | 23.5s]
  → Creating execution plan
    • Running architect...
    ✓ architect complete (15.2s)
    • Running patterns...
    ✓ patterns complete (6.7s)

[Turn 3/10 | executing | 48.9s]
  → Building feature
    • Running builder...
    ✓ builder complete (45.1s)
    • Running tester...
    ✓ tester complete (18.3s)
```

**JSONL Output** (`.claude/runtime/logs/auto_*/events.jsonl`):
```jsonl
{"type":"turn_start","timestamp":1699564801.234,"data":{"turn":1,"phase":"clarifying"}}
{"type":"agent_start","timestamp":1699564801.456,"data":{"agent":"architect"}}
{"type":"agent_complete","timestamp":1699564813.789,"data":{"agent":"architect","duration":12.333}}
{"type":"turn_start","timestamp":1699564823.567,"data":{"turn":2,"phase":"planning"}}
{"type":"session_complete","timestamp":1699564901.234,"data":{"turns":5,"duration":100.0,"status":"success"}}
```

**Machine-Readable Benefits:**
- External tools can monitor progress
- Build dashboards and visualizations
- Track performance metrics
- Automate based on events
- Post-session analysis

### 2.4 Philosophy Compliance

**Ruthless Simplicity:** ✓ GOOD
- More code than minimal approach (~250 LOC)
- Event pattern is well-understood
- No complex dependencies
- Clear separation of concerns
- Can start simple and grow

**Modular Design:** ✓ EXCELLENT
- Perfect brick pattern
- EventEmitter is completely self-contained
- Handlers are pluggable
- Can add/remove handlers without changing core
- Clear contracts between components

**Zero-BS Implementation:** ✓ EXCELLENT
- All features complete
- No half-implemented handlers
- Full JSONL support from day one
- Comprehensive event types
- Production-ready

**Regeneratable:** ✓ EXCELLENT
- Clear specifications for each component
- Well-defined interfaces
- Easy to rebuild from scratch
- Standard event-driven pattern

### 2.5 Trade-offs

**Benefits:**
- Machine-readable progress (JSONL)
- Extensible architecture (add handlers easily)
- Agent visibility (when orchestration detected)
- Foundation for dashboards/monitoring
- No breaking changes to existing API
- Separation of concerns (display vs logic)
- Multiple output formats simultaneously

**Costs:**
- More code to maintain (~250 LOC)
- Slightly more complex architecture
- Requires agent detection in prompts (heuristic)
- Event overhead (minimal but present)
- More testing surface area

**When to Choose:**
- Need machine-readable output
- Building monitoring/dashboard tools
- Want extensibility for future handlers
- Value separation of concerns
- Planning to add more transparency features later

---

## Approach 3: Rich TUI Integration

**Branch:** `feat/auto-transparency-tui`

**Philosophy:** Terminal UI provides maximum visual feedback and live updates.

### 3.1 Technical Architecture

#### Core Components

**Component 1: TUIManager**

```python
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table


class TUIManager:
    """Rich terminal UI for auto mode.

    Responsibility: Manage split-screen TUI with progress and logs
    Dependencies: rich (external library)
    """
    def __init__(self, max_turns: int):
        self.max_turns = max_turns
        self.console = Console()
        self.layout = Layout()

        # Progress tracking
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
        )
        self.turn_task = self.progress.add_task("Initializing...", total=max_turns)

        # Log buffer
        self.log_lines: List[str] = []
        self.max_log_lines = 20

        # Setup layout
        self._setup_layout()

    def _setup_layout(self):
        """Create split-screen layout."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        self.layout["body"].split_row(
            Layout(name="progress", ratio=1),
            Layout(name="logs", ratio=2),
        )

    def update_turn(self, turn: int, phase: str):
        """Update turn progress."""
        self.progress.update(
            self.turn_task,
            completed=turn,
            description=f"Turn {turn}/{self.max_turns}: {phase}",
        )

    def add_log(self, message: str):
        """Add log message to display."""
        self.log_lines.append(message)
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines.pop(0)

    def render(self) -> Layout:
        """Render current TUI state."""
        # Header
        self.layout["header"].update(
            Panel("Auto Mode - Agentic Execution", style="bold blue")
        )

        # Progress panel
        self.layout["progress"].update(
            Panel(self.progress, title="Progress", border_style="green")
        )

        # Logs panel
        log_text = "\n".join(self.log_lines[-self.max_log_lines:])
        self.layout["logs"].update(
            Panel(log_text, title="Recent Activity", border_style="yellow")
        )

        # Footer
        self.layout["footer"].update(
            Panel("Press Ctrl+C to stop", style="dim")
        )

        return self.layout
```

**Component 2: LiveTUIContext**

```python
class LiveTUIContext:
    """Context manager for live TUI updates.

    Responsibility: Manage live display lifecycle
    Dependencies: TUIManager
    """
    def __init__(self, tui_manager: TUIManager):
        self.tui = tui_manager
        self.live = None

    def __enter__(self):
        self.live = Live(
            self.tui.render(),
            console=self.tui.console,
            refresh_per_second=4,
        )
        self.live.__enter__()
        return self.tui

    def __exit__(self, *args):
        if self.live:
            self.live.__exit__(*args)

    def refresh(self):
        """Refresh display."""
        if self.live:
            self.live.update(self.tui.render())
```

**Component 3: TUIOutputStream**

```python
class TUIOutputStream:
    """Stream wrapper that routes output to TUI.

    Responsibility: Capture stdout/stderr and route to TUI logs
    Dependencies: TUIManager
    """
    def __init__(self, tui_manager: TUIManager, original_stream):
        self.tui = tui_manager
        self.original = original_stream
        self.buffer = []

    def write(self, text: str):
        """Write text to TUI logs."""
        if text.strip():
            self.tui.add_log(text.strip())
        self.original.write(text)

    def flush(self):
        """Flush buffer."""
        self.original.flush()
```

#### Integration Points

**File:** `/src/amplihack/launcher/auto_mode.py`

**Modifications:**

1. Add TUI mode flag and initialization:
   ```python
   def __init__(self, sdk: str, prompt: str, max_turns: int = 10,
                working_dir: Optional[Path] = None, use_tui: bool = True):
       # ... existing init ...
       self.use_tui = use_tui
       self.tui = TUIManager(max_turns) if use_tui else None
   ```

2. Wrap execution in TUI context:
   ```python
   def run(self) -> int:
       if self.use_tui:
           return self._run_with_tui()
       else:
           return self._run_standard()

   def _run_with_tui(self) -> int:
       """Run with rich TUI."""
       with LiveTUIContext(self.tui) as tui:
           # Redirect stdout/stderr to TUI
           old_stdout = sys.stdout
           old_stderr = sys.stderr
           try:
               sys.stdout = TUIOutputStream(tui, old_stdout)
               sys.stderr = TUIOutputStream(tui, old_stderr)
               return self._execute_turns(tui)
           finally:
               sys.stdout = old_stdout
               sys.stderr = old_stderr
   ```

3. Update progress throughout execution:
   ```python
   def _execute_turns(self, tui: Optional[TUIManager] = None):
       # Turn 1
       if tui:
           tui.update_turn(1, "Clarifying Objective")
           tui.add_log("Starting objective clarification...")
       # ... existing turn logic ...
   ```

#### Data Flow

```
AutoMode.run()
  ├─> LiveTUIContext.__enter__()
  │   └─> Live display starts
  │
  ├─> TUIOutputStream redirects stdout/stderr
  │   └─> All output → tui.add_log()
  │
  ├─> _execute_turns(tui)
  │   ├─> tui.update_turn() → Progress bar
  │   ├─> tui.add_log() → Log panel
  │   └─> tui.refresh() → Live update
  │
  └─> LiveTUIContext.__exit__()
      └─> Clean shutdown
```

### 3.2 Implementation Complexity

**Lines of Code:** ~400 LOC
- TUIManager: 150 LOC
- LiveTUIContext: 40 LOC
- TUIOutputStream: 50 LOC
- Integration in auto_mode.py: 120 LOC
- CLI flag handling: 40 LOC

**Time Estimate:** 2-3 days
- Implementation: 6-8 hours
- Testing: 3-4 hours
- Documentation: 2-3 hours

**Dependencies:**
- `rich` library (external dependency)
  - Well-maintained (10k+ stars)
  - Mature API (v13+)
  - No security concerns
  - Excellent documentation

**Files Modified:**
1. `/src/amplihack/launcher/auto_mode.py` (~120 insertions, major refactor)
2. `/src/amplihack/cli.py` (~20 insertions for --no-tui flag)
3. `pyproject.toml` or `requirements.txt` (add `rich` dependency)

**Files Created:**
1. `/src/amplihack/launcher/auto_tui.py` (~240 LOC - TUI components)
2. `/tests/launcher/test_auto_tui.py` (~200 LOC - TUI tests)

### 3.3 User Experience

**Terminal Display:**

```
┌─────────────────────────────────────────────────────────────┐
│ Auto Mode - Agentic Execution                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐ ┌────────────────────────────────────────┐
│ Progress        │ │ Recent Activity                        │
│                 │ │                                        │
│ ⠋ Turn 3/10:    │ │ [23:15:42] Starting architect agent   │
│ Executing       │ │ [23:15:45] Analyzing requirements     │
│ ████████░░░ 30% │ │ [23:15:48] Creating module spec       │
│ 2m 15s          │ │ [23:15:51] Architect complete         │
│                 │ │ [23:15:52] Starting builder agent     │
│                 │ │ [23:15:55] Generating code structure  │
│                 │ │ [23:15:58] Implementing features      │
│                 │ │ [23:16:01] Writing tests              │
│                 │ │ [23:16:04] Builder complete           │
│                 │ │ [23:16:05] Starting reviewer agent    │
│                 │ │ [23:16:08] Checking philosophy        │
│                 │ │ [23:16:11] Validating modularity      │
│                 │ │ [23:16:14] Reviewer complete          │
│                 │ │ [23:16:15] Turn 3 complete            │
│                 │ │                                        │
└─────────────────┘ └────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Press Ctrl+C to stop                                        │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Live progress bar with spinner
- Percentage complete
- Elapsed time
- Scrolling log panel (last 20 lines)
- Real-time updates (4fps)
- Clean layout with borders
- Color-coded panels

**CLI Integration:**
```bash
# Default: Use TUI
amplihack claude --auto -- -p "task"

# Disable TUI (use standard output)
amplihack claude --auto --no-tui -- -p "task"
```

### 3.4 Philosophy Compliance

**Ruthless Simplicity:** ⚠️ MODERATE
- Most code of all approaches (~400 LOC)
- External dependency (`rich`)
- More complex architecture
- BUT: `rich` is battle-tested and well-documented
- Can be disabled with --no-tui flag
- Complexity is isolated in auto_tui.py module

**Modular Design:** ✓ EXCELLENT
- TUI components in separate module
- Clean separation from core logic
- Can be completely removed without breaking auto mode
- Perfect brick: self-contained, clear contract
- Original functionality preserved with --no-tui

**Zero-BS Implementation:** ✓ EXCELLENT
- Full TUI from day one
- All panels working
- Live updates functional
- Proper cleanup on exit
- Graceful fallback if rich unavailable

**Regeneratable:** ✓ GOOD
- Clear specifications for each component
- Standard TUI patterns
- Well-documented rich library
- Could rebuild from scratch
- Slightly higher complexity to regenerate

### 3.5 Trade-offs

**Benefits:**
- Maximum visual feedback
- Live progress updates (not just snapshots)
- Professional appearance
- Split-screen information density
- Scrolling log history
- Time-elapsed display
- Spinner for "working" indication
- Best user experience of all approaches
- Can disable via --no-tui flag

**Costs:**
- External dependency (rich library)
- Most code to maintain (~400 LOC)
- Highest implementation time (2-3 days)
- More testing complexity
- Terminal compatibility concerns (Windows, old terminals)
- May conflict with subprocess output
- Requires output redirection
- More points of failure

**When to Choose:**
- User experience is priority
- Terminal-based workflow
- Professional presentation matters
- Have time for proper implementation
- Can accept external dependency
- Target modern terminals

---

## Comparison Matrix

| Dimension | Approach 1: Minimal | Approach 2: Events | Approach 3: TUI |
|-----------|---------------------|--------------------|--------------------|
| **Complexity** | ~60 LOC | ~250 LOC | ~400 LOC |
| **Implementation Time** | 2-3 hours | 1-2 days | 2-3 days |
| **External Dependencies** | None | None | rich |
| **Visual Impact** | Low | Medium | High |
| **Machine-Readable** | No | Yes (JSONL) | No |
| **Extensibility** | Low | High | Medium |
| **User Experience** | Basic | Good | Excellent |
| **Risk Level** | Very Low | Low | Medium |
| **Maintenance Burden** | Very Low | Low | Medium |
| **Philosophy Alignment** | Excellent | Excellent | Good |
| **Backward Compatible** | Yes | Yes | Yes (with flag) |

## Recommendation Strategy

### Sequential Implementation (Conservative)

1. **Start with Approach 1** (Minimal) - Week 1
   - Get quick win
   - Validate user value
   - Foundation for others

2. **Add Approach 2** (Events) - Week 2
   - Build on minimal approach
   - Add machine-readable output
   - Enable monitoring tools

3. **Consider Approach 3** (TUI) - Week 3
   - Only if user feedback demands it
   - Most complex, evaluate carefully
   - Can use events as data source

### Parallel Implementation (Aggressive)

1. **Three Branches Simultaneously**
   - Assign to different builders
   - Independent development
   - Compare results after 1 week

2. **User Testing**
   - Test all three with real users
   - Gather feedback on preferences
   - Measure value vs complexity

3. **Choose Winner(s)**
   - May merge 1+2 (minimal + events)
   - May choose only 1 (simplest)
   - May offer all three as modes

### Hybrid Approach (Recommended)

1. **Implement 1+2 in Single Branch**
   - Start with Approach 1 (minimal progress)
   - Add Approach 2 (event system) on top
   - Events emit to both progress display AND JSONL
   - Best of both worlds: ~300 LOC total

2. **Defer Approach 3**
   - Wait for user demand
   - External dependency needs justification
   - Can build on event system later

3. **Timeline**
   - Day 1: Approach 1 implementation
   - Day 2-3: Add event system
   - Day 4: Testing and documentation
   - Total: 4 days for 1+2 combined

## Integration Requirements Checklist

All three approaches must satisfy:

- [ ] No breaking changes to existing CLI
- [ ] No breaking changes to AutoMode API
- [ ] Works with both SDK and subprocess modes
- [ ] Preserves existing logging functionality
- [ ] Backward compatible (existing code continues to work)
- [ ] Doesn't slow down execution significantly (<5% overhead)
- [ ] Handles errors gracefully (transparency fails shouldn't crash auto mode)
- [ ] Documented in AUTO_MODE.md
- [ ] Unit tests for new components
- [ ] Integration tests with real auto mode execution

## Next Steps

**For Parallel Implementation:**

1. **Architect reviews this document**
   - Validate designs
   - Challenge complexity
   - Approve approaches

2. **Create three branches**
   ```bash
   git checkout -b feat/auto-transparency-minimal
   git checkout -b feat/auto-transparency-events
   git checkout -b feat/auto-transparency-tui
   ```

3. **Assign to builders**
   - Builder 1: Approach 1 (Minimal)
   - Builder 2: Approach 2 (Events)
   - Builder 3: Approach 3 (TUI)

4. **Implementation phase** (parallel)
   - Each builder follows their spec
   - Regular check-ins for blockers
   - Independent testing

5. **Review and decision**
   - Compare implementations
   - Test with real users
   - Choose approach(es) to merge

**For Sequential Implementation:**

1. Start with Approach 1 in main branch
2. Get user feedback
3. Decide on next steps based on value delivered

---

## Conclusion

All three approaches are viable and align with project philosophy to varying degrees. The recommendation is to implement Approach 1+2 as a hybrid (minimal + events) for maximum value with acceptable complexity, deferring Approach 3 unless user demand justifies the additional complexity and external dependency.

**Key Decision Factors:**
- **If time is limited:** Choose Approach 1
- **If need machine-readable output:** Choose Approach 2
- **If user experience is critical:** Choose Approach 3
- **If want best balance:** Implement Approach 1+2 together

The modular design ensures any approach can be added later without breaking existing functionality.
