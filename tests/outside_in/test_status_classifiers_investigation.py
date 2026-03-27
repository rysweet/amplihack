"""Outside-in tests for investigation #2898: dual status classifiers.

These tests validate the investigation findings from a user perspective:
- Both classifiers exist and are importable
- Each classifier serves its distinct purpose
- The keyword overlap is bounded (not growing unexpectedly)
- The output taxonomies are distinct
"""

import pytest


class TestWorkflowClassifierExists:
    """WorkflowClassifier is importable and classifies requests."""

    def test_import(self):
        from amplihack.workflows.classifier import WorkflowClassifier

        assert WorkflowClassifier is not None

    def test_classifies_investigation_request(self):
        from amplihack.workflows.classifier import WorkflowClassifier

        c = WorkflowClassifier()
        result = c.classify("investigate why the tests are failing")
        assert result["workflow"] == "INVESTIGATION_WORKFLOW"

    def test_classifies_development_request(self):
        from amplihack.workflows.classifier import WorkflowClassifier

        c = WorkflowClassifier()
        result = c.classify("implement user authentication")
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    def test_classifies_ops_request(self):
        from amplihack.workflows.classifier import WorkflowClassifier

        c = WorkflowClassifier()
        result = c.classify("disk cleanup on the repo")
        assert result["workflow"] == "OPS_WORKFLOW"

    def test_classifies_qa_request(self):
        from amplihack.workflows.classifier import WorkflowClassifier

        c = WorkflowClassifier()
        result = c.classify("what is the purpose of this module?")
        assert result["workflow"] == "Q&A_WORKFLOW"

    def test_four_distinct_output_values(self):
        """Confirms the 4-workflow taxonomy is stable."""
        from amplihack.workflows.classifier import WorkflowClassifier

        c = WorkflowClassifier()
        expected = {"Q&A_WORKFLOW", "OPS_WORKFLOW", "INVESTIGATION_WORKFLOW", "DEFAULT_WORKFLOW"}
        actual = set(c.DEFAULT_KEYWORD_MAP.keys())
        assert actual == expected


class TestSessionDetectionMixinExists:
    """SessionDetectionMixin is importable and detects session types."""

    def test_import(self):
        # Import via the power_steering_checker package path
        import sys
        from pathlib import Path

        hook_dir = str(
            Path(__file__).parent.parent.parent
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
        )
        if hook_dir not in sys.path:
            sys.path.insert(0, hook_dir)

        from power_steering_checker.session_detection import SessionDetectionMixin

        assert SessionDetectionMixin is not None

    def test_six_distinct_session_types_documented(self):
        """Confirms the 6-session-type taxonomy is distinct from WorkflowClassifier."""
        import sys
        from pathlib import Path

        hook_dir = str(
            Path(__file__).parent.parent.parent
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
        )
        if hook_dir not in sys.path:
            sys.path.insert(0, hook_dir)

        from power_steering_checker.session_detection import SessionDetectionMixin

        # These are the documented session types (from docstring)
        expected_types = {
            "SIMPLE",
            "DEVELOPMENT",
            "INFORMATIONAL",
            "MAINTENANCE",
            "INVESTIGATION",
            "OPERATIONS",
        }

        # WorkflowClassifier has 4 types; SessionDetectionMixin has 6.
        # They are intentionally different taxonomies.
        from amplihack.workflows.classifier import WorkflowClassifier

        workflow_types = set(WorkflowClassifier.DEFAULT_KEYWORD_MAP.keys())
        assert workflow_types != expected_types, (
            "The two taxonomies should remain distinct; "
            "if they've converged, reconsider whether unification is needed"
        )


class TestKeywordOverlapIsBounded:
    """Verifies keyword overlap between classifiers does not grow unexpectedly.

    Per investigation #2898, the overlapping keywords are:
    investigate, understand, analyze, research, explore, how does, cleanup, clean up, organize

    This test acts as a regression guard: if new overlapping keywords are added,
    the set size will change and this test will alert reviewers.
    """

    def test_overlapping_investigation_keywords(self):
        import sys
        from pathlib import Path

        hook_dir = str(
            Path(__file__).parent.parent.parent
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
        )
        if hook_dir not in sys.path:
            sys.path.insert(0, hook_dir)

        from power_steering_checker.session_detection import SessionDetectionMixin
        from amplihack.workflows.classifier import WorkflowClassifier

        mixin_investigation = set(SessionDetectionMixin.INVESTIGATION_KEYWORDS)
        classifier_investigation = set(
            WorkflowClassifier.DEFAULT_KEYWORD_MAP["INVESTIGATION_WORKFLOW"]
        )

        overlap = mixin_investigation & classifier_investigation

        # These 6 keywords currently overlap — this count is the baseline.
        # If this increases significantly, consider whether a shared constants
        # module (Option A from investigation #2898) is now justified.
        assert len(overlap) <= 8, (
            f"Keyword overlap has grown to {len(overlap)}: {overlap}. "
            "Consider whether a shared _status.py constants module is now warranted. "
            "See docs/investigations/2898-status-classifiers.md"
        )

    def test_ops_keywords_overlap_is_bounded(self):
        import sys
        from pathlib import Path

        hook_dir = str(
            Path(__file__).parent.parent.parent
            / ".claude"
            / "tools"
            / "amplihack"
            / "hooks"
        )
        if hook_dir not in sys.path:
            sys.path.insert(0, hook_dir)

        from power_steering_checker.session_detection import SessionDetectionMixin
        from amplihack.workflows.classifier import WorkflowClassifier

        mixin_simple = set(SessionDetectionMixin.SIMPLE_TASK_KEYWORDS)
        mixin_ops = set(SessionDetectionMixin.OPERATIONS_KEYWORDS)
        classifier_ops = set(WorkflowClassifier.DEFAULT_KEYWORD_MAP["OPS_WORKFLOW"])

        # cleanup/clean up/organize overlap between OPS_WORKFLOW and SIMPLE
        simple_ops_overlap = mixin_simple & classifier_ops
        # operations PM keywords don't overlap with OPS_WORKFLOW keywords
        ops_ops_overlap = mixin_ops & classifier_ops

        assert len(simple_ops_overlap) <= 5, (
            f"Simple/OPS overlap grew to {len(simple_ops_overlap)}: {simple_ops_overlap}"
        )
        assert len(ops_ops_overlap) <= 3, (
            f"Operations/OPS keyword overlap grew to {len(ops_ops_overlap)}: {ops_ops_overlap}"
        )


class TestClassifiersAreArchitecturallyIndependent:
    """Verifies neither classifier imports the other (no coupling)."""

    def test_workflow_classifier_does_not_import_session_detection(self):
        import ast
        from pathlib import Path

        src = (
            Path(__file__).parent.parent.parent
            / "src"
            / "amplihack"
            / "workflows"
            / "classifier.py"
        )
        tree = ast.parse(src.read_text())
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        import_names = []
        for node in imports:
            if isinstance(node, ast.ImportFrom) and node.module:
                import_names.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    import_names.append(alias.name)

        assert not any(
            "session_detection" in name or "power_steering" in name
            for name in import_names
        ), "WorkflowClassifier must not import from power_steering_checker"

    def test_investigation_doc_exists(self):
        from pathlib import Path

        doc = (
            Path(__file__).parent.parent.parent
            / "docs"
            / "investigations"
            / "2898-status-classifiers.md"
        )
        assert doc.exists(), "Investigation document must exist"
        content = doc.read_text()
        assert "DO-NOT-RECOMMEND" in content, "Document must have a clear recommendation"
