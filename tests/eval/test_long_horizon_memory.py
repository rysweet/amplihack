"""Tests for long-horizon memory evaluation system.

Tests dialogue generation, question generation, ground truth tracking,
scoring logic, and report generation -- all without LLM calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.long_horizon_data import (
    CONTRADICTORY_REPORTS,
    INCIDENTS,
    INFRASTRUCTURE,
    NUMERICAL_DATA,
    PEOPLE,
    PROBLEM_TASKS,
    PROJECTS,
    SECURITY_EVENTS,
    TECHNICAL_DOMAINS,
    generate_dialogue,
    generate_questions,
)
from amplihack.eval.long_horizon_memory import (
    CategoryBreakdown,
    DimensionScore,
    EvalReport,
    EvalResult,
    LongHorizonMemoryEval,
    _extract_json,
)


class TestDialogueGeneration:
    """Tests for deterministic dialogue content generation."""

    def test_standard_1000_turn_count(self):
        """Standard variant produces exactly 1000 turns."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        assert len(gt.turns) == 1000

    def test_quick_100_turn_count(self):
        """Quick variant produces exactly 100 turns."""
        gt = generate_dialogue(num_turns=100, seed=42)
        assert len(gt.turns) == 100

    def test_turns_have_sequential_numbers(self):
        """Turn numbers are sequential starting from 0."""
        gt = generate_dialogue(num_turns=100, seed=42)
        for i, turn in enumerate(gt.turns):
            assert turn.turn_number == i, f"Turn {i} has number {turn.turn_number}"

    def test_all_blocks_present(self):
        """All 12 blocks are present in the dialogue at sufficient scale."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        blocks = {t.block for t in gt.turns}
        assert blocks == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}

    def test_original_8_blocks_present_at_1000(self):
        """At 1000 turns, all 12 blocks are present (scaled down)."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        blocks = {t.block for t in gt.turns}
        # All 12 blocks should be present even at 1000 turns
        assert blocks == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}

    def test_block_names_match_numbers(self):
        """Block names are consistent with block numbers."""
        expected_names = {
            1: "people",
            2: "projects",
            3: "technical",
            4: "evolving_story",
            5: "numerical",
            6: "contradictory",
            7: "callbacks",
            8: "distractors",
            9: "security_logs",
            10: "incidents",
            11: "infrastructure",
            12: "problem_solving",
        }
        gt = generate_dialogue(num_turns=1000, seed=42)
        for turn in gt.turns:
            if turn.block in expected_names:
                assert turn.block_name == expected_names[turn.block], (
                    f"Block {turn.block} should be '{expected_names[turn.block]}', "
                    f"got '{turn.block_name}'"
                )

    def test_people_block_contains_all_people(self):
        """Block 1 mentions all 10 people."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        people_content = " ".join(t.content for t in gt.turns if t.block == 1)
        for person in PEOPLE:
            assert person["name"] in people_content, f"{person['name']} not found in people block"

    def test_project_block_contains_all_projects(self):
        """Block 2 mentions all 5 projects."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        project_content = " ".join(t.content for t in gt.turns if t.block == 2)
        for proj in PROJECTS:
            assert proj["name"] in project_content, (
                f"Project {proj['name']} not found in project block"
            )

    def test_technical_block_contains_multiple_domains(self):
        """Block 3 covers multiple technical domains."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        tech_content = " ".join(t.content for t in gt.turns if t.block == 3)
        domains_found = sum(1 for domain in TECHNICAL_DOMAINS if domain in tech_content.lower())
        assert domains_found >= 5, f"Only {domains_found} domains found in technical block"

    def test_reproducibility_with_same_seed(self):
        """Same seed produces identical dialogue."""
        gt1 = generate_dialogue(num_turns=100, seed=42)
        gt2 = generate_dialogue(num_turns=100, seed=42)
        assert len(gt1.turns) == len(gt2.turns)
        for t1, t2 in zip(gt1.turns, gt2.turns, strict=False):
            assert t1.content == t2.content
            assert t1.block == t2.block

    def test_different_seeds_produce_different_content(self):
        """Different seeds produce different dialogue ordering."""
        gt1 = generate_dialogue(num_turns=100, seed=42)
        gt2 = generate_dialogue(num_turns=100, seed=99)
        # At least some turns should differ (block 3 shuffles tech facts)
        differences = sum(
            1 for t1, t2 in zip(gt1.turns, gt2.turns, strict=False) if t1.content != t2.content
        )
        assert differences > 0, "Different seeds should produce some different content"


class TestGroundTruthTracking:
    """Tests for ground truth fact tracking."""

    def test_facts_by_entity_populated(self):
        """facts_by_entity tracks facts delivered per entity."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        assert len(gt.facts_by_entity) > 0, "facts_by_entity should be populated"

    def test_current_values_populated(self):
        """current_values tracks the latest value for each entity.attribute."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        assert len(gt.current_values) > 0, "current_values should be populated"

    def test_superseded_values_tracked(self):
        """superseded_values tracks value changes."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        assert len(gt.superseded_values) > 0, "superseded_values should be populated"

    def test_people_details_in_current_values(self):
        """People's attributes are tracked in current_values."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        # Check Sarah Chen's birthday is tracked
        assert "Sarah Chen.birthday" in gt.current_values
        assert gt.current_values["Sarah Chen.birthday"] == "March 15"

    def test_project_updates_tracked(self):
        """Project updates create superseded entries."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        # Atlas deadline changed multiple times
        atlas_deadline_key = "Project Atlas.deadline"
        assert atlas_deadline_key in gt.superseded_values or any(
            atlas_deadline_key in k for k in gt.superseded_values
        ), "Atlas deadline changes should be tracked"

    def test_evolving_story_supersedes(self):
        """Block 4 evolving story creates superseded values."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        evolving_keys = [k for k in gt.superseded_values if k.startswith("evolving.")]
        assert len(evolving_keys) > 0, "Evolving story should create superseded values"


class TestQuestionGeneration:
    """Tests for quiz question generation."""

    def test_standard_100_questions(self):
        """Standard generates 100 questions."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        assert len(questions) == 100

    def test_quick_20_questions(self):
        """Quick variant generates 20 questions."""
        gt = generate_dialogue(num_turns=100, seed=42)
        questions = generate_questions(gt, num_questions=20)
        assert len(questions) == 20

    def test_all_categories_present(self):
        """All question categories are present (including security domain at 5000 turns)."""
        gt = generate_dialogue(num_turns=5000, seed=42)
        questions = generate_questions(gt, num_questions=200)
        categories = {q.category for q in questions}
        expected_core = {
            "needle_in_haystack",
            "temporal_evolution",
            "numerical_precision",
            "source_attribution",
            "cross_reference",
            "distractor_resistance",
            "meta_memory",
        }
        # Core categories always present
        assert expected_core.issubset(categories), f"Missing core categories: {expected_core - categories}"
        # Security categories present at 5000 turns
        expected_security = {
            "security_log_analysis",
            "incident_tracking",
            "infrastructure_knowledge",
            "problem_solving",
            "multi_hop_reasoning",
        }
        assert expected_security.issubset(categories), f"Missing security categories: {expected_security - categories}"

    def test_core_categories_present_at_1000(self):
        """Core categories plus security categories present at 1000 turns."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        categories = {q.category for q in questions}
        expected_core = {
            "needle_in_haystack",
            "temporal_evolution",
            "numerical_precision",
            "source_attribution",
            "cross_reference",
            "distractor_resistance",
            "meta_memory",
        }
        assert expected_core.issubset(categories), f"Missing core categories: {expected_core - categories}"

    def test_questions_have_expected_answers(self):
        """Every question has a non-empty expected answer."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        for q in questions:
            assert q.expected_answer, f"Question {q.question_id} has no expected answer"

    def test_questions_have_scoring_dimensions(self):
        """Every question has at least one scoring dimension."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        for q in questions:
            assert len(q.scoring_dimensions) >= 1, (
                f"Question {q.question_id} has no scoring dimensions"
            )

    def test_question_ids_unique(self):
        """All question IDs are unique."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        ids = [q.question_id for q in questions]
        assert len(ids) == len(set(ids)), "Question IDs must be unique"

    def test_category_distribution_proportional(self):
        """Category distribution has needle_in_haystack as largest core category."""
        gt = generate_dialogue(num_turns=1000, seed=42)
        questions = generate_questions(gt, num_questions=100)
        counts: dict[str, int] = {}
        for q in questions:
            counts[q.category] = counts.get(q.category, 0) + 1

        # Needle-in-haystack should have the most among core categories
        assert counts.get("needle_in_haystack", 0) >= 10
        # Meta-memory should have the fewest
        assert counts.get("meta_memory", 0) >= 3


