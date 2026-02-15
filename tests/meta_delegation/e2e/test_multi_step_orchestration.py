"""Layer 3: Multi-Step Orchestration Tests.

Tests complete meta-delegation workflows with multiple subprocess steps,
state machine transitions, evidence collection, and success evaluation.
These tests validate end-to-end orchestration scenarios.
"""

import pytest

from amplihack.meta_delegation.evidence_collector import EvidenceCollector

# These imports will fail initially - that's the point of TDD
from amplihack.meta_delegation.orchestrator import (
    MetaDelegationOrchestrator,
    OrchestrationState,
)
from amplihack.meta_delegation.success_evaluator import SuccessEvaluator


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestFullOrchestrationLifecycle:
    """Test complete orchestration lifecycle from start to finish."""

    def test_full_orchestration_lifecycle(self, test_workspace):
        """Test complete orchestration from initialization through completion.

        Validates that orchestrator can manage a full multi-step workflow
        with real subprocess execution at each step.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        goal = "Create a simple tutorial about Python functions"
        success_criteria = """
        - Has tutorial markdown file
        - Has example code with functions
        - Has README with instructions
        """

        result = orchestrator.run(goal=goal, success_criteria=success_criteria, max_steps=5)

        # Verify orchestration completed
        assert result.completed is True
        assert result.state == OrchestrationState.COMPLETED
        assert result.steps_executed > 0
        assert result.steps_executed <= 5

        # Verify timing
        assert result.duration_seconds > 0
        assert result.start_time is not None
        assert result.end_time is not None

    def test_orchestration_with_partial_success(self, test_workspace):
        """Test orchestration that completes with partial success.

        Validates that orchestrator can handle scenarios where not all
        success criteria are met but useful work was done.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        goal = "Create comprehensive documentation"
        success_criteria = """
        - Has tutorial (REQUIRED)
        - Has API reference (OPTIONAL)
        - Has 10+ examples (OPTIONAL)
        - Has video walkthrough (OPTIONAL)
        """

        result = orchestrator.run(goal=goal, success_criteria=success_criteria, allow_partial=True)

        # Should complete even if optional criteria not met
        assert result.completed is True
        assert result.success_score >= 50  # At least partial success
        assert result.success_score < 100  # Not perfect
        assert result.partial_completion_notes is not None

    def test_orchestration_state_persistence(self, test_workspace):
        """Test that orchestration state can be saved and restored.

        Validates state persistence for long-running orchestrations or crashes.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            enable_persistence=True,
        )

        goal = "Create tutorial"
        success_criteria = "Has tutorial.md"

        # Start orchestration
        result = orchestrator.run(
            goal=goal, success_criteria=success_criteria, steps=["plan", "implement", "review"]
        )

        # State should be saved
        state_file = test_workspace.path / ".meta_delegation_state.json"
        assert state_file.exists()

        # Should be able to restore and continue
        restored = MetaDelegationOrchestrator.restore(
            state_file=str(state_file), working_dir=str(test_workspace.path)
        )
        assert restored.current_state == result.state


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestStateMachineTransitions:
    """Test state machine transitions during orchestration."""

    def test_state_machine_transitions_with_real_execution(self, test_workspace):
        """Test state transitions during multi-step execution.

        Validates state machine progresses through expected states with
        real subprocess execution at each transition.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            track_states=True,
        )

        result = orchestrator.run(goal="Create simple example", success_criteria="Has example.py")

        # Verify state progression
        assert len(result.state_history) > 0
        expected_states = [
            OrchestrationState.INITIALIZING,
            OrchestrationState.PLANNING,
            OrchestrationState.EXECUTING,
            OrchestrationState.EVALUATING,
            OrchestrationState.COMPLETED,
        ]

        for state in expected_states:
            assert state in result.state_history

        # Each state should have subprocess execution
        for state_entry in result.state_history:
            if state_entry["state"] == OrchestrationState.EXECUTING:
                assert state_entry["subprocess_count"] > 0

    def test_state_rollback_on_failure(self, test_workspace):
        """Test state rollback when step fails.

        Validates that orchestrator can roll back to previous state on failure.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            enable_rollback=True,
        )

        # Create scenario that will fail at step 2
        result = orchestrator.run(
            goal="Create tutorial",
            success_criteria="Has perfect output",
            fail_at_step=2,  # For testing
            rollback_on_failure=True,
        )

        # Should roll back to previous successful state
        assert result.state == OrchestrationState.ROLLED_BACK
        assert result.rollback_count > 0
        assert len(result.state_history) > 2

    def test_concurrent_state_updates(self, test_workspace):
        """Test state handling with concurrent subprocess execution.

        Validates state machine handles parallel subprocess execution correctly.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            parallel_execution=True,
        )

        result = orchestrator.run(
            goal="Create multiple examples",
            success_criteria="Has 3 example files",
            parallel_steps=["example1", "example2", "example3"],
        )

        # Should track parallel executions
        assert result.parallel_subprocess_count >= 3
        assert result.completed is True


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestErrorRecoveryAcrossSteps:
    """Test error recovery across orchestration steps."""

    def test_error_recovery_across_orchestration_steps(self, test_workspace):
        """Test recovery from errors in middle of multi-step workflow.

        Validates that orchestrator can recover from step failures and
        continue with remaining steps.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            retry_failed_steps=True,
        )

        result = orchestrator.run(
            goal="Create tutorial with examples",
            success_criteria="Has tutorial and examples",
            steps=["plan", "write_tutorial", "create_examples", "review"],
            inject_failure_at_step=2,  # Fail at "create_examples"
        )

        # Should retry and eventually succeed
        assert result.completed is True
        assert result.retry_count > 0
        assert result.failed_steps == ["create_examples"]
        assert result.recovered_steps == ["create_examples"]

    def test_cascading_error_handling(self, test_workspace):
        """Test handling of cascading errors across steps.

        Validates that orchestrator handles situations where one step's
        failure affects subsequent steps.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        result = orchestrator.run(
            goal="Create dependent workflow",
            success_criteria="All steps complete",
            steps=[
                {"name": "setup", "depends_on": []},
                {"name": "build", "depends_on": ["setup"]},
                {"name": "test", "depends_on": ["build"]},
            ],
            fail_at_step="build",  # Will prevent "test" from running
        )

        # Should gracefully handle cascade
        assert result.completed is False
        assert "build" in result.failed_steps
        assert "test" in result.skipped_steps
        assert result.partial_completion_notes is not None

    def test_retry_with_different_strategy(self, test_workspace):
        """Test retrying failed step with different execution strategy.

        Validates adaptive retry strategies (e.g., different timeout, persona).
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            adaptive_retry=True,
        )

        result = orchestrator.run(
            goal="Create example",
            success_criteria="Has working example",
            initial_timeout=10,
            retry_timeout=30,  # Longer timeout on retry
            max_retries=2,
        )

        if result.retry_count > 0:
            # Should have tried different strategies
            assert len(result.retry_strategies_used) > 1
            assert result.retry_strategies_used[0] != result.retry_strategies_used[1]


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestPersonaSwitching:
    """Test persona switching during orchestration."""

    def test_persona_switching_during_orchestration(self, test_workspace):
        """Test switching personas between orchestration steps.

        Validates that different personas can be used at different workflow stages.
        """
        orchestrator = MetaDelegationOrchestrator(
            initial_persona="architect",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            enable_persona_switching=True,
        )

        result = orchestrator.run(
            goal="Design and implement feature",
            success_criteria="Has design doc and implementation",
            steps=[
                {"name": "design", "persona": "architect"},
                {"name": "implement", "persona": "builder"},
                {"name": "review", "persona": "reviewer"},
            ],
        )

        # Verify different personas were used
        assert result.completed is True
        assert len(result.personas_used) == 3
        assert "architect" in result.personas_used
        assert "builder" in result.personas_used
        assert "reviewer" in result.personas_used

    def test_persona_selection_based_on_step_requirements(self, test_workspace):
        """Test automatic persona selection based on step type.

        Validates orchestrator can choose appropriate persona for each step.
        """
        orchestrator = MetaDelegationOrchestrator(
            platform="claude_code", working_dir=str(test_workspace.path), auto_select_persona=True
        )

        result = orchestrator.run(
            goal="Complete workflow",
            success_criteria="All phases complete",
            steps=[
                {"name": "design", "type": "architecture"},
                {"name": "code", "type": "implementation"},
                {"name": "test", "type": "quality_assurance"},
            ],
        )

        # Should auto-select appropriate personas
        assert result.persona_selection_log is not None
        assert "architect" in str(result.persona_selection_log).lower()
        assert "builder" in str(result.persona_selection_log).lower()


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestEvidenceCollection:
    """Test evidence collection across subprocesses."""

    def test_evidence_collection_across_subprocesses(self, test_workspace):
        """Test collecting evidence from multiple subprocess executions.

        Validates evidence collector aggregates artifacts from all steps.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        result = orchestrator.run(
            goal="Create tutorial with examples",
            success_criteria="Has tutorial and 3 examples",
            steps=["write_tutorial", "example1", "example2", "example3"],
        )

        # Verify evidence collected
        assert result.evidence is not None
        assert len(result.evidence.files) >= 4  # tutorial + 3 examples

        # Each subprocess should contribute evidence
        for step in result.steps_executed_details:
            assert step["evidence_count"] > 0

    def test_evidence_deduplication(self, test_workspace):
        """Test that duplicate evidence is deduplicated.

        Validates evidence collector doesn't store the same file multiple times.
        """
        collector = EvidenceCollector(working_dir=str(test_workspace.path))

        # Create file and collect multiple times
        test_file = test_workspace.write_file("test.txt", "content")

        collector.collect_file(test_file)
        collector.collect_file(test_file)  # Duplicate
        collector.collect_file(test_file)  # Duplicate

        # Should only have one entry
        evidence = collector.get_evidence()
        matching = [e for e in evidence.files if e.path == str(test_file)]
        assert len(matching) == 1

    def test_evidence_timestamping(self, test_workspace):
        """Test that evidence is timestamped correctly.

        Validates evidence items have accurate timestamps for ordering.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        result = orchestrator.run(
            goal="Create files in sequence",
            success_criteria="Has file1.txt, file2.txt, file3.txt",
            steps=["create_file1", "create_file2", "create_file3"],
        )

        # Timestamps should be in order
        files = sorted(result.evidence.files, key=lambda e: e.path)
        for i in range(len(files) - 1):
            assert files[i].timestamp <= files[i + 1].timestamp


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestSuccessEvaluation:
    """Test success evaluation with real output."""

    def test_success_evaluation_with_real_output(self, test_workspace):
        """Test success evaluation using actual subprocess output.

        Validates success evaluator can analyze real evidence and determine
        if criteria are met.
        """
        _ = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        # Create known success scenario
        test_workspace.write_file("tutorial.md", "# Tutorial content")
        test_workspace.write_file("example.py", "def example(): pass")
        test_workspace.write_file("README.md", "# Setup instructions")

        success_criteria = """
        - Has tutorial.md with content
        - Has example.py with function definition
        - Has README.md with instructions
        """

        evaluator = SuccessEvaluator()
        score = evaluator.evaluate(criteria=success_criteria, evidence_dir=str(test_workspace.path))

        assert score >= 90  # Should score high
        assert evaluator.all_criteria_met is True

    def test_partial_success_scoring(self, test_workspace):
        """Test success scoring with partial criteria fulfillment.

        Validates nuanced scoring (not just pass/fail).
        """
        # Create partial success scenario
        test_workspace.write_file("tutorial.md", "# Tutorial")
        # Missing example.py
        # Missing README.md

        success_criteria = """
        - Has tutorial.md (REQUIRED)
        - Has example.py (OPTIONAL)
        - Has README.md (OPTIONAL)
        """

        evaluator = SuccessEvaluator()
        score = evaluator.evaluate(criteria=success_criteria, evidence_dir=str(test_workspace.path))

        # Should have partial score
        assert 30 <= score <= 60
        assert evaluator.all_criteria_met is False
        assert evaluator.required_criteria_met is True

    def test_success_evaluation_with_quality_checks(self, test_workspace):
        """Test success evaluation includes quality checks.

        Validates evaluator considers code quality, not just presence.
        """
        # Create low-quality example
        test_workspace.write_file(
            "bad_example.py",
            "x=1;y=2;print(x+y)",  # No comments, poor formatting
        )

        # Create high-quality example
        test_workspace.write_file(
            "good_example.py",
            '''"""
