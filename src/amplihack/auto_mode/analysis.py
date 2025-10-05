"""
Conversation Analysis Engine for Auto-Mode

Analyzes conversation quality, patterns, and improvement opportunities.
Provides quantitative and qualitative assessment of conversation effectiveness.
"""

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class ConversationSignal(Enum):
    """Types of signals detected in conversations"""

    POSITIVE_ENGAGEMENT = "positive_engagement"
    CONFUSION_INDICATOR = "confusion_indicator"
    FRUSTRATION_SIGNAL = "frustration_signal"
    SUCCESS_CONFIRMATION = "success_confirmation"
    CLARIFICATION_REQUEST = "clarification_request"
    GOAL_ACHIEVEMENT = "goal_achievement"
    WORKFLOW_EFFICIENCY = "workflow_efficiency"
    LEARNING_MOMENT = "learning_moment"


@dataclass
class ConversationPattern:
    """Identified pattern in conversation"""

    pattern_type: str
    description: str
    frequency: int
    confidence: float
    impact_level: str  # "low", "medium", "high"
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityDimension:
    """Quality assessment for a specific dimension"""

    dimension: str
    score: float  # 0.0 - 1.0
    evidence: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class ConversationAnalysis:
    """Complete analysis result for a conversation"""

    # Basic metrics
    timestamp: float = field(default_factory=time.time)
    conversation_length: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0

    # Quality assessment
    quality_score: float = 0.0  # Overall quality (0.0 - 1.0)
    quality_dimensions: List[QualityDimension] = field(default_factory=list)

    # Pattern analysis
    identified_patterns: List[ConversationPattern] = field(default_factory=list)
    detected_signals: List[ConversationSignal] = field(default_factory=list)

    # Opportunity identification
    improvement_opportunities: List[Dict[str, Any]] = field(default_factory=list)
    suggested_interventions: List[Dict[str, Any]] = field(default_factory=list)

    # Context and metadata
    conversation_activity_level: float = 1.0  # Factor for analysis frequency
    user_expertise_assessment: str = "unknown"  # "beginner", "intermediate", "advanced"
    domain_context: str = "general"

    # User satisfaction indicators
    satisfaction_signals: Dict[str, Any] = field(default_factory=dict)


class SignalDetector:
    """Detects various signals in conversation content"""

    def __init__(self):
        # Compile regex patterns for efficiency
        self.positive_patterns = [
            re.compile(
                r"\b(thank you|thanks|great|perfect|exactly|awesome|helpful)\b", re.IGNORECASE
            ),
            re.compile(r"\b(works|working|solved|fixed|success)\b", re.IGNORECASE),
            re.compile(r"(that helps|much better|makes sense)\b", re.IGNORECASE),
        ]

        self.confusion_patterns = [
            re.compile(
                r"\b(confused|don\'t understand|unclear|not sure|what do you mean)\b", re.IGNORECASE
            ),
            re.compile(r"\b(how do I|what is|can you explain|I don\'t get)\b", re.IGNORECASE),
            re.compile(r"(\?\?\?|huh\?|what\?)", re.IGNORECASE),
        ]

        self.frustration_patterns = [
            re.compile(r"\b(frustrated|annoying|not working|broken|error)\b", re.IGNORECASE),
            re.compile(r"\b(tried everything|nothing works|still failing)\b", re.IGNORECASE),
            re.compile(r"(this is ridiculous|waste of time)", re.IGNORECASE),
        ]

        self.clarification_patterns = [
            re.compile(
                r"\b(can you clarify|what exactly|more specific|elaborate)\b", re.IGNORECASE
            ),
            re.compile(r"\b(show me|example|demonstrate|walk me through)\b", re.IGNORECASE),
        ]

        self.success_patterns = [
            re.compile(r"\b(it works|working now|fixed|resolved|completed)\b", re.IGNORECASE),
            re.compile(r"\b(goal achieved|task done|mission accomplished)\b", re.IGNORECASE),
        ]

    def detect_signals(self, text: str) -> List[ConversationSignal]:
        """Detect conversation signals in text"""
        signals = []

        # Check positive engagement
        if any(pattern.search(text) for pattern in self.positive_patterns):
            signals.append(ConversationSignal.POSITIVE_ENGAGEMENT)

        # Check confusion indicators
        if any(pattern.search(text) for pattern in self.confusion_patterns):
            signals.append(ConversationSignal.CONFUSION_INDICATOR)

        # Check frustration signals
        if any(pattern.search(text) for pattern in self.frustration_patterns):
            signals.append(ConversationSignal.FRUSTRATION_SIGNAL)

        # Check clarification requests
        if any(pattern.search(text) for pattern in self.clarification_patterns):
            signals.append(ConversationSignal.CLARIFICATION_REQUEST)

        # Check success confirmations
        if any(pattern.search(text) for pattern in self.success_patterns):
            signals.append(ConversationSignal.SUCCESS_CONFIRMATION)

        return signals


