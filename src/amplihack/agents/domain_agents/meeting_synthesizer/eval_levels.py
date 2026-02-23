"""Evaluation levels for the Meeting Synthesizer agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario

_SIMPLE_TRANSCRIPT = (
    "Alice: Good morning. Let's discuss the Q1 roadmap.\n"
    "Bob: I think we should prioritize the API redesign.\n"
    "Alice: Agreed. Bob, can you draft the API spec by Friday?\n"
    "Bob: Sure, I will have the draft ready by Friday.\n"
    "Charlie: I need to finish the database migration first.\n"
    "Alice: Charlie, please complete the migration by next Wednesday.\n"
    "Alice: Let's meet again next Monday to review progress.\n"
)

_MULTI_SPEAKER = (
    "Alice: Welcome to the sprint retrospective.\n"
    "Bob: The deployment pipeline improvements reduced deploy time by 40%.\n"
    "Charlie: We had three incidents related to the new caching layer.\n"
    "Diana: I think the caching issues were because we didn't have enough testing.\n"
    "Alice: Diana, can you set up integration tests for the cache by end of sprint?\n"
    "Diana: Yes, I will write the integration test suite.\n"
    "Bob: We also need monitoring. I'll add cache monitoring dashboards by next Tuesday.\n"
    "Charlie: We decided to move from Redis to Valkey.\n"
    "Alice: Charlie, please update the ADR document.\n"
    "Alice: I'll get you staging access today.\n"
)

_DECISIONS_TRANSCRIPT = (
    "Alice: We need to choose a database.\n"
    "Bob: I vote for PostgreSQL.\n"
    "Charlie: After discussion, we decided to use PostgreSQL.\n"
    "Alice: Agreed. Let's go with PostgreSQL.\n"
    "Bob: We also decided to use Redis for caching.\n"
)

_EMPTY_TRANSCRIPT = ""


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Basic Extraction",
        description="Extracts action items and summaries from clear transcripts",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Simple action extraction",
                input_data={"transcript": _SIMPLE_TRANSCRIPT, "task_type": "full_synthesis"},
                expected_output={"min_action_count": 1, "must_mention": ["Bob", "Alice"]},
                grading_rubric="Must extract at least 1 action item and mention key participants.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Summary generation",
                input_data={"transcript": _SIMPLE_TRANSCRIPT, "task_type": "summarize"},
                expected_output={"min_word_count": 1, "must_mention": ["Alice", "Bob"]},
                grading_rubric="Must generate a non-empty summary with participant names.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Empty transcript handling",
                input_data={"transcript": _EMPTY_TRANSCRIPT, "task_type": "full_synthesis"},
                expected_output={},
                grading_rubric="Must handle empty transcript gracefully without crashing.",
            ),
        ],
    )


def _l2() -> EvalLevel:
    return EvalLevel(
        level_id="L2",
        name="Attribution & Detail",
        description="Correctly attributes actions and identifies deadlines",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L2-001",
                name="Owner attribution",
                input_data={"transcript": _SIMPLE_TRANSCRIPT, "task_type": "extract_actions"},
                expected_output={"min_action_count": 2, "must_mention": ["Bob", "Charlie"]},
                grading_rubric="Must attribute action items to correct owners.",
            ),
            EvalScenario(
                scenario_id="L2-002",
                name="Deadline extraction",
                input_data={"transcript": _SIMPLE_TRANSCRIPT, "task_type": "extract_actions"},
                expected_output={"min_action_count": 1, "must_mention": ["Friday"]},
                grading_rubric="Must extract deadlines from action items.",
            ),
            EvalScenario(
                scenario_id="L2-003",
                name="Multi-speaker identification",
                input_data={"transcript": _MULTI_SPEAKER, "task_type": "identify_speakers"},
                expected_output={
                    "min_speaker_count": 4,
                    "must_mention": ["Alice", "Bob", "Charlie", "Diana"],
                },
                grading_rubric="Must identify all 4 speakers.",
            ),
        ],
    )


def _l3() -> EvalLevel:
    return EvalLevel(
        level_id="L3",
        name="Decision Tracking",
        description="Identifies decisions and key discussion points",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L3-001",
                name="Decision identification",
                input_data={"transcript": _DECISIONS_TRANSCRIPT, "task_type": "full_synthesis"},
                expected_output={"min_decision_count": 1, "must_mention": ["PostgreSQL"]},
                grading_rubric="Must identify the database decision.",
            ),
            EvalScenario(
                scenario_id="L3-002",
                name="Topic identification",
                input_data={"transcript": _MULTI_SPEAKER, "task_type": "full_synthesis"},
                expected_output={"min_topic_count": 1},
                grading_rubric="Must identify at least one discussion topic.",
            ),
        ],
    )


def _l4() -> EvalLevel:
    return EvalLevel(
        level_id="L4",
        name="Complex Synthesis",
        description="Handles complex multi-party meetings with overlapping threads",
        passing_threshold=0.5,
        scenarios=[
            EvalScenario(
                scenario_id="L4-001",
                name="Multi-party synthesis",
                input_data={"transcript": _MULTI_SPEAKER, "task_type": "full_synthesis"},
                expected_output={
                    "min_action_count": 2,
                    "must_mention": ["Diana", "Bob", "cache", "monitoring"],
                },
                grading_rubric="Must synthesize multiple action items across different speakers and topics.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Complete meeting analysis",
                input_data={"transcript": _MULTI_SPEAKER, "task_type": "full_synthesis"},
                expected_output={
                    "min_action_count": 2,
                    "min_decision_count": 1,
                    "must_mention": ["Redis", "Valkey"],
                },
                grading_rubric="Must capture actions, decisions, and technology mentions.",
            ),
        ],
    )
