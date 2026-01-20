"""Unit tests for OrchestrationConfig dataclass.

Tests configuration creation, validation, and defaults for orchestration settings.

Philosophy: Test the brick's public interface - configuration behavior and validation rules.
"""

import pytest
from datetime import timedelta


class TestOrchestrationConfig:
    """Unit tests for orchestration configuration."""

    def test_create_config_minimal(self):
        """Test creating config with minimal required parameters."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 103]
        )

        assert config.parent_issue == 1783
        assert config.sub_issues == [101, 102, 103]
        assert config.parallel_degree > 0  # Should have default

    def test_create_config_with_all_parameters(self):
        """Test creating config with all parameters specified."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 103, 104, 105],
            parallel_degree=5,
            timeout_minutes=120,
            recovery_strategy="continue_on_failure",
            worktree_base="/tmp/worktrees",
            status_poll_interval=30,
        )

        assert config.parent_issue == 1783
        assert len(config.sub_issues) == 5
        assert config.parallel_degree == 5
        assert config.timeout_minutes == 120
        assert config.recovery_strategy == "continue_on_failure"

    def test_config_defaults(self):
        """Test that config uses sensible defaults."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102]
        )

        # Should have sensible defaults
        assert config.parallel_degree >= 1
        assert config.timeout_minutes >= 60
        assert config.status_poll_interval >= 10
        assert config.recovery_strategy in ["fail_fast", "continue_on_failure"]

    @pytest.mark.parametrize("parallel_degree", [-1, 0, 101])
    def test_validate_parallel_degree_bounds(self, parallel_degree):
        """Test validation of parallel_degree parameter bounds."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        with pytest.raises(ValueError, match="parallel_degree"):
            OrchestrationConfig(
                parent_issue=1783,
                sub_issues=[101, 102],
                parallel_degree=parallel_degree
            )

    def test_validate_empty_sub_issues(self):
        """Test that empty sub_issues list is rejected."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        with pytest.raises(ValueError, match="sub_issues.*empty"):
            OrchestrationConfig(
                parent_issue=1783,
                sub_issues=[]
            )

    def test_validate_duplicate_sub_issues(self):
        """Test that duplicate sub-issues are detected and handled."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        # Should either deduplicate or raise error
        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 101, 103, 102]
        )

        # After validation, should have unique issues only
        assert len(config.sub_issues) == 3
        assert len(set(config.sub_issues)) == len(config.sub_issues)

    @pytest.mark.parametrize("strategy", [
        "fail_fast",
        "continue_on_failure",
        "retry_failed",
    ])
    def test_valid_recovery_strategies(self, strategy):
        """Test that valid recovery strategies are accepted."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102],
            recovery_strategy=strategy
        )

        assert config.recovery_strategy == strategy

    def test_invalid_recovery_strategy(self):
        """Test that invalid recovery strategy is rejected."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        with pytest.raises(ValueError, match="recovery_strategy"):
            OrchestrationConfig(
                parent_issue=1783,
                sub_issues=[101, 102],
                recovery_strategy="invalid_strategy"
            )

    def test_timeout_validation(self):
        """Test timeout parameter validation."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        # Valid timeout
        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101],
            timeout_minutes=60
        )
        assert config.timeout_minutes == 60

        # Invalid timeout (too short)
        with pytest.raises(ValueError, match="timeout"):
            OrchestrationConfig(
                parent_issue=1783,
                sub_issues=[101],
                timeout_minutes=0
            )

    def test_config_from_issue_body(self, sample_issue_body):
        """Test creating config from parsed issue body."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig.from_issue_body(
            parent_issue=1783,
            issue_body=sample_issue_body
        )

        assert config.parent_issue == 1783
        assert len(config.sub_issues) == 5
        assert 101 in config.sub_issues
        assert 105 in config.sub_issues

    def test_config_to_dict(self):
        """Test serialization to dictionary."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 103],
            parallel_degree=3
        )

        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["parent_issue"] == 1783
        assert result["sub_issues"] == [101, 102, 103]
        assert result["parallel_degree"] == 3

    def test_config_from_dict(self):
        """Test deserialization from dictionary."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        data = {
            "parent_issue": 1783,
            "sub_issues": [101, 102, 103],
            "parallel_degree": 3,
            "timeout_minutes": 120,
        }

        config = OrchestrationConfig.from_dict(data)

        assert config.parent_issue == 1783
        assert config.sub_issues == [101, 102, 103]
        assert config.parallel_degree == 3

    def test_calculate_optimal_parallel_degree(self):
        """Test automatic calculation of optimal parallel degree."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        # With many sub-issues, should use max parallelism
        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=list(range(101, 151))  # 50 issues
        )

        # Should auto-calculate based on system resources or cap at max
        assert config.parallel_degree <= 20  # Reasonable max
        assert config.parallel_degree >= 1

    def test_config_equality(self):
        """Test config equality comparison."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config1 = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102]
        )

        config2 = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102]
        )

        config3 = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102, 103]
        )

        assert config1 == config2
        assert config1 != config3

    def test_config_immutability(self):
        """Test that config is immutable after creation (frozen dataclass)."""
        from parallel_task_orchestrator.models.orchestration import OrchestrationConfig

        config = OrchestrationConfig(
            parent_issue=1783,
            sub_issues=[101, 102]
        )

        with pytest.raises((AttributeError, TypeError)):
            config.parent_issue = 9999  # Should not allow mutation
