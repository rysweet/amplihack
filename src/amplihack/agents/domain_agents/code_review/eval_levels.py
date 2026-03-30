"""Evaluation levels for the Code Review agent."""

from __future__ import annotations

from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario


def get_eval_levels() -> list[EvalLevel]:
    return [_l1(), _l2(), _l3(), _l4()]


def _l1() -> EvalLevel:
    return EvalLevel(
        level_id="L1",
        name="Basic Detection",
        description="Finds obvious bugs",
        passing_threshold=0.7,
        scenarios=[
            EvalScenario(
                scenario_id="L1-001",
                name="Undefined variable",
                input_data={"code": "def calc(x):\n    return x + y\n", "language": "python"},
                expected_output={
                    "issues": [{"type": "bug", "message_contains": "undefined"}],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify y is not defined.",
            ),
            EvalScenario(
                scenario_id="L1-002",
                name="Division by zero risk",
                input_data={"code": "def divide(a, b):\n    return a / b\n", "language": "python"},
                expected_output={
                    "issues": [{"type": "bug", "message_contains": "zero"}],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify division by zero risk.",
            ),
            EvalScenario(
                scenario_id="L1-003",
                name="Index out of range",
                input_data={
                    "code": "def get_last(items):\n    return items[len(items)]\n",
                    "language": "python",
                },
                expected_output={
                    "issues": [{"type": "bug", "message_contains": "index"}],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify off-by-one error.",
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
                    "issues": [{"type": "style", "message_contains": "naming"}],
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
                    "issues": [{"type": "style", "message_contains": "docstring"}],
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
                    "issues": [{"type": "style", "message_contains": "except"}],
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
                    "issues": [{"type": "security", "severity": "critical"}],
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
                    "issues": [{"type": "security", "severity": "critical"}],
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
                    "issues": [{"type": "security", "severity": "high"}],
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
                name="God class",
                input_data={
                    "code": "class AppManager:\n"
                    + "".join(f"    def method_{i}(self): pass\n" for i in range(10)),
                    "language": "python",
                },
                expected_output={
                    "issues": [{"type": "design", "message_contains": "single responsibility"}],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify god class.",
            ),
            EvalScenario(
                scenario_id="L4-002",
                name="Duplicated logic",
                input_data={
                    "code": "def process(orders):\n    for o in orders:\n        t = 0\n        for i in o.items:\n            t += i.price * i.qty\n        o.total = t\n\ndef calc_tax(orders):\n    for o in orders:\n        t = 0\n        for i in o.items:\n            t += i.price * i.qty\n        o.tax = t * 0.1\n",
                    "language": "python",
                },
                expected_output={
                    "issues": [{"type": "design", "message_contains": "duplicate"}],
                    "min_issue_count": 1,
                },
                grading_rubric="Must identify duplicated logic.",
            ),
        ],
    )
