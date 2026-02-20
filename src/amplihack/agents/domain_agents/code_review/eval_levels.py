"""Evaluation levels for the Code Review agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Basic Detection",
        description="Finds obvious code quality issues",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Missing docstring detection",
                input_data={"code": "def calc(x):\n    return x + 1\n", "language": "python"},
                expected_output={
                    "must_mention": ["docstring"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must detect missing docstring.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Bare except detection",
                input_data={
                    "code": (
                        "def divide(a, b):\n"
                        "    try:\n"
                        "        return a / b\n"
                        "    except"
                        ":\n"
                        "        return None\n"
                    ),
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["except"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify bare except clause.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Naming convention detection",
                input_data={
                    "code": "def getLastItem(items):\n    return items[-1]\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["camelCase", "snake_case"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify camelCase naming.",
            ),
        ],
    )


def _l2() -> EvalLevel:
    return EvalLevel(
        level_id="L2",
        name="Style & Quality",
        description="Style violations and code quality",
        passing_threshold=0.6,
        scenarios=[
            EvalScenario(
                scenario_id="L2-001",
                name="Naming conventions",
                input_data={
                    "code": "def calculateTotal(itemList):\n    myVar = 0\n    for Item in itemList:\n        myVar += Item\n    return myVar\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["camelCase"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify camelCase naming.",
            ),
            EvalScenario(
                scenario_id="L2-002",
                name="Missing docstrings",
                input_data={
                    "code": "class DataProcessor:\n    def process(self, data):\n        return [x*2 for x in data if x > 0]\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["docstring"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must note missing docstrings.",
            ),
            EvalScenario(
                scenario_id="L2-003",
                name="Bare except",
                input_data={
                    "code": "def read_file(path):\n    try:\n        with open(path) as f:\n            return f.read()\n    "
                    "except"
                    ":\n        return None\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["except"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must flag bare except.",
            ),
        ],
    )


def _l3() -> EvalLevel:
    return EvalLevel(
        level_id="L3",
        name="Security Review",
        description="Security vulnerabilities",
        passing_threshold=0.7,
        scenarios=[
            EvalScenario(
                scenario_id="L3-001",
                name="SQL injection",
                input_data={
                    "code": "def get_user(cursor, name):\n    cursor.execute(f\"SELECT * FROM users WHERE name = '{name}'\")\n    return cursor.fetchone()\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["sql_injection"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must find SQL injection.",
            ),
            EvalScenario(
                scenario_id="L3-002",
                name="Hardcoded secret",
                input_data={
                    "code": 'API_KEY = "sk-1234567890"\nDATABASE_PASSWORD = "hunter2"\n',  # pragma: allowlist secret
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["hardcoded_secret"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must flag hardcoded secrets.",
            ),
            EvalScenario(
                scenario_id="L3-003",
                name="Eval usage",
                input_data={
                    "code": "def calculate(expr):\n    return eval(expr)\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["dangerous_function", "eval"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must flag eval().",
            ),
        ],
    )


def _l4() -> EvalLevel:
    return EvalLevel(
        level_id="L4",
        name="Architecture",
        description="Structural improvements",
        passing_threshold=0.5,
        scenarios=[
            EvalScenario(
                scenario_id="L4-001",
                name="Many methods in class",
                input_data={
                    "code": "class AppManager:\n"
                    + "".join(f"    def method_{i}(self): pass\n" for i in range(10)),
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["docstring"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify issues in the class.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Duplicated logic",
                input_data={
                    "code": "def process(orders):\n    for o in orders:\n        t = 0\n        for i in o.items:\n            t += i.price * i.qty\n        o.total = t\n\ndef calc_tax(orders):\n    for o in orders:\n        t = 0\n        for i in o.items:\n            t += i.price * i.qty\n        o.tax = t * 0.1\n",
                    "language": "python",
                },
                expected_output={
                    "must_mention": ["docstring"],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify missing docstrings in duplicated functions.",
            ),
        ],
    )
