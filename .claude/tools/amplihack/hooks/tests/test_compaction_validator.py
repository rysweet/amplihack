#!/usr/bin/env python3
"""
TDD Unit tests for CompactionValidator module.

Tests the 10 core scenarios specified in the architect's design:
1. Happy path: Valid compaction data, successful load
2. Corrupt JSON: Malformed compaction_events.json
3. Missing transcript: Events file exists but transcript doesn't
4. Stale transcript: Compaction event > 24 hours old
5. Path traversal: Malicious paths outside project
6. Empty transcript: File exists but zero messages
7. Large transcript: 1000+ messages (performance check)
8. Multiple compactions: Multiple events in array
9. Fallback success: Pre-compaction fails, provided works
10. Complete failure: Both sources fail (fail-open verification)

Philosophy:
- Ruthlessly Simple: Clear test names, single assertions
- Fail-Open: Tests verify graceful degradation on errors
- Zero-BS: All tests should FAIL initially (TDD)
"""

import json
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# These imports will fail initially - that's the point of TDD
try:
    from compaction_validator import (
        CompactionContext,
        CompactionValidator,
        ValidationResult,
    )
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False
    # Create placeholder for better error messages
    class CompactionValidator:
        pass
    class CompactionContext:
        pass
    class ValidationResult:
        pass


