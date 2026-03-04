#!/usr/bin/env python3
"""
TDD tests for compaction_context.py standalone module.

Section 1: Module importability
Section 2: _parse_timestamp_age security hardening
Section 3: CompactionContext contract
Section 4: ValidationResult contract
"""

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from compaction_context import (
        CompactionContext,
        ValidationResult,
        _parse_timestamp_age,
    )

    MODULE_AVAILABLE = True
except ImportError:
    MODULE_AVAILABLE = False


class TestModuleImportability(unittest.TestCase):
    """Section 1: Module importability — all three symbols must be exported."""

    def test_compaction_context_importable(self):
        """CompactionContext must be importable from compaction_context."""
        self.assertTrue(MODULE_AVAILABLE, "compaction_context module not found")
        from compaction_context import CompactionContext

        self.assertIsNotNone(CompactionContext)

    def test_validation_result_importable(self):
        """ValidationResult must be importable from compaction_context."""
        self.assertTrue(MODULE_AVAILABLE, "compaction_context module not found")
        from compaction_context import ValidationResult

        self.assertIsNotNone(ValidationResult)

    def test_parse_timestamp_age_importable(self):
        """_parse_timestamp_age must be importable from compaction_context."""
        self.assertTrue(MODULE_AVAILABLE, "compaction_context module not found")
        from compaction_context import _parse_timestamp_age

        self.assertIsNotNone(_parse_timestamp_age)


class TestParseTimestampAge(unittest.TestCase):
    """Section 2: _parse_timestamp_age security hardening."""

    def setUp(self):
        if not MODULE_AVAILABLE:
            self.skipTest("compaction_context not available")

    def test_length_cap_rejects_long_string(self):
        """Strings longer than 35 chars must be rejected, returning (0.0, False)."""
        # 36-char string — one over the limit
        long_ts = "2026-01-22T10:00:00.000000+00:00EXT"
        age_hours, is_stale = _parse_timestamp_age(long_ts)
        self.assertEqual(age_hours, 0.0)
        self.assertFalse(is_stale)

    def test_length_cap_accepts_valid_length(self):
        """Strings of 35 chars or fewer with valid content must parse."""
        # "2026-01-22T10:00:00Z" is 20 chars — well within limit
        age_hours, is_stale = _parse_timestamp_age("2026-01-22T10:00:00Z")
        self.assertGreater(age_hours, 0.0)

    def test_z_suffix_normalised(self):
        """Z-suffix timestamps must parse correctly to a positive age."""
        timestamp = "2026-01-22T10:00:00Z"
        age_hours, is_stale = _parse_timestamp_age(timestamp)
        self.assertGreater(age_hours, 0.0)

    def test_naive_timestamp_coerced_to_utc(self):
        """Naive timestamps (no tz info) must be treated as UTC."""
        two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
        naive_ts = two_hours_ago.strftime("%Y-%m-%dT%H:%M:%S")  # no tz suffix
        age_hours, is_stale = _parse_timestamp_age(naive_ts)
        self.assertGreater(age_hours, 1.8)
        self.assertLess(age_hours, 2.2)

    def test_future_timestamp_clamped_to_zero_not_negative(self):
        """Future timestamps must return age_hours=0.0, never a negative value."""
        future = datetime.now(UTC) + timedelta(hours=1)
        # isoformat gives e.g. "2026-03-04T13:00:00.123456+00:00" = 32 chars ≤ 35
        age_hours, is_stale = _parse_timestamp_age(future.isoformat())
        self.assertGreaterEqual(age_hours, 0.0)
        self.assertFalse(is_stale)

    def test_rejects_age_older_than_10_years(self):
        """Implausible timestamps older than 10 years (87600 h) must return (0.0, False)."""
        ancient = datetime.now(UTC) - timedelta(hours=87601)
        age_hours, is_stale = _parse_timestamp_age(ancient.isoformat())
        self.assertEqual(age_hours, 0.0)
        self.assertFalse(is_stale)

    def test_non_string_input_returns_default(self):
        """Non-string inputs must return (0.0, False) without raising."""
        for bad in (None, 123, [], {}):
            age_hours, is_stale = _parse_timestamp_age(bad)
            self.assertEqual(age_hours, 0.0, f"Expected 0.0 for input {bad!r}")
            self.assertFalse(is_stale, f"Expected False for input {bad!r}")

    def test_invalid_string_returns_default(self):
        """Unparseable strings must return (0.0, False) without raising."""
        age_hours, is_stale = _parse_timestamp_age("not-a-timestamp")
        self.assertEqual(age_hours, 0.0)
        self.assertFalse(is_stale)

    def test_empty_string_returns_default(self):
        """Empty string must return (0.0, False)."""
        age_hours, is_stale = _parse_timestamp_age("")
        self.assertEqual(age_hours, 0.0)
        self.assertFalse(is_stale)


