"""Tests for the CodeReviewAgent."""

from __future__ import annotations

from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent
from amplihack.agents.domain_agents.code_review.tools import (
    analyze_code,
    check_style,
    detect_security_issues,
    suggest_improvements,
)
from amplihack.agents.domain_agents.skill_injector import SkillInjector


class TestCodeReviewTools:
    """Test code review tool functions."""

    def test_analyze_code_python(self):
        code = (
            "import os\n"
            "\n"
            "class MyClass:\n"
            "    def method_one(self):\n"
            "        pass\n"
            "\n"
            "    def method_two(self):\n"
            "        if True:\n"
            "            return 1\n"
        )
        result = analyze_code(code, "python")
        assert result["line_count"] == 9
        assert result["function_count"] == 2
        assert result["class_count"] == 1
        assert result["import_count"] == 1
        assert result["complexity_indicators"]["branch_count"] >= 1

    def test_analyze_code_empty(self):
        result = analyze_code("")
        assert result["line_count"] == 0
        assert result["function_count"] == 0

    def test_check_style_long_line(self):
        code = "x = " + "a" * 200 + "\n"
        issues = check_style(code)
        assert any(i["type"] == "line_too_long" for i in issues)

    def test_check_style_camelcase(self):
        code = "def myFunction():\n    pass\n"
        issues = check_style(code)
        assert any(i["type"] == "naming_convention" for i in issues)

    def test_check_style_bare_except(self):
        code = "try:\n    pass\nexcept:\n    pass\n"
        issues = check_style(code)
        assert any(i["type"] == "bare_except" for i in issues)

    def test_check_style_clean_code(self):
        code = "def add(a, b):\n    return a + b\n"
        issues = check_style(code)
        # Clean code should have minimal issues
        assert len(issues) <= 1

    def test_detect_security_sql_injection(self):
        code = "cursor.execute(f\"SELECT * FROM users WHERE name = '{name}'\")\n"
        issues = detect_security_issues(code)
        assert any(i["type"] == "sql_injection" for i in issues)

    def test_detect_security_hardcoded_secret(self):
        code = 'API_KEY = "sk-1234567890"\n'  # pragma: allowlist secret
        issues = detect_security_issues(code)
        assert any(i["type"] == "hardcoded_secret" for i in issues)

    def test_detect_security_eval(self):
        code = "result = eval(user_input)\n"
        issues = detect_security_issues(code)
        assert any(i["type"] == "dangerous_function" for i in issues)

    def test_detect_security_os_system(self):
        code = 'os.system("rm -rf " + user_path)\n'
        issues = detect_security_issues(code)
        assert any(i["type"] == "command_injection" for i in issues)

    def test_detect_security_clean_code(self):
        code = "def add(a, b):\n    return a + b\n"
        issues = detect_security_issues(code)
        assert len(issues) == 0

    def test_suggest_improvements_missing_docstring(self):
        code = "def my_func(x):\n    return x + 1\n"
        suggestions = suggest_improvements(code)
        assert any(s["type"] == "missing_docstring" for s in suggestions)

    def test_suggest_improvements_empty(self):
        suggestions = suggest_improvements("")
        assert len(suggestions) == 0


class TestCodeReviewAgent:
    """Test the CodeReviewAgent."""

    def test_init(self):
        agent = CodeReviewAgent("reviewer_1")
        assert agent.agent_name == "reviewer_1"
        assert agent.domain == "code_review"

    def test_tools_registered(self):
        agent = CodeReviewAgent()
        tools = agent.get_available_tools()
        assert "analyze_code" in tools
        assert "check_style" in tools
        assert "detect_security_issues" in tools
        assert "suggest_improvements" in tools

    def test_execute_task_review(self):
        agent = CodeReviewAgent()
        result = agent.execute_task(
            {
                "code": "def add(a, b):\n    return a + b\n",
                "language": "python",
            }
        )
        assert result.success is True
        assert "issues" in result.output
        assert "score" in result.output
        assert "summary" in result.output
        assert 0.0 <= result.output["score"] <= 1.0

    def test_execute_task_finds_security_issue(self):
        agent = CodeReviewAgent()
        result = agent.execute_task(
            {
                "code": "cursor.execute(f\"SELECT * FROM users WHERE id = '{uid}'\")\n",
                "language": "python",
            }
        )
        assert result.success is True
        assert result.output["issue_count"] >= 1

    def test_execute_task_empty_code(self):
        agent = CodeReviewAgent()
        result = agent.execute_task({"code": ""})
        assert result.success is False
        assert "No code" in result.error

    def test_execute_task_with_focus_areas(self):
        agent = CodeReviewAgent()
        result = agent.execute_task(
            {
                "code": "x = 1\n",
                "language": "python",
                "focus_areas": ["security"],
            }
        )
        assert result.success is True
        assert "security" in result.metadata["focus_areas"]

    def test_get_eval_levels(self):
        agent = CodeReviewAgent()
        levels = agent.get_eval_levels()
        assert len(levels) == 4
        assert levels[0].level_id == "L1"
        assert levels[1].level_id == "L2"
        assert levels[2].level_id == "L3"
        assert levels[3].level_id == "L4"

    def test_eval_levels_have_scenarios(self):
        agent = CodeReviewAgent()
        levels = agent.get_eval_levels()
        for level in levels:
            assert len(level.scenarios) >= 1
            for scenario in level.scenarios:
                assert scenario.scenario_id
                assert scenario.name
                assert scenario.input_data
                assert scenario.expected_output
                assert scenario.grading_rubric

    def test_teach_security(self):
        agent = CodeReviewAgent()
        result = agent.teach("security review")
        assert result.lesson_plan
        assert (
            "security" in result.lesson_plan.lower() or "vulnerabilit" in result.lesson_plan.lower()
        )
        assert result.instruction
        assert len(result.student_questions) >= 1
        assert len(result.agent_answers) >= 1
        assert result.student_attempt

    def test_teach_style(self):
        agent = CodeReviewAgent()
        result = agent.teach("style review")
        assert result.instruction
        assert "naming" in result.instruction.lower() or "style" in result.instruction.lower()

    def test_get_system_prompt(self):
        agent = CodeReviewAgent()
        prompt = agent.get_system_prompt()
        assert "code reviewer" in prompt.lower() or "review" in prompt.lower()

    def test_skill_injection(self):
        injector = SkillInjector()
        injector.register(
            "code_review", "code-smell-detector", lambda code, language="python": {"smells": []}
        )
        agent = CodeReviewAgent(skill_injector=injector)
        assert "code-smell-detector" in agent.get_available_tools()
        assert "code-smell-detector" in agent.injected_skills

    def test_high_quality_code_gets_high_score(self):
        agent = CodeReviewAgent()
        result = agent.execute_task(
            {
                "code": (
                    "def add(a: int, b: int) -> int:\n"
                    '    """Add two integers.\n'
                    "\n"
                    "    Args:\n"
                    "        a: First number\n"
                    "        b: Second number\n"
                    "\n"
                    "    Returns:\n"
                    "        Sum of a and b\n"
                    '    """\n'
                    "    return a + b\n"
                ),
                "language": "python",
            }
        )
        assert result.success is True
        assert result.output["score"] >= 0.7

    def test_insecure_code_gets_low_score(self):
        agent = CodeReviewAgent()
        result = agent.execute_task(
            {
                "code": (
                    'API_KEY = "secret123"\ndef run(cmd):\n    os.system(cmd)\n    eval(cmd)\n'  # pragma: allowlist secret
                ),
                "language": "python",
            }
        )
        assert result.success is True
        assert result.output["score"] < 0.7
