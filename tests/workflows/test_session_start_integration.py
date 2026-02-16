"""
Integration tests for session start classifier skill.

Tests the complete flow:
1. Session start detection
2. Workflow classification
3. Execution tier selection
4. Recipe/Skill/Markdown execution

Following TDD: These tests should FAIL until implementation is complete.
"""

from unittest.mock import patch

import pytest


class TestSessionStartDetection:
    """Test session start detection logic."""

    # ========================================
    # Session Detection Tests (30% of tests)
    # ========================================

    def test_detect_session_start_first_message(self, session_context):
        """Test session start detection on first message."""
        from amplihack.workflows.session_start import SessionStartDetector

        detector = SessionStartDetector()
        is_start = detector.is_session_start(session_context)

        assert is_start is True

    def test_detect_session_start_not_first_message(self, session_context):
        """Test that follow-up messages don't trigger session start."""
        from amplihack.workflows.session_start import SessionStartDetector

        session_context["is_first_message"] = False
        detector = SessionStartDetector()
        is_start = detector.is_session_start(session_context)

        assert is_start is False

    def test_detect_explicit_command_bypasses_classification(self, session_context):
        """Test that explicit commands bypass auto-classification."""
        from amplihack.workflows.session_start import SessionStartDetector

        session_context["user_request"] = "/analyze src/"
        detector = SessionStartDetector()
        is_start = detector.is_session_start(session_context)

        assert is_start is False  # Commands bypass session start classification

    def test_detect_slash_command_patterns(self):
        """Test various slash command patterns."""
        from amplihack.workflows.session_start import SessionStartDetector

        detector = SessionStartDetector()
        commands = [
            "/ultrathink add auth",
            "/analyze codebase",
            "/improve documentation",
            "/fix import errors",
        ]

        for cmd in commands:
            context = {"user_request": cmd, "is_first_message": True}
            assert detector.is_session_start(context) is False

    def test_detect_builtin_command_bypasses(self):
        """Test that built-in commands bypass classification."""
        from amplihack.workflows.session_start import SessionStartDetector

        detector = SessionStartDetector()
        builtin_commands = ["/help", "/clear", "/exit"]

        for cmd in builtin_commands:
            context = {"user_request": cmd, "is_first_message": True}
            assert detector.is_session_start(context) is False


class TestSessionStartClassifierSkill:
    """Test session start classifier skill."""

    def test_skill_can_be_imported(self):
        """Test that session start skill can be imported."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        assert SessionStartClassifierSkill is not None

    @pytest.mark.integration
    def test_skill_activates_on_session_start(self, session_context):
        """Test that skill activates automatically on session start."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["activated"] is True
        assert "workflow" in result
        assert "tier" in result

    @pytest.mark.integration
    def test_skill_skips_on_explicit_command(self):
        """Test that skill skips activation for explicit commands."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "/ultrathink add authentication",
            "is_first_message": True,
        }
        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        assert result["activated"] is False
        assert result["reason"] == "explicit_command"

    @pytest.mark.integration
    def test_skill_classifies_and_executes_default_workflow(self, session_context):
        """Test complete flow: classify DEFAULT -> execute via Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication to the API"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["tier"] in [1, 2, 3]
        assert result["status"] in ["success", "completed"]

    @pytest.mark.integration
    def test_skill_handles_q_and_a_workflow(self, session_context):
        """Test Q&A workflow doesn't use Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "What is the purpose of the architect agent?"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["workflow"] == "Q&A_WORKFLOW"
        # Q&A should not use Recipe Runner (no recipe exists for Q&A)
        assert result["method"] != "recipe_runner"

    @pytest.mark.integration
    def test_skill_handles_ops_workflow(self, session_context):
        """Test OPS workflow execution."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Clean up disk space in /tmp"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["workflow"] == "OPS_WORKFLOW"
        assert result["status"] in ["success", "completed"]

    @pytest.mark.integration
    def test_skill_handles_investigation_workflow(self, session_context):
        """Test INVESTIGATION workflow via Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Investigate how the memory system works"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["workflow"] == "INVESTIGATION_WORKFLOW"
        assert result["tier"] in [1, 2, 3]


class TestSessionStartWithRecipeRunner:
    """Test session start with Recipe Runner (Tier 1)."""

    @pytest.mark.integration
    def test_recipe_runner_invoked_for_default_workflow(self, mock_recipe_runner, session_context):
        """Test Recipe Runner is invoked for DEFAULT_WORKFLOW."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication"
        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        _result = skill.process(session_context)

        mock_recipe_runner.run_recipe_by_name.assert_called_once_with(
            "default-workflow", context=session_context
        )

    @pytest.mark.integration
    def test_recipe_runner_invoked_for_investigation_workflow(
        self, mock_recipe_runner, session_context
    ):
        """Test Recipe Runner is invoked for INVESTIGATION_WORKFLOW."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Investigate the authentication system"
        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        _result = skill.process(session_context)

        mock_recipe_runner.run_recipe_by_name.assert_called_once_with(
            "investigation-workflow", context=session_context
        )

    @pytest.mark.integration
    def test_recipe_runner_not_invoked_for_q_and_a(self, mock_recipe_runner, session_context):
        """Test Recipe Runner is NOT invoked for Q&A_WORKFLOW."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "What is the purpose?"
        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        _result = skill.process(session_context)

        mock_recipe_runner.run_recipe_by_name.assert_not_called()


