# Smart PROJECT.md Initializer

**Issue #1280 Implementation**

## Overview

Intelligent PROJECT.md initialization system that automatically detects file state and generates appropriate content on session start.

## Architecture

### Module: `project_initializer.py`

Standalone module with three key responsibilities:

1. **Detection** - Identifies PROJECT.md state (missing, describes amplihack, or has user content)
2. **Generation** - Creates contextual content using Claude SDK with template fallback
3. **Integration** - Hooks into session_start.py for automatic initialization

### State Detection

Three states implemented via `ProjectState` enum:

- **MISSING**: File doesn't exist or is unreadable
- **DESCRIBES_AMPLIHACK**: Contains amplihack self-description or uncustomized template
- **VALID_USER_CONTENT**: User has customized with real project information

Detection logic checks for:
- Amplihack-specific keywords ("Agentic Coding Framework", "Agent-Powered Development")
- Template placeholders ("[Your Project Name]", "[Brief description]")
- Content length and quality

### Content Generation

**Two-tier approach with graceful degradation:**

1. **Claude SDK (Optimal)**:
   - Uses anthropic SDK to generate contextual content
   - Analyzes project structure (pyproject.toml, package.json, etc.)
   - Creates project-specific descriptions
   - Automatically falls back on any error

2. **Template Fallback (Reliable)**:
   - Uses PR #1278 template as fallback
   - Always works, requires no external dependencies
   - Provides clear structure for user customization

### Session Integration

Integrated into `.claude/tools/amplihack/hooks/session_start.py`:

- Runs automatically on every session start
- Checks if initialization is needed
- Logs actions and tracks metrics
- Never overwrites valid user content
- Creates backups before replacing files

## Key Features

### Ruthless Simplicity

- Zero dependencies (anthropic SDK optional)
- Direct file operations (no complex frameworks)
- Single-purpose class with clear methods
- Graceful error handling throughout

### Safety First

- **Never overwrites user content** - Detects and preserves customized files
- **Creates backups** - Saves .md.backup before replacing
- **Idempotent** - Multiple calls safely handled
- **Error resilient** - Returns status, never crashes

### Intelligent Behavior

- **Context-aware** - Detects project type from structure
- **Automatic fallback** - SDK failure doesn't block initialization
- **State tracking** - Only initializes when needed
- **Metrics logging** - Tracks success/failure for monitoring

## API

### ProjectInitializer Class

```python
from amplihack.utils.project_initializer import ProjectInitializer

# Create initializer
initializer = ProjectInitializer(project_root=Path.cwd())

# Check if initialization needed
if initializer.should_initialize():
    # Initialize with SDK generation
    success = initializer.initialize(use_sdk=True)

# Or force reinitialization
success = initializer.initialize(force=True)

# Check current state
state, reason = initializer.detect_state()
```

### Key Methods

**`detect_state() -> Tuple[ProjectState, str]`**
- Returns current state and human-readable reason
- No side effects, safe to call repeatedly

**`should_initialize() -> bool`**
- Returns True if initialization needed
- Convenience method wrapping detect_state()

**`initialize(force=False, use_sdk=True) -> bool`**
- Performs initialization if needed
- Returns True on success, False on failure
- Creates backups and tracks metrics

**`generate_content(use_sdk=True) -> Tuple[str, str]`**
- Generates content via SDK or template
- Returns (content, method) tuple
- Gracefully degrades on errors

## Testing

### Comprehensive Test Coverage (42 tests)

**Unit Tests (27 tests)** - `tests/unit/test_project_initializer.py`

1. **State Detection (6 tests)**
   - Missing file detection
   - Amplihack description detection
   - Template detection
   - Valid user content detection
   - Empty file handling
   - Unreadable file handling

2. **Content Generation (5 tests)**
   - Template fallback generation
   - SDK generation success
   - SDK fallback on missing API key
   - SDK fallback on import error
   - SDK fallback on API error

3. **Project Context (4 tests)**
   - Python project detection
   - JavaScript project detection
   - Multiple indicators detection
   - No indicators handling

4. **Initialization (8 tests)**
   - Initialize missing file
   - Initialize amplihack description
   - Create backup
   - Skip valid content
   - Force overwrite
   - should_initialize logic
   - Directory structure creation
   - Error handling

5. **Edge Cases (4 tests)**
   - Custom project root
   - Default project root (cwd)
   - Concurrent initialization
   - Symlink handling

