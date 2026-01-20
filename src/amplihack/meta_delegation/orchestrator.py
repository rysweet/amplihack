"""Meta-Delegator Orchestrator Module.

This module coordinates the complete meta-delegation lifecycle, managing all
components and handling the delegation workflow from start to finish.

Delegation Phases:
1. Initialization: Load persona and platform, validate parameters
2. Subprocess Spawn: Start AI assistant subprocess
3. Monitoring: Track execution state, handle timeouts
4. Evidence Collection: Gather artifacts during and after execution
5. Success Evaluation: Score completion against criteria
6. Cleanup: Terminate subprocess, finalize results

Philosophy:
- Clear phase separation
- Comprehensive error handling
- Resource cleanup guaranteed
- Timeout and failure handling
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .evidence_collector import EvidenceCollector, EvidenceItem
from .persona import get_persona_strategy
from .platform_cli import get_platform_cli
from .scenario_generator import GadugiScenarioGenerator, TestScenario
from .state_machine import ProcessState, SubprocessStateMachine
from .success_evaluator import SuccessCriteriaEvaluator


class DelegationTimeout(Exception):
    """Exception raised when delegation exceeds timeout."""

    def __init__(self, elapsed_minutes: float, timeout_minutes: float):
        self.elapsed_minutes = elapsed_minutes
        self.timeout_minutes = timeout_minutes
        super().__init__(
            f"Delegation timed out after {elapsed_minutes:.1f} minutes "
            f"(timeout: {timeout_minutes:.1f} minutes)"
        )


class DelegationError(Exception):
    """Exception raised for delegation errors."""

    def __init__(self, reason: str, exit_code: Optional[int] = None):
        self.reason = reason
        self.exit_code = exit_code
        super().__init__(f"Delegation failed: {reason}")


@dataclass
class MetaDelegationResult:
    """Result of meta-delegation execution.

    Attributes:
        status: Status (SUCCESS, PARTIAL, FAILURE)
        success_score: Score from 0-100
        evidence: List of collected evidence items
        execution_log: Subprocess execution log
        duration_seconds: Total execution time
        persona_used: Persona that was used
        platform_used: Platform that was used
        failure_reason: Reason for failure (if FAILURE)
        partial_completion_notes: Notes on partial completion (if PARTIAL)
        subprocess_pid: Process ID of subprocess
        test_scenarios: Generated test scenarios (if QA persona)
    """

    status: str
    success_score: int
    evidence: List[EvidenceItem]
    execution_log: str
    duration_seconds: float
    persona_used: str
    platform_used: str
    failure_reason: Optional[str] = None
    partial_completion_notes: Optional[str] = None
    subprocess_pid: Optional[int] = None
    test_scenarios: Optional[List[TestScenario]] = None

    def get_evidence_by_type(self, evidence_type: str) -> List[EvidenceItem]:
        """Get evidence items of specific type.

        Args:
            evidence_type: Type of evidence to filter

        Returns:
            List of matching evidence items
        """
        return [e for e in self.evidence if e.type == evidence_type]

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation
        """
        data = {
            "status": self.status,
            "success_score": self.success_score,
            "evidence_count": len(self.evidence),
            "execution_log_length": len(self.execution_log),
            "duration_seconds": self.duration_seconds,
            "persona_used": self.persona_used,
            "platform_used": self.platform_used,
            "failure_reason": self.failure_reason,
            "partial_completion_notes": self.partial_completion_notes,
            "subprocess_pid": self.subprocess_pid,
            "test_scenarios_count": len(self.test_scenarios) if self.test_scenarios else 0,
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MetaDelegationResult":
        """Deserialize from JSON string.

        Args:
            json_str: JSON string

        Returns:
            MetaDelegationResult instance
        """
        data = json.loads(json_str)
        # Note: This is simplified - full deserialization would need to reconstruct evidence items
        return cls(
            status=data.get("status", "UNKNOWN"),
            success_score=data.get("success_score", 0),
            evidence=[],
            execution_log="",
            duration_seconds=data.get("duration_seconds", 0.0),
            persona_used=data.get("persona_used", "unknown"),
            platform_used=data.get("platform_used", "unknown"),
            failure_reason=data.get("failure_reason"),
            partial_completion_notes=data.get("partial_completion_notes"),
            subprocess_pid=data.get("subprocess_pid"),
            test_scenarios=None,
        )


class MetaDelegationOrchestrator:
    """Orchestrates complete meta-delegation lifecycle."""

    def __init__(self):
        """Initialize orchestrator."""
        self.platform_cli: Optional[Any] = None
        self.persona_strategy: Optional[Any] = None
        self.state_machine: Optional[SubprocessStateMachine] = None
        self.evidence_collector: Optional[EvidenceCollector] = None
        self.success_evaluator: Optional[SuccessCriteriaEvaluator] = None
        self.scenario_generator: Optional[GadugiScenarioGenerator] = None

    def orchestrate_delegation(
        self,
        goal: str,
        success_criteria: str,
        persona_type: str = "guide",
        platform: str = "claude-code",
        context: str = "",
        timeout_minutes: int = 30,
        enable_scenarios: bool = False,
        working_directory: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> MetaDelegationResult:
        """Orchestrate complete delegation workflow.

        Args:
            goal: Task goal
            success_criteria: Success criteria
            persona_type: Persona to use
            platform: Platform to use
            context: Additional context
            timeout_minutes: Timeout in minutes
            enable_scenarios: Generate test scenarios
            working_directory: Working directory (defaults to current)
            environment: Environment variables

        Returns:
            MetaDelegationResult

        Raises:
            DelegationTimeout: If execution exceeds timeout
            DelegationError: If delegation fails
        """
        start_time = datetime.now()
        working_directory = working_directory or os.getcwd()
        environment = environment or {}
        process = None

        try:
            # Phase 1: Initialize components
            self.initialize_components(
                goal=goal,
                success_criteria=success_criteria,
                persona_type=persona_type,
                platform=platform,
                working_directory=working_directory,
            )

            # Phase 2: Spawn subprocess
            process = self.spawn_subprocess(
                goal=goal,
                persona=persona_type,
                working_dir=working_directory,
                environment=environment,
                context=context,
            )

            # Phase 3: Monitor execution
            execution_log = self.monitor_execution(
                timeout_seconds=timeout_minutes * 60,
            )

            # Phase 4: Collect evidence
            evidence = self.collect_evidence(
                execution_log=execution_log,
            )

            # Phase 5: Evaluate success
            evaluation = self.evaluate_success(
                criteria=success_criteria,
                evidence=evidence,
                execution_log=execution_log,
            )

            # Phase 6: Generate scenarios if requested
            test_scenarios = None
            if enable_scenarios or persona_type == "qa_engineer":
                test_scenarios = self.generate_scenarios(
                    goal=goal,
                    success_criteria=success_criteria,
                    context=context,
                )

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Determine status
            if evaluation.score >= 80:
                status = "SUCCESS"
            elif evaluation.score >= 50:
                status = "PARTIAL"
            else:
                status = "FAILURE"

            return MetaDelegationResult(
                status=status,
                success_score=evaluation.score,
                evidence=evidence,
                execution_log=execution_log,
                duration_seconds=duration,
                persona_used=persona_type,
                platform_used=platform,
                failure_reason=None if status != "FAILURE" else evaluation.notes,
                partial_completion_notes=evaluation.notes if status == "PARTIAL" else None,
                subprocess_pid=process.pid,
                test_scenarios=test_scenarios,
            )

        except DelegationTimeout:
            # Handle timeout - collect partial results
            duration = (datetime.now() - start_time).total_seconds()
            evidence = self.collect_evidence(execution_log="<timeout>")

            return MetaDelegationResult(
                status="FAILURE",
                success_score=0,
                evidence=evidence,
                execution_log="Process timed out",
                duration_seconds=duration,
                persona_used=persona_type,
                platform_used=platform,
                failure_reason=f"Execution exceeded {timeout_minutes} minute timeout",
                subprocess_pid=process.pid if process else None,
            )

        except Exception as e:
            # Handle general errors
            duration = (datetime.now() - start_time).total_seconds()

            return MetaDelegationResult(
                status="FAILURE",
                success_score=0,
                evidence=[],
                execution_log=str(e),
                duration_seconds=duration,
                persona_used=persona_type,
                platform_used=platform,
                failure_reason=str(e),
            )

        finally:
            # Cleanup
            self.cleanup()

    def initialize_components(
        self,
        goal: str,
        success_criteria: str,
        persona_type: str,
        platform: str,
        working_directory: str,
    ) -> None:
        """Initialize all components.

        Args:
            goal: Task goal
            success_criteria: Success criteria
            persona_type: Persona type
            platform: Platform name
            working_directory: Working directory
        """
        # Validate parameters
        self.validate_parameters(goal, success_criteria)

        # Get platform CLI
        self.platform_cli = get_platform_cli(platform)

        # Get persona strategy
        self.persona_strategy = get_persona_strategy(persona_type)

        # Initialize evidence collector
        self.evidence_collector = EvidenceCollector(
            working_directory=working_directory,
            evidence_priorities=self.persona_strategy.evidence_collection_priority,
        )

        # Initialize success evaluator
        self.success_evaluator = SuccessCriteriaEvaluator()

        # Initialize scenario generator
        self.scenario_generator = GadugiScenarioGenerator()

    def validate_parameters(self, goal: str, success_criteria: str) -> None:
        """Validate delegation parameters.

        Args:
            goal: Task goal
            success_criteria: Success criteria

        Raises:
            ValueError: If parameters are invalid
        """
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty")

        if not success_criteria or not success_criteria.strip():
            raise ValueError("Success criteria cannot be empty")

    def spawn_subprocess(
        self,
        goal: str,
        persona: str,
        working_dir: str,
        environment: Dict[str, str],
        context: str = "",
    ) -> Any:
        """Spawn AI assistant subprocess.

        Args:
            goal: Task goal
            persona: Persona type
            working_dir: Working directory
            environment: Environment variables
            context: Additional context

        Returns:
            Process object
        """
        assert self.platform_cli is not None, "platform_cli must be initialized"
        process = self.platform_cli.spawn_subprocess(
            goal=goal,
            persona=persona,
            working_dir=working_dir,
            environment=environment,
            context=context,
        )

        # Initialize state machine
        self.state_machine = SubprocessStateMachine(
            process=process,
            timeout_seconds=1800,  # Will be overridden by monitor
        )

        self.state_machine.transition_to(ProcessState.STARTING)
        self.state_machine.transition_to(ProcessState.RUNNING)

        return process

    def monitor_execution(self, timeout_seconds: int) -> str:
        """Monitor subprocess execution.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            Execution log

        Raises:
            DelegationTimeout: If timeout exceeded
        """
        assert self.state_machine is not None, "state_machine must be initialized"
        self.state_machine.timeout_seconds = timeout_seconds
        execution_log_parts = []

        while not self.state_machine.is_complete():
            # Check timeout
            if self.state_machine.check_timeout():
                self.state_machine.kill_process()
                raise DelegationTimeout(
                    elapsed_minutes=self.state_machine.get_elapsed_time() / 60,
                    timeout_minutes=timeout_seconds / 60,
                )

            # Poll process
            self.state_machine.poll_process()

            # Read output (non-blocking)
            if self.state_machine.process:
                try:
                    # This is simplified - real implementation would use select/poll
                    pass
                except Exception:
                    pass

            time.sleep(1)

        # Process completed - get final output
        if self.state_machine.process:
            try:
                stdout, stderr = self.state_machine.process.communicate(timeout=5)
                execution_log_parts.append(stdout or "")
                if stderr:
                    execution_log_parts.append(f"STDERR:\n{stderr}")
            except Exception as e:
                execution_log_parts.append(f"Error reading output: {e}")

        # Transition to completed
        if not self.state_machine.has_failed():
            self.state_machine.transition_to(ProcessState.COMPLETING)
            self.state_machine.transition_to(ProcessState.COMPLETED)

        return "\n".join(execution_log_parts)

    def collect_evidence(self, execution_log: str) -> List[EvidenceItem]:
        """Collect evidence from working directory.

        Args:
            execution_log: Execution log content

        Returns:
            List of evidence items
        """
        assert self.evidence_collector is not None, "evidence_collector must be initialized"
        return self.evidence_collector.collect_evidence(
            execution_log=execution_log,
        )

    def evaluate_success(
        self,
        criteria: str,
        evidence: List[EvidenceItem],
        execution_log: str,
    ) -> Any:
        """Evaluate success against criteria.

        Args:
            criteria: Success criteria
            evidence: Collected evidence
            execution_log: Execution log

        Returns:
            EvaluationResult
        """
        assert self.success_evaluator is not None, "success_evaluator must be initialized"
        return self.success_evaluator.evaluate(
            criteria=criteria,
            evidence=evidence,
            execution_log=execution_log,
        )

    def generate_scenarios(
        self,
        goal: str,
        success_criteria: str,
        context: str,
    ) -> List[TestScenario]:
        """Generate test scenarios.

        Args:
            goal: Task goal
            success_criteria: Success criteria
            context: Additional context

        Returns:
            List of test scenarios
        """
        assert self.scenario_generator is not None, "scenario_generator must be initialized"
        return self.scenario_generator.generate_scenarios(
            goal=goal,
            success_criteria=success_criteria,
            context=context,
        )

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.state_machine and self.state_machine.process:
            if not self.state_machine.is_complete():
                self.state_machine.kill_process()

    def handle_timeout(self) -> None:
        """Handle timeout scenario."""
        # Attempt to collect partial evidence
        try:
            self.collect_evidence(execution_log="<timeout>")
        except Exception:
            pass


def run_meta_delegation(
    goal: str,
    success_criteria: str,
    persona_type: str = "guide",
    platform: str = "claude-code",
    context: str = "",
    timeout_minutes: int = 30,
    enable_scenarios: bool = False,
    working_directory: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None,
) -> MetaDelegationResult:
    """Run meta-delegation with specified parameters.

    This is the main entry point for the meta-delegation system.

    Args:
        goal: Task goal
        success_criteria: Success criteria to validate against
        persona_type: Persona (guide, qa_engineer, architect, junior_dev)
        platform: Platform (claude-code, copilot, amplifier)
        context: Additional context information
        timeout_minutes: Maximum execution time in minutes
        enable_scenarios: Generate test scenarios (always true for qa_engineer)
        working_directory: Working directory for subprocess
        environment: Environment variables for subprocess

    Returns:
        MetaDelegationResult with status, score, and evidence

    Raises:
        ValueError: If persona or platform is unknown
        DelegationTimeout: If execution exceeds timeout
        DelegationError: If delegation fails

    Example:
        >>> result = run_meta_delegation(
        ...     goal="Create a REST API",
        ...     success_criteria="API has endpoints for CRUD operations",
        ...     persona_type="architect",
        ... )
        >>> print(f"Success score: {result.success_score}")
    """
    orchestrator = MetaDelegationOrchestrator()

    return orchestrator.orchestrate_delegation(
        goal=goal,
        success_criteria=success_criteria,
        persona_type=persona_type,
        platform=platform,
        context=context,
        timeout_minutes=timeout_minutes,
        enable_scenarios=enable_scenarios,
        working_directory=working_directory,
        environment=environment,
    )
