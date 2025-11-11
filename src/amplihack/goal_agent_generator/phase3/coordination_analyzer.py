"""
CoordinationAnalyzer: Determines if a goal requires multi-agent coordination.

Analyzes execution plans to determine optimal coordination strategy.
Triggers multi-agent coordination for complex goals with 6+ phases,
multiple domains, or estimated duration > 1 hour.
"""

from typing import List, Set
from ..models import ExecutionPlan, CoordinationStrategy, PlanPhase


class CoordinationAnalyzer:
    """Analyzes execution plans to determine coordination strategy."""

    # Thresholds for triggering multi-agent coordination
    PHASE_COUNT_THRESHOLD = 6
    DURATION_THRESHOLD_MINUTES = 60
    DOMAIN_DIVERSITY_THRESHOLD = 3

    # Coordination overhead costs
    PARALLEL_OVERHEAD = 0.15  # 15% overhead for parallel coordination
    SEQUENTIAL_OVERHEAD = 0.05  # 5% overhead for sequential coordination
    HYBRID_OVERHEAD = 0.20  # 20% overhead for hybrid coordination

    def analyze(self, execution_plan: ExecutionPlan) -> CoordinationStrategy:
        """
        Analyze execution plan and determine coordination strategy.

        Args:
            execution_plan: The execution plan to analyze

        Returns:
            CoordinationStrategy with recommendation

        Example:
            >>> analyzer = CoordinationAnalyzer()
            >>> strategy = analyzer.analyze(complex_plan)
            >>> assert strategy.coordination_type in ["single", "multi_parallel", "multi_sequential", "hybrid"]
        """
        # Calculate complexity metrics
        phase_count = len(execution_plan.phases)
        estimated_minutes = self._estimate_duration_minutes(execution_plan.total_estimated_duration)
        domain_diversity = self._calculate_domain_diversity(execution_plan.phases)
        parallelization_potential = self._calculate_parallelization_potential(execution_plan)

        # Determine if multi-agent coordination is needed
        needs_coordination = self._needs_coordination(
            phase_count, estimated_minutes, domain_diversity
        )

        if not needs_coordination:
            return CoordinationStrategy(
                coordination_type="single",
                agent_count=1,
                agent_groupings=[],
                coordination_overhead=0.0,
                parallelization_benefit=0.0,
                recommendation_reason="Goal is simple enough for single agent execution"
            )

        # Determine best coordination type
        if parallelization_potential > 0.6 and len(execution_plan.parallel_opportunities) > 0:
            return self._create_parallel_strategy(execution_plan, parallelization_potential)
        elif parallelization_potential < 0.3:
            return self._create_sequential_strategy(execution_plan)
        else:
            return self._create_hybrid_strategy(execution_plan, parallelization_potential)

    def _needs_coordination(
        self, phase_count: int, estimated_minutes: float, domain_diversity: int
    ) -> bool:
        """
        Determine if goal needs multi-agent coordination.

        Args:
            phase_count: Number of phases in plan
            estimated_minutes: Estimated duration in minutes
            domain_diversity: Number of distinct domains/capabilities

        Returns:
            True if multi-agent coordination recommended
        """
        return (
            phase_count >= self.PHASE_COUNT_THRESHOLD
            or estimated_minutes >= self.DURATION_THRESHOLD_MINUTES
            or domain_diversity >= self.DOMAIN_DIVERSITY_THRESHOLD
        )

    def _estimate_duration_minutes(self, duration_str: str) -> float:
        """
        Parse duration string to minutes.

        Args:
            duration_str: Human-readable duration like "2 hours", "30 minutes"

        Returns:
            Duration in minutes
        """
        duration_str = duration_str.lower()

        # Parse hours
        if "hour" in duration_str:
            parts = duration_str.split()
            for i, part in enumerate(parts):
                if "hour" in part and i > 0:
                    try:
                        hours = float(parts[i - 1])
                        return hours * 60
                    except ValueError:
                        pass

        # Parse minutes
        if "minute" in duration_str or "min" in duration_str:
            parts = duration_str.split()
            for i, part in enumerate(parts):
                if ("minute" in part or "min" in part) and i > 0:
                    try:
                        return float(parts[i - 1])
                    except ValueError:
                        pass

        # Parse days
        if "day" in duration_str:
            parts = duration_str.split()
            for i, part in enumerate(parts):
                if "day" in part and i > 0:
                    try:
                        days = float(parts[i - 1])
                        return days * 24 * 60
                    except ValueError:
                        pass

        # Default to 30 minutes if unparseable
        return 30.0

    def _calculate_domain_diversity(self, phases: List[PlanPhase]) -> int:
        """
        Calculate number of distinct domains/capability areas.

        Args:
            phases: List of execution plan phases

        Returns:
            Number of distinct capability domains
        """
        all_capabilities: Set[str] = set()
        for phase in phases:
            all_capabilities.update(phase.required_capabilities)

        # Group capabilities by domain (first word typically indicates domain)
        domains: Set[str] = set()
        for capability in all_capabilities:
            # Extract domain from capability name (e.g., "data-processing" from "data-processing-csv")
            domain = capability.split("-")[0] if "-" in capability else capability.split("_")[0]
            domains.add(domain)

        return len(domains)

    def _calculate_parallelization_potential(self, execution_plan: ExecutionPlan) -> float:
        """
        Calculate potential benefit from parallelization.

        Args:
            execution_plan: The execution plan to analyze

        Returns:
            Parallelization potential score (0-1)
        """
        total_phases = len(execution_plan.phases)
        if total_phases == 0:
            return 0.0

        # Count phases that can run in parallel
        parallel_phase_count = sum(
            len(group) for group in execution_plan.parallel_opportunities
        )

        # Count phases with no dependencies
        independent_phases = sum(
            1 for phase in execution_plan.phases if not phase.dependencies
        )

        # Calculate potential: weighted average of parallel groups and independence
        group_score = parallel_phase_count / total_phases if total_phases > 0 else 0.0
        independence_score = independent_phases / total_phases if total_phases > 0 else 0.0

        return (0.6 * group_score + 0.4 * independence_score)

    def _create_parallel_strategy(
        self, execution_plan: ExecutionPlan, parallelization_potential: float
    ) -> CoordinationStrategy:
        """
        Create strategy for parallel multi-agent execution.

        Args:
            execution_plan: The execution plan
            parallelization_potential: Score indicating parallelization benefit

        Returns:
            CoordinationStrategy for parallel execution
        """
        # Group phases by parallel opportunities
        agent_groupings = []
        assigned_phases: Set[str] = set()

        # First, assign parallel groups
        for parallel_group in execution_plan.parallel_opportunities:
            if parallel_group and not any(p in assigned_phases for p in parallel_group):
                agent_groupings.append(parallel_group)
                assigned_phases.update(parallel_group)

        # Assign remaining phases to separate agents
        for phase in execution_plan.phases:
            if phase.name not in assigned_phases:
                agent_groupings.append([phase.name])
                assigned_phases.add(phase.name)

        agent_count = len(agent_groupings)

        return CoordinationStrategy(
            coordination_type="multi_parallel",
            agent_count=agent_count,
            agent_groupings=agent_groupings,
            coordination_overhead=self.PARALLEL_OVERHEAD,
            parallelization_benefit=parallelization_potential,
            recommendation_reason=(
                f"High parallelization potential ({parallelization_potential:.1%}) with "
                f"{len(execution_plan.parallel_opportunities)} parallel opportunities. "
                f"Splitting into {agent_count} parallel agents will reduce total execution time."
            )
        )

    def _create_sequential_strategy(self, execution_plan: ExecutionPlan) -> CoordinationStrategy:
        """
        Create strategy for sequential multi-agent execution.

        Args:
            execution_plan: The execution plan

        Returns:
            CoordinationStrategy for sequential execution
        """
        # Group phases by dependencies to create sequential chain
        agent_groupings = self._group_by_dependency_chains(execution_plan.phases)
        agent_count = len(agent_groupings)

        return CoordinationStrategy(
            coordination_type="multi_sequential",
            agent_count=agent_count,
            agent_groupings=agent_groupings,
            coordination_overhead=self.SEQUENTIAL_OVERHEAD,
            parallelization_benefit=0.1,  # Low benefit but better modularity
            recommendation_reason=(
                f"Phases have strong dependencies requiring sequential execution. "
                f"Splitting into {agent_count} specialized agents improves modularity "
                f"and allows independent failure handling."
            )
        )

    def _create_hybrid_strategy(
        self, execution_plan: ExecutionPlan, parallelization_potential: float
    ) -> CoordinationStrategy:
        """
        Create hybrid strategy combining parallel and sequential execution.

        Args:
            execution_plan: The execution plan
            parallelization_potential: Score indicating parallelization benefit

        Returns:
            CoordinationStrategy for hybrid execution
        """
        # Create groups that balance parallelization and dependencies
        agent_groupings = []
        assigned_phases: Set[str] = set()

        # Start with parallel opportunities
        for parallel_group in execution_plan.parallel_opportunities:
            if parallel_group and not any(p in assigned_phases for p in parallel_group):
                agent_groupings.append(parallel_group)
                assigned_phases.update(parallel_group)

        # Group remaining phases by dependency chains
        remaining_phases = [p for p in execution_plan.phases if p.name not in assigned_phases]
        dependency_groups = self._group_by_dependency_chains(remaining_phases)
        agent_groupings.extend(dependency_groups)

        agent_count = len(agent_groupings)

        return CoordinationStrategy(
            coordination_type="hybrid",
            agent_count=agent_count,
            agent_groupings=agent_groupings,
            coordination_overhead=self.HYBRID_OVERHEAD,
            parallelization_benefit=parallelization_potential * 0.8,  # Reduced due to hybrid nature
            recommendation_reason=(
                f"Mixed parallelization potential ({parallelization_potential:.1%}) with "
                f"some dependencies. Using {agent_count} agents in hybrid coordination "
                f"balances parallel execution with dependency management."
            )
        )

    def _group_by_dependency_chains(self, phases: List[PlanPhase]) -> List[List[str]]:
        """
        Group phases into dependency chains.

        Args:
            phases: List of phases to group

        Returns:
            List of phase name groups representing dependency chains
        """
        if not phases:
            return []

        # Build dependency graph
        phase_map = {phase.name: phase for phase in phases}
        dependents: dict[str, List[str]] = {phase.name: [] for phase in phases}

        for phase in phases:
            for dep in phase.dependencies:
                if dep in dependents:
                    dependents[dep].append(phase.name)

        # Find root phases (no dependencies within this set)
        roots = [
            phase.name for phase in phases
            if not phase.dependencies or not any(dep in phase_map for dep in phase.dependencies)
        ]

        # Build chains from roots
        chains: List[List[str]] = []
        visited: Set[str] = set()

        for root in roots:
            if root not in visited:
                chain = self._build_chain(root, dependents, visited)
                if chain:
                    chains.append(chain)

        # Add any remaining phases as individual chains
        for phase in phases:
            if phase.name not in visited:
                chains.append([phase.name])
                visited.add(phase.name)

        return chains

    def _build_chain(
        self, start: str, dependents: dict[str, List[str]], visited: Set[str]
    ) -> List[str]:
        """
        Build dependency chain starting from a root phase.

        Args:
            start: Starting phase name
            dependents: Map of phase name to dependent phases
            visited: Set of already visited phases

        Returns:
            List of phase names in dependency order
        """
        chain = [start]
        visited.add(start)

        # Follow the longest dependency path
        current = start
        while current in dependents and dependents[current]:
            # Find unvisited dependent
            next_phase = None
            for dep in dependents[current]:
                if dep not in visited:
                    next_phase = dep
                    break

            if next_phase:
                chain.append(next_phase)
                visited.add(next_phase)
                current = next_phase
            else:
                break

        return chain
