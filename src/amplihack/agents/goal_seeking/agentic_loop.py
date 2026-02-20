from __future__ import annotations

from collections.abc import Callable

"""Main PERCEIVE->REASON->ACT->LEARN loop for goal-seeking agents.

Philosophy:
- Single responsibility: Orchestrate agent loop
- LLM-powered reasoning via litellm
- Clear separation of concerns (perceive, reason, act, learn)
- Stateless execution (state stored in memory)
- Iterative reasoning: plan -> search -> evaluate -> refine -> answer
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import litellm

logger = logging.getLogger(__name__)


@dataclass
class LoopState:
    """State for one iteration of the agentic loop."""

    perception: str
    reasoning: str
    action: dict[str, Any]
    learning: str
    outcome: Any
    iteration: int


@dataclass
class RetrievalPlan:
    """Plan for what information to retrieve from memory."""

    search_queries: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class ReasoningStep:
    """A single step in the reasoning trace."""

    step_type: str  # "plan", "search", "evaluate", "refine"
    queries: list[str] = field(default_factory=list)
    facts_found: int = 0
    evaluation: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class ReasoningTrace:
    """Complete trace of the reasoning process for metacognition evaluation."""

    question: str = ""
    intent: dict[str, Any] = field(default_factory=dict)
    steps: list[ReasoningStep] = field(default_factory=list)
    total_facts_collected: int = 0
    total_queries_executed: int = 0
    iterations: int = 0
    final_confidence: float = 0.0
    used_simple_path: bool = False


@dataclass
class SufficiencyEvaluation:
    """Evaluation of whether collected facts are sufficient to answer."""

    sufficient: bool = False
    missing: str = ""
    confidence: float = 0.0
    refined_queries: list[str] = field(default_factory=list)


class AgenticLoop:
    """Main PERCEIVE->REASON->ACT->LEARN loop for goal-seeking agents."""

    def __init__(
        self,
        agent_name: str,
        action_executor,
        memory_retriever,
        model: str = "gpt-3.5-turbo",
        max_iterations: int = 10,
    ):
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.agent_name = agent_name.strip()
        self.action_executor = action_executor
        self.memory_retriever = memory_retriever
        self.model = model
        self.max_iterations = max_iterations
        self.iteration_count = 0

    def perceive(self, observation: str, goal: str) -> str:
        """PERCEIVE phase: Observe environment and retrieve relevant memory."""
        relevant_memories = self.memory_retriever.search(query=observation, limit=3)

        perception = f"Goal: {goal}\n"
        perception += f"Observation: {observation}\n"

        if relevant_memories:
            perception += "\nRelevant past experiences:\n"
            for i, mem in enumerate(relevant_memories, 1):
                perception += f"{i}. {mem['context']} -> {mem['outcome']}\n"

        return perception

    def reason(self, perception: str) -> dict[str, Any]:
        """REASON phase: Use LLM to decide what action to take."""
        available_actions = self.action_executor.get_available_actions()

        prompt = f"""You are a goal-seeking agent. Based on the perception, decide what action to take.

{perception}

Available actions: {", ".join(available_actions)}

Think step by step:
1. What is the current situation?
2. What action would best help achieve the goal?
3. What parameters does that action need?