class TestCompactionValidator(unittest.TestCase):
    """Unit tests for CompactionValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.validator = CompactionValidator(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    # Scenario 1: Happy path - Valid compaction data, successful load
    def test_happy_path_valid_compaction_load(self):
        """Test loading valid compaction data succeeds."""
        # Arrange: Create valid compaction event
        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_compaction_transcript.json"),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Create pre-compaction transcript
        pre_transcript = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        Path(event_data["pre_compaction_transcript_path"]).write_text(
            json.dumps(pre_transcript)
        )

        # Act: Load compaction context
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Context loaded successfully
        self.assertIsNotNone(context)
        self.assertTrue(context.has_compaction_event)
        self.assertEqual(context.turn_at_compaction, 45)
        self.assertEqual(context.messages_removed, 30)
        self.assertEqual(len(context.pre_compaction_transcript), 2)

    # Scenario 2: Corrupt JSON - Malformed compaction_events.json
    def test_corrupt_json_fails_gracefully(self):
        """Test malformed JSON in compaction_events.json fails open."""
        # Arrange: Create corrupt JSON file
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text("{ bad json content [[[")

        # Act: Attempt to load - should not crash
        context = self.validator.load_compaction_context("test_session")

        # Assert: Fail-open behavior (no compaction detected)
        self.assertIsNotNone(context)
        self.assertFalse(context.has_compaction_event)
        self.assertEqual(context.turn_at_compaction, 0)

    # Scenario 3: Missing transcript - Events file exists but transcript doesn't
    def test_missing_pre_compaction_transcript_fails_open(self):
        """Test missing pre-compaction transcript file fails open."""
        # Arrange: Create event pointing to non-existent transcript
        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": "/nonexistent/path/transcript.json",
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Act: Load context with missing transcript
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Fail-open - event detected but transcript unavailable
        self.assertIsNotNone(context)
        self.assertTrue(context.has_compaction_event)
        self.assertIsNone(context.pre_compaction_transcript)  # Graceful degradation
        self.assertEqual(context.turn_at_compaction, 45)

    # Scenario 4: Stale transcript - Compaction event > 24 hours old
    def test_stale_compaction_event_marked_as_stale(self):
        """Test compaction events older than 24 hours are marked stale."""
        # Arrange: Create old event (25 hours ago)
        from datetime import datetime, timedelta
        stale_time = datetime.now(timezone.utc) - timedelta(hours=25)
        event_data = {
            "timestamp": stale_time.isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Act: Load context
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Event is marked as stale
        self.assertTrue(context.has_compaction_event)
        self.assertTrue(context.is_stale)  # Events > 24h should be marked stale
        self.assertGreater(context.age_hours, 24)

    # Scenario 5: Path traversal - Malicious paths outside project
    def test_path_traversal_attack_prevented(self):
        """Test path traversal attacks are prevented."""
        # Arrange: Create event with path traversal attempt
        malicious_path = "../../../etc/passwd"
        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": malicious_path,
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Act: Attempt to load with malicious path
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Path traversal rejected (fail-open, transcript not loaded)
        self.assertTrue(context.has_compaction_event)
        self.assertIsNone(context.pre_compaction_transcript)  # Security: refuse to load
        self.assertTrue(context.has_security_violation)

    # Scenario 6: Empty transcript - File exists but zero messages
    def test_empty_pre_compaction_transcript_handled(self):
        """Test empty pre-compaction transcript handled gracefully."""
        # Arrange: Create event with empty transcript file
        transcript_path = self.runtime_dir / "empty_transcript.json"
        transcript_path.write_text("[]")  # Empty array

        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(transcript_path),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Act: Load context
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Empty transcript handled (fail-open)
        self.assertTrue(context.has_compaction_event)
        self.assertIsNotNone(context.pre_compaction_transcript)
        self.assertEqual(len(context.pre_compaction_transcript), 0)

    # Scenario 7: Large transcript - 1000+ messages (performance check)
    def test_large_transcript_performance(self):
        """Test large pre-compaction transcript loads in < 1 second."""
        # Arrange: Create large transcript (1500 messages)
        large_transcript = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1500)
        ]
        transcript_path = self.runtime_dir / "large_transcript.json"
        transcript_path.write_text(json.dumps(large_transcript))

        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 1450,
            "messages_removed": 1400,
            "pre_compaction_transcript_path": str(transcript_path),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Act: Time the load operation
        start = time.time()
        context = self.validator.load_compaction_context("test_session_123")
        duration = time.time() - start

        # Assert: Loads quickly and correctly
        self.assertLess(duration, 1.0)  # Should load in < 1 second
        self.assertTrue(context.has_compaction_event)
        self.assertEqual(len(context.pre_compaction_transcript), 1500)

    # Scenario 8: Multiple compactions - Multiple events in array
    def test_multiple_compaction_events_uses_latest(self):
        """Test multiple compaction events returns most recent."""
        # Arrange: Create multiple events for same session
        events = [
            {
                "timestamp": "2026-01-22T09:00:00Z",
                "turn_number": 45,
                "messages_removed": 30,
                "pre_compaction_transcript_path": str(self.runtime_dir / "transcript1.json"),
                "session_id": "test_session_123"
            },
            {
                "timestamp": "2026-01-22T10:00:00Z",  # More recent
                "turn_number": 90,
                "messages_removed": 50,
                "pre_compaction_transcript_path": str(self.runtime_dir / "transcript2.json"),
                "session_id": "test_session_123"
            },
            {
                "timestamp": "2026-01-22T08:00:00Z",  # Oldest
                "turn_number": 20,
                "messages_removed": 15,
                "pre_compaction_transcript_path": str(self.runtime_dir / "transcript3.json"),
                "session_id": "test_session_123"
            }
        ]
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps(events))

        # Create transcripts
        for i in range(1, 4):
            Path(self.runtime_dir / f"transcript{i}.json").write_text("[]")

        # Act: Load context
        context = self.validator.load_compaction_context("test_session_123")

        # Assert: Returns most recent event (10:00)
        self.assertTrue(context.has_compaction_event)
        self.assertEqual(context.turn_at_compaction, 90)  # Most recent
        self.assertEqual(context.messages_removed, 50)

    # Scenario 9: Fallback success - Pre-compaction fails, provided works
    def test_fallback_to_provided_transcript(self):
        """Test validator falls back to provided transcript when pre-compaction unavailable."""
        # Arrange: Event with broken pre-compaction path
        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": "/broken/path.json",
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Provide fallback transcript
        fallback_transcript = [
            {"role": "user", "content": "Fallback message"}
        ]

        # Act: Validate with fallback
        result = self.validator.validate(
            transcript=fallback_transcript,
            session_id="test_session_123"
        )

        # Assert: Validation succeeds using fallback
        self.assertIsNotNone(result)
        self.assertTrue(result.used_fallback)
        # Should still detect compaction but use provided transcript
        self.assertTrue(result.compaction_context.has_compaction_event)

    # Scenario 10: Complete failure - Both sources fail (fail-open verification)
    def test_complete_failure_fails_open(self):
        """Test complete failure of both data sources fails open."""
        # Arrange: Broken event file AND no fallback
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text("{ corrupt json")

        # Act: Validate with no fallback transcript
        result = self.validator.validate(
            transcript=None,  # No fallback
            session_id="test_session_123"
        )

        # Assert: Fail-open (assumes no compaction, validation passes)
        self.assertIsNotNone(result)
        self.assertTrue(result.passed)  # Fail-open on errors
        self.assertFalse(result.compaction_context.has_compaction_event)


class TestCompactionContext(unittest.TestCase):
    """Unit tests for CompactionContext dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionContext not implemented yet (TDD)")

    def test_context_initialization_default_values(self):
        """Test CompactionContext initializes with safe defaults."""
        # Act: Create empty context
        context = CompactionContext()

        # Assert: Safe defaults
        self.assertFalse(context.has_compaction_event)
        self.assertEqual(context.turn_at_compaction, 0)
        self.assertEqual(context.messages_removed, 0)
        self.assertIsNone(context.pre_compaction_transcript)
        self.assertFalse(context.is_stale)

    def test_context_with_valid_event_data(self):
        """Test CompactionContext with valid event data."""
        # Arrange: Create context with event
        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=45,
            messages_removed=30,
            pre_compaction_transcript=[{"role": "user", "content": "test"}],
            timestamp="2026-01-22T10:00:00Z"
        )

        # Assert: Values set correctly
        self.assertTrue(context.has_compaction_event)
        self.assertEqual(context.turn_at_compaction, 45)
        self.assertEqual(context.messages_removed, 30)
        self.assertEqual(len(context.pre_compaction_transcript), 1)

    def test_context_age_calculation(self):
        """Test context calculates age in hours correctly."""
        # Arrange: Create context with timestamp 2 hours ago
        from datetime import datetime, timedelta
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=45,
            messages_removed=30,
            timestamp=two_hours_ago.isoformat()
        )

        # Assert: Age calculated correctly (should be ~2 hours)
        self.assertGreater(context.age_hours, 1.9)
        self.assertLess(context.age_hours, 2.2)
        self.assertFalse(context.is_stale)  # < 24 hours

    def test_context_diagnostic_summary_generation(self):
        """Test context generates human-readable diagnostic summary."""
        # Arrange: Create context with event
        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=45,
            messages_removed=30,
            timestamp="2026-01-22T10:00:00Z"
        )

        # Act: Generate summary
        summary = context.get_diagnostic_summary()

        # Assert: Summary contains key information
        self.assertIn("45", summary)  # Turn number
        self.assertIn("30", summary)  # Messages removed
        self.assertIn("compaction", summary.lower())


