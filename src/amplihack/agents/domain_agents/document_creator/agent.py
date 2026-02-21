"""Document Creator domain agent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

from . import eval_levels as _eval_levels
from .tools import analyze_structure, assess_audience, evaluate_content, format_document

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class DocumentCreatorAgent(DomainAgent):
    """Agent that creates and evaluates structured documents."""

    def __init__(
        self,
        agent_name: str = "document_creator_agent",
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            domain="document_creator",
            model=model,
            skill_injector=skill_injector,
        )

    def _register_tools(self) -> None:
        self.executor.register_action("analyze_structure", analyze_structure)
        self.executor.register_action("evaluate_content", evaluate_content)
        self.executor.register_action("format_document", format_document)
        self.executor.register_action("assess_audience", assess_audience)

    def get_system_prompt(self) -> str:
        prompt_file = _PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are an expert document creator."

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        content = task.get("content", "")
        task_type = task.get("task_type", "full_analysis")
        doc_type = task.get("doc_type", "report")
        target_audience = task.get("target_audience", "general")
        format_type = task.get("format_type", "markdown")

        if not content or not content.strip():
            return TaskResult(success=False, output=None, error="No content provided")

        if task_type == "analyze":
            return self._analyze(content, doc_type)
        if task_type == "evaluate":
            return self._evaluate(content, target_audience)
        if task_type == "format":
            return self._format(content, format_type)
        if task_type == "audience":
            return self._audience(content, target_audience)
        if task_type == "full_analysis":
            return self._full_analysis(content, doc_type, target_audience, format_type)
        return TaskResult(success=False, output=None, error=f"Unknown task_type: {task_type}")

    def _analyze(self, content: str, doc_type: str) -> TaskResult:
        r = self.executor.execute("analyze_structure", content=content, doc_type=doc_type)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "analyze"},
        )

    def _evaluate(self, content: str, audience: str) -> TaskResult:
        r = self.executor.execute("evaluate_content", content=content, audience=audience)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "evaluate"},
        )

    def _format(self, content: str, format_type: str) -> TaskResult:
        r = self.executor.execute("format_document", content=content, format_type=format_type)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "format"},
        )

    def _audience(self, content: str, target_audience: str) -> TaskResult:
        r = self.executor.execute("assess_audience", content=content, target_audience=target_audience)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "audience"},
        )

    def _full_analysis(
        self, content: str, doc_type: str, audience: str, format_type: str
    ) -> TaskResult:
        tool_results = {}
        for name, kwargs in [
            ("analyze_structure", {"content": content, "doc_type": doc_type}),
            ("evaluate_content", {"content": content, "audience": audience}),
            ("format_document", {"content": content, "format_type": format_type}),
            ("assess_audience", {"content": content, "target_audience": audience}),
        ]:
            r = self.executor.execute(name, **kwargs)
            tool_results[name] = r.output if r.success else {}

        structure = tool_results.get("analyze_structure", {})
        evaluation = tool_results.get("evaluate_content", {})
        formatting = tool_results.get("format_document", {})
        audience_result = tool_results.get("assess_audience", {})

        overall_score = (
            0.25 * structure.get("structure_score", 0)
            + 0.30 * evaluation.get("readability_score", 0)
            + 0.20 * formatting.get("formatting_score", 0)
            + 0.25 * audience_result.get("audience_score", 0)
        )

        return TaskResult(
            success=True,
            output={
                "structure": structure,
                "evaluation": evaluation,
                "formatting": formatting,
                "audience": audience_result,
                "overall_score": round(overall_score, 3),
                "heading_count": structure.get("heading_count", 0),
                "word_count": structure.get("word_count", 0),
                "readability_score": evaluation.get("readability_score", 0),
                "completeness": evaluation.get("completeness", 0),
                "formatting_score": formatting.get("formatting_score", 0),
                "audience_score": audience_result.get("audience_score", 0),
                "tool_results": tool_results,
            },
            metadata={"task_type": "full_analysis", "doc_type": doc_type},
        )

    def get_eval_levels(self) -> list[EvalLevel]:
        return _eval_levels.get_eval_levels()

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        plans = {
            "structure": (
                "1. Why document structure matters\n"
                "2. Heading hierarchy and organization\n"
                "3. Section flow and transitions\n"
                "4. Introduction and conclusion patterns\n"
                "5. Practice structuring"
            ),
            "audience": (
                "1. Identifying your audience\n"
                "2. Vocabulary adaptation\n"
                "3. Tone and formality\n"
                "4. Technical vs. executive writing\n"
                "5. Practice adaptation"
            ),
            "format": (
                "1. Markdown fundamentals\n"
                "2. Consistent formatting\n"
                "3. Lists and tables\n"
                "4. Visual hierarchy\n"
                "5. Practice formatting"
            ),
        }
        instructions = {
            "structure": (
                "When structuring documents:\n\n"
                "1. **Heading Hierarchy**: Use H1 for title, H2 for sections, H3 for subsections\n"
                "   Bad: All headings at same level\n"
                "   Good: Clear nesting that shows relationships\n\n"
                "2. **Introduction**: Always start with context and purpose\n"
                "   Bad: Jumping straight into details\n"
                "   Good: 'This report covers Q1 results for the engineering team'\n\n"
                "3. **Conclusion**: Summarize and provide next steps\n"
                "   Bad: Ending abruptly\n"
                "   Good: Recap key points, recommend actions\n\n"
                "4. **Section Flow**: Each section builds on the previous one"
            ),
            "audience": (
                "When adapting for audience:\n\n"
                "1. **Technical Audience**: Include specifics, code examples, API details\n"
                "   Bad: 'The system was updated'\n"
                "   Good: 'Migrated from REST v2 to v3, updating auth endpoints'\n\n"
                "2. **Executive Audience**: Focus on business impact, ROI, strategy\n"
                "   Bad: 'We refactored the authentication module'\n"
                "   Good: 'Security improvements reduced breach risk by 40%'\n\n"
                "3. **Beginner Audience**: Define terms, use simple language\n"
                "4. **General Audience**: Balance detail with accessibility"
            ),
            "format": (
                "When formatting documents:\n\n"
                "1. **Markdown Headings**: Use # for H1, ## for H2, etc.\n"
                "   Bad: INTRODUCTION (all caps for heading)\n"
                "   Good: ## Introduction\n\n"
                "2. **Lists**: Consistent markers (-, *, or numbered)\n"
                "3. **Emphasis**: *italic* for emphasis, **bold** for important terms\n"
                "4. **Spacing**: Blank line between sections for readability"
            ),
        }

        key = topic.lower().split()[0] if topic else "structure"
        lesson_plan = plans.get(key, plans["structure"])
        if student_level == "advanced":
            lesson_plan += "\n6. Advanced: Document design patterns"
        instruction = instructions.get(key, instructions["structure"])

        practice_content = {
            "structure": (
                "The project launched in March. We had a team of five. The main goal "
                "was to improve performance. We achieved a 30% speed improvement. "
                "The budget was $50K. We recommend expanding to Phase 2."
            ),
            "audience": (
                "# API Migration\n"
                "We migrated from v2 to v3. The ROI was 200%. Revenue increased "
                "by 15%. The SDK was updated. Customer satisfaction improved."
            ),
            "format": (
                "TITLE\n"
                "First section about the project\n"
                "SECOND SECTION\n"
                "- item one\n"
                "* item two\n"
                "+ item three\n"
            ),
        }
        content = practice_content.get(key, practice_content["structure"])

        questions = [
            f"What are the key principles of {topic} in document creation?",
            f"Can you show me an example of good {topic}?",
        ]
        answers = [
            f"The key principles of {topic} include clarity, consistency, and audience awareness.",
            f"A good example of {topic}: start with clear purpose, organize logically, conclude with next steps.",
        ]

        # Generate student attempt using tools
        structure = analyze_structure(content)
        evaluation = evaluate_content(content)
        if structure.get("sections"):
            attempt = (
                f"Student findings:\n"
                f"- Found {structure.get('heading_count', 0)} sections\n"
                f"- Structure score: {structure.get('structure_score', 0):.0%}\n"
                f"- Readability: {evaluation.get('readability_score', 0):.0%}\n"
                f"- Completeness: {evaluation.get('completeness', 0):.0%}"
            )
        else:
            attempt = "Student: Could not identify clear structure (needs more training)"

        return TeachingResult(
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_questions=questions,
            agent_answers=answers,
            student_attempt=attempt,
        )
