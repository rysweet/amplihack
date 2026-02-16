"""
End-to-End tests for all 6 acceptance criteria scenarios.

Tests the complete user experience from session start to workflow execution.
Each test corresponds to a success criteria from Issue #2353.

Following TDD: These tests should FAIL until implementation is complete.
"""

from unittest.mock import patch

import pytest


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario1:
    """
    Scenario 1: Session Start with Recipe Runner Available
    User starts with: "Add authentication to the API"
    System announces: WORKFLOW: DEFAULT | Reason: keyword 'add' | Following: default-workflow via Recipe Runner
    Recipe Runner executes all 23 steps systematically
    """

    def test_scenario1_recipe_runner_available(self, mock_recipe_runner):
        """Test Scenario 1: DEFAULT workflow via Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
            "session_id": "scenario1-test",
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(context)

        # Verify classification
        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert "add" in result["reason"].lower()

        # Verify Recipe Runner invoked
        assert result["tier"] == 1
        assert result["method"] == "recipe_runner"
        mock_recipe_runner.run_recipe_by_name.assert_called_once_with(
            "default-workflow", context=context
        )

        # Verify announcement format
        announcement = result["announcement"]
        assert "WORKFLOW: DEFAULT" in announcement
        assert "Reason:" in announcement
        assert "keyword 'add'" in announcement.lower()
        assert "Following:" in announcement

    def test_scenario1_recipe_executes_23_steps(self, mock_recipe_runner):
        """Test that Recipe Runner executes all 23 workflow steps."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        # Mock recipe runner to return step execution details
        mock_recipe_runner.run_recipe_by_name.return_value = {
            "status": "success",
            "steps_executed": 23,
            "steps": [f"Step {i}" for i in range(23)],
        }

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(context)

        # Verify execution completed successfully
        execution = result.get("execution", {})
        assert execution.get("status") == "success"
        assert execution.get("method") == "recipe_runner"


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario2:
    """
    Scenario 2: Session Start without Recipe Runner
    User starts with: "Fix the login bug"
    System detects ImportError
    Falls back to Workflow Skills → Markdown as needed
    """

    def test_scenario2_recipe_runner_unavailable(self, mock_workflow_skill):
        """Test Scenario 2: Fallback when Recipe Runner unavailable."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Fix the login bug",
            "is_first_message": True,
            "session_id": "scenario2-test",
        }

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            skill = SessionStartClassifierSkill(workflow_skill=mock_workflow_skill)
            result = skill.process(context)

            # Verify classification
            assert result["workflow"] == "DEFAULT_WORKFLOW"
            assert "fix" in result["reason"].lower()

            # Verify fallback to Workflow Skills (Tier 2)
            assert result["tier"] == 2
            assert result["method"] == "workflow_skills"
            mock_workflow_skill.execute.assert_called_once()

    def test_scenario2_cascade_to_markdown(self):
        """Test cascade all the way to Markdown (Tier 3)."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Fix the login bug",
            "is_first_message": True,
        }

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            with patch(
                "amplihack.workflows.execution_tier_cascade.import_workflow_skills",
                side_effect=ImportError,
            ):
                skill = SessionStartClassifierSkill()
                result = skill.process(context)

                # Should cascade to Tier 3 (Markdown)
                assert result["tier"] == 3
                assert result["method"] == "markdown"
                assert result["status"] in ["success", "completed"]


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario3:
    """
    Scenario 3: Q&A Request
    User starts with: "What is the purpose of the architect agent?"
    System announces: WORKFLOW: Q&A
    Answers directly without Recipe Runner
    """

    def test_scenario3_q_and_a_direct_answer(self):
        """Test Scenario 3: Q&A workflow answers directly."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "What is the purpose of the architect agent?",
            "is_first_message": True,
            "session_id": "scenario3-test",
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Verify Q&A classification
        assert result["workflow"] == "Q&A_WORKFLOW"
        assert "what is" in result["reason"].lower()

        # Verify NO Recipe Runner (Q&A should not use recipes)
        assert result["method"] != "recipe_runner"

        # Verify announcement
        announcement = result["announcement"]
        assert "WORKFLOW: Q&A" in announcement

    def test_scenario3_q_and_a_no_recipe_execution(self, mock_recipe_runner):
        """Test that Q&A workflow doesn't invoke Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "What is the purpose of the architect agent?",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        _result = skill.process(context)

        # Recipe Runner should NOT be called for Q&A
        mock_recipe_runner.run_recipe_by_name.assert_not_called()


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario4:
    """
    Scenario 4: Explicit Command
    User starts with: /analyze src/
    System skips auto-classification
    Executes command directly
    """

    def test_scenario4_explicit_command_bypasses_classification(self):
        """Test Scenario 4: Explicit command bypasses auto-classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "/analyze src/",
            "is_first_message": True,
            "session_id": "scenario4-test",
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Should not activate for explicit commands
        assert result["activated"] is False
        assert result["reason"] == "explicit_command"

    def test_scenario4_various_commands_bypass(self):
        """Test various explicit commands bypass classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        commands = [
            "/ultrathink add authentication",
            "/analyze codebase",
            "/improve documentation",
            "/fix import errors",
            "/help",
            "/clear",
        ]

        skill = SessionStartClassifierSkill()

        for cmd in commands:
            context = {
                "user_request": cmd,
                "is_first_message": True,
            }
            result = skill.process(context)

            assert result["activated"] is False, f"Command {cmd} should bypass classification"


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario5:
    """
    Scenario 5: Recipe Runner Disabled
    User sets: AMPLIHACK_USE_RECIPES=0
    System skips Recipe Runner and uses Workflow Skills
    """

    def test_scenario5_recipe_runner_disabled_via_env(
        self, mock_environment_vars, mock_workflow_skill
    ):
        """Test Scenario 5: Recipe Runner disabled via environment variable."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_environment_vars({"AMPLIHACK_USE_RECIPES": "0"})

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
            "session_id": "scenario5-test",
        }

        skill = SessionStartClassifierSkill(workflow_skill=mock_workflow_skill)
        result = skill.process(context)

        # Should classify as DEFAULT but skip Recipe Runner
        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["tier"] == 2  # Skip to Workflow Skills
        assert result["method"] == "workflow_skills"
        mock_workflow_skill.execute.assert_called_once()

    def test_scenario5_recipe_runner_enabled_explicitly(
        self, mock_environment_vars, mock_recipe_runner
    ):
        """Test Recipe Runner enabled explicitly via AMPLIHACK_USE_RECIPES=1."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_environment_vars({"AMPLIHACK_USE_RECIPES": "1"})

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(context)

        # Should use Recipe Runner
        assert result["tier"] == 1
        assert result["method"] == "recipe_runner"


