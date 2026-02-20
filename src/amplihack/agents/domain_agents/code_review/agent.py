"""Code Review domain agent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

from . import eval_levels as _eval_levels
from .tools import analyze_code, check_style, detect_security_issues, suggest_improvements

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class CodeReviewAgent(DomainAgent):
    """Agent that reviews code for quality, security, and performance."""

    def __init__(
        self,
        agent_name: str = "code_review_agent",
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        super().__init__(
            agent_name=agent_name, domain="code_review", model=model, skill_injector=skill_injector
        )

    def _register_tools(self) -> None:
        self.executor.register_action("analyze_code", analyze_code)
        self.executor.register_action("check_style", check_style)
        self.executor.register_action("detect_security_issues", detect_security_issues)
        self.executor.register_action("suggest_improvements", suggest_improvements)

    def get_system_prompt(self) -> str:
        prompt_file = _PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return "You are an expert code reviewer."

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        code = task.get("code", "")
        language = task.get("language", "python")
        focus_areas = task.get("focus_areas", ["quality", "security", "style"])
        if not code or not code.strip():
            return TaskResult(success=False, output=None, error="No code provided for review")

        tool_results = {}
        for name in [
            "analyze_code",
            "check_style",
            "detect_security_issues",
            "suggest_improvements",
        ]:
            r = self.executor.execute(name, code=code, language=language)
            tool_results[name] = r.output if r.success else ([] if name != "analyze_code" else {})

        if self.executor.has_action("code-smell-detector"):
            r = self.executor.execute("code-smell-detector", code=code, language=language)
            if r.success:
                tool_results["code_smells"] = r.output

        all_issues = []
        for key in ["check_style", "detect_security_issues", "suggest_improvements"]:
            if isinstance(tool_results.get(key), list):
                all_issues.extend(tool_results[key])

        critical = sum(1 for i in all_issues if i.get("severity") == "critical")
        high = sum(1 for i in all_issues if i.get("severity") == "high")
        warning = sum(1 for i in all_issues if i.get("severity") == "warning")
        score = max(0.0, min(1.0, 1.0 - critical * 0.2 - high * 0.1 - warning * 0.05))

        severity_counts = {}
        for i in all_issues:
            s = i.get("severity", "info")
            severity_counts[s] = severity_counts.get(s, 0) + 1
        lc = tool_results.get("analyze_code", {}).get("line_count", 0)
        summary = f"Score: {score:.0%} | Issues: {len(all_issues)} | Lines: {lc}"

        return TaskResult(
            success=True,
            output={
                "issues": all_issues,
                "issue_count": len(all_issues),
                "score": round(score, 2),
                "summary": summary,
                "tool_results": tool_results,
            },
            metadata={"language": language, "focus_areas": focus_areas},
        )

    def get_eval_levels(self) -> list[EvalLevel]:
        return _eval_levels.get_eval_levels()

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        plans = {
            "security": "1. Common vulnerabilities\n2. SQL injection\n3. Secrets management\n4. Input validation\n5. Practice review",
            "style": "1. Why style matters\n2. PEP 8 naming\n3. Documentation\n4. Code organization\n5. Practice",
            "quality": "1. What is quality?\n2. Bug patterns\n3. Error handling\n4. Testing\n5. Practice",
        }
        instructions = {
            "security": 'When reviewing for security:\n\n1. **SQL Injection**: Never use f-strings for SQL. Use parameterized queries.\n   Bad: `f"SELECT * FROM users WHERE name = \'{name}\'"`\n   Good: `cursor.execute("SELECT * FROM users WHERE name = ?", (name,))`\n\n2. **Hardcoded Secrets**: Use environment variables, not string literals.\n\n3. **Dangerous Functions**: eval(), exec(), pickle.loads() with untrusted input.\n\n4. **Command Injection**: Use subprocess with shell=False.',
            "style": "Python style review:\n\n1. **Naming**: snake_case for functions, PascalCase for classes\n\n2. **Docstrings**: Every public function needs one\n\n3. **Line Length**: Under 120 characters\n\n4. **Exception Handling**: Never use bare except clauses - always catch specific exception types",
            "quality": "Code quality review:\n\n1. **Bug Detection**: undefined variables, off-by-one, None handling\n\n2. **Error Handling**: graceful, not swallowed\n\n3. **Edge Cases**: empty inputs, boundaries\n\n4. **Testing**: adequate coverage",
        }
        key = topic.lower().split()[0] if topic else "quality"
        lesson_plan = plans.get(key, plans["quality"])
        if student_level == "advanced":
            lesson_plan += "\n6. Advanced: Design patterns"
        instruction = instructions.get(key, instructions["quality"])
        practice = {
            "security": "def auth(cursor, user, pw):\n    cursor.execute(f\"SELECT * FROM users WHERE user='{user}' AND pw='{pw}'\")\n    return cursor.fetchone()\nAPI_SECRET = 'abc123'\ndef proc(data):\n    return eval(data)\n",  # pragma: allowlist secret
            "style": "class dataProcessor:\n    def processData(self, inputData):\n        try:\n            return [x*2 for x in inputData]\n        except Exception:\n            pass\n",
            "quality": "def get_item(items, idx):\n    return items[idx]\ndef average(nums):\n    return sum(nums) / len(nums)\n",
        }
        code = practice.get(key, practice["quality"])
        questions = [
            f"What should I look for when reviewing for {topic}?",
            f"Can you give me an example of a {topic} issue?",
        ]
        answers = [
            f"Focus on the most common {topic} patterns. Use a checklist approach.",
            f"A common {topic} issue is taking shortcuts - like using f-strings for SQL.",
        ]
        issues = (
            detect_security_issues(code)
            if "secur" in topic.lower()
            else check_style(code)
            if "style" in topic.lower()
            else suggest_improvements(code)
        )
        if issues:
            attempt = "Student findings:\n" + "\n".join(
                f"- {i.get('type', 'issue')}: {i.get('message', '')}" for i in issues[:5]
            )
        else:
            attempt = "Student: No major issues found (needs more training)"
        return TeachingResult(
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_questions=questions,
            agent_answers=answers,
            student_attempt=attempt,
        )
