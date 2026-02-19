"""Tests for metacognition grader.

Validates that the grader correctly scores reasoning traces
across different complexity levels and scenarios.
"""

from amplihack.eval.metacognition_grader import MetacognitionGrade, grade_metacognition


class TestEffortCalibration:
    """Test effort calibration scoring."""

    def test_simple_question_simple_path(self):
        """Simple recall with simple path should score 1.0."""
        trace = {
            "question": "What is X?",
            "intent": {"intent": "simple_recall"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.9,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.9, "L1")
        assert result.effort_calibration == 1.0

    def test_simple_question_iterative_penalized(self):
        """Simple recall with iterative loop should be penalized."""
        trace = {
            "question": "What is X?",
            "intent": {"intent": "simple_recall"},
            "steps": [
                {"step_type": "plan", "queries": ["q1", "q2"], "reasoning": ""},
                {"step_type": "search", "queries": ["q1", "q2"], "facts_found": 5},
                {"step_type": "evaluate", "evaluation": {"sufficient": True}},
            ],
            "total_queries_executed": 5,
            "total_facts_collected": 10,
            "iterations": 1,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.9, "L1")
        assert result.effort_calibration < 1.0

    def test_complex_question_simple_path_penalized(self):
        """Temporal comparison with simple path should be penalized."""
        trace = {
            "question": "Which improved most?",
            "intent": {"intent": "temporal_comparison"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.5,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.3, "L3")
        assert result.effort_calibration <= 0.3

    def test_complex_question_appropriate_effort(self):
        """Temporal comparison with 3-4 queries should score well."""
        trace = {
            "question": "Which improved most?",
            "intent": {"intent": "temporal_comparison"},
            "steps": [
                {"step_type": "plan", "queries": ["day 7", "day 10", "gold"], "reasoning": ""},
                {"step_type": "search", "queries": ["day 7", "day 10", "gold"], "facts_found": 8},
                {"step_type": "evaluate", "evaluation": {"sufficient": True, "confidence": 0.9}},
            ],
            "total_queries_executed": 3,
            "total_facts_collected": 8,
            "iterations": 1,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.9, "L3")
        assert result.effort_calibration == 1.0


class TestSufficiencyJudgment:
    """Test sufficiency judgment scoring."""

    def test_well_calibrated_high(self):
        """High confidence + high score = well calibrated."""
        trace = {
            "question": "test",
            "intent": {"intent": "simple_recall"},
            "steps": [
                {"step_type": "evaluate", "evaluation": {"sufficient": True, "confidence": 0.9}},
            ],
            "total_queries_executed": 2,
            "total_facts_collected": 5,
            "iterations": 1,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.85, "L1")
        assert result.sufficiency_judgment >= 0.9

    def test_overconfident(self):
        """High confidence + low score = overconfident."""
        trace = {
            "question": "test",
            "intent": {"intent": "temporal_comparison"},
            "steps": [
                {"step_type": "evaluate", "evaluation": {"sufficient": True, "confidence": 0.9}},
            ],
            "total_queries_executed": 2,
            "total_facts_collected": 3,
            "iterations": 1,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.3, "L3")
        assert result.sufficiency_judgment < 0.7

    def test_no_evaluation_steps(self):
        """No evaluation = low metacognition score."""
        trace = {
            "question": "test",
            "intent": {"intent": "multi_source_synthesis"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 3,
            "iterations": 0,
            "final_confidence": 0.0,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.3, "L2")
        assert result.sufficiency_judgment <= 0.6


class TestSearchQuality:
    """Test search quality scoring."""

    def test_all_searches_productive(self):
        """All queries found facts = high search quality."""
        trace = {
            "question": "test",
            "intent": {"intent": "multi_source_synthesis"},
            "steps": [
                {"step_type": "plan", "queries": ["q1", "q2", "q3"], "reasoning": ""},
                {"step_type": "search", "queries": ["q1", "q2", "q3"], "facts_found": 9},
                {"step_type": "evaluate", "evaluation": {"sufficient": True}},
            ],
            "total_queries_executed": 3,
            "total_facts_collected": 9,
            "iterations": 1,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.9, "L2")
        assert result.search_quality >= 0.8

    def test_no_queries(self):
        """No queries = neutral score."""
        trace = {
            "question": "test",
            "intent": {"intent": "simple_recall"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.8,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.9, "L1")
        assert result.search_quality == 0.5


class TestSelfCorrection:
    """Test self-correction scoring."""

    def test_refinement_after_insufficient(self):
        """Refining after insufficient evaluation should score well."""
        trace = {
            "question": "test",
            "intent": {"intent": "temporal_comparison"},
            "steps": [
                {"step_type": "plan", "queries": ["q1"], "reasoning": "initial"},
                {"step_type": "search", "queries": ["q1"], "facts_found": 3},
                {"step_type": "evaluate", "evaluation": {"sufficient": False, "confidence": 0.4}},
                {"step_type": "refine", "queries": ["q2", "q3"], "reasoning": "need more"},
                {"step_type": "search", "queries": ["q2", "q3"], "facts_found": 5},
                {"step_type": "evaluate", "evaluation": {"sufficient": True, "confidence": 0.9}},
            ],
            "total_queries_executed": 3,
            "total_facts_collected": 8,
            "iterations": 2,
            "final_confidence": 0.9,
            "used_simple_path": False,
        }
        result = grade_metacognition(trace, 0.9, "L3")
        assert result.self_correction >= 0.8

    def test_no_evaluation_low_correction(self):
        """No evaluation steps = low self-correction."""
        trace = {
            "question": "test",
            "intent": {"intent": "simple_recall"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.0,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.9, "L1")
        assert result.self_correction == 0.5


class TestOverallGrade:
    """Test overall grade computation."""

    def test_grade_returns_all_fields(self):
        """Grade result should have all expected fields."""
        trace = {
            "question": "test",
            "intent": {"intent": "simple_recall"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.8,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.9, "L1")

        assert isinstance(result, MetacognitionGrade)
        assert 0.0 <= result.effort_calibration <= 1.0
        assert 0.0 <= result.sufficiency_judgment <= 1.0
        assert 0.0 <= result.search_quality <= 1.0
        assert 0.0 <= result.self_correction <= 1.0
        assert 0.0 <= result.overall <= 1.0
        assert isinstance(result.details, dict)

    def test_overall_is_weighted_average(self):
        """Overall should be weighted average of dimensions."""
        trace = {
            "question": "test",
            "intent": {"intent": "simple_recall"},
            "steps": [],
            "total_queries_executed": 0,
            "total_facts_collected": 5,
            "iterations": 0,
            "final_confidence": 0.8,
            "used_simple_path": True,
        }
        result = grade_metacognition(trace, 0.9, "L1")

        expected_overall = (
            0.25 * result.effort_calibration
            + 0.30 * result.sufficiency_judgment
            + 0.25 * result.search_quality
            + 0.20 * result.self_correction
        )
        assert abs(result.overall - round(expected_overall, 3)) < 0.01
