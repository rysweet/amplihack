"""Coordinator Agent: Task classification and routing to specialist sub-agents.

Philosophy:
- Single responsibility: Classify tasks and route to specialists
- Does NOT perform retrieval, reasoning, or synthesis itself
- Reuses the existing _detect_intent logic from LearningAgent
- Routes to MemoryAgent for retrieval, then passes facts to synthesis

Public API:
    CoordinatorAgent: Task classification and routing
    TaskRoute: Dataclass describing which agents to invoke
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TaskRoute:
    """Describes how to route a task to sub-agents.

    Attributes:
        retrieval_strategy: Which retrieval approach to use
        needs_reasoning: Whether a dedicated reasoning step is needed
        needs_teaching: Whether pedagogical mode is needed
        reasoning_type: Specific reasoning type (temporal, causal, etc.)
        parallel_retrieval: Whether retrieval can run in parallel with other ops
    """

    retrieval_strategy: str = "auto"  # auto, entity, temporal, aggregation, full_text
    needs_reasoning: bool = False
    needs_teaching: bool = False
    reasoning_type: str = ""  # temporal, causal, counterfactual, mathematical, ratio_trend
    parallel_retrieval: bool = False


class CoordinatorAgent:
    """Routes tasks to specialist sub-agents based on intent classification.

    The Coordinator receives a question + intent and determines:
    1. Which retrieval strategy the MemoryAgent should use
    2. Whether dedicated reasoning is needed (and what type)
    3. Whether teaching mode should be activated

    It does NOT perform any of these operations itself.

    Args:
        agent_name: Name of the owning agent

    Example:
        >>> coord = CoordinatorAgent("test")
        >>> route = coord.classify(
        ...     question="How many projects?",
        ...     intent={"intent": "meta_memory"}
        ... )
        >>> print(route.retrieval_strategy)  # "aggregation"
    """

    def __init__(self, agent_name: str = "coordinator"):
        self.agent_name = agent_name

    def classify(self, question: str, intent: dict[str, Any]) -> TaskRoute:
        """Classify a question and determine the execution route.

        Args:
            question: The question text
            intent: Intent classification from _detect_intent

        Returns:
            TaskRoute describing which sub-agents to invoke
        """
        intent_type = intent.get("intent", "simple_recall")
        q_lower = question.lower()

        # Teaching check first (takes priority over intent classification)
        if "teach" in q_lower or "explain to" in q_lower:
            return TaskRoute(
                retrieval_strategy="auto",
                needs_teaching=True,
            )

        # Meta-memory: aggregation retrieval, no reasoning needed
        if intent_type == "meta_memory":
            return TaskRoute(retrieval_strategy="aggregation")

        # Simple recall: auto retrieval (entity or simple), no reasoning
        if intent_type == "simple_recall":
            return TaskRoute(retrieval_strategy="auto")

        # Incremental update: full retrieval for completeness
        if intent_type == "incremental_update":
            return TaskRoute(retrieval_strategy="auto")

        # Temporal comparison: temporal retrieval + temporal reasoning
        if intent_type == "temporal_comparison":
            return TaskRoute(
                retrieval_strategy="temporal",
                needs_reasoning=True,
                reasoning_type="temporal",
            )

        # Mathematical computation: auto retrieval + math reasoning
        if intent_type == "mathematical_computation":
            return TaskRoute(
                retrieval_strategy="auto",
                needs_reasoning=True,
                reasoning_type="mathematical",
            )

        # Causal/counterfactual: full retrieval + causal reasoning
        if intent_type == "causal_counterfactual":
            return TaskRoute(
                retrieval_strategy="auto",
                needs_reasoning=True,
                reasoning_type="causal",
            )

        # Multi-source synthesis: broad retrieval + synthesis reasoning
        if intent_type == "multi_source_synthesis":
            return TaskRoute(
                retrieval_strategy="auto",
                needs_reasoning=True,
                reasoning_type="multi_source",
            )

        # Contradiction resolution: full retrieval + contradiction reasoning
        if intent_type == "contradiction_resolution":
            return TaskRoute(
                retrieval_strategy="auto",
                needs_reasoning=True,
                reasoning_type="contradiction",
            )

        # Ratio/trend analysis: temporal retrieval + ratio reasoning
        if intent_type == "ratio_trend_analysis":
            return TaskRoute(
                retrieval_strategy="temporal",
                needs_reasoning=True,
                reasoning_type="ratio_trend",
            )

        # Default: auto retrieval with reasoning
        return TaskRoute(
            retrieval_strategy="auto",
            needs_reasoning=True,
            reasoning_type="general",
        )


__all__ = ["CoordinatorAgent", "TaskRoute"]
