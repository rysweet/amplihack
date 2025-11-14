from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentType(Enum):
    COORDINATOR = "coordinator"
    ANALYZER = "analyzer"
    SYNTHESIZER = "synthesizer"


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator initialization.

    Attributes:
        max_agents: Maximum number of concurrent agents (1-10)
        timeout: Workflow timeout in seconds (1-300)
        enable_logging: Enable verbose logging

    Example:
        >>> config = OrchestratorConfig(max_agents=5, timeout=30)
        >>> assert config.max_agents == 5
    """

    max_agents: int = 5
    timeout: int = 30
    enable_logging: bool = False

    def __post_init__(self):
        if not 1 <= self.max_agents <= 10:
            raise ValueError("max_agents must be between 1 and 10")
        if not 1 <= self.timeout <= 300:
            raise ValueError("timeout must be between 1 and 300 seconds")


@dataclass
class WorkflowRequest:
    """Request for workflow execution.

    Attributes:
        task: Description of the task to perform
        documents: List of document strings to process
        config: Optional configuration dictionary

    Example:
        >>> request = WorkflowRequest(
        ...     task="Synthesize documents",
        ...     documents=["doc1", "doc2"],
        ...     config={"mode": "fast"}
        ... )
    """

    task: str
    documents: List[str]
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task or not self.task.strip():
            raise ValueError("task cannot be empty")
        if not self.documents:
            raise ValueError("documents list cannot be empty")


@dataclass
class AgentResult:
    """Result from a single agent.

    Attributes:
        agent_type: Type of agent that produced this result
        status: Success or failure status
        data: Result data dictionary
        processing_time: Time taken in seconds
    """

    agent_type: AgentType
    status: str
    data: Dict[str, Any]
    processing_time: float


@dataclass
class WorkflowResult:
    """Result of workflow execution.

    Attributes:
        status: Overall status (success/error)
        data: Aggregated result data
        processing_time: Total time in seconds
        agent_results: Individual agent results
        error: Optional error message

    Example:
        >>> result = WorkflowResult(
        ...     status="success",
        ...     data={"output": "synthesized content"},
        ...     processing_time=1.5,
        ...     agent_results=[]
        ... )
    """

    status: str
    data: Dict[str, Any]
    processing_time: float
    agent_results: List[AgentResult] = field(default_factory=list)
    error: Optional[str] = None
