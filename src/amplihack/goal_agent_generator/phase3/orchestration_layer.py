"""
OrchestrationLayer: Orchestrates execution of multiple coordinated agents.

Manages async execution, enforces dependency order (DAG execution),
handles partial failures, and coordinates communication between agents.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from ..models import AgentDependencyGraph, SubAgentDefinition
from .shared_state_manager import SharedStateManager
from .coordination_protocol import CoordinationProtocol, MessageType


class OrchestrationResult:
    """Result of orchestrating multi-agent execution."""

    def __init__(self):
        """Initialize orchestration result."""
        self.success: bool = False
        self.completed_agents: List[uuid.UUID] = []
        self.failed_agents: List[uuid.UUID] = []
        self.skipped_agents: List[uuid.UUID] = []
        self.total_duration_seconds: float = 0.0
        self.error_messages: Dict[uuid.UUID, str] = {}
        self.agent_outputs: Dict[uuid.UUID, Dict] = {}

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate (0-1)."""
        total = len(self.completed_agents) + len(self.failed_agents) + len(self.skipped_agents)
        if total == 0:
            return 0.0
        return len(self.completed_agents) / total

    def __str__(self) -> str:
        """String representation."""
        return (
            f"OrchestrationResult(success={self.success}, "
            f"completed={len(self.completed_agents)}, "
            f"failed={len(self.failed_agents)}, "
            f"skipped={len(self.skipped_agents)})"
        )


