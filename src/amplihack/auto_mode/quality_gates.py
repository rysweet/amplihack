"""
Quality Gates for Auto-Mode

Implements quality gate evaluation system that determines when and how
auto-mode should intervene in conversations based on analysis results.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Set up logger
logger = logging.getLogger(__name__)

from .analysis import ConversationAnalysis, ConversationSignal
from .session import SessionState


class GatePriority(Enum):
    """Priority levels for quality gate actions"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionType(Enum):
    """Types of interventions that can be suggested"""

    CLARIFICATION_SUGGESTION = "clarification_suggestion"
    TOOL_RECOMMENDATION = "tool_recommendation"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    GOAL_REFOCUS = "goal_refocus"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    ERROR_RESOLUTION = "error_resolution"
    PRIVACY_PROTECTION = "privacy_protection"


@dataclass
class QualityGateCondition:
    """Condition for triggering a quality gate"""

    condition_type: str
    field_path: str  # e.g., "analysis.quality_score"
    operator: str  # "lt", "gt", "eq", "contains", etc.
    threshold: Any
    weight: float = 1.0


@dataclass
class QualityGateAction:
    """Action to take when a quality gate is triggered"""

    action_type: InterventionType
    title: str
    description: str
    confidence_boost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGateDefinition:
    """Definition of a quality gate"""

    gate_id: str
    name: str
    description: str
    priority: GatePriority

    # Trigger conditions (all must be met)
    conditions: List[QualityGateCondition] = field(default_factory=list)

    # Actions to suggest when triggered
    actions: List[QualityGateAction] = field(default_factory=list)

    # Configuration
    min_confidence_threshold: float = 0.5
    cooldown_minutes: int = 5  # Minimum time between same gate triggers
    max_triggers_per_session: int = 3

    # User customization
    user_enabled: bool = True
    user_threshold_adjustment: float = 0.0


@dataclass
class QualityGateResult:
    """Result of evaluating a quality gate"""

    gate_id: str
    gate_name: str
    triggered: bool
    confidence: float
    priority: GatePriority
    trigger_time: float = field(default_factory=time.time)

    # If triggered
    met_conditions: List[str] = field(default_factory=list)
    suggested_actions: List[Dict[str, Any]] = field(default_factory=list)

    # Context
    session_id: str = ""
    cycle_id: str = ""


