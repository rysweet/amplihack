"""
Unit tests for workflow classifier module.

Tests the 4-way classification logic that routes requests to:
- Q&A_WORKFLOW
- OPS_WORKFLOW
- INVESTIGATION_WORKFLOW
- DEFAULT_WORKFLOW

Following TDD: These tests should FAIL until implementation is complete.
"""

import pytest


class TestWorkflowClassifier:
    """Test workflow classification logic."""

    # ========================================
    # Classification Logic Tests (60% of tests - unit level)
    # ========================================

    def test_classifier_imports(self):
        """Test that classifier module can be imported."""
        from amplihack.workflows.classifier import WorkflowClassifier

        assert WorkflowClassifier is not None

    def test_classify_q_and_a_what_is(self, sample_q_and_a_request):
        """Test Q&A classification for 'what is' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("What is the purpose of this module?")

        assert result["workflow"] == "Q&A_WORKFLOW"
        assert result["reason"] == "keyword 'what is'"
        assert result["confidence"] > 0.8

    def test_classify_q_and_a_explain_briefly(self):
        """Test Q&A classification for 'explain briefly' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Explain briefly how the memory system works")

        assert result["workflow"] == "Q&A_WORKFLOW"
        assert result["reason"] == "keyword 'explain briefly'"

    def test_classify_q_and_a_quick_question(self):
        """Test Q&A classification for 'quick question' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Quick question about the API design")

        assert result["workflow"] == "Q&A_WORKFLOW"

    def test_classify_ops_run_command(self):
        """Test OPS classification for 'run command' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Run command to clean up disk space")

        assert result["workflow"] == "OPS_WORKFLOW"
        assert result["reason"] == "keyword 'run command'"

    def test_classify_ops_disk_cleanup(self, sample_ops_request):
        """Test OPS classification for disk cleanup."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify(sample_ops_request)

        assert result["workflow"] == "OPS_WORKFLOW"
        # Accept both "cleanup" and "clean up" keywords
        assert "clean" in result["reason"].lower()

    def test_classify_ops_repo_management(self):
        """Test OPS classification for repo management."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Manage git repository branches")

        assert result["workflow"] == "OPS_WORKFLOW"

    def test_classify_investigation_keyword(self, sample_investigation_request):
        """Test INVESTIGATION classification for 'investigate' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify(sample_investigation_request)

        assert result["workflow"] == "INVESTIGATION_WORKFLOW"
        assert result["reason"] == "keyword 'investigate'"

    def test_classify_investigation_understand(self):
        """Test INVESTIGATION classification for 'understand' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Understand how the hooks system works")

        assert result["workflow"] == "INVESTIGATION_WORKFLOW"

    def test_classify_investigation_analyze(self):
        """Test INVESTIGATION classification for 'analyze' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Analyze the codebase architecture")

        assert result["workflow"] == "INVESTIGATION_WORKFLOW"

    def test_classify_default_implement(self, sample_user_request):
        """Test DEFAULT classification for 'implement' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Implement user authentication")

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["reason"] == "keyword 'implement'"

    def test_classify_default_add(self, sample_user_request):
        """Test DEFAULT classification for 'add' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify(sample_user_request)

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["reason"] == "keyword 'add'"

    def test_classify_default_fix(self):
        """Test DEFAULT classification for 'fix' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Fix the login bug")

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["reason"] == "keyword 'fix'"

    def test_classify_default_create(self):
        """Test DEFAULT classification for 'create' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Create a new API endpoint")

        assert result["workflow"] == "DEFAULT_WORKFLOW"

    def test_classify_default_refactor(self):
        """Test DEFAULT classification for 'refactor' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Refactor the authentication module")

        assert result["workflow"] == "DEFAULT_WORKFLOW"

    def test_classify_default_update(self):
        """Test DEFAULT classification for 'update' keyword."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Update the dependencies")

        assert result["workflow"] == "DEFAULT_WORKFLOW"

    # ========================================
    # Edge Cases and Ambiguity Tests
    # ========================================

    def test_classify_ambiguous_defaults_to_default_workflow(self):
        """Test that ambiguous requests default to DEFAULT_WORKFLOW."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Do something with the code")

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert "ambiguous" in result["reason"].lower() or "default" in result["reason"].lower()

    def test_classify_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        with pytest.raises(ValueError, match="Request cannot be empty"):
            classifier.classify("")

    def test_classify_none_raises_error(self):
        """Test that None raises TypeError."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        with pytest.raises(TypeError):
            classifier.classify(None)

    def test_classify_multiple_keywords_uses_priority(self):
        """Test that multiple keywords use priority (DEFAULT > others)."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Investigate and implement authentication")

        # DEFAULT_WORKFLOW should win when both investigation and implementation keywords present
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    # ========================================
    # Classification Speed Tests (NFR2: <5s)
    # ========================================

    @pytest.mark.performance
    def test_classification_speed_simple_request(self):
        """Test that classification completes in <5 seconds."""
        import time

        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        start = time.time()
        result = classifier.classify("Add authentication")
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Classification took {elapsed}s, expected <5s"
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    @pytest.mark.performance
    def test_classification_speed_complex_request(self):
        """Test that complex request classification completes in <5 seconds."""
        import time

        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        complex_request = "Investigate the current authentication implementation, understand how JWT tokens work, analyze security implications, and then implement a new role-based access control system"

        start = time.time()
        _result = classifier.classify(complex_request)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Classification took {elapsed}s, expected <5s"

    # ========================================
    # Context Passing Tests
    # ========================================

    def test_classify_with_context_session_id(self, session_context):
        """Test that classification accepts and uses session context."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication", context=session_context)

        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["context"]["session_id"] == "test-session-123"

    def test_classify_with_context_first_message_flag(self, session_context):
        """Test that classification uses is_first_message flag."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication", context=session_context)

        assert result["context"]["is_first_message"] is True

    # ========================================
    # Keyword Extraction Tests
    # ========================================

    def test_extract_keywords_q_and_a(self):
        """Test keyword extraction for Q&A workflows."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        keywords = classifier._extract_keywords("What is the purpose of this?")

        assert "what is" in keywords

    def test_extract_keywords_multiple(self):
        """Test keyword extraction with multiple matches."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        keywords = classifier._extract_keywords("Add authentication and fix bugs")

        assert "add" in keywords
        assert "fix" in keywords

    def test_extract_keywords_case_insensitive(self):
        """Test that keyword extraction is case-insensitive."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        keywords_lower = classifier._extract_keywords("add authentication")
        keywords_upper = classifier._extract_keywords("ADD AUTHENTICATION")

        assert keywords_lower == keywords_upper

    # ========================================
    # Confidence Scoring Tests
    # ========================================

    def test_confidence_high_for_clear_keywords(self):
        """Test high confidence for clear keyword matches."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Implement user authentication")

        assert result["confidence"] >= 0.9

    def test_confidence_lower_for_ambiguous(self):
        """Test lower confidence for ambiguous requests."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Do something with the code")

        assert result["confidence"] < 0.7


class TestWorkflowClassifierConfiguration:
    """Test workflow classifier configuration and initialization."""

    def test_classifier_loads_keywords_from_config(self):
        """Test that classifier loads keywords from configuration."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        assert hasattr(classifier, "_keyword_map")
        assert "Q&A_WORKFLOW" in classifier._keyword_map
        assert "DEFAULT_WORKFLOW" in classifier._keyword_map

    def test_classifier_custom_keywords(self):
        """Test that classifier accepts custom keyword mappings."""
        from amplihack.workflows.classifier import WorkflowClassifier

        custom_keywords = {
            "Q&A_WORKFLOW": ["custom_q", "custom_a"],
        }
        classifier = WorkflowClassifier(custom_keywords=custom_keywords)
        result = classifier.classify("custom_q about something")

        assert result["workflow"] == "Q&A_WORKFLOW"


class TestWorkflowClassifierAnnouncement:
    """Test workflow announcement formatting."""

    def test_format_announcement_default(self):
        """Test announcement formatting for DEFAULT_WORKFLOW."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")
        announcement = classifier.format_announcement(result)

        assert "WORKFLOW: DEFAULT" in announcement
        assert "Reason:" in announcement
        assert "Following:" in announcement

    def test_format_announcement_q_and_a(self):
        """Test announcement formatting for Q&A_WORKFLOW."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("What is the purpose?")
        announcement = classifier.format_announcement(result)

        assert "WORKFLOW: Q&A" in announcement

    def test_announcement_includes_recipe_info(self):
        """Test that announcement includes Recipe Runner info when available."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        result = classifier.classify("Add authentication")
        announcement = classifier.format_announcement(result, recipe_runner_available=True)

        assert "Recipe Runner" in announcement or "default-workflow" in announcement.lower()