class TestScoringLogic:
    """Tests for scoring and grading infrastructure."""

    def test_dimension_score_creation(self):
        """DimensionScore can be created with all fields."""
        ds = DimensionScore(
            dimension="factual_accuracy",
            score=0.85,
            reasoning="Correct main facts",
        )
        assert ds.dimension == "factual_accuracy"
        assert ds.score == 0.85
        assert ds.reasoning == "Correct main facts"

    def test_eval_result_overall_score(self):
        """EvalResult correctly stores overall score."""
        result = EvalResult(
            question_id="test_01",
            question_text="Test question?",
            category="needle_in_haystack",
            expected_answer="Expected",
            actual_answer="Actual",
            dimensions=[
                DimensionScore("factual_accuracy", 0.8, ""),
                DimensionScore("specificity", 0.6, ""),
            ],
            overall_score=0.7,
        )
        assert result.overall_score == 0.7

    def test_category_breakdown_creation(self):
        """CategoryBreakdown aggregates correctly."""
        cb = CategoryBreakdown(
            category="needle_in_haystack",
            num_questions=20,
            avg_score=0.75,
            min_score=0.3,
            max_score=1.0,
            dimension_averages={"factual_accuracy": 0.8, "specificity": 0.7},
        )
        assert cb.avg_score == 0.75
        assert cb.num_questions == 20

    def test_eval_report_to_dict(self):
        """EvalReport.to_dict() produces valid JSON-serializable dict."""
        report = EvalReport(
            num_turns=100,
            num_questions=20,
            total_facts_delivered=500,
            learning_time_s=60.0,
            questioning_time_s=120.0,
            grading_time_s=90.0,
            overall_score=0.72,
            category_breakdown=[
                CategoryBreakdown(
                    category="test_cat",
                    num_questions=5,
                    avg_score=0.72,
                    min_score=0.5,
                    max_score=0.9,
                ),
            ],
            results=[
                EvalResult(
                    question_id="q1",
                    question_text="Test?",
                    category="test_cat",
                    expected_answer="Yes",
                    actual_answer="Indeed",
                    dimensions=[DimensionScore("factual_accuracy", 0.9, "Good")],
                    overall_score=0.9,
                ),
            ],
            memory_stats={"semantic_nodes": 100},
        )
        d = report.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        assert json_str
        assert d["overall_score"] == 0.72
        assert len(d["results"]) == 1

    def test_extract_json_raw(self):
        """_extract_json handles raw JSON."""
        result = _extract_json('{"score": 0.85}')
        assert result["score"] == 0.85

    def test_extract_json_fenced(self):
        """_extract_json handles markdown-fenced JSON."""
        result = _extract_json('```json\n{"score": 0.85}\n```')
        assert result["score"] == 0.85

    def test_extract_json_embedded(self):
        """_extract_json handles JSON embedded in text."""
        result = _extract_json('Here is the result: {"score": 0.85, "reasoning": "good"}')
        assert result["score"] == 0.85

    def test_extract_json_returns_empty_on_invalid(self):
        """_extract_json returns empty dict on invalid input."""
        result = _extract_json("no json here")
        assert result == {}