class PatternAnalyzer:
    """Analyzes conversation patterns and recurring themes"""

    def __init__(self):
        self.pattern_cache: Dict[str, List[ConversationPattern]] = {}

    def analyze_patterns(
        self, conversation_context: Dict[str, Any], session_history: List[Any]
    ) -> List[ConversationPattern]:
        """Analyze conversation for patterns"""
        patterns = []

        # Extract conversation messages
        messages = conversation_context.get("messages", [])
        if not messages:
            return patterns

        # Analyze message patterns
        patterns.extend(self._analyze_message_patterns(messages))
        patterns.extend(self._analyze_tool_usage_patterns(conversation_context))
        patterns.extend(self._analyze_goal_patterns(conversation_context))
        patterns.extend(self._analyze_learning_patterns(messages))

        return patterns

    def _analyze_message_patterns(
        self, messages: List[Dict[str, Any]]
    ) -> List[ConversationPattern]:
        """Analyze patterns in message content and structure"""
        patterns = []

        if len(messages) < 3:
            return patterns

        # Look for repetitive questions
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        question_count = sum(1 for msg in user_messages if "?" in msg.get("content", ""))

        if question_count > len(user_messages) * 0.7:
            patterns.append(
                ConversationPattern(
                    pattern_type="high_question_frequency",
                    description="User asking many questions, might need more proactive guidance",
                    frequency=question_count,
                    confidence=0.8,
                    impact_level="medium",
                    examples=[
                        msg["content"][:100]
                        for msg in user_messages
                        if "?" in msg.get("content", "")
                    ][:3],
                )
            )

        # Look for repeated similar requests
        user_contents = [msg.get("content", "") for msg in user_messages]
        similar_requests = self._find_similar_content(user_contents)

        if len(similar_requests) > 1:
            patterns.append(
                ConversationPattern(
                    pattern_type="repeated_requests",
                    description="User making similar requests multiple times",
                    frequency=len(similar_requests),
                    confidence=0.7,
                    impact_level="high",
                    examples=similar_requests[:3],
                )
            )

        return patterns

    def _analyze_tool_usage_patterns(
        self, conversation_context: Dict[str, Any]
    ) -> List[ConversationPattern]:
        """Analyze tool usage patterns"""
        patterns = []

        tool_usage = conversation_context.get("tool_usage", [])
        if not tool_usage:
            return patterns

        # Count tool frequency
        tool_counts = {}
        for tool_use in tool_usage:
            tool_name = tool_use.get("tool_name", "unknown")
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        # Look for overused tools
        total_tools = len(tool_usage)
        for tool_name, count in tool_counts.items():
            if count > total_tools * 0.4:  # More than 40% of tool usage
                patterns.append(
                    ConversationPattern(
                        pattern_type="tool_overuse",
                        description=f"Heavy reliance on {tool_name} tool",
                        frequency=count,
                        confidence=0.8,
                        impact_level="medium",
                        metadata={"tool_name": tool_name, "usage_percentage": count / total_tools},
                    )
                )

        return patterns

    def _analyze_goal_patterns(
        self, conversation_context: Dict[str, Any]
    ) -> List[ConversationPattern]:
        """Analyze goal achievement patterns"""
        patterns = []

        goals = conversation_context.get("goals", [])
        if not goals:
            return patterns

        completed_goals = [g for g in goals if g.get("status") == "completed"]
        pending_goals = [g for g in goals if g.get("status") != "completed"]

        # Check for goal completion efficiency
        if len(goals) > 3:
            completion_rate = len(completed_goals) / len(goals)
            if completion_rate < 0.3:
                patterns.append(
                    ConversationPattern(
                        pattern_type="low_goal_completion",
                        description="Many goals started but few completed",
                        frequency=len(pending_goals),
                        confidence=0.9,
                        impact_level="high",
                        metadata={"completion_rate": completion_rate},
                    )
                )

        return patterns

    def _analyze_learning_patterns(
        self, messages: List[Dict[str, Any]]
    ) -> List[ConversationPattern]:
        """Analyze learning and knowledge transfer patterns"""
        patterns = []

        # Look for learning indicators
        learning_keywords = ["how", "why", "what", "explain", "understand", "learn"]
        user_messages = [msg for msg in messages if msg.get("role") == "user"]

        learning_message_count = 0
        for msg in user_messages:
            content = msg.get("content", "").lower()
            if any(keyword in content for keyword in learning_keywords):
                learning_message_count += 1

        if learning_message_count > len(user_messages) * 0.5:
            patterns.append(
                ConversationPattern(
                    pattern_type="learning_focused",
                    description="User is in learning mode, focus on educational responses",
                    frequency=learning_message_count,
                    confidence=0.8,
                    impact_level="medium",
                    metadata={"learning_intensity": learning_message_count / len(user_messages)},
                )
            )

        return patterns

    def _find_similar_content(
        self, contents: List[str], similarity_threshold: float = 0.4
    ) -> List[str]:
        """Find similar content in a list of strings"""
        similar_groups = []

        for i, content1 in enumerate(contents):
            for j, content2 in enumerate(contents[i + 1 :], i + 1):
                similarity = self._calculate_similarity(content1, content2)
                if similarity >= similarity_threshold:
                    similar_groups.append(content1)
                    break

        return similar_groups

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts"""
        if not text1 or not text2:
            return 0.0

        # Normalize and extract key words
        import re

        # Remove punctuation and normalize
        text1_clean = re.sub(r'[^\w\s]', '', text1.lower())
        text2_clean = re.sub(r'[^\w\s]', '', text2.lower())

        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())

        if not words1 or not words2:
            return 0.0

        # Check for semantic similarity - key terms that indicate similar intent
        key_terms = ['create', 'make', 'file', 'new']

        # Give higher weight to shared key terms
        key_intersection = words1.intersection(words2).intersection(key_terms)
        regular_intersection = words1.intersection(words2)
        union = words1.union(words2)

        # Boost similarity score if key terms match
        base_similarity = len(regular_intersection) / len(union)
        if key_intersection:
            base_similarity += 0.3  # Boost for matching key terms

        return min(base_similarity, 1.0)  # Cap at 1.0


class QualityAssessor:
    """Assesses conversation quality across multiple dimensions"""

    def __init__(self):
        self.dimensions = [
            "clarity",
            "effectiveness",
            "engagement",
            "technical_accuracy",
            "efficiency",
            "satisfaction",
        ]

    def assess_quality(
        self,
        conversation_context: Dict[str, Any],
        detected_signals: List[ConversationSignal],
        identified_patterns: List[ConversationPattern],
    ) -> Tuple[float, List[QualityDimension]]:
        """Assess overall conversation quality"""

        dimension_assessments = []

        # Assess each dimension
        for dimension in self.dimensions:
            assessment = self._assess_dimension(
                dimension, conversation_context, detected_signals, identified_patterns
            )
            dimension_assessments.append(assessment)

        # Calculate overall quality score
        overall_score = sum(dim.score for dim in dimension_assessments) / len(dimension_assessments)

        return overall_score, dimension_assessments

    def _assess_dimension(
        self,
        dimension: str,
        conversation_context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess a specific quality dimension"""

        if dimension == "clarity":
            return self._assess_clarity(conversation_context, signals, patterns)
        elif dimension == "effectiveness":
            return self._assess_effectiveness(conversation_context, signals, patterns)
        elif dimension == "engagement":
            return self._assess_engagement(conversation_context, signals, patterns)
        elif dimension == "technical_accuracy":
            return self._assess_technical_accuracy(conversation_context, signals, patterns)
        elif dimension == "efficiency":
            return self._assess_efficiency(conversation_context, signals, patterns)
        elif dimension == "satisfaction":
            return self._assess_satisfaction(conversation_context, signals, patterns)
        else:
            return QualityDimension(dimension=dimension, score=0.5)

    def _assess_clarity(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess conversation clarity"""
        base_score = 0.7
        evidence = []
        suggestions = []

        # Negative indicators
        if ConversationSignal.CONFUSION_INDICATOR in signals:
            base_score -= 0.3
            evidence.append("Confusion indicators detected in conversation")
            suggestions.append("Consider providing clearer explanations or examples")

        if ConversationSignal.CLARIFICATION_REQUEST in signals:
            base_score -= 0.2
            evidence.append("User requested clarification")
            suggestions.append("Be more specific and provide step-by-step guidance")

        # Pattern-based adjustments
        for pattern in patterns:
            if pattern.pattern_type == "repeated_requests":
                base_score -= 0.2
                evidence.append("User repeating similar requests")
                suggestions.append("Ensure requests are fully understood before responding")

        # Positive indicators
        if ConversationSignal.POSITIVE_ENGAGEMENT in signals:
            base_score += 0.1
            evidence.append("Positive engagement signals detected")

        return QualityDimension(
            dimension="clarity",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )

    def _assess_effectiveness(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess conversation effectiveness"""
        base_score = 0.7
        evidence = []
        suggestions = []

        # Check goal achievement
        goals = context.get("goals", [])
        if goals:
            completed = len([g for g in goals if g.get("status") == "completed"])
            completion_rate = completed / len(goals)
            base_score = completion_rate
            evidence.append(f"Goal completion rate: {completion_rate:.1%}")

            if completion_rate < 0.5:
                suggestions.append("Focus on completing current goals before adding new ones")

        # Signal-based adjustments
        if ConversationSignal.SUCCESS_CONFIRMATION in signals:
            base_score += 0.2
            evidence.append("Success confirmations detected")

        if ConversationSignal.FRUSTRATION_SIGNAL in signals:
            base_score -= 0.3
            evidence.append("Frustration signals detected")
            suggestions.append("Address user frustration and provide alternative approaches")

        return QualityDimension(
            dimension="effectiveness",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )

    def _assess_engagement(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess user engagement level"""
        base_score = 0.6
        evidence = []
        suggestions = []

        messages = context.get("messages", [])
        if messages:
            user_messages = [m for m in messages if m.get("role") == "user"]
            avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)

            if avg_length > 100:
                base_score += 0.2
                evidence.append("User providing detailed messages")
            elif avg_length < 20:
                base_score -= 0.1
                evidence.append("User messages are very brief")
                suggestions.append("Encourage more detailed communication")

        # Positive engagement signals
        if ConversationSignal.POSITIVE_ENGAGEMENT in signals:
            base_score += 0.2
            evidence.append("Positive engagement detected")

        # Learning pattern adjustment
        for pattern in patterns:
            if pattern.pattern_type == "learning_focused":
                base_score += 0.1
                evidence.append("User actively learning")

        return QualityDimension(
            dimension="engagement",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )

    def _assess_technical_accuracy(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess technical accuracy of solutions"""
        # This is a simplified assessment - in practice would need more sophisticated checks
        base_score = 0.8
        evidence = ["Baseline technical accuracy assessment"]
        suggestions = []

        # Look for error indicators
        tool_usage = context.get("tool_usage", [])
        error_count = sum(1 for tool in tool_usage if tool.get("status") == "error")

        if error_count > 0:
            error_rate = error_count / len(tool_usage)
            base_score -= error_rate * 0.3
            evidence.append(f"Tool error rate: {error_rate:.1%}")
            suggestions.append("Review and improve error handling")

        return QualityDimension(
            dimension="technical_accuracy",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )

    def _assess_efficiency(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess conversation efficiency"""
        base_score = 0.7
        evidence = []
        suggestions = []

        # Check for tool overuse pattern
        for pattern in patterns:
            if pattern.pattern_type == "tool_overuse":
                base_score -= 0.2
                evidence.append(f"Overuse of {pattern.metadata.get('tool_name', 'tool')} detected")
                suggestions.append("Consider diversifying tool usage for better efficiency")

        # Check message efficiency
        messages = context.get("messages", [])
        if len(messages) > 20:
            base_score -= 0.1
            evidence.append("Long conversation - check for efficiency opportunities")
            suggestions.append("Look for ways to achieve goals more directly")

        return QualityDimension(
            dimension="efficiency",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )

    def _assess_satisfaction(
        self,
        context: Dict[str, Any],
        signals: List[ConversationSignal],
        patterns: List[ConversationPattern],
    ) -> QualityDimension:
        """Assess user satisfaction"""
        base_score = 0.6
        evidence = []
        suggestions = []

        # Positive satisfaction signals
        positive_signals = [
            ConversationSignal.POSITIVE_ENGAGEMENT,
            ConversationSignal.SUCCESS_CONFIRMATION,
        ]
        positive_count = sum(1 for signal in signals if signal in positive_signals)

        # Negative satisfaction signals
        negative_signals = [
            ConversationSignal.FRUSTRATION_SIGNAL,
            ConversationSignal.CONFUSION_INDICATOR,
        ]
        negative_count = sum(1 for signal in signals if signal in negative_signals)

        # Adjust based on signal balance
        signal_balance = positive_count - negative_count
        base_score += signal_balance * 0.1

        if positive_count > 0:
            evidence.append(f"{positive_count} positive satisfaction signals")
        if negative_count > 0:
            evidence.append(f"{negative_count} negative satisfaction signals")
            suggestions.append("Address sources of user frustration or confusion")

        return QualityDimension(
            dimension="satisfaction",
            score=max(0.0, min(1.0, base_score)),
            evidence=evidence,
            improvement_suggestions=suggestions,
        )


class AnalysisEngine:
    """
    Main analysis engine for conversation quality and pattern analysis.
    """

    def __init__(self):
        self.signal_detector = SignalDetector()
        self.pattern_analyzer = PatternAnalyzer()
        self.quality_assessor = QualityAssessor()

    async def initialize(self):
        """Initialize the analysis engine"""
        # Any async initialization can go here
        pass

    async def analyze_conversation(
        self, conversation_context: Dict[str, Any], session_history: List[Any]
    ) -> ConversationAnalysis:
        """
        Perform comprehensive conversation analysis.

        Args:
            conversation_context: Current conversation context
            session_history: Historical analysis results

        Returns:
            ConversationAnalysis: Complete analysis results
        """
        analysis = ConversationAnalysis()

        # Extract basic metrics
        messages = conversation_context.get("messages", [])
        analysis.conversation_length = len(messages)
        analysis.user_message_count = len([m for m in messages if m.get("role") == "user"])
        analysis.assistant_message_count = len(
            [m for m in messages if m.get("role") == "assistant"]
        )

        # Detect signals in conversation
        all_text = " ".join(msg.get("content", "") for msg in messages)
        analysis.detected_signals = self.signal_detector.detect_signals(all_text)

        # Analyze patterns
        analysis.identified_patterns = self.pattern_analyzer.analyze_patterns(
            conversation_context, session_history
        )

        # Assess quality
        analysis.quality_score, analysis.quality_dimensions = self.quality_assessor.assess_quality(
            conversation_context, analysis.detected_signals, analysis.identified_patterns
        )

        # Generate improvement opportunities
        analysis.improvement_opportunities = self._generate_improvement_opportunities(analysis)

        # Assess user expertise and domain
        analysis.user_expertise_assessment = self._assess_user_expertise(conversation_context)
        analysis.domain_context = self._identify_domain_context(conversation_context)

        # Calculate activity level for adaptive analysis frequency
        analysis.conversation_activity_level = self._calculate_activity_level(
            conversation_context, session_history
        )

        # Extract satisfaction signals
        analysis.satisfaction_signals = self._extract_satisfaction_signals(analysis)

        return analysis

    def _generate_improvement_opportunities(
        self, analysis: ConversationAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate improvement opportunities based on analysis"""
        opportunities = []

        # Collect suggestions from quality dimensions
        for dimension in analysis.quality_dimensions:
            if dimension.score < 0.6 and dimension.improvement_suggestions:
                for suggestion in dimension.improvement_suggestions:
                    opportunities.append(
                        {
                            "area": dimension.dimension,
                            "description": suggestion,
                            "priority": "high" if dimension.score < 0.4 else "medium",
                            "confidence": 0.8,
                        }
                    )

        # Add pattern-based opportunities
        for pattern in analysis.identified_patterns:
            if pattern.impact_level == "high":
                opportunities.append(
                    {
                        "area": "pattern_optimization",
                        "description": f"Address {pattern.pattern_type}: {pattern.description}",
                        "priority": "high",
                        "confidence": pattern.confidence,
                    }
                )

        return opportunities

    def _assess_user_expertise(self, conversation_context: Dict[str, Any]) -> str:
        """Assess user's technical expertise level"""
        messages = conversation_context.get("messages", [])
        user_messages = [m for m in messages if m.get("role") == "user"]

        if not user_messages:
            return "unknown"

        # Simple heuristic based on technical vocabulary and question complexity
        technical_terms = 0
        basic_questions = 0

        for msg in user_messages:
            content = msg.get("content", "").lower()

            # Count technical terms (simplified)
            tech_keywords = [
                "api",
                "function",
                "class",
                "method",
                "algorithm",
                "database",
                "framework",
            ]
            technical_terms += sum(1 for keyword in tech_keywords if keyword in content)

            # Count basic questions
            if any(phrase in content for phrase in ["how do i", "what is", "can you help"]):
                basic_questions += 1

        # Simple classification
        if technical_terms > len(user_messages):
            return "advanced"
        elif technical_terms > 0 and basic_questions < len(user_messages) * 0.5:
            return "intermediate"
        else:
            return "beginner"

    def _identify_domain_context(self, conversation_context: Dict[str, Any]) -> str:
        """Identify the domain context of the conversation"""
        messages = conversation_context.get("messages", [])
        all_text = " ".join(msg.get("content", "") for msg in messages).lower()

        # Domain keywords mapping
        domains = {
            "programming": ["code", "function", "class", "variable", "programming", "software"],
            "data_science": ["data", "analysis", "machine learning", "statistics", "model"],
            "web_development": ["web", "html", "css", "javascript", "frontend", "backend"],
            "devops": ["deployment", "docker", "kubernetes", "CI/CD", "infrastructure"],
            "security": ["security", "authentication", "encryption", "vulnerability"],
            "general": [],
        }

        domain_scores = {}
        for domain, keywords in domains.items():
            if domain == "general":
                continue
            score = sum(1 for keyword in keywords if keyword in all_text)
            domain_scores[domain] = score

        # Return domain with highest score, or 'general' if none
        if domain_scores:
            max_domain = max(domain_scores, key=domain_scores.get)
            if domain_scores[max_domain] > 0:
                return max_domain

        return "general"

    def _calculate_activity_level(
        self, conversation_context: Dict[str, Any], session_history: List[Any]
    ) -> float:
        """Calculate conversation activity level for adaptive analysis"""
        base_level = 1.0

        # Recent message frequency
        messages = conversation_context.get("messages", [])
        if len(messages) > 10:
            base_level *= 1.5  # More active conversation

        # Recent analysis results
        if len(session_history) > 3:
            recent_analyses = session_history[-3:]
            avg_quality = sum(r.analysis.quality_score for r in recent_analyses) / len(
                recent_analyses
            )

            if avg_quality < 0.5:
                base_level *= 2.0  # More frequent analysis needed
            elif avg_quality > 0.8:
                base_level *= 0.7  # Less frequent analysis needed

        return min(3.0, base_level)  # Cap at 3x base frequency

    def _extract_satisfaction_signals(self, analysis: ConversationAnalysis) -> Dict[str, Any]:
        """Extract user satisfaction signals from analysis"""
        signals = {"overall_sentiment": "neutral", "confidence": 0.5, "indicators": []}

        positive_signals = [
            ConversationSignal.POSITIVE_ENGAGEMENT,
            ConversationSignal.SUCCESS_CONFIRMATION,
        ]
        negative_signals = [
            ConversationSignal.FRUSTRATION_SIGNAL,
            ConversationSignal.CONFUSION_INDICATOR,
        ]

        positive_count = sum(1 for s in analysis.detected_signals if s in positive_signals)
        negative_count = sum(1 for s in analysis.detected_signals if s in negative_signals)

        if positive_count > negative_count:
            signals["overall_sentiment"] = "positive"
            signals["confidence"] = min(0.9, 0.5 + (positive_count * 0.1))
        elif negative_count > positive_count:
            signals["overall_sentiment"] = "negative"
            signals["confidence"] = min(0.9, 0.5 + (negative_count * 0.1))

        signals["indicators"] = [signal.value for signal in analysis.detected_signals]

        return signals
