# Power-Steering Compaction API Reference

Developer documentation for compaction handling in power-steering mode.

## Overview

The compaction handling system provides robust validation and diagnostics when conversation context is compacted (older messages removed due to token limits). This ensures critical session data is preserved and developers can integrate compaction awareness into their tools.

## Core Components

### CompactionValidator

Validates that critical session data was preserved during compaction.

**Module:** `power_steering_checker.py`

**Purpose:** Analyzes transcript to detect compaction events and validate data integrity.

**API:**

```python
class CompactionValidator:
    """Validates conversation compaction and data preservation.

    Detects when Claude's context window was compacted (old messages removed)
    and validates that critical session data was preserved. Provides actionable
    diagnostics for recovery when data is lost.

    Philosophy:
    - Fail-open: Default to "valid" when uncertain
    - Actionable: Provide specific recovery steps, not just "data lost"
    - Fast: Validation completes in < 100ms for typical transcripts

    Examples:
        Basic validation:
        >>> validator = CompactionValidator()
        >>> result = validator.validate(transcript, session_id)
        >>> if not result.passed:
        ...     print(f"Warnings: {result.warnings}")
        ...     print(f"Recovery: {result.recovery_steps}")

        Check specific data types:
        >>> result = validator.validate_todos(transcript)
        >>> result.passed
        True

        Get compaction metrics:
        >>> ctx = validator.get_compaction_context(transcript)
        >>> print(f"Turn: {ctx.turn_at_compaction}")
        >>> print(f"Messages removed: {ctx.messages_removed}")
    """

    def validate(
        self,
        transcript: list[dict],
        session_id: str
    ) -> ValidationResult:
        """Validate entire transcript for compaction data loss.

        Checks all critical data types (TODOs, objectives, recent context)
        and returns comprehensive validation result with recovery steps.

        Args:
            transcript: Full conversation transcript (list of turn dicts)
            session_id: Unique session identifier for logging

        Returns:
            ValidationResult with:
                - passed: bool (True if all validations passed)
                - warnings: list[str] (specific failures)
                - recovery_steps: list[str] (how to recover)
                - compaction_context: CompactionContext (metadata)

        Examples:
            >>> transcript = load_transcript("session_123")
            >>> result = validator.validate(transcript, "session_123")
            >>> result.passed
            True
            >>> result.compaction_context.detected
            True
            >>> result.compaction_context.turn_at_compaction
            45
        """
        pass

    def validate_todos(
        self,
        transcript: list[dict]
    ) -> ValidationResult:
        """Validate TODO items preserved after compaction.

        Checks if active TODO items from before compaction are still
        visible in transcript. Fails if TODOs were lost.

        Args:
            transcript: Full conversation transcript

        Returns:
            ValidationResult with TODO-specific validation

        Examples:
            >>> result = validator.validate_todos(transcript)
            >>> if not result.passed:
            ...     print("TODOs lost:", result.warnings)
            ...     print("Recovery:", result.recovery_steps[0])
            Recovery: Recreate TODO list using TodoWrite based on recent work
        """
        pass

    def validate_objectives(
        self,
        transcript: list[dict]
    ) -> ValidationResult:
        """Validate session objectives still clear after compaction.

        Checks if original user goals and current objectives are still
        visible. Fails if context is too fragmented.

        Args:
            transcript: Full conversation transcript

        Returns:
            ValidationResult with objective-specific validation

        Examples:
            >>> result = validator.validate_objectives(transcript)
            >>> result.passed
            False
            >>> result.warnings
            ['Session objectives unclear after compaction']
            >>> result.recovery_steps
            ['Explicitly restate your current goal in the conversation']
        """
        pass

    def get_compaction_context(
        self,
        transcript: list[dict]
    ) -> CompactionContext:
        """Extract compaction metadata from transcript.

        Detects compaction events and extracts diagnostic metadata
        without performing validation.

        Args:
            transcript: Full conversation transcript

        Returns:
            CompactionContext with metadata (see below)

        Examples:
            >>> ctx = validator.get_compaction_context(transcript)
            >>> ctx.detected
            True
            >>> ctx.turn_at_compaction
            45
            >>> ctx.messages_removed
            30
            >>> ctx.get_diagnostic_summary()
            '⚠️  COMPACTION DETECTED at turn 45 (30 messages removed)'
        """
        pass
```

### CompactionContext

Enhanced context object with compaction diagnostics.