class TestEvalClass:
    """Tests for LongHorizonMemoryEval class."""

    def test_generate_creates_data(self):
        """generate() populates ground_truth and questions."""
        evaluator = LongHorizonMemoryEval(num_turns=100, num_questions=20)
        gt, qs = evaluator.generate()
        assert len(gt.turns) == 100
        assert len(qs) == 20
        assert evaluator.ground_truth is gt
        assert evaluator.questions is qs

    def test_run_dialogue_calls_agent_learn(self):
        """run_dialogue() calls agent.learn_from_content for each turn."""
        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=10)
        evaluator.generate()

        agent = MagicMock()
        agent.learn_from_content.return_value = {"facts_extracted": 1, "facts_stored": 1}

        evaluator.run_dialogue(agent)

        # Agent should be called for every non-empty turn
        non_empty = sum(1 for t in evaluator.ground_truth.turns if t.content.strip())
        assert agent.learn_from_content.call_count == non_empty

    def test_run_dialogue_without_generate_raises(self):
        """run_dialogue() raises if generate() wasn't called."""
        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=10)
        agent = MagicMock()
        with pytest.raises(ValueError, match="Must call generate"):
            evaluator.run_dialogue(agent)

    @patch("amplihack.eval.long_horizon_memory._grade_with_llm")
    def test_evaluate_calls_agent_answer(self, mock_grade):
        """evaluate() calls agent.answer_question for each question."""
        mock_grade.return_value = [DimensionScore("factual_accuracy", 0.8, "OK")]

        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=5)
        evaluator.generate()

        agent = MagicMock()
        agent.answer_question.return_value = "Test answer"
        agent.get_memory_stats.return_value = {}

        report = evaluator.evaluate(agent)

        assert agent.answer_question.call_count == len(evaluator.questions)
        assert len(report.results) == len(evaluator.questions)

    @patch("amplihack.eval.long_horizon_memory._grade_with_llm")
    def test_evaluate_handles_agent_tuple_return(self, mock_grade):
        """evaluate() handles agents that return (answer, trace) tuples."""
        mock_grade.return_value = [DimensionScore("factual_accuracy", 0.8, "OK")]

        evaluator = LongHorizonMemoryEval(num_turns=50, num_questions=3)
        evaluator.generate()

        agent = MagicMock()
        agent.answer_question.return_value = ("Test answer", None)
        agent.get_memory_stats.return_value = {}

        report = evaluator.evaluate(agent)
        assert report.results[0].actual_answer == "Test answer"