Example module demonstrating best practices.
"""

def add(x: int, y: int) -> int:
    """Add two numbers.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of x and y
    """
    return x + y
''',
        )

        success_criteria = "Has well-documented Python code"

        evaluator = SuccessEvaluator(enable_quality_checks=True)

        bad_score = evaluator.evaluate(
            criteria=success_criteria,
            evidence_dir=str(test_workspace.path),
            target_file="bad_example.py",
        )

        good_score = evaluator.evaluate(
            criteria=success_criteria,
            evidence_dir=str(test_workspace.path),
            target_file="good_example.py",
        )

        # Good example should score higher
        assert good_score > bad_score
        assert good_score >= 80


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestScenarioGeneratorIntegration:
    """Test integration with scenario generator."""

    def test_scenario_generator_integration(self, test_workspace):
        """Test orchestration with scenario generator for test generation.

        Validates orchestrator can work with scenario generator to create
        comprehensive test scenarios.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="qa_engineer",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            use_scenario_generator=True,
        )

        result = orchestrator.run(
            goal="Validate authentication feature",
            success_criteria="Has comprehensive test scenarios",
            generate_scenarios=True,
            scenario_types=["happy_path", "edge_cases", "security"],
        )

        # Should generate scenarios
        assert result.scenarios_generated is not None
        assert len(result.scenarios_generated) >= 3

        # Each scenario type should be present
        scenario_types = [s["type"] for s in result.scenarios_generated]
        assert "happy_path" in scenario_types
        assert "edge_cases" in scenario_types
        assert "security" in scenario_types

    def test_scenario_execution_results(self, test_workspace):
        """Test execution and validation of generated scenarios.

        Validates orchestrator can execute generated scenarios and collect results.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="qa_engineer", platform="claude_code", working_dir=str(test_workspace.path)
        )

        result = orchestrator.run(
            goal="Test login feature",
            success_criteria="All scenarios pass",
            generate_and_execute_scenarios=True,
        )

        # Should have execution results
        assert result.scenario_results is not None
        assert len(result.scenario_results) > 0

        # Each result should have outcome
        for scenario_result in result.scenario_results:
            assert "scenario_name" in scenario_result
            assert "outcome" in scenario_result  # pass/fail
            assert "evidence" in scenario_result


@pytest.mark.e2e
@pytest.mark.subprocess
@pytest.mark.orchestration
class TestComplexWorkflows:
    """Test complex orchestration workflows."""

    def test_nested_delegation(self, test_workspace):
        """Test orchestration with nested delegation (meta-meta-delegation).

        Validates orchestrator can delegate to another orchestrator.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide",
            platform="claude_code",
            working_dir=str(test_workspace.path),
            enable_nested_delegation=True,
        )

        result = orchestrator.run(
            goal="Create comprehensive tutorial",
            success_criteria="Has tutorial with working examples and tests",
            steps=[
                {"name": "tutorial", "delegate_to": "guide"},
                {"name": "examples", "delegate_to": "builder"},
                {"name": "tests", "delegate_to": "qa_engineer"},
            ],
        )

        # Should track nested delegations
        assert result.nested_delegation_count > 0
        assert len(result.delegation_tree) > 1

    def test_conditional_step_execution(self, test_workspace):
        """Test conditional step execution based on previous results.

        Validates orchestrator can skip or modify steps based on results.
        """
        orchestrator = MetaDelegationOrchestrator(
            persona="guide", platform="claude_code", working_dir=str(test_workspace.path)
        )

        result = orchestrator.run(
            goal="Create tutorial",
            success_criteria="Has appropriate content",
            steps=[
                {"name": "check_existing", "conditional": None},
                {"name": "create_new", "conditional": "if:no_existing_content"},
                {"name": "update_existing", "conditional": "if:has_existing_content"},
            ],
        )

        # Should execute conditional logic
        _ = result.skipped_steps
        executed = [s["name"] for s in result.steps_executed_details]

        # Exactly one of create_new or update_existing should run
        assert ("create_new" in executed) != ("update_existing" in executed)