@pytest.mark.e2e
class TestAcceptanceCriteriaScenario6:
    """
    Scenario 6: Recipe Runner Failure
    Recipe Runner throws exception
    System falls back to Workflow Skills
    Logs error for debugging
    """

    def test_scenario6_recipe_runner_exception_fallback(
        self, mock_recipe_runner, mock_workflow_skill, caplog
    ):
        """Test Scenario 6: Recipe Runner failure falls back to Workflow Skills."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Recipe execution failed")

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
            "session_id": "scenario6-test",
        }

        skill = SessionStartClassifierSkill(
            recipe_runner=mock_recipe_runner, workflow_skill=mock_workflow_skill
        )
        result = skill.process(context)

        # Should classify as DEFAULT
        assert result["workflow"] == "DEFAULT_WORKFLOW"

        # Should fall back to Workflow Skills (Tier 2)
        assert result["tier"] == 2
        assert result["method"] == "workflow_skills"
        mock_workflow_skill.execute.assert_called_once()

        # Verify error was logged
        assert any("recipe execution failed" in record.message.lower() for record in caplog.records)
        assert any("fallback" in record.message.lower() for record in caplog.records)

    def test_scenario6_multiple_failures_cascade(
        self, mock_recipe_runner, mock_workflow_skill, caplog
    ):
        """Test multiple failures cascade to Markdown (Tier 3)."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Recipe failed")
        mock_workflow_skill.execute.side_effect = RuntimeError("Skill failed")

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill(
            recipe_runner=mock_recipe_runner, workflow_skill=mock_workflow_skill
        )
        result = skill.process(context)

        # Should cascade all the way to Markdown
        assert result["tier"] == 3
        assert result["method"] == "markdown"

        # Verify both errors logged
        assert any("recipe failed" in record.message.lower() for record in caplog.records)
        assert any("skill failed" in record.message.lower() for record in caplog.records)