Respond in this JSON format:
{{
  "reasoning": "Your reasoning here",
  "action": "action_name",
  "params": {{"param1": "value1"}}
}}
"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful goal-seeking agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            response_text = response.choices[0].message.content

            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    result = json.loads(json_str)
                    return result
                return {
                    "reasoning": "Failed to parse LLM response",
                    "action": "error",
                    "params": {"error": "Invalid LLM response format"},
                }

        except Exception as e:
            logger.error("LLM reasoning call failed: %s", e)
            return {
                "reasoning": "LLM call failed due to an internal error",
                "action": "error",
                "params": {"error": "Internal reasoning error"},
            }

    def act(self, action_decision: dict[str, Any]) -> Any:
        """ACT phase: Execute the chosen action."""
        action_name = action_decision.get("action", "")
        params = action_decision.get("params", {})

        if not action_name:
            return {"error": "No action specified"}

        result = self.action_executor.execute(action_name, **params)

        if result.success:
            return result.output
        return {"error": result.error}

    def learn(self, perception: str, reasoning: str, action: dict[str, Any], outcome: Any) -> str:
        """LEARN phase: Store experience in memory."""
        success = True
        if isinstance(outcome, dict) and "error" in outcome:
            success = False

        context = f"{perception}\nReasoning: {reasoning}"
        learning = f"Action: {action['action']} with {action.get('params', {})}\n"
        learning += f"Outcome: {outcome}"

        confidence = 0.9 if success else 0.5
        self.memory_retriever.store_fact(
            context=context[:500],
            fact=learning[:500],
            confidence=confidence,
            tags=[action["action"], "agent_loop"],
        )

        return learning

    def run_iteration(self, goal: str, observation: str) -> LoopState:
        """Run one iteration of the PERCEIVE->REASON->ACT->LEARN loop."""
        self.iteration_count += 1

        perception = self.perceive(observation, goal)
        action_decision = self.reason(perception)
        outcome = self.act(action_decision)
        learning = self.learn(
            perception=perception,
            reasoning=action_decision.get("reasoning", ""),
            action=action_decision,
            outcome=outcome,
        )

        return LoopState(
            perception=perception,
            reasoning=action_decision.get("reasoning", ""),
            action=action_decision,
            learning=learning,
            outcome=outcome,
            iteration=self.iteration_count,
        )

    def run_until_goal(
        self, goal: str, initial_observation: str, is_goal_achieved: Callable | None = None
    ) -> list[LoopState]:
        """Run loop until goal is achieved or max iterations reached."""
        states = []
        observation = initial_observation

        for _ in range(self.max_iterations):
            state = self.run_iteration(goal, observation)
            states.append(state)

            if is_goal_achieved and is_goal_achieved(state):
                break

            observation = f"Previous action result: {state.outcome}"

        return states

    # ------------------------------------------------------------------
    # Iterative reasoning: plan -> search -> evaluate -> refine -> answer
    # ------------------------------------------------------------------

    def reason_iteratively(
        self,
        question: str,
        memory,
        intent: dict[str, Any],
        max_steps: int = 3,
    ) -> tuple[list[dict[str, Any]], list[Any], ReasoningTrace]:
        """Multi-step reasoning: plan, search, evaluate, refine, answer."""
        collected_facts: list[dict[str, Any]] = []
        collected_nodes: list[Any] = []
        seen_ids: set[str] = set()
        evaluation = SufficiencyEvaluation()

        trace = ReasoningTrace(question=question, intent=intent)

        intent_type = intent.get("intent", "simple_recall")
        if intent_type in ("multi_source_synthesis", "temporal_comparison"):
            search_max_nodes = 30
        else:
            search_max_nodes = 10

        total_queries = 0
        plan = RetrievalPlan()
        step = 0

        for step in range(max_steps):
            if step == 0:
                plan = self._plan_retrieval(question, intent)
                step_type = "plan"
            else:
                plan = self._refine_retrieval(question, collected_facts, evaluation)
                step_type = "refine"

            if not plan.search_queries:
                break

            trace.steps.append(
                ReasoningStep(
                    step_type=step_type,
                    queries=list(plan.search_queries),
                    reasoning=plan.reasoning,
                )
            )

            new_facts_this_round = 0
            for query in plan.search_queries:
                total_queries += 1
                nodes, facts = self._targeted_search(
                    query, memory, seen_ids, max_nodes=search_max_nodes
                )
                for node, fact in zip(nodes, facts, strict=False):
                    nid = getattr(node, "node_id", id(node))
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        collected_nodes.append(node)
                        collected_facts.append(fact)
                        new_facts_this_round += 1

            trace.steps.append(
                ReasoningStep(
                    step_type="search",
                    queries=list(plan.search_queries),
                    facts_found=new_facts_this_round,
                )
            )

            if new_facts_this_round == 0 and step > 0:
                break

            evaluation = self._evaluate_sufficiency(question, collected_facts, intent)

            trace.steps.append(
                ReasoningStep(
                    step_type="evaluate",
                    evaluation={
                        "sufficient": evaluation.sufficient,
                        "confidence": evaluation.confidence,
                        "missing": evaluation.missing,
                    },
                )
            )

            if evaluation.sufficient or evaluation.confidence > 0.8:
                break

        trace.total_facts_collected = len(collected_facts)
        trace.total_queries_executed = total_queries
        trace.iterations = min(step + 1, max_steps) if plan.search_queries else 0
        trace.final_confidence = evaluation.confidence

        return collected_facts, collected_nodes, trace

    def _plan_retrieval(self, question: str, intent: dict[str, Any]) -> RetrievalPlan:
        """Plan what information to retrieve."""
        intent_type = intent.get("intent", "simple_recall")

        extra_instruction = ""
        if intent_type == "multi_source_synthesis":
            extra_instruction = (
                "\n\nIMPORTANT: This question requires combining information from MULTIPLE sources.\n"
                "Generate at least 3 queries covering different aspects."
            )
        elif intent_type in ("temporal_comparison", "mathematical_computation"):
            extra_instruction = (
                "\n\nIMPORTANT: This question requires comparing data across TIME PERIODS.\n"
                "Generate a SEPARATE search query for EACH time period mentioned."
            )

        prompt = f"""Given this question, what specific information do I need to find in a knowledge base?

Question: {question}
Question type: {intent_type}
{extra_instruction}

Generate 2-5 SHORT, TARGETED search queries (keywords/phrases) that would find the needed facts.

Return ONLY a JSON object:
{{"search_queries": ["query1", "query2", ...], "reasoning": "brief explanation"}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a search planner. Generate targeted search queries. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = self._parse_json_response(response.choices[0].message.content)
            if result and "search_queries" in result:
                return RetrievalPlan(
                    search_queries=result["search_queries"][:5],
                    reasoning=result.get("reasoning", ""),
                )
        except Exception as e:
            logger.debug("Plan retrieval failed: %s", e)

        return RetrievalPlan(
            search_queries=[question],
            reasoning="fallback: using original question",
        )

    def _refine_retrieval(
        self,
        question: str,
        collected_facts: list[dict[str, Any]],
        evaluation: SufficiencyEvaluation,
    ) -> RetrievalPlan:
        """Refine retrieval based on what is missing."""
        facts_summary = "\n".join(
            f"- [{f.get('context', '?')}] {f.get('outcome', '')[:80]}" for f in collected_facts[:10]
        )

        prompt = f"""I'm trying to answer: {question}

