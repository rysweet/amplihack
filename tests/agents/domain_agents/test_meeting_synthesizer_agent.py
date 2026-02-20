"""Tests for the MeetingSynthesizerAgent."""

from __future__ import annotations

from amplihack.agents.domain_agents.meeting_synthesizer.agent import MeetingSynthesizerAgent
from amplihack.agents.domain_agents.meeting_synthesizer.tools import (
    extract_action_items,
    generate_summary,
    identify_decisions,
    identify_topics,
)
from amplihack.agents.domain_agents.skill_injector import SkillInjector

_SAMPLE_TRANSCRIPT = (
    "Alice: Good morning. Let's discuss the Q1 roadmap.\n"
    "Bob: I think we should prioritize the API redesign.\n"
    "Alice: Agreed. Bob, can you draft the API spec by Friday?\n"
    "Bob: Sure, I will have the draft ready by Friday.\n"
    "Charlie: I need to finish the database migration first.\n"
    "Alice: Charlie, please complete the migration by next Wednesday.\n"
    "Alice: Let's meet again next Monday to review progress.\n"
)

_COMPLEX_TRANSCRIPT = (
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


class TestMeetingSynthesizerTools:
    """Test meeting synthesizer tool functions."""

    def test_extract_action_items_simple(self):
        items = extract_action_items(_SAMPLE_TRANSCRIPT)
        assert len(items) >= 2
        owners = [i["owner"] for i in items]
        assert "Bob" in owners or "Alice" in owners

    def test_extract_action_items_empty(self):
        items = extract_action_items("")
        assert items == []

    def test_extract_action_items_with_deadlines(self):
        items = extract_action_items(_SAMPLE_TRANSCRIPT)
        deadlines = [i["deadline"] for i in items if i["deadline"]]
        assert len(deadlines) >= 1

    def test_generate_summary(self):
        summary = generate_summary(_SAMPLE_TRANSCRIPT)
        assert summary["word_count"] > 0
        assert len(summary["participants"]) >= 2
        assert "Alice" in summary["participants"]
        assert summary["duration_estimate"]

    def test_generate_summary_empty(self):
        summary = generate_summary("")
        assert summary["word_count"] == 0
        assert summary["participants"] == []

    def test_identify_decisions(self):
        transcript = (
            "Alice: After discussion, we decided to use PostgreSQL.\n"
            "Bob: I agreed with Alice's proposal.\n"
        )
        decisions = identify_decisions(transcript)
        assert len(decisions) >= 1

    def test_identify_decisions_empty(self):
        decisions = identify_decisions("")
        assert decisions == []

    def test_identify_topics(self):
        topics = identify_topics(_SAMPLE_TRANSCRIPT)
        assert len(topics) >= 1
        for topic in topics:
            assert "topic" in topic
            assert "speakers" in topic

    def test_identify_topics_empty(self):
        topics = identify_topics("")
        assert topics == []


class TestMeetingSynthesizerAgent:
    """Test the MeetingSynthesizerAgent."""

    def test_init(self):
        agent = MeetingSynthesizerAgent("synth_1")
        assert agent.agent_name == "synth_1"
        assert agent.domain == "meeting_synthesizer"

    def test_tools_registered(self):
        agent = MeetingSynthesizerAgent()
        tools = agent.get_available_tools()
        assert "extract_action_items" in tools
        assert "generate_summary" in tools
        assert "identify_decisions" in tools
        assert "identify_topics" in tools

    def test_execute_full_synthesis(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task(
            {
                "transcript": _SAMPLE_TRANSCRIPT,
                "task_type": "full_synthesis",
            }
        )
        assert result.success is True
        output = result.output
        assert "action_items" in output
        assert "summary" in output
        assert "decisions" in output
        assert "topics" in output
        assert output["action_count"] >= 1

    def test_execute_extract_actions(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task(
            {
                "transcript": _SAMPLE_TRANSCRIPT,
                "task_type": "extract_actions",
            }
        )
        assert result.success is True
        assert result.output["action_count"] >= 1

    def test_execute_summarize(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task(
            {
                "transcript": _SAMPLE_TRANSCRIPT,
                "task_type": "summarize",
            }
        )
        assert result.success is True
        assert "participants" in result.output
        assert len(result.output["participants"]) >= 2

    def test_execute_identify_speakers(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task(
            {
                "transcript": _SAMPLE_TRANSCRIPT,
                "task_type": "identify_speakers",
            }
        )
        assert result.success is True
        assert result.output["speaker_count"] >= 2
        assert "Alice" in result.output["speakers"]

    def test_execute_empty_transcript(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task({"transcript": ""})
        assert result.success is False
        assert "No transcript" in result.error

    def test_get_eval_levels(self):
        agent = MeetingSynthesizerAgent()
        levels = agent.get_eval_levels()
        assert len(levels) == 4
        level_ids = [lv.level_id for lv in levels]
        assert level_ids == ["L1", "L2", "L3", "L4"]

    def test_eval_levels_have_scenarios(self):
        agent = MeetingSynthesizerAgent()
        levels = agent.get_eval_levels()
        for level in levels:
            assert len(level.scenarios) >= 1
            for scenario in level.scenarios:
                assert scenario.scenario_id
                assert scenario.input_data

    def test_teach(self):
        agent = MeetingSynthesizerAgent()
        result = agent.teach("action item extraction")
        assert result.lesson_plan
        assert result.instruction
        assert "action" in result.instruction.lower()
        assert len(result.student_questions) >= 1
        assert len(result.agent_answers) >= 1
        assert result.student_attempt

    def test_get_system_prompt(self):
        agent = MeetingSynthesizerAgent()
        prompt = agent.get_system_prompt()
        assert "meeting" in prompt.lower()

    def test_skill_injection(self):
        injector = SkillInjector()
        injector.register(
            "meeting_synthesizer", "meeting-notes", lambda transcript: {"notes": "test"}
        )
        agent = MeetingSynthesizerAgent(skill_injector=injector)
        assert "meeting-notes" in agent.get_available_tools()
        assert "meeting-notes" in agent.injected_skills

    def test_complex_transcript_synthesis(self):
        agent = MeetingSynthesizerAgent()
        result = agent.execute_task(
            {
                "transcript": _COMPLEX_TRANSCRIPT,
                "task_type": "full_synthesis",
            }
        )
        assert result.success is True
        assert result.output["action_count"] >= 2
        # Should find multiple speakers
        speakers = result.output["summary"].get("participants", [])
        assert len(speakers) >= 3
