# Terminal Enhancements - Quick Reference

## Import

```python
from amplihack.terminal import (
    # Title & Bell
    update_title,
    ring_bell,
    is_title_enabled,
    is_bell_enabled,
    is_rich_enabled,

    # Rich Formatting
    progress_spinner,
    create_progress_bar,
    format_success,
    format_error,
    format_warning,
    format_info,
)
```

## Basic Usage

### Update Terminal Title
```python
update_title("Amplihack - Session 20251102_143022")
```

### Ring Bell
```python
ring_bell()  # Beep!
```

### Progress Spinner
```python
with progress_spinner("Analyzing files..."):
    analyze_codebase()
```

### Progress Bar
```python
with create_progress_bar(100, "Processing files") as progress:
    task_id = progress.add_task("Processing", total=100)
    for i in range(100):
        process_item(i)
        progress.update(task_id, advance=1)
```

### Status Messages
```python
format_success("Operation completed")  # Green ✓
format_error("Operation failed")       # Red ✗
format_warning("Deprecation notice")   # Yellow ⚠
format_info("Starting analysis...")    # Blue ℹ
```

## Configuration

```bash
# Enable/disable features (default: true)
export AMPLIHACK_TERMINAL_TITLE=true
export AMPLIHACK_TERMINAL_BELL=true
export AMPLIHACK_TERMINAL_RICH=true
```

## Complete Workflow Example

```python
from amplihack.terminal import (
    update_title,
    progress_spinner,
    format_info,
    format_success,
    ring_bell,
)

# Start
session_id = "20251102_143022"
update_title(f"Amplihack - Session {session_id}")
format_info("Session started")

# Work
update_title(f"Amplihack - Analysis - {session_id}")
with progress_spinner("Analyzing files..."):
    results = analyze_codebase()
format_success(f"Found {len(results)} files")

# Complete
update_title(f"Amplihack - Complete - {session_id}")
format_success("Analysis complete")
ring_bell()
```

## Testing

```bash
# Run all tests
pytest src/amplihack/terminal/tests/

# Run verification script (no pytest needed)
python3 verify_terminal.py
```

## File Locations

```
src/amplihack/terminal/
├── __init__.py              # Import from here
├── enhancements.py          # Title & bell implementation
├── rich_output.py           # Rich formatting implementation
├── README.md                # Full documentation
└── tests/
    ├── test_enhancements.py # 27 tests
    ├── test_rich_output.py  # 22 tests
    ├── test_integration.py  # 6 tests
    └── test_e2e.py          # 6 tests
```

## Performance

- Title update: ~0.1ms
- Bell notification: ~0.1ms
- Format functions: ~1-2ms
- All operations < 10ms ✓

## Platform Support

- **Linux**: Full support ✓
- **macOS**: Full support ✓
- **Windows**: Full support ✓
- **Non-TTY**: Graceful degradation ✓