class OrchestrationLayer:
    """Orchestrates execution of multiple coordinated agents."""

    def __init__(
        self,
        state_manager: SharedStateManager,
        max_concurrent_agents: int = 5,
        timeout_seconds: float = 3600.0,
    ):
        """
        Initialize orchestration layer.

        Args:
            state_manager: Shared state manager for coordination
            max_concurrent_agents: Maximum agents to run concurrently
            timeout_seconds: Timeout for entire orchestration

        Example:
            >>> state_manager = SharedStateManager()
            >>> orchestrator = OrchestrationLayer(state_manager)
        """
        self.state_manager = state_manager
        self.max_concurrent_agents = max_concurrent_agents
        self.timeout_seconds = timeout_seconds
        self._running_agents: Set[uuid.UUID] = set()
        self._agent_tasks: Dict[uuid.UUID, asyncio.Task] = {}

    async def orchestrate(
        self, dependency_graph: AgentDependencyGraph
    ) -> OrchestrationResult:
        """
        Orchestrate execution of agents according to dependency graph.

        Args:
            dependency_graph: Graph of agents and dependencies

        Returns:
            OrchestrationResult with execution summary

        Example:
            >>> orchestrator = OrchestrationLayer(state_manager)
            >>> result = await orchestrator.orchestrate(graph)
            >>> assert result.success or len(result.failed_agents) > 0
        """
        result = OrchestrationResult()
        start_time = datetime.utcnow()

        try:
            # Validate graph
            if not dependency_graph.nodes:
                result.success = True
                return result

            # Execute layers in topological order
            for layer_index, layer in enumerate(dependency_graph.execution_order):
                await self._execute_layer(layer, dependency_graph, result)

                # Check if we should continue after this layer
                if not self._should_continue(result, dependency_graph):
                    break

            # Determine overall success
            result.success = (
                len(result.failed_agents) == 0
                and len(result.completed_agents) == len(dependency_graph.nodes)
            )

        except asyncio.TimeoutError:
            result.error_messages[uuid.uuid4()] = "Orchestration timeout exceeded"
            result.success = False

        except Exception as e:
            result.error_messages[uuid.uuid4()] = f"Orchestration error: {str(e)}"
            result.success = False

        finally:
            # Calculate duration
            end_time = datetime.utcnow()
            result.total_duration_seconds = (end_time - start_time).total_seconds()

            # Cancel any remaining tasks
            await self._cleanup_tasks()

        return result

    async def _execute_layer(
        self,
        layer: List[uuid.UUID],
        dependency_graph: AgentDependencyGraph,
        result: OrchestrationResult,
    ) -> None:
        """
        Execute a layer of agents in parallel.

        Args:
            layer: List of agent IDs in this layer
            dependency_graph: Complete dependency graph
            result: Result object to update

        Side effects:
            Updates result with completed/failed agents
        """
        # Filter out agents whose dependencies failed
        executable_agents = self._filter_executable_agents(
            layer, dependency_graph, result.failed_agents
        )

        # Skip agents whose dependencies failed
        skipped = set(layer) - set(executable_agents)
        result.skipped_agents.extend(skipped)

        if not executable_agents:
            return

        # Execute agents in batches to respect concurrency limit
        for batch in self._create_batches(executable_agents, self.max_concurrent_agents):
            tasks = [
                self._execute_agent(agent_id, dependency_graph.nodes[agent_id])
                for agent_id in batch
            ]

            # Wait for batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for agent_id, agent_result in zip(batch, batch_results):
                if isinstance(agent_result, Exception):
                    result.failed_agents.append(agent_id)
                    result.error_messages[agent_id] = str(agent_result)
                    # Publish failure message
                    msg = CoordinationProtocol.create_message(
                        MessageType.AGENT_FAILED,
                        agent_id,
                        {
                            "agent_id": str(agent_id),
                            "timestamp": datetime.utcnow().isoformat(),
                            "error": str(agent_result),
                        },
                    )
                    self.state_manager.publish_message(msg)
                else:
                    result.completed_agents.append(agent_id)
                    result.agent_outputs[agent_id] = agent_result or {}
                    # Publish completion message
                    msg = CoordinationProtocol.create_agent_completed(
                        agent_id, "success", outputs=agent_result
                    )
                    self.state_manager.publish_message(msg)

    async def _execute_agent(
        self, agent_id: uuid.UUID, agent_def: SubAgentDefinition
    ) -> Dict:
        """
        Execute a single agent.

        Args:
            agent_id: Agent ID
            agent_def: Agent definition

        Returns:
            Agent execution outputs

        Raises:
            Exception: If agent execution fails
        """
        self._running_agents.add(agent_id)

        try:
            # Publish start message
            msg = CoordinationProtocol.create_agent_started(
                agent_id, agent_def.name, agent_def.role
            )
            self.state_manager.publish_message(msg)

            # Set initial state
            self.state_manager.set(f"agent.{agent_id}.status", "running", agent_id)
            self.state_manager.set(f"agent.{agent_id}.progress", 0.0, agent_id)

            # Execute agent phases
            outputs = await self._execute_agent_phases(agent_id, agent_def)

            # Update final state
            self.state_manager.set(f"agent.{agent_id}.status", "completed", agent_id)
            self.state_manager.set(f"agent.{agent_id}.progress", 1.0, agent_id)

            return outputs

        finally:
            self._running_agents.discard(agent_id)

    async def _execute_agent_phases(
        self, agent_id: uuid.UUID, agent_def: SubAgentDefinition
    ) -> Dict:
        """
        Execute all phases for an agent.

        Args:
            agent_id: Agent ID
            agent_def: Agent definition

        Returns:
            Dictionary of phase outputs
        """
        if not agent_def.execution_plan:
            return {}

        phase_outputs = {}
        total_phases = len(agent_def.execution_plan.phases)

        for index, phase in enumerate(agent_def.execution_plan.phases):
            # Update progress
            progress = (index / total_phases) if total_phases > 0 else 0.0
            self.state_manager.set(f"agent.{agent_id}.progress", progress, agent_id)

            # Publish phase start
            msg = CoordinationProtocol.create_message(
                MessageType.PHASE_STARTED,
                agent_id,
                {
                    "agent_id": str(agent_id),
                    "phase_name": phase.name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "phase_index": index,
                    "total_phases": total_phases,
                },
            )
            self.state_manager.publish_message(msg)

            # Execute phase (simulated - in real implementation would call actual phase execution)
            try:
                phase_start = datetime.utcnow()
                output = await self._simulate_phase_execution(agent_id, phase, agent_def)
                phase_end = datetime.utcnow()
                duration = (phase_end - phase_start).total_seconds()

                phase_outputs[phase.name] = output

                # Store output in shared state
                state_key = f"phase.{phase.name}.output"
                self.state_manager.set(state_key, output, agent_id)
                self.state_manager.set(f"phase.{phase.name}.status", "completed", agent_id)

                # Publish phase completion
                msg = CoordinationProtocol.create_phase_completed(
                    agent_id,
                    phase.name,
                    success=True,
                    outputs=output,
                    duration_seconds=duration,
                )
                self.state_manager.publish_message(msg)

                # Notify that data is available
                data_msg = CoordinationProtocol.create_data_available(
                    agent_id, state_key, "dict", {"phase": phase.name}
                )
                self.state_manager.publish_message(data_msg)

            except Exception as e:
                # Phase failed
                self.state_manager.set(f"phase.{phase.name}.status", "failed", agent_id)

                # Publish phase failure
                msg = CoordinationProtocol.create_message(
                    MessageType.PHASE_FAILED,
                    agent_id,
                    {
                        "agent_id": str(agent_id),
                        "phase_name": phase.name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": str(e),
                        "retry_count": 0,
                        "will_retry": False,
                    },
                )
                self.state_manager.publish_message(msg)

                raise

        return phase_outputs

    async def _simulate_phase_execution(
        self,
        agent_id: uuid.UUID,
        phase,
        agent_def: SubAgentDefinition,
    ) -> Dict:
        """
        Simulate phase execution (placeholder for actual execution).

        In a real implementation, this would:
        1. Load required data from shared state
        2. Execute phase logic using agent skills
        3. Return outputs

        Args:
            agent_id: Agent ID
            phase: Phase to execute
            agent_def: Agent definition

        Returns:
            Simulated phase outputs
        """
        # Simulate some work
        await asyncio.sleep(0.1)

        # Check dependencies are available
        for dep_phase in phase.dependencies:
            dep_key = f"phase.{dep_phase}.output"
            dep_output = self.state_manager.get(dep_key)
            if dep_output is None:
                raise ValueError(f"Dependency phase '{dep_phase}' output not available")

        # Return simulated output
        return {
            "status": "completed",
            "phase_name": phase.name,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": str(agent_id),
        }

    def _filter_executable_agents(
        self,
        layer: List[uuid.UUID],
        dependency_graph: AgentDependencyGraph,
        failed_agents: List[uuid.UUID],
    ) -> List[uuid.UUID]:
        """
        Filter agents whose dependencies have not failed.

        Args:
            layer: Layer of agent IDs
            dependency_graph: Complete graph
            failed_agents: List of failed agent IDs

        Returns:
            List of executable agent IDs
        """
        executable = []
        failed_set = set(failed_agents)

        for agent_id in layer:
            # Get agent's dependencies
            deps = dependency_graph.edges.get(agent_id, [])

            # Check if any dependency failed
            if not any(dep in failed_set for dep in deps):
                executable.append(agent_id)

        return executable

    def _create_batches(
        self, items: List[uuid.UUID], batch_size: int
    ) -> List[List[uuid.UUID]]:
        """
        Create batches of items for concurrent execution.

        Args:
            items: List of items to batch
            batch_size: Maximum batch size

        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i : i + batch_size])
        return batches

    def _should_continue(
        self, result: OrchestrationResult, dependency_graph: AgentDependencyGraph
    ) -> bool:
        """
        Determine if orchestration should continue.

        Args:
            result: Current result
            dependency_graph: Dependency graph

        Returns:
            True if should continue, False to stop
        """
        # Continue if no failures
        if not result.failed_agents:
            return True

        # Stop if critical agent failed (leader or monitor)
        for agent_id in result.failed_agents:
            agent = dependency_graph.nodes.get(agent_id)
            if agent and agent.role in ["leader", "monitor"]:
                return False

        # Continue with graceful degradation
        return True

    async def _cleanup_tasks(self) -> None:
        """Cancel and cleanup any running tasks."""
        for task in self._agent_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for cancellation
        if self._agent_tasks:
            await asyncio.gather(*self._agent_tasks.values(), return_exceptions=True)

        self._agent_tasks.clear()
        self._running_agents.clear()

    def get_running_agents(self) -> List[uuid.UUID]:
        """
        Get list of currently running agent IDs.

        Returns:
            List of agent IDs

        Example:
            >>> orchestrator = OrchestrationLayer(state_manager)
            >>> running = orchestrator.get_running_agents()
        """
        return list(self._running_agents)

    async def wait_for_agent(self, agent_id: uuid.UUID, timeout: Optional[float] = None) -> bool:
        """
        Wait for specific agent to complete.

        Args:
            agent_id: Agent ID to wait for
            timeout: Timeout in seconds (optional)

        Returns:
            True if agent completed, False if timeout

        Example:
            >>> completed = await orchestrator.wait_for_agent(agent_id, timeout=30)
        """
        if agent_id not in self._agent_tasks:
            return False

        try:
            if timeout:
                await asyncio.wait_for(self._agent_tasks[agent_id], timeout=timeout)
            else:
                await self._agent_tasks[agent_id]
            return True
        except asyncio.TimeoutError:
            return False