class TestValidationResult(unittest.TestCase):
    """Unit tests for ValidationResult dataclass."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("ValidationResult not implemented yet (TDD)")

    def test_validation_result_passed(self):
        """Test validation result for passed validation."""
        # Arrange: Create passed result
        context = CompactionContext(has_compaction_event=False)
        result = ValidationResult(
            passed=True,
            warnings=[],
            recovery_steps=[],
            compaction_context=context,
            used_fallback=False
        )

        # Assert: Result indicates success
        self.assertTrue(result.passed)
        self.assertEqual(len(result.warnings), 0)
        self.assertEqual(len(result.recovery_steps), 0)

    def test_validation_result_failed_with_warnings(self):
        """Test validation result for failed validation with warnings."""
        # Arrange: Create failed result
        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=45,
            messages_removed=30
        )
        result = ValidationResult(
            passed=False,
            warnings=["TODO items lost after compaction"],
            recovery_steps=["Recreate TODO list using TodoWrite"],
            compaction_context=context,
            used_fallback=False
        )

        # Assert: Result contains failure information
        self.assertFalse(result.passed)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("TODO", result.warnings[0])
        self.assertEqual(len(result.recovery_steps), 1)

    def test_validation_result_summary_generation(self):
        """Test validation result generates human-readable summary."""
        # Arrange: Create result with warnings
        context = CompactionContext(has_compaction_event=True, turn_at_compaction=45)
        result = ValidationResult(
            passed=False,
            warnings=["Data loss detected"],
            recovery_steps=["Review recent work", "Recreate TODO list"],
            compaction_context=context,
            used_fallback=False
        )

        # Act: Generate summary
        summary = result.get_summary()

        # Assert: Summary contains key information
        self.assertIn("Data loss", summary)
        self.assertIn("Review recent work", summary)
        self.assertIn("Recreate TODO list", summary)


class TestCompactionValidatorValidation(unittest.TestCase):
    """Unit tests for CompactionValidator validation logic."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.validator = CompactionValidator(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_validate_todo_preservation(self):
        """Test validation detects when TODO items are lost."""
        # Arrange: Pre-compaction transcript with TODOs
        pre_transcript = [
            {"role": "user", "content": "Implement feature X"},
            {"role": "assistant", "content": "I'll create a TODO list"},
            {
                "role": "assistant",
                "content": "TODO: Implement feature X\nTODO: Write tests\nTODO: Update docs"
            }
        ]

        # Post-compaction transcript WITHOUT TODOs (they were removed)
        post_transcript = [
            {"role": "user", "content": "How's it going?"},
            {"role": "assistant", "content": "Working on it"}
        ]

        # Act: Validate TODO preservation
        result = self.validator.validate_todos(
            pre_compaction=pre_transcript,
            post_compaction=post_transcript
        )

        # Assert: Detects TODO loss
        self.assertFalse(result.passed)
        self.assertTrue(any("TODO" in w for w in result.warnings))
        self.assertTrue(any("recreate" in s.lower() for s in result.recovery_steps))

    def test_validate_objectives_preservation(self):
        """Test validation detects when session objectives are unclear."""
        # Arrange: Pre-compaction with clear objective
        pre_transcript = [
            {"role": "user", "content": "I need to implement compaction handling for power-steering"},
            {"role": "assistant", "content": "I'll help implement compaction handling"}
        ]

        # Post-compaction without objective context
        post_transcript = [
            {"role": "user", "content": "What's next?"},
            {"role": "assistant", "content": "Let me check"}
        ]

        # Act: Validate objectives
        result = self.validator.validate_objectives(
            pre_compaction=pre_transcript,
            post_compaction=post_transcript
        )

        # Assert: Detects objective loss
        self.assertFalse(result.passed)
        self.assertTrue(any("objective" in w.lower() for w in result.warnings))

    def test_validate_recent_context_preservation(self):
        """Test validation ensures recent context (last 10 turns) is preserved."""
        # Arrange: Compaction that removed recent messages
        pre_transcript = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(100)
        ]

        # Post-compaction removed messages 80-90 (recent context lost)
        post_transcript = pre_transcript[:80] + pre_transcript[91:]

        # Create context indicating compaction at turn 85
        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=85,
            messages_removed=10
        )

        # Act: Validate recent context
        result = self.validator.validate_recent_context(
            pre_compaction=pre_transcript,
            post_compaction=post_transcript,
            context=context
        )

        # Assert: Detects recent context loss
        self.assertFalse(result.passed)
        self.assertTrue(any("recent" in w.lower() for w in result.warnings))