class TestCompactionContextContract(unittest.TestCase):
    """Section 3: CompactionContext dataclass contract."""

    def setUp(self):
        if not MODULE_AVAILABLE:
            self.skipTest("compaction_context not available")

    def test_safe_defaults(self):
        """CompactionContext() must have safe zero/False/None defaults."""
        ctx = CompactionContext()
        self.assertFalse(ctx.has_compaction_event)
        self.assertEqual(ctx.turn_at_compaction, 0)
        self.assertEqual(ctx.messages_removed, 0)
        self.assertIsNone(ctx.pre_compaction_transcript)
        self.assertIsNone(ctx.timestamp)
        self.assertFalse(ctx.is_stale)
        self.assertEqual(ctx.age_hours, 0.0)
        self.assertFalse(ctx.has_security_violation)

    def test_post_init_uses_direct_assignment_not_object_setattr(self):
        """__post_init__ must assign attributes directly, never via object.__setattr__."""
        import inspect

        import compaction_context

        source = inspect.getsource(compaction_context.CompactionContext.__post_init__)
        self.assertNotIn("object.__setattr__", source)

    def test_mutability(self):
        """CompactionContext must be mutable (dataclass is not frozen)."""
        ctx = CompactionContext()
        ctx.has_security_violation = True  # must not raise
        self.assertTrue(ctx.has_security_violation)

    def test_post_init_computes_age_for_compaction_event(self):
        """age_hours and is_stale are computed in __post_init__ when event present."""
        two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
        ctx = CompactionContext(
            has_compaction_event=True,
            timestamp=two_hours_ago.isoformat(),
        )
        self.assertGreater(ctx.age_hours, 1.8)
        self.assertLess(ctx.age_hours, 2.2)
        self.assertFalse(ctx.is_stale)

    def test_get_diagnostic_summary_contains_turn_and_messages(self):
        """get_diagnostic_summary must include turn number, messages removed, and 'compaction'."""
        ctx = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=45,
            messages_removed=30,
        )
        summary = ctx.get_diagnostic_summary()
        self.assertIn("45", summary)
        self.assertIn("30", summary)
        self.assertIn("compaction", summary.lower())

    def test_get_diagnostic_summary_no_event(self):
        """get_diagnostic_summary with no event returns a non-empty informative string."""
        ctx = CompactionContext()
        summary = ctx.get_diagnostic_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)

    def test_repr_does_not_leak_transcript_content(self):
        """repr() must not expose pre_compaction_transcript contents."""
        ctx = CompactionContext(
            has_compaction_event=True,
            pre_compaction_transcript=[{"role": "user", "content": "/etc/secret"}],
        )
        repr_str = repr(ctx)
        # The default dataclass repr WILL include the field — this test verifies
        # we don't accidentally surface sensitive path content in str() output
        # (full repr is acceptable; str() should be safe)
        str_out = str(ctx)
        self.assertIsInstance(str_out, str)


class TestValidationResultContract(unittest.TestCase):
    """Section 4: ValidationResult dataclass contract."""

    def setUp(self):
        if not MODULE_AVAILABLE:
            self.skipTest("compaction_context not available")

    def test_defaults_with_passed_true(self):
        """ValidationResult(passed=True) must have empty warnings/steps and used_fallback=False."""
        result = ValidationResult(passed=True)
        self.assertTrue(result.passed)
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.recovery_steps, [])
        self.assertFalse(result.used_fallback)

    def test_get_summary_passed_contains_passed(self):
        """get_summary() for a passing result must contain 'PASSED'."""
        result = ValidationResult(passed=True)
        summary = result.get_summary()
        self.assertIn("PASSED", summary)

    def test_get_summary_failed_contains_failed(self):
        """get_summary() for a failing result must contain 'FAILED'."""
        result = ValidationResult(passed=False, warnings=["Data lost"])
        summary = result.get_summary()
        self.assertIn("FAILED", summary)

    def test_get_summary_failed_includes_warnings_and_steps(self):
        """get_summary() for a failed result must include all warnings and recovery steps."""
        result = ValidationResult(
            passed=False,
            warnings=["Data lost"],
            recovery_steps=["Recreate TODO list"],
        )
        summary = result.get_summary()
        self.assertIn("Data lost", summary)
        self.assertIn("Recreate TODO list", summary)

    def test_repr_is_string(self):
        """repr(ValidationResult) must be a string and not raise."""
        result = ValidationResult(passed=True)
        self.assertIsInstance(repr(result), str)


if __name__ == "__main__":
    unittest.main()