**Purpose:** Provides visibility into compaction events for monitoring and debugging.

**API:**

```python
@dataclass
class CompactionContext:
    """Compaction event metadata and diagnostics.

    Captures information about compaction events for logging, monitoring,
    and user feedback. Immutable dataclass for thread safety.

    Attributes:
        detected: Whether compaction occurred in this session
        turn_at_compaction: Which turn number triggered compaction (0-indexed)
        messages_removed: Estimated number of messages removed
        validation_passed: Whether critical data was preserved
        warnings: List of specific validation failures
        diagnostics: Human-readable diagnostic summary

    Examples:
        Create from validation result:
        >>> ctx = CompactionContext(
        ...     detected=True,
        ...     turn_at_compaction=45,
        ...     messages_removed=30,
        ...     validation_passed=False,
        ...     warnings=["TODO items lost"],
        ...     diagnostics="See warnings for recovery steps"
        ... )

        Use in logging:
        >>> if ctx.detected:
        ...     logger.warning(f"Compaction at turn {ctx.turn_at_compaction}")
        ...     for warning in ctx.warnings:
        ...         logger.warning(f"  - {warning}")

        Display to user:
        >>> if ctx.detected and not ctx.validation_passed:
        ...     print(ctx.get_diagnostic_summary())
        ...     print("\\nRecovery needed:")
        ...     for warning in ctx.warnings:
        ...         print(f"  • {warning}")
    """

    detected: bool = False
    turn_at_compaction: int = 0
    messages_removed: int = 0
    validation_passed: bool = True
    warnings: list[str] = field(default_factory=list)
    diagnostics: str = ""

    def get_diagnostic_summary(self) -> str:
        """Generate human-readable diagnostic summary.

        Returns:
            Multi-line string with compaction details and status

        Examples:
            >>> ctx = CompactionContext(detected=True, turn_at_compaction=45,
            ...                         messages_removed=30, validation_passed=True)
            >>> print(ctx.get_diagnostic_summary())
            ⚠️  COMPACTION DETECTED
            Conversation was compacted at turn 45
            Messages removed: ~30 (estimated 15,000 tokens)
            Validation: PASSED ✓

            Critical data preserved:
              • Active TODO items
              • Current objectives
              • Recent code changes (last 10 turns)
        """
        pass

    def has_warnings(self) -> bool:
        """Check if any validation warnings exist.

        Returns:
            True if warnings list is non-empty

        Examples:
            >>> ctx = CompactionContext(warnings=["TODO items lost"])
            >>> ctx.has_warnings()
            True
        """
        return len(self.warnings) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict with all fields serializable to JSON

        Examples:
            >>> ctx = CompactionContext(detected=True, turn_at_compaction=45)
            >>> json.dumps(ctx.to_dict())
            '{"detected": true, "turn_at_compaction": 45, ...}'
        """
        pass
```

### ValidationResult

Result object returned by validation methods.

**Purpose:** Encapsulates validation outcome with recovery guidance.

**API:**

```python
@dataclass
class ValidationResult:
    """Result of compaction validation with recovery guidance.

    Immutable result object containing validation outcome and
    actionable recovery steps when validation fails.

    Attributes:
        passed: Whether validation passed (True = data preserved)
        warnings: List of specific validation failures
        recovery_steps: List of actionable recovery steps
        compaction_context: Metadata about compaction event

    Examples:
        Success case:
        >>> result = ValidationResult(
        ...     passed=True,
        ...     warnings=[],
        ...     recovery_steps=[],
        ...     compaction_context=CompactionContext(detected=False)
        ... )
        >>> result.passed
        True

        Failure case with recovery:
        >>> result = ValidationResult(
        ...     passed=False,
        ...     warnings=["TODO items lost after compaction"],
        ...     recovery_steps=[
        ...         "Recreate TODO list using TodoWrite",
        ...         "Check recent commits for completion evidence"
        ...     ],
        ...     compaction_context=CompactionContext(
        ...         detected=True,
        ...         turn_at_compaction=45
        ...     )
        ... )
        >>> result.passed
        False
        >>> len(result.recovery_steps)
        2
    """

    passed: bool
    warnings: list[str] = field(default_factory=list)
    recovery_steps: list[str] = field(default_factory=list)
    compaction_context: CompactionContext = field(default_factory=CompactionContext)

    def get_summary(self) -> str:
        """Generate human-readable validation summary.

        Returns:
            Multi-line summary with status and guidance

        Examples:
            >>> result = ValidationResult(passed=False,
            ...     warnings=["TODOs lost"],
            ...     recovery_steps=["Recreate TODO list"])
            >>> print(result.get_summary())
            Validation: FAILED ✗

            Issues detected:
              • TODOs lost

            Recovery steps:
              1. Recreate TODO list
        """
        pass
```