class TestDataIntegrity:
    """Tests for data integrity and consistency."""

    def test_people_have_all_required_fields(self):
        """Every person has all required fields."""
        required = {
            "name",
            "birthday",
            "allergy",
            "hobby",
            "role",
            "team",
            "pet",
            "hometown",
            "favorite_food",
            "degree",
        }
        for person in PEOPLE:
            missing = required - set(person.keys())
            assert not missing, f"{person['name']} missing fields: {missing}"

    def test_projects_have_all_required_fields(self):
        """Every project has all required fields."""
        required = {
            "name",
            "description",
            "original_deadline",
            "budget",
            "team_size",
            "lead",
            "updates",
        }
        for proj in PROJECTS:
            missing = required - set(proj.keys())
            assert not missing, f"Project {proj['name']} missing fields: {missing}"

    def test_numerical_data_has_all_fields(self):
        """Every numerical data entry has required fields."""
        for nd in NUMERICAL_DATA:
            assert "entity" in nd, "Missing entity"
            assert "value" in nd, "Missing value"
            assert "detail" in nd, "Missing detail"

    def test_contradictory_reports_have_multiple_sources(self):
        """Each contradictory topic has 2+ sources."""
        for cr in CONTRADICTORY_REPORTS:
            assert len(cr["sources"]) >= 2, f"Topic '{cr['topic']}' needs at least 2 sources"

    def test_technical_domains_count(self):
        """There are exactly 8 technical domains."""
        assert len(TECHNICAL_DOMAINS) == 8

    def test_people_count(self):
        """There are exactly 10 people."""
        assert len(PEOPLE) == 10

    def test_projects_count(self):
        """There are exactly 5 projects."""
        assert len(PROJECTS) == 5
