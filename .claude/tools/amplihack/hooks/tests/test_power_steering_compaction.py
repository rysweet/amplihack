#!/usr/bin/env python3
"""
TDD Integration tests for power-steering compaction handling.

Tests integration between CompactionValidator and PowerSteeringChecker,
focusing on the end-to-end flow through the consideration framework.

Philosophy:
- Ruthlessly Simple: Clear test scenarios matching real-world usage
- Fail-Open: Verify graceful degradation paths
- Zero-BS: All tests should FAIL initially (TDD)

These tests verify:
- CompactionValidator integrates into PowerSteeringChecker
- Compaction consideration runs as part of check suite
- Diagnostics are generated correctly
- Fail-open behavior works across the stack
"""

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import checker (already exists)
from power_steering_checker import (
    PowerSteeringChecker,
)

# Import validator (will fail initially - TDD)
try:
    from compaction_validator import (
        CompactionContext,
        CompactionValidator,
        ValidationResult,
    )

    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False

    # Create placeholder
    class CompactionValidator:
        pass

    class CompactionContext:
        pass

    class ValidationResult:
        pass


class TestPowerSteeringCompactionIntegration(unittest.TestCase):
    """Integration tests for compaction handling in power-steering."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        # Create default checker config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "version": "1.0.0",
            "phase": 1,
            "checkers_enabled": {
                "compaction_handling": True,
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

        # Create considerations.yaml with compaction consideration
        considerations_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        )
        considerations = [
            {
                "id": "compaction_handling",
                "category": "Session Completion & Progress",
                "question": "Was compaction handled appropriately?",
                "description": "Validates critical data preserved after conversation compaction",
                "severity": "warning",
                "checker": "_check_compaction_handling",
                "enabled": True,
            }
        ]
        considerations_path.write_text(json.dumps(considerations, indent=2))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_compaction_check_runs_in_checker_suite(self):
        """Test compaction consideration runs as part of checker suite."""
        # Arrange: Create simple transcript without compaction
        transcript = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session")

        # Assert: Compaction check was executed
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertTrue(compaction_check.satisfied)  # No compaction = pass

    def test_compaction_check_detects_event(self):
        """Test compaction check detects compaction event from runtime data."""
        # Arrange: Create compaction event
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Create pre-compaction transcript
        pre_transcript = [
            {"role": "user", "content": "Task: Implement feature"},
            {"role": "assistant", "content": "TODO: Step 1\nTODO: Step 2"},
        ]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        # Current transcript (after compaction, TODOs preserved)
        transcript = [
            {"role": "assistant", "content": "TODO: Step 1\nTODO: Step 2"},
            {"role": "user", "content": "Great"},
        ]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Compaction detected and handled
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertTrue(compaction_check.satisfied)  # Data preserved
        self.assertIsNotNone(result.compaction_context)
        self.assertTrue(result.compaction_context.has_compaction_event)

    def test_compaction_check_fails_on_data_loss(self):
        """Test compaction check fails when critical data is lost."""
        # Arrange: Create compaction event
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Pre-compaction transcript with TODOs
        pre_transcript = [
            {"role": "user", "content": "Task: Implement feature"},
            {"role": "assistant", "content": "TODO: Step 1\nTODO: Step 2\nTODO: Step 3"},
        ]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        # Current transcript (TODOs LOST)
        transcript = [
            {"role": "user", "content": "What should I do?"},
            {"role": "assistant", "content": "Let me check"},
        ]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Compaction check fails
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertFalse(compaction_check.satisfied)  # Data lost
        self.assertIsNotNone(compaction_check.reason)
        self.assertIn("TODO", compaction_check.reason)

    def test_compaction_check_provides_recovery_guidance(self):
        """Test compaction check provides actionable recovery steps."""
        # Arrange: Create compaction event with data loss
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Pre-compaction with objective
        pre_transcript = [
            {"role": "user", "content": "I need to implement compaction handling"},
            {"role": "assistant", "content": "I'll help with that"},
        ]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        # Post-compaction (objective unclear)
        transcript = [{"role": "user", "content": "What's next?"}]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Recovery guidance provided
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertIsNotNone(compaction_check.recovery_steps)
        self.assertGreater(len(compaction_check.recovery_steps), 0)
        # Recovery steps should mention restating objective
        recovery_text = " ".join(compaction_check.recovery_steps)
        self.assertTrue(
            any(word in recovery_text.lower() for word in ["restate", "clarify", "objective"])
        )

    def test_compaction_check_includes_diagnostics(self):
        """Test compaction check includes diagnostic information."""
        # Arrange: Create compaction event
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        pre_transcript = [{"role": "user", "content": "Hello"}]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        transcript = [{"role": "user", "content": "Hello"}]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Diagnostics included
        self.assertIsNotNone(result.compaction_context)
        self.assertEqual(result.compaction_context.turn_at_compaction, 45)
        self.assertEqual(result.compaction_context.messages_removed, 30)

        # Diagnostic summary should be available
        diagnostic = result.compaction_context.get_diagnostic_summary()
        self.assertIsNotNone(diagnostic)
        self.assertIn("45", diagnostic)
        self.assertIn("30", diagnostic)

    def test_compaction_check_handles_missing_events_file(self):
        """Test compaction check handles missing compaction_events.json gracefully."""
        # Arrange: No compaction events file
        # (Just don't create one)

        transcript = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session")

        # Assert: Check passes (no compaction detected)
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertTrue(compaction_check.satisfied)  # Fail-open

    def test_compaction_check_handles_corrupt_events_file(self):
        """Test compaction check handles corrupt compaction_events.json gracefully."""
        # Arrange: Create corrupt JSON file
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text("{ bad json [[")

        transcript = [{"role": "user", "content": "Hello"}]

        # Act: Run checker (should not crash)
        result = self.checker.check(transcript, session_id="test_session")

        # Assert: Check passes (fail-open on corruption)
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        self.assertIsNotNone(compaction_check)
        assert compaction_check is not None  # Type narrowing for mypy
        self.assertTrue(compaction_check.satisfied)  # Fail-open

    def test_compaction_check_respects_enabled_flag(self):
        """Test compaction check respects enabled flag in considerations.yaml."""
        # Arrange: Disable compaction check
        considerations_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        )
        considerations = [
            {
                "id": "compaction_handling",
                "category": "Session Completion & Progress",
                "question": "Was compaction handled appropriately?",
                "description": "Validates critical data preserved after conversation compaction",
                "severity": "warning",
                "checker": "_check_compaction_handling",
                "enabled": False,  # DISABLED
            }
        ]
        considerations_path.write_text(json.dumps(considerations, indent=2))

        # Reload checker to pick up new config
        self.checker = PowerSteeringChecker(self.project_root)

        transcript = [{"role": "user", "content": "Hello"}]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session")

        # Assert: Compaction check not present or marked as disabled
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        # Either not present, or present but not executed
        if compaction_check:
            self.assertFalse(compaction_check.executed)


class TestCompactionCheckStaleEvents(unittest.TestCase):
    """Tests for handling stale compaction events."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        # Create checker config
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True, "version": "1.0.0"}
        config_path.write_text(json.dumps(config))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_stale_event_marked_in_diagnostics(self):
        """Test stale compaction events (>24h) are marked in diagnostics."""
        # Arrange: Create old event (25 hours ago)
        stale_time = datetime.now(UTC) - timedelta(hours=25)
        event_data = {
            "timestamp": stale_time.isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        pre_transcript = [{"role": "user", "content": "Old message"}]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        transcript = [{"role": "user", "content": "New message"}]

        # Act: Run checker
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Stale event marked in context
        self.assertTrue(result.compaction_context.is_stale)
        self.assertGreater(result.compaction_context.age_hours, 24)


class TestCompactionCheckPerformance(unittest.TestCase):
    """Performance tests for compaction validation."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True}
        config_path.write_text(json.dumps(config))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_large_transcript_validation_performance(self):
        """Test compaction validation with large transcripts completes quickly."""
        # Arrange: Create large compaction event
        large_pre_transcript = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(1000)
        ]
        transcript_path = self.runtime_dir / "large_pre_transcript.json"
        transcript_path.write_text(json.dumps(large_pre_transcript))

        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 950,
            "messages_removed": 900,
            "pre_compaction_transcript_path": str(transcript_path),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        # Large current transcript
        large_transcript = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(950, 1100)
        ]

        # Act: Time the validation
        import time

        start = time.time()
        result = self.checker.check(large_transcript, session_id="test_session_123")
        duration = time.time() - start

        # Assert: Completes in reasonable time (< 2 seconds for large transcript)
        self.assertLess(duration, 2.0)
        self.assertIsNotNone(result)


class TestCompactionCheckSecurityValidation(unittest.TestCase):
    """Security tests for compaction handling."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True}
        config_path.write_text(json.dumps(config))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_path_traversal_blocked(self):
        """Test path traversal attempts are blocked in compaction paths."""
        # Arrange: Create event with path traversal
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": "../../../etc/passwd",  # Malicious
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        transcript = [{"role": "user", "content": "Test"}]

        # Act: Run checker (should not read malicious path)
        result = self.checker.check(transcript, session_id="test_session_123")

        # Assert: Security violation detected, fail-open
        self.assertTrue(result.compaction_context.has_security_violation)
        # Should still pass (fail-open) but mark security issue
        compaction_check = next(
            (c for c in result.considerations if c.id == "compaction_handling"), None
        )
        if compaction_check:
            self.assertTrue(compaction_check.satisfied)  # Fail-open


class TestCompactionCheckDiagnosticOutput(unittest.TestCase):
    """Tests for diagnostic output formatting."""

    def setUp(self):
        """Set up test fixtures."""
        if not VALIDATOR_AVAILABLE:
            self.skipTest("CompactionValidator not implemented yet (TDD)")

        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True}
        config_path.write_text(json.dumps(config))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_diagnostic_summary_contains_key_metrics(self):
        """Test diagnostic summary contains turn number and messages removed."""
        # Arrange: Create compaction event
        event_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "turn_number": 45,
            "messages_removed": 30,
            "pre_compaction_transcript_path": str(self.runtime_dir / "pre_transcript.json"),
            "session_id": "test_session_123",
        }
        events_file = self.runtime_dir / "compaction_events.json"
        events_file.write_text(json.dumps([event_data]))

        pre_transcript = [{"role": "user", "content": "Hello"}]
        Path(event_data["pre_compaction_transcript_path"]).write_text(json.dumps(pre_transcript))

        transcript = [{"role": "user", "content": "Hello"}]

        # Act: Run checker and get diagnostics
        result = self.checker.check(transcript, session_id="test_session_123")
        diagnostic = result.compaction_context.get_diagnostic_summary()

        # Assert: Key metrics in output
        self.assertIn("45", diagnostic)  # Turn number
        self.assertIn("30", diagnostic)  # Messages removed
        self.assertIn("compaction", diagnostic.lower())


if __name__ == "__main__":
    unittest.main()
