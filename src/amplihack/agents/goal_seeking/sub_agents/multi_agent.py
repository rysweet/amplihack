"""Multi-Agent Learning Agent: Drop-in replacement for LearningAgent.

Philosophy:
- Same external interface as LearningAgent (learn_from_content, answer_question)
- Internally decomposes into Coordinator + MemoryAgent + synthesis
- MemoryAgent handles retrieval strategy selection
- Coordinator determines the execution plan
- Backward compatible: if something fails, falls back to parent LearningAgent
- When enable_spawning=True, can dynamically spawn sub-agents for multi-hop reasoning

Public API:
    MultiAgentLearningAgent: Drop-in replacement with multi-agent retrieval
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..learning_agent import LearningAgent
from ..similarity import rerank_facts_by_query
from .agent_spawner import AgentSpawner
from .coordinator import CoordinatorAgent
from .memory_agent import MemoryAgent

logger = logging.getLogger(__name__)


class MultiAgentLearningAgent(LearningAgent):
    """Learning agent with multi-agent internal architecture.

    Extends LearningAgent by replacing the monolithic retrieval+synthesis
    pipeline with:
    - CoordinatorAgent: classifies questions and routes to specialists
    - MemoryAgent: selects optimal retrieval strategy per question
    - AgentSpawner (optional): spawns sub-agents for multi-hop reasoning

    The synthesis step still uses the parent LearningAgent's _synthesize_with_llm
    because the LLM prompt engineering for different question types is extensive
    and well-tested. The key improvement is in RETRIEVAL, not synthesis.

    Args:
        agent_name: Name for the agent
        model: LLM model to use
        storage_path: Custom storage path for memory
        use_hierarchical: Must be True for multi-agent benefits
        enable_spawning: If True, enable dynamic sub-agent spawning

    Example:
        >>> agent = MultiAgentLearningAgent(
        ...     "multi_agent_eval",
        ...     use_hierarchical=True,
        ...     storage_path="/tmp/test_db",
        ...     enable_spawning=True,
        ... )
        >>> agent.learn_from_content("Sarah Chen has a tabby cat named Mochi.")
        >>> answer = agent.answer_question("What pet does Sarah Chen have?")
    """

    def __init__(
        self,
        agent_name: str = "multi_agent_learning",
        model: str | None = None,
        storage_path: Path | None = None,
        use_hierarchical: bool = True,
        enable_spawning: bool = False,
    ):
        # Initialize parent LearningAgent with hierarchical memory
        super().__init__(
            agent_name=agent_name,
            model=model,
            storage_path=storage_path,
            use_hierarchical=use_hierarchical,
        )

        # Create sub-agents that share the same memory instance
        self.coordinator = CoordinatorAgent(agent_name=agent_name)
        self.memory_agent = MemoryAgent(memory=self.memory, agent_name=agent_name)

        # Optional: Initialize spawner for dynamic sub-agent creation
        self.enable_spawning = enable_spawning
        self.spawner: AgentSpawner | None = None
        if enable_spawning:
            try:
                self.spawner = AgentSpawner(
                    parent_agent_name=agent_name,
                    parent_memory_path=str(storage_path) if storage_path else str(
                        Path.home() / ".amplihack" / "agents" / agent_name
                    ),
                )
                logger.info("Spawner initialized for MultiAgentLearningAgent '%s'", agent_name)
            except Exception as e:
                logger.warning("Failed to initialize spawner: %s", e)

    def answer_question(
        self,
        question: str,
        question_level: str = "L1",
        return_trace: bool = False,
    ) -> str | tuple[str, Any]:
        """Answer a question using multi-agent retrieval + LLM synthesis.

        Execution flow:
        1. Detect intent (inherited from parent)
        2. Coordinator classifies and creates route
        3. MemoryAgent retrieves facts using optimal strategy
        4. Parent's _synthesize_with_llm produces the answer

        Falls back to parent's answer_question if multi-agent path fails.

        Args:
            question: Question to answer
            question_level: Complexity level (L1/L2/L3/L4/L5)
            return_trace: If True, return (answer, trace) tuple

        Returns:
            Synthesized answer string (or tuple with trace)
        """
        if not question or not question.strip():
            return "Error: Question is empty"

        try:
            return self._multi_agent_answer(question, question_level, return_trace)
        except Exception as e:
            logger.warning("Multi-agent path failed, falling back to parent: %s", e)
            return super().answer_question(question, question_level, return_trace)

    def _multi_agent_answer(
        self,
        question: str,
        question_level: str,
        return_trace: bool,
    ) -> str | tuple[str, Any]:
        """Multi-agent answer pipeline.

        Args:
            question: Question text
            question_level: Complexity level
            return_trace: Whether to return reasoning trace

        Returns:
            Answer string or (answer, trace) tuple
        """
        # Step 1: Intent detection (reused from parent)
        intent = self._detect_intent(question)
        intent_type = intent.get("intent", "simple_recall")

        # Step 2: Coordinator creates execution route
        route = self.coordinator.classify(question, intent)
        logger.debug(
            "MultiAgent route: strategy=%s, reasoning=%s, type=%s",
            route.retrieval_strategy,
            route.needs_reasoning,
            route.reasoning_type,
        )

        # Step 3: MemoryAgent retrieves facts using the selected strategy
        relevant_facts = self.memory_agent.retrieve(
            question=question,
            intent=intent,
            max_facts=60 if route.needs_reasoning else 30,
        )

        # Step 3b: If spawning is enabled and this is a multi-hop question,
        # spawn a retrieval sub-agent for additional fact gathering
        if (
            self.spawner
            and route.needs_reasoning
            and route.reasoning_type in ("multi_hop", "causal", "multi_source")
        ):
            try:
                spawned_result = self._spawn_retrieval(question, route.reasoning_type)
                if spawned_result:
                    # Merge spawned results with existing facts (dedup by content)
                    existing_outcomes = {f.get("outcome", "") for f in relevant_facts}
                    for fact in spawned_result:
                        if fact.get("outcome", "") not in existing_outcomes:
                            relevant_facts.append(fact)
            except Exception as e:
                logger.debug("Spawned retrieval failed, continuing: %s", e)

        # Fall back to parent's simple retrieval if MemoryAgent finds nothing
        if not relevant_facts:
            if hasattr(self.memory, "get_all_facts"):
                relevant_facts = self.memory.get_all_facts(limit=50)

        if not relevant_facts:
            result = "I don't have enough information to answer that question."
            if return_trace:
                return result, None
            return result

        # Step 4: Sort/rerank based on intent
        if intent.get("needs_temporal"):

            def temporal_key(fact: dict) -> tuple:
                meta = fact.get("metadata", {})
                t_idx = meta.get("temporal_index", 999999) if meta else 999999
                return (t_idx, fact.get("timestamp", ""))

            relevant_facts = sorted(relevant_facts, key=temporal_key)
        elif intent_type not in ("meta_memory",):
            relevant_facts = rerank_facts_by_query(relevant_facts, question)

        # Step 5: Source-specific filtering
        source_specific_facts = self._filter_facts_by_source_reference(question, relevant_facts)
        if source_specific_facts:
            intent["source_specific_facts"] = source_specific_facts

        # Step 6: Summary nodes for knowledge overview
        if self.use_hierarchical:
            summary_nodes = self._get_summary_nodes()
            if summary_nodes:
                intent["summary_context"] = "\n".join(f"- {s['outcome']}" for s in summary_nodes)

        # Step 7: Synthesize answer (uses parent's well-tested prompt engineering)
        answer = self._synthesize_with_llm(
            question=question,
            context=relevant_facts,
            question_level=question_level,
            intent=intent,
        )

        # Step 8: Validate arithmetic if needed
        if intent.get("needs_math"):
            answer = self._validate_arithmetic(answer)

        # Build trace
        from ..agentic_loop import ReasoningTrace

        trace = ReasoningTrace(
            question=question,
            intent=intent,
            used_simple_path=True,
            total_facts_collected=len(relevant_facts),
        )
        trace.metadata = {
            "architecture": "multi_agent",
            "retrieval_strategy": route.retrieval_strategy,
            "reasoning_type": route.reasoning_type,
        }

        # Store Q&A pair
        self.memory.store_fact(
            context=f"Question: {question[:200]}",
            fact=f"Answer: {answer[:900]}",
            confidence=0.7,
            tags=["q_and_a", question_level.lower()],
        )

        if return_trace:
            return answer, trace
        return answer

    def _spawn_retrieval(
        self, question: str, reasoning_type: str
    ) -> list[dict[str, Any]]:
        """Spawn a retrieval sub-agent for multi-hop fact gathering.

        Creates a retrieval specialist that searches the parent's memory
        for additional facts related to the question. This is useful when
        the primary retrieval misses cross-referenced facts.

        Args:
            question: The question being answered
            reasoning_type: Type of reasoning needed (multi_hop, causal, etc.)

        Returns:
            List of additional fact dicts, or empty list
        """
        if not self.spawner:
            return []

        task = f"Find all facts related to: {question}"
        self.spawner.spawn(task, "retrieval")
        results = self.spawner.collect_results(timeout=15.0)

        facts: list[dict[str, Any]] = []
        for agent in results:
            if agent.status == "completed" and agent.result:
                # Parse the retrieval result back into fact dicts
                # The default retrieval executor returns "- context: outcome" lines
                for line in agent.result.split("\n"):
                    line = line.strip()
                    if line.startswith("- ") and ":" in line:
                        parts = line[2:].split(":", 1)
                        if len(parts) == 2:
                            facts.append({
                                "context": parts[0].strip(),
                                "outcome": parts[1].strip(),
                                "confidence": 0.7,
                                "metadata": {"source": "spawned_retrieval"},
                            })

        # Clear spawner for next use
        self.spawner.clear()
        return facts

    def close(self) -> None:
        """Close agent and release resources, including spawner."""
        if self.spawner:
            self.spawner.clear()
        super().close()


__all__ = ["MultiAgentLearningAgent"]
