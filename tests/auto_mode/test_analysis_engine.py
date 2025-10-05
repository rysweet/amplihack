"""
Test suite for AnalysisEngine.

Tests conversation analysis functionality including:
- Signal detection and pattern recognition
- Quality assessment across multiple dimensions
- Improvement opportunity identification
- User expertise and domain assessment
"""

import pytest
import pytest_asyncio
import time
from unittest.mock import Mock, patch

from amplihack.auto_mode.analysis import (
    AnalysisEngine,
    ConversationAnalysis,
    ConversationSignal,
    ConversationPattern,
    QualityDimension,
    SignalDetector,
    PatternAnalyzer,
    QualityAssessor
)


class TestSignalDetector:
    """Test conversation signal detection"""

    @pytest.fixture
    def signal_detector(self):
        return SignalDetector()

    def test_positive_engagement_detection(self, signal_detector):
        """Test detection of positive engagement signals"""
        text = "Thank you so much! That's exactly what I needed. This works perfectly."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.POSITIVE_ENGAGEMENT in signals

    def test_confusion_indicator_detection(self, signal_detector):
        """Test detection of confusion indicators"""
        text = "I'm confused about this. I don't understand what you mean."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.CONFUSION_INDICATOR in signals

    def test_frustration_signal_detection(self, signal_detector):
        """Test detection of frustration signals"""
        text = "This is so frustrating! Nothing works and I've tried everything."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.FRUSTRATION_SIGNAL in signals

    def test_clarification_request_detection(self, signal_detector):
        """Test detection of clarification requests"""
        text = "Can you clarify what you mean? Show me a specific example please."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.CLARIFICATION_REQUEST in signals

    def test_success_confirmation_detection(self, signal_detector):
        """Test detection of success confirmations"""
        text = "It works now! The problem is resolved and everything is working perfectly."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.SUCCESS_CONFIRMATION in signals

    def test_mixed_signals_detection(self, signal_detector):
        """Test detection of multiple signals in same text"""
        text = "Thank you for the help, but I'm still confused about one part. Can you clarify?"
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.POSITIVE_ENGAGEMENT in signals
        assert ConversationSignal.CONFUSION_INDICATOR in signals
        assert ConversationSignal.CLARIFICATION_REQUEST in signals

    def test_no_signals_detection(self, signal_detector):
        """Test when no signals are detected"""
        text = "The weather is nice today. I went to the store."
        signals = signal_detector.detect_signals(text)

        assert len(signals) == 0

    def test_case_insensitive_detection(self, signal_detector):
        """Test that signal detection is case insensitive"""
        text = "THANK YOU! this is EXACTLY what I needed."
        signals = signal_detector.detect_signals(text)

        assert ConversationSignal.POSITIVE_ENGAGEMENT in signals