class TestSessionStartFallbackChain:
    """Test session start fallback chain scenarios."""

    @pytest.mark.integration
    def test_fallback_recipe_to_skills(
        self, mock_recipe_runner, mock_workflow_skill, session_context
    ):
        """Test fallback from Recipe Runner to Workflow Skills."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = ImportError("Recipe Runner unavailable")
        session_context["user_request"] = "Add authentication"

        skill = SessionStartClassifierSkill(
            recipe_runner=mock_recipe_runner, workflow_skill=mock_workflow_skill
        )
        result = skill.process(session_context)

        assert result["tier"] == 2
        assert result["method"] == "workflow_skills"
        mock_workflow_skill.execute.assert_called_once()

    @pytest.mark.integration
    def test_fallback_skills_to_markdown(self, mock_workflow_skill, session_context):
        """Test fallback from Workflow Skills to Markdown."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_workflow_skill.execute.side_effect = RuntimeError("Skill failed")
        session_context["user_request"] = "Add authentication"

        with patch(
            "amplihack.workflows.execution_tier_cascade.import_recipe_runner",
            side_effect=ImportError,
        ):
            skill = SessionStartClassifierSkill(workflow_skill=mock_workflow_skill)
            result = skill.process(session_context)

            assert result["tier"] == 3
            assert result["method"] == "markdown"

    @pytest.mark.integration
    def test_fallback_logs_error_details(self, mock_recipe_runner, session_context, caplog):
        """Test that fallback logs error details for debugging."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Connection timeout")
        session_context["user_request"] = "Add authentication"

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        result = skill.process(session_context)

        assert any("connection timeout" in record.message.lower() for record in caplog.records)
        assert result["tier"] > 1  # Should have fallen back


class TestSessionStartAnnouncement:
    """Test session start workflow announcements."""

    @pytest.mark.integration
    def test_announcement_format_default_recipe_runner(self, session_context):
        """Test announcement format for DEFAULT via Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        announcement = result["announcement"]
        assert "WORKFLOW: DEFAULT" in announcement
        assert "Reason: keyword 'add'" in announcement
        assert "Following:" in announcement

    @pytest.mark.integration
    def test_announcement_includes_tier_info(self, session_context):
        """Test that announcement includes tier information."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        announcement = result["announcement"]
        # Should mention Recipe Runner, Workflow Skills, or Markdown
        tier_keywords = ["recipe runner", "workflow skills", "markdown", "default-workflow"]
        assert any(keyword in announcement.lower() for keyword in tier_keywords)

    @pytest.mark.integration
    def test_announcement_clear_for_q_and_a(self, session_context):
        """Test announcement clarity for Q&A workflow."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "What is the purpose?"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        announcement = result["announcement"]
        assert "WORKFLOW: Q&A" in announcement
        assert "direct" in announcement.lower() or "answer" in announcement.lower()


class TestSessionStartPerformance:
    """Test session start performance requirements."""

    @pytest.mark.performance
    def test_session_start_classification_under_5_seconds(self, session_context):
        """Test that session start classification completes in <5s (NFR2)."""
        import time

        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication to the API"
        skill = SessionStartClassifierSkill()

        start = time.time()
        result = skill.process(session_context)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Session start took {elapsed}s, expected <5s"
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    @pytest.mark.performance
    def test_session_start_with_fallback_reasonable_time(self, mock_recipe_runner, session_context):
        """Test that session start with fallback still completes reasonably."""
        import time

        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Failed")
        session_context["user_request"] = "Add authentication"

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        start = time.time()
        result = skill.process(session_context)
        elapsed = time.time() - start

        # Even with fallback, should be reasonable (<10s)
        assert elapsed < 10.0
        assert result["tier"] > 1  # Should have fallen back


class TestSessionStartBackwardCompatibility:
    """Test backward compatibility (NFR1)."""

    @pytest.mark.integration
    def test_existing_workflows_unaffected_when_disabled(
        self, mock_environment_vars, session_context
    ):
        """Test that existing workflows work when session start is disabled."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_environment_vars({"AMPLIHACK_SESSION_START_CLASSIFIER": "0"})
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["activated"] is False
        assert result["reason"] == "disabled"

    @pytest.mark.integration
    def test_explicit_commands_still_work(self, session_context):
        """Test that explicit commands bypass and work as before."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "/ultrathink add authentication"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["activated"] is False
        # User's /ultrathink command should execute normally

    @pytest.mark.integration
    def test_follow_up_messages_unaffected(self, session_context):
        """Test that follow-up messages in same session are unaffected."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["is_first_message"] = False
        session_context["user_request"] = "Also add logout"

        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert result["activated"] is False
        # Follow-ups should not trigger auto-classification


class TestSessionStartContextPassing:
    """Test context passing through the chain."""

    @pytest.mark.integration
    def test_context_passed_to_recipe_runner(self, mock_recipe_runner, session_context):
        """Test that full context is passed to Recipe Runner."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication"
        session_context["custom_data"] = {"key": "value"}

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        _result = skill.process(session_context)

        call_args = mock_recipe_runner.run_recipe_by_name.call_args
        context_arg = call_args[1]["context"]
        assert context_arg["custom_data"]["key"] == "value"

    @pytest.mark.integration
    def test_context_augmented_with_classification_results(self, session_context):
        """Test that context is augmented with classification results."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        session_context["user_request"] = "Add authentication"
        skill = SessionStartClassifierSkill()
        result = skill.process(session_context)

        assert "workflow" in result["context"]
        assert "classification_time" in result["context"]
        assert "tier" in result["context"]
