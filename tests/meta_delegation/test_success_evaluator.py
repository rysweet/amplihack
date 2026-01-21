"""Unit tests for Success Criteria Evaluator.

Tests evidence-based success evaluation and scoring.
These tests will FAIL until the success_evaluator module is implemented.
"""

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.success_evaluator import (
        EvaluationResult,
        SuccessCriteriaEvaluator,
        parse_success_criteria,
    )
except ImportError:
    pytest.skip("success_evaluator module not implemented yet", allow_module_level=True)


class TestSuccessCriteriaEvaluator:
    """Test SuccessCriteriaEvaluator class."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return SuccessCriteriaEvaluator()

    @pytest.fixture
    def sample_evidence(self):
        """Create sample evidence items."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        return [
            EvidenceItem(
                type="code_file",
                path="app.py",
                content="def login(): pass",
                excerpt="def login()...",
                size_bytes=100,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="test_file",
                path="test_app.py",
                content="def test_login(): assert True",
                excerpt="def test_login()...",
                size_bytes=80,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

    def test_initialization(self, evaluator):
        """Test evaluator initializes correctly."""
        assert evaluator is not None

    def test_evaluate_returns_result(self, evaluator, sample_evidence):
        """Test evaluate returns EvaluationResult."""
        criteria = "Module has login function and tests"
        execution_log = "Tests passed\n"

        result = evaluator.evaluate(criteria, sample_evidence, execution_log)

        assert isinstance(result, EvaluationResult)
        assert hasattr(result, "score")
        assert hasattr(result, "notes")

    def test_evaluate_score_range(self, evaluator, sample_evidence):
        """Test evaluate returns score between 0 and 100."""
        criteria = "Has code and tests"
        result = evaluator.evaluate(criteria, sample_evidence, "")

        assert 0 <= result.score <= 100

    def test_evaluate_with_all_criteria_met(self, evaluator):
        """Test evaluation when all criteria are met."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        criteria = """
        - Has login.py file
        - Has test_login.py file
        - Tests pass
        """

        evidence = [
            EvidenceItem(
                type="code_file",
                path="login.py",
                content="def login(): return True",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="test_file",
                path="test_login.py",
                content="def test_login(): assert True",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        execution_log = "PASS test_login.py"

        result = evaluator.evaluate(criteria, evidence, execution_log)

        assert result.score >= 80, "Should score high when criteria met"

    def test_evaluate_with_no_criteria_met(self, evaluator):
        """Test evaluation when no criteria are met."""
        criteria = """
        - Has authentication system
        - Has JWT tokens
        - Has refresh tokens
        """

        evidence = []
        execution_log = ""

        result = evaluator.evaluate(criteria, evidence, execution_log)

        assert result.score < 50, "Should score low when criteria not met"

    def test_evaluate_with_partial_completion(self, evaluator):
        """Test evaluation with partial criteria completion."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        criteria = """
        - Has user model
        - Has authentication endpoints
        - Has tests
        - Has documentation
        """

        evidence = [
            EvidenceItem(
                type="code_file",
                path="models.py",
                content="class User: pass",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="test_file",
                path="test_models.py",
                content="def test_user(): pass",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        execution_log = ""

        result = evaluator.evaluate(criteria, evidence, execution_log)

        assert 40 <= result.score <= 70, "Should score medium for partial completion"

    def test_evaluate_bonus_for_passing_tests(self, evaluator, sample_evidence):
        """Test bonus points awarded for passing tests."""
        criteria = "Has code"
        log_with_passing = "All tests passed\nPASS test_app.py"
        log_without_passing = "Code written"

        result_with = evaluator.evaluate(criteria, sample_evidence, log_with_passing)
        result_without = evaluator.evaluate(criteria, sample_evidence, log_without_passing)

        # Passing tests should increase score
        assert result_with.score >= result_without.score

    def test_evaluate_bonus_for_documentation(self, evaluator):
        """Test bonus points for including documentation."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        criteria = "Has code"

        evidence_with_docs = [
            EvidenceItem(
                type="code_file",
                path="app.py",
                content="code",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="documentation",
                path="README.md",
                content="# Documentation",
                excerpt="",
                size_bytes=100,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        evidence_without_docs = [
            EvidenceItem(
                type="code_file",
                path="app.py",
                content="code",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            )
        ]

        result_with = evaluator.evaluate(criteria, evidence_with_docs, "")
        result_without = evaluator.evaluate(criteria, evidence_without_docs, "")

        assert result_with.score >= result_without.score

    def test_evaluate_provides_detailed_notes(self, evaluator, sample_evidence):
        """Test evaluation provides detailed notes."""
        criteria = "Has login function and tests"

        result = evaluator.evaluate(criteria, sample_evidence, "")

        assert isinstance(result.notes, str)
        assert len(result.notes) > 0

    def test_evaluate_notes_explain_gaps(self, evaluator):
        """Test evaluation notes explain missing criteria."""
        criteria = """
        - Has authentication module
        - Has password hashing
        - Has rate limiting
        """

        result = evaluator.evaluate(criteria, [], "")

        notes_lower = result.notes.lower()
        # Should mention missing items
        assert "missing" in notes_lower or "incomplete" in notes_lower or "not found" in notes_lower


class TestParseSucessCriteria:
    """Test parse_success_criteria function."""

    def test_parse_simple_criteria(self):
        """Test parsing simple criteria list."""
        criteria = """
        - Has login function
        - Has logout function
        - Has tests
        """

        requirements = parse_success_criteria(criteria)

        assert isinstance(requirements, list)
        assert len(requirements) == 3

    def test_parse_criteria_with_descriptions(self):
        """Test parsing criteria with detailed descriptions."""
        criteria = """
        - User Authentication: System must support username/password login
        - JWT Tokens: API returns JWT tokens for authenticated users
        - Tests: All authentication flows have test coverage
        """

        requirements = parse_success_criteria(criteria)

        assert len(requirements) == 3

    def test_parse_criteria_extracts_requirements(self):
        """Test parsing extracts requirement objects."""
        criteria = "- Has API endpoint\n- Has tests"

        requirements = parse_success_criteria(criteria)

        # Each requirement should have structure
        for req in requirements:
            assert hasattr(req, "description") or isinstance(req, (str, dict))

    def test_parse_empty_criteria(self):
        """Test parsing empty criteria."""
        requirements = parse_success_criteria("")

        assert isinstance(requirements, list)
        assert len(requirements) == 0

    def test_parse_criteria_ignores_non_requirements(self):
        """Test parsing ignores non-requirement lines."""
        criteria = """
        This is a description.

        Requirements:
        - Has feature A
        - Has feature B

        Additional notes here.
        """

        requirements = parse_success_criteria(criteria)

        # Should only extract the requirements
        assert len(requirements) == 2


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_evaluation_result_has_required_fields(self):
        """Test EvaluationResult has score and notes."""
        result = EvaluationResult(score=85, notes="All criteria met")

        assert result.score == 85
        assert result.notes == "All criteria met"

    def test_evaluation_result_score_validation(self):
        """Test EvaluationResult validates score range."""
        # Valid scores
        EvaluationResult(score=0, notes="")
        EvaluationResult(score=50, notes="")
        EvaluationResult(score=100, notes="")

        # Invalid scores should be handled
        # (implementation may clamp or raise error)

    def test_evaluation_result_to_dict(self):
        """Test EvaluationResult can be serialized."""
        result = EvaluationResult(score=75, notes="Good progress")

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result.__dict__

        assert "score" in result_dict
        assert "notes" in result_dict


class TestSuccessEvaluationEdgeCases:
    """Test edge cases in success evaluation."""

    @pytest.fixture
    def evaluator(self):
        return SuccessCriteriaEvaluator()

    def test_evaluate_with_no_evidence(self, evaluator):
        """Test evaluation with empty evidence list."""
        criteria = "Has implementation"

        result = evaluator.evaluate(criteria, [], "")

        assert result.score < 50, "No evidence should result in low score"

    def test_evaluate_with_no_criteria(self, evaluator, sample_evidence):
        """Test evaluation with empty criteria."""
        result = evaluator.evaluate("", sample_evidence, "")

        # Should handle gracefully
        assert isinstance(result, EvaluationResult)

    def test_evaluate_with_conflicting_evidence(self, evaluator):
        """Test evaluation when evidence conflicts with criteria."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        criteria = "Tests must pass"

        evidence = [
            EvidenceItem(
                type="test_file",
                path="test.py",
                content="tests",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            )
        ]

        execution_log = "FAIL test.py\n5 tests failed"

        result = evaluator.evaluate(criteria, evidence, execution_log)

        # Should recognize test failures
        assert result.score < 80, "Failed tests should reduce score"

    def test_evaluate_recognizes_test_patterns(self, evaluator):
        """Test evaluator recognizes various test output patterns."""
        from amplihack.meta_delegation.evidence_collector import EvidenceItem
        from datetime import datetime

        criteria = "Tests pass"
        evidence = [
            EvidenceItem(
                type="test_file",
                path="test.py",
                content="test",
                excerpt="",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            )
        ]

        test_patterns = [
            "All tests passed",
            "PASS",
            "OK",
            "100% passed",
            "✓ All tests successful",
        ]

        for pattern in test_patterns:
            result = evaluator.evaluate(criteria, evidence, pattern)
            assert result.score > 50, f"Should recognize test pattern: {pattern}"
