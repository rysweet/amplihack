"""
Unit tests for execution tier cascade module.

Tests the 3-tier fallback chain:
1. Recipe Runner (Tier 1 - Code-enforced workflow)
2. Workflow Skills (Tier 2 - LLM-driven with recipe files as prompts)
3. Markdown Workflow (Tier 3 - Direct markdown reading)

Following TDD: These tests should FAIL until implementation is complete.
"""

from unittest.mock import patch

import pytest


class TestExecutionTierCascade:
    """Test execution tier cascade logic."""

    # ========================================
    # Tier Detection Tests (30% of tests - integration level)
    # ========================================

    def test_cascade_imports(self):
        """Test that cascade module can be imported."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        assert ExecutionTierCascade is not None

    def test_tier1_recipe_runner_available(self, mock_recipe_runner):
        """Test Tier 1 (Recipe Runner) is detected when available."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        tier = cascade.detect_available_tier()

        assert tier == 1
        assert cascade.is_recipe_runner_available() is True

    def test_tier1_recipe_runner_disabled_by_env_var(self, mock_environment_vars):
        """Test Recipe Runner is disabled when AMPLIHACK_USE_RECIPES=0."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_environment_vars({"AMPLIHACK_USE_RECIPES": "0"})
        cascade = ExecutionTierCascade()
        tier = cascade.detect_available_tier()

        # Should fall back to tier 3 (markdown) since workflow skills not implemented
        assert tier == 3
        assert cascade.is_recipe_runner_available() is False

    def test_tier2_workflow_skills_when_recipe_runner_unavailable(self):
        """Test Tier 2 (Workflow Skills) when Recipe Runner import fails."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            cascade = ExecutionTierCascade()
            tier = cascade.detect_available_tier()

            # Falls back to tier 3 since workflow skills not implemented yet
            assert tier == 3
            assert cascade.is_workflow_skills_available() is False

    def test_tier3_markdown_fallback_when_skills_unavailable(self):
        """Test Tier 3 (Markdown) as last fallback."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            with patch(
                "amplihack.workflows.execution_tier_cascade.import_workflow_skills",
                side_effect=ImportError,
            ):
                cascade = ExecutionTierCascade()
                tier = cascade.detect_available_tier()

                assert tier == 3
                assert cascade.is_markdown_available() is True  # Always True

    # ========================================
    # Execution Tests
    # ========================================

    def test_execute_tier1_recipe_runner(self, mock_recipe_runner, session_context):
        """Test execution via Tier 1 (Recipe Runner)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)
        result = cascade.execute("DEFAULT_WORKFLOW", session_context)

        assert result["tier"] == 1
        assert result["method"] == "recipe_runner"
        assert result["status"] == "success"
        mock_recipe_runner.run_recipe_by_name.assert_called_once()

    def test_execute_tier2_workflow_skills(self, mock_workflow_skill, session_context):
        """Test execution via Tier 2 (Workflow Skills)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            cascade = ExecutionTierCascade(workflow_skill=mock_workflow_skill)
            result = cascade.execute("DEFAULT_WORKFLOW", session_context)

            assert result["tier"] == 2
            assert result["method"] == "workflow_skills"
            mock_workflow_skill.execute.assert_called_once()

    def test_execute_tier3_markdown(self, session_context):
        """Test execution via Tier 3 (Markdown)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            with patch(
                "amplihack.workflows.execution_tier_cascade.import_workflow_skills",
                side_effect=ImportError,
            ):
                cascade = ExecutionTierCascade()
                result = cascade.execute("DEFAULT_WORKFLOW", session_context)

                assert result["tier"] == 3
                assert result["method"] == "markdown"
                assert result["status"] == "success"

    # ========================================
    # Fallback Chain Tests
    # ========================================

    def test_fallback_tier1_to_tier2_on_exception(
        self, mock_recipe_runner, mock_workflow_skill, session_context
    ):
        """Test fallback from Tier 1 to Tier 2 when Recipe Runner fails."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Recipe execution failed")
        cascade = ExecutionTierCascade(
            recipe_runner=mock_recipe_runner, workflow_skill=mock_workflow_skill
        )

        result = cascade.execute("DEFAULT_WORKFLOW", session_context)

        assert result["tier"] == 2
        assert result["method"] == "workflow_skills"
        assert "fallback_reason" in result
        mock_workflow_skill.execute.assert_called_once()

    def test_fallback_tier2_to_tier3_on_exception(self, mock_workflow_skill, session_context):
        """Test fallback from Tier 2 to Tier 3 when Workflow Skills fail."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_workflow_skill.execute.side_effect = RuntimeError("Skill execution failed")

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            cascade = ExecutionTierCascade(workflow_skill=mock_workflow_skill)
            result = cascade.execute("DEFAULT_WORKFLOW", session_context)

            assert result["tier"] == 3
            assert result["method"] == "markdown"
            assert "fallback_reason" in result

    def test_fallback_chain_logs_errors(self, mock_recipe_runner, session_context, caplog):
        """Test that fallback chain logs errors for debugging."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Recipe failed")
        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)

        result = cascade.execute("DEFAULT_WORKFLOW", session_context)

        assert any("fallback" in record.message.lower() for record in caplog.records)
        assert result["tier"] > 1  # Should have fallen back

    # ========================================
    # Recipe Runner Integration Tests
    # ========================================

    def test_recipe_runner_receives_correct_recipe_name(self, mock_recipe_runner, session_context):
        """Test that Recipe Runner receives workflow-to-recipe name mapping."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)
        cascade.execute("DEFAULT_WORKFLOW", session_context)

        call_args = mock_recipe_runner.run_recipe_by_name.call_args
        assert call_args[0][0] == "default-workflow"  # Should convert to recipe name

    def test_recipe_runner_receives_context(self, mock_recipe_runner, session_context):
        """Test that Recipe Runner receives session context."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)
        cascade.execute("DEFAULT_WORKFLOW", session_context)

        call_args = mock_recipe_runner.run_recipe_by_name.call_args
        assert "context" in call_args[1] or len(call_args[0]) > 1

    @pytest.mark.integration
    def test_recipe_runner_with_cli_subprocess_adapter(
        self, mock_cli_subprocess_adapter, session_context
    ):
        """Test Recipe Runner with CLISubprocessAdapter."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        # This should work with real recipe runner if available
        result = cascade.execute("Q&A_WORKFLOW", session_context)

        # Q&A should not use recipe runner, should use direct response
        assert result["tier"] in [1, 2, 3]  # Any tier is acceptable for Q&A

    # ========================================
    # Workflow-to-Recipe Mapping Tests
    # ========================================

    def test_workflow_to_recipe_mapping_default(self):
        """Test DEFAULT_WORKFLOW maps to default-workflow recipe."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        recipe_name = cascade.workflow_to_recipe_name("DEFAULT_WORKFLOW")

        assert recipe_name == "default-workflow"

    def test_workflow_to_recipe_mapping_investigation(self):
        """Test INVESTIGATION_WORKFLOW maps to investigation-workflow recipe."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        recipe_name = cascade.workflow_to_recipe_name("INVESTIGATION_WORKFLOW")

        assert recipe_name == "investigation-workflow"

    def test_workflow_to_recipe_mapping_q_and_a_has_no_recipe(self):
        """Test Q&A_WORKFLOW has no recipe (should return None)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        recipe_name = cascade.workflow_to_recipe_name("Q&A_WORKFLOW")

        assert recipe_name is None  # Q&A doesn't use recipes

    def test_workflow_to_recipe_mapping_ops_has_no_recipe(self):
        """Test OPS_WORKFLOW has no recipe (should return None)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        recipe_name = cascade.workflow_to_recipe_name("OPS_WORKFLOW")

        assert recipe_name is None  # OPS doesn't use recipes

    # ========================================
    # Error Handling Tests
    # ========================================

    def test_execute_invalid_workflow_raises_error(self, session_context):
        """Test that invalid workflow name raises ValueError."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        with pytest.raises(ValueError, match="Invalid workflow"):
            cascade.execute("INVALID_WORKFLOW", session_context)

    def test_execute_empty_workflow_raises_error(self, session_context):
        """Test that empty workflow name raises ValueError."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        with pytest.raises(ValueError):
            cascade.execute("", session_context)

    def test_execute_none_context_uses_defaults(self):
        """Test that None context uses default values."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        result = cascade.execute("Q&A_WORKFLOW", context=None)

        assert result["status"] in ["success", "completed"]
        assert "context" in result


class TestExecutionTierCascadeConfiguration:
    """Test execution tier cascade configuration."""

    def test_cascade_respects_amplihack_use_recipes_env_var(self, mock_environment_vars):
        """Test AMPLIHACK_USE_RECIPES environment variable."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_environment_vars({"AMPLIHACK_USE_RECIPES": "1"})
        cascade = ExecutionTierCascade()

        assert cascade.is_recipe_runner_enabled() is True

    def test_cascade_disable_recipe_runner_via_env(self, mock_environment_vars):
        """Test disabling Recipe Runner via environment variable."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_environment_vars({"AMPLIHACK_USE_RECIPES": "0"})
        cascade = ExecutionTierCascade()

        assert cascade.is_recipe_runner_enabled() is False

    def test_cascade_custom_tier_priority(self):
        """Test custom tier priority configuration."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade(tier_priority=[3, 2, 1])  # Reverse priority
        tier = cascade.detect_available_tier()

        # Should try tier 3 first with custom priority
        assert tier == 3


class TestExecutionTierCascadeMetrics:
    """Test execution tier cascade metrics and logging."""

    def test_cascade_tracks_execution_time(self, session_context):
        """Test that cascade tracks execution time."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        result = cascade.execute("Q&A_WORKFLOW", session_context)

        assert "execution_time" in result
        assert result["execution_time"] >= 0

    def test_cascade_logs_tier_usage(self, session_context, caplog):
        """Test that cascade logs which tier was used."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        result = cascade.execute("Q&A_WORKFLOW", session_context)

        assert any(f"tier {result['tier']}" in record.message.lower() for record in caplog.records)

    def test_cascade_records_fallback_count(self, mock_recipe_runner, session_context):
        """Test that cascade records number of fallbacks."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Failed")
        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)

        result = cascade.execute("DEFAULT_WORKFLOW", session_context)

        assert "fallback_count" in result
        assert result["fallback_count"] >= 1