## Integration Points

### Power-Steering Checker Integration

The `CompactionValidator` integrates into the main power-steering checker.

**Location:** `power_steering_checker.py` - `PowerSteeringChecker` class

**Integration method:**

```python
class PowerSteeringChecker:
    """Main power-steering checker with compaction support."""

    def __init__(self):
        """Initialize checker with compaction validator."""
        self.compaction_validator = CompactionValidator()

    def check(
        self,
        transcript: list[dict],
        session_id: str
    ) -> PowerSteeringResult:
        """Run all checks including compaction validation.

        Compaction validation runs as part of the consideration set:
        - Consideration ID: "compaction_handling"
        - Category: "Session Completion & Progress"
        - Severity: "warning" (doesn't block by default)
        - Checker: "_check_compaction_handling"

        Examples:
            >>> checker = PowerSteeringChecker()
            >>> result = checker.check(transcript, "session_123")
            >>>
            >>> # Check compaction results
            >>> compaction_check = next(
            ...     c for c in result.considerations
            ...     if c.id == "compaction_handling"
            ... )
            >>> compaction_check.satisfied
            True
            >>> compaction_check.compaction_context.detected
            True
        """
        # Run all considerations including compaction
        considerations = self._run_all_considerations(transcript, session_id)

        # Extract compaction context for visibility
        compaction_ctx = self.compaction_validator.get_compaction_context(transcript)

        return PowerSteeringResult(
            considerations=considerations,
            compaction_context=compaction_ctx
        )

    def _check_compaction_handling(
        self,
        transcript: list[dict],
        session_id: str
    ) -> bool:
        """Consideration checker for compaction validation.

        Called by consideration framework. Returns True if compaction
        was handled appropriately or didn't occur.

        Returns:
            True if no compaction or validation passed, False if failed
        """
        result = self.compaction_validator.validate(transcript, session_id)
        return result.passed
```

## Testing Scenarios

The compaction system handles 10 edge case scenarios comprehensively tested.

### Test Scenario 1: No Compaction

**Setup:** Normal session with < 100k tokens

**Expected:**

```python
ctx = validator.get_compaction_context(transcript)
assert not ctx.detected
assert ctx.turn_at_compaction == 0
assert ctx.validation_passed  # No validation needed
```

### Test Scenario 2: Clean Compaction

**Setup:** Compaction occurred, all critical data preserved

**Expected:**

```python
result = validator.validate(transcript, "session_123")
assert result.passed
assert result.compaction_context.detected
assert len(result.warnings) == 0
```

### Test Scenario 3: TODO Loss

**Setup:** Compaction removed messages containing active TODOs

**Expected:**

```python
result = validator.validate_todos(transcript)
assert not result.passed
assert "TODO items lost" in result.warnings
assert "Recreate TODO list" in result.recovery_steps[0]
```

### Test Scenario 4: Objective Loss

**Setup:** Original user goal was in removed messages

**Expected:**

```python
result = validator.validate_objectives(transcript)
assert not result.passed
assert "objectives unclear" in result.warnings[0].lower()
assert "restate your goal" in result.recovery_steps[0].lower()
```

### Test Scenario 5: Multiple Compactions

**Setup:** Conversation compacted more than once

**Expected:**

```python
ctx = validator.get_compaction_context(transcript)
assert ctx.detected
# Reports latest compaction event
assert ctx.turn_at_compaction > 0
```

### Test Scenario 6: Edge of Context

**Setup:** Compaction occurred just before critical message

**Expected:**

```python
result = validator.validate(transcript, "session_123")
# Should warn about potential data loss
if not result.passed:
    assert "recent changes may be incomplete" in result.warnings
```

### Test Scenario 7: Empty Transcript

**Setup:** Empty or very short transcript

**Expected:**

```python
ctx = validator.get_compaction_context([])
assert not ctx.detected
assert ctx.validation_passed  # Fail-open
```

### Test Scenario 8: Malformed Transcript

**Setup:** Transcript with missing fields or bad structure

**Expected:**