class TestPatternAnalyzer:
    """Test conversation pattern analysis"""

    @pytest.fixture
    def pattern_analyzer(self):
        return PatternAnalyzer()

    def test_high_question_frequency_pattern(self, pattern_analyzer):
        """Test detection of high question frequency pattern"""
        messages = [
            {"role": "user", "content": "How do I do this?"},
            {"role": "assistant", "content": "You can do it this way..."},
            {"role": "user", "content": "What about this other thing?"},
            {"role": "assistant", "content": "For that, you should..."},
            {"role": "user", "content": "Why doesn't this work?"},
            {"role": "assistant", "content": "The reason is..."}
        ]

        conversation_context = {"messages": messages}
        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should detect high question frequency
        question_patterns = [p for p in patterns if p.pattern_type == "high_question_frequency"]
        assert len(question_patterns) > 0
        assert question_patterns[0].impact_level == "medium"

    def test_repeated_requests_pattern(self, pattern_analyzer):
        """Test detection of repeated similar requests"""
        messages = [
            {"role": "user", "content": "How do I create a file?"},
            {"role": "assistant", "content": "Use the touch command..."},
            {"role": "user", "content": "How can I create a new file?"},
            {"role": "assistant", "content": "You can use touch..."},
            {"role": "user", "content": "What's the way to make a file?"},
            {"role": "assistant", "content": "The touch command..."}
        ]

        conversation_context = {"messages": messages}
        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should detect repeated requests
        repeated_patterns = [p for p in patterns if p.pattern_type == "repeated_requests"]
        assert len(repeated_patterns) > 0
        assert repeated_patterns[0].impact_level == "high"

    def test_tool_overuse_pattern(self, pattern_analyzer):
        """Test detection of tool overuse pattern"""
        tool_usage = [
            {"tool_name": "bash", "timestamp": time.time()},
            {"tool_name": "bash", "timestamp": time.time()},
            {"tool_name": "bash", "timestamp": time.time()},
            {"tool_name": "bash", "timestamp": time.time()},
            {"tool_name": "edit", "timestamp": time.time()}
        ]

        conversation_context = {
            "messages": [],
            "tool_usage": tool_usage
        }

        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should detect bash tool overuse
        overuse_patterns = [p for p in patterns if p.pattern_type == "tool_overuse"]
        assert len(overuse_patterns) > 0
        assert overuse_patterns[0].metadata['tool_name'] == "bash"

    def test_low_goal_completion_pattern(self, pattern_analyzer):
        """Test detection of low goal completion pattern"""
        goals = [
            {"id": "goal1", "status": "pending"},
            {"id": "goal2", "status": "pending"},
            {"id": "goal3", "status": "completed"},
            {"id": "goal4", "status": "pending"},
            {"id": "goal5", "status": "pending"}
        ]

        conversation_context = {
            "messages": [],
            "goals": goals
        }

        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should detect low goal completion
        goal_patterns = [p for p in patterns if p.pattern_type == "low_goal_completion"]
        assert len(goal_patterns) > 0
        assert goal_patterns[0].impact_level == "high"

    def test_learning_focused_pattern(self, pattern_analyzer):
        """Test detection of learning-focused pattern"""
        messages = [
            {"role": "user", "content": "Can you explain how this works?"},
            {"role": "assistant", "content": "Sure, let me explain..."},
            {"role": "user", "content": "I want to understand the underlying concepts"},
            {"role": "assistant", "content": "The concepts are..."},
            {"role": "user", "content": "Why does it work this way?"},
            {"role": "assistant", "content": "The reason is..."}
        ]

        conversation_context = {"messages": messages}
        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should detect learning-focused pattern
        learning_patterns = [p for p in patterns if p.pattern_type == "learning_focused"]
        assert len(learning_patterns) > 0
        assert learning_patterns[0].impact_level == "medium"

    def test_no_patterns_detected(self, pattern_analyzer):
        """Test when no patterns are detected"""
        conversation_context = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        }

        patterns = pattern_analyzer.analyze_patterns(conversation_context, [])

        # Should not detect any significant patterns
        assert len(patterns) == 0

    def test_similarity_calculation(self, pattern_analyzer):
        """Test content similarity calculation"""
        text1 = "How do I create a file?"
        text2 = "How can I create a new file?"
        text3 = "What's the weather like today?"

        similarity_12 = pattern_analyzer._calculate_similarity(text1, text2)
        similarity_13 = pattern_analyzer._calculate_similarity(text1, text3)

        assert similarity_12 > similarity_13
        assert 0.0 <= similarity_12 <= 1.0
        assert 0.0 <= similarity_13 <= 1.0


