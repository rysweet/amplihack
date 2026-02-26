#!/usr/bin/env python3
"""
Tests for the power-steering state module refactoring (Issue #2556).

Verifies:
1. Backward compatibility: all imports from power_steering_state still work
2. Module isolation: each new module works independently
3. Constants are shared correctly across modules
4. Data models serialize/deserialize identically to the original
5. TurnStateManager delegates correctly to state_io
6. DeltaAnalyzer works independently of TurnStateManager
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Test 1: Backward Compatibility (imports from power_steering_state)
# ============================================================================


class TestBackwardCompatibility:
    """Verify all original imports still work from power_steering_state."""

    def test_import_failure_evidence(self):
        from power_steering_state import FailureEvidence

        fe = FailureEvidence(consideration_id="test", reason="test reason")
        assert fe.consideration_id == "test"
        assert fe.reason == "test reason"

    def test_import_block_snapshot(self):
        from power_steering_state import BlockSnapshot

        bs = BlockSnapshot(
            block_number=1, timestamp="2024-01-01", transcript_index=0, transcript_length=10
        )
        assert bs.block_number == 1

    def test_import_power_steering_turn_state(self):
        from power_steering_state import PowerSteeringTurnState

        state = PowerSteeringTurnState(session_id="test")
        assert state.session_id == "test"
        assert state.turn_count == 0
        assert state.MAX_CONSECUTIVE_BLOCKS == 5
        assert state.WARNING_THRESHOLD == 2
        assert state.LOOP_DETECTION_THRESHOLD == 3

    def test_import_turn_state_manager(self):
        from power_steering_state import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            assert manager.session_id == "test"

    def test_import_delta_analyzer(self):
        from power_steering_state import DeltaAnalyzer

        da = DeltaAnalyzer()
        assert da is not None

    def test_import_delta_analysis_result(self):
        from power_steering_state import DeltaAnalysisResult

        dar = DeltaAnalysisResult(
            new_content_addresses_failures={},
            new_claims_detected=[],
            new_content_summary="test",
        )
        assert dar.new_content_summary == "test"

    def test_import_locking_available(self):
        from power_steering_state import LOCKING_AVAILABLE

        assert isinstance(LOCKING_AVAILABLE, bool)

    def test_all_exports(self):
        import power_steering_state

        expected_exports = [
            "FailureEvidence",
            "BlockSnapshot",
            "PowerSteeringTurnState",
            "TurnStateManager",
            "DeltaAnalyzer",
            "DeltaAnalysisResult",
            "LOCKING_AVAILABLE",
        ]
        for name in expected_exports:
            assert hasattr(power_steering_state, name), f"Missing export: {name}"


# ============================================================================
# Test 2: Constants Module
# ============================================================================


class TestConstants:
    """Verify constants are accessible and correct."""

    def test_max_consecutive_blocks(self):
        from power_steering_constants import MAX_CONSECUTIVE_BLOCKS

        assert MAX_CONSECUTIVE_BLOCKS == 5

    def test_warning_threshold(self):
        from power_steering_constants import WARNING_THRESHOLD

        assert WARNING_THRESHOLD == 2

    def test_loop_detection_threshold(self):
        from power_steering_constants import LOOP_DETECTION_THRESHOLD

        assert LOOP_DETECTION_THRESHOLD == 3

    def test_claim_keywords(self):
        from power_steering_constants import CLAIM_KEYWORDS

        assert isinstance(CLAIM_KEYWORDS, list)
        assert "completed" in CLAIM_KEYWORDS
        assert "workflow complete" in CLAIM_KEYWORDS

    def test_max_save_retries(self):
        from power_steering_constants import MAX_SAVE_RETRIES

        assert MAX_SAVE_RETRIES == 3

    def test_lock_timeout_seconds(self):
        from power_steering_constants import LOCK_TIMEOUT_SECONDS

        assert LOCK_TIMEOUT_SECONDS == 2.0

    def test_max_turn_count(self):
        from power_steering_constants import MAX_TURN_COUNT

        assert MAX_TURN_COUNT == 1000


# ============================================================================
# Test 3: Models Module (independent of I/O)
# ============================================================================


class TestModels:
    """Verify models work independently."""

    def test_failure_evidence_serialization(self):
        from power_steering_models import FailureEvidence

        fe = FailureEvidence(
            consideration_id="c1",
            reason="test reason",
            evidence_quote="some quote",
            was_claimed_complete=True,
        )
        d = fe.to_dict()
        fe2 = FailureEvidence.from_dict(d)
        assert fe2.consideration_id == "c1"
        assert fe2.reason == "test reason"
        assert fe2.evidence_quote == "some quote"
        assert fe2.was_claimed_complete is True

    def test_block_snapshot_serialization(self):
        from power_steering_models import BlockSnapshot, FailureEvidence

        snapshot = BlockSnapshot(
            block_number=2,
            timestamp="2024-01-01T00:00:00",
            transcript_index=10,
            transcript_length=50,
            failed_evidence=[
                FailureEvidence(consideration_id="c1", reason="r1"),
            ],
            user_claims_detected=["claim1"],
        )
        d = snapshot.to_dict()
        snapshot2 = BlockSnapshot.from_dict(d)
        assert snapshot2.block_number == 2
        assert len(snapshot2.failed_evidence) == 1
        assert snapshot2.failed_evidence[0].consideration_id == "c1"

    def test_power_steering_turn_state_serialization(self):
        from power_steering_models import PowerSteeringTurnState

        state = PowerSteeringTurnState(
            session_id="sess1",
            turn_count=5,
            consecutive_blocks=2,
            failure_fingerprints=["abc123"],
        )
        d = state.to_dict()
        state2 = PowerSteeringTurnState.from_dict(d, "sess1")
        assert state2.turn_count == 5
        assert state2.consecutive_blocks == 2
        assert state2.failure_fingerprints == ["abc123"]

    def test_fingerprint_generation(self):
        from power_steering_models import PowerSteeringTurnState

        state = PowerSteeringTurnState(session_id="test")
        fp1 = state.generate_failure_fingerprint(["c1", "c2"])
        fp2 = state.generate_failure_fingerprint(["c2", "c1"])
        assert fp1 == fp2  # Order independent
        assert len(fp1) == 16

    def test_loop_detection(self):
        from power_steering_models import PowerSteeringTurnState

        state = PowerSteeringTurnState(
            session_id="test",
            failure_fingerprints=["abc", "abc", "abc"],
        )
        assert state.detect_loop("abc") is True
        assert state.detect_loop("xyz") is False

    def test_blocks_until_auto_approve(self):
        from power_steering_models import PowerSteeringTurnState

        state = PowerSteeringTurnState(session_id="test", consecutive_blocks=3)
        assert state.blocks_until_auto_approve == 2

    def test_should_auto_approve(self):
        from power_steering_models import PowerSteeringTurnState

        state = PowerSteeringTurnState(session_id="test", consecutive_blocks=5)
        assert state.should_auto_approve() is True

        state2 = PowerSteeringTurnState(session_id="test", consecutive_blocks=4)
        assert state2.should_auto_approve() is False


# ============================================================================
# Test 4: Delta Analyzer Module
# ============================================================================


class TestDeltaAnalyzer:
    """Verify DeltaAnalyzer works independently."""

    def test_analyze_empty_delta(self):
        from power_steering_delta_analyzer import DeltaAnalyzer

        analyzer = DeltaAnalyzer()
        result = analyzer.analyze_delta([], [])
        assert result.new_content_summary == "0 new messages"
        assert result.new_claims_detected == []
        assert result.new_content_addresses_failures == {}

    def test_detect_claims(self):
        from power_steering_delta_analyzer import DeltaAnalyzer

        analyzer = DeltaAnalyzer()
        messages = [{"content": "I have completed the implementation"}]
        result = analyzer.analyze_delta(messages, [])
        assert len(result.new_claims_detected) > 0

    def test_extract_text_from_nested_content(self):
        from power_steering_delta_analyzer import DeltaAnalyzer

        analyzer = DeltaAnalyzer()
        messages = [{"content": {"content": [{"type": "text", "text": "Hello world"}]}}]
        text = analyzer._extract_all_text(messages)
        assert "Hello world" in text


# ============================================================================
# Test 5: State I/O Module
# ============================================================================


class TestStateIO:
    """Verify state I/O functions work independently."""

    def test_validate_state_negative_turn_count(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_io import validate_state

        log_messages = []
        state = PowerSteeringTurnState(session_id="test", turn_count=-1)
        validate_state(state, log=lambda msg, level="INFO": log_messages.append(msg))
        assert any("negative" in m for m in log_messages)

    def test_validate_state_high_turn_count(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_io import validate_state

        log_messages = []
        state = PowerSteeringTurnState(session_id="test", turn_count=1001)
        validate_state(state, log=lambda msg, level="INFO": log_messages.append(msg))
        assert any("1000" in m for m in log_messages)

    def test_load_nonexistent_state(self):
        from power_steering_state_io import load_state_from_file

        state = load_state_from_file(Path("/tmp/nonexistent/path.json"), "test-session")
        assert state.session_id == "test-session"
        assert state.turn_count == 0

    def test_save_and_load_state(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_io import load_state_from_file, save_state_to_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "state" / "turn_state.json"
            state = PowerSteeringTurnState(session_id="test", turn_count=42)
            save_state_to_file(state_file, state, _skip_locking=True)

            loaded = load_state_from_file(state_file, "test")
            assert loaded.turn_count == 42


# ============================================================================
# Test 6: State Manager Module
# ============================================================================


class TestStateManager:
    """Verify TurnStateManager delegates correctly."""

    def test_manager_load_and_save(self):
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir, session_id="test-session")
            state = manager.load_state()
            assert state.turn_count == 0

            state.turn_count = 10
            manager.save_state(state)

            state2 = manager.load_state()
            assert state2.turn_count == 10

    def test_increment_turn(self):
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir, session_id="test-session")
            state = manager.load_state()
            state = manager.increment_turn(state)
            assert state.turn_count == 1

    def test_atomic_increment(self):
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir, session_id="test-session")
            state = manager.atomic_increment_turn()
            assert state.turn_count == 1

            state = manager.atomic_increment_turn()
            assert state.turn_count == 2

    def test_record_block_with_evidence(self):
        from power_steering_models import FailureEvidence
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            state = manager.load_state()
            evidence = [FailureEvidence(consideration_id="c1", reason="failed")]
            state = manager.record_block_with_evidence(state, evidence, 100)
            assert state.consecutive_blocks == 1
            assert len(state.block_history) == 1

    def test_record_approval(self):
        from power_steering_models import FailureEvidence
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            state = manager.load_state()
            evidence = [FailureEvidence(consideration_id="c1", reason="failed")]
            state = manager.record_block_with_evidence(state, evidence, 100)
            assert state.consecutive_blocks == 1

            state = manager.record_approval(state)
            assert state.consecutive_blocks == 0
            assert state.block_history == []

    def test_should_auto_approve(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            state = PowerSteeringTurnState(session_id="test", consecutive_blocks=5)
            should_approve, reason, msg = manager.should_auto_approve(state)
            assert should_approve is True

    def test_generate_power_steering_message(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            state = PowerSteeringTurnState(session_id="test", turn_count=5, consecutive_blocks=0)
            msg = manager.generate_power_steering_message(state)
            assert "Turn 5" in msg

    def test_get_delta_transcript_range(self):
        from power_steering_models import PowerSteeringTurnState
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir)
            state = PowerSteeringTurnState(session_id="test", last_analyzed_transcript_index=10)
            start, end = manager.get_delta_transcript_range(state, 50)
            assert start == 10
            assert end == 50


# ============================================================================
# Test 7: Cross-Module Integration
# ============================================================================


class TestCrossModuleIntegration:
    """Verify modules integrate correctly."""

    def test_constants_used_by_models(self):
        """Constants module values are reflected in model class vars."""
        from power_steering_constants import MAX_CONSECUTIVE_BLOCKS
        from power_steering_models import PowerSteeringTurnState

        assert PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS == MAX_CONSECUTIVE_BLOCKS

    def test_delta_analyzer_uses_models(self):
        """DeltaAnalyzer accepts model instances correctly."""
        from power_steering_delta_analyzer import DeltaAnalyzer
        from power_steering_models import FailureEvidence

        analyzer = DeltaAnalyzer()
        failures = [FailureEvidence(consideration_id="test-c1", reason="test")]
        result = analyzer.analyze_delta([], failures)
        assert result.new_content_addresses_failures == {}

    def test_state_manager_uses_state_io(self):
        """TurnStateManager correctly delegates to state_io for persistence."""
        from power_steering_state_manager import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            manager = TurnStateManager(project_root=tmp_dir, session_id="integration-test")

            # Save and load roundtrip
            state = manager.load_state()
            state.turn_count = 99
            state.consecutive_blocks = 3
            manager.save_state(state)

            # Verify via raw file read
            state_file = manager.get_state_file_path()
            raw_data = json.loads(state_file.read_text())
            assert raw_data["turn_count"] == 99
            assert raw_data["consecutive_blocks"] == 3

    def test_backward_compat_patch_target(self):
        """Test that patching power_steering_state.get_shared_runtime_dir works."""
        from power_steering_state import TurnStateManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_runtime = Path(tmp_dir) / "custom" / "runtime"
            custom_runtime.mkdir(parents=True)

            with patch(
                "power_steering_state.get_shared_runtime_dir",
                return_value=str(custom_runtime),
            ):
                manager = TurnStateManager(project_root="/some/path")
                state_file = manager.get_state_file_path()
                assert str(custom_runtime) in str(state_file)