I already found these facts:
{facts_summary}

What's missing: {evaluation.missing}

Generate 2-3 NEW search queries targeting the MISSING information.

Return ONLY a JSON object:
{{"search_queries": ["query1", "query2"], "reasoning": "what these queries target"}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a search planner. Generate targeted search queries for missing information. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = self._parse_json_response(response.choices[0].message.content)
            if result and "search_queries" in result:
                return RetrievalPlan(
                    search_queries=result["search_queries"][:3],
                    reasoning=result.get("reasoning", ""),
                )
        except Exception as e:
            logger.debug("Refine retrieval failed: %s", e)

        if evaluation.refined_queries:
            return RetrievalPlan(
                search_queries=evaluation.refined_queries[:3],
                reasoning="from evaluation suggestions",
            )
        return RetrievalPlan()

    def _evaluate_sufficiency(
        self,
        question: str,
        collected_facts: list[dict[str, Any]],
        intent: dict[str, Any],
    ) -> SufficiencyEvaluation:
        """Evaluate if collected facts are sufficient."""
        if not collected_facts:
            return SufficiencyEvaluation(
                sufficient=False,
                missing="No facts found yet",
                confidence=0.0,
                refined_queries=[question],
            )

        facts_summary = "\n".join(
            f"- [{f.get('context', '?')}] {f.get('outcome', '')[:100]}"
            for f in collected_facts[:15]
        )

        intent_type = intent.get("intent", "simple_recall")
        prompt = f"""Can I answer this question with these facts?

Question: {question}
Question type: {intent_type}

Available facts:
{facts_summary}

Return ONLY a JSON object:
{{"sufficient": true/false, "missing": "what's missing or empty string", "confidence": 0.8, "refined_queries": ["query if more search needed"]}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact sufficiency evaluator. Be strict. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = self._parse_json_response(response.choices[0].message.content)
            if result:
                return SufficiencyEvaluation(
                    sufficient=bool(result.get("sufficient", False)),
                    missing=result.get("missing", ""),
                    confidence=float(result.get("confidence", 0.5)),
                    refined_queries=result.get("refined_queries", []),
                )
        except Exception as e:
            logger.debug("Evaluate sufficiency failed: %s", e)

        return SufficiencyEvaluation(
            sufficient=len(collected_facts) >= 5,
            missing="" if len(collected_facts) >= 5 else "unable to evaluate",
            confidence=0.6 if len(collected_facts) >= 5 else 0.3,
        )

    def _targeted_search(
        self,
        query: str,
        memory,
        seen_ids: set[str],
        max_nodes: int = 10,
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        """Run a targeted search against memory."""
        nodes = []
        facts = []

        if hasattr(memory, "memory") and hasattr(memory.memory, "retrieve_subgraph"):
            subgraph = memory.memory.retrieve_subgraph(query=query, max_nodes=max_nodes)
            for node in subgraph.nodes:
                if node.node_id not in seen_ids:
                    nodes.append(node)
                    facts.append(
                        {
                            "context": node.concept,
                            "outcome": node.content,
                            "confidence": node.confidence,
                            "metadata": node.metadata if node.metadata else {},
                        }
                    )
        elif hasattr(memory, "search"):
            results = memory.search(query=query, limit=max_nodes)
            for r in results:
                rid = r.get("experience_id", str(id(r)))
                if rid not in seen_ids:
                    nodes.append(r)
                    facts.append(r)
        elif hasattr(memory, "get_all_facts"):
            results = memory.get_all_facts(limit=max_nodes)
            for r in results:
                rid = r.get("experience_id", str(id(r)))
                if rid not in seen_ids:
                    nodes.append(r)
                    facts.append(r)

        return nodes, facts

    @staticmethod
    def _parse_json_response(response_text: str) -> dict[str, Any] | None:
        """Parse JSON from an LLM response, handling markdown code blocks."""
        if not response_text:
            return None

        text = response_text.strip()

        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            if json_end > json_start:
                try:
                    result = json.loads(text[json_start:json_end].strip())
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass

        if "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            if json_end > json_start:
                try:
                    result = json.loads(text[json_start:json_end].strip())
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass

        return None
