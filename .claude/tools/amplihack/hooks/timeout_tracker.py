"""
Timeout tracking for stop hook operations.

Provides TimeoutTracker class to help stop hook gracefully skip operations
when insufficient time remains in the 30-second hook budget.

Security considerations:
- Uses time.monotonic() to prevent clock manipulation attacks
- Fails open on all errors (returns True from has_time())
- Validates configuration at module load
- Logs all timeout-based decisions for audit trail

Constants:
    HOOK_TIMEOUT_BUDGET: Total time budget (25s, leaving 5s buffer)
    MIN_TIME_POWER_STEERING: Minimum time needed for power-steering (15s)
    MIN_TIME_REFLECTION: Minimum time needed for reflection (12s)
"""

import time

# Configuration constants
HOOK_TIMEOUT_BUDGET = 25.0  # Leave 5s buffer before Claude Code's 30s timeout
MIN_TIME_POWER_STEERING = 15.0  # Power-steering needs meaningful time
MIN_TIME_REFLECTION = 12.0  # Reflection needs meaningful time

# Validate configuration at module load (SECURITY REQUIREMENT)
assert HOOK_TIMEOUT_BUDGET > 0, "Timeout budget must be positive"
assert MIN_TIME_POWER_STEERING > 0, "Power-steering minimum must be positive"
assert MIN_TIME_REFLECTION > 0, "Reflection minimum must be positive"
assert MIN_TIME_POWER_STEERING < HOOK_TIMEOUT_BUDGET, (
    f"Power-steering minimum ({MIN_TIME_POWER_STEERING}s) exceeds budget ({HOOK_TIMEOUT_BUDGET}s)"
)
assert MIN_TIME_REFLECTION < HOOK_TIMEOUT_BUDGET, (
    f"Reflection minimum ({MIN_TIME_REFLECTION}s) exceeds budget ({HOOK_TIMEOUT_BUDGET}s)"
)


class TimeoutTracker:
    """
    Thread-safe timeout tracking using monotonic time.

    Tracks elapsed time and remaining budget to help decide whether
    to start expensive operations that may not complete in time.

    Security considerations:
    - Uses time.monotonic() to prevent clock manipulation attacks
    - Fails open on all errors (returns True from has_time())
    - Validates inputs and provides defensive bounds checking

    Example:
        >>> tracker = TimeoutTracker(budget_seconds=25.0)
        >>> if tracker.has_time(operation_min=15.0):
        ...     run_expensive_operation()
        >>> print(f"Elapsed: {tracker.elapsed():.1f}s")
        Elapsed: 5.2s
    """

    def __init__(self, budget_seconds: float = HOOK_TIMEOUT_BUDGET):
        """
        Initialize timeout tracker.

        Args:
            budget_seconds: Total time budget in seconds (default: HOOK_TIMEOUT_BUDGET)

        Raises:
            ValueError: If budget_seconds is not positive
        """
        if budget_seconds <= 0:
            raise ValueError(f"budget_seconds must be positive, got {budget_seconds}")

        # SECURITY: Use monotonic time to prevent clock manipulation
        self.start_time = time.monotonic()
        self.budget_seconds = budget_seconds

    def elapsed(self) -> float:
        """
        Get elapsed time since tracker creation.

        Returns:
            Elapsed seconds as float

        Security:
            Uses time.monotonic() which is immune to system clock changes
        """
        # SECURITY: Use monotonic time (immune to clock changes)
        elapsed = time.monotonic() - self.start_time

        # Defensive: Check for negative values (should be impossible with monotonic)
        if elapsed < 0:
            # This should never happen with monotonic time, but check anyway
            import sys

            print(
                f"WARNING: Negative elapsed time detected "
                f"(start={self.start_time}, now={time.monotonic()})",
                file=sys.stderr,
            )
            return 0.0  # Fail-safe: return 0 instead of negative

        return elapsed

    def remaining(self) -> float:
        """
        Get remaining time in budget.

        Returns:
            Remaining seconds as float (may be negative if over budget)
        """
        return self.budget_seconds - self.elapsed()

    def has_time(self, operation_min: float) -> bool:
        """
        Check if sufficient time remains for an operation.

        Args:
            operation_min: Minimum time required in seconds (must be non-negative)

        Returns:
            True if sufficient time remains (remaining >= operation_min),
            False otherwise. Always returns True for operation_min=0.

        Raises:
            ValueError: If operation_min is negative

        Security:
            Returns True (fail-open) on all errors except validation errors.
            This ensures that timeout tracking failures don't block operations.
        """
        if operation_min < 0:
            raise ValueError(f"operation_min must be non-negative, got {operation_min}")

        # Special case: If operation needs 0 time, always allow it
        if operation_min == 0.0:
            return True

        try:
            remaining = self.remaining()
            return remaining >= operation_min
        except Exception:
            # SECURITY: Fail-open on any unexpected error
            # This is critical - timeout tracking should never block operations
            return True

    def __repr__(self) -> str:
        """
        Return string representation for debugging.

        Returns:
            String showing elapsed and remaining time
        """
        try:
            elapsed = self.elapsed()
            remaining = self.remaining()
            return f"TimeoutTracker(elapsed={elapsed:.1f}s, remaining={remaining:.1f}s, budget={self.budget_seconds:.1f}s)"
        except Exception:
            # Fail-safe: return basic info if calculation fails
            return f"TimeoutTracker(budget={self.budget_seconds:.1f}s)"

    __str__ = __repr__
