"""Tests for BenchmarkRunner orchestration."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import using relative path from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude"))

from tools.benchmarking.runner import (
    BenchmarkRunner,
    AggregatedTaskResult,
    BenchmarkResults
)
from tools.benchmarking.agent_config import AgentConfig, TaskConfig
from tools.benchmarking.docker_manager import TrialResult


@pytest.fixture
def tmp_path(tmp_path):
    """Provide temp directory for tests."""
    return tmp_path


@pytest.fixture
def mock_agent(tmp_path):
    """Create a mock agent configuration."""
    agent_dir = tmp_path / "agents" / "test_agent"
    agent_dir.mkdir(parents=True)

    (agent_dir / "agent.yaml").write_text("required_env_vars: []")
    (agent_dir / "install.dockerfile").write_text("RUN echo 'test'")
    (agent_dir / "command_template.txt").write_text("cli '{{task_instructions}}'")

    return AgentConfig.from_directory(agent_dir)


@pytest.fixture
def mock_task(tmp_path):
    """Create a mock task configuration."""
    task_dir = tmp_path / "tasks" / "test_task"
    task_dir.mkdir(parents=True)

    (task_dir / "task.yaml").write_text("""
name: test_task
timeout_seconds: 60
test_command: python test.py
required_env_vars: []
""")
    (task_dir / "instructions.txt").write_text("Do something")

    return TaskConfig.from_directory(task_dir)


# Test 1: Discover Valid Agents
def test_discover_agents_success(tmp_path):
    """Should find all valid agent directories."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    for agent_name in ["agent1", "agent2"]:
        agent_dir = agents_dir / agent_name
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text("required_env_vars: []")
        (agent_dir / "install.dockerfile").write_text("RUN echo test")
        (agent_dir / "command_template.txt").write_text("cli '{{task_instructions}}'")

    runner = BenchmarkRunner(
        agents_dir=agents_dir,
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )

    agents = runner.discover_agents()

    assert len(agents) == 2
    assert {a.name for a in agents} == {"agent1", "agent2"}


# Test 2: Discover Agents Skips Invalid
def test_discover_agents_skips_invalid(tmp_path):
    """Should skip agents with missing files and continue."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Valid agent
    valid_agent = agents_dir / "valid"
    valid_agent.mkdir()
    (valid_agent / "agent.yaml").write_text("required_env_vars: []")
    (valid_agent / "install.dockerfile").write_text("RUN echo test")
    (valid_agent / "command_template.txt").write_text("cli '{{task_instructions}}'")

    # Invalid agent (missing command_template.txt)
    invalid_agent = agents_dir / "invalid"
    invalid_agent.mkdir()
    (invalid_agent / "agent.yaml").write_text("required_env_vars: []")

    runner = BenchmarkRunner(
        agents_dir=agents_dir,
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )
    agents = runner.discover_agents()

    assert len(agents) == 1
    assert agents[0].name == "valid"


# Test 3: Run Single Trial Success
@patch('tools.benchmarking.runner.DockerManager')
@patch('tools.benchmarking.runner.SecretsManager')
def test_run_single_trial_success(mock_secrets, mock_docker_class, tmp_path, mock_agent, mock_task):
    """Should execute agent command and test, return result."""
    # Setup base dockerfile
    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    # Mock SecretsManager
    mock_secrets.get_container_env.return_value = {}

    # Mock DockerManager instance
    mock_docker = MagicMock()
    mock_docker_class.return_value.__enter__.return_value = mock_docker

    # Mock exec_command calls: first for agent, second for test
    mock_docker.exec_command.side_effect = [
        TrialResult(score=0, duration_seconds=5.0, timed_out=False,
                   test_output="agent output", exit_code=0),
        TrialResult(score=0, duration_seconds=1.0, timed_out=False,
                   test_output='{"score": 85}', exit_code=0)
    ]

    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    result = runner.run_single_trial(mock_agent, mock_task, trial_num=1)

    assert result.score == 85
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.duration_seconds == 6.0  # 5.0 + 1.0


# Test 4: Run Single Trial Timeout Handling
@patch('tools.benchmarking.runner.DockerManager')
@patch('tools.benchmarking.runner.SecretsManager')
def test_run_single_trial_timeout(mock_secrets, mock_docker_class, tmp_path, mock_agent, mock_task):
    """Should handle timeout gracefully and return timed_out=True."""
    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    mock_secrets.get_container_env.return_value = {}

    mock_docker = MagicMock()
    mock_docker_class.return_value.__enter__.return_value = mock_docker

    # Mock agent command timeout, test still runs
    mock_docker.exec_command.side_effect = [
        TrialResult(score=0, duration_seconds=600.0, timed_out=True,
                   test_output="", exit_code=124),
        TrialResult(score=0, duration_seconds=1.0, timed_out=False,
                   test_output='{"score": 0}', exit_code=0)
    ]

    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    result = runner.run_single_trial(mock_agent, mock_task)

    assert result.timed_out is True
    assert result.exit_code == 0  # Test command exit code
    assert result.score == 0


# Test 5: Run Multi-Trial Aggregation
def test_run_multi_trial_aggregation(tmp_path, mock_agent, mock_task):
    """Should run N trials and compute statistics."""
    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    # Mock 3 trials with scores: 80, 90, 100
    mock_results = [
        TrialResult(score=80, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0),
        TrialResult(score=90, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0),
        TrialResult(score=100, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0)
    ]

    with patch.object(runner, 'run_single_trial', side_effect=mock_results):
        aggregated = runner.run_multi_trial(mock_agent, mock_task, num_trials=3)

    assert aggregated.mean_score == 90.0
    assert aggregated.median_score == 90.0
    assert aggregated.min_score == 80
    assert aggregated.max_score == 100
    assert aggregated.num_perfect_trials == 1
    assert aggregated.total_trials == 3


# Test 6: Run Benchmark Matrix All Combinations
def test_run_benchmark_matrix_all(tmp_path):
    """Should run all (agent, task) combinations."""
    # Setup directories
    agents_dir = tmp_path / "agents"
    tasks_dir = tmp_path / "tasks"
    agents_dir.mkdir()
    tasks_dir.mkdir()

    # Create 2 agents
    for i in [1, 2]:
        agent_dir = agents_dir / f"agent{i}"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text("required_env_vars: []")
        (agent_dir / "install.dockerfile").write_text("RUN echo test")
        (agent_dir / "command_template.txt").write_text("cli '{{task_instructions}}'")

    # Create 2 tasks
    for i in [1, 2]:
        task_dir = tasks_dir / f"task{i}"
        task_dir.mkdir()
        (task_dir / "task.yaml").write_text(f"""
