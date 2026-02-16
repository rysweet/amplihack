from __future__ import annotations
from collections.abc import Callable

"""Main PERCEIVE→REASON→ACT→LEARN loop for goal-seeking agents.

Philosophy:
- Single responsibility: Orchestrate agent loop
- LLM-powered reasoning via litellm
- Clear separation of concerns (perceive, reason, act, learn)
- Stateless execution (state stored in memory)
"""

from dataclasses import dataclass
from typing import Any

import litellm


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
