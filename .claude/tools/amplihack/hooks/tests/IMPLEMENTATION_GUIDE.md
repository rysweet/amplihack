# Compaction Validator Implementation Guide

**Purpose:** Guide for implementing `compaction_validator.py` to pass all 34 TDD tests.

## Required Module Structure

Create `/home/azureuser/src/amplihack/worktrees/feat/issue-2069-power-steering-compaction-enhancements/.claude/tools/amplihack/hooks/compaction_validator.py`

## Required Classes and APIs

### 1. CompactionContext (Dataclass)

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CompactionContext:
    """Compaction event metadata and diagnostics."""

    # Required attributes (tests expect these)
    has_compaction_event: bool = False
    turn_at_compaction: int = 0
    messages_removed: int = 0
    pre_compaction_transcript: Optional[list[dict]] = None
    timestamp: Optional[str] = None
    is_stale: bool = False
    age_hours: float = 0.0
    has_security_violation: bool = False

    # Required method
    def get_diagnostic_summary(self) -> str:
        """Generate human-readable diagnostic summary.

        Must include:
        - Turn number where compaction occurred
        - Number of messages removed
        - Word "compaction" (case-insensitive)
        """
        pass
```

### 2. ValidationResult (Dataclass)

```python
@dataclass
class ValidationResult:
    """Result of compaction validation."""

    # Required attributes
    passed: bool
    warnings: list[str] = field(default_factory=list)
    recovery_steps: list[str] = field(default_factory=list)
    compaction_context: CompactionContext = field(default_factory=CompactionContext)
    used_fallback: bool = False

    # Required method
    def get_summary(self) -> str:
        """Generate human-readable validation summary."""
        pass
```

### 3. CompactionEvent (Dataclass)

```python
@dataclass
class CompactionEvent:
    """Single compaction event from compaction_events.json."""

    timestamp: str
    turn_number: int
    messages_removed: int
    pre_compaction_transcript_path: str
    session_id: str
```

### 4. CompactionValidator (Main Class)

```python
class CompactionValidator:
    """Validates conversation compaction and data preservation."""

    def __init__(self, project_root: Path):
        """Initialize validator with project root.

        Args:
            project_root: Project root directory path
        """
        self.project_root = project_root
        self.runtime_dir = project_root / ".claude" / "runtime" / "power-steering"

    def load_compaction_context(self, session_id: str) -> CompactionContext:
        """Load compaction context from runtime data.

        Must handle:
        1. Missing compaction_events.json file (fail-open)
        2. Corrupt JSON (fail-open)
        3. Missing pre-compaction transcript file (fail-open, but mark event)
        4. Path traversal attacks (set has_security_violation)
        5. Multiple events (return most recent by timestamp)
        6. Stale events (> 24 hours, set is_stale=True)

        Args:
            session_id: Session identifier to find events for

        Returns:
            CompactionContext with loaded data or safe defaults
        """
        pass

    def validate(
        self,
        transcript: Optional[list[dict]],
        session_id: str
    ) -> ValidationResult:
        """Validate entire transcript for compaction data loss.

        Must:
        1. Load compaction context for session
        2. If no compaction detected, return passed
        3. If compaction detected, validate critical data preservation
        4. Use provided transcript as fallback if pre-compaction unavailable
        5. Generate specific warnings and recovery steps

        Args:
            transcript: Current transcript (may be None)
            session_id: Session identifier

        Returns:
            ValidationResult with validation outcome
        """
        pass

    def validate_todos(
        self,
        pre_compaction: list[dict],
        post_compaction: list[dict]
    ) -> ValidationResult:
        """Validate TODO items preserved after compaction.

        Must detect:
        - TODOs present in pre-compaction but missing in post-compaction
        - Provide recovery step about recreating TODO list

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction

        Returns:
            ValidationResult indicating if TODOs preserved
        """
        pass

    def validate_objectives(
        self,
        pre_compaction: list[dict],
        post_compaction: list[dict]
    ) -> ValidationResult:
        """Validate session objectives still clear after compaction.

        Must detect:
        - Original user goal unclear in post-compaction transcript
        - Provide recovery step about restating objective

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction

        Returns:
            ValidationResult indicating if objectives clear
        """
        pass

    def validate_recent_context(
        self,
        pre_compaction: list[dict],
        post_compaction: list[dict],
        context: CompactionContext
    ) -> ValidationResult:
        """Validate recent context (last 10 turns) preserved.

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction
            context: Compaction context with metadata

        Returns:
            ValidationResult indicating if recent context intact
        """
        pass
```

## Test Execution Flow

### Red Phase (Expected)

```bash
$ ./RUN_COMPACTION_TESTS.sh all

