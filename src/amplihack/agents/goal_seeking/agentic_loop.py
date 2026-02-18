from __future__ import annotations

from collections.abc import Callable

"""Main PERCEIVE→REASON→ACT→LEARN loop for goal-seeking agents.

Philosophy:
- Single responsibility: Orchestrate agent loop
- LLM-powered reasoning via litellm
- Clear separation of concerns (perceive, reason, act, learn)
- Stateless execution (state stored in memory)
- Iterative reasoning: plan → search → evaluate → refine → answer
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import litellm

logger = logging.getLogger(__name__)


@dataclass
class LoopState:
    """State for one iteration of the agentic loop.

    Attributes:
        perception: What the agent observes
        reasoning: Agent's reasoning about the situation
        action: Action decided by the agent
        learning: What the agent learned from the outcome
        outcome: Result of the action
        iteration: Iteration number
    """

    perception: str
    reasoning: str
    action: dict[str, Any]
    learning: str
    outcome: Any
    iteration: int


@dataclass
class RetrievalPlan:
    """Plan for what information to retrieve from memory.

    Attributes:
        search_queries: Targeted queries to run against memory
        reasoning: Why these queries were chosen
    """

    search_queries: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class SufficiencyEvaluation:
    """Evaluation of whether collected facts are sufficient to answer.

    Attributes:
        sufficient: Whether we have enough information
        missing: Description of what is still missing
        confidence: Confidence that we can answer (0.0-1.0)
        refined_queries: New queries to try if insufficient
    """

    sufficient: bool = False
    missing: str = ""
    confidence: float = 0.0
    refined_queries: list[str] = field(default_factory=list)


class AgenticLoop:
    """Main PERCEIVE→REASON→ACT→LEARN loop for goal-seeking agents.

    Implements the core agentic loop pattern:
    1. PERCEIVE: Observe environment/input
    2. REASON: Use LLM to decide what to do
    3. ACT: Execute chosen action
    4. LEARN: Store experience in memory

    Philosophy:
    - LLM drives reasoning (not hardcoded rules)
    - Memory stores learnings for future use
    - Actions are extensible via ActionExecutor
    - Each iteration is self-contained

    Example:
        >>> from amplihack.agents.goal_seeking import AgenticLoop, ActionExecutor, MemoryRetriever
        >>> memory = MemoryRetriever("test_agent")
        >>> executor = ActionExecutor()
        >>> executor.register_action("greet", lambda name: f"Hello {name}!")
        >>>
        >>> loop = AgenticLoop(
        ...     agent_name="test_agent",
        ...     action_executor=executor,
        ...     memory_retriever=memory,
        ...     model="gpt-3.5-turbo"
        ... )
        >>>
        >>> state = loop.run_iteration(
        ...     goal="Greet the user",
        ...     observation="User named Alice is present"
        ... )
        >>> print(state.action)  # {'name': 'greet', 'params': {'name': 'Alice'}}
    """

    def __init__(
        self,
        agent_name: str,
        action_executor,
        memory_retriever,
        model: str = "gpt-3.5-turbo",
        max_iterations: int = 10,
    ):
        """Initialize agentic loop.

        Args:
            agent_name: Name of the agent
            action_executor: ActionExecutor instance
            memory_retriever: MemoryRetriever instance
            model: LLM model to use (litellm format)
            max_iterations: Maximum iterations per goal

        Raises:
            ValueError: If agent_name is empty
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.agent_name = agent_name.strip()
        self.action_executor = action_executor
        self.memory_retriever = memory_retriever
        self.model = model
        self.max_iterations = max_iterations
        self.iteration_count = 0

    def perceive(self, observation: str, goal: str) -> str:
        """PERCEIVE phase: Observe environment and retrieve relevant memory.

        Args:
            observation: Current observation/input
            goal: Current goal

        Returns:
            Perception string combining observation and relevant memory
        """
        # Search memory for relevant experiences
        relevant_memories = self.memory_retriever.search(query=observation, limit=3)

        # Build perception
        perception = f"Goal: {goal}\n"
        perception += f"Observation: {observation}\n"

        if relevant_memories:
            perception += "\nRelevant past experiences:\n"
            for i, mem in enumerate(relevant_memories, 1):
                perception += f"{i}. {mem['context']} → {mem['outcome']}\n"

        return perception

    def reason(self, perception: str) -> dict[str, Any]:
        """REASON phase: Use LLM to decide what action to take.

        Args:
            perception: Perception from perceive() phase

        Returns:
            Dictionary with:
                - reasoning: LLM's reasoning text
                - action: Chosen action name
                - params: Parameters for the action

        Note:
            This uses litellm to call the configured LLM model.
            Set OPENAI_API_KEY or other provider keys as needed.
        """
        # Get available actions
        available_actions = self.action_executor.get_available_actions()

        # Build prompt for LLM
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
            # Call LLM via litellm
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful goal-seeking agent."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            # Extract response
            response_text = response.choices[0].message.content

            # Parse JSON response
            import json

            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # Fallback: extract from markdown code block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    result = json.loads(json_str)
                    return result
                # Last resort: return error action
                return {
                    "reasoning": "Failed to parse LLM response",
                    "action": "error",
                    "params": {"error": "Invalid LLM response format"},
                }

        except Exception as e:
            return {
                "reasoning": f"LLM call failed: {e!s}",
                "action": "error",
                "params": {"error": str(e)},
            }

    def act(self, action_decision: dict[str, Any]) -> Any:
        """ACT phase: Execute the chosen action.

        Args:
            action_decision: Decision from reason() phase

        Returns:
            Result from action execution
        """
        action_name = action_decision.get("action", "")
        params = action_decision.get("params", {})

        if not action_name:
            return {"error": "No action specified"}

        result = self.action_executor.execute(action_name, **params)

        if result.success:
            return result.output
        return {"error": result.error}

    def learn(self, perception: str, reasoning: str, action: dict[str, Any], outcome: Any) -> str:
        """LEARN phase: Store experience in memory.

        Args:
            perception: What was observed
            reasoning: How the agent reasoned
            action: What action was taken
            outcome: What happened as a result

        Returns:
            Learning summary string
        """
        # Determine if outcome was successful
        success = True
        if isinstance(outcome, dict) and "error" in outcome:
            success = False

        # Build context and learning
        context = f"{perception}\nReasoning: {reasoning}"
        learning = f"Action: {action['action']} with {action.get('params', {})}\n"
        learning += f"Outcome: {outcome}"

        # Store in memory
        confidence = 0.9 if success else 0.5
        self.memory_retriever.store_fact(
            context=context[:500],  # Limit context length
            fact=learning[:500],
            confidence=confidence,
            tags=[action["action"], "agent_loop"],
        )

        return learning

    def run_iteration(self, goal: str, observation: str) -> LoopState:
        """Run one iteration of the PERCEIVE→REASON→ACT→LEARN loop.

        Args:
            goal: Current goal to achieve
            observation: Current observation

        Returns:
            LoopState with results from each phase

        Example:
            >>> loop = AgenticLoop("agent", executor, memory)
            >>> state = loop.run_iteration("Greet user", "User Alice present")
            >>> print(state.reasoning)  # LLM's reasoning
            >>> print(state.outcome)    # Action result
        """
        self.iteration_count += 1

        # PERCEIVE
        perception = self.perceive(observation, goal)

        # REASON
        action_decision = self.reason(perception)

        # ACT
        outcome = self.act(action_decision)

        # LEARN
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
        """Run loop until goal is achieved or max iterations reached.

        Args:
            goal: Goal to achieve
            initial_observation: Starting observation
            is_goal_achieved: Optional function to check if goal is met

        Returns:
            List of LoopState from each iteration

        Example:
            >>> def check_goal(state):
            ...     return "success" in str(state.outcome).lower()
            >>>
            >>> states = loop.run_until_goal(
            ...     goal="Complete task",
            ...     initial_observation="Task pending",
            ...     is_goal_achieved=check_goal
            ... )
        """
        states = []
        observation = initial_observation

        for _ in range(self.max_iterations):
            state = self.run_iteration(goal, observation)
            states.append(state)

            # Check if goal achieved
            if is_goal_achieved and is_goal_achieved(state):
                break

            # Update observation for next iteration
            observation = f"Previous action result: {state.outcome}"

        return states

    # ------------------------------------------------------------------
    # Iterative reasoning: plan → search → evaluate → refine → answer
    # ------------------------------------------------------------------

    def reason_iteratively(
        self,
        question: str,
        memory,
        intent: dict[str, Any],
        max_steps: int = 3,
    ) -> tuple[str, list[Any]]:
        """Multi-step reasoning: plan, search, evaluate, refine, answer.

        Instead of dumping all facts to the LLM, this method:
        1. PLAN - Asks the LLM what specific information is needed
        2. SEARCH - Runs targeted queries against memory
        3. EVALUATE - Checks if retrieved facts are sufficient
        4. REFINE - If not sufficient, generates new queries and loops
        5. ANSWER - Synthesizes final answer from collected facts

        Args:
            question: The question to answer
            memory: Memory object with retrieve_subgraph and/or search methods
            intent: Intent classification dict from _detect_intent()
            max_steps: Maximum retrieval rounds (default 3)

        Returns:
            Tuple of (list of collected fact dicts, list of KnowledgeNode objects)
            The caller is responsible for final synthesis.
        """
        collected_facts: list[dict[str, Any]] = []
        collected_nodes: list[Any] = []
        seen_ids: set[str] = set()
        evaluation = SufficiencyEvaluation()

        for step in range(max_steps):
            # Step 1/1b: Plan or refine retrieval
            if step == 0:
                plan = self._plan_retrieval(question, intent)
            else:
                plan = self._refine_retrieval(
                    question, collected_facts, evaluation
                )

            if not plan.search_queries:
                logger.debug(
                    "No search queries generated at step %d, stopping", step
                )
                break

            # Step 2: Targeted search for each query
            new_facts_this_round = 0
            for query in plan.search_queries:
                nodes, facts = self._targeted_search(
                    query, memory, seen_ids, max_nodes=10
                )
                for node, fact in zip(nodes, facts):
                    nid = getattr(node, "node_id", id(node))
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        collected_nodes.append(node)
                        collected_facts.append(fact)
                        new_facts_this_round += 1

            logger.debug(
                "Step %d: %d new facts from %d queries",
                step,
                new_facts_this_round,
                len(plan.search_queries),
            )

            # If no new facts found, no point evaluating again
            if new_facts_this_round == 0 and step > 0:
                break

            # Step 3: Evaluate sufficiency
            evaluation = self._evaluate_sufficiency(
                question, collected_facts, intent
            )

            if evaluation.sufficient or evaluation.confidence > 0.8:
                logger.debug(
                    "Sufficient at step %d (confidence=%.2f)",
                    step,
                    evaluation.confidence,
                )
                break

        return collected_facts, collected_nodes

    def _plan_retrieval(
        self, question: str, intent: dict[str, Any]
    ) -> RetrievalPlan:
        """Plan what information to retrieve. One short LLM call.

        Args:
            question: The question to answer
            intent: Intent classification

        Returns:
            RetrievalPlan with search queries and reasoning
        """
        intent_type = intent.get("intent", "simple_recall")
        prompt = f"""Given this question, what specific information do I need to find in a knowledge base?

Question: {question}
Question type: {intent_type}

Generate 2-4 SHORT, TARGETED search queries (keywords/phrases) that would find the needed facts.
Each query should target ONE specific piece of information.

Return ONLY a JSON object:
{{"search_queries": ["query1", "query2", ...], "reasoning": "brief explanation of search strategy"}}"""

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

            result = self._parse_json_response(
                response.choices[0].message.content
            )
            if result and "search_queries" in result:
                return RetrievalPlan(
                    search_queries=result["search_queries"][:4],
                    reasoning=result.get("reasoning", ""),
                )
        except Exception as e:
            logger.debug("Plan retrieval failed: %s", e)

        # Fallback: use the question itself as a query
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
        """Refine retrieval based on what is missing. One short LLM call.

        Args:
            question: The original question
            collected_facts: Facts collected so far
            evaluation: Previous sufficiency evaluation

        Returns:
            RetrievalPlan with refined search queries
        """
        # Summarize what we have so far (keep it short)
        facts_summary = "\n".join(
            f"- [{f.get('context', '?')}] {f.get('outcome', '')[:80]}"
            for f in collected_facts[:10]
        )

        prompt = f"""I'm trying to answer: {question}

I already found these facts:
{facts_summary}

What's missing: {evaluation.missing}

Generate 2-3 NEW search queries targeting the MISSING information.
Use different keywords than before.

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

            result = self._parse_json_response(
                response.choices[0].message.content
            )
            if result and "search_queries" in result:
                return RetrievalPlan(
                    search_queries=result["search_queries"][:3],
                    reasoning=result.get("reasoning", ""),
                )
        except Exception as e:
            logger.debug("Refine retrieval failed: %s", e)

        # Fallback: use evaluation's refined queries if available
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
        """Evaluate if collected facts are sufficient. One short LLM call.

        Args:
            question: The question to answer
            collected_facts: Facts collected so far
            intent: Intent classification

        Returns:
            SufficiencyEvaluation with assessment
        """
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

Evaluate:
1. Do I have ALL the specific data points needed?
2. What is STILL MISSING (if anything)?
3. Confidence I can answer correctly (0.0-1.0)?

Return ONLY a JSON object:
{{"sufficient": true/false, "missing": "what's missing or empty string", "confidence": 0.8, "refined_queries": ["query if more search needed"]}}"""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact sufficiency evaluator. Be strict: if key data points are missing, say so. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = self._parse_json_response(
                response.choices[0].message.content
            )
            if result:
                return SufficiencyEvaluation(
                    sufficient=bool(result.get("sufficient", False)),
                    missing=result.get("missing", ""),
                    confidence=float(result.get("confidence", 0.5)),
                    refined_queries=result.get("refined_queries", []),
                )
        except Exception as e:
            logger.debug("Evaluate sufficiency failed: %s", e)

        # Conservative fallback: assume sufficient if we have 5+ facts
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
        """Run a targeted search against memory.

        Tries retrieve_subgraph first (Graph RAG), falls back to search/get_all_facts.

        Args:
            query: Search query
            memory: Memory object (FlatRetrieverAdapter or MemoryRetriever)
            seen_ids: IDs already collected (to avoid duplicates)
            max_nodes: Max nodes to retrieve per query

        Returns:
            Tuple of (list of raw nodes, list of fact dicts)
        """
        nodes = []
        facts = []

        # Try Graph RAG subgraph retrieval first
        if hasattr(memory, "memory") and hasattr(memory.memory, "retrieve_subgraph"):
            subgraph = memory.memory.retrieve_subgraph(
                query=query, max_nodes=max_nodes
            )
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
        """Parse JSON from an LLM response, handling markdown code blocks.

        Args:
            response_text: Raw LLM response text

        Returns:
            Parsed dict or None if parsing fails
        """
        if not response_text:
            return None

        text = response_text.strip()

        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
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

        # Try extracting from generic code block
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
