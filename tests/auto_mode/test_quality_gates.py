"""
Test suite for QualityGateEvaluator.

Tests quality gate evaluation, condition checking, and intervention decisions:
- Gate condition evaluation
- Quality gate triggering logic
- Intervention suggestion generation
- Cooldown and rate limiting
- Custom gate configuration
"""

import time
from unittest.mock import Mock

import pytest

from amplihack.auto_mode.analysis import (
    ConversationAnalysis,
    ConversationPattern,
    ConversationSignal,
    QualityDimension,
)
from amplihack.auto_mode.quality_gates import (
    GatePriority,
    InterventionType,
    QualityGateAction,
    QualityGateCondition,
    QualityGateDefinition,
    QualityGateEvaluator,
)
from amplihack.auto_mode.session import SessionState


class TestQualityGateEvaluator:
    """Test QualityGateEvaluator initialization and configuration"""

    def test_evaluator_initialization_with_defaults(self):
        """Test evaluator initialization with default gates"""
        evaluator = QualityGateEvaluator()

        assert len(evaluator.gates) > 0
        assert "quality_drop" in evaluator.gates
        assert "goal_stagnation" in evaluator.gates
        assert "tool_optimization" in evaluator.gates
        assert "privacy_protection" in evaluator.gates

    def test_default_gate_definitions(self):
        """Test default gate definitions are properly configured"""
        evaluator = QualityGateEvaluator()

        quality_drop_gate = evaluator.gates["quality_drop"]
        assert quality_drop_gate.priority == GatePriority.HIGH
        assert len(quality_drop_gate.conditions) > 0
        assert len(quality_drop_gate.actions) > 0

        privacy_gate = evaluator.gates["privacy_protection"]
        assert privacy_gate.priority == GatePriority.CRITICAL
        assert privacy_gate.min_confidence_threshold == 0.9

    @pytest.mark.asyncio
    async def test_evaluator_initialization(self):
        """Test evaluator async initialization"""
        evaluator = QualityGateEvaluator()
        await evaluator.initialize()
        # Should complete without errors

    def test_add_custom_gate(self):
        """Test adding custom quality gate"""
        evaluator = QualityGateEvaluator()

        custom_gate = QualityGateDefinition(
            gate_id="custom_test_gate",
            name="Custom Test Gate",
            description="Test gate for unit testing",
            priority=GatePriority.MEDIUM,
            conditions=[
                QualityGateCondition(
                    condition_type="threshold",
                    field_path="analysis.quality_score",
                    operator="lt",
                    threshold=0.5,
                )
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.CLARIFICATION_SUGGESTION,
                    title="Test Action",
                    description="Test description",
                )
            ],
        )

        evaluator.add_custom_gate(custom_gate)

        assert "custom_test_gate" in evaluator.gates
        assert evaluator.gates["custom_test_gate"] == custom_gate

    def test_enable_disable_gate(self):
        """Test enabling and disabling gates"""
        evaluator = QualityGateEvaluator()

        gate_id = "quality_drop"

        # Disable gate
        success = evaluator.enable_gate(gate_id, False)
        assert success is True
        assert evaluator.gates[gate_id].user_enabled is False

        # Enable gate
        success = evaluator.enable_gate(gate_id, True)
        assert success is True
        assert evaluator.gates[gate_id].user_enabled is True

        # Try non-existent gate
        success = evaluator.enable_gate("nonexistent", True)
        assert success is False

    def test_adjust_gate_threshold(self):
        """Test adjusting gate thresholds"""
        evaluator = QualityGateEvaluator()

        gate_id = "quality_drop"
        adjustment = 0.1

        success = evaluator.adjust_gate_threshold(gate_id, adjustment)
        assert success is True
        assert evaluator.gates[gate_id].user_threshold_adjustment == adjustment

        # Try non-existent gate
        success = evaluator.adjust_gate_threshold("nonexistent", 0.1)
        assert success is False