class QualityGateEvaluator:
    """
    Evaluates quality gates to determine when interventions should be suggested.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.gates: Dict[str, QualityGateDefinition] = {}
        self.config_path = config_path
        self.gate_history: Dict[str, List[float]] = {}  # session_id -> trigger times

        # Load default gates
        self._load_default_gates()

        # Load custom gates if config provided
        if config_path:
            self._load_custom_gates(config_path)

    async def initialize(self):
        """Initialize the quality gate evaluator"""
        pass

    def _load_default_gates(self):
        """Load default quality gate definitions"""

        # Gate: Conversation Quality Drop
        self.gates["quality_drop"] = QualityGateDefinition(
            gate_id="quality_drop",
            name="Conversation Quality Drop",
            description="Triggered when conversation quality falls below threshold",
            priority=GatePriority.HIGH,
            conditions=[
                QualityGateCondition(
                    condition_type="threshold",
                    field_path="analysis.quality_score",
                    operator="lt",
                    threshold=0.6,
                ),
                QualityGateCondition(
                    condition_type="signal_present",
                    field_path="analysis.detected_signals",
                    operator="contains",
                    threshold=ConversationSignal.CONFUSION_INDICATOR,
                ),
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.CLARIFICATION_SUGGESTION,
                    title="Suggest Clarification",
                    description="Ask clarifying questions to improve understanding",
                    confidence_boost=0.2,
                )
            ],
        )

        # Gate: Goal Stagnation
        self.gates["goal_stagnation"] = QualityGateDefinition(
            gate_id="goal_stagnation",
            name="Goal Achievement Stagnation",
            description="Triggered when goals are not being achieved efficiently",
            priority=GatePriority.MEDIUM,
            conditions=[
                QualityGateCondition(
                    condition_type="quality_dimension",
                    field_path="analysis.quality_dimensions",
                    operator="dimension_score_lt",
                    threshold={"dimension": "effectiveness", "score": 0.5},
                ),
                QualityGateCondition(
                    condition_type="pattern_present",
                    field_path="analysis.identified_patterns",
                    operator="pattern_type_exists",
                    threshold="low_goal_completion",
                ),
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.GOAL_REFOCUS,
                    title="Refocus on Goals",
                    description="Suggest prioritizing and focusing on specific goals",
                    confidence_boost=0.1,
                ),
                QualityGateAction(
                    action_type=InterventionType.WORKFLOW_OPTIMIZATION,
                    title="Optimize Workflow",
                    description="Suggest more efficient approach to current tasks",
                    confidence_boost=0.15,
                ),
            ],
        )

        # Gate: Tool Usage Optimization
        self.gates["tool_optimization"] = QualityGateDefinition(
            gate_id="tool_optimization",
            name="Tool Usage Optimization",
            description="Triggered when tool usage could be optimized",
            priority=GatePriority.MEDIUM,
            conditions=[
                QualityGateCondition(
                    condition_type="pattern_present",
                    field_path="analysis.identified_patterns",
                    operator="pattern_type_exists",
                    threshold="tool_overuse",
                ),
                QualityGateCondition(
                    condition_type="quality_dimension",
                    field_path="analysis.quality_dimensions",
                    operator="dimension_score_lt",
                    threshold={"dimension": "efficiency", "score": 0.6},
                ),
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.TOOL_RECOMMENDATION,
                    title="Recommend Alternative Tools",
                    description="Suggest more appropriate tools for current tasks",
                    confidence_boost=0.1,
                )
            ],
        )

        # Gate: Learning Opportunity Detection
        self.gates["learning_opportunity"] = QualityGateDefinition(
            gate_id="learning_opportunity",
            name="Learning Opportunity Detection",
            description="Triggered when user could benefit from learning suggestions",
            priority=GatePriority.LOW,
            conditions=[
                QualityGateCondition(
                    condition_type="pattern_present",
                    field_path="analysis.identified_patterns",
                    operator="pattern_type_exists",
                    threshold="learning_focused",
                ),
                QualityGateCondition(
                    condition_type="expertise_level",
                    field_path="analysis.user_expertise_assessment",
                    operator="eq",
                    threshold="beginner",
                ),
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.LEARNING_OPPORTUNITY,
                    title="Suggest Learning Resources",
                    description="Provide educational content or deeper explanations",
                    confidence_boost=0.05,
                )
            ],
        )

        # Gate: User Frustration Detection
        self.gates["frustration_detection"] = QualityGateDefinition(
            gate_id="frustration_detection",
            name="User Frustration Detection",
            description="Triggered when user shows signs of frustration",
            priority=GatePriority.HIGH,
            conditions=[
                QualityGateCondition(
                    condition_type="signal_present",
                    field_path="analysis.detected_signals",
                    operator="contains",
                    threshold=ConversationSignal.FRUSTRATION_SIGNAL,
                )
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.ERROR_RESOLUTION,
                    title="Address Frustration",
                    description="Acknowledge frustration and provide alternative approaches",
                    confidence_boost=0.3,
                )
            ],
            cooldown_minutes=10,  # Longer cooldown for frustration gates
        )

        # Gate: Privacy Protection
        self.gates["privacy_protection"] = QualityGateDefinition(
            gate_id="privacy_protection",
            name="Privacy Protection",
            description="Triggered when sensitive data is detected",
            priority=GatePriority.CRITICAL,
            conditions=[
                QualityGateCondition(
                    condition_type="sensitive_data",
                    field_path="session_state.sensitive_data_flags",
                    operator="not_empty",
                    threshold=None,
                )
            ],
            actions=[
                QualityGateAction(
                    action_type=InterventionType.PRIVACY_PROTECTION,
                    title="Protect Sensitive Data",
                    description="Suggest privacy protection measures",
                    confidence_boost=0.5,
                )
            ],
            min_confidence_threshold=0.9,  # High threshold for privacy
        )

    def _load_custom_gates(self, config_path: str):
        """Load custom quality gates from configuration file"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, "r") as f:
                    config_data = yaml.safe_load(f)

                custom_gates = config_data.get("quality_gates", {})
                for gate_id, gate_config in custom_gates.items():
                    self._parse_gate_config(gate_id, gate_config)

        except Exception as e:
            logger.error(f"Failed to load custom quality gates: {e}")

    def _parse_gate_config(self, gate_id: str, config: Dict[str, Any]):
        """Parse gate configuration from YAML"""
        try:
            # Parse conditions
            conditions = []
            for cond_config in config.get("conditions", []):
                conditions.append(
                    QualityGateCondition(
                        condition_type=cond_config["condition_type"],
                        field_path=cond_config["field_path"],
                        operator=cond_config["operator"],
                        threshold=cond_config["threshold"],
                        weight=cond_config.get("weight", 1.0),
                    )
                )

            # Parse actions
            actions = []
            for action_config in config.get("actions", []):
                actions.append(
                    QualityGateAction(
                        action_type=InterventionType(action_config["action_type"]),
                        title=action_config["title"],
                        description=action_config["description"],
                        confidence_boost=action_config.get("confidence_boost", 0.0),
                        metadata=action_config.get("metadata", {}),
                    )
                )

            # Create gate definition
            gate = QualityGateDefinition(
                gate_id=gate_id,
                name=config["name"],
                description=config["description"],
                priority=GatePriority(config.get("priority", "medium")),
                conditions=conditions,
                actions=actions,
                min_confidence_threshold=config.get("min_confidence_threshold", 0.5),
                cooldown_minutes=config.get("cooldown_minutes", 5),
                max_triggers_per_session=config.get("max_triggers_per_session", 3),
            )

            self.gates[gate_id] = gate

        except Exception as e:
            logger.error(f"Failed to parse gate config for {gate_id}: {e}")

    async def evaluate(
        self, analysis: ConversationAnalysis, session_state: SessionState, config: Any
    ) -> List[QualityGateResult]:
        """
        Evaluate all quality gates against the current analysis.

        Args:
            analysis: Current conversation analysis
            session_state: Current session state
            config: Orchestrator configuration

        Returns:
            List[QualityGateResult]: Results of gate evaluation
        """
        results = []
        current_time = time.time()

        for gate_id, gate in self.gates.items():
            # Skip disabled gates
            if not gate.user_enabled:
                continue

            # Check cooldown
            if self._is_gate_in_cooldown(
                gate_id, session_state.session_id, current_time, gate.cooldown_minutes
            ):
                continue

            # Check session trigger limit
            if self._exceeds_session_limit(
                gate_id, session_state.session_id, gate.max_triggers_per_session
            ):
                continue

            # Evaluate gate conditions
            result = await self._evaluate_gate(gate, analysis, session_state, config)
            if result:
                results.append(result)

                # Record trigger time
                self._record_gate_trigger(gate_id, session_state.session_id, current_time)

        return results

    async def _evaluate_gate(
        self,
        gate: QualityGateDefinition,
        analysis: ConversationAnalysis,
        session_state: SessionState,
        config: Any,
    ) -> Optional[QualityGateResult]:
        """Evaluate a single quality gate"""

        met_conditions = []
        total_confidence = 0.0
        condition_count = 0

        # Evaluate each condition
        for condition in gate.conditions:
            condition_met, confidence = self._evaluate_condition(condition, analysis, session_state)

            if condition_met:
                met_conditions.append(
                    f"{condition.field_path} {condition.operator} {condition.threshold}"
                )
                total_confidence += confidence * condition.weight
                condition_count += 1
            else:
                # All conditions must be met for gate to trigger
                return None

        # Calculate overall confidence
        if condition_count > 0:
            avg_confidence = total_confidence / condition_count
        else:
            avg_confidence = 0.0

        # Apply user threshold adjustment
        adjusted_threshold = gate.min_confidence_threshold + gate.user_threshold_adjustment

        # Check if confidence meets threshold
        if avg_confidence < adjusted_threshold:
            return None

        # Gate is triggered - generate result
        result = QualityGateResult(
            gate_id=gate.gate_id,
            gate_name=gate.name,
            triggered=True,
            confidence=avg_confidence,
            priority=gate.priority,
            met_conditions=met_conditions,
            session_id=session_state.session_id,
        )

        # Generate suggested actions
        for action in gate.actions:
            action_confidence = avg_confidence + action.confidence_boost
            result.suggested_actions.append(
                {
                    "type": action.action_type.value,
                    "title": action.title,
                    "description": action.description,
                    "confidence": min(1.0, action_confidence),
                    "metadata": action.metadata,
                }
            )

        return result

    def _evaluate_condition(
        self,
        condition: QualityGateCondition,
        analysis: ConversationAnalysis,
        session_state: SessionState,
    ) -> tuple[bool, float]:
        """Evaluate a single gate condition"""

        try:
            # Get the field value
            value = self._get_field_value(condition.field_path, analysis, session_state)

            if value is None:
                return False, 0.0

            # Evaluate based on operator
            if condition.operator == "lt":
                met = value < condition.threshold
                confidence = (
                    max(0.0, (condition.threshold - value) / condition.threshold) if met else 0.0
                )

            elif condition.operator == "gt":
                met = value > condition.threshold
                confidence = (
                    max(0.0, (value - condition.threshold) / (1.0 - condition.threshold))
                    if met
                    else 0.0
                )

            elif condition.operator == "eq":
                met = value == condition.threshold
                confidence = 1.0 if met else 0.0

            elif condition.operator == "contains":
                met = condition.threshold in value if hasattr(value, "__contains__") else False
                confidence = 0.8 if met else 0.0

            elif condition.operator == "not_empty":
                met = bool(value) and len(value) > 0
                confidence = 0.9 if met else 0.0

            elif condition.operator == "dimension_score_lt":
                # Special operator for quality dimensions
                met, confidence = self._evaluate_dimension_condition(value, condition.threshold)

            elif condition.operator == "pattern_type_exists":
                # Special operator for pattern existence
                met = (
                    any(p.pattern_type == condition.threshold for p in value)
                    if isinstance(value, list)
                    else False
                )
                confidence = 0.8 if met else 0.0

            else:
                # Unknown operator
                return False, 0.0

            return met, confidence

        except Exception as e:
            logger.error(f"Error evaluating condition {condition.field_path}: {e}")
            return False, 0.0

    def _get_field_value(
        self, field_path: str, analysis: ConversationAnalysis, session_state: SessionState
    ):
        """Get field value using dot notation path"""

        # Determine root object
        if field_path.startswith("analysis."):
            obj = analysis
            path = field_path[9:]  # Remove "analysis." prefix
        elif field_path.startswith("session_state."):
            obj = session_state
            path = field_path[13:]  # Remove "session_state." prefix
        else:
            return None

        # Navigate through path
        for part in path.split("."):
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None

        return obj

    def _evaluate_dimension_condition(
        self, dimensions: List[Any], threshold: Dict[str, Any]
    ) -> tuple[bool, float]:
        """Evaluate quality dimension specific condition"""
        target_dimension = threshold.get("dimension")
        target_score = threshold.get("score")

        for dim in dimensions:
            if hasattr(dim, "dimension") and dim.dimension == target_dimension:
                if hasattr(dim, "score") and dim.score < target_score:
                    confidence = (target_score - dim.score) / target_score
                    return True, confidence
                break

        return False, 0.0

    def _is_gate_in_cooldown(
        self, gate_id: str, session_id: str, current_time: float, cooldown_minutes: int
    ) -> bool:
        """Check if gate is in cooldown period"""
        key = f"{session_id}:{gate_id}"

        if key not in self.gate_history:
            return False

        last_trigger_time = self.gate_history[key][-1] if self.gate_history[key] else 0
        cooldown_seconds = cooldown_minutes * 60

        return (current_time - last_trigger_time) < cooldown_seconds

    def _exceeds_session_limit(self, gate_id: str, session_id: str, max_triggers: int) -> bool:
        """Check if gate has exceeded session trigger limit"""
        key = f"{session_id}:{gate_id}"

        if key not in self.gate_history:
            return False

        return len(self.gate_history[key]) >= max_triggers

    def _record_gate_trigger(self, gate_id: str, session_id: str, trigger_time: float):
        """Record a gate trigger for cooldown and limit tracking"""
        key = f"{session_id}:{gate_id}"

        if key not in self.gate_history:
            self.gate_history[key] = []

        self.gate_history[key].append(trigger_time)

        # Keep only recent triggers (last 24 hours)
        cutoff_time = trigger_time - (24 * 60 * 60)
        self.gate_history[key] = [t for t in self.gate_history[key] if t >= cutoff_time]

    def add_custom_gate(self, gate: QualityGateDefinition):
        """Add a custom quality gate at runtime"""
        self.gates[gate.gate_id] = gate

    def remove_gate(self, gate_id: str) -> bool:
        """Remove a quality gate"""
        if gate_id in self.gates:
            del self.gates[gate_id]
            return True
        return False

    def enable_gate(self, gate_id: str, enabled: bool = True) -> bool:
        """Enable or disable a quality gate"""
        if gate_id in self.gates:
            self.gates[gate_id].user_enabled = enabled
            return True
        return False

    def adjust_gate_threshold(self, gate_id: str, adjustment: float) -> bool:
        """Adjust gate threshold for user customization"""
        if gate_id in self.gates:
            self.gates[gate_id].user_threshold_adjustment = adjustment
            return True
        return False

    def get_gate_statistics(self) -> Dict[str, Any]:
        """Get statistics about gate triggers"""
        stats = {
            "total_gates": len(self.gates),
            "enabled_gates": len([g for g in self.gates.values() if g.user_enabled]),
            "gate_triggers": {},
        }

        for key, triggers in self.gate_history.items():
            session_id, gate_id = key.split(":", 1)
            if gate_id not in stats["gate_triggers"]:
                stats["gate_triggers"][gate_id] = 0
            stats["gate_triggers"][gate_id] += len(triggers)

        return stats