# After creating compaction_validator.py with stubs:
# Expected: FAILURES (not SKIPS)
# This means implementation is being tested but not working yet
```

### Green Phase (Goal)

Implement methods one at a time until all tests pass:

```bash
$ ./RUN_COMPACTION_TESTS.sh all
==========================================
Ran 34 tests in 0.5s
OK
```

## Implementation Order (Suggested)

1. **CompactionContext dataclass** (simplest)
   - Basic attributes
   - `get_diagnostic_summary()` method
   - Tests: `TestCompactionContext` (3 tests)

2. **ValidationResult dataclass**
   - Basic attributes
   - `get_summary()` method
   - Tests: `TestValidationResult` (3 tests)

3. **CompactionValidator initialization**
   - `__init__()` method
   - Directory setup
   - Tests: Passes validator creation

4. **load_compaction_context() - basic path**
   - Read compaction_events.json
   - Parse single event
   - Return context
   - Tests: `test_happy_path_valid_compaction_load`

5. **load_compaction_context() - error handling**
   - Corrupt JSON → fail-open
   - Missing file → fail-open
   - Missing transcript → partial load
   - Tests: All error scenario tests

6. **load_compaction_context() - security**
   - Path traversal detection
   - Normalize paths
   - Set security violation flag
   - Tests: `test_path_traversal_attack_prevented`

7. **load_compaction_context() - advanced**
   - Multiple events → latest
   - Stale detection (> 24h)
   - Age calculation
   - Tests: `test_multiple_compaction_events_uses_latest`, `test_stale_compaction_event_marked_as_stale`

8. **validate() - basic**
   - Load context
   - No compaction → pass
   - Compaction detected → delegate to specific validators
   - Tests: `test_end_to_end_validation_success`

9. **validate_todos()**
   - Search for TODO patterns
   - Compare pre/post
   - Generate warnings and recovery steps
   - Tests: `test_validate_todo_preservation`

10. **validate_objectives()**
    - Check for goal statements
    - Compare clarity pre/post
    - Generate appropriate recovery
    - Tests: `test_validate_objectives_preservation`

11. **validate_recent_context()**
    - Check last 10 turns preserved
    - Detect gaps near compaction point
    - Tests: `test_validate_recent_context_preservation`

12. **Integration with PowerSteeringChecker**
    - Add `_check_compaction_handling()` method to PowerSteeringChecker
    - Wire into consideration framework
    - Tests: All integration tests in `test_power_steering_compaction.py`

## Common Pitfalls to Avoid

### 1. Not Failing Open
```python
# ❌ Bad: Raises exception
def load_compaction_context(self, session_id):
    with open(events_file) as f:
        return json.load(f)  # Will raise FileNotFoundError

# ✅ Good: Fails open
def load_compaction_context(self, session_id):
    try:
        with open(events_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return CompactionContext()  # Safe default
```

### 2. Not Handling Path Traversal
```python
# ❌ Bad: No security check
transcript_path = Path(event["pre_compaction_transcript_path"])
with open(transcript_path) as f:
    ...

# ✅ Good: Validate path is within project
transcript_path = Path(event["pre_compaction_transcript_path"])
if not transcript_path.resolve().is_relative_to(self.project_root):
    context.has_security_violation = True
    return context
```

### 3. Not Selecting Latest Event
```python
# ❌ Bad: Returns first event
events = json.load(f)
return events[0]

# ✅ Good: Returns most recent
events = sorted(events, key=lambda e: e["timestamp"], reverse=True)
return events[0]
```

### 4. Not Providing Recovery Steps
```python
# ❌ Bad: Generic warning
return ValidationResult(passed=False, warnings=["Data loss detected"])

# ✅ Good: Specific recovery guidance
return ValidationResult(
    passed=False,
    warnings=["TODO items lost after compaction"],
    recovery_steps=[
        "Review recent work in last 10-20 turns",
        "Recreate TODO list using TodoWrite",
        "Check git commits for completed items"
    ]
)
```

## Performance Requirements

Tests verify these thresholds:

- **load_compaction_context()**: < 100ms even for large events
- **validate()**: < 500ms for 500+ turn transcripts
- **Large transcript (1500 messages)**: < 1 second

Use efficient JSON parsing and avoid unnecessary file I/O.

## Success Criteria

✅ All 34 tests passing
✅ No test skips (all tests execute)
✅ < 2 second total test execution time
✅ All fail-open paths working
✅ All security validations working
✅ Integration tests pass (PowerSteeringChecker)

## Next Step

Create `compaction_validator.py` and start with the simplest class (CompactionContext).

Run tests frequently to see progress:
```bash
./RUN_COMPACTION_TESTS.sh unit
```