@pytest.mark.e2e
class TestFullUserExperienceFlow:
    """Test complete end-to-end user experience flows."""

    def test_full_flow_new_feature_development(self, mock_recipe_runner):
        """Test full flow: New feature from session start to execution."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Implement JWT authentication for the API",
            "is_first_message": True,
            "session_id": "full-flow-feature",
            "cwd": "/test/project",
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(context)

        # Full flow verification
        assert result["activated"] is True
        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["tier"] == 1
        assert result["method"] == "recipe_runner"
        assert result["status"] in ["success", "completed"]
        assert "announcement" in result
        assert "execution" in result

    def test_full_flow_investigation_task(self, mock_recipe_runner):
        """Test full flow: Investigation task from session start."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Investigate how the authentication system integrates with the database",
            "is_first_message": True,
            "session_id": "full-flow-investigation",
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(context)

        # Verify INVESTIGATION workflow via Recipe Runner
        assert result["workflow"] == "INVESTIGATION_WORKFLOW"
        assert result["tier"] == 1
        assert result["method"] == "recipe_runner"
        mock_recipe_runner.run_recipe_by_name.assert_called_once_with(
            "investigation-workflow", context=context
        )

    def test_full_flow_ops_task(self):
        """Test full flow: Operations task (no Recipe Runner)."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Clean up old Docker containers and images",
            "is_first_message": True,
            "session_id": "full-flow-ops",
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Verify OPS workflow (doesn't use Recipe Runner)
        assert result["workflow"] == "OPS_WORKFLOW"
        assert result["method"] != "recipe_runner"
        assert result["status"] in ["success", "completed"]


@pytest.mark.e2e
class TestUserExperienceQuality:
    """Test user experience quality requirements."""

    def test_clear_workflow_announcements(self):
        """Test that workflow announcements are clear and helpful."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        test_cases = [
            ("Add authentication", "DEFAULT", "add"),
            ("What is the purpose?", "Q&A", "what is"),
            ("Investigate the system", "INVESTIGATION", "investigate"),
            ("Clean up files", "OPS", "clean"),
        ]

        skill = SessionStartClassifierSkill()

        for request, expected_workflow, expected_keyword in test_cases:
            context = {
                "user_request": request,
                "is_first_message": True,
            }
            result = skill.process(context)

            announcement = result["announcement"]
            # Verify announcement quality
            assert f"WORKFLOW: {expected_workflow}" in announcement
            assert "Reason:" in announcement
            assert expected_keyword.lower() in announcement.lower()
            assert "Following:" in announcement

    def test_performance_meets_nfr2(self):
        """Test that classification meets NFR2 (<5 seconds)."""
        import time

        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill()

        start = time.time()
        _result = skill.process(context)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Classification took {elapsed}s, expected <5s (NFR2)"

    def test_backward_compatibility_maintained(self, mock_environment_vars):
        """Test that existing workflows remain unaffected (NFR1)."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        # Test that explicit commands bypass classification
        skill = SessionStartClassifierSkill()

        context = {
            "user_request": "/ultrathink Add authentication",
            "is_first_message": True,
            "is_explicit_command": True,
        }

        result = skill.process(context)

        # Should bypass when explicit command
        assert result["activated"] is False
        assert result["bypassed"] is True