class TestQualityAssessor:
    """Test quality assessment functionality"""

    @pytest.fixture
    def quality_assessor(self):
        return QualityAssessor()

    def test_assess_quality_with_good_indicators(self, quality_assessor):
        """Test quality assessment with positive indicators"""
        conversation_context = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
                {"role": "user", "content": "Thank you, that works perfectly!"}
            ],
            "goals": [
                {"id": "goal1", "status": "completed"},
                {"id": "goal2", "status": "completed"}
            ]
        }

        signals = [ConversationSignal.POSITIVE_ENGAGEMENT, ConversationSignal.SUCCESS_CONFIRMATION]
        patterns = []

        overall_score, dimensions = quality_assessor.assess_quality(
            conversation_context, signals, patterns
        )

        assert 0.0 <= overall_score <= 1.0
        assert overall_score > 0.5  # Should be good with positive signals
        assert len(dimensions) == 6  # All quality dimensions

    def test_assess_quality_with_negative_indicators(self, quality_assessor):
        """Test quality assessment with negative indicators"""
        conversation_context = {
            "messages": [
                {"role": "user", "content": "I'm confused"},
                {"role": "assistant", "content": "Let me help..."},
                {"role": "user", "content": "This is frustrating"}
            ],
            "goals": [
                {"id": "goal1", "status": "pending"},
                {"id": "goal2", "status": "pending"}
            ]
        }

        signals = [ConversationSignal.CONFUSION_INDICATOR, ConversationSignal.FRUSTRATION_SIGNAL]
        patterns = [
            ConversationPattern(
                pattern_type="repeated_requests",
                description="User repeating requests",
                frequency=3,
                confidence=0.8,
                impact_level="high"
            )
        ]

        overall_score, dimensions = quality_assessor.assess_quality(
            conversation_context, signals, patterns
        )

        assert 0.0 <= overall_score <= 1.0
        assert overall_score < 0.7  # Should be lower with negative indicators

    def test_clarity_assessment(self, quality_assessor):
        """Test clarity dimension assessment"""
        context = {"messages": []}
        signals = [ConversationSignal.CONFUSION_INDICATOR]
        patterns = [
            ConversationPattern(
                pattern_type="repeated_requests",
                description="Repeated requests",
                frequency=2,
                confidence=0.8,
                impact_level="medium"
            )
        ]

        clarity = quality_assessor._assess_clarity(context, signals, patterns)

        assert clarity.dimension == "clarity"
        assert clarity.score < 0.7  # Should be low due to confusion
        assert len(clarity.evidence) > 0
        assert len(clarity.improvement_suggestions) > 0

    def test_effectiveness_assessment(self, quality_assessor):
        """Test effectiveness dimension assessment"""
        context = {
            "goals": [
                {"id": "goal1", "status": "completed"},
                {"id": "goal2", "status": "completed"},
                {"id": "goal3", "status": "pending"}
            ]
        }
        signals = [ConversationSignal.SUCCESS_CONFIRMATION]
        patterns = []

        effectiveness = quality_assessor._assess_effectiveness(context, signals, patterns)

        assert effectiveness.dimension == "effectiveness"
        assert effectiveness.score > 0.6  # Good completion rate
        assert "Goal completion rate" in effectiveness.evidence[0]

    def test_engagement_assessment(self, quality_assessor):
        """Test engagement dimension assessment"""
        context = {
            "messages": [
                {"role": "user", "content": "This is a detailed message with lots of content about my specific problem and what I'm trying to achieve"},
                {"role": "assistant", "content": "Here's a detailed response..."},
                {"role": "user", "content": "Great explanation! I appreciate the thoroughness"}
            ]
        }
        signals = [ConversationSignal.POSITIVE_ENGAGEMENT]
        patterns = [
            ConversationPattern(
                pattern_type="learning_focused",
                description="User is learning",
                frequency=1,
                confidence=0.8,
                impact_level="medium"
            )
        ]

        engagement = quality_assessor._assess_engagement(context, signals, patterns)

        assert engagement.dimension == "engagement"
        assert engagement.score > 0.6  # Good engagement indicators

    def test_satisfaction_assessment(self, quality_assessor):
        """Test satisfaction dimension assessment"""
        context = {}
        positive_signals = [ConversationSignal.POSITIVE_ENGAGEMENT, ConversationSignal.SUCCESS_CONFIRMATION]
        negative_signals = [ConversationSignal.FRUSTRATION_SIGNAL]
        patterns = []

        # Test positive satisfaction
        satisfaction_positive = quality_assessor._assess_satisfaction(context, positive_signals, patterns)
        assert satisfaction_positive.score > 0.6

        # Test negative satisfaction
        satisfaction_negative = quality_assessor._assess_satisfaction(context, negative_signals, patterns)
        assert satisfaction_negative.score < 0.6


