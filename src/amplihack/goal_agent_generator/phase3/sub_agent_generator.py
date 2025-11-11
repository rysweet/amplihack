"""
SubAgentGenerator: Generates coordinated sub-agents from complex goals.

Creates multiple coordinated sub-agents, each responsible for a subset of phases.
Generates dependency graph and assigns roles (leader, worker, monitor).
"""

import uuid
from typing import List, Dict, Set
from ..models import (
    GoalDefinition,
    ExecutionPlan,
    PlanPhase,
    SkillDefinition,
    SubAgentDefinition,
    AgentDependencyGraph,
    CoordinationStrategy,
)


class SubAgentGenerator:
    """Generates coordinated sub-agents from complex execution plans."""

    def generate(
        self,
        goal_definition: GoalDefinition,
        execution_plan: ExecutionPlan,
        available_skills: List[SkillDefinition],
        coordination_strategy: CoordinationStrategy,
    ) -> AgentDependencyGraph:
        """
        Generate sub-agents based on coordination strategy.

        Args:
            goal_definition: Original goal definition
            execution_plan: Complete execution plan
            available_skills: Pool of available skills
            coordination_strategy: Strategy for coordination

        Returns:
            AgentDependencyGraph with all sub-agents and dependencies

        Example:
            >>> generator = SubAgentGenerator()
            >>> graph = generator.generate(goal, plan, skills, strategy)
            >>> assert len(graph.nodes) == strategy.agent_count
        """
        if coordination_strategy.coordination_type == "single":
            # Single agent - no sub-agent generation needed
            return self._create_single_agent_graph(
                goal_definition, execution_plan, available_skills
            )

        # Create sub-agents based on groupings
        sub_agents = self._create_sub_agents(
            goal_definition,
            execution_plan,
            available_skills,
            coordination_strategy,
        )

        # Build dependency graph
        graph = self._build_dependency_graph(sub_agents, execution_plan)

        # Assign roles based on graph structure
        self._assign_roles(graph, coordination_strategy)

        # Calculate execution order (topological sort)
        graph.execution_order = self._topological_sort(graph)

        return graph

    def _create_single_agent_graph(
        self,
        goal_definition: GoalDefinition,
        execution_plan: ExecutionPlan,
        available_skills: List[SkillDefinition],
    ) -> AgentDependencyGraph:
        """
        Create graph with single agent (no coordination needed).

        Args:
            goal_definition: Goal definition
            execution_plan: Execution plan
            available_skills: Available skills

        Returns:
            Graph with single agent
        """
        agent = SubAgentDefinition(
            name=f"agent-{goal_definition.domain}",
            role="leader",
            goal_definition=goal_definition,
            execution_plan=execution_plan,
            skills=available_skills,
            dependencies=[],
            shared_state_keys=[],
            coordination_protocol="v1",
        )

        return AgentDependencyGraph(
            nodes={agent.id: agent},
            edges={agent.id: []},
            execution_order=[[agent.id]],
        )

    def _create_sub_agents(
        self,
        goal_definition: GoalDefinition,
        execution_plan: ExecutionPlan,
        available_skills: List[SkillDefinition],
        coordination_strategy: CoordinationStrategy,
    ) -> List[SubAgentDefinition]:
        """
        Create sub-agents based on phase groupings.

        Args:
            goal_definition: Original goal
            execution_plan: Complete plan
            available_skills: Available skills
            coordination_strategy: Coordination strategy

        Returns:
            List of sub-agent definitions
        """
        sub_agents: List[SubAgentDefinition] = []
        phase_map = {phase.name: phase for phase in execution_plan.phases}

        for i, phase_group in enumerate(coordination_strategy.agent_groupings):
            # Get phases for this agent
            agent_phases = [phase_map[name] for name in phase_group if name in phase_map]

            if not agent_phases:
                continue

            # Create sub-goal for this agent
            sub_goal = self._create_sub_goal(goal_definition, agent_phases, i)

            # Create execution plan for this agent
            sub_plan = self._create_sub_plan(execution_plan, agent_phases)

            # Match skills to agent's capabilities
            agent_skills = self._match_skills(agent_phases, available_skills)

            # Determine shared state keys this agent needs
            shared_state_keys = self._determine_shared_state_keys(agent_phases, i)

            # Create sub-agent
            sub_agent = SubAgentDefinition(
                name=f"agent-{i+1}-{sub_goal.domain}",
                role="worker",  # Will be updated later based on graph
                goal_definition=sub_goal,
                execution_plan=sub_plan,
                skills=agent_skills,
                dependencies=[],  # Will be populated when building graph
                shared_state_keys=shared_state_keys,
                coordination_protocol="v1",
            )

            sub_agents.append(sub_agent)

        return sub_agents

    def _create_sub_goal(
        self, original_goal: GoalDefinition, phases: List[PlanPhase], agent_index: int
    ) -> GoalDefinition:
        """
        Create sub-goal for a sub-agent.

        Args:
            original_goal: Original goal definition
            phases: Phases assigned to this agent
            agent_index: Index of this agent

        Returns:
            Sub-goal definition
        """
        # Summarize phases into sub-goal
        phase_descriptions = [phase.description for phase in phases]
        sub_goal_text = f"Sub-goal {agent_index + 1}: " + "; ".join(phase_descriptions)

        # Collect capabilities to determine sub-domain
        all_capabilities = set()
        for phase in phases:
            all_capabilities.update(phase.required_capabilities)

        # Determine sub-domain from capabilities
        sub_domain = self._infer_domain(all_capabilities) or original_goal.domain

        return GoalDefinition(
            raw_prompt=sub_goal_text,
            goal=sub_goal_text,
            domain=sub_domain,
            constraints=original_goal.constraints,
            success_criteria=[ind for phase in phases for ind in phase.success_indicators],
            context={
                "parent_goal": original_goal.goal,
                "agent_index": agent_index,
                "phase_count": len(phases),
            },
            complexity=original_goal.complexity,
        )

    def _create_sub_plan(
        self, original_plan: ExecutionPlan, phases: List[PlanPhase]
    ) -> ExecutionPlan:
        """
        Create execution plan for sub-agent.

        Args:
            original_plan: Original execution plan
            phases: Phases for this sub-agent

        Returns:
            Sub-execution plan
        """
        # Calculate total duration for these phases
        total_minutes = sum(self._parse_duration_minutes(p.estimated_duration) for p in phases)
        total_duration = self._format_duration(total_minutes)

        # Collect required skills
        required_skills = list(
            set(cap for phase in phases for cap in phase.required_capabilities)
        )

        # Find parallel opportunities within this subset
        parallel_opportunities = self._find_parallel_opportunities(phases)

        return ExecutionPlan(
            goal_id=original_plan.goal_id,
            phases=phases,
            total_estimated_duration=total_duration,
            required_skills=required_skills,
            parallel_opportunities=parallel_opportunities,
            risk_factors=[],  # Subset may have different risks
        )

    def _match_skills(
        self, phases: List[PlanPhase], available_skills: List[SkillDefinition]
    ) -> List[SkillDefinition]:
        """
        Match skills to agent's required capabilities.

        Args:
            phases: Agent's phases
            required_capabilities: Capabilities needed
            available_skills: Pool of available skills

        Returns:
            List of matching skills
        """
        required_capabilities = set(cap for phase in phases for cap in phase.required_capabilities)
        matched_skills: List[SkillDefinition] = []

        for skill in available_skills:
            # Check if skill provides any required capability
            if any(cap in skill.capabilities for cap in required_capabilities):
                matched_skills.append(skill)

        return matched_skills

    def _determine_shared_state_keys(
        self, phases: List[PlanPhase], agent_index: int
    ) -> List[str]:
        """
        Determine which shared state keys this agent needs access to.

        Args:
            phases: Agent's phases
            agent_index: Index of this agent

        Returns:
            List of shared state keys
        """
        keys: List[str] = []

        # Add input/output keys for each phase
        for phase in phases:
            # Input from previous phases
            if phase.dependencies:
                for dep in phase.dependencies:
                    keys.append(f"phase.{dep}.output")

            # Output for this phase
            keys.append(f"phase.{phase.name}.output")
            keys.append(f"phase.{phase.name}.status")

        # Add agent-level keys
        keys.append(f"agent.{agent_index}.status")
        keys.append(f"agent.{agent_index}.progress")

        return keys

    def _build_dependency_graph(
        self, sub_agents: List[SubAgentDefinition], execution_plan: ExecutionPlan
    ) -> AgentDependencyGraph:
        """
        Build dependency graph from sub-agents and their phases.

        Args:
            sub_agents: List of sub-agents
            execution_plan: Original execution plan

        Returns:
            Dependency graph
        """
        # Create maps for easy lookup
        phase_to_agent: Dict[str, uuid.UUID] = {}
        for agent in sub_agents:
            if agent.execution_plan:
                for phase in agent.execution_plan.phases:
                    phase_to_agent[phase.name] = agent.id

        # Build edges based on phase dependencies
        nodes = {agent.id: agent for agent in sub_agents}
        edges: Dict[uuid.UUID, List[uuid.UUID]] = {agent.id: [] for agent in sub_agents}

        for agent in sub_agents:
            if not agent.execution_plan:
                continue

            dependencies: Set[uuid.UUID] = set()

            for phase in agent.execution_plan.phases:
                # Find which agents own the dependency phases
                for dep_phase_name in phase.dependencies:
                    if dep_phase_name in phase_to_agent:
                        dep_agent_id = phase_to_agent[dep_phase_name]
                        if dep_agent_id != agent.id:
                            dependencies.add(dep_agent_id)

            # Update agent dependencies
            agent.dependencies = list(dependencies)
            edges[agent.id] = list(dependencies)

        return AgentDependencyGraph(nodes=nodes, edges=edges, execution_order=[])

    def _assign_roles(
        self, graph: AgentDependencyGraph, coordination_strategy: CoordinationStrategy
    ) -> None:
        """
        Assign roles (leader, worker, monitor) based on graph structure.

        Args:
            graph: Dependency graph
            coordination_strategy: Coordination strategy

        Side effects:
            Modifies agent roles in graph.nodes
        """
        # Find root agents (no dependencies)
        roots = [agent_id for agent_id, deps in graph.edges.items() if not deps]

        # Find leaf agents (no dependents)
        has_dependents = set()
        for deps in graph.edges.values():
            has_dependents.update(deps)
        leaves = [agent_id for agent_id in graph.nodes if agent_id not in has_dependents]

        # Assign leader role to first root (or first agent if no roots)
        if roots:
            leader_id = roots[0]
        elif graph.nodes:
            leader_id = next(iter(graph.nodes))
        else:
            return

        graph.nodes[leader_id].role = "leader"

        # Assign monitor role to last leaf (if different from leader)
        if leaves and leaves[-1] != leader_id:
            monitor_id = leaves[-1]
            graph.nodes[monitor_id].role = "monitor"

        # All others are workers (already default)

    def _topological_sort(self, graph: AgentDependencyGraph) -> List[List[uuid.UUID]]:
        """
        Perform topological sort to determine execution order.

        Args:
            graph: Dependency graph

        Returns:
            List of layers, where each layer contains agents that can run in parallel

        Example:
            >>> # Layer 0: agents with no dependencies
            >>> # Layer 1: agents depending only on layer 0
            >>> # Layer 2: agents depending on layers 0 and/or 1
        """
        # In graph.edges, each node maps to its DEPENDENCIES
        # So in_degree is the number of dependencies (length of list)
        in_degree: Dict[uuid.UUID, int] = {
            agent_id: len(deps) for agent_id, deps in graph.edges.items()
        }

        # Initialize with nodes having no dependencies
        layers: List[List[uuid.UUID]] = []
        current_layer = [agent_id for agent_id, degree in in_degree.items() if degree == 0]

        while current_layer:
            layers.append(current_layer)
            next_layer: List[uuid.UUID] = []

            # Process current layer - for each node in current layer,
            # find nodes that depend on it and decrement their in-degree
            for agent_id in current_layer:
                # Find all nodes that have this agent as a dependency
                for other_id, deps in graph.edges.items():
                    if agent_id in deps:
                        in_degree[other_id] -= 1
                        if in_degree[other_id] == 0:
                            next_layer.append(other_id)

            current_layer = next_layer

        # Check for cycles
        if sum(1 for _ in graph.nodes) != sum(len(layer) for layer in layers):
            # Cycle detected - return single layer with all nodes as fallback
            return [[agent_id for agent_id in graph.nodes]]

        return layers

    # Helper methods

    def _parse_duration_minutes(self, duration_str: str) -> float:
        """Parse duration string to minutes."""
        duration_str = duration_str.lower()

        if "hour" in duration_str:
            parts = duration_str.split()
            for i, part in enumerate(parts):
                if "hour" in part and i > 0:
                    try:
                        return float(parts[i - 1]) * 60
                    except ValueError:
                        pass

        if "minute" in duration_str or "min" in duration_str:
            parts = duration_str.split()
            for i, part in enumerate(parts):
                if ("minute" in part or "min" in part) and i > 0:
                    try:
                        return float(parts[i - 1])
                    except ValueError:
                        pass

        return 15.0  # Default

    def _format_duration(self, minutes: float) -> str:
        """Format minutes as human-readable duration."""
        if minutes < 60:
            return f"{int(minutes)} minutes"
        else:
            hours = minutes / 60
            return f"{hours:.1f} hours"

    def _infer_domain(self, capabilities: Set[str]) -> str:
        """Infer domain from capability names."""
        if not capabilities:
            return "general"

        # Extract first word from capabilities as domain indicator
        domains = [cap.split("-")[0] if "-" in cap else cap.split("_")[0] for cap in capabilities]

        # Return most common domain
        domain_counts = {}
        for domain in domains:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return max(domain_counts.items(), key=lambda x: x[1])[0]

    def _find_parallel_opportunities(self, phases: List[PlanPhase]) -> List[List[str]]:
        """Find phases that can run in parallel within this subset."""
        if not phases:
            return []

        parallel_groups: List[List[str]] = []
        processed: Set[str] = set()

        for phase in phases:
            if phase.name in processed or not phase.parallel_safe:
                continue

            # Find other phases that can run in parallel with this one
            group = [phase.name]
            processed.add(phase.name)

            for other in phases:
                if (
                    other.name not in processed
                    and other.parallel_safe
                    and not self._has_dependency_relationship(phase, other, phases)
                ):
                    group.append(other.name)
                    processed.add(other.name)

            if len(group) > 1:
                parallel_groups.append(group)

        return parallel_groups

    def _has_dependency_relationship(
        self, phase1: PlanPhase, phase2: PlanPhase, all_phases: List[PlanPhase]
    ) -> bool:
        """Check if two phases have a dependency relationship."""
        # Direct dependency
        if phase1.name in phase2.dependencies or phase2.name in phase1.dependencies:
            return True

        # Transitive dependency (simplified check)
        phase1_ancestors = set(phase1.dependencies)
        phase2_ancestors = set(phase2.dependencies)

        return bool(
            phase1.name in phase2_ancestors
            or phase2.name in phase1_ancestors
            or phase1_ancestors.intersection(phase2_ancestors)
        )
