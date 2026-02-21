"""Data Analysis domain agent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

from . import eval_levels as _eval_levels
from .tools import compute_statistics, create_narrative, detect_trends, generate_insights

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class DataAnalysisAgent(DomainAgent):
    """Agent that analyzes data, detects trends, and generates insights."""

    def __init__(
        self,
        agent_name: str = "data_analysis_agent",
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            domain="data_analysis",
            model=model,
            skill_injector=skill_injector,
        )

    def _register_tools(self) -> None:
        self.executor.register_action("compute_statistics", compute_statistics)
        self.executor.register_action("detect_trends", detect_trends)
        self.executor.register_action("generate_insights", generate_insights)
        self.executor.register_action("create_narrative", create_narrative)

    def get_system_prompt(self) -> str:
        prompt_file = _PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are an expert data analyst."

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        values = task.get("values", [])
        task_type = task.get("task_type", "full_analysis")
        labels = task.get("labels", [])
        title = task.get("title", "Dataset")
        style = task.get("style", "executive")

        if task_type == "statistics":
            return self._statistics(values)
        if task_type == "trends":
            return self._trends(values, labels)
        if task_type == "insights":
            return self._insights(values, labels, title)
        if task_type == "narrative":
            return self._narrative(values, labels, title, style)
        if task_type == "full_analysis":
            return self._full_analysis(values, labels, title, style)
        return TaskResult(success=False, output=None, error=f"Unknown task_type: {task_type}")

    def _statistics(self, values: list) -> TaskResult:
        r = self.executor.execute("compute_statistics", data=values)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "statistics"},
        )

    def _trends(self, values: list, labels: list) -> TaskResult:
        if len(values) < 2:
            return TaskResult(
                success=True,
                output={"trend_direction": "insufficient_data", "data_points": len(values)},
                metadata={"task_type": "trends"},
            )
        r = self.executor.execute("detect_trends", data=values, labels=labels if labels else None)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "trends"},
        )

    def _insights(self, values: list, labels: list, title: str) -> TaskResult:
        data = {"values": values, "labels": labels, "title": title}
        r = self.executor.execute("generate_insights", data=data)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "insights"},
        )

    def _narrative(self, values: list, labels: list, title: str, style: str) -> TaskResult:
        data = {"values": values, "labels": labels, "title": title}
        r = self.executor.execute("create_narrative", data=data, style=style)
        if not r.success:
            return TaskResult(success=False, output=None, error=str(r.output))
        return TaskResult(
            success=True,
            output=r.output,
            metadata={"task_type": "narrative"},
        )

    def _full_analysis(
        self, values: list, labels: list, title: str, style: str
    ) -> TaskResult:
        tool_results = {}

        # Statistics
        r = self.executor.execute("compute_statistics", data=values)
        tool_results["statistics"] = r.output if r.success else {}

        # Trends (needs at least 2 data points)
        if len(values) >= 2:
            r = self.executor.execute("detect_trends", data=values, labels=labels if labels else None)
            tool_results["trends"] = r.output if r.success else {}
        else:
            tool_results["trends"] = {"trend_direction": "insufficient_data"}

        # Insights
        data = {"values": values, "labels": labels, "title": title}
        r = self.executor.execute("generate_insights", data=data)
        tool_results["insights"] = r.output if r.success else {}

        # Narrative
        r = self.executor.execute("create_narrative", data=data, style=style)
        tool_results["narrative"] = r.output if r.success else {}

        stats = tool_results.get("statistics", {})
        trends = tool_results.get("trends", {})
        insights = tool_results.get("insights", {})
        narrative = tool_results.get("narrative", {})

        return TaskResult(
            success=True,
            output={
                "statistics": stats,
                "trends": trends,
                "insights": insights,
                "narrative": narrative,
                "mean": stats.get("mean", 0),
                "median": stats.get("median", 0),
                "trend_direction": trends.get("trend_direction", "unknown"),
                "key_finding": insights.get("key_finding", ""),
                "anomalies": insights.get("anomalies", []),
                "recommendations": insights.get("recommendations", []),
                "tool_results": tool_results,
            },
            metadata={"task_type": "full_analysis", "title": title},
        )

    def get_eval_levels(self) -> list[EvalLevel]:
        return _eval_levels.get_eval_levels()

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        plans = {
            "statistics": (
                "1. What are descriptive statistics?\n"
                "2. Mean, median, mode\n"
                "3. Variance and standard deviation\n"
                "4. When to use each measure\n"
                "5. Practice computing"
            ),
            "trends": (
                "1. What is a trend?\n"
                "2. Detecting direction (up/down/stable)\n"
                "3. Rate of change\n"
                "4. Seasonal patterns\n"
                "5. Practice detection"
            ),
            "insights": (
                "1. From data to insight\n"
                "2. Anomaly detection\n"
                "3. Pattern recognition\n"
                "4. Actionable recommendations\n"
                "5. Practice analysis"
            ),
        }
        instructions = {
            "statistics": (
                "When computing statistics:\n\n"
                "1. **Mean**: Sum of all values divided by count\n"
                "   Example: [10, 20, 30] -> mean = 20\n\n"
                "2. **Median**: Middle value when sorted\n"
                "   Example: [10, 20, 30] -> median = 20\n"
                "   Example: [10, 20, 30, 40] -> median = 25\n\n"
                "3. **Standard Deviation**: Measure of spread\n"
                "   Low SD = data is clustered, High SD = data is spread out\n\n"
                "4. **When to Use**: Mean for symmetric data, median for skewed data"
            ),
            "trends": (
                "When detecting trends:\n\n"
                "1. **Direction**: Compare beginning to end\n"
                "   Increasing: more ups than downs\n"
                "   Decreasing: more downs than ups\n\n"
                "2. **Change Rate**: (end - start) / start\n"
                "   Example: 100 -> 150 = 50% increase\n\n"
                "3. **Peak/Trough**: Find max and min values\n\n"
                "4. **Segments**: Identify where direction changes"
            ),
            "insights": (
                "When generating insights:\n\n"
                "1. **Anomalies**: Values > 2 standard deviations from mean\n"
                "   These often indicate important events\n\n"
                "2. **Key Finding**: The single most important observation\n"
                "   Focus on what's actionable\n\n"
                "3. **Recommendations**: What should be done next\n"
                "   Always tie back to the data\n\n"
                "4. **Context**: Data without context is just numbers"
            ),
        }

        key = topic.lower().split()[0] if topic else "statistics"
        lesson_plan = plans.get(key, plans["statistics"])
        if student_level == "advanced":
            lesson_plan += "\n6. Advanced: Correlation and regression"
        instruction = instructions.get(key, instructions["statistics"])

        practice_data = [10, 15, 22, 28, 35, 41]
        stats = compute_statistics(practice_data)
        trends = detect_trends(practice_data)

        questions = [
            f"What should I focus on when doing {topic} analysis?",
            f"Can you give me an example of {topic} in practice?",
        ]
        answers = [
            f"Focus on the most important {topic} metrics. Always check for anomalies.",
            f"For example, with [10,15,22,28,35,41]: mean={stats['mean']}, trend={trends['trend_direction']}.",
        ]

        attempt = (
            f"Student findings:\n"
            f"- Computed mean: {stats['mean']}\n"
            f"- Detected trend: {trends['trend_direction']}\n"
            f"- Change rate: {trends['change_rate']:.1%}"
        )

        return TeachingResult(
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_questions=questions,
            agent_answers=answers,
            student_attempt=attempt,
        )