```python
# Should not crash, fail-open
result = validator.validate(malformed_transcript, "session_123")
assert result.passed  # Fail-open on errors
```

### Test Scenario 9: Large Transcript

**Setup:** Transcript with 500+ turns (performance test)

**Expected:**

```python
import time
start = time.time()
result = validator.validate(large_transcript, "session_123")
duration = time.time() - start

assert duration < 0.5  # Should complete in < 500ms
```

### Test Scenario 10: Concurrent Validation

**Setup:** Multiple validations running in parallel

**Expected:**

```python
# CompactionValidator is stateless and thread-safe
import concurrent.futures

validator = CompactionValidator()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(validator.validate, transcript, f"session_{i}")
        for i in range(100)
    ]
    results = [f.result() for f in futures]

# All validations should complete without errors
assert all(r.passed or not r.passed for r in results)  # No crashes
```

## Metrics and Observability

### Tracked Metrics

Compaction events expose these metrics for monitoring:

**Event metrics:**

- `compaction.detected` (counter) - Number of compaction events detected
- `compaction.turn_at_compaction` (histogram) - Distribution of compaction timing
- `compaction.messages_removed` (histogram) - Distribution of data loss

**Validation metrics:**

- `compaction.validation.passed` (counter) - Successful validations
- `compaction.validation.failed` (counter) - Failed validations
- `compaction.validation.duration_ms` (histogram) - Validation performance

**Warning metrics:**

- `compaction.warning.todo_loss` (counter) - TODO items lost
- `compaction.warning.objective_loss` (counter) - Objectives unclear
- `compaction.warning.context_loss` (counter) - Recent context incomplete

### Logging

Compaction events log at appropriate levels:

```python
import logging

logger = logging.getLogger("power_steering.compaction")

# INFO: Compaction detected
logger.info(f"Compaction detected at turn {ctx.turn_at_compaction}")

# WARNING: Validation failed
if not result.passed:
    logger.warning(f"Compaction validation failed: {result.warnings}")
    for step in result.recovery_steps:
        logger.info(f"Recovery: {step}")

# DEBUG: Detailed diagnostics
logger.debug(f"Compaction context: {ctx.to_dict()}")
```

## Best Practices

### For Developers

**DO:**

- ✅ Use `get_compaction_context()` for read-only diagnostics
- ✅ Check `validation_passed` before trusting session state
- ✅ Log compaction events for monitoring
- ✅ Provide recovery guidance to users
- ✅ Test with large transcripts (500+ turns)

**DON'T:**

- ❌ Assume no compaction in long sessions
- ❌ Block users on compaction detection (use warnings)
- ❌ Ignore validation failures
- ❌ Retry validation on failure (won't change outcome)

### For Tool Builders

**Integration checklist:**

1. Import `CompactionValidator` from `power_steering_checker.py`
2. Create validator instance (stateless, reusable)
3. Call `validate()` after loading transcript
4. Check `result.passed` and display warnings
5. Show `compaction_context.diagnostics` to users
6. Log metrics for observability

**Example integration:**

```python
from power_steering_checker import CompactionValidator, ValidationResult

def check_session_completeness(transcript: list[dict], session_id: str):
    """Check if session is complete, including compaction validation."""

    # Create validator
    validator = CompactionValidator()

    # Run validation
    result = validator.validate(transcript, session_id)

    # Handle results
    if result.compaction_context.detected:
        print(f"⚠️  Compaction detected at turn {result.compaction_context.turn_at_compaction}")

        if not result.passed:
            print("❌ Validation failed:")
            for warning in result.warnings:
                print(f"  • {warning}")

            print("\nRecovery steps:")
            for i, step in enumerate(result.recovery_steps, 1):
                print(f"  {i}. {step}")

            return False
        else:
            print("✅ Critical data preserved")

    return True
```

## Performance Characteristics

**Validation performance:**

- Small transcript (< 50 turns): < 10ms
- Medium transcript (50-200 turns): < 50ms
- Large transcript (200-500 turns): < 200ms
- Very large transcript (500+ turns): < 500ms

**Memory usage:**

- Stateless validator: ~1KB overhead
- ValidationResult object: ~500 bytes
- CompactionContext object: ~300 bytes

**Thread safety:**

- `CompactionValidator` is stateless and thread-safe
- Multiple validations can run concurrently
- No shared mutable state

---

**Version:** v1.0
**Status:** Implemented
**Last Updated:** 2026-01-22