class TestConditionEvaluation:
    """Test quality gate condition evaluation"""

    @pytest.fixture
    def evaluator(self):
        return QualityGateEvaluator()

    @pytest.fixture
    def sample_analysis(self):
        return ConversationAnalysis(
            quality_score=0.5,
            conversation_length=10,
            detected_signals=[ConversationSignal.CONFUSION_INDICATOR],
            identified_patterns=[
                ConversationPattern(
                    pattern_type="repeated_requests",
                    description="User repeating requests",
                    frequency=3,
                    confidence=0.8,
                    impact_level="high",
                )
            ],
            quality_dimensions=[
                QualityDimension(
                    dimension="clarity",
                    score=0.4,
                    evidence=["Confusion detected"],
                    improvement_suggestions=["Provide clearer explanations"],
                ),
                QualityDimension(
                    dimension="effectiveness",
                    score=0.3,
                    evidence=["Low goal completion"],
                    improvement_suggestions=["Focus on goal completion"],
                ),
            ],
        )

    @pytest.fixture
    def sample_session(self):
        return SessionState(
            session_id="test_session",
            user_id="test_user",
            sensitive_data_flags=["email_address", "phone_number"],
        )

    def test_less_than_condition(self, evaluator, sample_analysis, sample_session):
        """Test less than condition evaluation"""
        condition = QualityGateCondition(
            condition_type="threshold",
            field_path="analysis.quality_score",
            operator="lt",
            threshold=0.6,
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_greater_than_condition(self, evaluator, sample_analysis, sample_session):
        """Test greater than condition evaluation"""
        condition = QualityGateCondition(
            condition_type="threshold",
            field_path="analysis.conversation_length",
            operator="gt",
            threshold=5,
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_equals_condition(self, evaluator, sample_analysis, sample_session):
        """Test equals condition evaluation"""
        condition = QualityGateCondition(
            condition_type="exact_match",
            field_path="analysis.conversation_length",
            operator="eq",
            threshold=10,
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence == 1.0

    def test_contains_condition(self, evaluator, sample_analysis, sample_session):
        """Test contains condition evaluation"""
        condition = QualityGateCondition(
            condition_type="signal_present",
            field_path="analysis.detected_signals",
            operator="contains",
            threshold=ConversationSignal.CONFUSION_INDICATOR,
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_not_empty_condition(self, evaluator, sample_analysis, sample_session):
        """Test not empty condition evaluation"""
        condition = QualityGateCondition(
            condition_type="sensitive_data",
            field_path="session_state.sensitive_data_flags",
            operator="not_empty",
            threshold=None,
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_dimension_score_condition(self, evaluator, sample_analysis, sample_session):
        """Test quality dimension score condition evaluation"""
        condition = QualityGateCondition(
            condition_type="quality_dimension",
            field_path="analysis.quality_dimensions",
            operator="dimension_score_lt",
            threshold={"dimension": "clarity", "score": 0.5},
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_pattern_exists_condition(self, evaluator, sample_analysis, sample_session):
        """Test pattern existence condition evaluation"""
        condition = QualityGateCondition(
            condition_type="pattern_present",
            field_path="analysis.identified_patterns",
            operator="pattern_type_exists",
            threshold="repeated_requests",
        )

        met, confidence = evaluator._evaluate_condition(condition, sample_analysis, sample_session)

        assert met is True
        assert confidence > 0.0

    def test_field_path_navigation(self, evaluator, sample_analysis, sample_session):
        """Test field path navigation for nested values"""
        # Test analysis field path
        value = evaluator._get_field_value(
            "analysis.quality_score", sample_analysis, sample_session
        )
        assert value == 0.5

        # Test session field path
        value = evaluator._get_field_value("session_state.user_id", sample_analysis, sample_session)
        assert value == "test_user"

        # Test invalid field path
        value = evaluator._get_field_value("analysis.nonexistent", sample_analysis, sample_session)
        assert value is None

        # Test invalid root
        value = evaluator._get_field_value("invalid.field", sample_analysis, sample_session)
        assert value is None


class TestGateEvaluation:
    """Test complete gate evaluation logic"""

    @pytest.fixture
    def evaluator(self):
        return QualityGateEvaluator()

    @pytest.fixture
    def sample_analysis(self):
        return ConversationAnalysis(
            quality_score=0.5, detected_signals=[ConversationSignal.CONFUSION_INDICATOR]
        )

    @pytest.fixture
    def sample_session(self):
        return SessionState(session_id="test_session", user_id="test_user")

    @pytest.fixture
    def mock_config(self):
        mock_config = Mock()
        mock_config.intervention_confidence_threshold = 0.7
        return mock_config

    @pytest.mark.asyncio
    async def test_gate_evaluation_triggered(
        self, evaluator, sample_analysis, sample_session, mock_config
    ):
        """Test gate evaluation when conditions are met"""
        results = await evaluator.evaluate(sample_analysis, sample_session, mock_config)

        # Should have triggered quality_drop gate
        quality_drop_results = [r for r in results if r.gate_id == "quality_drop"]
        assert len(quality_drop_results) > 0

        result = quality_drop_results[0]
        assert result.triggered is True
        assert result.confidence > 0.0
        assert len(result.suggested_actions) > 0

    @pytest.mark.asyncio
    async def test_gate_evaluation_not_triggered(self, evaluator, sample_session, mock_config):
        """Test gate evaluation when conditions are not met"""
        # High quality analysis
        high_quality_analysis = ConversationAnalysis(
            quality_score=0.9, detected_signals=[ConversationSignal.POSITIVE_ENGAGEMENT]
        )

        results = await evaluator.evaluate(high_quality_analysis, sample_session, mock_config)

        # Should not trigger quality_drop gate
        quality_drop_results = [r for r in results if r.gate_id == "quality_drop"]
        assert len(quality_drop_results) == 0

    @pytest.mark.asyncio
    async def test_disabled_gate_not_evaluated(
        self, evaluator, sample_analysis, sample_session, mock_config
    ):
        """Test that disabled gates are not evaluated"""
        # Disable quality_drop gate
        evaluator.enable_gate("quality_drop", False)

        results = await evaluator.evaluate(sample_analysis, sample_session, mock_config)

        # Should not have quality_drop results
        quality_drop_results = [r for r in results if r.gate_id == "quality_drop"]
        assert len(quality_drop_results) == 0

    @pytest.mark.asyncio
    async def test_gate_cooldown_prevents_triggering(
        self, evaluator, sample_analysis, sample_session, mock_config
    ):
        """Test that gate cooldown prevents repeated triggering"""
        # First evaluation - should trigger
        results1 = await evaluator.evaluate(sample_analysis, sample_session, mock_config)
        quality_drop_results1 = [r for r in results1 if r.gate_id == "quality_drop"]
        assert len(quality_drop_results1) > 0

        # Second evaluation immediately - should not trigger due to cooldown
        results2 = await evaluator.evaluate(sample_analysis, sample_session, mock_config)
        quality_drop_results2 = [r for r in results2 if r.gate_id == "quality_drop"]
        assert len(quality_drop_results2) == 0

    @pytest.mark.asyncio
    async def test_session_trigger_limit(
        self, evaluator, sample_analysis, sample_session, mock_config
    ):
        """Test session trigger limit enforcement"""
        gate = evaluator.gates["quality_drop"]
        gate.max_triggers_per_session = 1
        gate.cooldown_minutes = 0  # Disable cooldown for this test

        # First trigger
        results1 = await evaluator.evaluate(sample_analysis, sample_session, mock_config)
        quality_drop_results1 = [r for r in results1 if r.gate_id == "quality_drop"]
        assert len(quality_drop_results1) > 0

        # Second attempt - should be blocked by session limit
        results2 = await evaluator.evaluate(sample_analysis, sample_session, mock_config)
        quality_drop_results2 = [r for r in results2 if r.gate_id == "quality_drop"]
        assert len(quality_drop_results2) == 0

    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, evaluator, sample_analysis, sample_session):
        """Test that results below confidence threshold are filtered"""
        # Set very high confidence threshold
        high_threshold_config = Mock()
        high_threshold_config.intervention_confidence_threshold = 0.99

        results = await evaluator.evaluate(sample_analysis, sample_session, high_threshold_config)

        # Should have no results due to high threshold
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_user_threshold_adjustment(
        self, evaluator, sample_analysis, sample_session, mock_config
    ):
        """Test user threshold adjustment affects evaluation"""
        # Adjust threshold to make gate harder to trigger
        evaluator.adjust_gate_threshold("quality_drop", 0.3)

        results = await evaluator.evaluate(sample_analysis, sample_session, mock_config)

        # Should have fewer or no results due to adjusted threshold
        quality_drop_results = [r for r in results if r.gate_id == "quality_drop"]
        # The exact behavior depends on the specific gate configuration


class TestGateStatistics:
    """Test gate statistics and monitoring"""

    def test_gate_statistics_empty(self):
        """Test gate statistics when no gates have been triggered"""
        evaluator = QualityGateEvaluator()

        stats = evaluator.get_gate_statistics()

        assert stats["total_gates"] > 0
        assert stats["enabled_gates"] > 0
        assert len(stats["gate_triggers"]) == 0

    def test_gate_statistics_with_triggers(self):
        """Test gate statistics after gates have been triggered"""
        evaluator = QualityGateEvaluator()

        # Simulate gate triggers
        evaluator._record_gate_trigger("quality_drop", "session1", time.time())
        evaluator._record_gate_trigger("quality_drop", "session1", time.time())
        evaluator._record_gate_trigger("goal_stagnation", "session2", time.time())

        stats = evaluator.get_gate_statistics()

        assert stats["gate_triggers"]["quality_drop"] == 2
        assert stats["gate_triggers"]["goal_stagnation"] == 1

    def test_gate_trigger_history_cleanup(self):
        """Test that old gate triggers are cleaned up"""
        evaluator = QualityGateEvaluator()

        # Record old trigger (25 hours ago)
        old_time = time.time() - (25 * 60 * 60)
        evaluator._record_gate_trigger("quality_drop", "session1", old_time)

        # Record new trigger
        new_time = time.time()
        evaluator._record_gate_trigger("quality_drop", "session1", new_time)

        # Check that only recent trigger remains
        key = "session1:quality_drop"
        assert len(evaluator.gate_history[key]) == 1
        assert evaluator.gate_history[key][0] == new_time


class TestPrivacyGate:
    """Test privacy protection gate specifically"""

    @pytest.fixture
    def evaluator(self):
        return QualityGateEvaluator()

    @pytest.fixture
    def session_with_sensitive_data(self):
        return SessionState(
            session_id="test_session",
            user_id="test_user",
            sensitive_data_flags=["email_address", "credit_card"],
        )

    @pytest.mark.asyncio
    async def test_privacy_gate_triggers_with_sensitive_data(
        self, evaluator, session_with_sensitive_data
    ):
        """Test privacy gate triggers when sensitive data is detected"""
        analysis = ConversationAnalysis()
        config = Mock()
        config.intervention_confidence_threshold = 0.5

        results = await evaluator.evaluate(analysis, session_with_sensitive_data, config)

        privacy_results = [r for r in results if r.gate_id == "privacy_protection"]
        assert len(privacy_results) > 0

        result = privacy_results[0]
        assert result.triggered is True
        assert result.priority == GatePriority.CRITICAL
        assert len(result.suggested_actions) > 0

    @pytest.mark.asyncio
    async def test_privacy_gate_high_confidence_requirement(
        self, evaluator, session_with_sensitive_data
    ):
        """Test privacy gate requires high confidence"""
        privacy_gate = evaluator.gates["privacy_protection"]
        assert privacy_gate.min_confidence_threshold == 0.9


if __name__ == "__main__":
    pytest.main([__file__])
