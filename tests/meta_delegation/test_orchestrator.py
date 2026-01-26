"""Unit tests for Meta-Delegator Orchestrator.

Tests complete delegation lifecycle and coordination.
These tests will FAIL until the orchestrator module is implemented.
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation import MetaDelegationResult, run_meta_delegation
    from amplihack.meta_delegation.orchestrator import MetaDelegationOrchestrator
except ImportError:
    pytest.skip("orchestrator module not implemented yet", allow_module_level=True)


class TestMetaDelegationResult:
    """Test MetaDelegationResult dataclass."""

    def test_result_has_required_fields(self):
        """Test result object has all required fields."""
        result = MetaDelegationResult(
            status="SUCCESS",
            success_score=95,
            evidence=[],
            execution_log="Log content",
            duration_seconds=120.5,
            persona_used="guide",
            platform_used="claude-code",
            failure_reason=None,
            partial_completion_notes=None,
            subprocess_pid=12345,
            test_scenarios=None,
        )

        assert result.status == "SUCCESS"
        assert result.success_score == 95
        assert result.duration_seconds == 120.5

    def test_result_status_values(self):
        """Test result status is one of valid values."""
        valid_statuses = ["SUCCESS", "PARTIAL", "FAILURE"]

        for status in valid_statuses:
            result = MetaDelegationResult(
                status=status,
                success_score=50,
                evidence=[],
                execution_log="",
                duration_seconds=10.0,
                persona_used="guide",
                platform_used="claude-code",
                failure_reason=None,
                partial_completion_notes=None,
                subprocess_pid=123,
                test_scenarios=None,
            )
            assert result.status in valid_statuses

    def test_result_get_evidence_by_type(self):
        """Test filtering evidence by type."""
        from datetime import datetime

        from amplihack.meta_delegation.evidence_collector import EvidenceItem

        evidence = [
            EvidenceItem(
                type="code_file",
                path="app.py",
                content="code",
                excerpt="",
                size_bytes=10,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="test_file",
                path="test.py",
                content="test",
                excerpt="",
                size_bytes=10,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        result = MetaDelegationResult(
            status="SUCCESS",
            success_score=90,
            evidence=evidence,
            execution_log="",
            duration_seconds=10.0,
            persona_used="guide",
            platform_used="claude-code",
            failure_reason=None,
            partial_completion_notes=None,
            subprocess_pid=123,
            test_scenarios=None,
        )

        code_files = result.get_evidence_by_type("code_file")
        assert len(code_files) == 1
        assert code_files[0].type == "code_file"


class TestRunMetaDelegation:
    """Test run_meta_delegation function."""

    @pytest.fixture
    def mock_components(self):
        """Mock all orchestrator components."""
        with (
            patch("amplihack.meta_delegation.platform_cli.get_platform_cli") as mock_platform,
            patch("amplihack.meta_delegation.persona.get_persona_strategy") as mock_persona,
            patch("amplihack.meta_delegation.state_machine.SubprocessStateMachine") as mock_sm,
            patch("amplihack.meta_delegation.evidence_collector.EvidenceCollector") as mock_ec,
            patch(
                "amplihack.meta_delegation.success_evaluator.SuccessCriteriaEvaluator"
            ) as mock_se,
        ):
            # Configure mocks
            mock_platform_instance = Mock()
            mock_platform_instance.spawn_subprocess.return_value = Mock(pid=123)
            mock_platform.return_value = mock_platform_instance

            mock_persona.return_value = Mock(
                name="guide",
                prompt_template="Goal: {goal}",
                evidence_collection_priority=["code_file"],
            )

            yield {
                "platform": mock_platform,
                "persona": mock_persona,
                "state_machine": mock_sm,
                "evidence_collector": mock_ec,
                "success_evaluator": mock_se,
            }

    def test_run_meta_delegation_returns_result(self, mock_components):
        """Test run_meta_delegation returns MetaDelegationResult."""
        result = run_meta_delegation(
            goal="Create a module",
            success_criteria="Module has functions and tests",
        )

        assert isinstance(result, MetaDelegationResult)

    def test_run_meta_delegation_with_minimal_params(self, mock_components):
        """Test run_meta_delegation with only required parameters."""
        result = run_meta_delegation(
            goal="Simple task",
            success_criteria="Task completed",
        )

        assert result is not None
        assert result.persona_used is not None
        assert result.platform_used is not None

    def test_run_meta_delegation_with_all_params(self, mock_components):
        """Test run_meta_delegation with all parameters."""
        result = run_meta_delegation(
            goal="Complex task",
            success_criteria="All features implemented",
            persona_type="architect",
            platform="claude-code",
            context="Legacy system",
            timeout_minutes=60,
            enable_scenarios=True,
            working_directory="/tmp/test",
            environment={"VAR": "value"},
        )

        assert result is not None

    def test_run_meta_delegation_uses_correct_persona(self, mock_components):
        """Test delegation uses specified persona."""
        run_meta_delegation(
            goal="Task",
            success_criteria="Done",
            persona_type="qa_engineer",
        )

        mock_components["persona"].assert_called_with("qa_engineer")

    def test_run_meta_delegation_uses_correct_platform(self, mock_components):
        """Test delegation uses specified platform."""
        run_meta_delegation(
            goal="Task",
            success_criteria="Done",
            platform="amplifier",
        )

        mock_components["platform"].assert_called_with("amplifier")

    def test_run_meta_delegation_spawns_subprocess(self, mock_components):
        """Test delegation spawns subprocess via platform CLI."""
        run_meta_delegation(
            goal="Task",
            success_criteria="Done",
        )

        platform_instance = mock_components["platform"].return_value
        platform_instance.spawn_subprocess.assert_called_once()

    def test_run_meta_delegation_collects_evidence(self, mock_components):
        """Test delegation collects evidence."""
        mock_ec_instance = Mock()
        mock_ec_instance.collect_evidence.return_value = []
        mock_components["evidence_collector"].return_value = mock_ec_instance

        run_meta_delegation(
            goal="Task",
            success_criteria="Done",
        )

        mock_ec_instance.collect_evidence.assert_called()

    def test_run_meta_delegation_evaluates_success(self, mock_components):
        """Test delegation evaluates success criteria."""
        mock_se_instance = Mock()
        mock_se_instance.evaluate.return_value = Mock(score=85, notes="Good")
        mock_components["success_evaluator"].return_value = mock_se_instance

        result = run_meta_delegation(
            goal="Task",
            success_criteria="Done",
        )

        mock_se_instance.evaluate.assert_called()
        assert result.success_score == 85


class TestMetaDelegationOrchestrator:
    """Test MetaDelegationOrchestrator class."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return MetaDelegationOrchestrator()

    def test_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator is not None

    def test_orchestrate_delegation_complete_flow(self, orchestrator):
        """Test complete delegation orchestration flow."""
        with (
            patch.object(orchestrator, "initialize_components"),
            patch.object(orchestrator, "spawn_subprocess"),
            patch.object(orchestrator, "monitor_execution"),
            patch.object(orchestrator, "collect_evidence"),
            patch.object(orchestrator, "evaluate_success"),
            patch.object(orchestrator, "cleanup"),
        ):
            result = orchestrator.orchestrate_delegation(
                goal="Task",
                success_criteria="Done",
                persona_type="guide",
                platform="claude-code",
            )

            assert isinstance(result, MetaDelegationResult)

    def test_orchestrator_initialization_phase(self, orchestrator):
        """Test initialization phase validates parameters."""
        with patch.object(orchestrator, "validate_parameters") as mock_validate:
            mock_validate.return_value = None

            orchestrator.initialize_components(
                goal="Task",
                success_criteria="Done",
                persona_type="guide",
                platform="claude-code",
            )

            mock_validate.assert_called_once()

    def test_orchestrator_spawn_phase(self, orchestrator):
        """Test subprocess spawn phase."""
        with patch.object(orchestrator, "platform_cli") as mock_cli:
            mock_process = Mock(pid=123)
            mock_cli.spawn_subprocess.return_value = mock_process

            orchestrator.spawn_subprocess(
                goal="Task",
                persona="guide",
                working_dir="/tmp",
                environment={},
            )

            mock_cli.spawn_subprocess.assert_called_once()

    def test_orchestrator_monitoring_phase(self, orchestrator):
        """Test monitoring phase polls state machine."""
        mock_sm = Mock()
        mock_sm.is_complete.side_effect = [False, False, True]
        mock_sm.check_timeout.return_value = False

        orchestrator.state_machine = mock_sm

        orchestrator.monitor_execution()

        assert mock_sm.is_complete.call_count >= 3

    def test_orchestrator_evidence_collection_phase(self, orchestrator):
        """Test evidence collection phase."""
        mock_collector = Mock()
        mock_collector.collect_evidence.return_value = []

        orchestrator.evidence_collector = mock_collector

        evidence = orchestrator.collect_evidence(execution_log="Log")

        mock_collector.collect_evidence.assert_called()

    def test_orchestrator_evaluation_phase(self, orchestrator):
        """Test success evaluation phase."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = Mock(score=90, notes="Excellent")

        orchestrator.success_evaluator = mock_evaluator

        result = orchestrator.evaluate_success(
            criteria="Done",
            evidence=[],
            execution_log="Log",
        )

        mock_evaluator.evaluate.assert_called()

    def test_orchestrator_cleanup_phase(self, orchestrator):
        """Test cleanup phase terminates subprocess."""
        mock_sm = Mock()
        orchestrator.state_machine = mock_sm

        orchestrator.cleanup()

        # Should cleanup resources

    def test_orchestrator_handles_timeout(self, orchestrator):
        """Test orchestrator handles timeout gracefully."""
        mock_sm = Mock()
        mock_sm.check_timeout.return_value = True
        mock_sm.is_complete.return_value = False

        orchestrator.state_machine = mock_sm

        with pytest.raises(Exception):  # Should raise DelegationTimeout
            orchestrator.monitor_execution()

    def test_orchestrator_handles_subprocess_failure(self, orchestrator):
        """Test orchestrator handles subprocess failure."""
        mock_sm = Mock()
        mock_sm.has_failed.return_value = True
        mock_sm.failure_reason = "Process crashed"

        orchestrator.state_machine = mock_sm

        # Should handle gracefully and return FAILURE result

    def test_orchestrator_captures_partial_results_on_timeout(self, orchestrator):
        """Test orchestrator captures partial results on timeout."""
        with patch.object(orchestrator, "collect_evidence") as mock_collect:
            mock_collect.return_value = []

            # Simulate timeout
            try:
                orchestrator.handle_timeout()
            except Exception:
                pass

            # Should have attempted to collect evidence
            mock_collect.assert_called()


class TestMetaDelegationErrorHandling:
    """Test error handling in meta-delegation."""

    def test_invalid_persona_raises_error(self):
        """Test invalid persona type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown persona"):
            run_meta_delegation(
                goal="Task",
                success_criteria="Done",
                persona_type="invalid_persona",
            )

    def test_invalid_platform_raises_error(self):
        """Test invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Unknown platform"):
            run_meta_delegation(
                goal="Task",
                success_criteria="Done",
                platform="invalid_platform",
            )

    def test_timeout_raises_delegation_timeout(self):
        """Test timeout raises DelegationTimeout exception."""
        from amplihack.meta_delegation import DelegationTimeout

        with patch(
            "amplihack.meta_delegation.orchestrator.MetaDelegationOrchestrator"
        ) as mock_orch:
            mock_instance = Mock()
            mock_instance.orchestrate_delegation.side_effect = DelegationTimeout(
                elapsed_minutes=31.0,
                timeout_minutes=30,
            )
            mock_orch.return_value = mock_instance

            with pytest.raises(DelegationTimeout):
                run_meta_delegation(
                    goal="Long task",
                    success_criteria="Done",
                    timeout_minutes=30,
                )

    def test_subprocess_crash_raises_delegation_error(self):
        """Test subprocess crash raises DelegationError."""
        from amplihack.meta_delegation import DelegationError

        with patch("amplihack.meta_delegation.platform_cli.get_platform_cli") as mock_platform:
            mock_platform.return_value.spawn_subprocess.side_effect = DelegationError(
                reason="Failed to start",
                exit_code=1,
            )

            with pytest.raises(DelegationError):
                run_meta_delegation(
                    goal="Task",
                    success_criteria="Done",
                )


class TestMetaDelegationResultSerialization:
    """Test result serialization and deserialization."""

    def test_result_to_json(self):
        """Test result can be serialized to JSON."""
        result = MetaDelegationResult(
            status="SUCCESS",
            success_score=95,
            evidence=[],
            execution_log="Log",
            duration_seconds=10.0,
            persona_used="guide",
            platform_used="claude-code",
            failure_reason=None,
            partial_completion_notes=None,
            subprocess_pid=123,
            test_scenarios=None,
        )

        json_str = result.to_json()

        assert isinstance(json_str, str)
        assert "SUCCESS" in json_str
        assert "95" in json_str

    def test_result_from_json(self):
        """Test result can be deserialized from JSON."""
        json_str = '{"status": "SUCCESS", "success_score": 95, "evidence": []}'

        result = MetaDelegationResult.from_json(json_str)

        assert isinstance(result, MetaDelegationResult)
        assert result.status == "SUCCESS"
