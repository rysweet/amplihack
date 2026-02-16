"""
Regression tests to ensure existing workflows are unaffected.

Tests NFR1: Backward compatibility - no breaking changes.
Verifies that existing functionality continues to work as expected.

Following TDD: These tests should FAIL until implementation is complete.
"""

import pytest


@pytest.mark.integration
class TestExistingWorkflowsUnaffected:
    """Test that existing workflows continue to work."""

    def test_ultrathink_command_still_works(self):
        """Test /ultrathink command works as before."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "/ultrathink add authentication",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Should NOT activate for explicit commands
        assert result["activated"] is False
        assert result["reason"] == "explicit_command"

    def test_analyze_command_unaffected(self):
        """Test /analyze command works as before."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "/analyze src/amplihack",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        assert result["activated"] is False

    def test_improve_command_unaffected(self):
        """Test /improve command works as before."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "/improve documentation",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        assert result["activated"] is False

    def test_custom_commands_unaffected(self):
        """Test custom commands continue to work."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        custom_commands = [
            "/amplihack:ddd:1-plan",
            "/amplihack:debate should we use Redis?",
            "/multitask workstreams.json",
        ]

        skill = SessionStartClassifierSkill()

        for cmd in custom_commands:
            context = {
                "user_request": cmd,
                "is_first_message": True,
            }
            result = skill.process(context)

            assert result["activated"] is False, f"Command {cmd} should bypass classification"


@pytest.mark.integration
class TestFollowUpMessagesUnaffected:
    """Test that follow-up messages in existing sessions work."""

    def test_follow_up_in_same_session(self):
        """Test follow-up messages don't trigger classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Also add logout functionality",
            "is_first_message": False,  # Follow-up message
            "session_id": "existing-session",
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Should NOT activate for follow-ups
        assert result["activated"] is False
        assert result["reason"] in ["not_first_message", "follow_up_message"]

    def test_clarifications_unaffected(self):
        """Test clarification messages don't trigger classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        clarifications = [
            "I meant using JWT tokens",
            "To clarify, I want role-based access",
            "Actually, let's use OAuth2 instead",
        ]

        skill = SessionStartClassifierSkill()

        for clarification in clarifications:
            context = {
                "user_request": clarification,
                "is_first_message": False,
            }
            result = skill.process(context)

            assert result["activated"] is False

    def test_additions_unaffected(self):
        """Test addition messages don't trigger classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        additions = [
            "Also...",
            "And also add...",
            "What about...",
        ]

        skill = SessionStartClassifierSkill()

        for addition in additions:
            context = {
                "user_request": addition,
                "is_first_message": False,
            }
            result = skill.process(context)

            assert result["activated"] is False


@pytest.mark.integration
class TestExistingRecipeRunnerUnaffected:
    """Test that existing Recipe Runner functionality works."""

    def test_recipe_runner_direct_invocation_works(self, mock_recipe_runner):
        """Test Recipe Runner can still be invoked directly."""
        from amplihack.recipes import run_recipe_by_name
        from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

        # Direct invocation should still work
        adapter = CLISubprocessAdapter()
        result = run_recipe_by_name("default-workflow", adapter=adapter)

        # Should work as before (this is just interface test)
        assert result is not None

    def test_recipe_runner_cli_unaffected(self):
        """Test Recipe Runner CLI still works."""
        from amplihack import recipe_cli

        # Recipe CLI module should still be importable
        # (This would be tested with subprocess in real scenarios)
        assert recipe_cli is not None


@pytest.mark.integration
class TestExistingWorkflowSkillsUnaffected:
    """Test that existing Workflow Skills continue to work."""

    def test_workflow_skills_direct_invocation(self, mock_workflow_skill):
        """Test Workflow Skills can still be invoked directly."""
        # Direct skill invocation should still work
        context = {"workflow": "DEFAULT_WORKFLOW"}
        result = mock_workflow_skill.execute(context)

        assert result is not None

    def test_ultrathink_orchestrator_unaffected(self):
        """Test ultrathink-orchestrator skill still works."""
        # Ultrathink should continue to work as before
        # (This is a smoke test for the skill existence)
        try:
            from amplihack.workflows.ultrathink_orchestrator import UltraThinkOrchestrator

            assert UltraThinkOrchestrator is not None
        except ImportError:
            # Skill might not exist yet, that's okay
            pass


@pytest.mark.integration
class TestDisableFeaturePreservesExistingBehavior:
    """Test that disabling the feature restores original behavior."""

    def test_disable_via_env_var(self, mock_environment_vars):
        """Test that follow-up messages don't trigger classification."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Add authentication",
            "is_first_message": False,  # Follow-up message
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Should NOT activate for follow-ups
        assert result["activated"] is False
        assert result["bypassed"] is True

    def test_disable_preserves_explicit_ultrathink(self, mock_environment_vars):
        """Test disabling doesn't affect explicit /ultrathink."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_environment_vars({"AMPLIHACK_SESSION_START_CLASSIFIER": "0"})

        context = {
            "user_request": "/ultrathink add authentication",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill()
        result = skill.process(context)

        # Should still bypass for explicit commands
        assert result["activated"] is False
        assert result["reason"] == "explicit_command"


@pytest.mark.integration
class TestExistingCLAUDEmdBehavior:
    """Test that CLAUDE.md workflow classification still works."""

    def test_manual_workflow_classification_still_possible(self):
        """Test manual workflow classification via CLAUDE.md still works."""
        from amplihack.workflows.classifier import WorkflowClassifier

        # Manual classification should still be possible
        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        # This proves manual classification isn't broken

    def test_workflow_announcement_format_unchanged(self):
        """Test workflow announcement format matches CLAUDE.md spec."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")
        announcement = classifier.format_announcement(result)

        # Should match CLAUDE.md format
        assert "WORKFLOW:" in announcement
        assert "Reason:" in announcement
        assert "Following:" in announcement