name: task{i}
timeout_seconds: 60
test_command: python test.py
required_env_vars: []
""")
        (task_dir / "instructions.txt").write_text("Do something")

    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    runner = BenchmarkRunner(
        agents_dir=agents_dir,
        tasks_dir=tasks_dir,
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    # Mock aggregated result
    mock_aggregated = AggregatedTaskResult(
        mean_score=75.0,
        median_score=75.0,
        std_dev=5.0,
        min_score=70,
        max_score=80,
        num_perfect_trials=0,
        total_trials=3,
        trial_results=[]
    )

    with patch.object(runner, 'run_multi_trial', return_value=mock_aggregated):
        results = runner.run_benchmark_matrix(num_trials=3)

    # Should run 2 * 2 = 4 combinations
    assert len(results.agent_task_results) == 4
    assert results.num_agents == 2
    assert results.num_tasks == 2
    assert results.total_trials == 12  # 4 combinations * 3 trials


# Test 7: Run Benchmark Matrix Subset
def test_run_benchmark_matrix_subset(tmp_path):
    """Should run only specified agents and tasks."""
    agents_dir = tmp_path / "agents"
    tasks_dir = tmp_path / "tasks"
    agents_dir.mkdir()
    tasks_dir.mkdir()

    # Create 3 agents
    for i in [1, 2, 3]:
        agent_dir = agents_dir / f"agent{i}"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text("required_env_vars: []")
        (agent_dir / "install.dockerfile").write_text("RUN echo test")
        (agent_dir / "command_template.txt").write_text("cli '{{task_instructions}}'")

    # Create 3 tasks
    for i in [1, 2, 3]:
        task_dir = tasks_dir / f"task{i}"
        task_dir.mkdir()
        (task_dir / "task.yaml").write_text(f"""
name: task{i}
timeout_seconds: 60
test_command: python test.py
required_env_vars: []
""")
        (task_dir / "instructions.txt").write_text("Do something")

    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    runner = BenchmarkRunner(
        agents_dir=agents_dir,
        tasks_dir=tasks_dir,
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    mock_aggregated = AggregatedTaskResult(
        mean_score=75.0, median_score=75.0, std_dev=5.0,
        min_score=70, max_score=80, num_perfect_trials=0,
        total_trials=1, trial_results=[]
    )

    with patch.object(runner, 'run_multi_trial', return_value=mock_aggregated):
        results = runner.run_benchmark_matrix(
            agent_names=["agent1", "agent2"],
            task_names=["task1"],
            num_trials=1
        )

    # Should run 2 agents * 1 task = 2 combinations
    assert len(results.agent_task_results) == 2


# Test 8: Environment Variable Merging
@patch('tools.benchmarking.runner.DockerManager')
@patch('tools.benchmarking.runner.SecretsManager')
def test_environment_merging(mock_secrets, mock_docker_class, tmp_path):
    """Should merge agent and task required env vars."""
    # Create agent with env vars
    agent_dir = tmp_path / "agents" / "test_agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "agent.yaml").write_text("""
required_env_vars:
  - ANTHROPIC_API_KEY
  - SHARED
""")
    (agent_dir / "install.dockerfile").write_text("RUN echo test")
    (agent_dir / "command_template.txt").write_text("cli '{{task_instructions}}'")
    agent = AgentConfig.from_directory(agent_dir)

    # Create task with env vars
    task_dir = tmp_path / "tasks" / "test_task"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text("""