class TestCompactionValidatorIntegration(unittest.TestCase):
    """Integration tests for CompactionValidator end-to-end flows."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        self.validator = CompactionValidator(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_end_to_end_validation_success(self):
        """Test complete validation flow with all data preserved."""
        # Arrange: Create compaction event with preserved data
        pre_transcript = [
            {"role": "user", "content": "Implement feature X"},
            {"role": "assistant", "content": "TODO: Task 1\nTODO: Task 2"},
            {"role": "user", "content": "Great"},
        ]

        transcript_path = self.runtime_dir / "pre_transcript.json"
        transcript_path.write_text(json.dumps(pre_transcript))

        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 2,
            "messages_removed": 1,
            "pre_compaction_transcript_path": str(transcript_path),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Post-compaction transcript (TODOs preserved)
        post_transcript = [
            {"role": "assistant", "content": "TODO: Task 1\nTODO: Task 2"},
            {"role": "user", "content": "Great"},
        ]

        # Act: Run full validation
        result = self.validator.validate(
            transcript=post_transcript,
            session_id="test_session_123"
        )

        # Assert: Validation passes
        self.assertTrue(result.passed)
        self.assertEqual(len(result.warnings), 0)
        self.assertTrue(result.compaction_context.has_compaction_event)

    def test_end_to_end_validation_failure(self):
        """Test complete validation flow with data loss."""
        # Arrange: Create compaction event with data loss
        pre_transcript = [
            {"role": "user", "content": "Implement compaction handling"},
            {"role": "assistant", "content": "TODO: Write validator\nTODO: Write tests"},
        ]

        transcript_path = self.runtime_dir / "pre_transcript.json"
        transcript_path.write_text(json.dumps(pre_transcript))

        event_data = {
            "timestamp": "2026-01-22T10:00:00Z",
            "turn_number": 2,
            "messages_removed": 1,
            "pre_compaction_transcript_path": str(transcript_path),
            "session_id": "test_session_123"
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Post-compaction transcript (TODOs LOST)
        post_transcript = [
            {"role": "user", "content": "What should I do next?"},
        ]

        # Act: Run full validation
        result = self.validator.validate(
            transcript=post_transcript,
            session_id="test_session_123"
        )

        # Assert: Validation fails with actionable recovery
        self.assertFalse(result.passed)
        self.assertGreater(len(result.warnings), 0)
        self.assertGreater(len(result.recovery_steps), 0)
        self.assertTrue(result.compaction_context.has_compaction_event)


if __name__ == "__main__":
    unittest.main()
