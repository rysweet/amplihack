import time

try:
    from .models import AgentResult, AgentType, OrchestratorConfig, WorkflowRequest, WorkflowResult
except ImportError:
    # Fallback for direct execution/testing
    from models import AgentResult, AgentType, OrchestratorConfig, WorkflowRequest, WorkflowResult


class Agent:
    """Base agent for workflow execution."""

    def __init__(self, agent_type: AgentType, config: OrchestratorConfig):
        self.agent_type = agent_type
        self.config = config

    def process(self, documents: list[str], task: str) -> AgentResult:
        """Process documents according to agent type."""
        start_time = time.time()

        if self.agent_type == AgentType.COORDINATOR:
            data = {
                "coordinated": True,
                "agent_count": self.config.max_agents,
                "task_plan": f"Plan for: {task}",
            }
        elif self.agent_type == AgentType.ANALYZER:
            data = {
                "analyzed": True,
                "document_count": len(documents),
                "analysis": [f"Analysis of doc {i + 1}" for i in range(len(documents))],
            }
        else:
            data = {
                "synthesized": True,
                "output": f"Synthesis of {len(documents)} documents for task: {task}",
            }

        processing_time = time.time() - start_time

        return AgentResult(
            agent_type=self.agent_type, status="success", data=data, processing_time=processing_time
        )


class Orchestrator:
    """Orchestrates multi-agent workflows."""

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.agents: list[Agent] = []
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize agent pool."""
        agent_types = [AgentType.COORDINATOR, AgentType.ANALYZER, AgentType.SYNTHESIZER]

        for agent_type in agent_types[: min(3, self.config.max_agents)]:
            self.agents.append(Agent(agent_type, self.config))

        if self.config.enable_logging:
            print(f"Initialized {len(self.agents)} agents")

    def execute(self, request: WorkflowRequest) -> WorkflowResult:
        """Execute workflow with all agents."""
        start_time = time.time()
        agent_results = []

        try:
            for agent in self.agents:
                if time.time() - start_time > self.config.timeout:
                    raise TimeoutError(f"Workflow exceeded {self.config.timeout}s timeout")

                if self.config.enable_logging:
                    print(f"Executing {agent.agent_type.value} agent...")

                result = agent.process(request.documents, request.task)
                agent_results.append(result)

            processing_time = time.time() - start_time

            aggregated_data = {
                "task": request.task,
                "document_count": len(request.documents),
                "agent_count": len(agent_results),
                "results": [r.data for r in agent_results],
            }

            return WorkflowResult(
                status="success",
                data=aggregated_data,
                processing_time=processing_time,
                agent_results=agent_results,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            return WorkflowResult(
                status="error",
                data={},
                processing_time=processing_time,
                agent_results=agent_results,
                error=str(e),
            )


def initialize_orchestrator(config: OrchestratorConfig) -> Orchestrator:
    """Initialize orchestrator with given configuration.

    Args:
        config: Configuration for orchestrator setup

    Returns:
        Initialized Orchestrator instance

    Raises:
        ValueError: If config is invalid

    Example:
        >>> config = OrchestratorConfig(max_agents=3, timeout=30)
        >>> orchestrator = initialize_orchestrator(config)
        >>> assert len(orchestrator.agents) > 0
    """
    if not isinstance(config, OrchestratorConfig):
        raise ValueError("config must be OrchestratorConfig instance")

    return Orchestrator(config)


def execute_workflow(orchestrator: Orchestrator, request: WorkflowRequest) -> WorkflowResult:
    """Execute workflow on orchestrator.

    Args:
        orchestrator: Initialized orchestrator
        request: Workflow request with task and documents

    Returns:
        WorkflowResult with status and data

    Raises:
        ValueError: If request is invalid
        TimeoutError: If workflow exceeds timeout

    Example:
        >>> config = OrchestratorConfig(max_agents=3)
        >>> orchestrator = initialize_orchestrator(config)
        >>> request = WorkflowRequest(
        ...     task="Test task",
        ...     documents=["doc1", "doc2"]
        ... )
        >>> result = execute_workflow(orchestrator, request)
        >>> assert result.status == "success"
    """
    if not isinstance(request, WorkflowRequest):
        raise ValueError("request must be WorkflowRequest instance")

    return orchestrator.execute(request)
