"""Evaluation levels for the Data Analysis agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Basic Statistics",
        description="Computes basic statistical measures",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Simple statistics",
                input_data={
                    "values": [10, 20, 30, 40, 50],
                    "task_type": "statistics",
                },
                expected_output={
                    "must_mention": ["mean", "median"],
                },
                grading_rubric="Must compute mean and median correctly.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Empty dataset",
                input_data={
                    "values": [],
                    "task_type": "statistics",
                },
                expected_output={},
                grading_rubric="Must handle empty dataset without crashing.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Single value",
                input_data={
                    "values": [42],
                    "task_type": "statistics",
                },
                expected_output={
                    "must_mention": ["mean"],
                },
                grading_rubric="Must handle single-element dataset.",
            ),
        ],
    )


def _l2() -> EvalLevel:
    return EvalLevel(
        level_id="L2",
        name="Trend Detection",
        description="Detects trends in sequential data",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L2-001",
                name="Increasing trend",
                input_data={
                    "values": [10, 15, 22, 28, 35, 41],
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "task_type": "trends",
                },
                expected_output={
                    "must_mention": ["increasing", "trend"],
                },
                grading_rubric="Must detect increasing trend.",
            ),
            EvalScenario(
                scenario_id="L2-002",
                name="Decreasing trend",
                input_data={
                    "values": [50, 45, 38, 32, 25, 20],
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "task_type": "trends",
                },
                expected_output={
                    "must_mention": ["decreasing", "trend"],
                },
                grading_rubric="Must detect decreasing trend.",
            ),
            EvalScenario(
                scenario_id="L2-003",
                name="Peak and trough identification",
                input_data={
                    "values": [10, 30, 20, 50, 15, 35],
                    "labels": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"],
                    "task_type": "trends",
                },
                expected_output={
                    "must_mention": ["peak"],
                },
                grading_rubric="Must identify peak value.",
            ),
        ],
    )


def _l3() -> EvalLevel:
    return EvalLevel(
        level_id="L3",
        name="Insight Quality",
        description="Generates meaningful analytical insights",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L3-001",
                name="Anomaly detection",
                input_data={
                    "values": [10, 12, 11, 13, 100, 12, 11],
                    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                    "title": "Weekly Sales",
                    "task_type": "insights",
                },
                expected_output={
                    "must_mention": ["anomal"],
                },
                grading_rubric="Must detect the anomalous Friday value.",
            ),
            EvalScenario(
                scenario_id="L3-002",
                name="Growth insight",
                input_data={
                    "values": [100, 120, 140, 165, 195, 230],
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "title": "Revenue Growth",
                    "task_type": "insights",
                },
                expected_output={
                    "must_mention": ["increasing", "growth"],
                },
                grading_rubric="Must identify growth pattern and provide recommendations.",
            ),
        ],
    )


def _l4() -> EvalLevel:
    return EvalLevel(
        level_id="L4",
        name="Storytelling",
        description="Produces narrative summaries from data",
        passing_threshold=0.5,
        scenarios=[
            EvalScenario(
                scenario_id="L4-001",
                name="Executive narrative",
                input_data={
                    "values": [100, 110, 105, 130, 145, 160],
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "title": "Quarterly Revenue",
                    "task_type": "narrative",
                    "style": "executive",
                },
                expected_output={
                    "must_mention": ["narrative", "trend"],
                },
                grading_rubric="Must produce executive-style narrative with trend analysis.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Storytelling narrative",
                input_data={
                    "values": [50, 30, 20, 25, 40, 55, 70],
                    "labels": ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6", "Week 7"],
                    "title": "Recovery Story",
                    "task_type": "narrative",
                    "style": "storytelling",
                },
                expected_output={
                    "must_mention": ["story", "narrative"],
                },
                grading_rubric="Must produce a narrative story from the data.",
            ),
        ],
    )
