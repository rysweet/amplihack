"""Benchmark orchestration: coordinates all bricks to run agent benchmarks."""

import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from .agent_config import AgentConfig, TaskConfig
from .docker_manager import DockerManager, TrialResult
from .secrets_manager import SecretsManager

logger = logging.getLogger(__name__)


@dataclass
class AggregatedTaskResult:
    """Multiple trials aggregated with statistics."""
    mean_score: float
    median_score: float
    std_dev: float
    min_score: int
    max_score: int
    num_perfect_trials: int
    total_trials: int
    trial_results: List[TrialResult]

    @staticmethod
    def from_trials(trials: List[TrialResult]) -> 'AggregatedTaskResult':
        """
        Compute statistics from trial list.

        Args:
            trials: List of trial results

        Returns:
            AggregatedTaskResult: Computed statistics
        """
        scores = [t.score for t in trials]

        mean_score = statistics.mean(scores) if scores else 0.0
        median_score = statistics.median(scores) if scores else 0.0
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        num_perfect_trials = sum(1 for s in scores if s == 100)

        return AggregatedTaskResult(
            mean_score=mean_score,
            median_score=median_score,
            std_dev=std_dev,
            min_score=min_score,
            max_score=max_score,
            num_perfect_trials=num_perfect_trials,
            total_trials=len(trials),
            trial_results=trials
        )


