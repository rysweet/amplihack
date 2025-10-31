try:
    import pytest
except ImportError:
    raise ImportError("pytest is required to run tests. Install with: pip install pytest")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import initialize_orchestrator, execute_workflow  # type: ignore
from models import OrchestratorConfig, WorkflowRequest, AgentType  # type: ignore


class TestOrchestratorInitialization:
    """Test orchestrator initialization"""

    def test_initialize_with_valid_config(self):
        config = OrchestratorConfig(max_agents=3, timeout=30)
        orchestrator = initialize_orchestrator(config)

        assert orchestrator is not None
        assert len(orchestrator.agents) > 0
        assert len(orchestrator.agents) <= 3

    def test_initialize_with_invalid_config(self):
        with pytest.raises(ValueError):
            OrchestratorConfig(max_agents=20)

    def test_agents_initialized_correctly(self):
        config = OrchestratorConfig(max_agents=5, enable_logging=False)
        orchestrator = initialize_orchestrator(config)

        agent_types = [agent.agent_type for agent in orchestrator.agents]
        assert AgentType.COORDINATOR in agent_types
        assert AgentType.ANALYZER in agent_types
        assert AgentType.SYNTHESIZER in agent_types


class TestWorkflowExecution:
    """Test workflow execution"""

    def test_execute_simple_workflow(self):
        config = OrchestratorConfig(max_agents=3, timeout=30)
        orchestrator = initialize_orchestrator(config)

        request = WorkflowRequest(task="Test synthesis", documents=["doc1", "doc2"], config={})

        result = execute_workflow(orchestrator, request)

        assert result.status == "success"
        assert result.processing_time > 0
        assert len(result.agent_results) > 0

    def test_execute_with_multiple_documents(self):
        config = OrchestratorConfig(max_agents=3, timeout=30)
        orchestrator = initialize_orchestrator(config)

        request = WorkflowRequest(
            task="Process multiple docs", documents=[f"doc{i}" for i in range(10)], config={}
        )

        result = execute_workflow(orchestrator, request)

        assert result.status == "success"
        assert result.data["document_count"] == 10

    def test_workflow_timeout(self):
        config = OrchestratorConfig(max_agents=3, timeout=1)
        orchestrator = initialize_orchestrator(config)

        request = WorkflowRequest(task="Slow task", documents=["doc1"] * 100, config={})

        result = execute_workflow(orchestrator, request)

        assert result.status == "error"
        if result.error:
            assert "timeout" in result.error.lower()


class TestRequestValidation:
    """Test request validation"""

    def test_empty_task_raises_error(self):
        with pytest.raises(ValueError):
            WorkflowRequest(task="", documents=["doc1"])

    def test_empty_documents_raises_error(self):
        with pytest.raises(ValueError):
            WorkflowRequest(task="Test", documents=[])

    def test_valid_request(self):
        request = WorkflowRequest(task="Valid task", documents=["doc1"], config={"key": "value"})

        assert request.task == "Valid task"
        assert len(request.documents) == 1
        assert request.config["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