**Integration Tests (15 tests)** - `tests/integration/test_project_initializer_integration.py`

1. **Session Start Integration (4 tests)**
   - Initializes missing PROJECT.md
   - Skips valid PROJECT.md
   - Replaces amplihack description
   - Handles errors gracefully

2. **End-to-End Flow (4 tests)**
   - Fresh project initialization
   - Amplihack installation migration
   - User content preservation
   - SDK generation with context

3. **Real World Scenarios (4 tests)**
   - Multiple session starts (idempotent)
   - Parallel session starts (safe)
   - Corrupted file replacement
   - Migration from old versions

4. **Metrics and Logging (3 tests)**
   - Successful initialization tracking
   - Skipped initialization tracking
   - Failed initialization tracking

### Running Tests

```bash
# Unit tests only
PYTHONPATH=src:$PYTHONPATH pytest tests/unit/test_project_initializer.py -v

# Integration tests only
PYTHONPATH=src:$PYTHONPATH pytest tests/integration/test_project_initializer_integration.py -v

# All tests
PYTHONPATH=src:$PYTHONPATH pytest tests/unit/test_project_initializer.py tests/integration/test_project_initializer_integration.py -v
```

All 42 tests pass successfully.

## Implementation Philosophy

### Zero-BS Implementation

- No stub methods or placeholders
- No TODO comments
- Every function works or doesn't exist
- Direct, simple implementations

### Modular Design

- Self-contained module with clear boundaries
- Public interface via class methods
- Internal utilities kept private
- Can be regenerated from this spec

### Graceful Degradation

- SDK failure → Template fallback
- Missing API key → Template fallback
- Import error → Template fallback
- Write error → Returns False, doesn't crash

## Files Created

```
src/amplihack/utils/
├── project_initializer.py           # Main implementation (360 lines)
└── README_PROJECT_INITIALIZER.md    # This file

tests/unit/
└── test_project_initializer.py      # Unit tests (500 lines)

tests/integration/
└── test_project_initializer_integration.py  # Integration tests (540 lines)

.claude/tools/amplihack/hooks/
└── session_start.py                 # Modified for integration
```

## Usage Example

### Automatic (Session Start)

PROJECT.md is automatically initialized on session start if:
- File is missing
- File describes amplihack framework
- File contains uncustomized template

User-customized files are never touched.

### Manual

```python
from pathlib import Path
from amplihack.utils.project_initializer import ProjectInitializer

# Create initializer
init = ProjectInitializer(Path("/path/to/project"))

# Check state
state, reason = init.detect_state()
print(f"State: {state.value} - {reason}")

# Initialize if needed
if init.should_initialize():
    success = init.initialize(use_sdk=True)
    if success:
        print("✓ PROJECT.md initialized")
    else:
        print("✗ Initialization failed")
else:
    print("✓ PROJECT.md already configured")
```

## Design Decisions

### Why Enum for States?

Clear, type-safe state representation with explicit values. Better than strings or booleans.

### Why Template Fallback?

Ensures reliable operation even without API key or SDK. Zero external dependencies for basic functionality.

### Why Backup Before Replace?

Safety first - preserves user data even if detection logic has edge cases.

### Why Session Hook Integration?

Automatic initialization provides best UX - users never see incorrect PROJECT.md content.

### Why Not Async?

File operations are fast, synchronous code is simpler, no need for async complexity.

## Future Enhancements

Potential improvements (not implemented in MVP):

1. **Interactive Mode** - Ask user questions to generate better content
2. **Multi-language Support** - Detect and use project language for descriptions
3. **Git Integration** - Use commit history to understand project evolution
4. **Custom Templates** - Allow users to define their own templates
5. **Diff Preview** - Show what will change before replacing

These are deliberately excluded to maintain ruthless simplicity.

## Related

- **Issue #1280**: Smart PROJECT.md initialization
- **PR #1278**: PROJECT.md template
- **Issue #1277**: UVX deployment context confusion

## Metrics

- **Lines of Code**: ~360 (implementation) + ~1040 (tests)
- **Test Coverage**: 42 tests (27 unit + 15 integration)
- **Dependencies**: 0 required, 1 optional (anthropic SDK)
- **Integration Points**: 1 (session_start.py hook)

---

**Implementation Complete** ✓
All requirements satisfied with ruthless simplicity and comprehensive testing.