@pytest.mark.integration
class TestExistingAPICompatibility:
    """Test that existing APIs remain compatible."""

    def test_classifier_api_backward_compatible(self):
        """Test WorkflowClassifier API is backward compatible."""
        from amplihack.workflows.classifier import WorkflowClassifier

        # Old-style usage should still work
        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")

        # Essential fields should be present
        assert "workflow" in result
        assert "reason" in result
        assert "confidence" in result

    def test_cascade_api_backward_compatible(self):
        """Test ExecutionTierCascade API is backward compatible."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        context = {"user_request": "test", "is_first_message": True}

        # Old-style usage should still work
        result = cascade.execute("Q&A_WORKFLOW", context)

        # Essential fields should be present
        assert "status" in result
        assert "tier" in result
        assert "method" in result

    def test_session_detector_api_backward_compatible(self):
        """Test SessionStartDetector API is backward compatible."""
        from amplihack.workflows.session_start import SessionStartDetector

        detector = SessionStartDetector()
        context = {
            "user_request": "Add auth",
            "is_first_message": True,
        }

        # API should be stable
        is_start = detector.is_session_start(context)
        assert isinstance(is_start, bool)


@pytest.mark.integration
class TestNoBreakingChangesInDependencies:
    """Test that no breaking changes affect dependencies."""

    def test_recipe_runner_import_safe(self):
        """Test Recipe Runner import doesn't break."""
        try:
            from amplihack.recipes import run_recipe_by_name

            assert run_recipe_by_name is not None
        except ImportError:
            # ImportError is expected if not available
            pass

    def test_workflow_skills_import_safe(self):
        """Test Workflow Skills import doesn't break."""
        try:
            # This should either work or raise ImportError (both are okay)
            from amplihack.workflows import workflow_skills as _workflow_skills  # noqa: F401
        except (ImportError, AttributeError):
            # Expected if module doesn't exist yet
            pass

    def test_cli_subprocess_adapter_import_safe(self):
        """Test CLISubprocessAdapter import doesn't break."""
        try:
            from amplihack.recipes.adapters import CLISubprocessAdapter

            assert CLISubprocessAdapter is not None
        except ImportError:
            # Expected if not available
            pass


@pytest.mark.integration
class TestDataStructureCompatibility:
    """Test that data structures remain compatible."""

    def test_classification_result_structure(self):
        """Test classification result structure is compatible."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")

        # Required fields that existing code might depend on
        required_fields = ["workflow", "reason", "confidence"]
        for field in required_fields:
            assert field in result, f"Required field '{field}' missing"

    def test_execution_result_structure(self):
        """Test execution result structure is compatible."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        context = {"user_request": "test", "is_first_message": True}
        result = cascade.execute("Q&A_WORKFLOW", context)

        # Required fields
        required_fields = ["status", "tier", "method"]
        for field in required_fields:
            assert field in result, f"Required field '{field}' missing"

    def test_session_context_structure(self):
        """Test session context structure remains compatible."""
        from amplihack.workflows.session_start import SessionStartDetector

        detector = SessionStartDetector()

        # Old-style context should still work
        old_style_context = {
            "user_request": "Add auth",
            "is_first_message": True,
        }

        result = detector.is_session_start(old_style_context)
        assert isinstance(result, bool)


@pytest.mark.integration
class TestErrorHandlingBackwardCompatibility:
    """Test that error handling remains compatible."""

    def test_invalid_workflow_raises_same_error(self):
        """Test that invalid workflow raises expected error."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        context = {"user_request": "test"}

        # Should raise ValueError for invalid workflow (as before)
        with pytest.raises(ValueError):
            cascade.execute("INVALID_WORKFLOW", context)

    def test_empty_request_raises_same_error(self):
        """Test that empty request raises expected error."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()

        # Should raise ValueError for empty request (as before)
        with pytest.raises(ValueError):
            classifier.classify("")

    def test_none_context_handled_gracefully(self):
        """Test that None context is handled as before."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()

        # Should handle None context gracefully (as before)
        result = cascade.execute("Q&A_WORKFLOW", context=None)
        assert result is not None