name: test_task
timeout_seconds: 60
test_command: python test.py
required_env_vars:
  - OPENAI_API_KEY
  - SHARED
""")
    (task_dir / "instructions.txt").write_text("Do something")
    task = TaskConfig.from_directory(task_dir)

    base_dockerfile = tmp_path / "base.dockerfile"
    base_dockerfile.write_text("FROM python:3.11-slim")

    # Setup mocks
    mock_secrets.get_container_env.return_value = {}
    mock_docker = MagicMock()
    mock_docker_class.return_value.__enter__.return_value = mock_docker
    mock_docker.exec_command.side_effect = [
        TrialResult(score=0, duration_seconds=1.0, timed_out=False,
                   test_output="", exit_code=0),
        TrialResult(score=0, duration_seconds=1.0, timed_out=False,
                   test_output='{"score": 50}', exit_code=0)
    ]

    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=base_dockerfile,
        results_dir=tmp_path / "results"
    )

    runner.run_single_trial(agent, task)

    # Should call with merged list
    called_vars = mock_secrets.get_container_env.call_args[0][0]
    assert set(called_vars) == {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SHARED"}


# Test 9: Test Scoring from JSON Output
def test_parse_test_score_json(tmp_path):
    """Should extract score from test.py JSON output."""
    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )

    # Mock test execution returns JSON with score
    test_output = '{"score": 75, "details": "mostly correct"}'

    score = runner._parse_test_score(test_output)

    assert score == 75


# Test 10: Test Scoring Fallback on Non-JSON
def test_parse_test_score_fallback(tmp_path):
    """Should use exit code heuristic if output not JSON."""
    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )

    # Non-JSON output
    test_output = "Test passed!"
    exit_code = 0

    score = runner._parse_test_score(test_output, exit_code)

    assert score == 50  # Default for passed non-JSON test


# Additional Edge Cases

def test_discover_agents_no_valid_agents(tmp_path):
    """Should raise ValueError if no valid agents found."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    runner = BenchmarkRunner(
        agents_dir=agents_dir,
        tasks_dir=tmp_path / "tasks",
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )

    with pytest.raises(ValueError, match="No valid agents found"):
        runner.discover_agents()


def test_discover_tasks_no_valid_tasks(tmp_path):
    """Should raise ValueError if no valid tasks found."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    runner = BenchmarkRunner(
        agents_dir=tmp_path / "agents",
        tasks_dir=tasks_dir,
        base_dockerfile_path=tmp_path / "base.dockerfile",
        results_dir=tmp_path / "results"
    )

    with pytest.raises(ValueError, match="No valid tasks found"):
        runner.discover_tasks()


def test_benchmark_results_to_json(tmp_path):
    """Should serialize BenchmarkResults to JSON."""
    results = BenchmarkResults(
        agent_task_results={
            ("agent1", "task1"): AggregatedTaskResult(
                mean_score=85.0, median_score=85.0, std_dev=5.0,
                min_score=80, max_score=90, num_perfect_trials=0,
                total_trials=3, trial_results=[]
            )
        },
        num_agents=1,
        num_tasks=1,
        total_trials=3,
        start_time=datetime(2025, 1, 1, 12, 0, 0),
        end_time=datetime(2025, 1, 1, 12, 5, 0),
        duration_seconds=300.0
    )

    json_output = results.to_json()
    parsed = json.loads(json_output)

    assert parsed["num_agents"] == 1
    assert parsed["num_tasks"] == 1
    assert parsed["total_trials"] == 3
    assert parsed["duration_seconds"] == 300.0
    assert "agent1_task1" in parsed["results"]


def test_benchmark_results_to_markdown(tmp_path):
    """Should format BenchmarkResults as Markdown."""
    results = BenchmarkResults(
        agent_task_results={
            ("agent1", "task1"): AggregatedTaskResult(
                mean_score=85.0, median_score=85.0, std_dev=5.0,
                min_score=80, max_score=90, num_perfect_trials=0,
                total_trials=3, trial_results=[]
            )
        },
        num_agents=1,
        num_tasks=1,
        total_trials=3,
        start_time=datetime(2025, 1, 1, 12, 0, 0),
        end_time=datetime(2025, 1, 1, 12, 5, 0),
        duration_seconds=300.0
    )

    markdown = results.to_markdown()

    assert "# Benchmark Results" in markdown
    assert "**Agents**: 1" in markdown
    assert "**Tasks**: 1" in markdown
    assert "| agent1 | task1 |" in markdown


def test_aggregated_task_result_from_trials():
    """Should compute statistics correctly from trials."""
    trials = [
        TrialResult(score=80, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0),
        TrialResult(score=90, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0),
        TrialResult(score=100, duration_seconds=5.0, timed_out=False,
                   test_output="", exit_code=0)
    ]

    result = AggregatedTaskResult.from_trials(trials)

    assert result.mean_score == 90.0
    assert result.median_score == 90.0
    assert result.min_score == 80
    assert result.max_score == 100
    assert result.num_perfect_trials == 1
    assert result.total_trials == 3
    assert result.std_dev > 0  # Should have some std deviation
