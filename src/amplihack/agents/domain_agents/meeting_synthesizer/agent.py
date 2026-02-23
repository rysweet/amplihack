"""Meeting Synthesizer domain agent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

from . import eval_levels as _eval_levels
from .tools import extract_action_items, generate_summary, identify_decisions, identify_topics

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class MeetingSynthesizerAgent(DomainAgent):
    """Agent that synthesizes meeting transcripts into structured outputs."""

    def __init__(
        self,
        agent_name: str = "meeting_synthesizer_agent",
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            domain="meeting_synthesizer",
            model=model,
            skill_injector=skill_injector,
        )

    def _register_tools(self) -> None:
        self.executor.register_action("extract_action_items", extract_action_items)
        self.executor.register_action("generate_summary", generate_summary)
        self.executor.register_action("identify_decisions", identify_decisions)
        self.executor.register_action("identify_topics", identify_topics)

    def get_system_prompt(self) -> str:
        prompt_file = _PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are an expert meeting synthesizer."

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        transcript = task.get("transcript", "")
        task_type = task.get("task_type", "full_synthesis")

        if not transcript or not transcript.strip():
            return TaskResult(success=False, output=None, error="No transcript provided")

        if task_type == "extract_actions":
            return self._extract_actions(transcript)
        if task_type == "summarize":
            return self._summarize(transcript)
        if task_type == "identify_speakers":
            return self._identify_speakers(transcript)
        if task_type == "full_synthesis":
            return self._full_synthesis(transcript)
        return TaskResult(success=False, output=None, error=f"Unknown task_type: {task_type}")

    def _extract_actions(self, transcript: str) -> TaskResult:
        r = self.executor.execute("extract_action_items", transcript=transcript)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        items = r.output if r.output else []
        return TaskResult(
            success=True,
            output={"action_items": items, "action_count": len(items)},
            metadata={"task_type": "extract_actions"},
        )

    def _summarize(self, transcript: str) -> TaskResult:
        r = self.executor.execute("generate_summary", transcript=transcript)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        summary = r.output if r.output else {}
        return TaskResult(
            success=True,
            output={
                "summary": summary,
                "participants": summary.get("participants", []),
                "word_count": summary.get("word_count", 0),
            },
            metadata={"task_type": "summarize"},
        )

    def _identify_speakers(self, transcript: str) -> TaskResult:
        r = self.executor.execute("generate_summary", transcript=transcript)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        summary = r.output if r.output else {}
        speakers = summary.get("participants", [])
        return TaskResult(
            success=True,
            output={"speakers": speakers, "speaker_count": len(speakers)},
            metadata={"task_type": "identify_speakers"},
        )

    def _full_synthesis(self, transcript: str) -> TaskResult:
        tool_results = {}
        for name in [
            "extract_action_items",
            "generate_summary",
            "identify_decisions",
            "identify_topics",
        ]:
            r = self.executor.execute(name, transcript=transcript)
            tool_results[name] = (
                r.output if r.success else ([] if name != "generate_summary" else {})
            )

        # Check for injected meeting-notes skill
        if self.executor.has_action("meeting-notes"):
            r = self.executor.execute("meeting-notes", transcript=transcript)
            if r.success:
                tool_results["meeting_notes"] = r.output

        action_items = tool_results.get("extract_action_items", [])
        summary = tool_results.get("generate_summary", {})
        decisions = tool_results.get("identify_decisions", [])
        topics = tool_results.get("identify_topics", [])

        return TaskResult(
            success=True,
            output={
                "action_items": action_items,
                "action_count": len(action_items),
                "summary": summary,
                "decisions": decisions,
                "decision_count": len(decisions),
                "topics": topics,
                "topic_count": len(topics),
                "participants": summary.get("participants", []),
                "tool_results": tool_results,
            },
            metadata={"task_type": "full_synthesis"},
        )

    def get_eval_levels(self) -> list[EvalLevel]:
        return _eval_levels.get_eval_levels()

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        plans = {
            "action": "1. What are action items?\n2. Identifying owners\n3. Extracting deadlines\n4. Prioritization\n5. Practice extraction",
            "summary": "1. Meeting structure\n2. Key point identification\n3. Participant roles\n4. Concise writing\n5. Practice summarization",
            "decision": "1. What constitutes a decision?\n2. Explicit vs implicit decisions\n3. Recording rationale\n4. Tracking follow-ups\n5. Practice identification",
        }
        instructions = {
            "action": (
                "When extracting action items from meeting transcripts:\n\n"
                "1. **Owner Identification**: Look for direct assignments - 'Bob, can you...' or self-assignments 'I will...'\n"
                "   Example: 'Alice: Bob, can you draft the spec by Friday?' -> Owner: Bob, Action: draft spec, Deadline: Friday\n\n"
                "2. **Deadline Extraction**: Look for temporal phrases - 'by Friday', 'next week', 'end of sprint'\n"
                "   Bad: Missing the deadline entirely\n"
                "   Good: Capturing both explicit ('by Friday') and relative ('next sprint') deadlines\n\n"
                "3. **Implicit Actions**: Watch for commitments without explicit assignment language\n"
                "   Example: 'I'll get you staging access today' is an action item for the speaker\n\n"
                "4. **Priority Signals**: Words like 'urgent', 'first', 'critical' indicate priority"
            ),
            "summary": (
                "When summarizing meetings:\n\n"
                "1. **Participant List**: Always identify who was in the meeting\n\n"
                "2. **Key Decisions**: Highlight what was decided, not just discussed\n"
                "   Bad: 'They talked about databases'\n"
                "   Good: 'Team decided to use PostgreSQL for the new service'\n\n"
                "3. **Action Items**: Include a summary of assigned tasks\n\n"
                "4. **Duration & Scope**: Estimate meeting length and breadth of topics"
            ),
            "decision": (
                "When identifying decisions in meetings:\n\n"
                "1. **Decision Indicators**: 'decided', 'agreed', 'approved', 'let's go with'\n\n"
                "2. **Implicit Decisions**: Sometimes decisions are made without explicit language\n"
                "   Example: 'Alice: We'll use PostgreSQL then.' is a decision even without 'decided'\n\n"
                "3. **Context Matters**: Record who made the decision and what alternatives were discussed\n\n"
                "4. **Follow-up Actions**: Decisions often generate action items"
            ),
        }
        key = topic.lower().split()[0] if topic else "action"
        lesson_plan = plans.get(key, plans["action"])
        if student_level == "advanced":
            lesson_plan += "\n6. Advanced: Multi-threaded discussion analysis"
        instruction = instructions.get(key, instructions["action"])

        practice = {
            "action": (
                "Alice: Let's review the sprint goals.\n"
                "Bob: I think we need to fix the login bug.\n"
                "Alice: Bob, can you fix the login bug by tomorrow?\n"
                "Charlie: I'll update the test suite by end of week.\n"
            ),
            "summary": (
                "Alice: Welcome to the planning meeting.\n"
                "Bob: We have three items on the agenda.\n"
                "Charlie: The first is the API migration.\n"
                "Alice: Let's prioritize that. It blocks other work.\n"
            ),
            "decision": (
                "Alice: We need to pick a framework.\n"
                "Bob: I suggest FastAPI.\n"
                "Charlie: After reviewing options, we decided to use FastAPI.\n"
                "Alice: Agreed. Bob will start the implementation.\n"
            ),
        }
        code = practice.get(key, practice["action"])
        questions = [
            f"What should I look for when extracting {topic}?",
            f"Can you give me an example of a {topic} extraction?",
        ]
        answers = [
            f"Focus on speaker assignment patterns and temporal indicators for {topic}.",
            f"A common {topic} pattern: 'Bob, can you do X by Y' -> Owner: Bob, Action: X, Deadline: Y.",
        ]

        # Generate student attempt from practice
        items = extract_action_items(code)
        if items:
            attempt = "Student findings:\n" + "\n".join(
                f"- Action: {i.get('action', '')} (Owner: {i.get('owner', 'unknown')})"
                for i in items[:5]
            )
        else:
            summary = generate_summary(code)
            if summary.get("participants"):
                attempt = (
                    f"Student: Found {len(summary['participants'])} participants: "
                    f"{', '.join(summary['participants'])}. "
                    f"Summary: {summary.get('summary_text', 'No summary generated')}"
                )
            else:
                attempt = "Student: No major findings (needs more training on this topic)"

        return TeachingResult(
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_questions=questions,
            agent_answers=answers,
            student_attempt=attempt,
        )