class TestAnalysisEngine:
    """Test the main AnalysisEngine integration"""

    @pytest_asyncio.fixture
    async def analysis_engine(self):
        engine = AnalysisEngine()
        await engine.initialize()
        try:
            yield engine
        finally:
            # Cleanup if needed
            pass

    @pytest.mark.asyncio
    async def test_analyze_conversation_basic(self, analysis_engine):
        """Test basic conversation analysis"""
        conversation_context = {
            "messages": [
                {"role": "user", "content": "Hello, can you help me?"},
                {"role": "assistant", "content": "Of course! What do you need help with?"},
                {"role": "user", "content": "Thank you! That's exactly what I needed."}
            ],
            "goals": [
                {"id": "goal1", "status": "completed"}
            ]
        }

        session_history = []

        analysis = await analysis_engine.analyze_conversation(conversation_context, session_history)

        assert isinstance(analysis, ConversationAnalysis)
        assert analysis.conversation_length == 3
        assert analysis.user_message_count == 2
        assert analysis.assistant_message_count == 1
        assert 0.0 <= analysis.quality_score <= 1.0
        assert len(analysis.quality_dimensions) == 6

    @pytest.mark.asyncio
    async def test_analyze_conversation_with_patterns(self, analysis_engine):
        """Test conversation analysis with pattern detection"""
        conversation_context = {
            "messages": [
                {"role": "user", "content": "How do I create a file?"},
                {"role": "assistant", "content": "Use touch command..."},
                {"role": "user", "content": "How can I create a file?"},
                {"role": "assistant", "content": "You can use touch..."},
                {"role": "user", "content": "What's the way to make a file?"}
            ]
        }

        analysis = await analysis_engine.analyze_conversation(conversation_context, [])

        # Should detect patterns
        assert len(analysis.identified_patterns) > 0

        # Should have improvement opportunities
        assert len(analysis.improvement_opportunities) > 0

    @pytest.mark.asyncio
    async def test_user_expertise_assessment(self, analysis_engine):
        """Test user expertise assessment"""
        # Beginner context
        beginner_context = {
            "messages": [
                {"role": "user", "content": "How do I start? What is a function?"},
                {"role": "user", "content": "Can you help me understand the basics?"}
            ]
        }

        beginner_analysis = await analysis_engine.analyze_conversation(beginner_context, [])
        assert beginner_analysis.user_expertise_assessment == "beginner"

        # Advanced context
        advanced_context = {
            "messages": [
                {"role": "user", "content": "I need to implement a complex algorithm using asynchronous programming"},
                {"role": "user", "content": "The API endpoints need proper authentication middleware"}
            ]
        }

        advanced_analysis = await analysis_engine.analyze_conversation(advanced_context, [])
        assert advanced_analysis.user_expertise_assessment == "advanced"

    @pytest.mark.asyncio
    async def test_domain_context_identification(self, analysis_engine):
        """Test domain context identification"""
        # Programming context
        programming_context = {
            "messages": [
                {"role": "user", "content": "I need help with my Python code and functions"},
                {"role": "user", "content": "The class inheritance is not working properly"}
            ]
        }

        programming_analysis = await analysis_engine.analyze_conversation(programming_context, [])
        assert programming_analysis.domain_context == "programming"

        # Web development context
        web_context = {
            "messages": [
                {"role": "user", "content": "My HTML and CSS are not rendering correctly"},
                {"role": "user", "content": "The JavaScript frontend is having issues"}
            ]
        }

        web_analysis = await analysis_engine.analyze_conversation(web_context, [])
        assert web_analysis.domain_context == "web_development"

    @pytest.mark.asyncio
    async def test_activity_level_calculation(self, analysis_engine):
        """Test conversation activity level calculation"""
        # High activity context
        high_activity_context = {
            "messages": [f"Message {i}" for i in range(15)]  # Many messages
        }

        high_activity_analysis = await analysis_engine.analyze_conversation(high_activity_context, [])
        assert high_activity_analysis.conversation_activity_level > 1.0

        # Low activity context
        low_activity_context = {
            "messages": ["Hello", "Hi"]  # Few messages
        }

        low_activity_analysis = await analysis_engine.analyze_conversation(low_activity_context, [])
        assert low_activity_analysis.conversation_activity_level == 1.0

    @pytest.mark.asyncio
    async def test_satisfaction_signals_extraction(self, analysis_engine):
        """Test satisfaction signals extraction"""
        positive_context = {
            "messages": [
                {"role": "user", "content": "Thank you so much! This works perfectly!"}
            ]
        }

        positive_analysis = await analysis_engine.analyze_conversation(positive_context, [])
        assert positive_analysis.satisfaction_signals['overall_sentiment'] == 'positive'
        assert positive_analysis.satisfaction_signals['confidence'] > 0.5

        negative_context = {
            "messages": [
                {"role": "user", "content": "This is so frustrating and confusing!"}
            ]
        }

        negative_analysis = await analysis_engine.analyze_conversation(negative_context, [])
        assert negative_analysis.satisfaction_signals['overall_sentiment'] == 'negative'
        assert negative_analysis.satisfaction_signals['confidence'] > 0.5

    @pytest.mark.asyncio
    async def test_improvement_opportunities_generation(self, analysis_engine):
        """Test improvement opportunities generation"""
        poor_quality_context = {
            "messages": [
                {"role": "user", "content": "I'm confused and frustrated"},
                {"role": "user", "content": "I don't understand anything"}
            ]
        }

        analysis = await analysis_engine.analyze_conversation(poor_quality_context, [])

        # Should generate improvement opportunities for poor quality
        assert len(analysis.improvement_opportunities) > 0

        # Check that opportunities have required fields
        for opportunity in analysis.improvement_opportunities:
            assert 'area' in opportunity
            assert 'description' in opportunity
            assert 'priority' in opportunity
            assert 'confidence' in opportunity


if __name__ == "__main__":
    pytest.main([__file__])