@dataclass
class BenchmarkResults:
    """Results from complete benchmark run."""
    agent_task_results: Dict[Tuple[str, str], AggregatedTaskResult]
    num_agents: int
    num_tasks: int
    total_trials: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float

    def to_json(self) -> str:
        """Serialize results to JSON."""
        data = {
            "num_agents": self.num_agents,
            "num_tasks": self.num_tasks,
            "total_trials": self.total_trials,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "results": {
                f"{agent}_{task}": {
                    "mean_score": result.mean_score,
                    "median_score": result.median_score,
                    "std_dev": result.std_dev,
                    "min_score": result.min_score,
                    "max_score": result.max_score,
                    "num_perfect_trials": result.num_perfect_trials,
                    "total_trials": result.total_trials
                }
                for (agent, task), result in self.agent_task_results.items()
            }
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """Format results as Markdown table."""
        lines = [
            "# Benchmark Results",
            "",
            f"- **Agents**: {self.num_agents}",
            f"- **Tasks**: {self.num_tasks}",
            f"- **Total Trials**: {self.total_trials}",
            f"- **Duration**: {self.duration_seconds:.1f}s",
            "",
            "## Results Matrix",
            "",
            "| Agent | Task | Mean | Median | Std Dev | Min | Max | Perfect |",
            "|-------|------|------|--------|---------|-----|-----|---------|"
        ]

        for (agent, task), result in sorted(self.agent_task_results.items()):
            lines.append(
                f"| {agent} | {task} | {result.mean_score:.1f} | "
                f"{result.median_score:.1f} | {result.std_dev:.1f} | "
                f"{result.min_score} | {result.max_score} | "
                f"{result.num_perfect_trials}/{result.total_trials} |"
            )

        return "\n".join(lines)


class BenchmarkRunner:
    """Orchestrates agent benchmarking on multiple tasks."""

    def __init__(
        self,
        agents_dir: Path,
        tasks_dir: Path,
        base_dockerfile_path: Path,
        results_dir: Path
    ):
        """
        Initialize benchmark runner.

        Args:
            agents_dir: Directory containing agent subdirectories
            tasks_dir: Directory containing task subdirectories
            base_dockerfile_path: Path to base.dockerfile
            results_dir: Directory to store results
        """
        self.agents_dir = Path(agents_dir)
        self.tasks_dir = Path(tasks_dir)
        self.base_dockerfile_path = Path(base_dockerfile_path)
        self.results_dir = Path(results_dir)

        # Cached discovered agents and tasks
        self._agents: Optional[List[AgentConfig]] = None
        self._tasks: Optional[List[TaskConfig]] = None

    def discover_agents(self) -> List[AgentConfig]:
        """
        Discover and load all valid agent configurations.

        Returns:
            list: Validated AgentConfig instances

        Raises:
            ValueError: If no valid agents found
        """
        if self._agents is not None:
            return self._agents

        if not self.agents_dir.exists():
            raise ValueError(f"Agents directory not found: {self.agents_dir}")

        agents = []

        # Scan for agent subdirectories
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            try:
                agent = AgentConfig.from_directory(agent_dir)
                agent.validate()
                agents.append(agent)
                logger.info(f"Discovered agent: {agent.name}")
            except Exception as e:
                logger.warning(f"Skipping invalid agent {agent_dir.name}: {e}")
                continue

        if not agents:
            raise ValueError(f"No valid agents found in {self.agents_dir}")

        self._agents = agents
        return agents

    def discover_tasks(self) -> List[TaskConfig]:
        """
        Discover and load all valid task configurations.

        Returns:
            list: Validated TaskConfig instances

        Raises:
            ValueError: If no valid tasks found
        """
        if self._tasks is not None:
            return self._tasks

        if not self.tasks_dir.exists():
            raise ValueError(f"Tasks directory not found: {self.tasks_dir}")

        tasks = []

        # Scan for task subdirectories
        for task_dir in self.tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue

            try:
                task = TaskConfig.from_directory(task_dir)
                task.validate()
                tasks.append(task)
                logger.info(f"Discovered task: {task.name}")
            except Exception as e:
                logger.warning(f"Skipping invalid task {task_dir.name}: {e}")
                continue

        if not tasks:
            raise ValueError(f"No valid tasks found in {self.tasks_dir}")

        self._tasks = tasks
        return tasks

    def _parse_test_score(self, test_output: str, exit_code: int = 0) -> int:
        """
        Extract score from test output.

        Args:
            test_output: Output from test command
            exit_code: Test command exit code

        Returns:
            int: Score (0-100)
        """
        # Try to parse as JSON first
        try:
            result = json.loads(test_output.strip())
            if isinstance(result, dict) and "score" in result:
                return int(result["score"])
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: use exit code heuristic
        if exit_code == 0:
            return 50  # Default for passed non-JSON test
        else:
            return 0

    def run_single_trial(
        self,
        agent: AgentConfig,
        task: TaskConfig,
        trial_num: int = 1
    ) -> TrialResult:
        """
        Execute single trial: agent on task.

        Args:
            agent: Agent configuration
            task: Task configuration
            trial_num: Trial number for logging

        Returns:
            TrialResult: Execution result with score

        Raises:
            RuntimeError: If trial execution fails
        """
        logger.info(f"Running trial {trial_num}: {agent.name} on {task.name}")

        # Merge required environment variables
        merged_vars = agent.get_all_required_vars(task.required_env_vars)

        # Get container environment
        try:
            container_env = SecretsManager.get_container_env(merged_vars)
        except ValueError as e:
            raise RuntimeError(f"Failed to prepare environment: {e}")

        # Load base dockerfile
        if not self.base_dockerfile_path.exists():
            raise RuntimeError(f"Base dockerfile not found: {self.base_dockerfile_path}")
        base_dockerfile = self.base_dockerfile_path.read_text()

        # Create image tag
        image_tag = f"eval-recipes/{agent.name}:latest"

        # Execute in Docker container
        try:
            with DockerManager(
                base_dockerfile=base_dockerfile,
                agent_dockerfile=agent.install_dockerfile,
                agent_name=agent.name,
                image_tag=image_tag,
                container_env=container_env
            ) as dm:
                # Render and execute agent command
                rendered_command = agent.render_command(task.instructions)
                agent_result = dm.exec_command(rendered_command, timeout_seconds=task.timeout_seconds)

                # Execute test command
                test_result = dm.exec_command(task.test_command, timeout_seconds=60)

                # Parse score from test output
                score = self._parse_test_score(test_result.test_output, test_result.exit_code)

                # Create final result combining both executions
                final_result = TrialResult(
                    score=score,
                    duration_seconds=agent_result.duration_seconds + test_result.duration_seconds,
                    timed_out=agent_result.timed_out or test_result.timed_out,
                    test_output=test_result.test_output,
                    exit_code=test_result.exit_code,
                    error_message=agent_result.error_message or test_result.error_message
                )

                logger.info(f"Trial {trial_num} completed: score={score}, duration={final_result.duration_seconds:.1f}s")
                return final_result

        except Exception as e:
            logger.error(f"Trial {trial_num} failed: {e}")
            raise RuntimeError(f"Trial execution failed: {e}")

    def run_multi_trial(
        self,
        agent: AgentConfig,
        task: TaskConfig,
        num_trials: int = 3
    ) -> AggregatedTaskResult:
        """
        Execute multiple trials and aggregate results.

        Args:
            agent: Agent configuration
            task: Task configuration
            num_trials: Number of trials to run

        Returns:
            AggregatedTaskResult: Statistics across trials

        Raises:
            RuntimeError: If all trials fail
        """
        logger.info(f"Running {num_trials} trials: {agent.name} on {task.name}")

        results = []
        for trial_num in range(1, num_trials + 1):
            try:
                result = self.run_single_trial(agent, task, trial_num)
                results.append(result)
            except RuntimeError as e:
                logger.error(f"Trial {trial_num} failed: {e}")
                # Add failed result
                results.append(TrialResult(
                    score=0,
                    duration_seconds=0.0,
                    timed_out=False,
                    test_output="",
                    exit_code=1,
                    error_message=str(e)
                ))

        if not results:
            raise RuntimeError(f"All {num_trials} trials failed")

        return AggregatedTaskResult.from_trials(results)

    def run_benchmark_matrix(
        self,
        agent_names: Optional[List[str]] = None,
        task_names: Optional[List[str]] = None,
        num_trials: int = 3
    ) -> BenchmarkResults:
        """
        Run complete benchmark: all agents on all tasks.

        Args:
            agent_names: Subset of agents to run (None = all)
            task_names: Subset of tasks to run (None = all)
            num_trials: Trials per (agent, task) pair

        Returns:
            BenchmarkResults: Complete results matrix

        Raises:
            ValueError: If specified agents/tasks not found
        """
        start_time = datetime.now()

        # Discover agents and tasks
        all_agents = self.discover_agents()
        all_tasks = self.discover_tasks()

        # Filter agents if specified
        if agent_names is not None:
            agents = [a for a in all_agents if a.name in agent_names]
            missing = set(agent_names) - {a.name for a in agents}
            if missing:
                available = [a.name for a in all_agents]
                raise ValueError(f"Agents not found: {missing}. Available: {available}")
        else:
            agents = all_agents

        # Filter tasks if specified
        if task_names is not None:
            tasks = [t for t in all_tasks if t.name in task_names]
            missing = set(task_names) - {t.name for t in tasks}
            if missing:
                available = [t.name for t in all_tasks]
                raise ValueError(f"Tasks not found: {missing}. Available: {available}")
        else:
            tasks = all_tasks

        logger.info(f"Running benchmark matrix: {len(agents)} agents x {len(tasks)} tasks x {num_trials} trials")

        # Run all combinations
        results = {}
        total_combinations = len(agents) * len(tasks)
        current_combination = 0

        for agent in agents:
            for task in tasks:
                current_combination += 1
                logger.info(f"Progress: {current_combination}/{total_combinations} - {agent.name} on {task.name}")

                try:
                    aggregated = self.run_multi_trial(agent, task, num_trials)
                    results[(agent.name, task.name)] = aggregated
                except RuntimeError as e:
                    logger.error(f"Failed combination {agent.name} + {task.name}: {e}")
                    # Store failed result
                    results[(agent.name, task.name)] = AggregatedTaskResult(
                        mean_score=0.0,
                        median_score=0.0,
                        std_dev=0.0,
                        min_score=0,
                        max_score=0,
                        num_perfect_trials=0,
                        total_trials=num_trials,
                        trial_results=[]
                    )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return BenchmarkResults(
            agent_task_results=results,
            num_agents=len(agents),
            num_tasks=len(tasks),
            total_trials=len(agents) * len(tasks) * num_trials,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
